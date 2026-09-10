"""Keyless regression checks for Pi log export and native execution inheritance."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from harbor.agents.installed.pi import Pi
from harbor.models.agent.context import AgentContext
from harbor.models.trajectories.trajectory import Trajectory

from affinity_agent import PiSessionsAgent, PiTrajectoryAgent
from affinity_agent.convert import convert_events, export_trajectory


def message(role, content, **kwargs):
    return {
        "type": "message_end",
        "message": {
            "role": role,
            "content": content,
            "timestamp": 1700000000000,
            **kwargs,
        },
    }


@pytest.fixture
def log(tmp_path):
    assistant = message(
        "assistant",
        [
            {"type": "thinking", "thinking": "Inspect the current battle."},
            {"type": "text", "text": "Checking status."},
            {
                "type": "toolCall",
                "id": "call1",
                "name": "bash",
                "arguments": {"command": "affinity-arena status"},
            },
        ],
        model="test-model",
        stopReason="toolUse",
        usage={
            "input": 10,
            "output": 5,
            "cacheRead": 20,
            "cacheWrite": 3,
            "cost": {"total": 0.01},
        },
    )
    events = [
        {"type": "session", "version": 3, "id": "session1"},
        message("user", [{"type": "text", "text": "Play battle 2."}]),
        {**assistant, "type": "message_start"},
        assistant,
        {"type": "tool_execution_end", "toolCallId": "call1", "result": {}},
        message(
            "toolResult",
            [{"type": "text", "text": "HP 100/100"}],
            toolCallId="call1",
            isError=False,
        ),
        message(
            "assistant", [], model="test-model", stopReason="error", errorMessage="503 UNAVAILABLE"
        ),
        {"type": "agent_end", "messages": [assistant["message"]]},
    ]
    source = tmp_path / "pi.txt"
    source.write_text("startup diagnostic\n" + "\n".join(map(json.dumps, events)) + "\n")
    return source


def test_conversion_preserves_calls_errors_and_metrics_without_duplicates(log):
    result = convert_events(log, version="0.85.1")
    assert result.session_id == "session1"
    assert result.agent.version == "0.85.1"  # Not native session schema version 3.
    assert len(result.steps) == 3
    step = result.steps[1]
    assert step.reasoning_content == "Inspect the current battle."
    assert step.tool_calls[0].arguments == {"command": "affinity-arena status"}
    assert step.observation.results[0].source_call_id == "call1"
    assert step.observation.results[0].content == "HP 100/100"
    assert step.metrics.prompt_tokens == 33
    assert result.final_metrics.total_cached_tokens == 20
    assert result.final_metrics.total_completion_tokens == 5
    assert result.final_metrics.total_cost_usd == 0.01
    assert "503 UNAVAILABLE" in result.steps[2].message
    assert result.extra["skipped_diagnostic_lines"] == 1
    assert result.extra["unresolved_tool_call_ids"] == []
    assert not result.extra["partial"]


@pytest.mark.parametrize("agent_class", [PiTrajectoryAgent, PiSessionsAgent])
def test_post_run_exports_and_keeps_native_execution(log, agent_class):
    agent = agent_class(logs_dir=log.parent, model_name="google/test-model", version="0.85.1")
    assert agent_class.run is Pi.run
    assert agent.SUPPORTS_RESUME and agent.SUPPORTS_ATIF
    context = AgentContext()
    agent.populate_context_post_run(context)
    result = Trajectory.model_validate_json(log.with_name("trajectory.json").read_text())
    assert context.n_output_tokens == result.final_metrics.total_completion_tokens
    assert context.cost_usd == result.final_metrics.total_cost_usd
    # A resumed invocation exports only the new battle, not a cumulative session.
    log.write_text(json.dumps(message("user", "Play battle 3.")) + "\n")
    agent.populate_context_post_run(AgentContext())
    result = Trajectory.model_validate_json(log.with_name("trajectory.json").read_text())
    assert len(result.steps) == 1 and result.steps[0].message == "Play battle 3."


def test_backfill_preserves_logs_and_existing_trajectory(log):
    original = log.read_bytes()
    target = export_trajectory(log)
    contents = target.read_bytes()
    assert export_trajectory(log).read_bytes() == contents
    assert log.read_bytes() == original
    target.write_text('{"extra": {"exporter": "someone-else"}}')
    with pytest.raises(ValueError, match="another exporter"):
        export_trajectory(log, replace=True)
    assert "someone-else" in target.read_text()


@pytest.mark.parametrize(
    "bad_line", ['{"type":', json.dumps(message("toolResult", "orphan", toolCallId="missing")), ""]
)
def test_invalid_or_empty_input_does_not_publish(tmp_path, bad_line):
    source = tmp_path / "pi.txt"
    source.write_text(bad_line)
    with pytest.raises(ValueError):
        export_trajectory(source)
    assert not source.with_name("trajectory.json").exists()


def test_pending_call_remains_visible_on_interruption(tmp_path):
    source = tmp_path / "pi.txt"
    source.write_text(
        json.dumps(
            message(
                "assistant",
                [
                    {"type": "toolCall", "id": "pending", "name": "bash", "arguments": {}},
                ],
            )
        )
    )
    result = convert_events(source)
    assert result.extra["unresolved_tool_call_ids"] == ["pending"]
    assert result.extra["partial"]
    assert result.steps[0].observation is None


def test_truncated_final_event_exports_valid_prefix_and_preserves_source(log):
    log.write_text(log.read_text() + '{"type":"message_end","message":')
    original = log.read_bytes()
    result = Trajectory.model_validate_json(export_trajectory(log).read_text())
    assert len(result.steps) == 3
    assert result.extra["partial"]
    assert result.extra["truncated_tail_line"] == len(log.read_text().splitlines())
    assert result.notes.startswith("PARTIAL:")
    assert log.read_bytes() == original


@pytest.mark.parametrize("suffix", ["\n", '\n{"type":"agent_end"}\n'])
def test_corrupt_complete_or_interior_event_is_not_silently_dropped(log, suffix):
    log.write_text(log.read_text() + '{"type":' + suffix)
    with pytest.raises(ValueError, match="malformed Pi event"):
        export_trajectory(log)
    assert not log.with_name("trajectory.json").exists()


@pytest.mark.parametrize("failure", [ValueError("damaged event"), OSError("disk error")])
def test_export_failure_cannot_escape_post_run_or_lose_native_usage(
    log, monkeypatch, caplog, failure
):
    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr("affinity_agent.agent.export_trajectory", fail)
    agent = PiTrajectoryAgent(logs_dir=log.parent, model_name="google/test-model", version="0.85.1")
    context = AgentContext()
    agent.populate_context_post_run(context)
    assert context.n_output_tokens == 5
    assert context.cost_usd == 0.01
    assert "Trajectory export failed; native Pi logs preserved" in caplog.text


def test_backfill_cli_finds_step_logs(log):
    task = Path(__file__).resolve().parents[1]
    destination = log.parent / "job/trial/steps/battle-01/agent"
    destination.mkdir(parents=True)
    (destination / "pi.txt").write_bytes(log.read_bytes())
    command = [
        sys.executable,
        str(task / "convert_pi_trajectories.py"),
        str(log.parent / "job"),
    ]
    first = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert first.returncode == 0, first.stderr
    assert "Exported:" in first.stdout
    second = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert second.returncode == 0 and "Kept existing:" in second.stdout


@pytest.mark.docker
@pytest.mark.parametrize("interior", [False, True])
def test_timeout_and_damaged_export_still_reach_harbor_verifier(tmp_path, interior):
    import os

    from generate_steps import write_generated
    from run_no_memory import TASK, isolated_files

    task = tmp_path / "task"
    write_generated(task, isolated_files(TASK, 1), False)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(TASK / "checks"), str(TASK)])
    proc = subprocess.run(
        [
            str(Path(sys.executable).parent / "harbor"),
            "run",
            "-p",
            str(task),
            "--jobs-dir",
            str(tmp_path / "jobs"),
            "--job-name",
            "export-probe",
            "-n",
            "1",
            "--max-retries",
            "0",
            "-a",
            "resume_probe:ExportProbeAgent",
            "-m",
            "google/test-model",
            "--ak",
            f"interior={str(interior).lower()}",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    paths = list((tmp_path / "jobs/export-probe").glob("*/result.json"))
    assert len(paths) == 1, proc.stdout + proc.stderr
    result = json.loads(paths[0].read_text())
    assert result["exception_info"] is None
    step = result["step_results"][0]
    assert step["exception_info"]["exception_type"] == "AgentTimeoutError"
    assert step["verifier_result"]["rewards"]["completed"] == 0
    assert step["verifier_result"]["rewards"]["reward"] == 0
    agent = paths[0].parent / "steps/battle-01/agent"
    assert (agent / "pi.txt").is_file()
    if interior:
        assert not (agent / "trajectory.json").exists()
    else:
        trajectory = json.loads((agent / "trajectory.json").read_text())
        assert trajectory["extra"]["partial"]
