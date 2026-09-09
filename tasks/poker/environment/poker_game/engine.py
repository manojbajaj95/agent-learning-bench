"""Heads-up no-limit Hold'em. Two players, one pot, stacks persist."""

from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random

from .cards import best_hand, format_card, full_deck

HERO = 0
VILLAIN = 1
SB = 5
BB = 10
START_STACK = 1000
STREETS = ("preflop", "flop", "turn", "river")


def other(player: int) -> int:
    return 1 - player


@dataclass
class Hand:
    hole: list[list[tuple[int, int]]]
    board: list[tuple[int, int]]
    deck: list[tuple[int, int]]
    street: str
    pot: int
    contrib: list[int]
    stacks: list[int]
    to_act: int
    button: int
    current_bet: int
    last_raise: int
    must_act: list[int]
    over: bool
    folded: int | None
    showdown: bool


@dataclass
class Match:
    seed: int
    hands: int
    hero: int = START_STACK
    villain: int = START_STACK
    hand_index: int = 0
    button: int = HERO
    current: Hand | None = None

    def busted(self) -> bool:
        return self.hero <= 0 or self.villain <= 0

    def complete(self) -> bool:
        return self.hand_index >= self.hands or self.busted()


def _deal(deck: list[tuple[int, int]], n: int) -> list[tuple[int, int]]:
    cards = deck[:n]
    del deck[:n]
    return cards


def start_hand(match: Match) -> Match:
    if match.current is not None:
        raise ValueError("hand already in progress")
    if match.complete():
        raise ValueError("match is over")
    rng = Random(match.seed + 1_000_003 * (match.hand_index + 1))
    deck = full_deck()
    rng.shuffle(deck)
    hole = [_deal(deck, 2), _deal(deck, 2)]
    stacks = [match.hero, match.villain]
    button = match.button
    bb_seat = other(button)
    contrib = [0, 0]
    sb_post = min(SB, stacks[button])
    bb_post = min(BB, stacks[bb_seat])
    stacks[button] -= sb_post
    stacks[bb_seat] -= bb_post
    contrib[button] = sb_post
    contrib[bb_seat] = bb_post
    hand = Hand(
        hole=hole,
        board=[],
        deck=deck,
        street="preflop",
        pot=sb_post + bb_post,
        contrib=contrib,
        stacks=stacks,
        to_act=button,
        button=button,
        current_bet=max(contrib),
        last_raise=BB,
        must_act=[button] if stacks[button] > 0 else [],
        over=False,
        folded=None,
        showdown=False,
    )
    if stacks[button] == 0 or stacks[bb_seat] == 0:
        if contrib[button] != contrib[bb_seat] and stacks[button] > 0:
            hand.to_act = button
            hand.must_act = [button]
        else:
            _runout(hand)
    elif not hand.must_act:
        _runout(hand)
    return replace(match, current=hand)


def legal_actions(hand: Hand) -> dict[str, int]:
    if hand.over or not hand.must_act:
        return {}
    player = hand.to_act
    to_call = max(0, hand.current_bet - hand.contrib[player])
    stack = hand.stacks[player]
    actions: dict[str, int] = {}
    if to_call > 0:
        actions["fold"] = 0
        actions["call"] = min(to_call, stack)
    else:
        actions["check"] = 0
    min_to = _min_raise_to(hand, player)
    max_to = hand.contrib[player] + stack
    if stack > to_call and min_to <= max_to:
        actions["raise"] = min_to
    return actions


def _min_raise_to(hand: Hand, player: int) -> int:
    return max(hand.current_bet + max(hand.last_raise, BB), hand.contrib[player] + 1)


def apply_action(hand: Hand, action: str, raise_to: int | None = None) -> Hand:
    if hand.over:
        raise ValueError("hand is over")
    action = action.lower()
    legal = legal_actions(hand)
    if action not in legal:
        raise ValueError(f"illegal action: {action}")
    player = hand.to_act
    bb_seat = other(hand.button)
    if action == "fold":
        hand.folded = player
        _award(hand, other(player))
        return hand
    if action == "check":
        _done_acting(hand, player)
        return _advance(hand)
    if action == "call":
        _put(hand, player, legal["call"])
        limp = (
            hand.street == "preflop"
            and player == hand.button
            and hand.contrib[player] == hand.contrib[bb_seat]
            and hand.stacks[bb_seat] > 0
            and hand.current_bet == BB
        )
        _done_acting(hand, player)
        if limp:
            hand.must_act = [bb_seat]
            hand.to_act = bb_seat
            return hand
        return _advance(hand)
    min_to = legal["raise"]
    max_to = hand.contrib[player] + hand.stacks[player]
    if raise_to is None:
        raise_to = min_to
    if raise_to < min_to and raise_to < max_to:
        raise ValueError(f"raise must be to at least {min_to}")
    if raise_to > max_to:
        raise ValueError(f"raise cannot exceed {max_to}")
    increment = raise_to - hand.current_bet
    _put(hand, player, raise_to - hand.contrib[player])
    if increment >= max(hand.last_raise, BB):
        hand.last_raise = increment
    hand.current_bet = hand.contrib[player]
    hand.must_act = [other(player)] if hand.stacks[other(player)] > 0 else []
    return _advance(hand)


def _put(hand: Hand, player: int, chips: int) -> None:
    chips = min(max(chips, 0), hand.stacks[player])
    hand.stacks[player] -= chips
    hand.contrib[player] += chips
    hand.pot += chips


def _done_acting(hand: Hand, player: int) -> None:
    hand.must_act = [seat for seat in hand.must_act if seat != player]


def _advance(hand: Hand) -> Hand:
    if hand.over:
        return hand
    if _all_in_settled(hand):
        _runout(hand)
        return hand
    if not hand.must_act:
        return _next_street(hand)
    hand.to_act = hand.must_act[0]
    return hand


def _all_in_settled(hand: Hand) -> bool:
    if hand.folded is not None:
        return False
    if hand.stacks[0] > 0 and hand.stacks[1] > 0:
        return False
    return all(
        hand.stacks[seat] == 0 or hand.contrib[seat] == max(hand.contrib)
        for seat in (HERO, VILLAIN)
    )


def _next_street(hand: Hand) -> Hand:
    if hand.street == "river":
        _showdown(hand)
        return hand
    nxt = STREETS[STREETS.index(hand.street) + 1]
    deal = 3 if nxt == "flop" else 1
    hand.street = nxt
    hand.board.extend(_deal(hand.deck, deal))
    hand.contrib = [0, 0]
    hand.current_bet = 0
    hand.last_raise = BB
    first = other(hand.button)
    if hand.stacks[0] == 0 or hand.stacks[1] == 0:
        _runout(hand)
        return hand
    hand.must_act = [first, hand.button]
    hand.to_act = first
    return hand


def _return_unmatched(hand: Hand) -> None:
    extra = abs(hand.contrib[0] - hand.contrib[1])
    if extra == 0:
        return
    player = 0 if hand.contrib[0] > hand.contrib[1] else 1
    hand.contrib[player] -= extra
    hand.stacks[player] += extra
    hand.pot -= extra


def _runout(hand: Hand) -> None:
    _return_unmatched(hand)
    if not hand.board:
        hand.board.extend(_deal(hand.deck, 3))
    if len(hand.board) == 3:
        hand.board.extend(_deal(hand.deck, 1))
    if len(hand.board) == 4:
        hand.board.extend(_deal(hand.deck, 1))
    hand.street = "river"
    _showdown(hand)


def _award(hand: Hand, winner: int) -> None:
    hand.over = True
    hand.stacks[winner] += hand.pot
    hand.pot = 0


def _showdown(hand: Hand) -> None:
    hand.over = True
    hand.showdown = True
    hero = best_hand(hand.hole[HERO] + hand.board)
    villain = best_hand(hand.hole[VILLAIN] + hand.board)
    if hero > villain:
        hand.stacks[HERO] += hand.pot
    elif villain > hero:
        hand.stacks[VILLAIN] += hand.pot
    else:
        half, rem = divmod(hand.pot, 2)
        hand.stacks[HERO] += half
        hand.stacks[VILLAIN] += half + rem
    hand.pot = 0


def finish_hand(match: Match) -> Match:
    hand = match.current
    if hand is None or not hand.over:
        raise ValueError("hand is not over")
    return replace(
        match,
        hero=hand.stacks[HERO],
        villain=hand.stacks[VILLAIN],
        hand_index=match.hand_index + 1,
        button=other(match.button),
        current=None,
    )


def hole_text(cards: list[tuple[int, int]]) -> str:
    return " ".join(format_card(card) for card in cards)
