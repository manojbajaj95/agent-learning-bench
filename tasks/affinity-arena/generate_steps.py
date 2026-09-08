#!/usr/bin/env python3
"""Generate a reproducible Harbor task; --check detects committed-file drift."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "environment"))

from arena.engine import Combat, State, action_command, draft, matchup_from_dict, outcome
from arena.generation import generate_trial
from arena.oracle import Solver


def generated_files(seed: int) -> dict[str, str]:
    trial = generate_trial(seed)
    result = {"environment/trial.json": json.dumps(trial, indent=2) + "\n"}
    instruction = (ROOT / "instruction.md").read_text()
    toml = """schema_version = "1.4"
multi_step_reward_strategy = "mean"
artifacts = ["/app/view.txt", "/app/notes.md", "/app/affinity-chart.json", "/app/sessions"]

[task]
name = "agent-learning-bench/affinity-arena"
version = "0.2.1"
description = "Learn a hidden affinity chart across twenty deterministic creature battles."
keywords = ["multi-step", "learning", "games", "hidden-chart"]

[metadata]
difficulty = "hard"
category = "games"
seed = SEED

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
""".replace("SEED", str(seed))
    chart = tuple(tuple(row) for row in trial["chart"])
    for battle in trial["battles"]:
        index = battle["index"]
        step = f"battle-{index:02d}"
        prefix = f"steps/{step}"
        result[f"{prefix}/instruction.md"] = instruction
        result[f"{prefix}/workdir/setup.sh"] = (
            "#!/usr/bin/env bash\nset -euo pipefail\naffinity-arena status\n"
        )
        result[f"{prefix}/tests/test.sh"] = (
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            f"/usr/bin/python3 -I /opt/affinity-arena/admin.py settle {index}\n"
        )
        matchup = matchup_from_dict(battle)
        chosen = next(
            row["team"]
            for row in battle["draft_values"]
            if tuple(row["value"]) == tuple(battle["oracle_value"])
        )
        team = draft(matchup, chosen)
        solver = Solver(Combat(team, matchup.opponent, chart))
        state = State()
        commands = [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "affinity-arena draft " + " ".join(chosen),
        ]
        while not outcome(state):
            action = solver.optimal_actions(state)[0]
            commands.append("affinity-arena " + action_command(team, state, action))
            state = solver.combat.advance(state, action)
        solver.close()
        result[f"{prefix}/solution/solve.sh"] = "\n".join(commands) + "\n"
        toml += f'\n[[steps]]\nname = "{step}"\nartifacts = ["/app/battles/{step}.jsonl"]\n'
    result["task.toml"] = toml
    return result


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
    # Never recursively delete a directory: unexpected files should be reviewed.
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
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = generated_files(args.seed)
    # A separate output is a complete task, with implementation assets copied as
    # text. This avoids changing the checked-in instance for multi-seed runs.
    if args.output.resolve() != ROOT:
        for path in (ROOT / "environment").rglob("*"):
            if (
                path.is_file()
                and path.suffix != ".pyc"
                and "__pycache__" not in path.parts
                and path.name != "trial.json"
            ):
                files[str(path.relative_to(ROOT))] = path.read_text()
    mismatch = write_generated(args.output, files, args.check)
    if args.check and mismatch:
        raise SystemExit("Generated files differ: " + ", ".join(mismatch))
    print(
        f"{'Checked' if args.check else 'Generated'} 20 battles, seed {args.seed}, at {args.output}"
    )


if __name__ == "__main__":
    main()
