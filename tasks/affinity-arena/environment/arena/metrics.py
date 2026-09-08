"""Post-battle grading from authoritative state and the original decisions."""

from .engine import (
    AFFINITIES,
    Action,
    Chart,
    Combat,
    Matchup,
    draft,
    outcome,
    reward,
    state_from_dict,
)
from .oracle import Solver


def belief_metrics(data: object, chart: Chart) -> tuple[float, float]:
    correct = filled = 0
    if isinstance(data, dict):
        for a, name in enumerate(AFFINITIES):
            row = data.get(name)
            if not isinstance(row, dict):
                continue
            for d, target in enumerate(AFFINITIES):
                value = row.get(target)
                if type(value) in (int, float) and value in (0.5, 1, 2):
                    filled += 1
                    correct += value * 2 == chart[a][d]
    return correct / 36, filled / 36


def grade(
    battle: dict, chart: Chart, matchup: Matchup, record: dict, cells: list, beliefs: object
) -> dict[str, float | int]:
    state = state_from_dict(record["state"])
    terminal = outcome(state) if record["team"] else None
    actual_reward = reward(state) if terminal else 0.0
    best = tuple(battle["oracle_value"])
    draft_ok = optimal = 0
    events = record["events"]
    if record["team"]:
        team = draft(matchup, record["team"])
        chosen = next(
            row["value"] for row in battle["draft_values"] if row["team"] == record["team"]
        )
        draft_ok = int(tuple(chosen) == best)
        optimal = draft_ok
        solver = Solver(Combat(team, matchup.opponent, chart))
        for event in events:
            if event["kind"] == "tick":
                before = state_from_dict(event["before"])
                optimal += Action(*event["action"]) in solver.optimal_actions(before)
        solver.close()
    accuracy, coverage = belief_metrics(beliefs, chart)
    return {
        "reward": actual_reward,
        "won": int(terminal == "win"),
        "completed": int(terminal is not None),
        "ticks": state.tick,
        "oracle_ticks": -best[1],
        "opt_rate": optimal / len(events) if events else 0.0,
        "regret": best[0] / 4200 - actual_reward,
        "draft_ok": draft_ok,
        "cells_seen": len(cells) / 36,
        "belief_acc": accuracy,
        "belief_cov": coverage,
        "env_actions": len(events),
    }
