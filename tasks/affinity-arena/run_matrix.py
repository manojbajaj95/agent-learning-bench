#!/usr/bin/env python3
"""Run a matched memory comparison or the legacy four-condition agent matrix."""

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
from memory_report import validate_pairs, write_comparison

TASK = Path(__file__).resolve().parent
REPO = TASK.parents[1]
PI_VERSION = "0.85.1"
PLAY_THINKING = "low"


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
        ("baseline", "affinity_agent:PiTrajectoryAgent"),
        ("sessions", "affinity_agent:PiSessionsAgent"),
        ("icl", "affinity_agent:PiTrajectoryAgent"),
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


def memory_commands(
    harbor: str, task: Path, jobs: Path, prefix: str, model: str, custom_endpoint: bool
) -> list[tuple[str, list[str]]]:
    """Same Pi version/settings; only cross-battle memory differs."""
    baseline = [
        sys.executable,
        str(TASK / "run_no_memory.py"),
        "--task",
        str(task),
        "--jobs-dir",
        str(jobs),
        "--job-name",
        f"{prefix}-no-memory",
        "--model",
        model,
    ]
    learning = dict(commands(harbor, task, jobs, prefix, model, PI_VERSION, custom_endpoint))["icl"]
    learning[learning.index("--job-name") + 1] = f"{prefix}-learning"
    learning.extend(["--ak", f"thinking={PLAY_THINKING}"])
    return [("no-memory", baseline), ("learning", learning)]


def memory_report(jobs: Path, prefix: str, output: Path, invalid_reason: str | None = None) -> bool:
    """Regenerate from saved results only; never compare incomplete attempts."""
    trials, problems = [], [invalid_reason] if invalid_reason else []
    for condition in ("no-memory", "learning"):
        job = jobs / f"{prefix}-{condition}"
        try:
            rows = analyze_job(job)
        except (OSError, ValueError) as exc:
            problems.append(f"{job.name}: cannot read results: {exc}")
            continue
        if len(rows) != 1:
            problems.append(f"{job.name}: expected one trial, found {len(rows)}")
        else:
            trials.extend(rows)
            problems.extend(f"{job.name}: {issue}" for issue in rows[0]["issues"])
    seed = None
    try:
        seed = json.loads((jobs / f"{prefix}-no-memory/no-memory.json").read_text()).get("seed")
    except (OSError, ValueError):
        pass  # Missing/damaged results have already been flagged above.
    return write_comparison([{"seed": seed, "trials": trials}], output, problems)


def read_pair(
    directory: Path, *, model: str, seed: int | None = None, digest: str | None = None
) -> dict:
    """Only complete, matched pairs may be reused or aggregated."""
    manifest = json.loads((directory / "matrix.json").read_text())
    if manifest.get("mode") != "memory-comparison" or manifest.get("status") != "complete":
        raise ValueError(f"{directory}: pair is not complete")
    for key, value in (("model", model), ("pi_version", PI_VERSION), ("thinking", PLAY_THINKING)):
        if manifest.get(key) != value:
            raise ValueError(f"{directory}: mismatched {key}")
    jobs, prefix = Path(manifest["jobs_dir"]), manifest["prefix"]
    metadata = json.loads((jobs / f"{prefix}-no-memory/no-memory.json").read_text())
    if type(metadata.get("seed")) is not int or (seed is not None and metadata["seed"] != seed):
        raise ValueError(f"{directory}: missing or mismatched seed")
    for key in ("model", "pi_version", "thinking", "instance_sha256"):
        if metadata.get(key) != manifest.get(key):
            raise ValueError(f"{directory}: no-memory {key} disagrees with pair manifest")
    if digest is not None and manifest.get("instance_sha256") != digest:
        raise ValueError(f"{directory}: task fingerprint differs from generated seed")
    trials = []
    for condition in ("no-memory", "learning"):
        rows = analyze_job(jobs / f"{prefix}-{condition}")
        if len(rows) != 1 or rows[0]["issues"]:
            raise ValueError(f"{directory}: {condition} has incomplete or invalid results")
        trials.extend(rows)
    pair = {"seed": metadata["seed"], "trials": trials}
    validate_pairs([pair])
    return pair


def seed_report(output: Path, manifest: dict) -> bool:
    problems = (
        []
        if manifest["status"] == "complete"
        else [manifest.get("error", "Seed sweep has not completed")]
    )
    pairs = []
    for entry in manifest["pairs"]:
        try:
            pairs.append(
                read_pair(
                    Path(entry["report_dir"]),
                    model=manifest["model"],
                    seed=entry["seed"],
                    digest=entry.get("instance_sha256"),
                )
            )
        except (OSError, ValueError, KeyError) as exc:
            problems.append(f"Seed {entry['seed']}: {exc}")
    return write_comparison(pairs, output, problems)


def run_seeds(args, parser) -> None:
    if not args.compare_memory or args.task.resolve() != TASK:
        parser.error("--seeds requires --compare-memory and the default source task")
    if len(args.seeds) < 2 or len(set(args.seeds)) != len(args.seeds) or min(args.seeds) < 0:
        parser.error("supply at least two distinct nonnegative seeds")
    reused = {}
    for directory in args.reuse:
        try:
            seed = read_pair(directory.resolve(), model=args.model)["seed"]
        except (OSError, ValueError, KeyError) as exc:
            parser.error(f"cannot reuse {directory}: {exc}")
        if seed not in args.seeds or seed in reused:
            parser.error("each reused pair must have a distinct requested seed")
        reused[seed] = directory.resolve()
    entries = [
        {
            "seed": seed,
            "reused": seed in reused,
            "task": str(args.out_dir / "tasks" / f"seed-{seed}"),
            "report_dir": str(reused.get(seed, args.out_dir / f"seed-{seed}")),
        }
        for seed in args.seeds
    ]
    plans = []
    for entry in entries:
        seed = entry["seed"]
        generate = [
            sys.executable,
            str(TASK / "generate_steps.py"),
            "--seed",
            str(seed),
            "--output",
            entry["task"],
        ]
        run = [
            sys.executable,
            str(TASK / "run_matrix.py"),
            "--compare-memory",
            "--model",
            args.model,
            "--task",
            entry["task"],
            "--jobs-dir",
            str(args.jobs_dir),
            "--prefix",
            f"{args.prefix}-seed-{seed}",
            "--out-dir",
            entry["report_dir"],
        ]
        plans.append((entry, generate, run))
    if args.dry_run:
        for entry, generate, run in plans:
            print(shlex.join(generate))
            print(
                f"Reuse seed {entry['seed']}: {entry['report_dir']}"
                if entry["reused"]
                else shlex.join(run)
            )
        return
    if args.out_dir.exists():
        parser.error("sweep report directory already exists; use a new prefix or out-dir")
    if any(
        (args.jobs_dir / f"{args.prefix}-seed-{e['seed']}-{c}").exists()
        for e in entries
        if not e["reused"]
        for c in ("no-memory", "learning")
    ):
        parser.error("a target seed job already exists; use a new prefix")
    manifest = {
        "mode": "memory-sweep",
        "prefix": args.prefix,
        "model": args.model,
        "pi_version": PI_VERSION,
        "thinking": PLAY_THINKING,
        "status": "running",
        "pairs": entries,
    }
    args.out_dir.mkdir(parents=True, exist_ok=False)
    path = args.out_dir / "matrix.json"

    def save():
        path.write_text(json.dumps(manifest, indent=2) + "\n")

    save()
    try:
        # Freeze every seed before any paid run and validate reused pairs against
        # regenerated inputs, not just a seed number or a favorable score.
        source_digest = task_digest(TASK)
        for entry, generate, _ in plans:
            subprocess.run(generate, cwd=REPO, check=True)
            entry["instance_sha256"] = task_digest(Path(entry["task"]))
            if entry["reused"]:
                read_pair(
                    Path(entry["report_dir"]),
                    model=args.model,
                    seed=entry["seed"],
                    digest=entry["instance_sha256"],
                )
        if task_digest(TASK) != source_digest:
            raise ValueError("source task changed while preparing seeds")
        save()
        for entry, _, run in plans:
            if not entry["reused"]:
                print(f"Running paired seed {entry['seed']}", flush=True)
                subprocess.run(run, cwd=REPO, check=True)
            read_pair(
                Path(entry["report_dir"]),
                model=args.model,
                seed=entry["seed"],
                digest=entry["instance_sha256"],
            )
            entry["complete"] = True
            save()
        manifest["status"] = "complete"
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        manifest.update(status="failed", error=str(exc) or "interrupted")
        raise SystemExit(f"Seed sweep stopped: {manifest['error']}") from exc
    finally:
        save()
        seed_report(args.out_dir, manifest)
    print(f"Report: {args.out_dir / 'comparison.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="provider/model-id; used unchanged for all conditions")
    parser.add_argument("--task", type=Path, default=TASK)
    parser.add_argument("--jobs-dir", type=Path, default=REPO / "jobs")
    parser.add_argument("--prefix", default="affinity-arena")
    parser.add_argument("--pi-version", default=PI_VERSION)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument(
        "--seeds", type=int, nargs="+", help="generate and compare multiple matched seeds"
    )
    parser.add_argument(
        "--reuse",
        type=Path,
        nargs="+",
        default=[],
        help="with --seeds: reuse complete pair report directories after validation",
    )
    parser.add_argument(
        "--compare-memory",
        action="store_true",
        help="run true no-memory and resumed-context conditions back-to-back",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="with --compare-memory: regenerate reports without API calls",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print commands without requiring credentials or spending tokens",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.prefix):
        parser.error("prefix must be a simple job-name slug")
    args.out_dir = (
        args.out_dir or TASK / "results" / (args.prefix if args.compare_memory else "matrix")
    ).resolve()
    args.jobs_dir = args.jobs_dir.resolve()
    if args.reuse and not args.seeds:
        parser.error("--reuse requires --seeds")
    if args.report_only:
        if not args.compare_memory or args.dry_run:
            parser.error("--report-only requires --compare-memory and cannot use --dry-run")
        try:
            manifest = json.loads((args.out_dir / "matrix.json").read_text())
        except (OSError, ValueError) as exc:
            parser.error(f"cannot read comparison manifest: {exc}")
        if (
            manifest.get("mode") not in {"memory-comparison", "memory-sweep"}
            or manifest.get("prefix") != args.prefix
        ):
            parser.error("report directory does not belong to this memory comparison")
        if manifest["mode"] == "memory-sweep":
            if not seed_report(args.out_dir, manifest):
                raise SystemExit("Seed comparison is incomplete; inspect comparison.md")
            print(f"Report: {args.out_dir / 'comparison.md'}")
            return
        jobs = Path(manifest["jobs_dir"])
        invalid_reason = (
            None
            if manifest.get("status") == "complete"
            else manifest.get("error", "Run has not completed")
        )
        if not memory_report(jobs, args.prefix, args.out_dir, invalid_reason):
            raise SystemExit(
                "Comparison is incomplete or failed; inspect comparison.md and matrix.json"
            )
        print(f"Report: {args.out_dir / 'comparison.md'}")
        return
    model_pattern = (
        r"[A-Za-z0-9_-]+/[A-Za-z0-9][A-Za-z0-9._/-]*"
        if args.compare_memory
        else r"openai/[A-Za-z0-9][A-Za-z0-9._/-]*"
    )
    if not args.model or not re.fullmatch(model_pattern, args.model):
        parser.error("supply --model provider/model-id (legacy matrix requires openai/<model-id>)")
    if args.compare_memory and args.pi_version != PI_VERSION:
        parser.error(f"memory comparison pins both conditions to Pi {PI_VERSION}")
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
    if args.seeds:
        run_seeds(args, parser)
        return
    runs = (
        memory_commands(
            harbor, args.task.resolve(), args.jobs_dir, args.prefix, args.model, bool(endpoint)
        )
        if args.compare_memory
        else commands(
            harbor,
            args.task.resolve(),
            args.jobs_dir.resolve(),
            args.prefix,
            args.model,
            args.pi_version,
            bool(endpoint),
        )
    )
    if args.dry_run:
        for _, command in runs:
            print(shlex.join(command))
        return
    if not args.compare_memory and not os.environ.get("OPENAI_API_KEY"):
        parser.error(
            "set OPENAI_API_KEY in your shell before running the matrix; --dry-run needs no key"
        )
    if not Path(harbor).is_file():
        parser.error("Harbor is missing; install requirements-dev.txt in your virtual environment")
    if any((args.jobs_dir / f"{args.prefix}-{condition}").exists() for condition, _ in runs):
        parser.error("a target job already exists; choose a new --prefix to preserve previous runs")
    if args.compare_memory and args.out_dir.exists():
        parser.error("report directory already exists; choose a new --prefix or --out-dir")
    digest = task_digest(args.task)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(TASK) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    if args.compare_memory:
        manifest = {
            "mode": "memory-comparison",
            "prefix": args.prefix,
            "model": args.model,
            "pi_version": PI_VERSION,
            "thinking": PLAY_THINKING,
            "instance_sha256": digest,
            "jobs_dir": str(args.jobs_dir),
            "status": "running",
        }
        args.out_dir.mkdir(parents=True, exist_ok=False)
        manifest_path = args.out_dir / "matrix.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        try:
            for condition, command in runs:
                if task_digest(args.task) != digest:
                    raise RuntimeError("source task changed; refusing a mismatched comparison")
                print(f"Running {condition}", flush=True)
                subprocess.run(command, cwd=REPO, env=env, check=True)
                rows = analyze_job(args.jobs_dir / f"{args.prefix}-{condition}")
                if len(rows) != 1 or rows[0]["issues"]:
                    raise RuntimeError(f"{condition} did not complete all twenty battles")
                if task_digest(args.task) != digest:
                    raise RuntimeError("source task changed during execution; comparison invalid")
            manifest["status"] = "complete"
        except (
            OSError,
            RuntimeError,
            ValueError,
            subprocess.CalledProcessError,
            KeyboardInterrupt,
        ) as exc:
            manifest.update(status="failed", error=str(exc) or "interrupted")
            raise SystemExit(f"Comparison stopped: {manifest['error']}") from exc
        finally:
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            memory_report(args.jobs_dir, args.prefix, args.out_dir, manifest.get("error"))
        print(f"Report: {args.out_dir / 'comparison.md'}")
        return
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
