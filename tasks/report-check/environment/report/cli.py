#!/usr/bin/env python3
"""report CLI: submit, status. brief/settle belong to the Harbor hooks.

The agent reaches this file through `report`, a sudo wrapper. `settle` is held
shut by a guard variable that sudo's env reset strips, so the agent cannot
settle its own job. `brief` runs as the agent because Harbor runs setup.sh as
the agent, and is held shut by the run-order check in desk.guard_open.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import cmd_brief, cmd_settle, cmd_status, cmd_submit  # noqa: E402


def _usage() -> str:
    return "usage: report submit|status"


def main(argv: list[str]) -> int:
    if not argv:
        print(_usage(), file=sys.stderr)
        return 2

    cmd = argv[0]
    if cmd == "submit":
        text, code = cmd_submit()
        sys.stdout.write(text)
        return code
    if cmd == "status":
        print(cmd_status())
        return 0
    if cmd == "brief":
        # Harbor runs setup.sh as the agent user, so this arrives through the
        # same sudo wrapper the agent uses. desk.guard_open is what keeps the
        # agent from opening a job for itself.
        print(cmd_brief(int(argv[1])))
        return 0
    if cmd == "settle":
        if os.environ.get("REPORT_SETTLE") != "1":
            print("The desk settles the job, not you.", file=sys.stderr)
            return 1
        print(cmd_settle())
        return 0

    print(_usage(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
