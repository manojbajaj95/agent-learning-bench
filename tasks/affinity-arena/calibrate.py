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


def calibration_gates(rows: list[dict]) -> dict[str, bool]:
    def avg(policy, key, start, end):
        return mean(
            row[key] for row in rows if row["policy"] == policy and start <= row["battle"] <= end
        )

    oracle_rows = [r for r in rows if r["policy"] == "oracle"]
    late = avg("learner", "reward", 11, 15)
    return {
        "oracle_exact": all(
            r["won"] == 1 and r["regret"] == 0 and r["opt_rate"] == 1 and r["draft_ok"] == 1
            for r in oracle_rows
        ),
        "learner_improvement": late - avg("learner", "reward", 1, 5) >= 0.15,
        "learner_near_oracle": avg("oracle", "reward", 11, 15) - late <= 0.08,
        "holdout_transfer": late - avg("learner", "reward", 16, 20) <= 0.10,
        "memoryless_floor": avg("memoryless", "reward", 1, 20) <= 0.55,
        "memoryless_flat": avg("memoryless", "reward", 11, 15) - avg("memoryless", "reward", 1, 5)
        <= 0.10,
        "coverage": 0.70 <= avg("learner", "cells_seen", 20, 20) <= 0.95,
    }


def render_report(rows: list[dict], gates: dict[str, bool]) -> str:
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
    lines.extend(["", "Acceptance gates:", ""])
    lines.extend(f"- {name}: {'PASS' if passed else 'FAIL'}" for name, passed in gates.items())
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(1, 11)))
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results" / "calibration")
    parser.add_argument(
        "--check", action="store_true", help="exit nonzero if calibration gates fail"
    )
    args = parser.parse_args()
    rows = []
    for seed in args.seeds:
        trial = generate_trial(seed)
        for policy in ("oracle", "learner", "memoryless"):
            rows.extend(simulate(trial, policy))
        print(f"Finished seed {seed}", flush=True)
    gates = calibration_gates(rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "calibration.json").write_text(
        json.dumps({"rows": rows, "gates": gates}, indent=2) + "\n"
    )
    report = render_report(rows, gates)
    (args.out_dir / "calibration.md").write_text(report)
    print(report)
    if args.check and not all(gates.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
