"""Locked match state. Agent sees /app/view.txt only."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from .engine import (
    HERO,
    START_STACK,
    Match,
    apply_action,
    finish_hand,
    legal_actions,
    start_hand,
)
from .fish import fish_action
from .view import render

PRIVATE = Path("/opt/poker")
PUBLIC = Path("/app")
VERIFIER = Path("/logs/verifier")
HANDS = 100
SEED = 1


def atomic_write(path: Path, text: str, mode: int = 0o600) -> None:
    fd, name = tempfile.mkstemp(prefix=".poker-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _cards(value) -> list[tuple[int, int]]:
    return [tuple(card) for card in value]


def _hand_from_json(data: dict):
    from .engine import Hand

    return Hand(
        hole=[_cards(player) for player in data["hole"]],
        board=_cards(data["board"]),
        deck=_cards(data["deck"]),
        street=data["street"],
        pot=data["pot"],
        contrib=list(data["contrib"]),
        stacks=list(data["stacks"]),
        to_act=data["to_act"],
        button=data["button"],
        current_bet=data["current_bet"],
        last_raise=data["last_raise"],
        must_act=list(data["must_act"]),
        over=data["over"],
        folded=data["folded"],
        showdown=data["showdown"],
    )


def _match_to_json(match: Match) -> dict:
    return {
        "seed": match.seed,
        "hands": match.hands,
        "hero": match.hero,
        "villain": match.villain,
        "hand_index": match.hand_index,
        "button": match.button,
        "current": None if match.current is None else asdict(match.current),
    }


def _match_from_json(data: dict) -> Match:
    current = data.get("current")
    return Match(
        seed=data["seed"],
        hands=data["hands"],
        hero=data["hero"],
        villain=data["villain"],
        hand_index=data["hand_index"],
        button=data["button"],
        current=None if current is None else _hand_from_json(current),
    )


class Runtime:
    def __init__(self, private: Path = PRIVATE, public: Path = PUBLIC, verifier: Path = VERIFIER):
        self.private = private
        self.public = public
        self.verifier = verifier

    @contextmanager
    def locked(self):
        self.private.mkdir(parents=True, exist_ok=True)
        with (self.private / "lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def load(self) -> Match:
        path = self.private / "match.json"
        if not path.exists():
            return Match(seed=SEED, hands=HANDS)
        return _match_from_json(json.loads(path.read_text()))

    def save(self, match: Match) -> None:
        atomic_write(self.private / "match.json", json.dumps(_match_to_json(match)) + "\n")

    def publish(self, match: Match) -> str:
        view = render(match)
        self.public.mkdir(parents=True, exist_ok=True)
        atomic_write(self.public / "view.txt", view, 0o644)
        return view

    def start(self, index: int) -> str:
        with self.locked():
            match = self.load()
            if match.complete() and match.current is None:
                return self.publish(match)
            if match.current is not None:
                if match.hand_index + 1 == index:
                    return self.publish(match)
                raise ValueError("hand already in progress")
            if match.hand_index + 1 != index:
                raise ValueError(f"expected hand {match.hand_index + 1}")
            match = start_hand(match)
            match = self._fish_until_hero(match)
            self.save(match)
            return self.publish(match)

    def command(self, argv: list[str]) -> str:
        with self.locked():
            if not argv:
                raise ValueError("use status or act fold|check|call|raise [amount]")
            if argv[0] == "status":
                return self.publish(self.load())
            if argv[0] != "act":
                raise ValueError("use status or act fold|check|call|raise [amount]")
            return self._act(argv[1:])

    def _act(self, argv: list[str]) -> str:
        match = self.load()
        if match.current is None or match.current.over:
            raise ValueError("hand is over")
        if match.current.to_act != HERO:
            raise ValueError("not your turn")
        if not argv:
            raise ValueError("act fold|check|call|raise [amount]")
        action = argv[0].lower()
        raise_to = None
        if action == "raise":
            if len(argv) > 1:
                try:
                    raise_to = int(argv[1])
                except ValueError as exc:
                    raise ValueError("raise amount must be an integer") from exc
        elif len(argv) > 1:
            raise ValueError("only raise takes an amount")
        apply_action(match.current, action, raise_to)
        actions = self.private / "hero_actions.txt"
        count = int(actions.read_text().strip() or "0") if actions.exists() else 0
        actions.write_text(f"{count + 1}\n")
        if not match.current.over:
            match = self._fish_until_hero(match)
        self.save(match)
        return self.publish(match)

    def _fish_until_hero(self, match: Match) -> Match:
        hand = match.current
        assert hand is not None
        while not hand.over and hand.to_act != HERO and legal_actions(hand):
            action, raise_to = fish_action(hand)
            apply_action(hand, action, raise_to)
        return match

    def settle(self, index: int) -> dict:
        with self.locked():
            match = self.load()
            if match.current is None:
                if match.complete() and index >= match.hand_index:
                    return self._emit(match, index)
                raise ValueError(f"cannot settle hand {index}")
            if match.hand_index + 1 != index:
                raise ValueError(f"cannot settle hand {index}")
            if not match.current.over:
                self._force_end(match)
            if match.current is not None and match.current.over:
                match = finish_hand(match)
            chips = match.hero
            if not match.complete() and match.current is None:
                match = start_hand(match)
                match = self._fish_until_hero(match)
            self.save(match)
            return self._emit(match, index, chips)

    def _emit(self, match: Match, index: int, chips: int | None = None) -> dict:
        if chips is None:
            chips = match.hero
        actions_path = self.private / "hero_actions.txt"
        env_actions = (
            int(actions_path.read_text().strip() or "0") if actions_path.exists() else 0
        )
        actions_path.write_text("0\n")
        record = {
            "reward": chips,
            "chips": chips,
            "profit": chips - START_STACK,
            "hands_done": min(index, match.hand_index),
            "completed": 1,
            "env_actions": env_actions,
        }
        self.verifier.mkdir(parents=True, exist_ok=True)
        atomic_write(self.verifier / "reward.txt", f"{chips}\n", 0o644)
        atomic_write(self.verifier / "reward.json", json.dumps(record) + "\n", 0o644)
        return record

    def _force_end(self, match: Match) -> None:
        hand = match.current
        assert hand is not None
        while not hand.over:
            legal = legal_actions(hand)
            if hand.to_act != HERO:
                match = self._fish_until_hero(match)
                hand = match.current
                if hand is None or hand.over:
                    return
                legal = legal_actions(hand)
            if "fold" in legal:
                apply_action(hand, "fold")
            elif "check" in legal:
                apply_action(hand, "check")
            elif "call" in legal:
                apply_action(hand, "call")
            else:
                raise ValueError("hand did not finish")
