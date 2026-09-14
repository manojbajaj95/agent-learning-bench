"""Real Linux user/permission boundaries; run explicitly with -m docker."""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

TASK = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.docker


@pytest.fixture
def container():
    build = subprocess.run(
        ["docker", "build", "-t", "affinity-arena:checks", str(TASK / "environment")],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    proc = subprocess.run(
        ["docker", "run", "-d", "--rm", "affinity-arena:checks", "sleep", "infinity"],
        capture_output=True,
        text=True,
        check=True,
    )
    identity = proc.stdout.strip()
    try:
        yield identity
    finally:
        subprocess.run(["docker", "stop", identity], capture_output=True, check=True)


def execute(container, *command, user="agent"):
    return subprocess.run(
        ["docker", "exec", "--user", user, container, *command], capture_output=True, text=True
    )


def test_host_log_collection_preserves_resume_access(container):
    # Reproduce Harbor 0.22's per-step prepare_logs_for_host(): ownership is
    # transferred to the host UID before the root verifier runs.
    setup = execute(
        container,
        "python3",
        "-c",
        "from pathlib import Path; import os; "
        "p=Path('/logs/agent/pi/sessions'); p.mkdir(parents=True, exist_ok=True); "
        "(p/'session.jsonl').write_text('first battle\\n'); "
        "Path('/logs/agent/pi.txt').write_text('first log\\n'); "
        "os.chown('/logs/agent', 1000, 1000); "
        "[(os.chown(q, 1000, 1000), q.chmod(0o755 if q.is_dir() else 0o600)) "
        "for q in Path('/logs/agent').rglob('*')]; "
        "(p/'private-link').symlink_to('/opt/affinity-arena/trial.json'); "
        "(p/'private-dir').symlink_to('/opt/affinity-arena'); "
        "os.link('/app/notes.md', p/'hard-link'); "
        "os.mkfifo(p/'fifo')",
        user="root",
    )
    assert setup.returncode == 0, setup.stderr
    append = [
        "python3",
        "-c",
        "from pathlib import Path; "
        "p=Path('/logs/agent/pi/sessions'); "
        "s=p/'session.jsonl'; "
        "assert s.read_text() == 'first battle\\n'; "
        "s.open('a').write('next battle\\n'); "
        "Path('/logs/agent/pi.txt').open('a').write('next log\\n'); "
        "(p/'next.jsonl').write_text('new session\\n')",
    ]
    assert execute(container, *append).returncode != 0
    settle = execute(
        container,
        "python3",
        "-I",
        "/opt/affinity-arena/admin.py",
        "settle",
        "1",
        user="root",
    )
    assert settle.returncode == 0, settle.stderr
    result = execute(container, *append)
    assert result.returncode == 0, result.stderr
    assert execute(container, "cat", "/opt/affinity-arena/trial.json").returncode != 0
    assert execute(container, "cat", "/logs/verifier/reward.json").returncode != 0
    inspect = execute(
        container,
        "python3",
        "-c",
        "from pathlib import Path; "
        "s=Path('/logs/agent/pi/sessions/session.jsonl').stat(); "
        "assert (s.st_uid, s.st_gid, s.st_mode & 0o777) == (1000, 2000, 0o660); "
        "assert Path('/opt/affinity-arena').stat().st_mode & 0o777 == 0o700; "
        "assert Path('/opt/affinity-arena/trial.json').stat().st_gid == 0; "
        "assert Path('/app/notes.md').stat().st_mode & 0o777 == 0o644; "
        "assert Path('/logs/verifier').stat().st_mode & 0o777 == 0o700",
        user="root",
    )
    assert inspect.returncode == 0, inspect.stderr


def test_security_and_oracle_game(container):
    admin = ["/usr/bin/python3", "-I", "/opt/affinity-arena/admin.py"]
    start = execute(container, *admin, "start", "1", user="root")
    assert start.returncode == 0, start.stderr
    status = execute(container, "affinity-arena", "status")
    assert status.returncode == 0 and status.stdout == start.stdout
    forbidden = [
        ["cat", "/opt/affinity-arena/trial.json"],
        ["cat", "/opt/affinity-arena/state.json"],
        ["ls", "/opt/affinity-arena"],
        ["affinity-arena", "start", "1"],
        ["affinity-arena", "settle"],
        ["affinity-arena", "play"],
        [*admin, "start", "1"],
        ["sudo", "-n", "/usr/bin/python3", "-I", "/opt/affinity-arena/admin.py", "settle"],
        ["sudo", "-n", "/bin/sh"],
        [
            "sudo",
            "-n",
            "PYTHONPATH=/app/workspace",
            "/usr/local/libexec/affinity-arena-public",
            "status",
        ],
        ["rm", "/app/view.txt"],
        ["mv", "/app/battles", "/app/workspace/battles"],
        ["ln", "-s", "/opt/affinity-arena/trial.json", "/app/battles/battle-01.jsonl"],
        ["chmod", "777", "/opt/affinity-arena"],
    ]
    for command in forbidden:
        result = execute(container, *command)
        assert result.returncode != 0, command
        assert '"chart"' not in result.stdout
    script = (TASK / "steps/battle-01/solution/solve.sh").read_text()
    commands = [line.split() for line in script.splitlines() if line.startswith("affinity-arena")]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: execute(container, *commands[0]), range(4)))
    assert sum(r.returncode == 0 for r in results) == 1
    for command in commands[1:]:
        result = execute(container, *command)
        assert result.returncode == 0, result.stderr
    assert execute(container, *admin, "settle", "1", user="root").returncode == 0
    assert execute(container, "cat", "/logs/verifier/reward.json").returncode != 0
    assert execute(container, "ls", "/logs/verifier").returncode != 0
    assert execute(container, "affinity-arena", "attack", "Spore").returncode != 0
    metrics = json.loads(
        execute(container, "cat", "/logs/verifier/reward.json", user="root").stdout
    )
    assert metrics["won"] == metrics["opt_rate"] == metrics["draft_ok"] == 1
    assert metrics["regret"] == 0
    assert execute(container, *admin, "settle", "1", user="root").returncode == 0
    again = json.loads(execute(container, "cat", "/logs/verifier/reward.json", user="root").stdout)
    assert again == metrics
    trace = execute(container, "cat", "/app/battles/battle-01.jsonl")
    assert trace.returncode == 0
    assert '"chart"' not in trace.stdout and "oracle_value" not in trace.stdout
    assert execute(container, *admin, "start", "2", user="root").returncode == 0
    assert execute(container, "cat", "/logs/verifier/reward.json").returncode != 0


def test_harbor_resumes_logs_for_all_twenty_steps(tmp_path):
    # Exercise the real mounted-log ownership transfer, not just docker exec.
    # The probe intentionally leaves battles untouched: this tests resumption,
    # not gameplay, and does not install Pi or make model API calls.
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(TASK / "checks"), str(TASK)]) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    job = tmp_path / "jobs" / "resume-check"
    result = subprocess.run(
        [
            str(Path(sys.executable).parent / "harbor"),
            "run",
            "-p",
            str(TASK),
            "-a",
            "resume_probe:ResumeProbeAgent",
            "--resume-trajectory",
            "--jobs-dir",
            str(job.parent),
            "--job-name",
            job.name,
            "-n",
            "1",
            "--max-retries",
            "0",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    paths = list(job.glob("*/result.json"))
    assert len(paths) == 1
    trial = json.loads(paths[0].read_text())
    assert not trial["exception_info"]
    assert len(trial["step_results"]) == 20
    for index, step in enumerate(trial["step_results"], 1):
        assert not step["exception_info"], step["exception_info"]
        session = (
            paths[0].parent / "steps" / step["step_name"] / "agent/pi/sessions/resume-probe.jsonl"
        )
        assert session.read_text().splitlines() == [str(i) for i in range(1, index + 1)]
