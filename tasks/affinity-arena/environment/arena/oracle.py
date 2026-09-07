"""Exact finite-horizon dynamic programming, with integer reward comparisons."""

from __future__ import annotations

from functools import cache
from itertools import permutations

from .engine import (
    TICK_CAP,
    Action,
    Chart,
    Combat,
    Creature,
    Matchup,
    State,
    legal_actions,
    outcome,
    score,
)

# Higher score, then fewer remaining ticks. All optimal sets use both criteria.
Value = tuple[int, int]


class Solver:
    def __init__(self, combat: Combat, cap: int = TICK_CAP):
        self.combat = combat
        self.cap = cap
        # Instance-owned cache: avoid retaining every solver via a decorated method.
        self.value = cache(self._value)

    def _value(self, state: State) -> Value:
        if outcome(state, self.cap):
            return score(state), 0
        return max(self.q(state, a) for a in legal_actions(state, self.cap))

    def q(self, state: State, action: Action) -> Value:
        score_value, negative_ticks = self.value(self.combat.advance(state, action))
        return score_value, negative_ticks - 1

    def optimal_actions(self, state: State) -> tuple[Action, ...]:
        best = self.value(state)
        return tuple(a for a in legal_actions(state, self.cap) if self.q(state, a) == best)

    def close(self) -> None:
        self.value.cache_clear()


def solve_drafts(
    matchup: Matchup, chart: Chart, cap: int = TICK_CAP
) -> tuple[Value, dict[tuple[str, ...], Value]]:
    values = {}
    for team in permutations(matchup.offered, 3):
        solver = Solver(Combat(team, matchup.opponent, chart), cap)
        values[tuple(c.name for c in team)] = solver.value(State())
        solver.close()
    return max(values.values()), values


def trajectory(
    team: tuple[Creature, ...], matchup: Matchup, chart: Chart
) -> tuple[State, list[Action]]:
    solver = Solver(Combat(team, matchup.opponent, chart))
    state, actions = State(), []
    while not outcome(state):
        action = solver.optimal_actions(state)[0]
        actions.append(action)
        state = solver.combat.advance(state, action)
    solver.close()
    return state, actions
