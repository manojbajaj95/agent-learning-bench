from collections import Counter
from dataclasses import replace
from itertools import combinations

import pytest
from arena.engine import (
    Action,
    Combat,
    Creature,
    Matchup,
    Move,
    State,
    damage,
    draft,
    legal_actions,
    matchup_from_dict,
    outcome,
    reward,
    score,
)
from arena.generation import generate_chart, generate_roster
from arena.oracle import Solver, solve_drafts
from hypothesis import given, settings
from hypothesis import strategies as st


def fixture_combat(multiplier=2):
    creatures = tuple(
        Creature(f"c{i}", i, (Move("A", 0, 50), Move("B", 1, 36), Move("C", 2, 36)))
        for i in range(3)
    )
    return Combat(creatures, creatures, tuple((multiplier,) * 6 for _ in range(6)))


def test_hundred_balanced_charts():
    charts = [generate_chart(seed) for seed in range(100)]
    assert len(set(charts)) > 95
    for seed, chart in enumerate(charts):
        assert chart == generate_chart(seed)
        for row in (*chart, *zip(*chart, strict=True)):
            assert Counter(row) == {1: 2, 2: 2, 4: 2}


def test_charts_have_distinct_affinities_and_structural_diversity():
    signatures = set()
    for seed in range(100):
        chart = generate_chart(seed)
        assert len(set(chart)) == 6
        assert len(set(zip(*chart, strict=True))) == 6
        # Pairwise row agreement is invariant under row/column permutations.
        # Different signatures rule out merely relabeling one fixed table.
        signatures.add(
            tuple(
                sorted(
                    sum(a == b for a, b in zip(left, right, strict=True))
                    for left, right in combinations(chart, 2)
                )
            )
        )
    assert len(signatures) > 1


def test_roster_contract():
    for seed in range(20):
        main, tail = generate_roster(seed), generate_roster(seed, True)
        assert {c.name for c in main}.isdisjoint(c.name for c in tail)
        assert main == generate_roster(seed)
        for roster in (main, tail):
            assert Counter(c.affinity for c in roster) == dict.fromkeys(range(6), 2)
            assert Counter(m.affinity for c in roster for m in c.moves) == dict.fromkeys(
                range(6), 6
            )
            for c in roster:
                assert len({m.affinity for m in c.moves}) == 3
                assert sorted(m.power for m in c.moves) == [36, 36, 50]
                assert next(m for m in c.moves if m.power == 50).affinity == c.affinity
            for affinity in range(6):
                pair = [
                    set(m.affinity for m in c.moves if m.power == 36)
                    for c in roster
                    if c.affinity == affinity
                ]
                assert len(pair[0] & pair[1]) == 1
                assert pair[0] != pair[1]


def test_damage_and_knockout_skip_response():
    combat = fixture_combat(4)
    state, hits = combat.step(State(enemy_hp=50), Action("attack", 0))
    assert state == State(enemy=1, tick=1)
    assert len(hits) == 1 and hits[0].damage == 100  # Uncapped observation.
    half = fixture_combat(1)
    assert damage(Move("odd", 0, 35), half.team[0], ((1,) * 6,) * 6) == 17


def test_switch_and_fainting():
    combat = fixture_combat()
    state, hits = combat.step(State(), Action("switch", 2))
    assert state.hp == (100, 100, 50) and state.active == 2
    assert len(hits) == 1 and hits[0].defender == "c2"
    state, _ = combat.step(state, Action("attack", 0))
    assert state.hp == (100, 100, 0) and state.active == 0
    assert Action("switch", 2) not in legal_actions(state)
    assert Action("switch", 0) not in legal_actions(state)


def test_enemy_ties_and_terminal_rules():
    combat = fixture_combat()
    tied = replace(
        combat.opponent[0],
        moves=(Move("first", 0, 36), Move("second", 1, 36), Move("third", 2, 36)),
    )
    combat = Combat(combat.team, (tied, *combat.opponent[1:]), ((2,) * 6,) * 6)
    _, hits = combat.step(State(), Action("attack", 0))
    assert hits[-1].move == "first"
    assert outcome(State(enemy=3, enemy_hp=0, tick=30)) == "win"
    assert outcome(State(hp=(0, 0, 0), tick=30)) == "loss"
    assert outcome(State(tick=30)) == "tick_cap"
    assert not legal_actions(State(tick=30))
    with pytest.raises(ValueError):
        combat.step(State(tick=30), Action("attack", 0))
    assert reward(State()) == 0.5
    assert reward(State(enemy=3, enemy_hp=0)) == 1


@given(
    st.integers(min_value=0, max_value=10000),
    st.lists(st.integers(min_value=0, max_value=100), min_size=30, max_size=30),
)
@settings(max_examples=100, deadline=None)
def test_transition_properties(seed, choices):
    roster = generate_roster(seed)
    combat = Combat(roster[:3], roster[3:6], generate_chart(seed))
    state = State()
    for choice in choices:
        legal = legal_actions(state)
        if not legal:
            break
        action = legal[choice % len(legal)]
        after, hits = combat.step(state, action)
        assert (after, hits) == combat.step(state, action)
        assert after.tick == state.tick + 1
        assert all(0 <= h <= 100 for h in after.hp)
        assert 0 <= after.enemy_hp <= 140
        assert sum(after.hp) <= sum(state.hp)
        assert (
            sum(after.hp) < sum(state.hp)
            or after.enemy > state.enemy
            or after.enemy_hp < state.enemy_hp
        )
        assert 0 <= reward(after) <= 1
        if not outcome(after):
            assert after.hp[after.active] > 0
        state = after
    assert outcome(state) is not None


def test_solver_against_exhaustive_short_horizon():
    combat = fixture_combat()
    state = State(hp=(18, 40, 20), enemy=2, enemy_hp=50)
    solver = Solver(combat, cap=3)

    def brute(s):
        if outcome(s, 3):
            return score(s), 0
        values = []
        for a in legal_actions(s, 3):
            end, _ = combat.step(s, a, 3)
            value, ticks = brute(end)
            values.append((value, ticks - 1))
        return max(values)

    assert solver.value(state) == brute(state)
    assert solver.value(state) == (7 * 78 + 2100, -1)  # Power 50 wins before retaliation.


def test_drafts_and_replay(trial):
    chart = tuple(tuple(row) for row in trial["chart"])
    for battle in trial["battles"]:
        matchup = matchup_from_dict(battle)
        assert len(set(c.name for c in (*matchup.offered, *matchup.opponent))) == 8
        best, values = solve_drafts(matchup, chart)
        assert len(values) == 60 and best == tuple(battle["oracle_value"])
        names = next(names for names, value in values.items() if value == best)
        team = draft(matchup, list(names))
        solver = Solver(Combat(team, matchup.opponent, chart))
        state = State()
        while not outcome(state):
            action = solver.optimal_actions(state)[0]
            state, _ = solver.combat.step(state, action)
        assert outcome(state) == "win"
        assert (score(state), -state.tick) == best
        solver.close()


def test_draft_validation():
    roster = generate_roster(1)
    matchup = Matchup(roster[:5], roster[5:8])
    for names in ([], ["unknown"] * 3, [roster[0].name] * 3):
        with pytest.raises(ValueError):
            draft(matchup, names)
