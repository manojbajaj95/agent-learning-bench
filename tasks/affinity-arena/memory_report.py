"""Paired reward-gap summaries and dependency-free five-battle rolling plots."""

from __future__ import annotations

import json
from html import escape
from math import ceil, isclose, isfinite
from pathlib import Path
from statistics import mean

from analyze import report


def rolling(values: list[float], window: int = 5) -> list[float]:
    """Trailing full windows only: the first plotted point ends at battle five."""
    if window < 1 or len(values) < window:
        raise ValueError("rolling average needs a positive, full window")
    return [mean(values[i - window : i]) for i in range(window, len(values) + 1)]


def summarize_pairs(pairs: list[dict]) -> dict:
    seeds, curves = [], []
    for pair in pairs:
        baseline, learning = pair["trials"]
        baseline_rewards, learning_rewards = (
            [s["rewards"]["reward"] for s in t["steps"]] for t in (baseline, learning)
        )
        seeds.append(
            {
                "seed": pair["seed"],
                "no_memory_reward": mean(baseline_rewards),
                "learning_reward": mean(learning_rewards),
                "reward_gap": mean(learning_rewards) - mean(baseline_rewards),
                "no_memory_wins": sum(s["rewards"]["won"] for s in baseline["steps"]),
                "learning_wins": sum(s["rewards"]["won"] for s in learning["steps"]),
            }
        )
        curves.append(
            {
                "seed": pair["seed"],
                "no_memory": rolling(baseline_rewards),
                "learning": rolling(learning_rewards),
                "gap": rolling(
                    [y - x for x, y in zip(baseline_rewards, learning_rewards, strict=True)]
                ),
            }
        )
    phases = []
    for name, start, end in (
        ("All", 0, 20),
        ("1–5", 0, 5),
        ("6–10", 5, 10),
        ("11–15", 10, 15),
        ("16–20 (holdout)", 15, 20),
    ):
        baseline_mean, learning_mean = (
            mean(
                mean(s["rewards"]["reward"] for s in p["trials"][i]["steps"][start:end])
                for p in pairs
            )
            for i in (0, 1)
        )
        phases.append(
            {
                "battles": name,
                "no_memory_reward": baseline_mean,
                "learning_reward": learning_mean,
                "reward_gap": learning_mean - baseline_mean,
            }
        )
    gaps = [s["reward_gap"] for s in seeds]
    return {
        "complete": True,
        "n_seeds": len(seeds),
        "mean_reward_gap": mean(gaps),
        "seed_gap_range": [min(gaps), max(gaps)],
        "seeds": seeds,
        "phases": phases,
        "rolling_window": 5,
        "window_end_battles": list(range(5, 21)),
        "rolling": curves,
    }


def rolling_plot(summary: dict) -> str:
    curves = summary["rolling"]
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 730" role="img" aria-labelledby="title desc">',
        '<title id="title">Affinity Arena: five-battle rolling reward and paired memory gap</title>',
        '<desc id="desc">Trailing full windows ending at battles five through twenty. Thin lines show individual seeds; thick lines show the mean across seeds.</desc>',
        '<rect width="960" height="730" fill="white"/>',
        '<g font-family="sans-serif" fill="#17202a">',
    ]

    def text(x, y, value, size=13, **attrs):
        options = " ".join(
            f'{key.replace("_", "-")}="{escape(str(v))}"' for key, v in attrs.items()
        )
        svg.append(
            f'<text x="{x}" y="{y}" font-size="{size}" {options}>{escape(str(value))}</text>'
        )

    text(70, 32, "Five-battle rolling reward", 23, font_weight="bold")
    text(
        70,
        57,
        f"Headline: learning − no-memory = {summary['mean_reward_gap']:+.3f} mean reward; {summary['n_seeds']} matched seed(s)",
    )
    text(70, 81, "Learning", fill="#1267b1")
    text(170, 81, "No memory", fill="#bc5b0a")
    text(300, 81, "Thin: individual seeds · Thick: seed mean")
    max_gap = max(abs(v) for c in curves for v in c["gap"])
    limit = max(0.1, ceil(max_gap * 10) / 10)
    for top, bottom, low, high, keys in (
        (115, 350, 0, 1, (("no_memory", "#bc5b0a"), ("learning", "#1267b1"))),
        (440, 655, -limit, limit, (("gap", "#7543a0"),)),
    ):

        def x(battle):
            return 70 + (battle - 5) / 15 * 850

        def y(value, bottom=bottom, low=low, high=high, top=top):
            return bottom - (value - low) / (high - low) * (bottom - top)

        for i in range(5):
            value = low + i * (high - low) / 4
            svg.append(f'<path d="M70 {y(value):.2f}H920" stroke="#e1e5ea"/>')
            text(60, y(value) + 4, f"{value:.2f}", text_anchor="end")
        for battle in (5, 10, 15, 20):
            text(x(battle), bottom + 22, battle, text_anchor="middle")
        svg.append(
            f'<path d="M{x(15.5):.2f} {top}V{bottom}" stroke="#727b85" stroke-dasharray="5 4"/>'
        )
        text(x(15.5) + 6, top - 7, "Holdout starts", 11)
        for key, color in keys:
            lines = (
                [(c[key], 1.2, 0.28, f"Seed {c['seed']}: {key}") for c in curves]
                if len(curves) > 1
                else []
            )
            lines.append(
                ([mean(c[key][i] for c in curves) for i in range(16)], 3, 1, f"Seed mean: {key}")
            )
            for values, width, opacity, title in lines:
                points = " ".join(f"{x(i):.2f},{y(v):.2f}" for i, v in enumerate(values, 5))
                svg.append(
                    f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="{width}" opacity="{opacity}"><title>{escape(title)}</title></polyline>'
                )
        if low < 0:
            svg.append(f'<path d="M70 {y(0):.2f}H920" stroke="#727b85" stroke-dasharray="3 4"/>')
    text(70, 410, "Paired reward gap: positive favors memory", 19, font_weight="bold")
    text(495, 697, "Battle at end of trailing window", text_anchor="middle")
    text(
        70,
        720,
        "Windows ending at 16–19 mix training and holdout battles. Seed spread is descriptive, not a confidence interval.",
        11,
    )
    svg.append("</g></svg>\n")
    return "\n".join(svg)


def validate_pairs(pairs: list[dict]) -> None:
    if not pairs or len({p["seed"] for p in pairs}) != len(pairs):
        raise ValueError("expected at least one pair, with distinct seeds")
    for pair in pairs:
        trials = pair["trials"]
        if len(trials) != 2 or any(t["issues"] or len(t["steps"]) != 20 for t in trials):
            raise ValueError("expected two complete conditions per seed")
        for baseline, learning in zip(trials[0]["steps"], trials[1]["steps"], strict=True):
            if baseline["name"] != learning["name"]:
                raise ValueError("paired battle names differ")
            br, lr = baseline["rewards"], learning["rewards"]
            if not all(isfinite(r[k]) for r in (br, lr) for k in ("reward", "regret")):
                raise ValueError("non-finite reward or regret")
            if any(not 0 <= r["reward"] <= 1 or r["regret"] < -1e-9 for r in (br, lr)):
                raise ValueError("reward or regret is out of range")
            if not isclose(br["reward"] + br["regret"], lr["reward"] + lr["regret"], abs_tol=1e-9):
                raise ValueError("paired battles do not share the same oracle reward")


def write_comparison(pairs: list[dict], output: Path, problems: list[str]) -> bool:
    problems = list(problems)
    if not problems:
        try:
            validate_pairs(pairs)
        except ValueError as exc:
            problems.append(str(exc))
    trials = [t for p in pairs for t in p["trials"]]
    output.mkdir(parents=True, exist_ok=True)
    if problems:
        summary = {"complete": False, "issues": problems}
        text = "# Affinity Arena memory comparison\n\nComparison incomplete; no memory advantage calculated.\n\n"
        text += "\n".join(f"- {p}" for p in problems) + "\n\n"
        # Replace a previous plot with an explicit warning, never stale success.
        plot = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 80"><text x="20" y="40">Comparison incomplete: see comparison.md.</text></svg>\n'
    else:
        summary = summarize_pairs(pairs)
        text = (
            "# Affinity Arena memory comparison\n\n## Memory advantage\n\n"
            f"**Mean paired reward gap: {summary['mean_reward_gap']:+.3f}** "
            f"(learning − no-memory), across {summary['n_seeds']} matched seed(s).\n\n"
            "Each seed has equal weight. These small-sample results are descriptive, not a significance test. "
            "Regret = oracle reward − agent reward, so paired regret reduction equals this reward gap; "
            "it is an interpretation, not independent evidence. Wins are a secondary, coarse metric.\n\n"
            "| Battles | No-memory reward | Learning reward | Reward gap |\n|---|---:|---:|---:|\n"
        )
        for p in summary["phases"]:
            text += f"| {p['battles']} | {p['no_memory_reward']:.3f} | {p['learning_reward']:.3f} | {p['reward_gap']:+.3f} |\n"
        text += (
            "\n![Five-battle rolling reward and paired gap](rolling-reward.svg)\n\n"
            "Full trailing windows only; the first point ends at battle 5. Thin lines show seeds; "
            "thick lines show their mean. Windows ending at 16–19 straddle the holdout boundary.\n\n"
            "## Per-seed results\n\n| Seed | Reward gap | No-memory wins | Learning wins |\n|---|---:|---:|---:|\n"
        )
        for s in summary["seeds"]:
            text += f"| {s['seed'] if s['seed'] is not None else '—'} | {s['reward_gap']:+.3f} | {s['no_memory_wins']}/20 | {s['learning_wins']}/20 |\n"
        plot = rolling_plot(summary)
    text += "\n## Battle diagnostics\n\n" + report(trials).split("\n", 2)[2]
    (output / "comparison.md").write_text(text)
    (output / "comparison.json").write_text(json.dumps(trials, indent=2) + "\n")
    (output / "reward-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (output / "rolling-reward.svg").write_text(plot)
    return not problems
