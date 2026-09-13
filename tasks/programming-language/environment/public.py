#!/usr/bin/python3 -I
"""The only privileged entrypoint available to the agent; source arrives on stdin."""

import sys

sys.path.insert(0, "/opt/programming-language")
from language_game.engine import MAX_SOURCE
from language_game.runtime import Runtime


def main():
    argv = sys.argv[1:]
    if argv == ["status"]:
        source = ""
    elif (len(argv) == 2 and argv[0] in ("compile", "submit")) or (
        len(argv) == 3 and argv[0] == "run" and len(argv[2]) <= 8192
    ):
        # Opening a path happens in the agent's shell before sudo. Root cannot
        # be tricked into reading a private file through a source-path argument.
        source = sys.stdin.buffer.read(MAX_SOURCE + 1).decode("utf-8", errors="replace")
    else:
        raise ValueError(
            "use status | compile <problem> | run <problem> '<inputs>' | submit <problem>"
        )
    sys.stdout.write(Runtime().command(argv, source))


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
