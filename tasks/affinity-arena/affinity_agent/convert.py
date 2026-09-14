"""Convert one Affinity Arena Pi event stream, not its cumulative session, to ATIF.

Only message_end events are consumed: starts, deltas, tool execution events,
and agent_end repeat the same messages. Native logs remain the source of truth.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from harbor.models.trajectories.trajectory import Trajectory

EXPORTER = "agent-learning-bench/pi-trajectory-v1"


def _text(content: str | list[dict[str, Any]]) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(
        part.get("text", "")
        if part.get("type") == "text"
        else f"[{part.get('type', 'unknown')} content: see native pi.txt]"
        for part in content
        if part.get("type") not in {"thinking", "toolCall"}
    )


def convert_events(source: Path, *, version: str = "unknown") -> Trajectory:
    steps: list[dict[str, Any]] = []
    pending: dict[str, dict[str, Any]] = {}
    session_id = None
    model = None
    skipped_lines = 0
    truncated_tail_line = None
    raw = source.read_text()
    lines = raw.splitlines()
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            # A killed process can leave its final event half-written. Keep
            # the valid prefix, visibly marked partial; reject interior damage.
            if line.lstrip().startswith("{"):
                if number == len(lines) and not raw.endswith("\n"):
                    truncated_tail_line = number
                    break
                raise ValueError(f"{source}:{number}: malformed Pi event") from exc
            skipped_lines += 1
            continue
        if not isinstance(event, dict):
            skipped_lines += 1
            continue
        if event.get("type") == "session":
            session_id = event.get("id")
        if event.get("type") != "message_end":
            continue
        message = event["message"]
        role = message.get("role")
        content = message.get("content") or []
        if role == "toolResult":
            call_id = message["toolCallId"]
            parent = pending.pop(call_id, None)
            if parent is None:
                raise ValueError(f"{source}:{number}: unmatched tool result {call_id}")
            parent.setdefault("observation", {"results": []})["results"].append(
                {
                    "source_call_id": call_id,
                    "content": _text(content),
                    "extra": {"is_error": message.get("isError", False)},
                }
            )
            continue
        if role not in {"user", "assistant", "system"}:
            raise ValueError(f"{source}:{number}: unsupported message role {role!r}")
        step: dict[str, Any] = {
            "step_id": len(steps) + 1,
            "source": "agent" if role == "assistant" else role,
            "message": _text(content),
        }
        timestamp = message.get("timestamp")
        if isinstance(timestamp, (int, float)):
            step["timestamp"] = datetime.fromtimestamp(timestamp / 1000, UTC).isoformat()
        elif isinstance(timestamp, str):
            step["timestamp"] = timestamp
        if role == "assistant":
            model = message.get("model") or model
            step["model_name"] = model
            step["extra"] = {"stop_reason": message.get("stopReason")}
            if message.get("errorMessage"):
                step["message"] += "\nAPI error: " + message["errorMessage"]
            parts = content if isinstance(content, list) else []
            thinking = "\n".join(
                part.get("thinking", "") for part in parts if part.get("type") == "thinking"
            )
            if thinking:
                step["reasoning_content"] = thinking
            calls = [
                {
                    "tool_call_id": part["id"],
                    "function_name": part["name"],
                    "arguments": part.get("arguments", {}),
                }
                for part in parts
                if part.get("type") == "toolCall"
            ]
            if calls:
                step["tool_calls"] = calls
                for call in calls:
                    call_id = call["tool_call_id"]
                    if call_id in pending:
                        raise ValueError(f"{source}:{number}: duplicate pending call {call_id}")
                    pending[call_id] = step
            usage = message.get("usage")
            if usage:
                # Pi's input excludes cache hits and cache writes.
                step["metrics"] = {
                    "prompt_tokens": sum(
                        usage.get(k, 0) for k in ("input", "cacheRead", "cacheWrite")
                    ),
                    "completion_tokens": usage.get("output", 0),
                    "cached_tokens": usage.get("cacheRead", 0),
                    "cost_usd": (usage.get("cost") or {}).get("total"),
                    "extra": {"pi_usage": usage},
                }
        steps.append(step)
    if not steps:
        raise ValueError(f"{source}: no completed Pi messages to export")
    metrics = [s["metrics"] for s in steps if "metrics" in s]
    totals = {"total_steps": len(steps)}
    for name in ("prompt_tokens", "completion_tokens", "cached_tokens", "cost_usd"):
        values = [m[name] for m in metrics if m.get(name) is not None]
        if values:
            totals[f"total_{name}"] = sum(values)
    return Trajectory.model_validate(
        {
            "schema_version": "ATIF-v1.7",
            "session_id": session_id,
            "agent": {"name": "pi", "version": version, "model_name": model},
            "steps": steps,
            "final_metrics": totals,
            "notes": (
                "PARTIAL: interrupted final event; only preceding completed messages are exported. "
                if truncated_tail_line is not None
                else ""
            )
            + "Export of this invocation's completed Pi messages; native resume history is not duplicated. Non-text media are placeholders; see pi.txt for originals.",
            "extra": {
                "exporter": EXPORTER,
                "partial": truncated_tail_line is not None or bool(pending),
                "truncated_tail_line": truncated_tail_line,
                "skipped_diagnostic_lines": skipped_lines,
                "unresolved_tool_call_ids": list(pending),
            },
        }
    )


def export_trajectory(source: Path, *, version: str = "unknown", replace: bool = False) -> Path:
    """Atomically publish ATIF; only replace files produced by this exporter."""
    target = source.with_name("trajectory.json")
    if target.exists():
        if not replace:
            return target
        existing = json.loads(target.read_text())
        if (existing.get("extra") or {}).get("exporter") != EXPORTER:
            raise ValueError(f"Refusing to replace a trajectory from another exporter: {target}")
    trajectory = convert_events(source, version=version)
    fd, temporary = tempfile.mkstemp(prefix=".trajectory-", suffix=".json", dir=target.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(trajectory.model_dump_json(indent=2, exclude_none=True) + "\n")
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target
