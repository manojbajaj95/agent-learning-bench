#!/usr/bin/env python3
"""Summarize Harbor job results for multi-step trials (points, cost, time, tokens)."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_sec(started: str | None, finished: str | None) -> float | None:
    a = _parse_dt(started)
    b = _parse_dt(finished)
    if a is None or b is None:
        return None
    return max(0.0, (b - a).total_seconds())


def _agent_metrics(agent_result: dict[str, Any] | None) -> dict[str, Any]:
    if not agent_result:
        return {
            "cost_usd": None,
            "n_input_tokens": None,
            "n_cache_tokens": None,
            "n_output_tokens": None,
        }
    return {
        "cost_usd": agent_result.get("cost_usd"),
        "n_input_tokens": agent_result.get("n_input_tokens"),
        "n_cache_tokens": agent_result.get("n_cache_tokens"),
        "n_output_tokens": agent_result.get("n_output_tokens"),
    }


def _sum_optional(values: list[float | int | None]) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return float(sum(nums))


def _reward_from_verifier(verifier_result: dict[str, Any] | None) -> float | None:
    if not verifier_result:
        return None
    rewards = verifier_result.get("rewards")
    if isinstance(rewards, dict):
        if "reward" in rewards and rewards["reward"] is not None:
            return float(rewards["reward"])
        if rewards:
            return float(sum(float(v) for v in rewards.values() if v is not None))
    if verifier_result.get("reward") is not None:
        return float(verifier_result["reward"])
    return None


def summarize_trial(result: dict[str, Any]) -> dict[str, Any]:
    steps = result.get("step_results") or []
    step_rows: list[dict[str, Any]] = []
    step_rewards: list[float] = []
    costs: list[float | None] = []
    inputs: list[int | None] = []
    caches: list[int | None] = []
    outputs: list[int | None] = []

    for step in steps:
        name = step.get("name") or step.get("step_name") or "?"
        reward = _reward_from_verifier(step.get("verifier_result"))
        if reward is not None:
            step_rewards.append(reward)
        metrics = _agent_metrics(step.get("agent_result"))
        rewards = (step.get("verifier_result") or {}).get("rewards") or {}
        hit = None if reward is None else reward >= 1.0
        if "won" in rewards:
            hit = rewards["won"] == 1
        timing = step.get("agent_execution") or {}
        duration = _duration_sec(timing.get("started_at"), timing.get("finished_at"))
        costs.append(metrics["cost_usd"])
        inputs.append(metrics["n_input_tokens"])
        caches.append(metrics["n_cache_tokens"])
        outputs.append(metrics["n_output_tokens"])
        step_rows.append(
            {
                "name": name,
                "points": reward,
                "hit": hit,
                "rewards": rewards,
                "cost_usd": metrics["cost_usd"],
                "duration_sec": duration,
                "n_input_tokens": metrics["n_input_tokens"],
                "n_cache_tokens": metrics["n_cache_tokens"],
                "n_output_tokens": metrics["n_output_tokens"],
            }
        )

    # Single-step fallback: trial-level agent_result
    if not steps:
        metrics = _agent_metrics(result.get("agent_result"))
        reward = _reward_from_verifier(result.get("verifier_result"))
        if reward is not None:
            step_rewards.append(reward)
        costs.append(metrics["cost_usd"])
        inputs.append(metrics["n_input_tokens"])
        caches.append(metrics["n_cache_tokens"])
        outputs.append(metrics["n_output_tokens"])

    trial_timing = result.get("agent_execution") or {}
    wall = _duration_sec(result.get("started_at"), result.get("finished_at"))
    agent_wall = _duration_sec(
        trial_timing.get("started_at"), trial_timing.get("finished_at")
    )

    points_sum = float(sum(step_rewards)) if step_rewards else None
    mean_reward = (
        points_sum / len(step_rewards) if step_rewards else None
    )

    exception = (result.get("exception_info") or {}).get("exception_type")
    if not exception:
        for step in steps:
            exception = (step.get("exception_info") or {}).get("exception_type")
            if exception:
                break

    return {
        "trial_name": result.get("trial_name"),
        "task_name": result.get("task_name"),
        "points_sum": points_sum,
        "mean_reward": mean_reward,
        "n_steps": len(steps) or (1 if step_rewards else 0),
        "cost_usd": _sum_optional(costs),
        "duration_sec": agent_wall if agent_wall is not None else wall,
        "n_input_tokens": _sum_optional(inputs),
        "n_cache_tokens": _sum_optional(caches),
        "n_output_tokens": _sum_optional(outputs),
        "exception": exception,
        "steps": step_rows,
    }


def _task_matches(summary: dict[str, Any], task_filter: str | None) -> bool:
    if not task_filter:
        return True
    needle = task_filter.lower()
    name = (summary.get("task_name") or "").lower()
    trial = (summary.get("trial_name") or "").lower()
    return needle in name or needle in trial


def collect_trials(jobs_dir: Path, task_filter: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not jobs_dir.exists():
        return rows
    # Trial results live at jobs/<job>/<trial>/result.json (3 path parts).
    for result_path in sorted(jobs_dir.glob("*/*/result.json")):
        rel = result_path.relative_to(jobs_dir)
        try:
            data = json.loads(result_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if "trial_name" not in data and "step_results" not in data:
            continue
        summary = summarize_trial(data)
        summary["job"] = rel.parts[0]
        summary["result_path"] = str(result_path)
        if _task_matches(summary, task_filter):
            rows.append(summary)
    return rows


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "-"
        if digits == 0:
            return str(int(round(value)))
        text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
        return text or "0"
    if isinstance(value, int):
        return str(value)
    return str(value)


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Harbor run report",
        "",
        f"Trials: {len(rows)}",
        "",
        "| job | trial | points | mean | cost_usd | duration_s | in_tok | cache_tok | out_tok | error |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {job} | {trial} | {points} | {mean} | {cost} | {dur} | {inp} | {cache} | {out} | {err} |".format(
                job=row.get("job", ""),
                trial=row.get("trial_name") or "",
                points=_fmt(row.get("points_sum"), 2),
                mean=_fmt(row.get("mean_reward"), 3),
                cost=_fmt(row.get("cost_usd"), 6),
                dur=_fmt(row.get("duration_sec"), 1),
                inp=_fmt(row.get("n_input_tokens"), 0),
                cache=_fmt(row.get("n_cache_tokens"), 0),
                out=_fmt(row.get("n_output_tokens"), 0),
                err=row.get("exception") or "",
            )
        )

    if rows:
        lines.extend(["", "## Per-step (latest trial)", ""])
        latest = rows[-1]
        lines.append(f"Trial: `{latest.get('trial_name')}`")
        lines.append("")
        lines.append(
            "| step | points | hit | cost_usd | duration_s | in_tok | cache_tok | out_tok |"
        )
        lines.append("| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |")
        for step in latest.get("steps") or []:
            hit = step.get("hit")
            hit_s = "-" if hit is None else ("yes" if hit else "no")
            lines.append(
                "| {name} | {points} | {hit} | {cost} | {dur} | {inp} | {cache} | {out} |".format(
                    name=step.get("name"),
                    points=_fmt(step.get("points"), 2),
                    hit=hit_s,
                    cost=_fmt(step.get("cost_usd"), 6),
                    dur=_fmt(step.get("duration_sec"), 1),
                    inp=_fmt(step.get("n_input_tokens"), 0),
                    cache=_fmt(step.get("n_cache_tokens"), 0),
                    out=_fmt(step.get("n_output_tokens"), 0),
                )
            )

        # Simple reward-vs-attempt curve
        lines.extend(["", "## Reward vs attempt", ""])
        for i, row in enumerate(rows, start=1):
            pts = row.get("points_sum")
            bar = "" if pts is None else ("#" * int(round(pts)))
            lines.append(f"{i}. points={_fmt(pts, 2)} {bar}")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jobs-dir",
        type=Path,
        default=Path.home() / ".cache" / "harbor" / "jobs",
        help="Harbor jobs directory",
    )
    parser.add_argument(
        "--task",
        default=None,
        help="Filter trials whose task/trial name contains this string",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("reports"),
        help="Directory for latest.json and latest.md",
    )
    args = parser.parse_args()

    rows = collect_trials(args.jobs_dir, args.task)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "latest.json"
    md_path = args.out_dir / "latest.md"
    payload = {
        "jobs_dir": str(args.jobs_dir),
        "task_filter": args.task,
        "n_trials": len(rows),
        "trials": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    md_path.write_text(render_markdown(rows))
    print(render_markdown(rows))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
