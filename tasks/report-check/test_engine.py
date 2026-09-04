#!/usr/bin/env python3
"""Check the desk against every brief. Run: python3 test_engine.py"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True  # keep .pyc out of the image build context
sys.path.insert(0, str(ROOT / "environment" / "report"))

from engine import (  # noqa: E402
    MAX_SUBMISSIONS,
    REPORT_MAX_WORDS,
    SUMMARY_MAX_WORDS,
    active_rules,
    check,
    compose_gold,
    count_words,
    load_briefs,
    render_brief,
    reward_for,
    sections,
    step_name,
    strip_signoff,
)

FAILED: list[str] = []


def expect(condition: bool, message: str) -> None:
    if not condition:
        FAILED.append(message)


def naive_report(brief: dict) -> str:
    """What a writer produces on job one: the brief's own words, no house style."""
    lines = [f"# {brief['subject']}", "", "## Summary", "", brief["summary"], "", "## Findings", ""]
    lines += [f"- {item}" for item in brief["findings"]]
    lines += ["", "## Recommendation", "", brief["recommendation"], ""]
    return "\n".join(lines)


def main() -> int:
    briefs = load_briefs()
    expect(len(briefs) == 26, f"expected 26 briefs, found {len(briefs)}")
    expect(
        sum(1 for b in briefs if b.get("holdout")) == 4,
        "expected a 4-job holdout tail",
    )
    expect(
        [b["id"] for b in briefs] == list(range(1, len(briefs) + 1)),
        "brief ids must run 1..N with no gaps",
    )
    expect(
        all(b["tier"] <= briefs[i + 1]["tier"] for i, b in enumerate(briefs[:-1])),
        "tiers must not go down as jobs advance",
    )
    expect(
        all(b.get("holdout") for b in briefs[-4:]),
        "the holdout must be the tail of the run",
    )
    seen = {b["report_type"] for b in briefs if not b.get("holdout")}
    held = {b["report_type"] for b in briefs if b.get("holdout")}
    expect(not (seen & held), f"holdout report types must be new, shared: {seen & held}")

    for brief in briefs:
        name = step_name(brief["id"])
        gold = compose_gold(brief)

        faults = check(gold, brief)
        expect(not faults, f"{name}: the oracle report is rejected: {faults}")

        # An oracle that would pass a harder job must also pass this one, so a
        # late rule can never contradict an early one.
        strict = dict(brief, tier=3)
        if brief.get("risk_note") or not brief.get("figures"):
            strict_faults = [f for f in check(gold, strict) if f[0] not in {"R06-META", "R11-APPENDIX"}]
            expect(
                not strict_faults,
                f"{name}: oracle breaks a later-tier rule: {strict_faults}",
            )

        body = strip_signoff(gold.splitlines())
        expect(
            count_words("\n".join(body)) <= REPORT_MAX_WORDS,
            f"{name}: oracle runs long",
        )
        summary = dict(sections(body))["Summary"]
        expect(
            count_words("\n".join(summary)) <= SUMMARY_MAX_WORDS,
            f"{name}: oracle summary runs long",
        )

        naive = check(naive_report(brief), brief)
        expect(len(naive) >= 3, f"{name}: a naive report should break several rules, got {naive}")

        rendered = render_brief(brief)
        for leak in ("Prepared by", "End of report", "RC-", "R01", "R07-MONEY"):
            expect(leak not in rendered, f"{name}: the brief leaks the rule set ({leak})")

    # The rule set only ever grows.
    for tier in (1, 2, 3):
        earlier = active_rules(max(1, tier - 1))
        expect(
            set(earlier) <= set(active_rules(tier)),
            f"tier {tier} drops a rule that tier {tier - 1} enforced",
        )

    # The run-order guard is what stops the agent opening a job for itself,
    # now that Harbor runs setup.sh unprivileged.
    import engine

    state = ROOT / ".test-state"
    state.mkdir(exist_ok=True)
    engine.STATE_PATH = state / "current.json"
    if engine.STATE_PATH.exists():
        engine.STATE_PATH.unlink()

    def opening(job_id: int) -> str | None:
        try:
            engine.guard_open(job_id)
            return None
        except SystemExit as exc:
            return str(exc)

    expect(opening(2) is not None, "a run must not start at job-02")
    expect(opening(1) is None, "a run must be able to start at job-01")
    engine.write_state({"job": "job-01", "job_id": 1, "settled": False})
    expect(opening(1) is not None, "the open job must not be reopened")
    expect(opening(2) is not None, "the next job must not open while one is unsettled")
    engine.write_state({"job": "job-01", "job_id": 1, "settled": True})
    expect(opening(3) is not None, "jobs must not be skipped")
    expect(opening(2) is None, "the next job must open once the last one settled")
    shutil.rmtree(state, ignore_errors=True)

    curve = [reward_for({"passed": True, "pass_iteration": i}) for i in range(1, MAX_SUBMISSIONS + 1)]
    expect(curve[0] == 1.0, "a first-pass report should score 1.0")
    expect(all(a >= b for a, b in zip(curve, curve[1:])), "reward must fall as iterations rise")
    expect(reward_for({"passed": False}) == 0.0, "a rejected job scores 0.0")

    if FAILED:
        print(f"FAIL — {len(FAILED)} problem(s)")
        for line in FAILED:
            print(f"  {line}")
        return 1
    print(f"ok — {len(briefs)} briefs, oracle accepted, naive report rejected")
    print(f"    reward curve by iteration: {curve}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
