#!/usr/bin/env python3
"""Checks for the alb CLI: Harbor argv, smoke slicing, Typer extra args."""

from __future__ import annotations

import os
from pathlib import Path

from typer.testing import CliRunner

from alb.bench import (
    ROOT,
    default_job_name,
    harbor_example,
    harbor_run_cmd,
    needs_slice,
    script_has_flag,
    slice_task,
    system_names,
    system_spec,
)
from alb.cli import app
from alb.report import svg_lines, summarize_trial

runner = CliRunner()


def test_icl_cmd_resumes() -> None:
    cmd, _env = harbor_run_cmd(
        ROOT / "tasks" / "tally",
        "icl",
        model="openai/gpt-5.6-luna",
        job_name="tally-icl",
        jobs_dir=ROOT / "jobs",
        timeout=5.0,
        n_concurrent=1,
        upload=False,
        public=False,
        extra=[],
    )
    assert cmd[:6] == [
        "harbor",
        "run",
        "-p",
        str(ROOT / "tasks" / "tally"),
        "-a",
        "pi",
    ]
    assert "--resume-trajectory" in cmd
    assert "-m" in cmd
    assert "agents.pi_sessions:PiSessionsAgent" not in cmd


def test_sessions_cmd_sets_pythonpath() -> None:
    cmd, env = harbor_run_cmd(
        ROOT / "tasks" / "tally",
        "sessions",
        model="openai/gpt-5.6-luna",
        job_name="tally-sessions",
        jobs_dir=ROOT / "jobs",
        timeout=5.0,
        n_concurrent=1,
        upload=True,
        public=True,
        extra=["--force-build"],
    )
    assert "agents.pi_sessions:PiSessionsAgent" in cmd
    assert "--resume-trajectory" not in cmd
    assert "--upload" in cmd and "--public" in cmd
    assert "--force-build" in cmd
    assert env["PYTHONPATH"].split(os.pathsep)[0] == str(ROOT)


def test_oracle_skips_model() -> None:
    cmd, _env = harbor_run_cmd(
        ROOT / "tasks" / "tally",
        "oracle",
        model="openai/gpt-5.6-luna",
        job_name="tally-oracle",
        jobs_dir=ROOT / "jobs",
        timeout=5.0,
        n_concurrent=1,
        upload=False,
        public=False,
        extra=[],
    )
    assert "-m" not in cmd
    assert "oracle" in cmd


def test_slice_keeps_first_n(tmp_path: Path) -> None:
    src = tmp_path / "src"
    steps = src / "steps"
    steps.mkdir(parents=True)
    names = [f"turn-{i:02d}" for i in range(1, 13)]
    toml = 'schema_version = "1.4"\n\n'
    for name in names:
        toml += f'[[steps]]\nname = "{name}"\n\n'
        (steps / name).mkdir()
        (steps / name / "instruction.md").write_text(name)
    (src / "task.toml").write_text(toml)
    dest = tmp_path / "smoke"
    slice_task(src, dest, 10)
    kept = [p.name for p in sorted((dest / "steps").iterdir())]
    assert kept == names[:10]
    text = (dest / "task.toml").read_text()
    assert text.count("[[steps]]") == 10
    assert "turn-11" not in text


def test_generate_n_flag() -> None:
    db = ROOT / "tasks" / "database-analytics" / "generate_steps.py"
    poker = ROOT / "tasks" / "poker" / "generate_steps.py"
    assert script_has_flag(db, "--n")
    assert script_has_flag(db, "--all")
    assert not script_has_flag(poker, "--n")
    assert needs_slice(ROOT / "tasks" / "poker", 10)
    assert not needs_slice(ROOT / "tasks" / "database-analytics", 10)


def test_systems_toml_is_source() -> None:
    names = system_names()
    assert names == ["baseline", "icl", "sessions", "oracle"]
    icl = system_spec("icl")
    assert icl["agent"] == "pi"
    assert "--resume-trajectory" in icl["flags"]
    sessions = system_spec("sessions")
    assert sessions["pythonpath"] == str(ROOT)
    assert harbor_example("icl").startswith("harbor run")
    assert "--resume-trajectory" in harbor_example("icl")
    assert "PYTHONPATH=." in harbor_example("sessions")
    assert default_job_name("tally", "icl", None) == "tally-icl"
    assert default_job_name("tally", "icl", 10) == "tally-icl-n10"


def test_svg_and_extras() -> None:
    svg = svg_lines([("baseline", [0.0, 1.0, 0.5])], "Reward vs step")
    assert "<svg" in svg and "baseline" in svg
    summary = summarize_trial(
        {
            "trial_name": "t",
            "task_name": "database-analytics",
            "step_results": [
                {
                    "name": "q-1",
                    "verifier_result": {"rewards": {"reward": 1.0, "db_queries": 4}},
                    "agent_result": {"cost_usd": 0.1, "n_input_tokens": 10},
                }
            ],
        }
    )
    assert summary["steps"][0]["extras"]["db_queries"] == 4.0
    assert summary["extras"]["db_queries"] == 4.0


def test_dry_run_smoke_icl() -> None:
    result = runner.invoke(app, ["smoke", "tally", "--system", "icl", "--dry-run"])
    assert result.exit_code == 0
    assert "--resume-trajectory" in result.stdout


def test_extra_harbor_flags_after_dash() -> None:
    result = runner.invoke(
        app,
        ["run", "tally", "--system", "icl", "--dry-run", "--", "--force-build"],
    )
    assert result.exit_code == 0
    assert "--force-build" in result.stdout


def _tmp() -> Path:
    import tempfile

    return Path(tempfile.mkdtemp())


if __name__ == "__main__":
    test_icl_cmd_resumes()
    test_sessions_cmd_sets_pythonpath()
    test_oracle_skips_model()
    test_slice_keeps_first_n(_tmp())
    test_generate_n_flag()
    test_systems_toml_is_source()
    test_svg_and_extras()
    test_dry_run_smoke_icl()
    test_extra_harbor_flags_after_dash()
    print("ok")
