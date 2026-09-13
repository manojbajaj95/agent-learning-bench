import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from language_game.engine import MAX_SOURCE
from language_game.generation import LOCAL_CALLS, SUBMISSIONS
from language_game.runtime import Runtime

from oracle import reference_program


def oracle_source(runtime, index):
    problem = runtime.trial["problems"][index - 1]
    return runtime.language.encode(
        reference_program(problem["family"], problem["parameter"], runtime.language)
    )


def test_first_submission_freezes_reward_and_later_success_is_recorded(runtime):
    runtime.start(1)
    rejected = json.loads(runtime.command(["submit", "problem-01"], ""))
    assert rejected["score"] == 0
    source = oracle_source(runtime, 1)
    assert json.loads(runtime.command(["submit", "problem-01"], source))["score"] == 1
    with pytest.raises(ValueError, match="closed"):
        runtime.command(["run", "problem-01", "[]"], source)
    metrics = runtime.settle(1)
    assert metrics["reward"] == metrics["first_correctness"] == metrics["first_solved"] == 0
    assert metrics["best_correctness"] == metrics["solved"] == metrics["last_correctness"] == 1
    assert metrics["attempts_to_solve"] == metrics["submissions"] == 2
    assert runtime.load()["current"]["submissions"][1]["source"] == source
    (runtime.paths.public / "workspace/solution.lang").write_text("bad subsequent edit")
    assert runtime.settle(1) == metrics
    runtime.start(2)
    before = runtime.load()
    assert runtime.settle(1) == metrics
    assert runtime.load() == before


def test_partial_correctness_not_binary_scoring(runtime):
    runtime.start(1)
    runtime.settle(1)
    runtime.start(2)
    tests = runtime.trial["problems"][1]["hidden_tests"]
    value = tests[0]["output"][0]
    source = runtime.language.encode("+" * value + ".")
    feedback = json.loads(runtime.command(["submit", "problem-02"], source))
    assert feedback["passed"] == 1 and feedback["score"] == 1 / len(tests)
    runtime.command(["submit", "problem-02"], oracle_source(runtime, 2))
    assert runtime.settle(2)["reward"] == 1 / len(tests)


@pytest.mark.parametrize("visibility", ["hidden", "partial"])
def test_equality_constant_zero_cannot_receive_full_credit(runtime_factory, visibility):
    # Seed 2 previously put the only positive case in the public examples.
    runtime = runtime_factory(seed=2, visibility=visibility)
    problem = next(p for p in runtime.trial["problems"] if p["family"] == "equals")
    index = problem["index"]
    for previous in range(1, index):
        runtime.start(previous)
        runtime.settle(previous)
    runtime.start(index)
    command = ["submit", problem["public"]["id"]]
    response = json.loads(runtime.command(command, runtime.language.encode(".")))
    assert response["passed"] == response["total"] - 1
    assert 0 < response["score"] < 1
    assert json.loads(runtime.command(command, oracle_source(runtime, index)))["score"] == 1
    metrics = runtime.settle(index)
    assert metrics["reward"] == response["score"]
    assert metrics["first_solved"] == 0
    assert metrics["solved"] == 1


def test_status_lifecycle_budgets_and_no_submission(runtime):
    with pytest.raises(ValueError):
        runtime.command(["status"])
    with pytest.raises(ValueError):
        runtime.start(2)
    view = runtime.start(1)
    assert runtime.command(["status"]) == view
    assert runtime.load()["current"]["local_calls"] == 0
    for cmd in (
        ["settle", "1"],
        ["start", "1"],
        ["submit", "problem-02"],
        ["run", "problem-01"],
        ["status", "anything"],
    ):
        with pytest.raises(ValueError):
            runtime.command(cmd)
    for _ in range(LOCAL_CALLS):
        assert json.loads(runtime.command(["compile", "problem-01"], "?"))["error"].startswith(
            "SYNTAX_ERROR"
        )
    before = runtime.load()
    runtime.start(1)
    assert runtime.load() == before
    with pytest.raises(ValueError, match="budget"):
        runtime.command(["compile", "problem-01"], "")
    # Exhausting experiments does not prevent a hidden submission.
    runtime.command(["submit", "problem-01"], oracle_source(runtime, 1))
    metrics = runtime.settle(1)
    assert metrics["reward"] == 1
    assert metrics["compiler_errors"] == LOCAL_CALLS
    assert metrics["compiler_calls"] == metrics["env_actions"] == LOCAL_CALLS + 1
    assert metrics["tool_calls"] == LOCAL_CALLS + 2
    runtime.start(2)
    missing = runtime.settle(2)
    assert missing["reward"] == missing["submitted"] == missing["solved"] == 0
    assert missing["completed"] == 1  # Settled evaluation, distinct from solution success.
    with pytest.raises(ValueError):
        runtime.start(1)
    with pytest.raises(ValueError):
        runtime.settle(3)


def test_concurrent_submissions_cannot_exceed_cap(runtime):
    runtime.start(1)

    def attempt(_):
        try:
            runtime.command(["submit", "problem-01"], "")
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=12) as pool:
        assert sum(pool.map(attempt, range(12))) == SUBMISSIONS
    current = runtime.load()["current"]
    assert len(current["events"]) == len(current["submissions"]) == SUBMISSIONS
    assert current["closed"]
    assert runtime.settle(1)["reward"] == 0


def test_feedback_does_not_explain_rules_or_leak_hidden_tests(runtime):
    runtime.start(1)
    unknown = json.loads(runtime.command(["compile", "problem-01"], "?"))
    assert unknown == {"error": "SYNTAX_ERROR: invalid token at character 0"}
    runtime_error = json.loads(
        runtime.command(["run", "problem-01", "[]"], runtime.language.encode(","))
    )
    assert runtime_error["error"] == "INPUT_EXHAUSTED: no input remaining"
    for source in ("?", runtime.language.encode(","), ""):
        response = json.loads(runtime.command(["submit", "problem-01"], source))
        assert set(response) == {"submission", "passed", "total", "score"}
        assert response["score"] == 0
    events = (runtime.paths.public / "problems/problem-01.jsonl").read_text()
    view = runtime.command(["status"])
    for secret in (
        "hidden_tests",
        "operations",
        "modulus",
        "tape_size",
        "wrapping",
        "input_mode",
        "output_mode",
        "loop_mode",
        "seed",
        "oracle",
    ):
        assert secret not in events + view
    assert "tape machine" not in view
    metrics = runtime.settle(1)
    assert metrics["compiler_errors"] == 2
    assert metrics["runtime_errors"] == 2  # One local failure and one failing submission.


def test_input_and_source_validation_is_bounded(runtime):
    runtime.start(1)
    for invalid in ("[true]", "[-1]", "[65536]", "{}", "[", "1", "[[1]]"):
        assert json.loads(runtime.command(["run", "problem-01", invalid], ""))["error"].startswith(
            "INPUT_ERROR"
        )
    response = json.loads(runtime.command(["compile", "problem-01"], "a" * (MAX_SOURCE + 1)))
    assert response["error"].startswith("SOURCE_ERROR")
    assert runtime.load()["current"]["compiler_calls"] == 1


def test_full_trial_memory_persistence_and_independent_reset(runtime_factory):
    runtime = runtime_factory()
    language = runtime.language
    notes = runtime.paths.public / "notes.md"
    notes.write_text("discovered information")
    helper = runtime.paths.public / "workspace/generator.py"
    helper.write_text("# reusable helper")
    for index in range(1, 21):
        runtime = Runtime(runtime.paths)
        runtime.start(index)
        assert runtime.language == language
        assert notes.read_text() == "discovered information"
        assert helper.read_text() == "# reusable helper"
        assert runtime.load()["current"]["local_calls"] == 0
        result = json.loads(
            runtime.command(["submit", f"problem-{index:02d}"], oracle_source(runtime, index))
        )
        assert result["score"] == 1
        assert runtime.settle(index)["reward"] == 1
    assert len(list((runtime.paths.public / "problems").glob("*.jsonl"))) == 20
    with pytest.raises(ValueError):
        runtime.start(21)
    fresh = runtime_factory("independent", seed=2)
    fresh.start(1)
    assert fresh.language != language
    assert fresh.load()["completed"] == []
    assert fresh.load()["current"]["submissions"] == []
    assert not (fresh.paths.public / "notes.md").exists()
    assert not list((fresh.paths.public / "workspace").iterdir())


def test_only_information_differs_between_modes(runtime_factory):
    hidden, partial = runtime_factory("h"), runtime_factory("p", visibility="partial")
    hidden_view, partial_view = hidden.start(1), partial.start(1)
    assert "tape machine" not in hidden_view and "tape machine" in partial_view
    for runtime in (hidden, partial):
        runtime.command(["run", "problem-01", "[7]"], "ab")
        runtime.command(["submit", "problem-01"], "")
        runtime.command(["submit", "problem-01"], oracle_source(runtime, 1))
    assert hidden.settle(1) == partial.settle(1)
    assert hidden.load() == partial.load()
