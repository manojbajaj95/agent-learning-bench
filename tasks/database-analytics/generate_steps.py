#!/usr/bin/env python3
"""Build Harbor steps from the BIRD Formula 1 question bank.

  python3 generate_steps.py --n 10     # smoke
  python3 generate_steps.py --all      # all formula_1 questions (174)
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
artifacts = ["/app/answer.json", "/app/question.md", "/app/sessions"]
multi_step_reward_strategy = "mean"

[task]
name = "agent-learning-bench/database-analytics"
version = "0.1.0"
description = "Multi-step Formula 1 SQLite question answering"
keywords = ["sqlite", "text-to-sql", "formula-1", "rewardkit", "multi-step"]

[[task.authors]]
name = "Manoj Bajaj"
email = "manoj@example.com"

[metadata]
difficulty = "hard"
category = "databases"
tags = ["sqlite", "multi-step", "learning"]

[agent]
timeout_sec = 180.0
user = "agent"

[verifier]
timeout_sec = 60.0

[environment]
network_mode = "public"
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
gpus = 0
workdir = "/app"
"""


def load_formula_1() -> list[dict]:
    src = DATA / "dev_20251106.json"
    if not src.exists():
        raise SystemExit(f"missing {src}; run ./download.sh first")
    rows = json.loads(src.read_text())
    rows = [r for r in rows if r.get("db_id") == "formula_1"]
    rows.sort(key=lambda r: r["question_id"])
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
        "rewardkit /tests\n"
        "python3 /opt/f1/f1.py costs\n"
    )
    (step / "tests" / "test.sh").chmod(0o755)
    (step / "workdir" / "setup.sh").write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"python3 /opt/f1/f1.py publish {index}\n"
        'rm -- "$0"\n'
    )
    (step / "workdir" / "setup.sh").chmod(0o755)
    sql_lit = json.dumps(item["SQL"])
    (step / "solution" / "solve.sh").write_text(
        "#!/usr/bin/env python3\n"
        "import json, subprocess\n"
        "from pathlib import Path\n"
        f"sql = {sql_lit}\n"
        "raw = subprocess.check_output(['db', 'query', sql], text=True)\n"
        "rows = json.loads(raw.splitlines()[0])\n"
        "if len(rows) == 1 and len(rows[0]) == 1:\n"
        "    answer = rows[0][0]\n"
        "elif rows and all(len(r) == 1 for r in rows):\n"
        "    answer = [r[0] for r in rows]\n"
        "else:\n"
        "    answer = rows\n"
        "Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\\n')\n"
    )
    (step / "solution" / "solve.sh").chmod(0o755)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=10, help="question count (default 10)")
    parser.add_argument("--all", action="store_true", help="use every formula_1 question")
    args = parser.parse_args()
    rows = load_formula_1()
    chosen = rows if args.all else rows[: args.n]
    ENV_DATA.mkdir(parents=True, exist_ok=True)
    sqlite_src = DATA / "formula_1.sqlite"
    if sqlite_src.exists():
        shutil.copy2(sqlite_src, ENV_DATA / "formula_1.sqlite")
    questions = [{"question_id": r["question_id"], "question": r["question"]} for r in chosen]
    gold = [{"question_id": r["question_id"], "SQL": r["SQL"]} for r in chosen]
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
                timeout_sec = 60.0
                """
            )
        )
    (ROOT / "task.toml").write_text("\n".join(parts) + "\n")
    print(f"wrote {len(chosen)} steps (formula_1 has {len(rows)})")


if __name__ == "__main__":
    main()
