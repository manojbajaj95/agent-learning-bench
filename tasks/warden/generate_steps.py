#!/usr/bin/env python3
"""Write fight-01 … fight-10 and task.toml. Same instruction every step."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = ROOT / "steps"
INSTRUCTION = (ROOT / "instruction.md").read_text()
N = 10

SETUP = """\
#!/usr/bin/env bash
set -euo pipefail
export WARDEN_SETUP=1
python3 /opt/warden/cli.py start {fight}
rm -- "$0"
"""

TEST = """\
#!/usr/bin/env bash
set -euo pipefail
python3 /opt/warden/cli.py settle
"""

SOLVE = """\
#!/usr/bin/env bash
set -euo pipefail
warden dodge left
warden dodge left
warden jump
warden attack
warden dodge left
warden dodge left
warden jump
warden attack
"""

TASK_HEAD = """\
schema_version = "1.4"
artifacts = ["/app/fights", "/app/notes.md", "/app/view.txt", "/app/sessions"]
multi_step_reward_strategy = "mean"

[task]
name = "agent-learning-bench/warden"
version = "0.1.0"
description = "Multi-step hidden-policy duel. Same boss, ten fights."
keywords = ["warden", "pygame", "multi-step", "opponent-modeling"]

[[task.authors]]
name = "Manoj Bajaj"
email = "manoj@example.com"

[metadata]
difficulty = "hard"
category = "games"
tags = ["pygame", "multi-step", "learning", "hidden-policy"]

[agent]
timeout_sec = 180.0

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


def main() -> None:
    if STEPS.exists():
        for child in STEPS.iterdir():
            if child.is_dir():
                for p in child.rglob("*"):
                    if p.is_file():
                        p.unlink()
                for p in sorted(child.rglob("*"), reverse=True):
                    if p.is_dir():
                        p.rmdir()
                child.rmdir()
    STEPS.mkdir(parents=True, exist_ok=True)

    parts = [TASK_HEAD]
    for i in range(1, N + 1):
        name = f"fight-{i:02d}"
        fight = f"{i:02d}"
        step = STEPS / name
        (step / "workdir").mkdir(parents=True)
        (step / "tests").mkdir()
        (step / "solution").mkdir()
        (step / "instruction.md").write_text(INSTRUCTION)
        (step / "workdir" / "setup.sh").write_text(SETUP.format(fight=fight))
        (step / "tests" / "test.sh").write_text(TEST)
        (step / "solution" / "solve.sh").write_text(SOLVE)
        for script in (
            step / "workdir" / "setup.sh",
            step / "tests" / "test.sh",
            step / "solution" / "solve.sh",
        ):
            script.chmod(0o755)
        parts.append(
            f'\n[[steps]]\nname = "{name}"\n\n'
            "[steps.agent]\ntimeout_sec = 180.0\n\n"
            "[steps.verifier]\ntimeout_sec = 30.0\n"
        )

    (ROOT / "task.toml").write_text("".join(parts))
    print(f"wrote {N} steps and task.toml")


if __name__ == "__main__":
    main()
