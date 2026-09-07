#!/usr/bin/env python3
"""Build Harbor steps from pinned WebArena-Verified shopping tasks.

  python3 generate_steps.py --check   # validate pinned dataset
  python3 generate_steps.py --n 3     # smoke subset
  python3 generate_steps.py           # all 187 tasks
"""

from __future__ import annotations

import argparse
import json
import shutil
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATASET = DATA / "webarena-verified.json"
STEPS = ROOT / "steps"
INSTRUCTION = (ROOT / "instruction.md").read_text()
TASK_TOML_HEAD = """\
schema_version = "1.4"
artifacts = ["/app/answer.json", "/app/question.md", "/app/notes.md", "/app/sessions"]
multi_step_reward_strategy = "mean"

[task]
name = "agent-learning-bench/web-exploration"
version = "0.1.0"
description = "Multi-step WebArena shopping tasks"
keywords = ["web", "shopping", "webarena", "multi-step"]

[[task.authors]]
name = "Manoj Bajaj"
email = "manoj@example.com"

[metadata]
difficulty = "medium"
category = "web"
tags = ["web", "multi-step", "learning"]

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


def load_shopping_tasks(path: Path) -> list[dict]:
    rows = json.loads(path.read_text())
    tasks = [row for row in rows if row.get("sites") == ["shopping"]]
    seen: set[int] = set()
    for task in tasks:
        task_id = int(task["task_id"])
        if task_id in seen:
            raise ValueError(f"duplicate task_id {task_id}")
        if not task.get("intent") or not task.get("start_urls"):
            raise ValueError(f"task {task_id} is missing agent input")
        seen.add(task_id)
    return tasks


def agent_input(task: dict) -> dict:
    return {
        "task_id": task["task_id"],
        "intent_template_id": task["intent_template_id"],
        "sites": task["sites"],
        "start_urls": task["start_urls"],
        "intent": task["intent"],
    }


def write_step(task: dict) -> str:
    task_id = int(task["task_id"])
    name = f"task-{task_id:04d}"
    step = STEPS / name
    if step.exists():
        shutil.rmtree(step)
    (step / "workdir").mkdir(parents=True)
    (step / "tests").mkdir()
    (step / "solution").mkdir()
    (step / "instruction.md").write_text(INSTRUCTION)
    (step / "workdir" / "setup.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nrm -- \"$0\"\n"
    )
    (step / "workdir" / "setup.sh").chmod(0o755)
    (step / "tests" / "test.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
    )
    (step / "tests" / "test.sh").chmod(0o755)
    return name


def generate(tasks: list[dict], root: Path, limit: int | None) -> None:
    chosen = tasks if limit is None else tasks[:limit]
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    agent_rows = [agent_input(task) for task in chosen]
    (data_dir / "agent-input.json").write_text(json.dumps(agent_rows, indent=2) + "\n")

    steps_dir = root / "steps"
    if steps_dir.exists():
        shutil.rmtree(steps_dir)
    steps_dir.mkdir()

    parts = [TASK_TOML_HEAD]
    for task in chosen:
        name = write_step(task)
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
    (root / "task.toml").write_text("\n".join(parts) + "\n")
    print(f"wrote {len(chosen)} steps")


def check() -> None:
    if not DATASET.is_file():
        raise SystemExit(f"missing {DATASET}; run ./download.sh first")
    tasks = load_shopping_tasks(DATASET)
    if len(tasks) != 187:
        raise SystemExit(f"expected 187 shopping-only tasks, got {len(tasks)}")
    print("187 shopping-only tasks")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate pinned dataset")
    parser.add_argument("--n", type=int, default=None, help="generate first N tasks")
    args = parser.parse_args()

    if args.check:
        check()
        return

    if not DATASET.is_file():
        raise SystemExit(f"missing {DATASET}; run ./download.sh first")
    tasks = load_shopping_tasks(DATASET)
    generate(tasks, ROOT, args.n)


if __name__ == "__main__":
    main()
