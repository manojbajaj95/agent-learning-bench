import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest
from harbor.models.task.task import Task
from language_game.engine import Language, compile_source, execute
from language_game.generation import generate_language, generate_trial
from language_game.problems import expected

from generate_steps import generated_files, validate_trial, write_generated
from oracle import reference_program

TASK = Path(__file__).resolve().parents[1]


def test_seed_reproducibility_diversity_and_all_oracles():
    languages = []
    for seed in range(100):
        trial = generate_trial(seed)
        assert trial == generate_trial(seed)
        assert trial["language"] == asdict(generate_language(seed))
        languages.append(json.dumps(trial["language"], sort_keys=True))
        validate_trial(trial)
    assert len(set(languages)) > 95
    assert {generate_language(s).modulus for s in range(100)} == {16, 32, 256}
    assert {generate_language(s).tape_size for s in range(100)} == {8, 16, 32}
    assert {generate_language(s).wrapping for s in range(100)} == {False, True}
    assert {generate_language(s).input_mode for s in range(100)} == {"replace", "add"}
    assert {generate_language(s).output_mode for s in range(100)} == {"preserve", "clear"}
    assert {generate_language(s).loop_mode for s in range(100)} == {"manual", "consume"}


def test_modes_are_a_matched_experiment_and_schedule_has_transfer():
    hidden, partial = generate_trial(17), generate_trial(17, "partial")
    assert hidden | {"visibility": "partial"} == partial
    problems = hidden["problems"]
    assert [p["index"] for p in problems] == list(range(1, 21))
    assert len({p["family"] for p in problems}) == 20
    assert [p["phase"] for p in problems] == (
        ["foundation"] * 6 + ["practice"] * 6 + ["transfer"] * 4 + ["holdout"] * 4
    )
    assert {p["family"] for p in problems[:16]}.isdisjoint(p["family"] for p in problems[16:])
    language = Language(**hidden["language"])
    # An earlier reference solution cannot solve a holdout by copying it unchanged.
    for previous in problems[:16]:
        program = compile_source(
            language,
            language.encode(reference_program(previous["family"], previous["parameter"], language)),
        )
        for holdout in problems[16:]:
            outcomes = [
                execute(language, program, test["input"]) for test in holdout["hidden_tests"]
            ]
            assert any(
                result.error or list(result.output) != test["output"]
                for result, test in zip(outcomes, holdout["hidden_tests"], strict=True)
            )
    for problem in problems:
        tests = problem["hidden_tests"]
        assert len({tuple(t["input"]) for t in tests}) == len(tests)
        if problem["family"] != "constant":
            assert {tuple(t["input"]) for t in tests}.isdisjoint(
                tuple(t["input"]) for t in problem["public"]["examples"]
            )
        for test in tests:
            assert test["output"] == expected(
                problem["family"], problem["parameter"], test["input"]
            )


def test_expected_outputs_have_independent_known_examples():
    fixtures = [
        ("constant", 7, [], [7]),
        ("echo", None, [15], [15]),
        ("duplicate", None, [9], [9, 9]),
        ("overwrite", None, [9, 2], [2]),
        ("successor", None, [14], [15]),
        ("add", None, [7, 7], [14]),
        ("affine", [3, 2], [3], [11]),
        ("equals", 8, [8], [1]),
        ("equals", 8, [9], [0]),
        ("permute", [3, 1, 2], [7, 8, 9], [9, 7, 8]),
        ("range", 2, [3], [2, 3, 4]),
        ("repeat", 2, [3, 5], [7, 7, 7]),
        ("sum", 3, [3, 2, 0, 1], [6]),
        ("select", None, [0, 8, 9], [8]),
        ("select", None, [15, 8, 9], [9]),
        ("count", None, [3, 0, 15, 2], [2]),
        ("prefix", None, [3, 2, 0, 1], [2, 2, 3]),
        ("triangular", None, [5], [15]),
        ("stream_echo", None, [3, 7, 0, 2], [7, 0, 2]),
        ("totals", None, [3, 2, 0, 1], [2, 0, 1, 3]),
        ("pair_sums", None, [3, 7, 0, 0, 1, 2, 3], [7, 1, 5]),
        ("dot", None, [3, 2, 2, 0, 1, 1, 2], [6]),
    ]
    for family, parameter, inputs, answer in fixtures:
        assert expected(family, parameter, inputs) == answer


@pytest.mark.parametrize("visibility", ["hidden", "partial"])
def test_equality_reserves_positive_case_and_grades_both_branches(visibility):
    for seed in range(100):
        trial = generate_trial(seed, visibility)
        problem = next(p for p in trial["problems"] if p["family"] == "equals")
        examples = problem["public"]["examples"]
        hidden = problem["hidden_tests"]
        assert len(examples) == 2
        assert all(t["output"] == [0] for t in examples), seed
        assert [t for t in hidden if t["output"] == [1]] == [
            {"input": [problem["parameter"]], "output": [1]}
        ], seed
        assert any(t["output"] == [0] for t in hidden), seed
        public_inputs = {tuple(t["input"]) for t in examples}
        hidden_inputs = {tuple(t["input"]) for t in hidden}
        assert public_inputs.isdisjoint(hidden_inputs), seed
        assert public_inputs | hidden_inputs == {(x,) for x in range(16)}, seed


def test_cross_process_generation_and_golden_instance():
    script = (
        "import hashlib,json; from language_game.generation import generate_trial; "
        "print(hashlib.sha256(json.dumps(generate_trial(1),sort_keys=True).encode()).hexdigest())"
    )
    digests = []
    for hashseed in ("0", "42", "random"):
        env = dict(os.environ, PYTHONHASHSEED=hashseed, PYTHONPATH=str(TASK / "environment"))
        result = subprocess.run(
            [sys.executable, "-c", script],
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        digests.append(result.stdout.strip())
    committed = json.loads((TASK / "environment/trial.json").read_text())
    # Version 3, seed 1, hidden mode: intentional generator changes need a version review.
    assert digests[0] == "4c820f86d1250c3c2130d3118178f87d75c073962c51dd37d696b0c46666b6ee"
    assert set(digests) == {
        hashlib.sha256(json.dumps(committed, sort_keys=True).encode()).hexdigest()
    }
    assert write_generated(TASK, generated_files(), check=True) == []


def test_harbor_loader_and_self_contained_generation(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(TASK / "generate_steps.py"),
            "--seed",
            "2",
            "--visibility",
            "partial",
            "--output",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    task = Task(tmp_path)
    assert len(task.config.steps) == 20
    assert len({task.step_instruction(s.name) for s in task.config.steps}) == 1
    assert task.config.agent.user == "agent" and task.config.verifier.user == "root"
    assert task.config.multi_step_reward_strategy == "mean"
    assert all(s.min_reward is None for s in task.config.steps)
    assert task.config.metadata["seed"] == 2
    assert task.config.metadata["visibility"] == "partial"
    assert (tmp_path / "environment/language_game/engine.py").is_file()
    assert not (tmp_path / "environment/oracle.py").exists()
    check = subprocess.run(
        [
            sys.executable,
            str(TASK / "generate_steps.py"),
            "--seed",
            "2",
            "--visibility",
            "partial",
            "--output",
            str(tmp_path),
            "--check",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert check.returncode == 0, check.stderr
    assert json.loads((TASK / "environment/trial.json").read_text())["seed"] == 1


def test_writer_preserves_unexpected_files_and_rejects_symlinks(tmp_path):
    files = {"steps/problem-01/workdir/setup.sh": "#!/bin/sh\ntrue\n"}
    write_generated(tmp_path, files, False)
    extra = tmp_path / "steps/problem-01/notes.txt"
    extra.write_text("keep")
    assert "steps/problem-01/notes.txt" in write_generated(tmp_path, files, True)
    write_generated(tmp_path, files, False)
    assert extra.read_text() == "keep"
    (tmp_path / "link").symlink_to(tmp_path / "steps", target_is_directory=True)
    with pytest.raises(ValueError):
        write_generated(tmp_path, {"link/x": "bad"}, False)
    with pytest.raises(ValueError):
        generate_trial(1, "given")
