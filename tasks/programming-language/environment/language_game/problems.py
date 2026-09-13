"""Problem contracts and mathematical expected outputs, independent of the interpreter."""

from __future__ import annotations

from itertools import product


def description(family: str, parameter: object) -> tuple[str, str]:
    descriptions = {
        "constant": ("Constant output", f"No input. Output the single integer {parameter}."),
        "echo": ("Echo", "Input: one integer x in 0..15. Output x."),
        "duplicate": ("Print twice", "Input: x in 0..15. Output x twice."),
        "overwrite": (
            "Keep the newest value",
            "Input: a, b, each in 0..15. Output only b.",
        ),
        "successor": ("Successor", "Input: x in 0..14. Output x + 1."),
        "add": ("Add", "Input: a, b, each in 0..7. Output a + b."),
        "affine": (
            "Scale and offset",
            f"Input: x in 0..3. Output {parameter[0]} * x + {parameter[1]}."
            if isinstance(parameter, list)
            else "",
        ),
        "equals": (
            "Equality indicator",
            f"Input: x in 0..15. Output 1 if x equals {parameter}, otherwise 0.",
        ),
        "permute": (
            "Reorder three values",
            f"Input: three integers, each in 0..15. Output the values at input positions "
            f"{parameter} in that order. Input positions are numbered from 1.",
        ),
        "range": (
            "Counting sequence",
            f"Input: n in 0..8. Output n integers: {parameter}, {parameter} + 1, "
            f"..., {parameter} + n - 1. Output nothing when n = 0.",
        ),
        "repeat": (
            "Repeat a transformed value",
            f"Input: n in 0..5, v in 0..10. Output v + {parameter}, repeated n times.",
        ),
        "sum": (
            "Sum with offset",
            f"Input: n in 0..5, followed by n integers each in 0..2. "
            f"Output their sum + {parameter}. For n = 0, output {parameter}.",
        ),
        "select": (
            "Select a value",
            "Input: x, a, b, each in 0..15. Output a if x = 0, otherwise b.",
        ),
        "count": (
            "Count nonzero values",
            "Input: n in 0..5, followed by n integers each in 0..15. "
            "Output the number of nonzero values among those n integers.",
        ),
        "prefix": (
            "Running totals",
            "Input: n in 0..5, followed by n integers each in 0..2. "
            "Output their n successive prefix sums. Output nothing when n = 0.",
        ),
        "triangular": (
            "Triangular number",
            "Input: n in 0..5. Output 1 + 2 + ... + n. For n = 0, output 0.",
        ),
        "stream_echo": (
            "Echo a stream",
            "Input: n in 0..5, followed by n integers each in 0..15. "
            "Output those n values in order. Output nothing when n = 0.",
        ),
        "totals": (
            "Echo and total",
            "Input: n in 0..5, followed by n integers each in 0..2. "
            "Output those n values in order, then their sum. For n = 0, output 0.",
        ),
        "pair_sums": (
            "Sum successive pairs",
            "Input: n in 0..4, followed by n pairs a, b, each value in 0..7. "
            "Output the sum of each pair in order. Output nothing when n = 0.",
        ),
        "dot": (
            "Sum of products",
            "Input: n in 0..3, followed by n pairs a, b, each value in 0..2. "
            "Output the sum of the n products a * b. For n = 0, output 0.",
        ),
    }
    return descriptions[family]


def expected(family: str, parameter: object, inputs: list[int]) -> list[int]:
    if family == "constant":
        return [parameter]
    if family == "echo":
        return inputs[:]
    if family == "duplicate":
        return inputs * 2
    if family == "overwrite":
        return inputs[1:]
    if family == "successor":
        return [inputs[0] + 1]
    if family == "add":
        return [sum(inputs)]
    if family == "affine":
        return [parameter[0] * inputs[0] + parameter[1]]
    if family == "equals":
        return [int(inputs[0] == parameter)]
    if family == "permute":
        return [inputs[i - 1] for i in parameter]
    if family == "range":
        return list(range(parameter, parameter + inputs[0]))
    if family == "repeat":
        return [inputs[1] + parameter] * inputs[0]
    if family == "sum":
        return [sum(inputs[1:]) + parameter]
    if family == "select":
        return [inputs[1] if inputs[0] == 0 else inputs[2]]
    if family == "count":
        return [sum(x != 0 for x in inputs[1:])]
    if family == "prefix":
        return [sum(inputs[1:i]) for i in range(2, len(inputs) + 1)]
    if family == "triangular":
        return [inputs[0] * (inputs[0] + 1) // 2]
    if family == "stream_echo":
        return inputs[1:]
    if family == "totals":
        return inputs[1:] + [sum(inputs[1:])]
    if family == "pair_sums":
        return [inputs[i] + inputs[i + 1] for i in range(1, len(inputs), 2)]
    if family == "dot":
        return [sum(inputs[i] * inputs[i + 1] for i in range(1, len(inputs), 2))]
    raise ValueError(f"unknown problem family: {family}")


def cases(family: str, parameter: object, rng) -> list[list[int]]:
    """Exhaust small domains; cover edges plus sampled cases for larger domains."""
    if family == "constant":
        return [[]]
    sizes = {
        "echo": 16,
        "duplicate": 16,
        "successor": 15,
        "affine": 4,
        "equals": 16,
        "range": 9,
        "triangular": 6,
    }
    if family in sizes:
        return [[x] for x in range(sizes[family])]
    if family == "add":
        return [list(x) for x in product(range(8), repeat=2)]
    if family == "overwrite":
        return [list(x) for x in product(range(16), repeat=2)]
    if family == "repeat":
        return [list(x) for x in product(range(6), range(11))]
    if family in ("sum", "prefix", "totals"):
        return [[n, *xs] for n in range(6) for xs in product(range(3), repeat=n)]
    if family in ("count", "stream_echo"):
        edges = [[0], [1, 0], [1, 15], [5, 0, 0, 0, 0, 0], [5, 15, 15, 15, 15, 15], [3, 1, 0, 2]]
        return edges + [
            [n, *[rng.randrange(16) for _ in range(n)]]
            for n in (rng.randrange(6) for _ in range(60))
        ]
    if family in ("permute", "select"):
        edges = [list(xs) for xs in product((0, 1, 15), repeat=3)]
        return edges + [[rng.randrange(16) for _ in range(3)] for _ in range(60)]
    if family == "dot":
        return [[n, *xs] for n in range(4) for xs in product(range(3), repeat=2 * n)]
    if family == "pair_sums":
        edges = [[0], [1, 0, 0], [1, 7, 7], [4, *([7, 7] * 4)], [3, 7, 0, 0, 1, 2, 3]]
        return edges + [
            [n, *[rng.randrange(8) for _ in range(2 * n)]]
            for n in (rng.randrange(5) for _ in range(60))
        ]
    raise ValueError(f"unknown problem family: {family}")
