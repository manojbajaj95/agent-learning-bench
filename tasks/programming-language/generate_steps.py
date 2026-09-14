#!/usr/bin/env python3
"""Generate and validate a complete seeded Harbor task; --check detects drift."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "environment"))

from language_game.engine import TASK_VERSION, Language, compile_source, execute
from language_game.generation import MODES, generate_trial

from oracle import reference_program


def validate_trial(trial: dict) -> None:
    """A generation failure is an authoring error, never a silently dropped problem."""
    language = Language(**trial["language"])
    for problem in trial["problems"]:
        source = language.encode(
            reference_program(problem["family"], problem["parameter"], language)
        )
        program = compile_source(language, source)
        if not problem["hidden_tests"]:
            raise ValueError("problem has no hidden tests")
        for test in problem["public"]["examples"] + problem["hidden_tests"]:
            result = execute(language, program, test["input"])
            if result.error or list(result.output) != test["output"]:
                raise ValueError(f"oracle failed: seed {trial['seed']}, problem {problem['index']}")


def generated_files(seed: int = 1, visibility: str = "hidden") -> dict[str, str]:
    trial = generate_trial(seed, visibility)
    validate_trial(trial)
    language = Language(**trial["language"])
    files = {"environment/trial.json": json.dumps(trial, indent=2) + "\n"}
    instruction = (ROOT / "instruction.md").read_text()
    toml = f'''schema_version = "1.4"
multi_step_reward_strategy = "mean"
artifacts = ["/app/view.txt", "/app/notes.md", "/app/workspace", "/app/sessions"]

[task]
name = "agent-learning-bench/programming-language"
version = "{TASK_VERSION}"
description = "Learn one generated programming language across twenty programming problems."
keywords = ["programming", "hidden-rules", "multi-step", "continual-learning", "holdout"]

[metadata]
difficulty = "hard"
category = "programming"
seed = {seed}
visibility = "{visibility}"

[agent]
user = "agent"
timeout_sec = 300.0

[verifier]
user = "root"
timeout_sec = 30.0

[environment]
network_mode = "public"
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
workdir = "/app"
'''
    for problem in trial["problems"]:
        name = problem["public"]["id"]
        prefix = f"steps/{name}"
        files[f"{prefix}/instruction.md"] = instruction
        files[f"{prefix}/workdir/setup.sh"] = (
            "#!/usr/bin/env bash\nset -euo pipefail\nlanguage-lab status\n"
        )
        files[f"{prefix}/tests/test.sh"] = (
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            f"/usr/bin/python3 -I /opt/programming-language/admin.py settle {problem['index']}\n"
        )
        source = language.encode(
            reference_program(problem["family"], problem["parameter"], language)
        )
        files[f"{prefix}/solution/solve.sh"] = (
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            "cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'\n"
            f"{source}\nLANGUAGE_EOF\n"
            f"language-lab submit {name} < /app/workspace/solution.lang\n"
        )
        toml += f'\n[[steps]]\nname = "{name}"\nartifacts = ["/app/problems/{name}.jsonl"]\n'
    files["task.toml"] = toml
    return files


def write_generated(output: Path, files: dict[str, str], check: bool) -> list[str]:
    """Affinity Arena's non-destructive writer convention, kept task-local."""
    mismatches = []
    for relative, content in files.items():
        path = output / relative
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError(f"refusing symlink destination: {path}")
        matches = path.is_file() and path.read_text() == content
        if relative.endswith(".sh") and path.exists():
            matches = matches and path.stat().st_mode & 0o111 == 0o111
        if not matches:
            mismatches.append(relative)
        if not check and not matches:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
                stream.write(content)
                tmp = Path(stream.name)
            tmp.chmod(0o755 if relative.endswith(".sh") else 0o644)
            tmp.replace(path)
    steps = output / "steps"
    if steps.exists():
        mismatches.extend(
            str(p.relative_to(output))
            for p in steps.rglob("*")
            if p.is_file() and str(p.relative_to(output)) not in files
        )
    return mismatches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--visibility", choices=MODES, default="hidden")
    parser.add_argument("--output", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = generated_files(args.seed, args.visibility)
    if args.output.resolve() != ROOT:
        for path in (ROOT / "environment").rglob("*"):
            if (
                path.is_file()
                and path.suffix != ".pyc"
                and "__pycache__" not in path.parts
                and path.name != "trial.json"
            ):
                files[str(path.relative_to(ROOT))] = path.read_text()
    mismatch = write_generated(args.output, files, args.check)
    if args.check and mismatch:
        raise SystemExit("Generated files differ: " + ", ".join(mismatch))
    print(
        f"{'Checked' if args.check else 'Generated'} 20 problems, seed {args.seed}, "
        f"visibility {args.visibility}, at {args.output}"
    )


if __name__ == "__main__":
    main()
