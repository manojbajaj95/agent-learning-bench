"""Explicit public projections. Never serialize the private language or test bank."""

import json

from .engine import TOKENS
from .generation import LOCAL_CALLS, SUBMISSIONS


def information(visibility: str) -> str:
    text = f"Source alphabet: {TOKENS}. ASCII spaces, tabs, CR and LF are ignored.\n"
    if visibility == "partial":
        text += (
            "This is a tape machine with integer cells. Its eight tokens perform: "
            "move right, move left, increment, decrement, input, output, loop start, "
            "and loop end, in an unknown mapping. Cells start at zero. Input either "
            "replaces the current cell or adds to it. Output emits its value, then "
            "either preserves or clears the cell. Arithmetic and input reduce modulo "
            "the cell modulus. Paired loops test the current cell at both delimiters "
            "and skip when zero. In one variant the body must update the counter; "
            "in another the delimiter consumes one unit before each body iteration. "
            "Execution starts at cell 0. The selected behaviors, token mapping, "
            "modulus, tape size, and pointer boundary behavior are unknown.\n"
        )
    elif visibility != "hidden":
        raise ValueError("unsupported information mode")
    return text


def render(trial: dict, current: dict) -> str:
    problem = trial["problems"][current["index"] - 1]["public"]
    lines = [
        f"# {problem['id']} — {problem['title']}",
        "",
        problem["statement"],
        "",
        "Inputs and outputs are integer lists, not text or character codes.",
        "",
        "Examples:",
    ]
    for example in problem["examples"]:
        lines.append(f"  {json.dumps(example['input'])} -> {json.dumps(example['output'])}")
    lines += [
        "",
        information(trial["visibility"]),
        f"Local compile/run calls remaining: {LOCAL_CALLS - current['local_calls']}",
        f"Hidden submissions remaining: {SUBMISSIONS - len(current['submissions'])}",
        f"Problem closed: {str(current['closed'] or current['settled']).lower()}",
    ]
    if current["submissions"]:
        lines.append("Last submission: " + json.dumps(current["submissions"][-1]["feedback"]))
    return "\n".join(lines) + "\n"
