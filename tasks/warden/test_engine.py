#!/usr/bin/env python3
"""Local checks: pose loop, death, two-cycle win, wasted recovery."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "environment" / "warden"
sys.path.insert(0, str(ROOT))


def _bind(tmp: Path) -> None:
    os.environ["WARDEN_STATE_DIR"] = str(tmp)
    os.environ["WARDEN_VIEW"] = str(tmp / "view.txt")
    os.environ["WARDEN_FIGHTS"] = str(tmp / "fights")
    os.environ["WARDEN_REWARD"] = str(tmp / "reward.txt")


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="warden-"))
    _bind(tmp)
    import engine as e  # noqa: E402

    e.start_fight("01")
    assert "right arm" in e.status()

    dead = e.act("jump")
    assert "You die" in dead
    assert e.load_state()["ended"] == "dead"
    over = e.act("attack")
    assert "fight is over" in over.lower()

    e.start_fight("02")
    for a in (
        "dodge left",
        "dodge left",
        "jump",
        "attack",
        "dodge left",
        "dodge left",
        "jump",
        "attack",
    ):
        e.act(a)
    st = e.load_state()
    assert st["ended"] == "win", st
    assert st["boss_hp"] == 0
    assert st["env_actions"] == 8

    e.start_fight("03")
    e.act("dodge left")
    e.act("dodge left")
    e.act("jump")
    wasted = e.act("jump")
    assert "recovers its stance" in wasted
    assert "right arm" in wasted
    assert e.load_state()["boss_hp"] == 10
    assert e.load_state()["ended"] is None
    e.act("dodge left")
    e.act("dodge left")
    e.act("jump")
    e.act("attack")
    assert e.load_state()["boss_hp"] == 5
    print("ok")


if __name__ == "__main__":
    main()
