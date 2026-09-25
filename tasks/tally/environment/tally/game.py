#!/usr/bin/env python3
"""Tally engine: shuffle at env start, render view, settle a bet."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

STATE_DIR = Path("/opt/tally")
DECK_PATH = STATE_DIR / "deck.txt"
CURSOR_PATH = STATE_DIR / "cursor.txt"
LAST_PATH = STATE_DIR / "last.txt"
LOG_PATH = STATE_DIR / "log.jsonl"
VIEW_PATH = Path("/app/view.txt")
REWARD_PATH = Path("/logs/verifier/reward.txt")
REWARD_JSON = Path("/logs/verifier/reward.json")
PI_LOG_PATH = Path("/logs/agent/pi.txt")
COLORS = ("red", "blue", "yellow")
TURNS = 12


def _read_deck() -> list[str]:
    if not DECK_PATH.exists():
        raise SystemExit("deck missing; run shuffle first")
    return [line.strip() for line in DECK_PATH.read_text().splitlines() if line.strip()]


def _read_cursor() -> int:
    if not CURSOR_PATH.exists():
        return 0
    return int(CURSOR_PATH.read_text().strip() or "0")


def _write_cursor(n: int) -> None:
    CURSOR_PATH.write_text(f"{n}\n")


def cmd_shuffle() -> None:
    """Shuffle a fresh deck. Safe to call once per container."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if DECK_PATH.exists():
        return
    deck = list(COLORS) * 4
    random.shuffle(deck)
    DECK_PATH.write_text("\n".join(deck) + "\n")
    _write_cursor(0)
    if LAST_PATH.exists():
        LAST_PATH.unlink()
    if LOG_PATH.exists():
        LOG_PATH.unlink()


def cmd_view() -> None:
    """Write /app/view.txt for the current turn (last card only)."""
    deck = _read_deck()
    cursor = _read_cursor()
    turn = cursor + 1
    last = LAST_PATH.read_text().strip() if LAST_PATH.exists() else ""

    lines = [
        "Tally",
        f"Turn: {turn} of {TURNS}",
        f"Cards left to bet this game: {max(0, TURNS - cursor)}",
    ]
    if last:
        lines.append(f"Last card: {last}")
    else:
        lines.append("Last card: (none yet)")
    lines.append("")
    lines.append("Bet the color of the next card.")
    lines.append('Write {"color": "red"|"blue"|"yellow"} to /app/bet.json')

    VIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    VIEW_PATH.write_text("\n".join(lines) + "\n")

    # Defensive: never print deck to stdout.
    _ = deck


def cmd_score(bet_path: str) -> None:
    """Settle /app/bet.json against the next card; write reward 0 or 1."""
    deck = _read_deck()
    cursor = _read_cursor()
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)

    if cursor >= TURNS or cursor >= len(deck):
        REWARD_PATH.write_text("0\n")
        raise SystemExit("no cards left to score")

    path = Path(bet_path)
    color = ""
    try:
        data = json.loads(path.read_text())
        color = str(data.get("color", "")).strip().lower()
    except (OSError, json.JSONDecodeError, TypeError, AttributeError):
        color = ""

    drawn = deck[cursor]
    hit = 1 if color in COLORS and color == drawn else 0

    LAST_PATH.write_text(drawn + "\n")
    _write_cursor(cursor + 1)
    with LOG_PATH.open("a") as f:
        f.write(
            json.dumps(
                {
                    "turn": cursor + 1,
                    "bet": color,
                    "drawn": drawn,
                    "hit": hit,
                }
            )
            + "\n"
        )

    REWARD_PATH.write_text(f"{hit}\n")
    text = PI_LOG_PATH.read_text(errors="replace") if PI_LOG_PATH.is_file() else ""
    tool_calls = text.count('"type":"tool_execution_start"')
    tool_calls += text.count('"type": "tool_execution_start"')
    tokens = 0
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
        tokens += int(usage.get("totalTokens") or 0)
    REWARD_JSON.write_text(
        json.dumps(
            {"reward": hit, "tool_calls": tool_calls, "tokens": tokens}
        )
        + "\n"
    )
    print(f"drawn={drawn} bet={color or '(invalid)'} hit={hit}")


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit("usage: game.py shuffle|view|score <bet.json>")
    cmd = argv[0]
    if cmd == "shuffle":
        cmd_shuffle()
    elif cmd == "view":
        cmd_view()
    elif cmd == "score":
        if len(argv) < 2:
            raise SystemExit("usage: game.py score <bet.json>")
        cmd_score(argv[1])
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
