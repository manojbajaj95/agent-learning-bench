#!/usr/bin/python3 -I
"""Only this entrypoint may be executed with sudo by the agent."""

import sys

sys.path.insert(0, "/opt/poker")
from poker_game.runtime import Runtime

try:
    if len(sys.argv) < 2:
        raise ValueError("use status or act fold|check|call|raise [amount]")
    sys.stdout.write(Runtime().command(sys.argv[1:]))
except ValueError as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(2)
