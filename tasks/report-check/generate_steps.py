#!/usr/bin/env python3
"""Write job-01 … job-26 and task.toml. Same instruction every step.

  python3 generate_steps.py            # every brief in environment/report/briefs.json
  python3 generate_steps.py --n 8      # smoke run, first 8 jobs
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / "environment" / "report"
STEPS = ROOT / "steps"
INSTRUCTION = (ROOT / "instruction.md").read_text(encoding="utf-8")

sys.dont_write_bytecode = True  # keep .pyc out of the image build context
sys.path.insert(0, str(ENGINE))

from engine import compose_gold, load_briefs, step_name  # noqa: E402

SETUP = """\
#!/usr/bin/env bash
set -euo pipefail
report brief {job_id}
rm -- "$0"
"""

TEST = """\
#!/usr/bin/env bash
set -euo pipefail
REPORT_SETTLE=1 python3 /opt/report/cli.py settle
"""

SOLVE = """\
#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
{gold}REPORT_EOF
report submit
"""

TASK_HEAD = """\
schema_version = "1.4"
artifacts = ["/app/report.md", "/app/brief.md", "/app/notes.md", "/app/desk", "/app/sessions"]
multi_step_reward_strategy = "mean"

[task]
name = "agent-learning-bench/report-check"
version = "0.1.0"
description = "Multi-step report writing against an unpublished house style"
keywords = ["writing", "hidden-rules", "multi-step", "continual-learning"]

[[task.authors]]
name = "Manoj Bajaj"
email = "manoj@example.com"

[metadata]
difficulty = "hard"
category = "writing"
tags = ["hidden-rules", "multi-step", "learning", "holdout"]

[agent]
timeout_sec = 300.0
user = "agent"

[verifier]
timeout_sec = 30.0

[environment]
network_mode = "public"
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
gpus = 0
workdir = "/app"
"""

STEP_BLOCK = """
[[steps]]
name = "{name}"

[steps.agent]
timeout_sec = 300.0

[steps.verifier]
timeout_sec = 30.0
"""


def write_step(brief: dict) -> str:
    name = step_name(brief["id"])
    step = STEPS / name
    if step.exists():
        shutil.rmtree(step)
    (step / "workdir").mkdir(parents=True)
    (step / "tests").mkdir()
    (step / "solution").mkdir()
    (step / "instruction.md").write_text(INSTRUCTION, encoding="utf-8")

    files = {
        step / "workdir" / "setup.sh": SETUP.format(job_id=brief["id"]),
        step / "tests" / "test.sh": TEST,
        step / "solution" / "solve.sh": SOLVE.format(gold=compose_gold(brief)),
    }
    for path, text in files.items():
        path.write_text(text, encoding="utf-8", newline="\n")
        path.chmod(0o755)
    return name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=0, help="first N jobs only (default: all)")
    args = parser.parse_args()

    briefs = sorted(load_briefs(), key=lambda b: b["id"])
    chosen = briefs[: args.n] if args.n else briefs

    if STEPS.exists():
        shutil.rmtree(STEPS)
    STEPS.mkdir()

    parts = [TASK_HEAD]
    for brief in chosen:
        parts.append(STEP_BLOCK.format(name=write_step(brief)))
    (ROOT / "task.toml").write_text("".join(parts), encoding="utf-8", newline="\n")

    holdout = sum(1 for b in chosen if b.get("holdout"))
    print(f"wrote {len(chosen)} steps ({holdout} holdout) and task.toml")


if __name__ == "__main__":
    main()
