"""Exploitable opponent: sticky caller who hates checking (GTO Wizard Fish knobs)."""

from __future__ import annotations

from .cards import best_hand, rank5
from .engine import Hand, legal_actions

# Same knobs as the GTO Wizard Fish profile: bonus for call, penalty for check.
CALL_BONUS = 0.04
CHECK_PENALTY = 0.06
RAISE_PENALTY = 0.12


def hand_strength(hand: Hand, player: int) -> float:
    hole = hand.hole[player]
    board = hand.board
    if not board:
        a, b = sorted((hole[0][0], hole[1][0]), reverse=True)
        suited = hole[0][1] == hole[1][1]
        if a == b:
            return 0.55 + a / 40
        score = 0.12 + a / 40 + b / 80
        if suited:
            score += 0.05
        if a - b <= 2:
            score += 0.04
        return min(score, 0.72)
    cards = hole + board
    if len(cards) == 5:
        rank = rank5(cards)
    else:
        rank = best_hand(cards)
    return min(0.2 + rank[0] * 0.12 + rank[1] / 100, 0.98)


def fish_action(hand: Hand) -> tuple[str, int | None]:
    """Choose fold/check/call/raise from legal actions. Deterministic."""
    legal = legal_actions(hand)
    if not legal:
        raise ValueError("no legal action")
    player = hand.to_act
    strength = hand_strength(hand, player)
    pot = max(hand.pot, 1)
    scores: dict[str, float] = {}
    if "fold" in legal:
        scores["fold"] = 0.0
    if "call" in legal:
        cost = legal["call"]
        scores["call"] = strength * pot - cost + CALL_BONUS * pot
    if "check" in legal:
        scores["check"] = strength * pot - CHECK_PENALTY * pot
    if "raise" in legal:
        min_to = legal["raise"]
        raise_to = min(
            max(min_to, hand.contrib[player] + max(pot // 2, min_to - hand.contrib[player])),
            hand.contrib[player] + hand.stacks[player],
        )
        cost = raise_to - hand.contrib[player]
        scores["raise"] = strength * (pot + cost) - cost - RAISE_PENALTY * pot
    action = max(scores, key=lambda name: (scores[name], _tie(name)))
    if action != "raise":
        return action, None
    min_to = legal["raise"]
    raise_to = min(
        max(min_to, hand.contrib[player] + max(hand.pot // 2, min_to - hand.contrib[player])),
        hand.contrib[player] + hand.stacks[player],
    )
    return "raise", raise_to


def _tie(action: str) -> int:
    return {"fold": 0, "check": 1, "call": 2, "raise": 3}[action]
