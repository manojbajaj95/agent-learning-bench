#!/usr/bin/env python3
"""Build Harbor steps for the Kestrel Depot intranet.

  python3 generate_steps.py --n 10     # smoke
  python3 generate_steps.py --all      # all 30 jobs
"""

from __future__ import annotations

import argparse
import json
import shutil
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_DATA = ROOT / "environment" / "data"
PAGES = ROOT / "environment" / "web" / "pages.py"
STEPS = ROOT / "steps"
INSTRUCTION = (ROOT / "instruction.md").read_text()
TASK_TOML_HEAD = """\
schema_version = "1.4"
artifacts = ["/app/answer.json", "/app/question.md", "/app/notes.md", "/app/sessions"]
multi_step_reward_strategy = "mean"

[task]
name = "agent-learning-bench/web-exploration"
version = "0.1.0"
description = "Multi-step intranet question answering and form jobs"
keywords = ["web", "intranet", "qa", "forms", "rewardkit", "multi-step"]

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


def load_jobs() -> list[dict]:
    src = ROOT / "questions.json"
    rows = json.loads(src.read_text())
    if not rows:
        raise SystemExit(f"empty {src}")
    return rows


def validate(rows: list[dict]) -> None:
    blob = PAGES.read_text().casefold()
    for i, row in enumerate(rows, start=1):
        kind = row.get("kind")
        if kind == "qa":
            answer = str(row.get("answer") or "")
            if answer.casefold() not in blob:
                raise SystemExit(f"q-{i:03d}: gold {answer!r} is not on the site")
        elif kind == "action":
            endpoint = row.get("endpoint") or ""
            if endpoint.casefold() not in blob:
                raise SystemExit(f"q-{i:03d}: form {endpoint!r} is not on the site")
            if not row.get("fields"):
                raise SystemExit(f"q-{i:03d}: action is missing fields")
        else:
            raise SystemExit(f"q-{i:03d}: unknown kind {kind!r}")


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
        "python3 /opt/web/web.py costs\n"
    )
    (step / "tests" / "test.sh").chmod(0o755)
    (step / "workdir" / "setup.sh").write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"python3 /opt/web/web.py publish {index}\n"
        'rm -- "$0"\n'
    )
    (step / "workdir" / "setup.sh").chmod(0o755)
    if item["kind"] == "action":
        endpoint = json.dumps(item["endpoint"])
        fields = json.dumps(item["fields"])
        (step / "solution" / "solve.sh").write_text(
            "#!/usr/bin/env python3\n"
            "import json, re, subprocess\n"
            "from pathlib import Path\n"
            f"endpoint = {endpoint}\n"
            f"fields = {fields}\n"
            "args = ['web', 'post', endpoint]\n"
            "args.extend(f'{k}={v}' for k, v in fields.items())\n"
            "raw = subprocess.check_output(args, text=True)\n"
            "match = re.search(r'Confirmation: <strong>([^<]+)</strong>', raw)\n"
            "if not match:\n"
            "    raise SystemExit('no confirmation code')\n"
            "Path('/app/answer.json').write_text("
            "json.dumps({'answer': match.group(1)}) + '\\n')\n"
        )
    else:
        payload = json.dumps({"answer": item["answer"]})
        (step / "solution" / "solve.sh").write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            f"Path('/app/answer.json').write_text({payload!r} + '\\n')\n"
        )
    (step / "solution" / "solve.sh").chmod(0o755)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=10, help="job count (default 10)")
    parser.add_argument("--all", action="store_true", help="use every job")
    args = parser.parse_args()
    rows = load_jobs()
    validate(rows)
    chosen = rows if args.all else rows[: args.n]
    ENV_DATA.mkdir(parents=True, exist_ok=True)
    questions = [
        {"question_id": i, "kind": r["kind"], "question": r["question"]}
        for i, r in enumerate(chosen, start=1)
    ]
    gold = []
    for i, r in enumerate(chosen, start=1):
        item = {"question_id": i, "kind": r["kind"]}
        if r["kind"] == "qa":
            item["answer"] = r["answer"]
        else:
            item["endpoint"] = r["endpoint"]
            item["fields"] = r["fields"]
        gold.append(item)
    (ENV_DATA / "questions.json").write_text(json.dumps(questions, indent=2) + "\n")
    (ENV_DATA / "gold.json").write_text(json.dumps(gold, indent=2) + "\n")
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
    holdout = max(1, round(len(rows) * 0.1))
    print(
        f"wrote {len(chosen)} steps "
        f"(bank has {len(rows)}; last {holdout} of --all are holdout)"
    )


if __name__ == "__main__":
    main()
