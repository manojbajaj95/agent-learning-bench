#!/usr/bin/env python3
"""warden CLI: status, combat actions, replay, play. start/settle for Harbor only."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import ACTIONS, act, settle, start_fight, status  # noqa: E402


def _usage() -> str:
    return (
        "usage: warden status|attack|block|parry|jump|potion\n"
        "       warden dodge left|dodge right\n"
        "       warden replay [path.jsonl|trial-dir]\n"
        "       warden play"
    )


def _ensure_local_paths() -> None:
    opt = Path("/opt/warden")
    if opt.is_dir() and os.access(opt, os.W_OK):
        return
    root = Path.home() / ".warden-local"
    os.environ.setdefault("WARDEN_STATE_DIR", str(root))
    os.environ.setdefault("WARDEN_VIEW", str(root / "view.txt"))
    os.environ.setdefault("WARDEN_FIGHTS", str(root / "fights"))
    os.environ.setdefault("WARDEN_REWARD", str(root / "reward.txt"))


def main(argv: list[str]) -> int:
    if not argv:
        print(_usage(), file=sys.stderr)
        return 2

    cmd = argv[0]
    if cmd == "status":
        sys.stdout.write(status())
        return 0
    if cmd == "dodge":
        if len(argv) < 2 or argv[1] not in {"left", "right"}:
            print("usage: warden dodge left|right", file=sys.stderr)
            return 2
        sys.stdout.write(act(f"dodge {argv[1]}"))
        return 0
    if cmd in ACTIONS:
        sys.stdout.write(act(cmd))
        return 0
    if cmd == "replay":
        from render import replay

        replay(argv[1] if len(argv) > 1 else "")
        return 0
    if cmd == "play":
        _ensure_local_paths()
        from render import play

        play()
        return 0
    if cmd == "start":
        if os.environ.get("WARDEN_SETUP") != "1":
            print("The fight is already running.", file=sys.stderr)
            return 1
        fight = argv[1] if len(argv) > 1 else "01"
        sys.stdout.write(start_fight(fight))
        return 0
    if cmd == "settle":
        print(settle())
        return 0

    print(_usage(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
