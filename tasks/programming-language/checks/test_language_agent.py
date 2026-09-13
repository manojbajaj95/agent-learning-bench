import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from harbor.agents.installed.pi import Pi
from harbor.models.agent.context import AgentContext

from language_agent.agent import PiProviderFailure, SequentialPi
from language_agent.trace import read_pi_errors


def event(error=None, role="assistant", kind="message_end"):
    return json.dumps(
        {
            "type": kind,
            "message": {
                "role": role,
                "stopReason": "error" if error else "stop",
                "errorMessage": error,
            },
        }
    )


def test_trace_distinguishes_provider_failure_from_program_feedback(tmp_path):
    path = tmp_path / "pi.txt"
    assert read_pi_errors(path) == []
    path.write_text(
        "shell diagnostic\nnull\n{}\n[]\n"
        + "\n".join(
            [
                event("MALFORMED_FUNCTION_CALL", kind="message_update"),
                event("SYNTAX_ERROR", role="toolResult"),
                event(),
                event("Provider stopped with: MALFORMED_FUNCTION_CALL"),
                event("Provider stopped with: MALFORMED_FUNCTION_CALL"),
                event("EACCES: session log write failed"),
            ]
        )
    )
    assert read_pi_errors(path) == [
        "Provider stopped with: MALFORMED_FUNCTION_CALL",
        "EACCES: session log write failed",
    ]


def test_provider_error_prevents_next_paid_call_and_new_trial_resets(tmp_path):
    agent = SequentialPi(logs_dir=tmp_path, model_name="google/gemini-3.5-flash")
    (tmp_path / "pi.txt").write_text(event("Provider stopped with: MALFORMED_FUNCTION_CALL"))
    agent.populate_context_post_run(AgentContext())
    # Harbor moves logs between steps. The failure must survive that movement.
    (tmp_path / "pi.txt").unlink()
    agent.populate_context_post_run(AgentContext())
    with patch.object(Pi, "run", new_callable=AsyncMock) as run:
        with pytest.raises(PiProviderFailure, match="No further model calls"):
            asyncio.run(agent.run("next problem", object(), AgentContext()))
        run.assert_not_awaited()
        fresh = SequentialPi(logs_dir=tmp_path, model_name="google/gemini-3.5-flash")
        asyncio.run(fresh.run("new trial", object(), AgentContext()))
        run.assert_awaited_once()


def test_extension_flags_keep_existing_thinking_and_pin_version(tmp_path):
    agent = SequentialPi(logs_dir=tmp_path, thinking="low")
    assert agent.build_cli_flags().split() == [
        "--thinking",
        "low",
        "-e",
        "/opt/language-pi/sequential-tools.ts",
    ]
    with pytest.raises(ValueError, match="validated with Pi"):
        SequentialPi(logs_dir=tmp_path, version="other")


def test_failed_timeout_cleanup_preserves_cancellation_and_blocks_further_calls(tmp_path):
    agent = SequentialPi(logs_dir=tmp_path)
    with (
        patch.object(Pi, "run", new_callable=AsyncMock, side_effect=asyncio.CancelledError),
        patch.object(agent, "exec_as_root", new_callable=AsyncMock, side_effect=OSError),
    ):
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(agent.run("expired problem", object(), AgentContext()))
    with patch.object(Pi, "run", new_callable=AsyncMock) as run:
        with pytest.raises(PiProviderFailure, match="Timeout cleanup failed"):
            asyncio.run(agent.run("next problem", object(), AgentContext()))
        run.assert_not_awaited()
