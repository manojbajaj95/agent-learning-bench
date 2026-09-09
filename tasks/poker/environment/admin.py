#!/usr/bin/python3 -I
"""Root-only Harbor lifecycle entrypoint; never allowed through sudo."""

import os
import pwd
import sys
from pathlib import Path

sys.path.insert(0, "/opt/poker")
from poker_game.log_permissions import restore_agent_log_access
from poker_game.runtime import Runtime

if os.geteuid() != 0 or os.environ.get("SUDO_USER"):
    sys.exit("only the Harbor harness may manage hands")

try:
    if len(sys.argv) == 3 and sys.argv[1] == "start":
        Path("/logs").chmod(0o755)
        Path("/logs/verifier").mkdir(exist_ok=True)
        Path("/logs/verifier").chmod(0o700)
        sys.stdout.write(Runtime().start(int(sys.argv[2])))
    elif len(sys.argv) == 3 and sys.argv[1] == "settle":
        Runtime().settle(int(sys.argv[2]))
        restore_agent_log_access(Path("/logs/agent"), pwd.getpwnam("agent").pw_gid)
        print("Hand settled.")
    else:
        raise ValueError("usage: admin.py start <hand> | settle <hand>")
except ValueError as exc:
    sys.exit(str(exc))
