#!/usr/bin/env python3
"""Formula 1 DB CLI and step helpers."""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("/opt/f1/formula_1.sqlite")
QUESTIONS_PATH = Path("/opt/f1/questions.json")
GOLD_PATH = Path("/opt/f1/gold.json")
LOG_PATH = Path("/opt/f1/queries.jsonl")
STEP_PATH = Path("/app/.step.txt")
QUESTION_PATH = Path("/app/question.md")
ANSWER_PATH = Path("/app/answer.json")
TRAJECTORY_PATH = Path("/logs/agent/trajectory.json")
REWARD_PATH = Path("/logs/verifier/reward.json")
ROW_LIMIT = 100
ALLOWED = re.compile(r"^\s*(SELECT|WITH|PRAGMA|EXPLAIN)\b", re.IGNORECASE | re.DOTALL)


def _rows_to_json(rows: list[tuple]) -> list:
    out = []
    for row in rows:
        item = []
        for value in row:
            if isinstance(value, bytes):
                value = value.decode("utf-8", "replace")
            item.append(value)
        out.append(item)
    return out


def cmd_query(sql: str) -> None:
    if not ALLOWED.match(sql or ""):
        print("Only SELECT, WITH, PRAGMA, or EXPLAIN is allowed.", file=sys.stderr)
        raise SystemExit(2)
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        cur = con.execute(sql)
        rows = cur.fetchmany(ROW_LIMIT + 1)
    finally:
        con.close()
    truncated = len(rows) > ROW_LIMIT
    rows = rows[:ROW_LIMIT]
    payload = _rows_to_json(rows)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    step = STEP_PATH.read_text().strip() if STEP_PATH.exists() else ""
    with LOG_PATH.open("a") as f:
        f.write(json.dumps({"step": step, "sql": sql[:2000]}) + "\n")
    print(json.dumps(payload, default=str))
    if truncated:
        print(f"(truncated to {ROW_LIMIT} rows)", file=sys.stderr)


def cmd_reset_log() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("")


def cmd_publish(index: str) -> None:
    n = int(index)
    questions = json.loads(QUESTIONS_PATH.read_text())
    item = questions[n - 1]
    STEP_PATH.write_text(str(n) + "\n")
    QUESTION_PATH.write_text(
        f"Question {n} of {len(questions)}\n\n{item['question']}\n"
    )
    if ANSWER_PATH.exists():
        ANSWER_PATH.unlink()


def _canon(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def gold_result(sql: str) -> list[list]:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        rows = con.execute(sql).fetchall()
    finally:
        con.close()
    return [[_canon(v) for v in row] for row in rows]


def normalize_answer(raw) -> list[list]:
    if isinstance(raw, dict) and "answer" in raw:
        raw = raw["answer"]
    if raw is None:
        return []
    if isinstance(raw, (str, int, float, bool)):
        return [[_canon(raw)]]
    if isinstance(raw, list):
        if not raw:
            return []
        if not isinstance(raw[0], (list, tuple)):
            return [[_canon(v)] for v in raw]
        return [[_canon(v) for v in row] for row in raw]
    return [[_canon(raw)]]


def answers_match(pred, gold_rows: list[list]) -> bool:
    pred_rows = normalize_answer(pred)
    gold_norm = [[_canon(v) for v in row] for row in gold_rows]
    if pred_rows == gold_norm:
        return True
    try:
        return sorted(map(tuple, pred_rows)) == sorted(map(tuple, gold_norm))
    except TypeError:
        return False


def _trajectory_metrics() -> tuple[int, int]:
    if not TRAJECTORY_PATH.exists():
        return 0, 0
    data = json.loads(TRAJECTORY_PATH.read_text())
    final = data.get("final_metrics") or {}
    tokens = int(final.get("total_prompt_tokens") or 0) + int(
        final.get("total_completion_tokens") or 0
    )
    tool_calls = 0
    for step in data.get("steps") or []:
        tool_calls += len(step.get("tool_calls") or [])
    if not tool_calls:
        tool_calls = int(final.get("total_steps") or 0)
    return tool_calls, tokens


def cmd_costs() -> None:
    step = STEP_PATH.read_text().strip() if STEP_PATH.exists() else ""
    db_queries = 0
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if not step or rec.get("step") == step:
                db_queries += 1
    tool_calls, tokens = _trajectory_metrics()
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    rewards = {}
    if REWARD_PATH.exists():
        try:
            rewards = json.loads(REWARD_PATH.read_text())
        except json.JSONDecodeError:
            rewards = {}
    rewards["db_queries"] = float(db_queries)
    rewards["tool_calls"] = float(tool_calls)
    rewards["tokens"] = float(tokens)
    REWARD_PATH.write_text(json.dumps(rewards) + "\n")


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit("usage: f1.py query|publish|reset-log|costs ...")
    cmd = argv[0]
    if cmd == "query":
        sql = argv[1] if len(argv) > 1 else sys.stdin.read()
        cmd_query(sql)
    elif cmd == "publish":
        if len(argv) < 2:
            raise SystemExit("usage: f1.py publish <1-based-index>")
        cmd_publish(argv[1])
    elif cmd == "reset-log":
        cmd_reset_log()
    elif cmd == "costs":
        cmd_costs()
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
