from poker_game.cards import (
    FLUSH,
    PAIR,
    QUADS,
    STRAIGHT,
    STRAIGHT_FLUSH,
    best_hand,
    parse_card,
    rank5,
)
from poker_game.engine import (
    BB,
    HERO,
    SB,
    START_STACK,
    VILLAIN,
    Match,
    apply_action,
    finish_hand,
    legal_actions,
    start_hand,
)
from poker_game.fish import fish_action
from poker_game.oracle import oracle_action


def C(text: str):
    return parse_card(text)


def test_rank5_categories():
    assert rank5([C("Ah"), C("Kh"), C("Qh"), C("Jh"), C("Th")])[0] == STRAIGHT_FLUSH
    assert rank5([C("Ah"), C("Ad"), C("Ac"), C("As"), C("2h")])[0] == QUADS
    assert rank5([C("Ah"), C("Kh"), C("9h"), C("4h"), C("2h")])[0] == FLUSH
    assert rank5([C("Ah"), C("2d"), C("3c"), C("4s"), C("5h")])[0] == STRAIGHT
    assert rank5([C("Ah"), C("Ad"), C("Kc"), C("9s"), C("2h")])[0] == PAIR


def test_wheel_beats_high_card():
    wheel = rank5([C("Ah"), C("2d"), C("3c"), C("4s"), C("5h")])
    ace_high = rank5([C("Ah"), C("Kd"), C("9c"), C("4s"), C("2h")])
    assert wheel > ace_high


def test_best_of_seven():
    cards = [C("Ah"), C("Ad"), C("Kh"), C("Kd"), C("2c"), C("7s"), C("9h")]
    assert best_hand(cards)[0] == 2  # two pair


def test_blinds_and_sb_to_act():
    match = start_hand(Match(seed=1, hands=2))
    hand = match.current
    assert hand.pot == SB + BB
    assert hand.button == HERO
    assert hand.to_act == HERO
    assert "call" in legal_actions(hand)
    assert legal_actions(hand)["call"] == 5


def test_limp_gives_bb_option():
    match = start_hand(Match(seed=1, hands=2))
    apply_action(match.current, "call")
    assert not match.current.over
    assert match.current.to_act == VILLAIN
    assert "check" in legal_actions(match.current)
    apply_action(match.current, "check")
    assert match.current.street == "flop"
    assert len(match.current.board) == 3


def test_fold_awards_pot():
    match = start_hand(Match(seed=1, hands=2))
    apply_action(match.current, "fold")
    assert match.current.over
    assert match.current.stacks[VILLAIN] == START_STACK + SB
    assert match.current.stacks[HERO] == START_STACK - SB


def test_raise_call_goes_to_flop():
    match = start_hand(Match(seed=1, hands=2))
    apply_action(match.current, "raise", 30)
    assert match.current.to_act == VILLAIN
    apply_action(match.current, "call")
    assert match.current.street == "flop"
    assert match.current.pot == 60


def test_stacks_persist():
    match = start_hand(Match(seed=1, hands=2))
    apply_action(match.current, "fold")
    match = finish_hand(match)
    assert match.hero == START_STACK - SB
    assert match.villain == START_STACK + SB
    match = start_hand(match)
    assert match.current.button == VILLAIN


def test_fish_and_oracle_pick_legal_actions():
    match = start_hand(Match(seed=7, hands=1))
    for _ in range(40):
        if match.current.over:
            break
        legal = legal_actions(match.current)
        assert legal
        if match.current.to_act == HERO:
            action, raise_to = oracle_action(match.current)
        else:
            action, raise_to = fish_action(match.current)
        apply_action(match.current, action, raise_to)
    assert match.current.over
    assert sum(match.current.stacks) == 2 * START_STACK


def test_twenty_hands_chip_conservation():
    match = Match(seed=1, hands=20)
    while not match.complete():
        match = start_hand(match)
        for _ in range(40):
            if match.current.over:
                break
            if match.current.to_act == HERO:
                action, raise_to = oracle_action(match.current)
            else:
                action, raise_to = fish_action(match.current)
            apply_action(match.current, action, raise_to)
        assert match.current.over
        match = finish_hand(match)
    assert match.hero + match.villain == 2 * START_STACK
    assert match.hero != START_STACK


def test_oracle_prints_money_in_full_match():
    match = Match(seed=1, hands=100)
    while not match.complete():
        match = start_hand(match)
        for _ in range(40):
            if match.current.over:
                break
            if match.current.to_act == HERO:
                action, raise_to = oracle_action(match.current)
            else:
                action, raise_to = fish_action(match.current)
            apply_action(match.current, action, raise_to)
        match = finish_hand(match)
    assert match.hero > START_STACK

