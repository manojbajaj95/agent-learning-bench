#!/usr/bin/env python3
"""Run oracle, baseline, pi-sessions, and resumed Pi with one immutable task/model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from analyze import analyze_job, report

TASK = Path(__file__).resolve().parent
REPO = TASK.parents[1]
PI_VERSION = "0.85.1"


def task_digest(task: Path) -> str:
    """Hash runnable inputs only, excluding reports and Python caches."""
    digest = hashlib.sha256()
    paths = [task / "task.toml"]
    for directory in ("environment", "steps"):
        paths.extend(
            p
            for p in (task / directory).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )
    for path in sorted(paths):
        digest.update(str(path.relative_to(task)).encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def commands(
    harbor: str,
    task: Path,
    jobs: Path,
    prefix: str,
    model: str,
    pi_version: str,
    custom_endpoint: bool,
) -> list[tuple[str, list[str]]]:
    common = [
        harbor,
        "run",
        "-p",
        str(task),
        "--jobs-dir",
        str(jobs),
        "--max-retries",
        "0",
        "-n",
        "1",
    ]
    result = []
    for condition, agent in (
        ("oracle", "oracle"),
        ("baseline", "agents.pi_trajectory:PiTrajectoryAgent"),
        ("sessions", "agents.pi_sessions:PiSessionsAgent"),
        ("icl", "agents.pi_trajectory:PiTrajectoryAgent"),
    ):
        command = [*common, "--job-name", f"{prefix}-{condition}", "-a", agent]
        if condition != "oracle":
            command.extend(
                ["-m", model, "--agent-timeout-multiplier", "5", "--ak", f"version={pi_version}"]
            )
            if custom_endpoint:
                command.extend(["--ak", "model_api=openai-responses"])
        if condition == "icl":
            command.append("--resume-trajectory")
        result.append((condition, command))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", required=True, help="openai/<model-id>; used unchanged for all conditions"
    )
    parser.add_argument("--task", type=Path, default=TASK)
    parser.add_argument("--jobs-dir", type=Path, default=REPO / "jobs")
    parser.add_argument("--prefix", default="affinity-arena")
    parser.add_argument("--pi-version", default=PI_VERSION)
    parser.add_argument("--out-dir", type=Path, default=TASK / "results" / "matrix")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print commands without requiring credentials or spending tokens",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"openai/[A-Za-z0-9][A-Za-z0-9._/-]*", args.model):
        parser.error("model must be openai/<model-id>, without shell metacharacters")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.prefix):
        parser.error("prefix must be a simple job-name slug")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", args.pi_version):
        parser.error("pi-version must be an exact version, such as 0.85.1")
    local_harbor = Path(sys.executable).parent / "harbor"
    harbor = (
        str(local_harbor) if local_harbor.is_file() else shutil.which("harbor") or str(local_harbor)
    )
    endpoint = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
    if endpoint:
        parsed = urlparse(endpoint)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            parser.error(
                "base URL must be an HTTP(S) endpoint without embedded credentials, query, or fragment"
            )
    runs = commands(
        harbor,
        args.task.resolve(),
        args.jobs_dir.resolve(),
        args.prefix,
        args.model,
        args.pi_version,
        bool(endpoint),
    )
    if args.dry_run:
        for _, command in runs:
            print(shlex.join(command))
        return
    if not os.environ.get("OPENAI_API_KEY"):
        parser.error(
            "set OPENAI_API_KEY in your shell before running the matrix; --dry-run needs no key"
        )
    if not Path(harbor).is_file():
        parser.error("Harbor is missing; install requirements-dev.txt in your virtual environment")
    if any((args.jobs_dir / f"{args.prefix}-{condition}").exists() for condition, _ in runs):
        parser.error("a target job already exists; choose a new --prefix to preserve previous runs")
    digest = task_digest(args.task)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    trials = []
    for condition, command in runs:
        if task_digest(args.task) != digest:
            raise SystemExit(
                "Task instance changed during the matrix; refusing a mismatched comparison"
            )
        print(f"Running {condition}", flush=True)
        subprocess.run(command, cwd=REPO, env=env, check=True)
        results = analyze_job(args.jobs_dir / f"{args.prefix}-{condition}")
        if len(results) != 1 or results[0]["issues"]:
            raise SystemExit(
                f"{condition} did not produce one complete 20-battle trial; inspect its logs"
            )
        if condition == "oracle" and any(
            s["rewards"]["won"] != 1
            or s["rewards"]["regret"] != 0
            or s["rewards"]["opt_rate"] != 1
            or s["rewards"]["draft_ok"] != 1
            or s["rewards"]["ticks"] != s["rewards"]["oracle_ticks"]
            for s in results[0]["steps"]
        ):
            raise SystemExit("Oracle correctness check failed; model runs were not started")
        trials.extend(results)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "comparison.md").write_text(report(trials))
        (args.out_dir / "comparison.json").write_text(json.dumps(trials, indent=2) + "\n")
    (args.out_dir / "matrix.json").write_text(
        json.dumps(
            {
                "model": args.model,
                "pi_version": args.pi_version,
                "instance_sha256": digest,
                "jobs": [f"{args.prefix}-{condition}" for condition, _ in runs],
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Manual review: {args.out_dir / 'comparison.md'}")


if __name__ == "__main__":
    main()
