#!/usr/bin/env python3
"""Reporting desk engine: publish a brief, review a report, settle a step.

The house style rules live in this file and nowhere the agent can read. The
desk reports only the rules a submission broke. It never lists the rule set,
never names a rule the report satisfied, and never names a rule that is not
active for the current job.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRIEFS_PATH = HERE / "briefs.json"

APP = Path(os.environ.get("REPORT_APP", "/app"))
STATE_DIR = Path(os.environ.get("REPORT_STATE_DIR", "/opt/report/state"))
REWARD_PATH = Path(os.environ.get("REPORT_REWARD", "/logs/verifier/reward.txt"))

BRIEF_PATH = APP / "brief.md"
REPORT_PATH = APP / "report.md"
NOTES_PATH = APP / "notes.md"
LEDGER_PATH = APP / "desk" / "ledger.jsonl"
STATE_PATH = STATE_DIR / "current.json"

MAX_SUBMISSIONS = 6
AGENT_USER = os.environ.get("REPORT_AGENT_USER", "agent")
PREPARER = "Reporting Desk"
SIGNOFF = "-- End of report --"
SUMMARY_MIN_WORDS = 15
SUMMARY_MAX_WORDS = 60
REPORT_MAX_WORDS = 350

# --- hidden house style -----------------------------------------------------

# Rules switch on by tier. A rule stays on for every later tier, so a late job
# is graded on everything an early job was graded on.
TIER_RULES = {
    1: ["R01-TITLE", "R02-SECTIONS", "R03-TERMS", "R04-SUMMARY-LEN", "R05-SIGNOFF"],
    2: ["R06-META", "R07-MONEY", "R08-DATES", "R09-BULLETS", "R13-RISK"],
    3: ["R10-NO-HEDGE", "R11-APPENDIX", "R12-LENGTH"],
}

TERMS = [
    ("customers", "account holders"),
    ("customer", "account holder"),
    ("clients", "account holders"),
    ("client", "account holder"),
    ("users", "account holders"),
    ("user", "account holder"),
    ("revenues", "net billings"),
    ("revenue", "net billings"),
    ("sales", "net billings"),
    ("profit", "net margin"),
    ("problems", "exceptions"),
    ("problem", "exception"),
    ("issues", "exceptions"),
    ("issue", "exception"),
    ("glitches", "exceptions"),
    ("glitch", "exception"),
    ("bugs", "exceptions"),
    ("bug", "exception"),
    ("tickets", "cases"),
    ("ticket", "case"),
    ("outages", "service interruptions"),
    ("outage", "service interruption"),
    ("deadlines", "due dates"),
    ("deadline", "due date"),
    ("staff", "personnel"),
    ("money", "funds"),
]

HEDGES = [
    "maybe",
    "probably",
    "perhaps",
    "possibly",
    "presumably",
    "likely",
    "arguably",
    "somewhat",
    "we think",
    "we believe",
    "we feel",
    "in our view",
    "it seems",
    "seems to",
    "it appears",
    "appears to",
    "it looks like",
    "sort of",
    "kind of",
    "might be",
    "could be",
]

# Oracle only. These hedges carry the verb, so dropping them outright would
# leave the sentence without one.
HEDGE_REWRITES = [
    ("seems to have", "has"),
    ("appears to have", "has"),
    ("might be", "is"),
    ("could be", "is"),
]

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

MONEY_TOKEN = re.compile(r"\$\d(?:[\d,]*\d)?(?:\.\d+)?")
MONEY_OK = re.compile(r"^\$\d{1,3}(?:,\d{3})*$")
MONEY_WORDY = re.compile(r"\b\d[\d,]*(?:\.\d+)?\s*(?:dollars|USD)\b|\bUSD\s*\d[\d,]*", re.I)
DATE_LONG = re.compile(
    r"\b(" + "|".join(MONTHS) + r")[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b", re.I
)
DATE_SLASH = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b|\b\d{4}/\d{1,2}/\d{1,2}\b")


def load_briefs() -> list[dict]:
    return json.loads(BRIEFS_PATH.read_text(encoding="utf-8"))


def brief_by_id(job_id: int) -> dict:
    for item in load_briefs():
        if item["id"] == job_id:
            return item
    raise SystemExit(f"no brief with id {job_id}")


def step_name(job_id: int) -> str:
    return f"job-{job_id:02d}"


def active_rules(tier: int) -> list[str]:
    codes: list[str] = []
    for level in sorted(TIER_RULES):
        if level <= tier:
            codes.extend(TIER_RULES[level])
    return codes


def money(amount: int) -> str:
    return f"${amount:,}"


def ref_code(brief: dict) -> str:
    return f"RC-{brief['period_end'][:4]}-{brief['id']:03d}"


def meta_lines(brief: dict) -> list[str]:
    return [
        f"**Prepared by:** {PREPARER}",
        f"**Period:** {brief['period_start']} to {brief['period_end']}",
        f"**Ref:** {ref_code(brief)}",
    ]


def expected_sections(brief: dict, active: list[str]) -> list[str]:
    names = ["Summary", "Findings"]
    if brief.get("risk_note") and "R13-RISK" in active:
        names.append("Risk")
    names.append("Recommendation")
    if brief.get("figures") and "R11-APPENDIX" in active:
        names.append("Appendix")
    return names


# --- text helpers -----------------------------------------------------------


def count_words(text: str) -> int:
    cleaned = re.sub(r"[#*_`>|]", " ", text)
    cleaned = re.sub(r"^\s*-\s+", " ", cleaned, flags=re.M)
    return sum(1 for tok in cleaned.split() if any(c.isalnum() for c in tok))


def strip_signoff(lines: list[str]) -> list[str]:
    out = list(lines)
    while out and not out[-1].strip():
        out.pop()
    if out and out[-1].strip() == SIGNOFF:
        out.pop()
    return out


def sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    found: list[tuple[str, list[str]]] = []
    body: list[str] = []
    for line in lines:
        head = re.match(r"^##\s+(.*?)\s*$", line)
        if head:
            body = []
            found.append((head.group(1), body))
        elif found:
            body.append(line)
    return found


def section_body(text_sections: list[tuple[str, list[str]]], name: str) -> list[str] | None:
    for found_name, body in text_sections:
        if found_name == name:
            return body
    return None


# --- brief -> house style ---------------------------------------------------


def _drop_hedges(text: str) -> str:
    out = text
    for hedge, plain in HEDGE_REWRITES:
        out = re.sub(rf"(?i)\b{re.escape(hedge)}\b", plain, out)
    for hedge in HEDGES:
        out = re.sub(rf"(?i)\b{re.escape(hedge)}\b\s*", "", out)
    out = out.strip()
    return out[:1].upper() + out[1:] if out else out


def _apply_terms(text: str) -> str:
    out = text
    for bad, good in TERMS:
        def swap(match: re.Match[str], good: str = good) -> str:
            word = match.group(0)
            return good[:1].upper() + good[1:] if word[:1].isupper() else good

        out = re.sub(rf"(?i)\b{bad}\b", swap, out)
    return out


def _apply_money(text: str) -> str:
    def wordy(match: re.Match[str]) -> str:
        digits = re.sub(r"[^\d]", "", match.group(0))
        return money(int(digits))

    return MONEY_WORDY.sub(wordy, text)


def _apply_dates(text: str) -> str:
    def iso(match: re.Match[str]) -> str:
        name, day, year = match.group(1), match.group(2), match.group(3)
        return f"{year}-{MONTHS[name.lower()]:02d}-{int(day):02d}"

    pattern = re.compile(
        r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2}),?\s+(\d{4})\b", re.I
    )
    return pattern.sub(iso, text)


def house_style(text: str) -> str:
    return _apply_dates(_apply_money(_apply_terms(_drop_hedges(text))))


def compose_gold(brief: dict) -> str:
    active = active_rules(brief["tier"])
    lines = [f"# {brief['report_type']}: {brief['subject']}"]
    if "R06-META" in active:
        lines += meta_lines(brief)
    lines += ["", "## Summary", "", house_style(brief["summary"])]
    lines += ["", "## Findings", ""]
    lines += [f"- {house_style(item)}" for item in brief["findings"]]
    if brief.get("risk_note") and "R13-RISK" in active:
        lines += ["", "## Risk", "", house_style(brief["risk_note"])]
    lines += ["", "## Recommendation", "", house_style(brief["recommendation"])]
    if brief.get("figures") and "R11-APPENDIX" in active:
        lines += ["", "## Appendix", "", "| Label | Amount |", "| --- | --- |"]
        lines += [f"| {f['label']} | {money(f['amount'])} |" for f in brief["figures"]]
    lines += ["", SIGNOFF]
    return "\n".join(lines) + "\n"


# --- the review --------------------------------------------------------------


def check(text: str, brief: dict) -> list[tuple[str, str]]:
    """Return [(rule code, desk comment)] for every active rule the report breaks."""
    active = active_rules(brief["tier"])
    raw_lines = text.splitlines()
    lines = strip_signoff(raw_lines)
    found = sections(lines)
    names = [name for name, _ in found]
    body = "\n".join(lines)
    faults: list[tuple[str, str]] = []

    def fault(code: str, message: str) -> None:
        if code in active:
            faults.append((code, message))

    title = raw_lines[0].strip() if raw_lines else ""
    want_title = f"# {brief['report_type']}: {brief['subject']}"
    if title != want_title:
        fault("R01-TITLE", f'the first line must be exactly "{want_title}"')

    want_sections = expected_sections(brief, active)
    if names != want_sections:
        fault(
            "R02-SECTIONS",
            "this report needs these level-two sections, in this order and no others: "
            + ", ".join(want_sections),
        )

    hits = []
    for bad, good in TERMS:
        if re.search(rf"(?i)\b{bad}\b", body):
            hits.append(f'"{bad}" -> "{good}"')
    if hits:
        fault(
            "R03-TERMS",
            "house terminology was not used: " + "; ".join(hits[:4]),
        )

    summary = section_body(found, "Summary")
    if summary is not None:
        n = count_words("\n".join(summary))
        if not SUMMARY_MIN_WORDS <= n <= SUMMARY_MAX_WORDS:
            fault(
                "R04-SUMMARY-LEN",
                f"the Summary section runs {n} words; the desk takes "
                f"{SUMMARY_MIN_WORDS} to {SUMMARY_MAX_WORDS}",
            )

    tail = [ln for ln in raw_lines if ln.strip()]
    if not tail or tail[-1].strip() != SIGNOFF:
        fault("R05-SIGNOFF", f'the last line of a report must be "{SIGNOFF}"')

    want_meta = meta_lines(brief)
    got_meta = [ln.strip() for ln in raw_lines[1:4]]
    if got_meta != want_meta:
        fault(
            "R06-META",
            "the three lines under the title must be exactly: " + " / ".join(want_meta),
        )

    bad_money = [tok for tok in MONEY_TOKEN.findall(body) if not MONEY_OK.match(tok)]
    bad_money += MONEY_WORDY.findall(body)
    if bad_money:
        fault(
            "R07-MONEY",
            "amounts are written as $1,240,000 with thousand separators and no "
            "decimals; found " + ", ".join(f'"{b.strip()}"' for b in bad_money[:3]),
        )

    bad_dates = DATE_LONG.findall(body)
    if bad_dates or DATE_SLASH.search(body):
        sample = DATE_LONG.search(body) or DATE_SLASH.search(body)
        fault(
            "R08-DATES",
            "dates are written as 2026-03-31; found "
            f'"{sample.group(0) if sample else ""}"',
        )

    findings = section_body(found, "Findings")
    if findings is not None:
        content = [ln for ln in findings if ln.strip()]
        bullets = [ln for ln in content if ln.strip().startswith("- ")]
        if len(bullets) != len(content):
            fault("R09-BULLETS", "the Findings section holds bullets only, nothing else")
        elif len(bullets) < 3:
            fault(
                "R09-BULLETS",
                f"the Findings section needs at least 3 bullets; found {len(bullets)}",
            )
        elif any(not ln.strip().endswith(".") for ln in bullets):
            fault("R09-BULLETS", "every Findings bullet ends with a full stop")

    if brief.get("risk_note"):
        risk = section_body(found, "Risk")
        if risk is None or count_words("\n".join(risk)) < 8:
            fault(
                "R13-RISK",
                "this brief carries a risk note, so the report needs a Risk section "
                "of at least 8 words",
            )

    hedged = [h for h in HEDGES if re.search(rf"(?i)\b{re.escape(h)}\b", body)]
    if hedged:
        fault(
            "R10-NO-HEDGE",
            "the desk does not print hedged language: " + ", ".join(f'"{h}"' for h in hedged[:3]),
        )

    if brief.get("figures"):
        appendix = section_body(found, "Appendix")
        want_table = ["| Label | Amount |", "| --- | --- |"]
        want_table += [f"| {f['label']} | {money(f['amount'])} |" for f in brief["figures"]]
        got_table = [ln.strip() for ln in (appendix or []) if ln.strip()]
        if got_table != want_table:
            fault(
                "R11-APPENDIX",
                "the Appendix holds every brief figure as a table, exactly: "
                + " / ".join(want_table),
            )

    total = count_words(body)
    if total > REPORT_MAX_WORDS:
        fault("R12-LENGTH", f"the report runs {total} words; the desk takes {REPORT_MAX_WORDS}")

    order = {code: i for i, code in enumerate(active)}
    faults.sort(key=lambda item: order.get(item[0], 99))
    return faults


# --- state ------------------------------------------------------------------


def hand_to_agent(path: Path) -> None:
    """Harbor runs setup.sh as the agent, but the desk answers it through sudo.

    Anything the desk writes for the agent to edit has to end up owned by the
    agent, not by root.
    """
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        return
    try:
        import pwd

        account = pwd.getpwnam(AGENT_USER)
    except (ImportError, KeyError):
        return
    try:
        os.chown(path, account.pw_uid, account.pw_gid)
    except OSError:
        pass


def read_state() -> dict:
    if not STATE_PATH.exists():
        raise SystemExit("no job is open at the desk")
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def write_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def reward_for(state: dict) -> float:
    if not state.get("passed"):
        return 0.0
    return round(max(0.4, 1.0 - 0.15 * (state["pass_iteration"] - 1)), 2)


# --- commands ---------------------------------------------------------------


def render_brief(brief: dict) -> str:
    lines = [
        f"# Job {step_name(brief['id'])} — {brief['report_type']}",
        "",
        f"**Report type:** {brief['report_type']}",
        f"**Subject:** {brief['subject']}",
        f"**Period:** {brief['period_start']} to {brief['period_end']}",
        f"**Job number:** {brief['id']:03d}",
        "",
        "## Source material",
        "",
        "Desk material, in plain language. It is not written in house style.",
        "",
        f"- {brief['summary']}",
    ]
    lines += [f"- {item}" for item in brief["findings"]]
    if brief.get("risk_note"):
        lines.append(f"- {brief['risk_note']}")
    lines.append(f"- {brief['recommendation']}")
    if brief.get("figures"):
        lines += ["", "## Figures", "", "| Label | Amount |", "| --- | --- |"]
        lines += [f"| {f['label']} | {f['amount']} |" for f in brief["figures"]]
    lines += [
        "",
        "## Deliverable",
        "",
        "Write the report to `/app/report.md`, then run `report submit`.",
        f"The desk takes at most {MAX_SUBMISSIONS} submissions for this job.",
        "",
    ]
    return "\n".join(lines)


def guard_open(job_id: int) -> None:
    """Only the next job in the run may be opened, and only once the one before
    it has been settled.

    Harbor runs setup.sh as the agent user, so `brief` is reachable from the
    agent's shell. The agent's turn always sits inside an open, unsettled job,
    so there is no moment at which this check lets it reopen the job it is
    working on or jump ahead to the next one.
    """
    first = min(item["id"] for item in load_briefs())
    if not STATE_PATH.exists():
        if job_id != first:
            raise SystemExit(f"the run opens with {step_name(first)}")
        return
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not state.get("settled"):
        raise SystemExit(f"{state['job']} is still open at the desk")
    if job_id != state["job_id"] + 1:
        raise SystemExit(f"{step_name(state['job_id'] + 1)} is the next job")


def cmd_brief(job_id: int) -> str:
    guard_open(job_id)
    brief = brief_by_id(job_id)
    APP.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    BRIEF_PATH.write_text(render_brief(brief), encoding="utf-8")
    hand_to_agent(BRIEF_PATH)
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()
    if not NOTES_PATH.exists():
        NOTES_PATH.write_text("", encoding="utf-8")
    hand_to_agent(NOTES_PATH)
    write_state(
        {
            "job": step_name(job_id),
            "job_id": job_id,
            "tier": brief["tier"],
            "holdout": bool(brief.get("holdout")),
            "submissions": 0,
            "passed": False,
            "pass_iteration": 0,
            "first_violations": None,
            "last_violations": [],
            "settled": False,
        }
    )
    return f"{step_name(job_id)} open at the desk. Brief written to {BRIEF_PATH}."


def cmd_submit() -> tuple[str, int]:
    state = read_state()
    brief = brief_by_id(state["job_id"])
    if not REPORT_PATH.exists():
        return (f"No {REPORT_PATH}. Write the report first.", 2)
    if state["submissions"] >= MAX_SUBMISSIONS:
        return (
            f"The desk has closed {state['job']} after {MAX_SUBMISSIONS} submissions.",
            1,
        )

    faults = check(REPORT_PATH.read_text(encoding="utf-8"), brief)
    state["submissions"] += 1
    codes = [code for code, _ in faults]
    if state["first_violations"] is None:
        state["first_violations"] = codes
    state["last_violations"] = codes
    if not faults and not state["passed"]:
        state["passed"] = True
        state["pass_iteration"] = state["submissions"]
    write_state(state)

    head = (
        f"DESK REVIEW — {state['job']} — submission "
        f"{state['submissions']} of {MAX_SUBMISSIONS}"
    )
    if not faults:
        return (f"{head}\nACCEPTED\n", 0)
    body = "\n".join(f"  {code:<16}{message}" for code, message in faults)
    left = MAX_SUBMISSIONS - state["submissions"]
    tail = (
        f"\nFix {REPORT_PATH} and run: report submit"
        if left
        else "\nNo submissions left for this job."
    )
    return (f"{head}\nREJECTED — {len(faults)} item(s)\n\n{body}\n{tail}\n", 1)


def cmd_status() -> str:
    state = read_state()
    left = MAX_SUBMISSIONS - state["submissions"]
    if state["passed"]:
        verdict = f"accepted on submission {state['pass_iteration']}"
    elif state["submissions"]:
        verdict = f"rejected, {len(state['last_violations'])} item(s)"
    else:
        verdict = "nothing submitted yet"
    return f"{state['job']} — {state['submissions']} used, {left} left — {verdict}"


def cmd_settle() -> str:
    state = read_state()
    brief = brief_by_id(state["job_id"])
    # The reward follows the file that is on disk at the end of the step, not
    # an accepted draft that was edited afterwards.
    final_ok = REPORT_PATH.exists() and not check(
        REPORT_PATH.read_text(encoding="utf-8"), brief
    )
    if not final_ok:
        state["passed"] = False
    state["settled"] = True
    write_state(state)
    reward = reward_for(state)
    first = state["first_violations"]
    row = {
        "job": state["job"],
        "tier": state["tier"],
        "holdout": state["holdout"],
        "reward": reward,
        "iterations": state["submissions"],
        "rule_violations": None if first is None else len(first),
        "first_violations": first or [],
        "passed": bool(state["passed"]),
    }
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REWARD_PATH.write_text(f"{reward}\n", encoding="utf-8")
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")
    return (
        f"{row['job']} reward={reward} iterations={row['iterations']} "
        f"rule_violations={row['rule_violations']} passed={str(row['passed']).lower()} "
        f"holdout={str(row['holdout']).lower()}"
    )
