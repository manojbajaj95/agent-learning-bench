#!/usr/bin/env python3
"""Generate Harbor steps for the poker match. --check detects drift."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "environment"))

from poker_game.engine import HERO, Match, apply_action, finish_hand, start_hand
from poker_game.fish import fish_action
from poker_game.oracle import oracle_action
from poker_game.runtime import HANDS, SEED

INSTRUCTION = (ROOT / "instruction.md").read_text()


def play_oracle_hand(match: Match) -> tuple[Match, list[str]]:
    match = start_hand(match)
    commands: list[str] = []
    hand = match.current
    assert hand is not None
    while not hand.over:
        while not hand.over and hand.to_act != HERO:
            action, raise_to = fish_action(hand)
            apply_action(hand, action, raise_to)
        if hand.over:
            break
        action, raise_to = oracle_action(hand)
        if action == "raise":
            commands.append(f"poker act raise {raise_to}")
        else:
            commands.append(f"poker act {action}")
        apply_action(hand, action, raise_to)
    return finish_hand(match), commands


def generated_files() -> dict[str, str]:
    toml = f"""schema_version = "1.4"
multi_step_reward_strategy = "final"
artifacts = ["/app/view.txt", "/app/sessions"]

[task]
name = "agent-learning-bench/poker"
version = "0.1.0"
description = "Heads-up Hold'em against a sticky opponent. Score is earnings at the end."
keywords = ["poker", "multi-step", "learning", "games"]

[metadata]
difficulty = "hard"
category = "games"
seed = {SEED}

[agent]
user = "agent"
timeout_sec = 180.0

[verifier]
user = "root"
timeout_sec = 30.0

[environment]
network_mode = "public"
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
workdir = "/app"
"""
    files: dict[str, str] = {}
    match = Match(seed=SEED, hands=HANDS)
    for index in range(1, HANDS + 1):
        step = f"hand-{index:03d}"
        prefix = f"steps/{step}"
        files[f"{prefix}/instruction.md"] = INSTRUCTION
        files[f"{prefix}/workdir/setup.sh"] = (
            "#!/usr/bin/env bash\nset -euo pipefail\npoker status\nrm -- \"$0\"\n"
        )
        files[f"{prefix}/tests/test.sh"] = (
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            f"/usr/bin/python3 -I /opt/poker/admin.py settle {index}\n"
        )
        if match.complete():
            commands = ["#!/usr/bin/env bash", "set -euo pipefail", "poker status"]
        else:
            match, acts = play_oracle_hand(match)
            commands = ["#!/usr/bin/env bash", "set -euo pipefail", *acts]
        files[f"{prefix}/solution/solve.sh"] = "\n".join(commands) + "\n"
        toml += f'\n[[steps]]\nname = "{step}"\n'
    files["task.toml"] = toml
    return files


def write_generated(output: Path, files: dict[str, str], check: bool) -> list[str]:
    mismatches = []
    for relative, content in files.items():
        path = output / relative
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError(f"refusing symlink destination: {path}")
        matches = path.is_file() and path.read_text() == content
        if relative.endswith(".sh") and path.exists():
            matches = matches and path.stat().st_mode & 0o111 == 0o111
        if not matches:
            mismatches.append(relative)
        if not check and not matches:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
                stream.write(content)
                tmp = Path(stream.name)
            tmp.chmod(0o755 if relative.endswith(".sh") else 0o644)
            tmp.replace(path)
    steps = output / "steps"
    if steps.exists():
        mismatches.extend(
            str(p.relative_to(output))
            for p in steps.rglob("*")
            if p.is_file() and str(p.relative_to(output)) not in files
        )
    return mismatches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = generated_files()
    mismatches = write_generated(ROOT, files, args.check)
    if args.check and mismatches:
        print("drift:", *mismatches, sep="\n")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
