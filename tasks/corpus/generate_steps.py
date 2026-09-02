#!/usr/bin/env python3
"""Build Harbor steps from EnterpriseRAG-Bench Confluence questions.

  python3 generate_steps.py --n 10     # smoke
  python3 generate_steps.py --all      # all confluence-only questions (64)
"""

from __future__ import annotations

import argparse
import json
import shutil
import textwrap
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ENV_DATA = ROOT / "environment" / "data"
STEPS = ROOT / "steps"
ZIPS = ("confluence_slice_0001.zip", "confluence_slice_0002.zip")
INSTRUCTION = (ROOT / "instruction.md").read_text()
TASK_TOML_HEAD = """\
schema_version = "1.4"
artifacts = ["/app/answer.json", "/app/question.md", "/app/notes.md", "/app/sessions"]
multi_step_reward_strategy = "mean"

[task]
name = "agent-learning-bench/corpus"
version = "0.1.0"
description = "Multi-step Confluence wiki question answering"
keywords = ["corpus", "confluence", "qa", "rewardkit", "multi-step"]

[[task.authors]]
name = "Manoj Bajaj"
email = "manoj@example.com"

[metadata]
difficulty = "hard"
category = "retrieval"
tags = ["corpus", "multi-step", "learning"]

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


def load_confluence() -> list[dict]:
    src = DATA / "questions.jsonl"
    if not src.exists():
        raise SystemExit(f"missing {src}; run ./download.sh first")
    rows = []
    for line in src.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return [r for r in rows if r.get("source_types") == ["confluence"]]


def corpus_ids() -> set[str]:
    ids: set[str] = set()
    for name in ZIPS:
        path = DATA / name
        if not path.exists():
            raise SystemExit(f"missing {path}; run ./download.sh first")
        with zipfile.ZipFile(path) as zf:
            for member in zf.namelist():
                base = Path(member).name
                if base.startswith("dsid_"):
                    ids.add(base.split("__", 1)[0])
    return ids


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
        "python3 /opt/corpus/corpus.py write-reference\n"
        "rewardkit /tests\n"
        "python3 /opt/corpus/corpus.py costs\n"
    )
    (step / "tests" / "test.sh").chmod(0o755)
    (step / "workdir" / "setup.sh").write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"python3 /opt/corpus/corpus.py publish {index}\n"
        'rm -- "$0"\n'
    )
    (step / "workdir" / "setup.sh").chmod(0o755)
    payload = json.dumps({"answer": item["gold_answer"]})
    (step / "solution" / "solve.sh").write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        f"Path('/app/answer.json').write_text({payload!r} + '\\n')\n"
    )
    (step / "solution" / "solve.sh").chmod(0o755)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=10, help="question count (default 10)")
    parser.add_argument("--all", action="store_true", help="use every confluence-only question")
    args = parser.parse_args()
    rows = load_confluence()
    ids = corpus_ids()
    for item in rows:
        missing = [d for d in item.get("expected_doc_ids") or [] if d not in ids]
        if missing:
            raise SystemExit(f"{item['question_id']} missing wiki pages: {missing}")
    chosen = rows if args.all else rows[: args.n]
    if ENV_DATA.exists():
        shutil.rmtree(ENV_DATA)
    ENV_DATA.mkdir(parents=True)
    for name in ZIPS:
        shutil.copy2(DATA / name, ENV_DATA / name)
    questions = [
        {
            "question_id": i,
            "source_id": r["question_id"],
            "question": r["question"],
        }
        for i, r in enumerate(chosen, start=1)
    ]
    gold = [
        {
            "question_id": i,
            "answer": r["gold_answer"],
        }
        for i, r in enumerate(chosen, start=1)
    ]
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
                timeout_sec = 180.0
                """
            )
        )
    (ROOT / "task.toml").write_text("\n".join(parts) + "\n")
    print(f"wrote {len(chosen)} steps (confluence-only has {len(rows)})")


if __name__ == "__main__":
    main()
