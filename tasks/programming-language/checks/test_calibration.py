import json
from dataclasses import asdict, replace
from itertools import product

import pytest
from language_game.engine import OPERATIONS, Language
from language_game.generation import generate_trial

from calibrate import ablate
from generate_steps import validate_trial


@pytest.mark.parametrize(
    "input_mode,output_mode,loop_mode",
    list(product(("replace", "add"), ("preserve", "clear"), ("manual", "consume"))),
)
def test_semantic_knowledge_transfers_beyond_the_token_mapping(input_mode, output_mode, loop_mode):
    trial = generate_trial(1)
    language = Language(OPERATIONS, 16, 8, False, input_mode, output_mode, loop_mode)
    trial["language"] = asdict(language)
    # The smallest tape and modulus must support every combination, including
    # copying live values for destructive output and nesting consuming loops.
    validate_trial(trial)
    rows = {row["field"]: row for row in ablate(trial)}
    for field in ("input_mode", "output_mode", "loop_mode"):
        failures = rows[field]["failures"]
        # Explicit clearing/copying is portable in the opposite direction.
        if (field == "input_mode" and input_mode == "replace") or (
            field == "output_mode" and output_mode == "preserve"
        ):
            assert failures == []
            continue
        assert any(p["phase"] in ("foundation", "practice") for p in failures)
        assert any(p["phase"] == "holdout" for p in failures)
        if field == "input_mode":
            assert {"overwrite", "dot"} <= {p["family"] for p in failures}
        if field == "output_mode":
            assert {"duplicate", "prefix"} <= {p["family"] for p in failures}


def test_usage_rules_are_distinguishable_through_public_runs(runtime_factory):
    # Token meanings are fixed here to isolate semantic observability. The
    # probes receive only normal CLI output, with no rule labels in feedback.
    for index, (input_mode, output_mode, loop_mode) in enumerate(
        product(("replace", "add"), ("preserve", "clear"), ("manual", "consume"))
    ):
        runtime = runtime_factory(str(index))
        language = replace(
            runtime.language, input_mode=input_mode, output_mode=output_mode, loop_mode=loop_mode
        )
        trial = runtime.trial | {"language": asdict(language)}
        (runtime.paths.private / "trial.json").write_text(json.dumps(trial))
        runtime = type(runtime)(runtime.paths)
        runtime.start(1)

        def probe(code, inputs, runtime=runtime, language=language):
            response = json.loads(
                runtime.command(["run", "problem-01", json.dumps(inputs)], language.encode(code))
            )
            assert not response.get("error")
            return response["output"]

        assert probe("++,,.", [2, 3]) == ([3] if input_mode == "replace" else [7])
        assert probe("+..", []) == ([1, 1] if output_mode == "preserve" else [1, 0])
        assert probe("++[->+<]>.", []) == ([2] if loop_mode == "manual" else [1])
