"""Real user boundaries and the actual Harbor oracle lifecycle; no model API calls."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from harbor.agents.installed.pi import Pi
from harbor.models.agent.context import AgentContext

from language_agent.agent import REMOTE_STOP_SCRIPT, STOP_SCRIPT, SequentialPi

TASK = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.docker


@pytest.fixture(scope="module")
def docker_available():
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("Docker is unavailable")
    if result.returncode:
        pytest.skip(
            "Docker daemon is unavailable (enable WSL integration when using Docker Desktop)"
        )


@pytest.fixture
def container(docker_available):
    build = subprocess.run(
        ["docker", "build", "-t", "programming-language:checks", str(TASK / "environment")],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    result = subprocess.run(
        ["docker", "run", "-d", "--rm", "programming-language:checks", "sleep", "infinity"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    identity = result.stdout.strip()
    try:
        yield identity
    finally:
        subprocess.run(["docker", "stop", identity], capture_output=True, check=True, timeout=30)


def command(container, *argv, user="agent", source=""):
    return subprocess.run(
        ["docker", "exec", "-i", "--user", user, container, *argv],
        input=source,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_private_files_commands_and_source_paths(container):
    forbidden = [
        ["cat", "/opt/programming-language/trial.json"],
        ["cat", "/opt/programming-language/state.json"],
        ["cat", "/opt/programming-language/language_game/engine.py"],
        ["language-lab", "start", "1"],
        ["language-lab", "settle", "1"],
        ["language-lab", "submit", "problem-02"],
        ["/usr/bin/python3", "-I", "/opt/programming-language/admin.py", "settle", "1"],
        ["sudo", "-n", "/bin/sh"],
        ["sudo", "-n", "PYTHONPATH=/app/workspace", "/usr/local/libexec/language-public", "status"],
        ["rm", "/app/view.txt"],
        ["mv", "/app/problems", "/app/workspace/problems"],
        ["ln", "-s", "/opt/programming-language/trial.json", "/app/problems/problem-01.jsonl"],
        ["sh", "-c", "language-lab compile problem-01 < /opt/programming-language/trial.json"],
    ]
    for argv in forbidden:
        result = command(container, *argv)
        assert result.returncode != 0, argv
        assert '"operations"' not in result.stdout
    assert (
        command(
            container, "test", "!", "-e", "/opt/programming-language/oracle.py", user="root"
        ).returncode
        == 0
    )
    # Spoofing local Python modules must not affect isolated privileged imports.
    command(
        container, "sh", "-c", "printf 'raise Exception(\"poison\")\n' > /app/workspace/json.py"
    )
    status = command(container, "sh", "-c", "cd /app/workspace && language-lab status")
    assert status.returncode == 0 and "problem-01" in status.stdout


def test_all_steps_oracle_permissions_logs_and_idempotence(container):
    admin = ["/usr/bin/python3", "-I", "/opt/programming-language/admin.py"]
    # The root verifier must restore access after Harbor's log ownership transfer.
    setup = r"""
from pathlib import Path
import os
p = Path('/logs/agent/pi/sessions')
p.mkdir(parents=True, exist_ok=True)
f = p / 'session.jsonl'
f.write_text('first\n')
os.chown(f, 1000, 1000)
f.chmod(0o600)
(p / 'private-link').symlink_to('/opt/programming-language/trial.json')
"""
    assert command(container, "python3", "-c", setup, user="root").returncode == 0
    assert command(container, "cat", "/logs/agent/pi/sessions/session.jsonl").returncode != 0
    assert command(container, "sh", "-c", "echo keep > /app/notes.md").returncode == 0
    trial_before = command(
        container, "cat", "/opt/programming-language/trial.json", user="root"
    ).stdout
    for index in range(1, 21):
        script = (TASK / f"steps/problem-{index:02d}/solution/solve.sh").read_text()
        result = command(container, "bash", source=script)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["score"] == 1
        settled = command(container, *admin, "settle", str(index), user="root")
        assert settled.returncode == 0, settled.stderr
        reward = command(container, "cat", "/logs/verifier/reward.json", user="root").stdout
        assert json.loads(reward)["reward"] == 1
        assert command(container, "cat", "/logs/verifier/reward.json").returncode != 0
        assert command(container, "cat", "/app/notes.md").stdout.strip() == "keep"
    assert command(container, "cat", "/logs/agent/pi/sessions/session.jsonl").stdout == "first\n"
    assert command(container, "cat", "/logs/agent/pi/sessions/private-link").returncode != 0
    assert (
        command(container, "cat", "/opt/programming-language/trial.json", user="root").stdout
        == trial_before
    )
    # Re-verifying an old result must not advance or reopen anything.
    state = command(container, "cat", "/opt/programming-language/state.json", user="root").stdout
    assert command(container, *admin, "settle", "1", user="root").returncode == 0
    assert (
        command(container, "cat", "/opt/programming-language/state.json", user="root").stdout
        == state
    )


def test_cancelled_agent_stops_container_children_before_next_step(container, tmp_path):
    """Cancelling the host Docker-exec await must also stop its container processes."""
    assert command(container, "mkdir", "-p", "/opt/language-pi", user="root").returncode == 0
    subprocess.run(
        ["docker", "cp", str(STOP_SCRIPT), f"{container}:{REMOTE_STOP_SCRIPT}"],
        check=True,
        capture_output=True,
        timeout=30,
    )
    fixture = tmp_path / "expired.py"
    fixture.write_text(
        "import ctypes, json, os, subprocess, time\n"
        "from pathlib import Path\n"
        "ctypes.CDLL(None).prctl(15, b'pi', 0, 0, 0)\n"
        "child = subprocess.Popen(['sleep', '600'])\n"
        "Path('/tmp/expired-pids.json').write_text(json.dumps([os.getpid(), child.pid]))\n"
        "time.sleep(600)\n"
    )
    subprocess.run(
        ["docker", "cp", str(fixture), f"{container}:/tmp/expired.py"],
        capture_output=True,
        check=True,
        timeout=30,
    )
    # An unrelated process in the same container must survive cleanup.
    subprocess.run(
        [
            "docker",
            "exec",
            "-d",
            "--user",
            "agent",
            container,
            "python3",
            "-c",
            "import os,time; from pathlib import Path; "
            "Path('/tmp/unrelated-pid').write_text(str(os.getpid())); time.sleep(600)",
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )
    agent = SequentialPi(logs_dir=tmp_path / "logs")

    async def exercise():
        ready = asyncio.Event()
        client = None

        async def stalled_run(_self, instruction, environment, context):
            nonlocal client
            client = await asyncio.create_subprocess_exec(
                "docker",
                "exec",
                "--user",
                "agent",
                container,
                "python3",
                "/tmp/expired.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            while True:
                probe = await asyncio.to_thread(
                    command, container, "test", "-f", "/tmp/expired-pids.json"
                )
                if probe.returncode == 0:
                    ready.set()
                    break
                await asyncio.sleep(0.05)
            await client.communicate()

        async def root_exec(environment, command, **kwargs):
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "exec",
                "--user",
                "root",
                container,
                "bash",
                "-c",
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            assert proc.returncode == 0, stderr.decode()
            return SimpleNamespace(stdout=stdout.decode())

        with patch.object(Pi, "run", stalled_run), patch.object(agent, "exec_as_root", root_exec):
            running = asyncio.create_task(agent.run("fixture", object(), AgentContext()))
            await asyncio.wait_for(ready.wait(), timeout=10)
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(running, timeout=0.1)
            await asyncio.wait_for(client.wait(), timeout=5)

    asyncio.run(exercise())
    verify = """
import json
from pathlib import Path
def alive(pid):
    p = Path(f'/proc/{pid}/stat')
    return p.exists() and p.read_text().split(')')[1].split()[0] != 'Z'
expired = json.loads(Path('/tmp/expired-pids.json').read_text())
assert not any(alive(pid) for pid in expired), expired
assert alive(int(Path('/tmp/unrelated-pid').read_text()))
print(json.dumps(expired))
"""
    verified = command(container, "python3", "-c", verify)
    assert verified.returncode == 0, verified.stderr
    killed = json.loads((agent.logs_dir / "timeout-cleanup.json").read_text())["killed"]
    assert set(json.loads(verified.stdout)).issubset({row["pid"] for row in killed})
    assert not agent._provider_failures


@pytest.mark.parametrize(
    "seed,visibility", [(1, "hidden"), (2, "partial")], ids=["hidden-seed1", "partial-seed2"]
)
def test_harbor_oracle_completes_twenty_steps(docker_available, tmp_path, seed, visibility):
    task = TASK
    if (seed, visibility) != (1, "hidden"):
        task = tmp_path / "generated-task"
        generated = subprocess.run(
            [
                sys.executable,
                str(TASK / "generate_steps.py"),
                "--seed",
                str(seed),
                "--visibility",
                visibility,
                "--output",
                str(task),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert generated.returncode == 0, generated.stdout + generated.stderr
    harbor = str(Path(sys.executable).parent / "harbor")
    result = subprocess.run(
        [
            harbor,
            "run",
            "-p",
            str(task),
            "-a",
            "oracle",
            "--jobs-dir",
            str(tmp_path),
            "--job-name",
            "language-oracle",
            "-n",
            "1",
            "--max-retries",
            "0",
        ],
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    paths = list((tmp_path / "language-oracle").glob("*/result.json"))
    assert len(paths) == 1
    trial = json.loads(paths[0].read_text())
    assert not trial.get("exception_info")
    assert len(trial["step_results"]) == 20
    for step in trial["step_results"]:
        assert not step.get("exception_info"), step.get("exception_info")
        assert step["verifier_result"]["rewards"]["reward"] == 1
        assert step["verifier_result"]["rewards"]["submissions"] == 1
