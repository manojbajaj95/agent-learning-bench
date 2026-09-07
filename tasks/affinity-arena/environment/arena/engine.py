"""Pure battle rules. No filesystem, randomness, or evaluator dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

AFFINITIES = ("Amber", "Basalt", "Cobalt", "Flint", "Jade", "Onyx")
PLAYER_HP = 100
OPPONENT_HP = 140
TICK_CAP = 30
# Integer half-units avoid floating-point comparisons throughout the engine.
Chart = tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class Move:
    name: str
    affinity: int
    power: int


@dataclass(frozen=True, slots=True)
class Creature:
    name: str
    affinity: int
    moves: tuple[Move, ...]


@dataclass(frozen=True, slots=True)
class Matchup:
    offered: tuple[Creature, ...]
    opponent: tuple[Creature, ...]


class State(NamedTuple):
    """Opponents before enemy are dead; opponents after it are at full HP."""

    hp: tuple[int, int, int] = (100, 100, 100)
    active: int = 0
    enemy: int = 0
    enemy_hp: int = 140
    tick: int = 0


class Action(NamedTuple):
    kind: str
    index: int


class Hit(NamedTuple):
    side: str
    attacker: str
    defender: str
    move: str
    attack_affinity: int
    defender_affinity: int
    power: int
    damage: int


def damage(move: Move, defender: Creature, chart: Chart) -> int:
    return move.power * chart[move.affinity][defender.affinity] // 2


def outcome(state: State, cap: int = TICK_CAP) -> str | None:
    if state.enemy == 3:
        return "win"
    if not any(state.hp):
        return "loss"
    return "tick_cap" if state.tick >= cap else None


def score(state: State) -> int:
    """Reward numerator, with denominator 4200, exact for comparisons."""
    opponent_hp = 0 if state.enemy == 3 else state.enemy_hp + (2 - state.enemy) * 140
    return 2100 + 7 * sum(state.hp) - 5 * opponent_hp


def reward(state: State) -> float:
    return score(state) / 4200


def draft(matchup: Matchup, names: list[str]) -> tuple[Creature, ...]:
    offered = {c.name: c for c in matchup.offered}
    if len(names) != 3 or len(set(names)) != 3 or any(n not in offered for n in names):
        raise ValueError("draft exactly three distinct offered creatures, in order")
    return tuple(offered[n] for n in names)


def legal_actions(state: State, cap: int = TICK_CAP) -> tuple[Action, ...]:
    if outcome(state, cap):
        return ()
    return tuple(Action("attack", i) for i in range(3)) + tuple(
        Action("switch", i) for i, hp in enumerate(state.hp) if hp and i != state.active
    )


def parse_action(team: tuple[Creature, ...], state: State, command: list[str]) -> Action:
    if len(command) != 2 or command[0] not in {"attack", "switch"}:
        raise ValueError("use attack <move> or switch <creature>")
    names = (
        [m.name for m in team[state.active].moves]
        if command[0] == "attack"
        else [c.name for c in team]
    )
    if command[1] not in names:
        raise ValueError("unknown move or creature for this team")
    return Action(command[0], names.index(command[1]))


def action_command(team: tuple[Creature, ...], state: State, action: Action) -> str:
    name = (
        team[state.active].moves[action.index].name
        if action.kind == "attack"
        else team[action.index].name
    )
    return f"{action.kind} {name}"


class Combat:
    """Precomputed damage for one draft, also used by the exact solver."""

    def __init__(self, team: tuple[Creature, ...], opponent: tuple[Creature, ...], chart: Chart):
        self.team, self.opponent = team, opponent
        self.attacks = tuple(
            tuple(tuple(damage(m, enemy, chart) for m in c.moves) for enemy in opponent)
            for c in team
        )
        self.responses = tuple(
            tuple(tuple(damage(m, c, chart) for m in enemy.moves) for c in team)
            for enemy in opponent
        )
        self.enemy_moves = tuple(
            tuple(max(range(3), key=lambda m: self.responses[e][p][m]) for p in range(3))
            for e in range(3)
        )

    def advance(self, state: State, action: Action) -> State:
        """Unchecked transition for a legal action; public callers use step()."""
        hp, active, enemy, enemy_hp, tick = state
        if action.kind == "attack":
            enemy_hp = max(0, enemy_hp - self.attacks[active][enemy][action.index])
            if not enemy_hp:
                enemy += 1
                return State(hp, active, enemy, 140 if enemy < 3 else 0, tick + 1)
        else:
            active = action.index
        new_hp = list(hp)
        new_hp[active] = max(0, hp[active] - max(self.responses[enemy][active]))
        if not new_hp[active]:
            # Earliest surviving creature in the original draft, including benched ones.
            active = next((i for i, value in enumerate(new_hp) if value), 0)
        return State(tuple(new_hp), active, enemy, enemy_hp, tick + 1)

    def step(
        self, state: State, action: Action, cap: int = TICK_CAP
    ) -> tuple[State, tuple[Hit, ...]]:
        if action not in legal_actions(state, cap):
            raise ValueError("action is not legal in the current battle state")
        after = self.advance(state, action)
        hits = []
        if action.kind == "attack":
            c, target = self.team[state.active], self.opponent[state.enemy]
            move = c.moves[action.index]
            hits.append(
                Hit(
                    "agent",
                    c.name,
                    target.name,
                    move.name,
                    move.affinity,
                    target.affinity,
                    move.power,
                    self.attacks[state.active][state.enemy][action.index],
                )
            )
        if after.enemy == state.enemy:
            active = action.index if action.kind == "switch" else state.active
            c, target = self.opponent[state.enemy], self.team[active]
            index = self.enemy_moves[state.enemy][active]
            move = c.moves[index]
            hits.append(
                Hit(
                    "opponent",
                    c.name,
                    target.name,
                    move.name,
                    move.affinity,
                    target.affinity,
                    move.power,
                    self.responses[state.enemy][active][index],
                )
            )
        return after, tuple(hits)


def creature_from_dict(data: dict) -> Creature:
    return Creature(data["name"], data["affinity"], tuple(Move(**m) for m in data["moves"]))


def matchup_from_dict(data: dict) -> Matchup:
    return Matchup(
        *(tuple(creature_from_dict(c) for c in data[key]) for key in ("offered", "opponent"))
    )


def state_from_dict(data: dict) -> State:
    return State(tuple(data["hp"]), data["active"], data["enemy"], data["enemy_hp"], data["tick"])
