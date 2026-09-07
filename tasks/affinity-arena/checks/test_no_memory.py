"""Matched one-battle tasks, reporting, and real sandbox isolation (keyless)."""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from arena.runtime import Paths, Runtime
from harbor.models.task.task import Task

import run_no_memory
from analyze import analyze_job
from generate_steps import write_generated
from run_no_memory import collect_result, command_for, isolated_files, save_report

TASK = Path(__file__).resolve().parents[1]


def test_isolated_tasks_keep_every_matchup_and_start_clean(tmp_path, trial):
    for index in range(1, 21):
        files = isolated_files(TASK, index)
        data = json.loads(files["environment/trial.json"])
        assert data.pop("isolated_battle") == index
        assert data == trial
        root = tmp_path / str(index)
        write_generated(root, files, False)
        task = Task(root)
        assert [step.name for step in task.config.steps] == [f"battle-{index:02d}"]
        assert task.config.agent.user == "agent"
        assert (
            files[f"steps/battle-{index:02d}/instruction.md"]
            == (TASK / "instruction.md").read_text()
        )
        paths = Paths(root / "environment", root / "app", root / "verifier")
        (paths.public / "battles").mkdir(parents=True)
        runtime = Runtime(paths)
        assert f"battle {index} of 20" in runtime.start(index)
        assert runtime.load()["cells"] == []
        assert runtime.load()["completed"] == []
        assert list((paths.public / "battles").iterdir()) == [
            paths.public / "battles" / f"battle-{index:02d}.jsonl"
        ]
        assert runtime.settle(index)["belief_acc"] == 0
        with pytest.raises(ValueError, match="one playable battle"):
            runtime.start(index % 20 + 1)


def test_commands_never_resume_or_mount_previous_runs(tmp_path):
    commands = [
        command_for("harbor", tmp_path, i, "google/test-model", False) for i in range(1, 21)
    ]
    assert len({c[c.index("-p") + 1] for c in commands}) == 20
    assert len({c[c.index("--job-name") + 1] for c in commands}) == 20
    for command in commands:
        assert "--resume-trajectory" not in command
        assert "--load-trajectory" not in command
        assert command[command.index("--max-retries") + 1] == "0"
        assert command[command.index("-a") + 1] == "affinity_agent:PiTrajectoryAgent"


def test_aggregate_preserves_metrics_and_flags_incomplete_attempts(tmp_path, trial):
    aggregate = {
        "task_name": "agent-learning-bench/affinity-arena",
        "trial_name": "no-memory",
        "step_results": [],
        "source_results": [],
    }
    for index, battle in enumerate(trial["battles"], 1):
        name = f"battle-{index:02d}"
        rewards = {
            "reward": battle["oracle_value"][0] / 4200,
            "won": 1,
            "completed": 1,
            "opt_rate": 1,
            "draft_ok": 1,
            "regret": 0,
            "cells_seen": 0.2,
            "belief_acc": 0,
            "ticks": -battle["oracle_value"][1],
            "oracle_ticks": -battle["oracle_value"][1],
            "env_actions": 8,
        }
        result = {"step_results": [{"step_name": name, "verifier_result": {"rewards": rewards}}]}
        path = tmp_path / "runs" / name / "trial" / "result.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(result))
        assert collect_result(tmp_path, index, aggregate)
    save_report(tmp_path, aggregate)
    summary = analyze_job(tmp_path)[0]
    assert not summary["issues"] and len(summary["steps"]) == 20
    assert summary["mean_reward"] == pytest.approx(0.7485)
    assert summary["phases"]["holdout"]["won"] == 1
    aggregate["step_results"][16]["verifier_result"]["rewards"]["completed"] = 0
    save_report(tmp_path, aggregate)
    assert "one or more incomplete attempts" in analyze_job(tmp_path)[0]["issues"]


def test_dry_run_does_not_create_files_or_call_api(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(TASK / "run_no_memory.py"),
            "--job-name",
            "dry",
            "--jobs-dir",
            str(tmp_path),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert len(result.stdout.splitlines()) == 20
    assert not list(tmp_path.iterdir())


def test_runner_stops_on_incomplete_battle_and_preserves_results(tmp_path, monkeypatch):
    calls = []

    def fake_harbor(command, **kwargs):
        calls.append(command)
        index = len(calls)
        rewards = dict.fromkeys(run_no_memory.METRICS, 0)
        rewards["completed"] = int(index < 3)
        path = tmp_path / "control/runs" / f"battle-{index:02d}" / "trial/result.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "step_results": [
                        {
                            "step_name": f"battle-{index:02d}",
                            "verifier_result": {"rewards": rewards},
                        }
                    ]
                }
            )
        )
        assert "--resume-trajectory" not in command
        assert kwargs["env"]["PYTHONPATH"].startswith(str(TASK))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(run_no_memory.subprocess, "run", fake_harbor)
    monkeypatch.setattr(
        sys, "argv", ["run_no_memory.py", "--job-name", "control", "--jobs-dir", str(tmp_path)]
    )
    with pytest.raises(SystemExit, match="Battle 3 failed or was incomplete"):
        run_no_memory.main()
    assert len(calls) == 3
    root = tmp_path / "control"
    result = json.loads((root / "no-memory.json").read_text())
    assert len(result["source_results"]) == len(result["step_results"]) == 3
    assert "one or more incomplete attempts" in analyze_job(root)[0]["issues"]
    with pytest.raises(SystemExit):
        run_no_memory.main()
    assert len(calls) == 3  # Existing output was not overwritten or retried.


@pytest.mark.docker
def test_fresh_harbor_sandboxes_and_oracle_parity(tmp_path, trial):
    env = dict(os.environ)
    for index in (2, 17):
        files = isolated_files(TASK, index)
        # Run these assertions as the task's real agent user before oracle play.
        probe = f"""
import json, os
from pathlib import Path
assert os.geteuid() == 2000
assert 'battle {index} of 20' in Path('/app/view.txt').read_text()
assert Path('/app/notes.md').read_text() == ''
assert json.loads(Path('/app/affinity-chart.json').read_text()) == {{}}
assert sorted(p.name for p in Path('/app/battles').iterdir()) == ['battle-{index:02d}.jsonl']
for directory in ('/app/workspace', '/app/sessions', '/logs/agent/pi/sessions'):
    assert not list(Path(directory).glob('*')), directory
assert not os.access('/opt/affinity-arena/trial.json', os.R_OK)
for name in ('/tmp/memory-marker', '/home/agent/memory-marker', '/app/workspace/memory-marker'):
    assert not Path(name).exists(), name
    Path(name).write_text('previous battle memory')
Path('/app/notes.md').write_text('previous battle notes')
"""
        script = f"steps/battle-{index:02d}/solution/solve.sh"
        files[script] = files[script].replace(
            "set -euo pipefail\n", "set -euo pipefail\npython3 -c " + shlex.quote(probe) + "\n"
        )
        write_generated(tmp_path / "tasks" / f"battle-{index:02d}", files, False)
        command = command_for(
            str(Path(sys.executable).parent / "harbor"), tmp_path, index, "", True
        )
        process = subprocess.run(command, env=env, capture_output=True, text=True, timeout=300)
        assert process.returncode == 0, process.stdout + process.stderr
        aggregate = {"step_results": [], "source_results": []}
        assert collect_result(tmp_path, index, aggregate)
        rewards = aggregate["step_results"][0]["verifier_result"]["rewards"]
        assert rewards["reward"] == trial["battles"][index - 1]["oracle_value"][0] / 4200
        assert rewards["won"] == rewards["draft_ok"] == rewards["opt_rate"] == 1
        assert rewards["regret"] == 0
