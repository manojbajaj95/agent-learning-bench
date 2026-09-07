#!/usr/bin/env python3
"""Run twenty matched battles in separate Harbor sandboxes; never resume an agent."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

from analyze import METRICS, analyze_job, report
from generate_steps import write_generated
from run_matrix import PI_VERSION, REPO, TASK, task_digest


def isolated_files(task: Path, index: int) -> dict[str, str]:
    """Keep the original chart, matchup, instructions, and verifier for battle N."""
    name = f"battle-{index:02d}"
    trial = json.loads((task / "environment/trial.json").read_text())
    if not 1 <= index <= len(trial["battles"]):
        raise ValueError("battle index is out of range")
    trial["isolated_battle"] = index
    config, *steps = (task / "task.toml").read_text().split("\n[[steps]]")
    selected = [s for s in steps if f'name = "{name}"' in s.splitlines()]
    if len(selected) != 1:
        raise ValueError(f"expected exactly one task step named {name}")
    files = {"task.toml": config + "\n[[steps]]" + selected[0]}
    for folder in (task / "environment", task / "steps" / name):
        for path in folder.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                files[str(path.relative_to(task))] = path.read_text()
    files["environment/trial.json"] = json.dumps(trial, indent=2) + "\n"
    marker = "/opt/affinity-arena/admin.py start 1 > /dev/null"
    if files["environment/Dockerfile"].count(marker) != 1:
        raise ValueError("unsupported Dockerfile: expected the initial battle setup")
    files["environment/Dockerfile"] = files["environment/Dockerfile"].replace(
        marker, f"/opt/affinity-arena/admin.py start {index} > /dev/null"
    )
    return files


def command_for(harbor: str, root: Path, index: int, model: str, oracle: bool) -> list[str]:
    name = f"battle-{index:02d}"
    command = [
        harbor,
        "run",
        "-p",
        str(root / "tasks" / name),
        "--jobs-dir",
        str(root / "runs"),
        "--job-name",
        name,
        "-a",
        "oracle" if oracle else "affinity_agent:PiTrajectoryAgent",
        "-n",
        "1",
        "--max-retries",
        "0",
    ]
    if not oracle:
        command += ["-m", model, "--ak", f"version={PI_VERSION}", "--agent-timeout-multiplier", "5"]
        if os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE"):
            command += ["--ak", "model_api=openai-responses"]
    return command


def collect_result(root: Path, index: int, aggregate: dict) -> bool:
    """Preserve raw step results, including failures; never substitute an attempt."""
    name = f"battle-{index:02d}"
    paths = list((root / "runs" / name).glob("*/result.json"))
    if len(paths) != 1:
        raise ValueError(f"{name}: expected one trial result, found {len(paths)}")
    result = json.loads(paths[0].read_text())
    steps = result.get("step_results") or []
    if len(steps) != 1 or steps[0].get("step_name") != name:
        raise ValueError(f"{name}: expected exactly one matching battle result")
    aggregate["step_results"].extend(steps)
    aggregate["source_results"].append(str(paths[0].relative_to(root)))
    if result.get("exception_info"):
        aggregate["exception_info"] = result["exception_info"]
    rewards = (steps[0].get("verifier_result") or {}).get("rewards") or {}
    return (
        not result.get("exception_info")
        and not steps[0].get("exception_info")
        and rewards.get("completed") == 1
        and all(k in rewards for k in METRICS)
    )


def save_report(root: Path, aggregate: dict) -> None:
    (root / "no-memory.json").write_text(json.dumps(aggregate, indent=2) + "\n")
    summaries = analyze_job(root)
    (root / "comparison.json").write_text(json.dumps(summaries, indent=2) + "\n")
    (root / "comparison.md").write_text(report(summaries))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--job-name", required=True, help="new name; existing output is never overwritten"
    )
    parser.add_argument("--model", default="google/gemini-3.5-flash")
    parser.add_argument("--task", type=Path, default=TASK)
    parser.add_argument("--jobs-dir", type=Path, default=REPO / "jobs")
    parser.add_argument(
        "--oracle", action="store_true", help="keyless correctness run, not an LLM baseline"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print commands without writing files or calling APIs",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.job_name):
        parser.error("job-name must be a simple slug")
    if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9][A-Za-z0-9._/-]*", args.model):
        parser.error("model must be provider/model-id without shell metacharacters")
    root = args.jobs_dir.resolve() / args.job_name
    if root.exists():
        parser.error("output already exists; choose a new job name")
    harbor = str(Path(sys.executable).parent / "harbor")
    commands = [command_for(harbor, root, i, args.model, args.oracle) for i in range(1, 21)]
    if args.dry_run:
        for command in commands:
            print(shlex.join(command))
        return
    if not Path(harbor).is_file():
        parser.error("run with .venv/bin/python after installing requirements-dev.txt")
    task = args.task.resolve()
    trial = json.loads((task / "environment/trial.json").read_text())
    if [b["index"] for b in trial["battles"]] != list(range(1, 21)):
        parser.error("expected the complete twenty-battle source task")
    fingerprint = task_digest(task)
    root.mkdir(parents=True, exist_ok=False)
    # Generate all isolated tasks before spending tokens. None includes prior
    # agent output; each Harbor invocation creates a fresh container and logs.
    for index in range(1, 21):
        write_generated(root / "tasks" / f"battle-{index:02d}", isolated_files(task, index), False)
    aggregate = {
        "task_name": "agent-learning-bench/affinity-arena",
        "trial_name": "no-memory",
        "condition": "no-memory-oracle" if args.oracle else "no-memory",
        "model": None if args.oracle else args.model,
        "pi_version": PI_VERSION,
        "seed": trial["seed"],
        "instance_sha256": fingerprint,
        "step_results": [],
        "source_results": [],
    }
    env = dict(os.environ)
    env["PYTHONPATH"] = str(TASK) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    save_report(root, aggregate)
    for index, command in enumerate(commands, 1):
        if task_digest(task) != fingerprint:
            raise SystemExit("source task changed; refusing a mismatched comparison")
        print(f"No-memory battle {index}/20 (fresh sandbox)", flush=True)
        try:
            process = subprocess.run(command, cwd=REPO, env=env, check=False)
            complete = collect_result(root, index, aggregate)
            if process.returncode:
                raise ValueError(f"Harbor exited with code {process.returncode}")
            if args.oracle and complete:
                rewards = aggregate["step_results"][-1]["verifier_result"]["rewards"]
                best = trial["battles"][index - 1]["oracle_value"]
                if not (
                    rewards["won"] == rewards["opt_rate"] == rewards["draft_ok"] == 1
                    and rewards["regret"] == 0
                    and rewards["ticks"] == -best[1]
                    and rewards["reward"] == best[0] / 4200
                ):
                    raise ValueError("oracle correctness check failed")
        except (ValueError, OSError) as exc:
            complete = False
            aggregate["exception_info"] = {
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            }
        finally:
            save_report(root, aggregate)
        if not complete:
            raise SystemExit(
                f"Battle {index} failed or was incomplete; inspect {root / 'comparison.md'}"
            )
    print(f"Report: {root / 'comparison.md'}")


if __name__ == "__main__":
    main()
