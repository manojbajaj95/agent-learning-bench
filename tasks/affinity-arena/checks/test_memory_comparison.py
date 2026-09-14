"""Keyless orchestration and reproducible comparison reports."""

import json
import subprocess
import sys

import pytest

import run_matrix
from analyze import METRICS
from run_matrix import PI_VERSION, PLAY_THINKING, TASK, memory_commands
from run_no_memory import command_for


def test_paired_commands_match_settings(tmp_path):
    baseline, learning = memory_commands("harbor", TASK, tmp_path, "pair", "google/test", True)
    assert baseline[0] == "no-memory" and learning[0] == "learning"
    baseline_cmd, learning_cmd = baseline[1], learning[1]
    assert (
        baseline_cmd[baseline_cmd.index("--task") + 1]
        == learning_cmd[learning_cmd.index("-p") + 1]
        == str(TASK)
    )
    assert (
        baseline_cmd[baseline_cmd.index("--model") + 1]
        == learning_cmd[learning_cmd.index("-m") + 1]
        == "google/test"
    )
    assert baseline_cmd[baseline_cmd.index("--job-name") + 1] == "pair-no-memory"
    assert learning_cmd[learning_cmd.index("--job-name") + 1] == "pair-learning"
    assert "--resume-trajectory" not in baseline_cmd and "--resume-trajectory" in learning_cmd
    assert f"version={PI_VERSION}" in learning_cmd
    assert "model_api=openai-responses" in learning_cmd
    isolated = command_for("harbor", tmp_path, 1, "google/test", False)
    assert f"thinking={PLAY_THINKING}" in learning_cmd
    assert f"thinking={PLAY_THINKING}" in isolated


@pytest.mark.parametrize(
    "failure", [None, "incomplete", "process", "changed-task", "changed-after-learning"]
)
def test_run_and_report_only(tmp_path, monkeypatch, failure):
    calls = []
    jobs, output = tmp_path / "jobs", tmp_path / "reports"
    prefix = "pair"

    def fake_run(command, **kwargs):
        calls.append(command)
        if failure == "process":
            raise subprocess.CalledProcessError(1, command)
        condition = "no-memory" if len(calls) == 1 else "learning"
        assert kwargs["env"]["PYTHONPATH"].startswith(str(TASK))
        reward = 0.6 if condition == "no-memory" else 0.7
        rewards = dict.fromkeys(METRICS, 0)
        rewards.update(reward=reward, regret=0.8 - reward, won=1, completed=1)
        data = {
            "task_name": "agent-learning-bench/affinity-arena",
            "trial_name": condition,
            "step_results": [
                {"step_name": f"battle-{i:02d}", "verifier_result": {"rewards": dict(rewards)}}
                for i in range(1, 21)
            ],
        }
        if failure == "incomplete":
            data["step_results"][0]["verifier_result"]["rewards"]["completed"] = 0
        job = jobs / f"{prefix}-{condition}"
        path = job / ("no-memory.json" if condition == "no-memory" else "trial/result.json")
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(data))
        if failure == "changed-task" or (
            failure == "changed-after-learning" and condition == "learning"
        ):
            monkeypatch.setattr(run_matrix, "task_digest", lambda _: "changed")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(run_matrix.subprocess, "run", fake_run)
    monkeypatch.setattr(run_matrix, "task_digest", lambda _: "original")
    args = [
        "run_matrix.py",
        "--compare-memory",
        "--prefix",
        prefix,
        "--jobs-dir",
        str(jobs),
        "--out-dir",
        str(output),
    ]
    monkeypatch.setattr(sys, "argv", [*args, "--model", "google/test"])
    if failure:
        with pytest.raises(SystemExit, match="Comparison stopped"):
            run_matrix.main()
        assert len(calls) == (2 if failure == "changed-after-learning" else 1)
    else:
        run_matrix.main()
        assert len(calls) == 2
    manifest = json.loads((output / "matrix.json").read_text())
    assert manifest["status"] == ("failed" if failure else "complete")
    assert manifest["thinking"] == PLAY_THINKING
    before = (output / "comparison.md").read_text()
    assert ("## Memory advantage" in before) == (failure is None)
    if not failure:
        assert "| All | 0.600 | 0.700 | +0.100 |" in before
        assert "Regret reduction |" not in before
        assert "not independent evidence" in before
    monkeypatch.setattr(sys, "argv", [*args, "--report-only"])
    if failure:
        with pytest.raises(SystemExit, match="incomplete or failed"):
            run_matrix.main()
    else:
        run_matrix.main()
    assert (output / "comparison.md").read_text() == before
    assert len(calls) == (1 if failure and failure != "changed-after-learning" else 2)


def test_paired_dry_run_and_existing_output(tmp_path, monkeypatch, capsys):
    args = [
        "run_matrix.py",
        "--compare-memory",
        "--model",
        "google/test",
        "--jobs-dir",
        str(tmp_path / "jobs"),
        "--out-dir",
        str(tmp_path / "reports"),
    ]
    monkeypatch.setattr(sys, "argv", [*args, "--dry-run"])
    run_matrix.main()
    assert len(capsys.readouterr().out.splitlines()) == 2
    assert not list(tmp_path.iterdir())
    (tmp_path / "reports").mkdir()
    sentinel = tmp_path / "reports/keep.txt"
    sentinel.write_text("previous report")
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit):
        run_matrix.main()
    assert sentinel.read_text() == "previous report"


def test_unreadable_results_produce_incomplete_report(tmp_path):
    job = tmp_path / "jobs/pair-no-memory"
    job.mkdir(parents=True)
    (job / "no-memory.json").write_text("{unfinished")
    output = tmp_path / "reports"
    assert not run_matrix.memory_report(tmp_path / "jobs", "pair", output)
    text = (output / "comparison.md").read_text()
    assert "cannot read results" in text
    assert "## Memory advantage" not in text
