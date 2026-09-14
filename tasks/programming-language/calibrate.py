#!/usr/bin/env python3
"""Host-only semantic ablation: can a token map plus wrong idioms solve the curriculum?

Reference algorithms are supplied to a compiler with one mistaken semantic assumption.
This tests whether the task exercises language usage. It is NOT a learning agent or
an estimate of stateful/stateless model performance. No model API calls are made.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "environment"))

from language_game.engine import VERSION, Language, compile_source, execute
from language_game.generation import generate_trial

from generate_steps import validate_trial
from oracle import reference_program

ASSUMPTIONS = {
    "input_mode": ("replace", "add"),
    "output_mode": ("preserve", "clear"),
    "loop_mode": ("manual", "consume"),
}


def ablate(trial: dict) -> list[dict]:
    """Hold token mapping, hardware, algorithms and tests fixed; change one assumption."""
    language = Language(**trial["language"])
    rows = []
    for field, choices in ASSUMPTIONS.items():
        actual = getattr(language, field)
        assumed = next(choice for choice in choices if choice != actual)
        mistaken = replace(language, **{field: assumed})
        failures = []
        for problem in trial["problems"]:
            code = reference_program(problem["family"], problem["parameter"], mistaken)
            program = compile_source(language, language.encode(code))
            for test in problem["hidden_tests"]:
                outcome = execute(language, program, test["input"])
                if outcome.error or list(outcome.output) != test["output"]:
                    failures.append({"family": problem["family"], "phase": problem["phase"]})
                    break
        rows.append(
            {
                "version": VERSION,
                "seed": trial["seed"],
                "field": field,
                "actual": actual,
                "assumed": assumed,
                "failures": failures,
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(1, 11)))
    parser.add_argument("--out-dir", type=Path, default=ROOT / f"results/semantics-v{VERSION}")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rows = []
    for seed in args.seeds:
        trial = generate_trial(seed)
        validate_trial(trial)
        rows.extend(ablate(trial))
    # A portable conservative idiom may work in both modes. Require a witness
    # across the requested seeds, not failure of every wrong assumption in both directions.
    covered = all(
        any(
            row["field"] == field and any(p["phase"] in phases for p in row["failures"])
            for row in rows
        )
        for field in ASSUMPTIONS
        for phases in ({"foundation", "practice"}, {"holdout"})
    )
    lines = [
        "# Semantic coverage diagnostic",
        "",
        "Known algorithms, correct token mapping, one wrong semantic assumption. "
        "Counts show problems failing at least one test, not an agent learning score.",
        "",
        "| Seed | Rule | Actual | Assumed | Foundation/practice failures | Transfer/holdout failures |",
        "|---|---|---|---|---:|---:|",
    ]
    for row in rows:
        early = sum(p["phase"] in ("foundation", "practice") for p in row["failures"])
        late = len(row["failures"]) - early
        lines.append(
            f"| {row['seed']} | {row['field']} | {row['actual']} | {row['assumed']} | {early} | {late} |"
        )
    lines += [
        "",
        f"Each rule has both a foundation/practice and a holdout witness: {covered}",
        "Correct reference programs passed every example and hidden test for these seeds.",
        "Conservative copying or clearing can be portable; zero failures is legitimate.",
        "",
    ]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "calibration.json").write_text(json.dumps(rows, indent=2) + "\n")
    (args.out_dir / "calibration.md").write_text("\n".join(lines))
    print("\n".join(lines))
    if args.check and not covered:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
