"""Seeded instance construction; hidden data stays outside the public view."""

from __future__ import annotations

import random
from dataclasses import asdict
from itertools import permutations

from .engine import Chart, Creature, Matchup, Move
from .oracle import solve_drafts

MAIN_NAMES = (
    "Kestrel",
    "Tarn",
    "Sable",
    "Moth",
    "Ridge",
    "Vale",
    "Gorm",
    "Wick",
    "Pell",
    "Reed",
    "Ash",
    "Dune",
)
HOLDOUT_NAMES = (
    "Ibis",
    "Fen",
    "Lark",
    "Rill",
    "Wren",
    "Cairn",
    "Brin",
    "Voss",
    "Neri",
    "Kelm",
    "Orin",
    "Tess",
)
MOVE_NAMES = ("Spore", "Quake", "Shard", "Ember", "Rend", "Gloom")
HOLDOUT_MOVES = ("Pulse", "Crash", "Needle", "Spark", "Thorn", "Veil")
TRIAL_VERSION = 2
_BALANCED_ROWS = tuple(sorted(set(permutations((1, 1, 2, 2, 4, 4)))))


def generate_chart(seed: int) -> Chart:
    """Construct a balanced chart with six distinct attack/defense profiles.

    Randomized backtracking samples beyond permutations of a fixed initializer;
    it is not a uniform sampler over all balanced charts. Sorted candidates and
    a private RNG keep construction reproducible across processes.
    """
    rng = random.Random(f"affinity-arena-v{TRIAL_VERSION}:chart:{seed}")
    rows: list[tuple[int, ...]] = []
    counts = [dict.fromkeys((1, 2, 4), 0) for _ in range(6)]

    def fill() -> bool:
        if len(rows) == 6:
            return len(set(zip(*rows, strict=True))) == 6
        candidates = [
            row
            for row in _BALANCED_ROWS
            if row not in rows and all(counts[c][value] < 2 for c, value in enumerate(row))
        ]
        rng.shuffle(candidates)
        for row in candidates:
            rows.append(row)
            for column, value in enumerate(row):
                counts[column][value] += 1
            if fill():
                return True
            rows.pop()
            for column, value in enumerate(row):
                counts[column][value] -= 1
        return False

    if not fill():
        raise RuntimeError(f"cannot generate a balanced chart for seed {seed}")
    return tuple(rows)


def generate_roster(seed: int, holdout: bool = False) -> tuple[Creature, ...]:
    rng = random.Random(f"affinity-arena-v1:roster:{seed}:{holdout}")
    names = HOLDOUT_NAMES if holdout else MAIN_NAMES
    moves = HOLDOUT_MOVES if holdout else MOVE_NAMES
    cycle = rng.sample(range(6), 6)
    offsets = rng.sample(range(1, 6), 3)
    types = list(range(6)) * 2
    rng.shuffle(types)
    copies = [0] * 6
    result = []
    for name, affinity in zip(names, types, strict=True):
        # Each affinity appears in exactly six moves across the roster: two
        # primary moves and four secondary moves. Its two creatures share one
        # secondary affinity and differ on the other. This provides repeated
        # observations without making their draft choices interchangeable.
        pair = offsets[copies[affinity] : copies[affinity] + 2]
        copies[affinity] += 1
        others = [cycle[(cycle.index(affinity) + offset) % 6] for offset in pair]
        moveset = [Move(moves[a], a, 50 if a == affinity else 36) for a in [affinity, *others]]
        rng.shuffle(moveset)
        result.append(Creature(name, affinity, tuple(moveset)))
    return tuple(result)


def generate_trial(seed: int, count: int = 20) -> dict:
    if not 1 <= count <= 20:
        raise ValueError("battle count must be between 1 and 20")
    chart = generate_chart(seed)
    rosters = (generate_roster(seed), generate_roster(seed, True))
    rng = random.Random(f"affinity-arena-v1:schedule:{seed}")
    battles = []
    for index in range(1, count + 1):
        roster = rosters[index > 15]
        for _ in range(1000):
            chosen = rng.sample(roster, 8)
            matchup = Matchup(tuple(chosen[:5]), tuple(chosen[5:]))
            best, values = solve_drafts(matchup, chart)
            if best[0] > 2100:
                break
        else:
            raise RuntimeError(f"cannot generate winnable battle {index} for seed {seed}")
        battles.append(
            {
                "index": index,
                "holdout": index > 15,
                **asdict(matchup),
                "oracle_value": best,
                "draft_values": [
                    {"team": list(team), "value": value} for team, value in values.items()
                ],
            }
        )
    return {"version": TRIAL_VERSION, "seed": seed, "chart": chart, "battles": battles}
