#!/usr/bin/env python3
"""Task-specific learning curves, using the repository's Harbor result summarizer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from tools.report_runs import summarize_trial

from language_agent.trace import read_pi_errors

METRICS = (
    "reward",
    "first_correctness",
    "best_correctness",
    "solved",
    "submissions",
    "local_calls",
    "compiler_calls",
    "compiler_errors",
    "runtime_errors",
    "env_actions",
)
PHASES = (("foundation", 1, 6), ("practice", 7, 12), ("transfer", 13, 16), ("holdout", 17, 20))


def analyze_job(job: Path) -> list[dict]:
    trials = []
    paths = [job / "result.json"] if (job / "steps").is_dir() else sorted(job.glob("*/result.json"))
    for path in paths:
        result = json.loads(path.read_text())
        if result.get("task_name") != "agent-learning-bench/programming-language":
            continue
        summary = summarize_trial(result)
        issues = [summary["exception"]] if summary["exception"] else []
        rows = summary["steps"]
        for row, raw in zip(rows, result.get("step_results", []), strict=True):
            row["metrics"] = (raw.get("verifier_result") or {}).get("rewards") or {}
            exception = (raw.get("exception_info") or {}).get("exception_type")
            row["agent_status"] = (
                "not attempted (error guard)"
                if exception == "PiProviderFailure"
                else exception or "finished"
            )
            if exception:
                issues.append(f"{row['name']}: {exception}")
            row["pi_errors"] = read_pi_errors(
                path.parent / "steps" / row["name"] / "agent" / "pi.txt"
            )
            issues.extend(f"{row['name']}: {error}" for error in row["pi_errors"])
            if row["pi_errors"] and not exception:
                row["agent_status"] = "Pi assistant error"
        if [row["name"] for row in rows] != [f"problem-{i:02d}" for i in range(1, 21)]:
            issues.append("expected all twenty ordered problems")
        if any(any(key not in row["metrics"] for key in METRICS) for row in rows):
            issues.append("missing per-problem metrics")
        if any(row["metrics"].get("completed") != 1 for row in rows):
            issues.append("one or more problems were not settled")
        phases = {}
        for phase, start, end in PHASES:
            selected = [
                row
                for row in rows
                if row["name"] in {f"problem-{i:02d}" for i in range(start, end + 1)}
            ]
            phases[phase] = {
                key: mean(row["metrics"][key] for row in selected)
                for key in METRICS
                if selected and all(key in row["metrics"] for row in selected)
            }
        summary.update(job=job.name, result_path=str(path), issues=issues, phases=phases)
        trials.append(summary)
    return trials


def report(trials: list[dict]) -> str:
    lines = [
        "# Programming language learning",
        "",
        "Reward is first-submission correctness. Solved measures eventual success.",
        "Foundation (1–6), practice (7–12), transfer (13–16), and holdout (17–20) "
        "contain different programs. Compare memory conditions on the same problems, "
        "seeds, models, versions, and budgets; phase differences alone do not measure learning.",
        "",
        "| Job | Phase | Reward | Best correctness | Solved | Local calls | Submissions |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]

    def fmt(value):
        return "—" if value is None else f"{value:.3f}"

    for trial in trials:
        for phase, values in trial["phases"].items():
            cells = [
                fmt(values.get(key))
                for key in ("reward", "best_correctness", "solved", "local_calls", "submissions")
            ]
            lines.append(f"| {trial['job']} | {phase} | " + " | ".join(cells) + " |")
    for trial in trials:
        lines += [
            "",
            f"## {trial['job']} / {trial['trial_name']}",
            "",
            "Run checks: " + ("; ".join(trial["issues"]) or "all twenty problems settled"),
            "",
            "| Problem | Reward | Solved | Calls | Compiler errors | Runtime errors | Submissions | Tokens | Seconds | Agent status |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for row in trial["steps"]:
            values = [
                row["metrics"].get(key)
                for key in (
                    "reward",
                    "solved",
                    "env_actions",
                    "compiler_errors",
                    "runtime_errors",
                    "submissions",
                )
            ]
            tokens = (
                row["n_input_tokens"] + row["n_output_tokens"]
                if row["n_input_tokens"] is not None and row["n_output_tokens"] is not None
                else None
            )
            values += [tokens, row["duration_sec"]]
            lines.append(
                f"| {row['name']} | "
                + " | ".join(fmt(v) for v in values)
                + f" | {row['agent_status']} |"
            )
    lines += [
        "",
        "Inspect correctness and costs together. An increasing difficulty curriculum "
        "or a single seed is not sufficient evidence of learning. Missing token counts are not zero.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jobs", nargs="+", type=Path)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results/agents")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    trials = [trial for job in args.jobs for trial in analyze_job(job)]
    if not trials:
        raise SystemExit("No programming-language trials found")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "comparison.json").write_text(json.dumps(trials, indent=2) + "\n")
    (args.out_dir / "comparison.md").write_text(report(trials))
    print(report(trials))
    if args.require_complete and any(trial["issues"] for trial in trials):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
