"""Detect Pi assistant failures which Harbor's built-in Pi does not classify."""

import json
from pathlib import Path


def read_pi_errors(path: Path) -> list[str]:
    if not path.is_file():
        return []
    errors = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue  # Pi stdout can also contain installation and shell messages.
        if not isinstance(event, dict) or event.get("type") != "message_end":
            continue
        message = event.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        if message.get("stopReason") == "error":
            errors.append(str(message.get("errorMessage") or "unspecified Pi assistant error"))
    return list(dict.fromkeys(errors))
