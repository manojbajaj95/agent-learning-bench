import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from arena.engine import (
    Combat,
    State,
    action_command,
    draft,
    matchup_from_dict,
    outcome,
    state_from_dict,
)
from arena.metrics import belief_metrics
from arena.oracle import Solver
from arena.runtime import read_beliefs


def oracle_play(runtime):
    runtime.start(1)
    battle = runtime.trial["battles"][0]
    matchup = matchup_from_dict(battle)
    names = next(
        row["team"] for row in battle["draft_values"] if row["value"] == battle["oracle_value"]
    )
    team = draft(matchup, names)
    runtime.command(["draft", *names])
    solver = Solver(Combat(team, matchup.opponent, runtime.chart))
    state = State()
    while not outcome(state):
        action = solver.optimal_actions(state)[0]
        runtime.command(action_command(team, state, action).split())
        state, _ = solver.combat.step(state, action)
    solver.close()


def test_status_invalid_and_lifecycle(runtime):
    with pytest.raises(ValueError):
        runtime.command(["status"])
    with pytest.raises(ValueError):
        runtime.start(2)
    view = runtime.start(1)
    before = runtime.load()
    assert runtime.command(["status"]) == view
    assert runtime.start(1) == view
    for command in (["attack", "Ember"], ["draft", "x", "y", "z"], ["start", "1"], ["settle"]):
        with pytest.raises(ValueError):
            runtime.command(command)
        assert runtime.load() == before
    assert runtime.settle()["reward"] == 0
    assert runtime.settle()["env_actions"] == 0
    runtime.start(2)
    with pytest.raises(ValueError):
        runtime.start(1)
    snapshot = runtime.load()
    assert runtime.settle(1)["reward"] == 0
    assert runtime.load() == snapshot
    with pytest.raises(ValueError):
        runtime.settle(3)


def test_oracle_grading_freeze_and_public_log(runtime):
    oracle_play(runtime)
    metrics = runtime.settle()
    assert metrics["reward"] == runtime.trial["battles"][0]["oracle_value"][0] / 4200
    assert metrics["won"] == metrics["completed"] == metrics["draft_ok"] == metrics["opt_rate"] == 1
    assert metrics["regret"] == 0
    assert metrics["ticks"] == metrics["oracle_ticks"]
    (runtime.paths.public / "affinity-chart.json").write_text(json.dumps({"Amber": {"Basalt": 2}}))
    assert runtime.settle() == metrics
    with pytest.raises(ValueError):
        runtime.command(["draft", "a", "b", "c"])
    trace = (runtime.paths.public / "battles/battle-01.jsonl").read_text()
    assert not any(s in trace for s in ("chart", "oracle", "optimal", "multiplier", "draft_values"))
    events = [json.loads(line) for line in trace.splitlines()]
    assert events[0]["kind"] == "start"
    assert len(events[0]["offered"]) == 5
    seen = {
        (h["attack_affinity"], h["defender_affinity"]) for e in events for h in e.get("hits", [])
    }
    assert metrics["cells_seen"] == len(seen) / 36
    runtime.start(2)
    assert len(runtime.load()["cells"]) == len(seen)


def test_concurrent_actions_are_serialized(runtime):
    runtime.start(1)
    names = [c["name"] for c in runtime.trial["battles"][0]["offered"][:3]]

    def attempt():
        try:
            runtime.command(["draft", *names])
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=8) as executor:
        assert sum(executor.map(lambda _: attempt(), range(8))) == 1
    current = runtime.load()["current"]
    assert len(current["events"]) == 1
    assert state_from_dict(current["state"]).tick == 0
    runtime.start(1)
    assert runtime.load()["current"] == current
    with pytest.raises(ValueError):
        runtime.command(["switch", names[0]])
    assert runtime.settle()["reward"] == 0


def test_beliefs_are_bounded_and_untrusted(tmp_path):
    chart = ((2,) * 6,) * 6
    assert belief_metrics(
        {"Amber": {"Amber": 1, "Basalt": 2, "Cobalt": True, "unknown": 1}, "Onyx": []}, chart
    ) == (1 / 36, 2 / 36)
    assert belief_metrics([1, 2], chart) == (0, 0)
    path = tmp_path / "beliefs.json"
    assert read_beliefs(path) == {}
    path.write_text("not json")
    assert read_beliefs(path) == {}
    path.write_text(" " * 65537)
    assert read_beliefs(path) == {}
    path.unlink()
    path.symlink_to(tmp_path / "secret.json")
    assert read_beliefs(path) == {}
    path.unlink()
    os.mkfifo(path)
    assert read_beliefs(path) == {}
