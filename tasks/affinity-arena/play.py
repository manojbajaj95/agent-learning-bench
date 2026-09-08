#!/usr/bin/env python3
"""Human-playable terminal battle, with isolated temporary state and no API."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "environment"))

from arena.engine import AFFINITIES, outcome, state_from_dict
from arena.generation import generate_trial
from arena.runtime import Paths, Runtime


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--battle", type=int, choices=range(1, 21), default=1)
    parser.add_argument(
        "--reveal-after", action="store_true", help="print chart after a finished battle"
    )
    args = parser.parse_args()
    trial = generate_trial(args.seed, args.battle)
    with tempfile.TemporaryDirectory(prefix="affinity-arena-play-") as directory:
        root = Path(directory)
        paths = Paths(root / "private", root / "app", root / "verifier")
        paths.private.mkdir()
        (paths.public / "battles").mkdir(parents=True)
        (paths.private / "trial.json").write_text(json.dumps(trial))
        runtime = Runtime(paths)
        # Local-only selection of a later battle. The sandbox exposes no play/reset command.
        runtime.save({"current": None, "cells": [], "completed": list(range(1, args.battle))})
        print(runtime.start(args.battle))
        print("Enter draft/attack/switch/status commands, rules, or quit.")
        while True:
            try:
                command = shlex.split(input("arena> "))
            except (EOFError, KeyboardInterrupt):
                print()
                break
            except ValueError as exc:
                print(exc)
                continue
            if command == ["quit"]:
                break
            if command == ["rules"]:
                print((ROOT / "environment" / "RULES.md").read_text())
                continue
            if command[:1] == ["affinity-arena"]:
                command = command[1:]
            try:
                print(runtime.command(command))
            except ValueError as exc:
                print(exc)
                continue
            current = runtime.load()["current"]
            if current["team"] and outcome(state_from_dict(current["state"])):
                print(f"Reward: {runtime.settle()['reward']:.3f}")
                if args.reveal_after:
                    print("Attack rows, defender columns:", " ".join(AFFINITIES))
                    for affinity, row in zip(AFFINITIES, trial["chart"], strict=True):
                        print(affinity, [value / 2 for value in row])
                break


if __name__ == "__main__":
    main()
