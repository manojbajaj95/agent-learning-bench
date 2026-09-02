#!/usr/bin/env python3
"""Corpus step helpers."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

QUESTIONS_PATH = Path("/opt/corpus/questions.json")
GOLD_PATH = Path("/opt/corpus/gold.json")
REFERENCE_PATH = Path("/opt/corpus/reference.md")
STEP_PATH = Path("/app/.step.txt")
QUESTION_PATH = Path("/app/question.md")
ANSWER_PATH = Path("/app/answer.json")
TRAJECTORY_PATH = Path("/logs/agent/trajectory.json")
REWARD_PATH = Path("/logs/verifier/reward.json")
FILE_RE = re.compile(r"/data/corpus/[^\s\"']+")


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


def cmd_write_reference() -> None:
    n = int(STEP_PATH.read_text().strip())
    gold = json.loads(GOLD_PATH.read_text())[n - 1]
    REFERENCE_PATH.write_text(f"# Gold answer for question {n}\n\n{gold['answer']}\n")
    REFERENCE_PATH.chmod(0o600)


def _trajectory_metrics() -> tuple[int, int, int]:
    if not TRAJECTORY_PATH.exists():
        return 0, 0, 0
    text = TRAJECTORY_PATH.read_text()
    files_opened = len(set(FILE_RE.findall(text)))
    data = json.loads(text)
    final = data.get("final_metrics") or {}
    tokens = int(final.get("total_prompt_tokens") or 0) + int(
        final.get("total_completion_tokens") or 0
    )
    tool_calls = 0
    for step in data.get("steps") or []:
        tool_calls += len(step.get("tool_calls") or [])
    if not tool_calls:
        tool_calls = int(final.get("total_steps") or 0)
    return tool_calls, tokens, files_opened


def cmd_costs() -> None:
    tool_calls, tokens, files_opened = _trajectory_metrics()
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    rewards = {}
    if REWARD_PATH.exists():
        try:
            rewards = json.loads(REWARD_PATH.read_text())
        except json.JSONDecodeError:
            rewards = {}
    rewards["tool_calls"] = float(tool_calls)
    rewards["tokens"] = float(tokens)
    rewards["files_opened"] = float(files_opened)
    REWARD_PATH.write_text(json.dumps(rewards) + "\n")


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit("usage: corpus.py publish|write-reference|costs ...")
    cmd = argv[0]
    if cmd == "publish":
        if len(argv) < 2:
            raise SystemExit("usage: corpus.py publish <1-based-index>")
        cmd_publish(argv[1])
    elif cmd == "write-reference":
        cmd_write_reference()
    elif cmd == "costs":
        cmd_costs()
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
