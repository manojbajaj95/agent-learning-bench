"""Pure, bounded interpreter. No host execution, imports, files, or clocks in programs."""

from __future__ import annotations

from dataclasses import dataclass

VERSION = 3
TASK_VERSION = "0.3.0"
TOKENS = "abcdefgh"
OPERATIONS = "><+-.,[]"
MAX_SOURCE = 8192
MAX_INPUTS = 128
MAX_OUTPUTS = 128
MAX_STEPS = 100_000


@dataclass(frozen=True)
class Language:
    # Token order is public and fixed; the corresponding operations are private.
    operations: str
    modulus: int
    tape_size: int
    wrapping: bool
    input_mode: str = "replace"
    output_mode: str = "preserve"
    loop_mode: str = "manual"

    def __post_init__(self):
        if sorted(self.operations) != sorted(OPERATIONS):
            raise ValueError("invalid operation permutation")
        if self.modulus not in (16, 32, 256) or self.tape_size not in (8, 16, 32):
            raise ValueError("invalid machine dimensions")
        if type(self.wrapping) is not bool:
            raise ValueError("invalid boundary behavior")
        if self.input_mode not in ("replace", "add"):
            raise ValueError("invalid input behavior")
        if self.output_mode not in ("preserve", "clear"):
            raise ValueError("invalid output behavior")
        if self.loop_mode not in ("manual", "consume"):
            raise ValueError("invalid loop behavior")

    def encode(self, program: str) -> str:
        """Authoring/oracle helper; never exposed by the public interpreter CLI."""
        return program.translate(str.maketrans(self.operations, TOKENS))


class ProgramError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class Program:
    code: str
    jumps: tuple[int, ...]


@dataclass(frozen=True)
class Execution:
    output: tuple[int, ...]
    steps: int
    error: str | None = None


def compile_source(language: Language, source: str) -> Program:
    if not isinstance(source, str) or len(source) > MAX_SOURCE:
        raise ProgramError("SOURCE_ERROR", f"source exceeds {MAX_SOURCE} characters")
    decoded = []
    mapping = dict(zip(TOKENS, language.operations, strict=True))
    for position, token in enumerate(source):
        if token in " \t\r\n":
            continue
        if token not in mapping:
            raise ProgramError("SYNTAX_ERROR", f"invalid token at character {position}")
        decoded.append(mapping[token])
    stack = []
    jumps = [-1] * len(decoded)
    for position, operation in enumerate(decoded):
        if operation == "[":
            stack.append(position)
        elif operation == "]":
            if not stack:
                raise ProgramError("SYNTAX_ERROR", f"unmatched token at instruction {position}")
            start = stack.pop()
            jumps[start] = position
            jumps[position] = start
    if stack:
        raise ProgramError("SYNTAX_ERROR", f"unmatched token at instruction {stack[-1]}")
    return Program("".join(decoded), tuple(jumps))


def validate_inputs(inputs: object) -> list[int]:
    if not isinstance(inputs, list) or len(inputs) > MAX_INPUTS:
        raise ProgramError("INPUT_ERROR", f"expected a list of at most {MAX_INPUTS} integers")
    if any(type(x) is not int or not 0 <= x <= 65535 for x in inputs):
        raise ProgramError("INPUT_ERROR", "integers must be in 0..65535")
    return inputs


def execute(language: Language, program: Program, inputs: list[int]) -> Execution:
    validate_inputs(inputs)
    cells = [0] * language.tape_size
    pointer = pc = consumed = steps = 0
    output: list[int] = []
    while pc < len(program.code):
        if steps == MAX_STEPS:
            return Execution(tuple(output), steps, "STEP_LIMIT: instruction budget exhausted")
        steps += 1
        operation = program.code[pc]
        if operation in "><":
            target = pointer + (1 if operation == ">" else -1)
            if language.wrapping:
                target %= language.tape_size
            elif not 0 <= target < language.tape_size:
                return Execution(tuple(output), steps, f"INDEX_ERROR: index {target} invalid")
            pointer = target
        elif operation == "+":
            cells[pointer] = (cells[pointer] + 1) % language.modulus
        elif operation == "-":
            cells[pointer] = (cells[pointer] - 1) % language.modulus
        elif operation == ",":
            if consumed == len(inputs):
                return Execution(tuple(output), steps, "INPUT_EXHAUSTED: no input remaining")
            previous = cells[pointer] if language.input_mode == "add" else 0
            cells[pointer] = (previous + inputs[consumed]) % language.modulus
            consumed += 1
        elif operation == ".":
            if len(output) == MAX_OUTPUTS:
                return Execution(tuple(output), steps, "OUTPUT_LIMIT: output budget exhausted")
            output.append(cells[pointer])
            if language.output_mode == "clear":
                cells[pointer] = 0
        elif operation == "[":
            if cells[pointer] == 0:
                pc = program.jumps[pc]
            elif language.loop_mode == "consume":
                cells[pointer] -= 1
        elif operation == "]" and cells[pointer] != 0:
            # Both modes test the current pointer, not a captured entry cell.
            # Consume mode removes one unit before each iteration, including
            # the first. The decrement belongs to the delimiter's gas cost.
            if language.loop_mode == "consume":
                cells[pointer] -= 1
            pc = program.jumps[pc]
        pc += 1
    return Execution(tuple(output), steps)
