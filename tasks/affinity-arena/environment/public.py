#!/usr/bin/python3 -I
"""Only this entrypoint may be executed with sudo by the agent."""

import sys

sys.path.insert(0, "/opt/affinity-arena")
from arena.runtime import Runtime

try:
    if len(sys.argv) < 2 or sys.argv[1] not in {"status", "draft", "attack", "switch"}:
        raise ValueError("use status, draft <a> <b> <c>, attack <move>, or switch <creature>")
    sys.stdout.write(Runtime().command(sys.argv[1:]))
except ValueError as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(2)
