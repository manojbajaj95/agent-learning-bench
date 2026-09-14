"""Matched seed orchestration and rolling averages without paid API calls."""

import json
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest

import run_matrix
from analyze import METRICS
from memory_report import rolling, summarize_pairs, write_comparison
from run_matrix import PI_VERSION, PLAY_THINKING, read_pair


def make_pair(directory, seed, gap=0.1):
    jobs, prefix = directory / "jobs", f"pair-{seed}"
    settings = {
        "model": "google/test",
        "pi_version": PI_VERSION,
        "thinking": PLAY_THINKING,
        "instance_sha256": f"seed-{seed}",
    }
    for condition, reward in (("no-memory", 0.4), ("learning", 0.4 + gap)):
        rewards = dict.fromkeys(METRICS, 0)
        rewards.update(reward=reward, regret=0.8 - reward, won=int(reward >= 0.5), completed=1)
        data = {
            "task_name": "affinity-arena",
            "trial_name": condition,
            "seed": seed,
            **settings,
            "step_results": [
                {"step_name": f"battle-{i:02d}", "verifier_result": {"rewards": rewards}}
                for i in range(1, 21)
            ],
        }
        path = (
            jobs
            / f"{prefix}-{condition}"
            / ("no-memory.json" if condition == "no-memory" else "trial/result.json")
        )
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(data))
    (directory / "matrix.json").write_text(
        json.dumps(
            {
                "mode": "memory-comparison",
                "status": "complete",
                "prefix": prefix,
                "jobs_dir": str(jobs),
                **settings,
            }
        )
    )
    return read_pair(directory, model="google/test")


def test_rolling_windows_and_seed_weighting(tmp_path):
    assert rolling(list(range(20))) == list(range(2, 18))
    with pytest.raises(ValueError):
        rolling([1, 2, 3, 4])
    pairs = [
        make_pair(tmp_path / str(seed), seed, gap) for seed, gap in enumerate((0.1, 0.2, -0.1), 1)
    ]
    summary = summarize_pairs(pairs)
    assert summary["mean_reward_gap"] == pytest.approx(0.2 / 3)
    assert summary["seed_gap_range"] == pytest.approx([-0.1, 0.2])
    assert summary["window_end_battles"] == list(range(5, 21))
    assert summary["rolling"][2]["gap"] == pytest.approx([-0.1] * 16)
    out = tmp_path / "report"
    assert write_comparison(pairs, out, [])
    text = (out / "comparison.md").read_text()
    assert text.index("Mean paired reward gap") < text.index("Wins are a secondary")
    assert "Regret reduction |" not in text
    svg = ElementTree.fromstring((out / "rolling-reward.svg").read_text())
    lines = svg.findall(".//{http://www.w3.org/2000/svg}polyline")
    assert len(lines) == 12  # Two rewards + gap, three seeds + mean each.
    for line in lines:
        points = [tuple(map(float, p.split(","))) for p in line.attrib["points"].split()]
        assert len(points) == 16
        assert points[0][0] == 70 and points[-1][0] == 920
        assert all(115 <= y <= 655 for _, y in points)
    assert not write_comparison(pairs, out, ["Seed 4 is incomplete"])
    assert "Mean paired reward gap" not in (out / "comparison.md").read_text()
    assert "polyline" not in (out / "rolling-reward.svg").read_text()
    assert not json.loads((out / "reward-summary.json").read_text())["complete"]


def test_reuse_and_oracle_validation(tmp_path):
    pair = make_pair(tmp_path, 1)
    for kwargs in (
        {"model": "google/other"},
        {"model": "google/test", "seed": 2},
        {"model": "google/test", "digest": "changed"},
    ):
        with pytest.raises(ValueError):
            read_pair(tmp_path, **kwargs)
    pair["trials"][1]["steps"][0]["rewards"]["regret"] += 0.1
    assert not write_comparison([pair], tmp_path / "bad", [])
    assert "same oracle" in (tmp_path / "bad/comparison.md").read_text()


@pytest.mark.parametrize("failure", [None, "process", "digest"])
def test_three_seed_sweep_reuse_and_report_only(tmp_path, monkeypatch, failure):
    reused = tmp_path / "existing"
    make_pair(reused, 1)
    out = tmp_path / "sweep"
    calls = []

    def digest(task):
        return "wrong" if failure == "digest" else task.name

    def fake_run(command, **kwargs):
        calls.append(command)
        if "generate_steps.py" in command[1]:
            Path(command[command.index("--output") + 1]).mkdir(parents=True)
        else:
            if failure == "process":
                raise subprocess.CalledProcessError(1, command)
            directory = Path(command[command.index("--out-dir") + 1])
            seed = int(Path(command[command.index("--task") + 1]).name.split("-")[-1])
            assert seed != 1  # Reused seed must never make a paid call.
            make_pair(directory, seed, 0.1 * seed)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(run_matrix, "task_digest", digest)
    monkeypatch.setattr(run_matrix.subprocess, "run", fake_run)
    args = [
        "run_matrix.py",
        "--compare-memory",
        "--prefix",
        "sweep",
        "--out-dir",
        str(out),
        "--jobs-dir",
        str(tmp_path / "jobs"),
    ]
    run_args = [*args, "--model", "google/test", "--seeds", "1", "2", "3", "--reuse", str(reused)]
    monkeypatch.setattr(sys, "argv", [*run_args, "--dry-run"])
    run_matrix.main()
    assert not calls and not out.exists()
    monkeypatch.setattr(sys, "argv", run_args)
    if failure:
        with pytest.raises(SystemExit, match="Seed sweep stopped"):
            run_matrix.main()
    else:
        run_matrix.main()
    manifest = json.loads((out / "matrix.json").read_text())
    assert manifest["status"] == ("failed" if failure else "complete")
    assert manifest["pairs"][0]["reused"]
    assert len(calls) == ({None: 5, "process": 4, "digest": 1}[failure])
    before = (out / "comparison.md").read_text()
    monkeypatch.setattr(sys, "argv", [*args, "--report-only"])
    if failure:
        with pytest.raises(SystemExit, match="incomplete"):
            run_matrix.main()
        assert "Mean paired reward gap" not in before
    else:
        run_matrix.main()
        summary = json.loads((out / "reward-summary.json").read_text())
        assert summary["n_seeds"] == 3
        assert summary["mean_reward_gap"] == pytest.approx(0.2)
    assert (out / "comparison.md").read_text() == before
    assert len(calls) == ({None: 5, "process": 4, "digest": 1}[failure])


def test_duplicate_seeds_rejected_before_output(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_matrix.py",
            "--compare-memory",
            "--seeds",
            "1",
            "1",
            "2",
            "--model",
            "google/test",
            "--out-dir",
            str(tmp_path / "out"),
        ],
    )
    with pytest.raises(SystemExit):
        run_matrix.main()
    assert not (tmp_path / "out").exists()
