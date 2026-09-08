#!/usr/bin/env python3
"""Compare exact, persistent-observation, and memoryless policies without an LLM."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "environment"))

from arena.engine import Combat, State, draft, matchup_from_dict, outcome, reward
from arena.generation import generate_trial
from arena.oracle import Solver, solve_drafts


def simulate(trial: dict, policy: str) -> list[dict]:
    chart = tuple(tuple(row) for row in trial["chart"])
    known: dict[tuple[int, int], int] = {}
    seen: set[tuple[int, int]] = set()
    rows = []
    for battle in trial["battles"]:
        if policy == "memoryless":
            known.clear()
        matchup = matchup_from_dict(battle)

        def estimate():
            return (
                chart
                if policy == "oracle"
                else tuple(tuple(known.get((a, d), 2) for d in range(6)) for a in range(6))
            )

        if policy == "oracle":
            best = tuple(battle["oracle_value"])
            drafts = {tuple(row["team"]): tuple(row["value"]) for row in battle["draft_values"]}
        else:
            best, drafts = solve_drafts(matchup, estimate())
        names = next(names for names, value in drafts.items() if value == best)
        team = draft(matchup, list(names))
        combat = Combat(team, matchup.opponent, chart)
        oracle = Solver(combat)
        true_best = tuple(battle["oracle_value"])
        chosen_value = next(
            tuple(row["value"]) for row in battle["draft_values"] if row["team"] == list(names)
        )
        draft_ok = int(chosen_value == true_best)
        optimal, actions, state = draft_ok, 1, State()
        while not outcome(state):
            planner = Solver(Combat(team, matchup.opponent, estimate()))
            candidates = planner.optimal_actions(state)
            # Explore only among equally valuable estimated actions. Unknown
            # opponent attacks are still learned from the subsequent observation.
            action = candidates[0]
            if policy != "oracle":
                for candidate in candidates:
                    if (
                        candidate.kind == "attack"
                        and (
                            team[state.active].moves[candidate.index].affinity,
                            matchup.opponent[state.enemy].affinity,
                        )
                        not in known
                    ):
                        action = candidate
                        break
            optimal += action in oracle.optimal_actions(state)
            state, hits = combat.step(state, action)
            for hit in hits:
                cell = (hit.attack_affinity, hit.defender_affinity)
                known[cell] = 2 * hit.damage // hit.power
                seen.add(cell)
            actions += 1
            planner.close()
        oracle.close()
        rows.append(
            {
                "seed": trial["seed"],
                "policy": policy,
                "battle": battle["index"],
                "reward": reward(state),
                "won": int(outcome(state) == "win"),
                "regret": true_best[0] / 4200 - reward(state),
                "ticks": state.tick,
                "oracle_ticks": -true_best[1],
                "opt_rate": optimal / actions,
                "draft_ok": draft_ok,
                "cells_seen": len(seen) / 36,
                "belief_acc": len(known) / 36,
                "env_actions": actions,
            }
        )
    return rows


def calibration_checks(rows: list[dict]) -> dict[str, bool]:
    """Check data completeness and exact-oracle behavior, not learning magnitude."""
    seeds = {r["seed"] for r in rows}
    expected = {
        (seed, policy, battle)
        for seed in seeds
        for policy in ("oracle", "learner", "memoryless")
        for battle in range(1, 21)
    }
    actual = [(r["seed"], r["policy"], r["battle"]) for r in rows]
    oracle_rows = [r for r in rows if r["policy"] == "oracle"]
    return {
        "complete_schedule": bool(rows)
        and len(actual) == len(expected)
        and set(actual) == expected,
        "oracle_exact": bool(oracle_rows)
        and all(
            r["won"] == 1
            and r["regret"] == 0
            and r["opt_rate"] == 1
            and r["draft_ok"] == 1
            and r["ticks"] == r["oracle_ticks"]
            for r in oracle_rows
        ),
    }


def render_report(rows: list[dict], checks: dict[str, bool]) -> str:
    lines = [
        "# Affinity Arena offline calibration",
        "",
        "Means across seeds. Policies share each chart and schedule.",
        "",
        "| Policy | Battles | Reward | Win rate | Optimal actions | Draft quality | Coverage | Regret |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for policy in ("oracle", "learner", "memoryless"):
        for start, end in ((1, 5), (11, 15), (16, 20)):
            selected = [r for r in rows if r["policy"] == policy and start <= r["battle"] <= end]
            values = " | ".join(
                f"{mean(r[key] for r in selected):.3f}"
                for key in ("reward", "won", "opt_rate", "draft_ok", "cells_seen", "regret")
            )
            lines.append(f"| {policy} | {start}–{end} | {values} |")
    lines.extend(["", "Reward changes (descriptive, without acceptance thresholds):", ""])
    for policy in ("learner", "memoryless"):
        early, late, holdout = (
            mean(r["reward"] for r in rows if r["policy"] == policy and start <= r["battle"] <= end)
            for start, end in ((1, 5), (11, 15), (16, 20))
        )
        lines.append(
            f"- {policy}: late − early = {late - early:+.3f}; "
            f"holdout − late = {holdout - late:+.3f}"
        )
    lines.extend(["", "Correctness and completeness checks (not learning claims):", ""])
    lines.extend(f"- {name}: {'PASS' if passed else 'FAIL'}" for name, passed in checks.items())
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(1, 11)))
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results" / "calibration")
    parser.add_argument(
        "--check", action="store_true", help="exit nonzero for incomplete data or oracle errors"
    )
    args = parser.parse_args()
    rows = []
    for seed in args.seeds:
        trial = generate_trial(seed)
        for policy in ("oracle", "learner", "memoryless"):
            rows.extend(simulate(trial, policy))
        print(f"Finished seed {seed}", flush=True)
    checks = calibration_checks(rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "calibration.json").write_text(
        json.dumps({"rows": rows, "checks": checks}, indent=2) + "\n"
    )
    report = render_report(rows, checks)
    (args.out_dir / "calibration.md").write_text(report)
    print(report)
    if args.check and not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
