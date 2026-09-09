"""Cards, decks, and a 5-card / 7-card hand ranker."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

RANKS = "23456789TJQKA"
SUITS = "cdhs"
RANK_VALUE = {rank: index + 2 for index, rank in enumerate(RANKS)}

# High card .. straight flush. Tie-breakers follow in the rest of the tuple.
HIGH, PAIR, TWO_PAIR, TRIPS, STRAIGHT, FLUSH, FULL_HOUSE, QUADS, STRAIGHT_FLUSH = range(9)


def parse_card(text: str) -> tuple[int, int]:
    if len(text) != 2 or text[0] not in RANK_VALUE or text[1] not in SUITS:
        raise ValueError(f"bad card: {text}")
    return RANK_VALUE[text[0]], SUITS.index(text[1])


def format_card(card: tuple[int, int]) -> str:
    rank, suit = card
    return RANKS[rank - 2] + SUITS[suit]


def full_deck() -> list[tuple[int, int]]:
    return [(rank, suit) for rank in range(2, 15) for suit in range(4)]


def _straight_high(ranks: set[int]) -> int:
    if {14, 5, 4, 3, 2} <= ranks:
        return 5
    for high in range(14, 5, -1):
        if all(rank in ranks for rank in range(high, high - 5, -1)):
            return high
    return 0


def rank5(cards: list[tuple[int, int]]) -> tuple[int, ...]:
    if len(cards) != 5:
        raise ValueError("need 5 cards")
    ranks = sorted((rank for rank, _ in cards), reverse=True)
    flush = len({suit for _, suit in cards}) == 1
    counts = Counter(ranks)
    by_count = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    straight = _straight_high(set(ranks))
    if flush and straight:
        return (STRAIGHT_FLUSH, straight)
    if by_count[0][1] == 4:
        return (QUADS, by_count[0][0], by_count[1][0])
    if by_count[0][1] == 3 and by_count[1][1] == 2:
        return (FULL_HOUSE, by_count[0][0], by_count[1][0])
    if flush:
        return (FLUSH, *ranks)
    if straight:
        return (STRAIGHT, straight)
    if by_count[0][1] == 3:
        kickers = sorted((rank for rank, count in counts.items() if count == 1), reverse=True)
        return (TRIPS, by_count[0][0], *kickers)
    if by_count[0][1] == 2 and by_count[1][1] == 2:
        pair_hi, pair_lo = sorted((by_count[0][0], by_count[1][0]), reverse=True)
        return (TWO_PAIR, pair_hi, pair_lo, by_count[2][0])
    if by_count[0][1] == 2:
        kickers = sorted((rank for rank, count in counts.items() if count == 1), reverse=True)
        return (PAIR, by_count[0][0], *kickers)
    return (HIGH, *ranks)


def best_hand(cards: list[tuple[int, int]]) -> tuple[int, ...]:
    if len(cards) < 5:
        raise ValueError("need at least 5 cards")
    if len(cards) == 5:
        return rank5(cards)
    return max(rank5(list(combo)) for combo in combinations(cards, 5))


def category_name(rank: tuple[int, ...]) -> str:
    return (
        "high card",
        "pair",
        "two pair",
        "trips",
        "straight",
        "flush",
        "full house",
        "quads",
        "straight flush",
    )[rank[0]]
