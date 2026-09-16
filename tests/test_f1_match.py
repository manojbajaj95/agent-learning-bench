#!/usr/bin/env python3
"""Strip-and-compare Formula 1 verifier."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "f1", ROOT / "tasks" / "database-analytics" / "environment" / "f1" / "f1.py"
)
f1 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(f1)


def test_strip_scalar() -> None:
    gold = [["Fernando Alonso"]]
    assert f1.answers_match("Fernando Alonso", gold)
    assert f1.answers_match({"answer": "  Fernando Alonso  "}, gold)
    assert not f1.answers_match("Lewis Hamilton", gold)


def test_split_name_fails() -> None:
    gold = [["Fernando Alonso"]]
    assert not f1.answers_match(["Fernando", "Alonso"], gold)


def test_null_equals_empty() -> None:
    assert f1.answers_match(None, [[None]])
    assert f1.answers_match({"answer": None}, [])


def test_list_order_is_exact() -> None:
    gold = [["sato"], ["davidson"], ["vettel"]]
    assert f1.answers_match(["sato", "davidson", "vettel"], gold)
    assert not f1.answers_match(["vettel", "sato", "davidson"], gold)


def test_extra_name_fails() -> None:
    gold = [["sato"], ["davidson"], ["vettel"], ["sutil"], ["fisichella"]]
    pred = ["coulthard", "fisichella", "vettel", "sutil", "davidson", "sato"]
    assert not f1.answers_match(pred, gold)


def test_partial_list_fails() -> None:
    gold = [["Polish"], ["German"], ["British"]]
    assert not f1.answers_match("Polish", gold)


def test_one_row_collapses() -> None:
    gold = [["UK", "Kent"]]
    assert f1.answers_match(["UK", "Kent"], gold)
    assert not f1.answers_match(["UK", "Brands Hatch", "Kent"], gold)


def test_shape_formats_match_gold_sql() -> None:
    data = ROOT / "tasks" / "database-analytics" / "environment" / "data"
    questions = {q["question_id"]: q for q in json.loads((data / "questions.json").read_text())}
    gold = {g["question_id"]: g for g in json.loads((data / "gold.json").read_text())}
    con = sqlite3.connect(f"file:{data / 'formula_1.sqlite'}?mode=ro", uri=True)

    assert questions[852]["format"] == "a JSON integer (not a string)"
    assert "oldest year first" in questions[848]["format"]
    assert "Z to A" in questions[883]["format"]
    assert "two decimal digits, rounded down" in questions[909]["format"]

    years = [r[0] for r in con.execute(gold[848]["SQL"]).fetchall()]
    assert years == sorted(years)
    names = [r[0] for r in con.execute(gold[883]["SQL"]).fetchall()]
    assert names == sorted(names, reverse=True)
    pct = con.execute(gold[909]["SQL"]).fetchone()[0]
    assert pct == 52.17


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("ok")
