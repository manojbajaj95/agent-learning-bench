"""Summarize Harbor job results for multi-step trials (points, cost, time, tokens)."""

from __future__ import annotations

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


def _extras_from_verifier(verifier_result: dict[str, Any] | None) -> dict[str, float]:
    if not verifier_result:
        return {}
    rewards = verifier_result.get("rewards")
    if not isinstance(rewards, dict):
        return {}
    extras: dict[str, float] = {}
    for key, value in rewards.items():
        if key == "reward" or value is None:
            continue
        try:
            extras[key] = float(value)
        except (TypeError, ValueError):
            continue
    return extras


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
        timing = step.get("agent_execution") or {}
        duration = _duration_sec(timing.get("started_at"), timing.get("finished_at"))
        costs.append(metrics["cost_usd"])
        inputs.append(metrics["n_input_tokens"])
        caches.append(metrics["n_cache_tokens"])
        outputs.append(metrics["n_output_tokens"])
        extras = _extras_from_verifier(step.get("verifier_result"))
        step_rows.append(
            {
                "name": name,
                "points": reward,
                "hit": None if reward is None else reward >= 1.0,
                "cost_usd": metrics["cost_usd"],
                "duration_sec": duration,
                "n_input_tokens": metrics["n_input_tokens"],
                "n_cache_tokens": metrics["n_cache_tokens"],
                "n_output_tokens": metrics["n_output_tokens"],
                "extras": extras,
            }
        )

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
    mean_reward = points_sum / len(step_rewards) if step_rewards else None

    exception = (result.get("exception_info") or {}).get("exception_type")
    if not exception:
        for step in steps:
            exception = (step.get("exception_info") or {}).get("exception_type")
            if exception:
                break

    extra_keys = sorted({k for row in step_rows for k in row.get("extras", {})})
    extra_sums = {
        key: _sum_optional([row.get("extras", {}).get(key) for row in step_rows])
        for key in extra_keys
    }

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
        "extras": extra_sums,
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


def collect_trials(
    jobs_dir: Path,
    task_filter: str | None,
    job_filter: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not jobs_dir.exists():
        return rows
    for result_path in sorted(jobs_dir.glob("*/*/result.json")):
        rel = result_path.relative_to(jobs_dir)
        job_name = rel.parts[0]
        if job_filter and job_filter.lower() not in job_name.lower():
            continue
        try:
            data = json.loads(result_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if "trial_name" not in data and "step_results" not in data:
            continue
        summary = summarize_trial(data)
        summary["job"] = job_name
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

        lines.extend(["", "## Reward vs attempt", ""])
        for i, row in enumerate(rows, start=1):
            pts = row.get("points_sum")
            bar = "" if pts is None else ("#" * int(round(pts)))
            lines.append(f"{i}. points={_fmt(pts, 2)} {bar}")

    lines.append("")
    return "\n".join(lines)


_CHART_COLORS = (
    "#3d7ea6",
    "#c44e1a",
    "#2a9d8f",
    "#7b2d8e",
    "#b08900",
    "#4a4a4a",
)


def _series_values(rows: list[dict[str, Any]], getter) -> list[tuple[str, list[float | None]]]:
    series: list[tuple[str, list[float | None]]] = []
    for row in rows:
        steps = row.get("steps") or []
        if not steps:
            continue
        series.append((row.get("job") or row.get("trial_name") or "trial", [getter(s) for s in steps]))
    return series


def svg_lines(
    series: list[tuple[str, list[float | None]]],
    title: str,
    width: int = 720,
    height: int = 280,
    pad: int = 44,
) -> str:
    if not series:
        return ""
    nums = [v for _, values in series for v in values if v is not None]
    if not nums:
        return ""
    lo, hi = min(nums), max(nums)
    span = hi - lo or 1.0
    inner_w = width - 2 * pad
    inner_h = height - 2 * pad
    n_max = max(len(values) for _, values in series)
    denom = max(n_max - 1, 1)

    def xy(index: int, value: float) -> tuple[float, float]:
        x = pad + inner_w * index / denom
        y = pad + inner_h * (1 - (value - lo) / span)
        return x, y

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
        f'<text x="{pad}" y="18" font-size="13" font-family="sans-serif" fill="#1a1a1a">{_xml(title)}</text>',
        f'<text x="{pad}" y="{pad - 6}" font-size="10" font-family="sans-serif" fill="#5c5c5c">{_fmt(hi, 3)}</text>',
        f'<text x="{pad}" y="{height - 12}" font-size="10" font-family="sans-serif" fill="#5c5c5c">{_fmt(lo, 3)}</text>',
        f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height - pad}" stroke="#e6e6e6"/>',
        f'<line x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}" stroke="#e6e6e6"/>',
    ]
    legend_x = pad
    for i, (label, values) in enumerate(series):
        color = _CHART_COLORS[i % len(_CHART_COLORS)]
        d: list[str] = []
        drawing = False
        for index, value in enumerate(values):
            if value is None:
                drawing = False
                continue
            x, y = xy(index, value)
            cmd = "L" if drawing else "M"
            d.append(f"{cmd}{x:.1f},{y:.1f}")
            drawing = True
        if d:
            parts.append(
                f'<path d="{" ".join(d)}" fill="none" stroke="{color}" stroke-width="2"/>'
            )
        parts.append(
            f'<text x="{legend_x}" y="{height - 2}" font-size="10" font-family="sans-serif" fill="{color}">{_xml(label)}</text>'
        )
        legend_x += 8 * max(len(label), 4) + 16
    parts.append("</svg>")
    return "\n".join(parts)


def _xml(text: Any) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_html(rows: list[dict[str, Any]], charts: dict[str, str]) -> str:
    blocks = [
        "<!doctype html>",
        '<meta charset="utf-8"/>',
        "<title>Harbor run report</title>",
        "<style>body{font:14px/1.4 sans-serif;max-width:900px;margin:24px auto;color:#1a1a1a}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:4px 8px;text-align:left}"
        "th{background:#f4f4f4}svg{display:block;margin:16px 0}</style>",
        "<h1>Harbor run report</h1>",
        f"<p>Trials: {len(rows)}</p>",
    ]
    for svg in charts.values():
        if svg:
            blocks.append(svg)
    blocks.append("<h2>Trials</h2>")
    blocks.append(
        "<table><tr><th>job</th><th>trial</th><th>points</th><th>mean</th>"
        "<th>cost_usd</th><th>duration_s</th><th>error</th></tr>"
    )
    for row in rows:
        blocks.append(
            "<tr><td>{job}</td><td>{trial}</td><td>{points}</td><td>{mean}</td>"
            "<td>{cost}</td><td>{dur}</td><td>{err}</td></tr>".format(
                job=_xml(row.get("job", "")),
                trial=_xml(row.get("trial_name") or ""),
                points=_xml(_fmt(row.get("points_sum"), 2)),
                mean=_xml(_fmt(row.get("mean_reward"), 3)),
                cost=_xml(_fmt(row.get("cost_usd"), 6)),
                dur=_xml(_fmt(row.get("duration_sec"), 1)),
                err=_xml(row.get("exception") or ""),
            )
        )
    blocks.append("</table>")
    return "\n".join(blocks) + "\n"


def write_charts(rows: list[dict[str, Any]], out_dir: Path) -> dict[str, Path]:
    charts = {
        "reward": svg_lines(_series_values(rows, lambda s: s.get("points")), "Reward vs step"),
        "cost": svg_lines(_series_values(rows, lambda s: s.get("cost_usd")), "Cost (USD) vs step"),
        "tokens": svg_lines(
            _series_values(rows, lambda s: s.get("n_input_tokens")),
            "Input tokens vs step",
        ),
    }
    extra_keys = sorted({k for row in rows for step in row.get("steps") or [] for k in step.get("extras", {})})
    for key in extra_keys:
        charts[key] = svg_lines(
            _series_values(rows, lambda s, k=key: s.get("extras", {}).get(k)),
            f"{key} vs step",
        )
    written: dict[str, Path] = {}
    for name, svg in charts.items():
        if not svg:
            continue
        path = out_dir / f"{name}.svg"
        path.write_text(svg + "\n")
        written[name] = path
    html_path = out_dir / "latest.html"
    html_path.write_text(render_html(rows, charts))
    written["html"] = html_path
    return written


def write_report(
    jobs_dir: Path,
    out_dir: Path,
    task_filter: str | None = None,
    job_filter: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Path]]:
    rows = collect_trials(jobs_dir, task_filter, job_filter)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "latest.json"
    md_path = out_dir / "latest.md"
    payload = {
        "jobs_dir": str(jobs_dir),
        "task_filter": task_filter,
        "job_filter": job_filter,
        "n_trials": len(rows),
        "trials": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    md_path.write_text(render_markdown(rows))
    written = write_charts(rows, out_dir)
    written["json"] = json_path
    written["md"] = md_path
    return rows, written
