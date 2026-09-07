#!/usr/bin/python3 -I
"""Root-only Harbor lifecycle entrypoint; never allowed through sudo."""

import os
import pwd
import sys
from pathlib import Path

sys.path.insert(0, "/opt/affinity-arena")
from arena.log_permissions import restore_agent_log_access
from arena.runtime import Runtime

if os.geteuid() != 0 or os.environ.get("SUDO_USER"):
    sys.exit("only the Harbor harness may manage battles")

try:
    if len(sys.argv) == 3 and sys.argv[1] == "start":
        Path("/logs").chmod(0o755)
        Path("/logs/verifier").mkdir(exist_ok=True)
        Path("/logs/verifier").chmod(0o700)
        sys.stdout.write(Runtime().start(int(sys.argv[2])))
    elif len(sys.argv) == 3 and sys.argv[1] == "settle":
        runtime = Runtime()
        index = int(sys.argv[2])
        runtime.settle(index)
        # Harbor chowns mounted logs to the host after each agent turn. Retain
        # that owner for archiving, but restore group access for Pi --continue.
        restore_agent_log_access(Path("/logs/agent"), pwd.getpwnam("agent").pw_gid)
        # Harbor runs workdir/setup.sh as the agent. The root verifier prepares
        # the next battle; the first is initialized during the image build.
        if index < len(runtime.trial["battles"]):
            runtime.start(index + 1)
        print("Battle settled.")
    else:
        raise ValueError("usage: admin.py start <battle> | settle <battle>")
except ValueError as exc:
    sys.exit(str(exc))
