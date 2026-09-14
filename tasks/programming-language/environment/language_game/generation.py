"""Versioned named RNG streams, following Affinity Arena's generation convention."""

from __future__ import annotations

import random
from dataclasses import asdict
from itertools import permutations

from .engine import OPERATIONS, VERSION, Language
from .problems import cases, description, expected

MODES = ("hidden", "partial")
LOCAL_CALLS = 64
SUBMISSIONS = 6


def rng_for(seed: int, stream: str) -> random.Random:
    return random.Random(f"programming-language-v{VERSION}:{stream}:{seed}")


def generate_language(seed: int) -> Language:
    rng = rng_for(seed, "language")
    return Language(
        "".join(rng.sample(OPERATIONS, len(OPERATIONS))),
        rng.choice((16, 32, 256)),
        rng.choice((8, 16, 32)),
        rng.choice((False, True)),
        rng.choice(("replace", "add")),
        rng.choice(("preserve", "clear")),
        rng.choice(("manual", "consume")),
    )


def generate_trial(seed: int, visibility: str = "hidden") -> dict:
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if visibility not in MODES:
        raise ValueError("visibility must be hidden or partial")
    rng = rng_for(seed, "problems")
    # Establish reusable idioms, then combine them in genuinely different jobs.
    # No family repeats. The final eight are not difficulty-matched to the first twelve.
    schedule = [
        ("constant", rng.randrange(1, 8), "foundation"),
        ("echo", None, "foundation"),
        ("duplicate", None, "foundation"),
        ("overwrite", None, "foundation"),
        ("successor", None, "foundation"),
        (
            "permute",
            list(rng.choice([p for p in permutations((1, 2, 3)) if p != (1, 2, 3)])),
            "foundation",
        ),
        ("add", None, "practice"),
        ("repeat", rng.randrange(4), "practice"),
        ("range", rng.randrange(4), "practice"),
        ("sum", rng.randrange(4), "practice"),
        ("equals", rng.randrange(1, 15), "practice"),
        ("affine", rng.choice([[2, 1], [2, 2], [3, 1], [3, 2]]), "practice"),
    ]
    schedule_rng = rng_for(seed, "schedule")
    for phase, families in (
        ("transfer", ["stream_echo", "totals", "select", "count"]),
        ("holdout", ["pair_sums", "prefix", "dot", "triangular"]),
    ):
        schedule_rng.shuffle(families)
        schedule.extend((family, None, phase) for family in families)
    problems = []
    for index, (family, parameter, phase) in enumerate(schedule, 1):
        public_rng = rng_for(seed, f"examples:{index}")
        candidates = cases(family, parameter, public_rng)
        if family == "equals":
            # Reserve the only positive case for grading; examples remain disjoint.
            candidates = [xs for xs in candidates if xs != [parameter]]
        examples = public_rng.sample(candidates, min(2, len(candidates)))
        hidden_rng = rng_for(seed, f"hidden-tests:{index}")
        hidden = cases(family, parameter, hidden_rng)
        # Unique tests with equal weight. The no-input constant has only one possible case.
        hidden = sorted({tuple(xs) for xs in hidden if xs not in examples or family == "constant"})
        hidden_rng.shuffle(hidden)
        title, statement = description(family, parameter)

        def pair(xs, family=family, parameter=parameter):
            return {"input": list(xs), "output": expected(family, parameter, list(xs))}

        problems.append(
            {
                "index": index,
                "family": family,
                "parameter": parameter,
                "phase": phase,
                "public": {
                    "id": f"problem-{index:02d}",
                    "title": title,
                    "statement": statement,
                    "examples": [pair(xs) for xs in examples],
                },
                "hidden_tests": [pair(xs) for xs in hidden],
            }
        )
    return {
        "version": VERSION,
        "seed": seed,
        "visibility": visibility,
        "language": asdict(generate_language(seed)),
        "problems": problems,
    }
