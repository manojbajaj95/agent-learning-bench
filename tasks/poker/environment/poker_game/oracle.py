"""Value-bet exploit of the Fish: bet made hands, skip bluffs, do not fold pairs cheap."""

from __future__ import annotations

from .cards import PAIR, TWO_PAIR, best_hand
from .engine import BB, HERO, Hand, legal_actions
from .fish import hand_strength


def oracle_action(hand: Hand) -> tuple[str, int | None]:
    legal = legal_actions(hand)
    if not legal:
        raise ValueError("no legal action")
    strength = hand_strength(hand, HERO)
    rank = None
    if len(hand.board) >= 3:
        rank = best_hand(hand.hole[HERO] + hand.board)
        made = rank[0] >= PAIR
        strong = rank[0] >= TWO_PAIR
    else:
        ranks = (hand.hole[HERO][0][0], hand.hole[HERO][1][0])
        made = ranks[0] == ranks[1] or min(ranks) >= 13
        strong = ranks[0] == ranks[1] and ranks[0] >= 12
    to_call = legal.get("call", 0)
    cheap = to_call <= max(BB, hand.pot // 2)
    if "fold" in legal and not made and not cheap:
        return "fold", None
    if "raise" in legal and made and (to_call == 0 or strong or cheap):
        min_to = legal["raise"]
        size = hand.contrib[HERO] + max(BB, min(max(hand.pot // 2, BB), 4 * BB))
        raise_to = min(max(min_to, size), hand.contrib[HERO] + hand.stacks[HERO])
        return "raise", raise_to
    if "call" in legal and (made or cheap or strength >= 0.4):
        return "call", None
    if "check" in legal:
        return "check", None
    return "fold", None
