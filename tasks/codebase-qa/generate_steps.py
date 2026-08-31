#!/usr/bin/env python3
"""Build Harbor steps from the SWE-QA Flask question bank.

  python3 generate_steps.py --n 10     # smoke
  python3 generate_steps.py --all      # all 48 Flask questions
"""

from __future__ import annotations

import argparse
import json
import shutil
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ENV_DATA = ROOT / "environment" / "data"
STEPS = ROOT / "steps"
INSTRUCTION = (ROOT / "instruction.md").read_text()
TASK_TOML_HEAD = """\
schema_version = "1.4"
artifacts = ["/app/answer.json", "/app/question.md", "/app/notes.md", "/app/sessions"]
multi_step_reward_strategy = "mean"

[task]
name = "agent-learning-bench/codebase-qa"
version = "0.1.0"
description = "Multi-step Flask repository question answering"
keywords = ["codebase", "flask", "qa", "rewardkit", "multi-step"]

[[task.authors]]
name = "Manoj Bajaj"
email = "manoj@example.com"

[metadata]
difficulty = "hard"
category = "programming"
tags = ["codebase", "multi-step", "learning"]

[agent]
timeout_sec = 180.0
user = "agent"

[verifier]
timeout_sec = 180.0

[verifier.env]
OPENAI_API_KEY = "${OPENAI_API_KEY}"

[environment]
network_mode = "public"
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
gpus = 0
workdir = "/app"
"""


def load_flask() -> list[dict]:
    src = DATA / "flask.jsonl"
    if not src.exists():
        raise SystemExit(f"missing {src}; run ./download.sh first")
    rows = []
    for line in src.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_step(index: int, item: dict) -> None:
    name = f"q-{index:03d}"
    step = STEPS / name
    if step.exists():
        shutil.rmtree(step)
    (step / "workdir").mkdir(parents=True)
    (step / "tests").mkdir()
    (step / "solution").mkdir()
    (step / "instruction.md").write_text(INSTRUCTION)
    (step / "tests" / "test.sh").write_text(
        "#!/bin/bash\nset -euo pipefail\n"
        "python3 /opt/qa/qa.py write-reference\n"
        "rewardkit /tests\n"
        "python3 /opt/qa/qa.py costs\n"
    )
    (step / "tests" / "test.sh").chmod(0o755)
    (step / "workdir" / "setup.sh").write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"python3 /opt/qa/qa.py publish {index}\n"
        'rm -- "$0"\n'
    )
    (step / "workdir" / "setup.sh").chmod(0o755)
    payload = json.dumps({"answer": item["answer"]})
    (step / "solution" / "solve.sh").write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        f"Path('/app/answer.json').write_text({payload!r} + '\\n')\n"
    )
    (step / "solution" / "solve.sh").chmod(0o755)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=10, help="question count (default 10)")
    parser.add_argument("--all", action="store_true", help="use every Flask question")
    args = parser.parse_args()
    rows = load_flask()
    chosen = rows if args.all else rows[: args.n]
    repo_src = DATA / "repo"
    if not repo_src.exists():
        raise SystemExit(f"missing {repo_src}; run ./download.sh first")
    if ENV_DATA.exists():
        shutil.rmtree(ENV_DATA)
    ENV_DATA.mkdir(parents=True)
    shutil.copytree(repo_src, ENV_DATA / "repo")
    questions = [{"question_id": i, "question": r["question"]} for i, r in enumerate(chosen, start=1)]
    gold = [{"question_id": i, "answer": r["answer"]} for i, r in enumerate(chosen, start=1)]
    (ENV_DATA / "questions.json").write_text(json.dumps(questions, indent=2) + "\n")
    (ENV_DATA / "gold.json").write_text(json.dumps(gold, indent=2) + "\n")
    (DATA / "questions.json").write_text(json.dumps(questions, indent=2) + "\n")
    (DATA / "gold.json").write_text(json.dumps(gold, indent=2) + "\n")
    if STEPS.exists():
        shutil.rmtree(STEPS)
    STEPS.mkdir()
    parts = [TASK_TOML_HEAD]
    for i, item in enumerate(chosen, start=1):
        write_step(i, item)
        name = f"q-{i:03d}"
        parts.append(
            textwrap.dedent(
                f"""
                [[steps]]
                name = "{name}"

                [steps.agent]
                timeout_sec = 180.0

                [steps.verifier]
                timeout_sec = 180.0
                """
            )
        )
    (ROOT / "task.toml").write_text("\n".join(parts) + "\n")
    print(f"wrote {len(chosen)} steps (flask has {len(rows)})")


if __name__ == "__main__":
    main()
