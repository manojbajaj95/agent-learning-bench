from dataclasses import replace
from itertools import product

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from language_game.engine import (
    MAX_INPUTS,
    MAX_OUTPUTS,
    MAX_SOURCE,
    MAX_STEPS,
    OPERATIONS,
    Execution,
    Language,
    ProgramError,
    compile_source,
    execute,
)
from language_game.generation import generate_language


def run(language, code, inputs=None):
    return execute(language, compile_source(language, language.encode(code)), inputs or [])


@pytest.mark.parametrize(
    "modulus,size,wrapping", list(product((16, 32, 256), (8, 16, 32), (False, True)))
)
def test_machine_semantics(modulus, size, wrapping):
    language = Language(OPERATIONS, modulus, size, wrapping)
    assert run(language, "-.").output == (modulus - 1,)
    assert run(language, "+" * modulus + ".").output == (0,)
    assert run(language, ",.", [modulus + 3]).output == (3,)
    assert run(language, "+>++<.>.").output == (1, 2)
    assert run(language, "[+].").output == (0,)
    assert run(language, "++[>+++[>+<-]<-]>>.").output == (6,)
    assert run(language, "[[]]+.").output == (1,)
    # Closing loops test the current pointer, not a captured entry cell.
    assert run(language, "+[>]<.").output == (1,)
    boundary = run(language, "+" + ">" * size + ".")
    if wrapping:
        assert boundary.output == (1,) and boundary.error is None
        assert run(language, "<+" + ">" * size + ".").output == (1,)
    else:
        assert boundary.error == f"INDEX_ERROR: index {size} invalid"
        assert run(language, "<").error == "INDEX_ERROR: index -1 invalid"


def test_errors_limits_and_exact_gas():
    language = Language(OPERATIONS, 16, 8, False)
    for code in ("[", "]", "][", "[[[]]"):
        with pytest.raises(ProgramError, match="SYNTAX_ERROR"):
            compile_source(language, language.encode(code))
    for source in ("import os", "λ", "\x00", "\v"):
        with pytest.raises(ProgramError, match="SYNTAX_ERROR"):
            compile_source(language, source)
    with pytest.raises(ProgramError, match="SOURCE_ERROR"):
        compile_source(language, "a" * (MAX_SOURCE + 1))
    assert run(language, ",", []).error == "INPUT_EXHAUSTED: no input remaining"
    assert run(language, ".,").output == (0,)
    assert run(language, "." * MAX_OUTPUTS).error is None
    assert run(language, "." * (MAX_OUTPUTS + 1)).error.startswith("OUTPUT_LIMIT")
    endless = run(language, "+[]")
    assert endless.steps == MAX_STEPS and endless.error.startswith("STEP_LIMIT")
    assert run(language, "++[-].") == Execution((0,), 8)
    assert run(language, "").steps == 0
    # Source whitespace is ignored, including in the compiler's jump positions.
    source = " \n".join(language.encode("++[-]."))
    assert execute(language, compile_source(language, source), []) == Execution((0,), 8)
    for inputs in ([True], [-1], [65536], [1.0], "1", [0] * (MAX_INPUTS + 1)):
        with pytest.raises(ProgramError, match="INPUT_ERROR"):
            execute(language, compile_source(language, ""), inputs)


@given(
    st.integers(),
    st.text(alphabet="+-.,><", max_size=150),
    st.lists(st.integers(0, 65535), max_size=20),
)
@settings(max_examples=100, deadline=None, derandomize=True)
def test_seeded_execution_replays_without_global_or_machine_state(seed, code, inputs):
    language = generate_language(seed)
    result = run(language, code, inputs)
    assert result == run(generate_language(seed), code, inputs)
    run(language, "+" * 20)
    assert result == run(language, code, inputs)
    assert run(language, ".").output == (0,)
    assert all(0 <= value < language.modulus for value in result.output)


def test_language_rejects_invalid_specs():
    language = generate_language(1)
    for values in (
        {"operations": "a" * 8},
        {"modulus": 17},
        {"tape_size": 0},
        {"wrapping": 1},
        {"input_mode": "unknown"},
        {"output_mode": "unknown"},
        {"loop_mode": "unknown"},
    ):
        with pytest.raises(ValueError):
            replace(language, **values)


@pytest.mark.parametrize(
    "input_mode,output_mode,loop_mode",
    list(product(("replace", "add"), ("preserve", "clear"), ("manual", "consume"))),
)
def test_semantic_variants_have_observable_consistent_rules(input_mode, output_mode, loop_mode):
    language = Language(OPERATIONS, 16, 8, False, input_mode, output_mode, loop_mode)
    assert run(language, "++,,.", [2, 3]).output == ((3 if input_mode == "replace" else 7),)
    assert run(language, "+..").output == ((1, 1) if output_mode == "preserve" else (1, 0))
    assert run(language, "++[->+<]>.").output == ((2,) if loop_mode == "manual" else (1,))
    # Independent nested-loop programs: do not use the reference compiler here.
    nested = "++[>+++[>+<]<]>>." if loop_mode == "consume" else "++[->+++[->+<]<]>>."
    assert run(language, nested).output == (6,)
    assert run(language, "[[]]+.").output == (1,)
    if loop_mode == "consume":
        assert run(language, "++[]") == Execution((), 5)
        assert run(language, "+[>]<.").output == (0,)
    assert run(language, nested) == run(language, nested)
