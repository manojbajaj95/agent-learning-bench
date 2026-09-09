#!/usr/bin/env python3
"""Play one seeded hand in the terminal (no Harbor)."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "environment"))

from poker_game.engine import HERO, Match, apply_action, legal_actions, start_hand
from poker_game.fish import fish_action
from poker_game.view import render


def fish_until_hero(match: Match) -> None:
    hand = match.current
    assert hand is not None
    while not hand.over and hand.to_act != HERO and legal_actions(hand):
        action, raise_to = fish_action(hand)
        apply_action(hand, action, raise_to)


def main() -> None:
    match = start_hand(Match(seed=1, hands=1))
    fish_until_hero(match)
    print(render(match), end="")
    while match.current and not match.current.over:
        try:
            argv = shlex.split(input("poker> "))
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not argv or argv == ["quit"]:
            break
        if argv[:1] == ["poker"]:
            argv = argv[1:]
        try:
            if argv == ["status"]:
                print(render(match), end="")
                continue
            if argv[:1] != ["act"]:
                raise ValueError("act fold|check|call|raise [amount]")
            action = argv[1]
            raise_to = int(argv[2]) if action == "raise" and len(argv) > 2 else None
            apply_action(match.current, action, raise_to)
            fish_until_hero(match)
        except (ValueError, IndexError) as exc:
            print(exc)
            continue
        print(render(match), end="")


if __name__ == "__main__":
    main()
