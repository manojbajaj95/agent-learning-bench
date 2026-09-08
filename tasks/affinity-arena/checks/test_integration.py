import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from harbor.agents.installed.pi import Pi
from harbor.agents.model_connection import ModelConnectionSpec, resolve_model_connection
from harbor.models.task.task import Task
from tools.report_runs import summarize_trial as summarize_harbor_trial

from affinity_agent import PiSessionsAgent
from analyze import analyze_job, report, summarize_trial
from generate_steps import generated_files, write_generated
from run_matrix import commands

TASK = Path(__file__).resolve().parents[1]


def test_generator_and_harbor_schema(tmp_path):
    assert write_generated(TASK, generated_files(1), check=True) == []
    task = Task(TASK)
    assert task.config.agent.user == "agent" and task.config.verifier.user == "root"
    assert len(task.config.steps) == 20
    assert len({task.step_instruction(s.name) for s in task.config.steps}) == 1
    assert all(s.min_reward is None for s in task.config.steps)
    # Explicit output produces a self-contained task and leaves the default alone.
    generated = generated_files(2)
    assert write_generated(tmp_path, generated, check=True)
    write_generated(tmp_path, generated, check=False)
    assert write_generated(tmp_path, generated, check=True) == []
    assert json.loads((TASK / "environment/trial.json").read_text())["seed"] == 1


def test_reports_keep_metrics_and_mark_wins(tmp_path):
    trial_dir = tmp_path / "trial"
    trial_dir.mkdir()
    metrics = {
        "reward": 0.75,
        "won": 1,
        "opt_rate": 1,
        "draft_ok": 1,
        "regret": 0,
        "cells_seen": 0.5,
        "belief_acc": 0.5,
        "ticks": 6,
        "oracle_ticks": 6,
        "env_actions": 7,
        "completed": 1,
    }
    data = {
        "trial_name": "trial",
        "task_name": "agent-learning-bench/affinity-arena",
        "step_results": [
            {"step_name": f"battle-{i:02d}", "verifier_result": {"rewards": metrics}}
            for i in range(1, 21)
        ],
    }
    (trial_dir / "result.json").write_text(json.dumps(data))
    summary = summarize_trial(data)
    assert summary["mean_reward"] == 0.75
    assert summary["steps"][0]["hit"] is True
    # Arena's win flag must not redefine success for existing benchmark tasks.
    shared = summarize_harbor_trial(data)
    assert shared["steps"][0]["hit"] is False
    assert "rewards" not in shared["steps"][0]
    rows = analyze_job(tmp_path)
    assert not rows[0]["issues"]
    assert rows[0]["phases"]["holdout"]["reward"] == 0.75
    assert "battle-20" in report(rows)
    data["step_results"].pop()
    (trial_dir / "result.json").write_text(json.dumps(data))
    assert analyze_job(tmp_path)[0]["issues"]
    # Existing binary-reward reports keep their behavior.
    assert (
        summarize_trial({"step_results": [{"verifier_result": {"rewards": {"reward": 1}}}]})[
            "steps"
        ][0]["hit"]
        is True
    )


def test_sessions_inherit_endpoint_and_resume(tmp_path):
    agent = PiSessionsAgent(
        logs_dir=tmp_path,
        model_name="openai/test-model",
        thinking="low",
        model_api="openai-responses",
    )
    assert PiSessionsAgent.run is Pi.run
    flags = shlex.split(agent.build_cli_flags())
    assert flags == ["--thinking", "low", "-e", "/opt/pi-sessions/save-sessions.ts"]
    values = {"OPENAI_API_KEY": "test-placeholder", "OPENAI_BASE_URL": "https://example.invalid/v1"}

    def lookup(*names):
        return next(((name, values[name]) for name in names if name in values), None)

    access = resolve_model_connection(
        "openai/test-model", ModelConnectionSpec(passthrough=True), lookup
    )
    assert access.env["OPENAI_BASE_URL"] == values["OPENAI_BASE_URL"]
    config = agent._build_custom_models_json(access, "test-model")
    provider = next(iter(config["providers"].values()))
    assert provider["api"] == "openai-responses"
    assert provider["apiKey"] == "$OPENAI_API_KEY"
    assert "test-placeholder" not in json.dumps(config)


def test_matrix_commands_are_matched_and_keyless(tmp_path):
    runs = commands("harbor", TASK, tmp_path, "arena-test", "openai/model", "0.85.1", True)
    assert len(runs) == 4
    for condition, command in runs:
        assert command[command.index("-p") + 1] == str(TASK)
        assert command[command.index("--max-retries") + 1] == "0"
        assert ("--resume-trajectory" in command) == (condition == "icl")
        if condition != "oracle":
            assert "model_api=openai-responses" in command
            assert command[command.index("-m") + 1] == "openai/model"
            assert command[command.index("-a") + 1].startswith("affinity_agent:")


def test_task_local_agents_load_without_modifying_shared_agents(tmp_path):
    script = """
from pathlib import Path
from harbor.agents.factory import AgentFactory
from harbor.agents.installed.pi import Pi
from agents.pi_sessions import PiSessionsAgent as SharedSessions

before = (Pi.run, Pi.populate_context_post_run, SharedSessions.run,
          SharedSessions.populate_context_post_run)
for name in ('PiTrajectoryAgent', 'PiSessionsAgent'):
    agent = AgentFactory.create_agent_from_import_path(
        'affinity_agent:' + name, logs_dir=Path('.'),
        model_name='google/test-model', version='0.85.1')
    assert type(agent).__module__.startswith('affinity_agent.')
    assert type(agent).run is Pi.run
assert before == (Pi.run, Pi.populate_context_post_run, SharedSessions.run,
                  SharedSessions.populate_context_post_run)
from affinity_agent.sessions import _EXTENSION_HOST_PATH
assert _EXTENSION_HOST_PATH.is_file()
assert 'affinity-arena' in _EXTENSION_HOST_PATH.parts
"""
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(TASK), str(TASK.parents[1]))))
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_human_play_oracle_script():
    commands = (TASK / "steps/battle-01/solution/solve.sh").read_text().splitlines()[2:]
    result = subprocess.run(
        [sys.executable, str(TASK / "play.py"), "--seed", "1", "--reveal-after"],
        input="\n".join(commands) + "\n",
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "Battle over: win." in result.stdout and "Reward:" in result.stdout
    assert result.stdout.index("Attack rows, defender columns") > result.stdout.index(
        "Battle over: win."
    )
