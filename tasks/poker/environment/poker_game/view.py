"""Public view: current hand only. Never print opponent hole cards until showdown."""

from __future__ import annotations

from .cards import format_card
from .engine import HERO, VILLAIN, Hand, Match, hole_text, legal_actions


def render(match: Match) -> str:
    hero = match.hero
    villain = match.villain
    hand = match.current
    if hand is not None:
        hero = hand.stacks[HERO]
        villain = hand.stacks[VILLAIN]
    lines = [
        "Heads-up no-limit Texas Hold'em",
        f"Hand {min(match.hand_index + 1, match.hands)} of {match.hands}",
        f"Your chips: {hero}",
        f"Opponent chips: {villain}",
        "Blinds: 5 / 10",
    ]
    if match.complete() and match.current is None:
        lines.append("Match over.")
        return "\n".join(lines) + "\n"
    if hand is None:
        lines.append("No hand is running.")
        return "\n".join(lines) + "\n"
    button = "you" if hand.button == HERO else "opponent"
    lines.append(f"Button: {button}")
    lines.append(f"Street: {hand.street}")
    lines.append(f"Your hand: {hole_text(hand.hole[HERO])}")
    board = " ".join(format_card(card) for card in hand.board) or "(none)"
    lines.append(f"Board: {board}")
    lines.append(f"Pot: {hand.pot}")
    if hand.over:
        lines.extend(_ending(hand))
        return "\n".join(lines) + "\n"
    actor = "you" if hand.to_act == HERO else "opponent"
    lines.append(f"To act: {actor}")
    if hand.to_act == HERO:
        lines.append(_action_help(hand))
    return "\n".join(lines) + "\n"


def _ending(hand: Hand) -> list[str]:
    lines = []
    if hand.showdown:
        lines.append(f"Opponent hand: {hole_text(hand.hole[VILLAIN])}")
        lines.append("Showdown.")
    elif hand.folded == HERO:
        lines.append("You folded.")
    else:
        lines.append("Opponent folded.")
    lines.append("Hand over. Stop.")
    return lines


def _action_help(hand: Hand) -> str:
    legal = legal_actions(hand)
    parts = []
    if "fold" in legal:
        parts.append("poker act fold")
    if "check" in legal:
        parts.append("poker act check")
    if "call" in legal:
        parts.append(f"poker act call  (put {legal['call']})")
    if "raise" in legal:
        parts.append(f"poker act raise {legal['raise']}  (raise to, min)")
    return "Legal: " + " | ".join(parts)
