#!/usr/bin/python3 -I
"""Root-only Harbor lifecycle. No agent command can reset, advance, or settle a job."""

import os
import pwd
import sys
from pathlib import Path

sys.path.insert(0, "/opt/programming-language")
from language_game.log_permissions import restore_agent_log_access
from language_game.runtime import Runtime


def main():
    if os.geteuid() != 0 or os.environ.get("SUDO_USER"):
        raise ValueError("only the Harbor harness may manage problems")
    if len(sys.argv) != 3 or sys.argv[1] not in ("start", "settle"):
        raise ValueError("usage: admin.py start <index> | settle <index>")
    runtime = Runtime()
    index = int(sys.argv[2])
    if sys.argv[1] == "start":
        Path("/logs").chmod(0o755)
        Path("/logs/verifier").mkdir(exist_ok=True)
        Path("/logs/verifier").chmod(0o700)
        sys.stdout.write(runtime.start(index))
    else:
        runtime.settle(index)
        restore_agent_log_access(Path("/logs/agent"), pwd.getpwnam("agent").pw_gid)
        if runtime.load()["current"]["index"] == index and index < len(runtime.trial["problems"]):
            runtime.start(index + 1)
        print("Problem settled.")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        sys.exit(str(exc))
