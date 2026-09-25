# Report check

The agent writes 26 reports for one company. The house style guide is hidden. The agent learns it from review comments. Later reports should be accepted on the first submission.

## Task type

Verifiable. `report submit` accepts or rejects the draft during the step. The agent can edit and submit again before the step ends. The grader allows six submissions per job.

## Labels

`fixed`, `ordered`. The style guide and the job list stay the same on every run. Later jobs use what earlier reviews taught.

## Environment

- Image: `ubuntu:24.04` with `python3` and sudo
- Agent user: `agent`
- Hidden rules, briefs, and state: `/opt/report` (root, mode 700)
- Public file: `/app/world/RULES.md` (it does not list the rules)
- Persistent files: `/app/notes.md`, `/app/desk/ledger.jsonl`
- Commands: `report submit`, `report status`
- Network: `public`
- No dataset download. Briefs are in [`environment/report/briefs.json`](environment/report/briefs.json).

The same instruction text is used on every step. It does not name the job or the active rules. See [`instruction.md`](instruction.md).

## Step design

One trial is 26 jobs, `job-01` through `job-26`. One step is one report. Setup publishes `/app/brief.md` and removes `/app/report.md`. Notes stay.

Rules turn on by tier and stay on:

| Tier | Jobs | What is added |
|---|---|---|
| 1 | job-01 … job-06 | Title, sections, terminology, summary length, sign-off |
| 2 | job-07 … job-13 | Metadata, money, dates, findings, risk |
| 3 | job-14 … job-26 | No hedging, appendix table, word limit |

`job-23` … `job-26` are the holdout. They use two new report types. Every rule on them was taught earlier.

## Learning goal

The learning object is the hidden style guide, including the term list and the hedge list. Acceptance should stay high while submissions per job fall toward 1. First-submission violations should fall too. Baseline starts a fresh chat each job. In-context learning resumes the same chat.

## Reward and cost

Reward depends on which submission was accepted:

| Accepted on | 1 | 2 | 3 | 4 | 5 | 6 | never |
|---|---|---|---|---|---|---|---|
| Reward | 1.0 | 0.85 | 0.7 | 0.55 | 0.4 | 0.4 | 0.0 |

A report that is accepted and then edited before settle scores 0. Harbor averages the job rewards.

Each job appends one row to `/app/desk/ledger.jsonl` with `reward`, `iterations`, `rule_violations`, `first_violations`, and `passed`. `rule_violations` counts rules broken on the first submission.

Harbor records `cost_usd`, input tokens, output tokens, and step duration. The learning curve is `iterations` and `rule_violations` falling while `reward` stays high.

## Details

The sections below keep the review loop, the controls, and the run commands.

## Feedback domain

Verifiable. The agent can grade itself inside the step with `report submit`, so
it can react before the step ends. The grader is capped at **six submissions per
job** and the reward decays with each one, so brute-force resubmission cannot
replace learning the rules.

## The loop

```text
setup.sh   ->  /app/brief.md, a fresh job; /app/report.md removed; /app/notes.md kept
agent      ->  writes /app/report.md, runs `report submit`, fixes, submits again
test.sh    ->  settles the job, writes the reward and one ledger row
```

Harbor uploads `workdir/` into the agent's working directory and runs `setup.sh`
**as the agent user**, not as root (`_prepare_step` wraps it in
`with_default_user(agent.user)`). So `report brief <n>` is reachable from the
agent's own shell, and an env-var guard on it would be useless — sudo strips the
variable either way. What holds it shut is the run order: the desk opens a job
only when it is the next one and the job before it has been settled. The agent's
turn always sits inside an open, unsettled job, so there is no point during the
turn at which it can reopen its job or jump to the next one. The verifier runs
as root and settles through the engine directly, out of the agent's reach.

`report submit` returns one of:

```text
DESK REVIEW — job-15 — submission 1 of 6
REJECTED — 3 item(s)

  R03-TERMS       house terminology was not used: "customer" -> "account holder"
  R07-MONEY       amounts are written as $1,240,000 with thousand separators and no decimals; found "2550000 dollars"
  R05-SIGNOFF     the last line of a report must be "-- End of report --"
```

The desk names only the rules the submitted report broke. It never names a rule
the report satisfied, never names a rule that is not active for the job, and has
no command that prints the guide.

## Hidden rules

Thirteen deterministic rules covering sections, required fields, terminology,
number and date formatting, and length. They switch on by tier and never switch
off, so a late job is graded on everything an early job was graded on.

| Tier | Jobs | Rules added |
|---|---|---|
| 1 | job-01 … job-06 | title line, section set and order, house terminology, Summary length, sign-off |
| 2 | job-07 … job-13 | metadata block (preparer, period, register ref), money format, ISO dates, Findings bullets, Risk section |
| 3 | job-14 … job-26 | no hedging, Appendix figure table, whole-report word limit |

Two of those rules carry a hidden vocabulary: R03-TERMS maps 26 plain words
("customer", "user", "sales", "glitch", "ticket", "outage", "deadline", "staff",
"money", …) onto house terms, and R10-NO-HEDGE bans 21 hedges ("maybe",
"likely", "arguably", "in our view", "it looks like", "could be", …). The desk
quotes at most four terms and three hedges per rejection, so the full lists
only come out over several jobs. Every term appears in a brief before the
holdout, and every hedge appears in a tier-3 brief before the holdout.

The briefs are written in plain language and deliberately break house style:
they say "customer", "revenue", "problem", "1240000 dollars", "March 12, 2026"
and open with "Perhaps". A report that copies the brief is rejected on several
rules at once.

## Holdout

`job-23 … job-26` are two report types the agent has never seen — Incident
Review and Vendor Assessment — with new subjects and new content. Every rule
that applies to them was learned on the earlier report types; none of them
received a correction on this content. They test whether the agent carries the
style guide across report types rather than memorising per-type templates.

Holdout steps are graded exactly like the rest, so `iterations` on the last four
jobs is the transfer measurement.

## Reward and metrics

Reward comes from the submission that got the report accepted:

| Accepted on submission | 1 | 2 | 3 | 4 | 5 | 6 | never |
|---|---|---|---|---|---|---|---|
| Reward | 1.0 | 0.85 | 0.7 | 0.55 | 0.4 | 0.4 | 0.0 |

The floor keeps correctness worth more than speed while still charging for
exploration. A report that is accepted and then edited before the step ends
scores 0: the verifier re-checks the file on disk.

Each step appends one row to `/app/desk/ledger.jsonl`:

```json
{"job": "job-15", "tier": 3, "holdout": false, "reward": 0.85, "iterations": 2,
 "rule_violations": 10, "first_violations": ["R01-TITLE", "..."], "passed": true}
```

`rule_violations` counts the rules broken on the **first** submission of the
job. That is the first-attempt signal: it should fall as the agent learns the
guide, independently of whether it recovers later in the step.

`tokens` and `wall_sec` come from the Harbor job record:

```bash
python3 tools/report_runs.py --jobs-dir jobs --task report-check --out-dir reports
```

## Controls

| Control | What it prevents |
|---|---|
| Six-submission cap, decaying reward | Resubmitting until something passes |
| First-submission violation count | A late fix hiding that nothing was learned |
| Holdout tail on unseen report types | Memorising one report type instead of the guide |
| Rules in `/opt/report`, mode 700, behind sudo | Reading the guide instead of learning it |
| Same instruction on every step | The prompt leaking the job's difficulty |
| Re-check at settle | Passing, then editing the file |
| Run-order check on `brief` | Reopening the current job to reset its submissions |

Two things the run-order check does not cover, both harmless to the result. A
run with the verifier disabled never settles a job, so the next step's setup is
refused and the run stalls; this task has no meaning without its verifier
anyway. And an agent that leaves a background process running past the end of
its turn could open the next job early, which strands its own step at reward 0
and gains it nothing.

## Environment details

- Base image: `ubuntu:24.04` + `python3` + `sudo`
- Agent runs as `agent`; the engine, rules and brief bank live in `/opt/report`,
  owned by root, mode 700
- The agent reaches the desk only through `report`, a wrapper over
  `sudo -n /usr/local/bin/report-desk`. sudo resets the environment, so the
  agent cannot set the guard variables that open `brief` and `settle`
- Engine: [`environment/report/engine.py`](environment/report/engine.py) (rules,
  review, reward, oracle text) and
  [`environment/report/cli.py`](environment/report/cli.py)
- Agent commands: `report submit`, `report status`
- Harbor hooks: `report brief <n>` in `setup.sh` (runs as the agent, gated by the
  run-order check) and `REPORT_SETTLE=1 python3 /opt/report/cli.py settle` in
  `test.sh` (runs as root)
- The verifier shares the agent's container, so `/opt/report/state` carries
  across the two phases. Do not add a `[verifier.environment]` block
- Public and deliberately unhelpful: `/app/world/RULES.md`
- Persistent across steps in a trial: `/app/notes.md`, `/app/desk/ledger.jsonl`,
  `/app/sessions/`

No network data to download. The brief bank is
[`environment/report/briefs.json`](environment/report/briefs.json).

## Layout

```
tasks/report-check/
├── task.toml               # generated
├── instruction.md
├── generate_steps.py
├── test_engine.py
├── environment/
│   ├── Dockerfile
│   └── report/
│       ├── engine.py         # hidden rules, review, reward, oracle text
│       ├── cli.py
│       ├── briefs.json     # 26 briefs, 4 of them holdout
│       └── RULES.md     # public, says nothing about the rules
└── steps/
    └── job-01 … job-26/
        ├── instruction.md
        ├── workdir/setup.sh    # publish the brief, clear report.md, remove self
        ├── tests/test.sh       # settle -> reward + ledger row
        └── solution/solve.sh   # oracle report, accepted on submission 1
```

## Building the steps

```bash
python3 generate_steps.py            # all 26 jobs
python3 generate_steps.py --n 8      # smoke run, first 8
```

The generator writes `steps/` and `task.toml` from `instruction.md` and
`briefs.json`. Oracle reports are composed by the same module that grades them,
so the two cannot drift.

`test_engine.py` checks that against every brief: the oracle is accepted with no
violations, a report that copies the brief is rejected on at least three rules,
the rule set only grows with tier, the holdout uses report types that appear
nowhere earlier, every hidden term and hedge is graded before the holdout, the
oracle keeps none of them, and the published brief leaks no rule.

```bash
python3 test_engine.py
```

It also checks the run-order guard: a run cannot start in the middle, the open
job cannot be reopened, the next job cannot open while one is unsettled, and no
job can be skipped.

To check the built environment end to end, drive all twenty-six steps with the
oracle the way Harbor does — `setup.sh` and `solve.sh` as the agent, `test.sh`
as root — and expect reward 1.0 at one submission on every step:

```bash
docker build -t report-check environment/
```

## Running

Same model in all three conditions. Needs `OPENAI_API_KEY`. Use the OpenAI id
`gpt-5.6-luna` (dot, not hyphen).

### Baseline

Harbor `pi`. Fresh chat each step. `/app/notes.md` and `/app/desk/` persist
because the container persists; `/app/sessions/` stays empty.

```bash
harbor run -p tasks/report-check -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5
```

### Pi sessions

Same `pi`, plus each step's session JSONL copied to `/app/sessions/`.

```bash
PYTHONPATH=. harbor run -p tasks/report-check \
  -a agents.pi_sessions:PiSessionsAgent \
  -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5
```

### In-context learning

Same `pi`, with the chat resumed across steps.

```bash
harbor run -p tasks/report-check -a pi -m openai/gpt-5.6-luna \
  --resume-trajectory \
  --agent-timeout-multiplier 5
```

## Expected curve

A writer who learns nothing pays for every rule again on every job: violations
on the first submission stay flat and iterations stay near the cap, with reward
sitting around the floor. A writer who keeps a usable record of the corrections
should reach one submission on the later jobs of each tier, take a bump at
job-07 and job-14 where new rules switch on, and — the result that matters —
stay near one submission on `job-23 … job-26`, where the report type is new and
the guide is not.
