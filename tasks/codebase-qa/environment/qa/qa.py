#!/usr/bin/env python3
"""Codebase Q&A step helpers."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

QUESTIONS_PATH = Path("/opt/qa/questions.json")
GOLD_PATH = Path("/opt/qa/gold.json")
REFERENCE_PATH = Path("/opt/qa/reference.md")
STEP_PATH = Path("/app/.step.txt")
QUESTION_PATH = Path("/app/question.md")
ANSWER_PATH = Path("/app/answer.json")
TRAJECTORY_PATH = Path("/logs/agent/trajectory.json")
PI_LOG_PATH = Path("/logs/agent/pi.txt")
REWARD_PATH = Path("/logs/verifier/reward.json")
FILE_RE = re.compile(r"/data/repo/[^\s\"']+")
_REPO_PREFIX = "/data/repo"
_EXPLORE_TOKEN = re.compile(r"\b(?:rg|grep|find)\b")


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


def _agent_log() -> str:
    if TRAJECTORY_PATH.is_file():
        return TRAJECTORY_PATH.read_text()
    if PI_LOG_PATH.is_file():
        return PI_LOG_PATH.read_text(errors="replace")
    return ""


def _pi_tokens(text: str) -> int:
    total = 0
    for line in text.splitlines():
        if '"message_end"' not in line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "message_end":
            continue
        usage = (event.get("message") or {}).get("usage") or {}
        total += int(usage.get("totalTokens") or 0)
    return total


def _trajectory_metrics() -> tuple[int, int, int]:
    text = _agent_log()
    if not text:
        return 0, 0, 0
    files_opened = len(set(FILE_RE.findall(text)))
    if TRAJECTORY_PATH.is_file():
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
    tool_calls = text.count('"type":"tool_execution_start"')
    tool_calls += text.count('"type": "tool_execution_start"')
    return tool_calls, _pi_tokens(text), files_opened


def _tool_args(event: dict) -> dict | str:
    args = event.get("args")
    if args is None:
        args = event.get("arguments")
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
        except json.JSONDecodeError:
            return args
        return parsed if isinstance(parsed, dict) else args
    if isinstance(args, dict):
        return args
    return {}


def _bash_command(args: dict | str) -> str:
    if isinstance(args, str):
        return args
    return str(args.get("command") or args.get("cmd") or "")


def _read_path(args: dict | str) -> str:
    if isinstance(args, str):
        return args
    return str(args.get("path") or args.get("file") or args.get("file_path") or "")


def _is_repo_read(path: str) -> bool:
    if not path:
        return False
    if path == _REPO_PREFIX or path.startswith(_REPO_PREFIX + "/"):
        return True
    if path.startswith("data/repo/") or path.startswith("/data/repo/"):
        return True
    return False


def _pi_txt_metrics() -> tuple[float, float, float]:
    """Return (explore, reads, cost_usd) from Harbor Pi's pi.txt.

    explore — count of each rg/grep/find word in bash/shell tool commands
    reads — read tool calls whose path is under /data/repo
    cost_usd — sum of turn_end message.usage.cost.total
    """
    if not PI_LOG_PATH.is_file():
        return 0.0, 0.0, 0.0

    explore = 0
    reads = 0
    cost_usd = 0.0

    for line in PI_LOG_PATH.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        etype = event.get("type")
        if etype == "tool_execution_start":
            name = event.get("toolName") or event.get("name") or ""
            args = _tool_args(event)
            if name in ("bash", "shell", "exec"):
                explore += len(_EXPLORE_TOKEN.findall(_bash_command(args)))
            elif name == "read":
                if _is_repo_read(_read_path(args)):
                    reads += 1
        elif etype == "turn_end":
            usage = (event.get("message") or {}).get("usage") or {}
            cost = usage.get("cost") or {}
            total = cost.get("total")
            if total is not None:
                cost_usd += float(total)

    return float(explore), float(reads), float(cost_usd)


def cmd_costs() -> None:
    tool_calls, tokens, files_opened = _trajectory_metrics()
    explore, reads, cost_usd = _pi_txt_metrics()
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
    rewards["explore"] = explore
    rewards["reads"] = reads
    rewards["cost_usd"] = cost_usd
    REWARD_PATH.write_text(json.dumps(rewards) + "\n")


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit("usage: qa.py publish|write-reference|costs ...")
    cmd = argv[0]
    if cmd == "publish":
        if len(argv) < 2:
            raise SystemExit("usage: qa.py publish <1-based-index>")
        cmd_publish(argv[1])
    elif cmd == "write-reference":
        cmd_write_reference()
    elif cmd == "costs":
        cmd_costs()
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
