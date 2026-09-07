#!/usr/bin/env python3
"""Produce per-battle and phase comparison reports from explicit Harbor jobs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from tools.report_runs import summarize_trial as summarize_harbor_trial


def summarize_trial(result: dict) -> dict:
    """Add Arena diagnostics without changing the shared report's score semantics."""
    summary = summarize_harbor_trial(result)
    for step, raw in zip(summary["steps"], result.get("step_results") or [], strict=True):
        rewards = (raw.get("verifier_result") or {}).get("rewards") or {}
        step["rewards"] = rewards
        if "won" in rewards:
            step["hit"] = rewards["won"] == 1
    return summary

METRICS = (
    "reward",
    "won",
    "opt_rate",
    "draft_ok",
    "regret",
    "cells_seen",
    "belief_acc",
    "ticks",
    "oracle_ticks",
    "env_actions",
)


def analyze_job(job: Path) -> list[dict]:
    trials = []
    paths = (
        [job / "result.json"]
        if (job / "config.json").exists() and any((job / "steps").glob("battle-*"))
        else sorted(job.glob("*/result.json"))
    )
    for path in paths:
        result = json.loads(path.read_text())
        if "affinity-arena" not in result.get("task_name", ""):
            continue
        summary = summarize_trial(result)
        steps = summary["steps"]
        issues = []
        if summary["exception"]:
            issues.append(summary["exception"])
        if [s["name"] for s in steps] != [f"battle-{i:02d}" for i in range(1, 21)]:
            issues.append("expected all twenty ordered battles")
        if any(any(k not in s["rewards"] for k in METRICS) for s in steps):
            issues.append("missing per-battle metrics")
        if any(s["rewards"].get("completed") != 1 for s in steps):
            issues.append("one or more incomplete attempts")
        phases = {}
        for phase, start, end in (("early", 1, 5), ("late", 11, 15), ("holdout", 16, 20)):
            selected = [
                s for s in steps if s["name"] in {f"battle-{i:02d}" for i in range(start, end + 1)}
            ]
            phases[phase] = {
                key: mean(s["rewards"][key] for s in selected)
                for key in METRICS
                if selected and all(key in s["rewards"] for s in selected)
            }
        summary.update(
            {"job": job.name, "phases": phases, "issues": issues, "result_path": str(path)}
        )
        trials.append(summary)
    return trials


def report(trials: list[dict]) -> str:
    lines = [
        "# Affinity Arena agent evaluation",
        "",
        "Early = battles 1–5; late = 11–15; holdout = 16–20. Baseline files persist, so it can learn too.",
        "",
        "| Job | Phase | Reward | Wins | Optimal actions | Draft quality | Regret | Belief accuracy |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for trial in trials:
        for phase, metrics in trial["phases"].items():
            values = " | ".join(
                f"{metrics[k]:.3f}" if k in metrics else "—"
                for k in ("reward", "won", "opt_rate", "draft_ok", "regret", "belief_acc")
            )
            lines.append(f"| {trial['job']} | {phase} | {values} |")
    for trial in trials:
        lines.extend(
            [
                "",
                f"## {trial['job']} / {trial['trial_name']}",
                "",
                "Run checks: "
                + (
                    "; ".join(trial["issues"])
                    if trial["issues"]
                    else "all twenty battles completed with metrics"
                ),
                "",
                "| Battle | Reward | Win | Optimal | Draft | Regret | Seen | Belief | Ticks | Excess ticks | Actions | Tokens | Seconds |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for step in trial["steps"]:
            r = step["rewards"]
            values = [
                r.get(k)
                for k in (
                    "reward",
                    "won",
                    "opt_rate",
                    "draft_ok",
                    "regret",
                    "cells_seen",
                    "belief_acc",
                    "ticks",
                )
            ]
            values.append(
                r["ticks"] - r["oracle_ticks"] if "ticks" in r and "oracle_ticks" in r else None
            )
            values.extend(
                [
                    r.get("env_actions"),
                    (step["n_input_tokens"] or 0) + (step["n_output_tokens"] or 0)
                    if step["n_input_tokens"] is not None
                    else None,
                    step["duration_sec"],
                ]
            )
            lines.append(
                f"| {step['name']} | "
                + " | ".join("—" if v is None else f"{v:.3f}" for v in values)
                + " |"
            )
    lines.extend(
        [
            "",
            "Review reward and decision quality together. Excess ticks can be negative on a quick loss; inspect it alongside wins.",
            "A single real-agent matrix is directional evidence. Read the traces and chart notes before attributing changes to learning.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jobs", type=Path, nargs="+")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results" / "agents")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    trials = [t for job in args.jobs for t in analyze_job(job)]
    if not trials:
        raise SystemExit("No Affinity Arena trial results found in the supplied jobs")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "comparison.json").write_text(json.dumps(trials, indent=2) + "\n")
    (args.out_dir / "comparison.md").write_text(report(trials))
    print(report(trials))
    if args.require_complete and any(t["issues"] for t in trials):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
