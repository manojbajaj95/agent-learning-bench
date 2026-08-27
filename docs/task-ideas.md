# Agent Learning Bench — Task Design

This document records the agreed task taxonomy, the feedback mechanism,
the measurement plan, and the approved task shortlist. It replaces the
earlier brainstorm notes.

## Goal

Test whether agents learn across runs inside one fixed environment.
Learning happens at the environment layer: one environment hosts many
sequential jobs (Harbor steps). Early turns are slow and exploratory.
Later turns reach correct answers with fewer actions. A stateless agent
stays flat; a learning agent improves.

One trial = one task = N steps = one growing agent context
(`--resume-trajectory`). This is an in-context learning system.
No cross-run trajectory transfer (`--load-trajectory`) is used.

## Three learning domains

Every task declares its domain.

### Domain 1 — Verifiable (closed)

Ground truth is observable during the step. The environment reacts to
each action: wall bumps, sensor reads, opponent responses, or a grader
CLI callable by the agent mid-step. The agent can iterate before it
commits.

- Feedback timing: immediate, inside the turn.
- Learning signal: action → reaction pairs within the episode, plus
  accumulated experience across episodes.
- Scoring rule: cap or penalize in-step checks when a grader exists;
  otherwise brute-force search replaces learning.
- Status: mechanism clear.

### Domain 2 — Semi-verifiable (post-release feedback) — TO BE STUDIED

The agent commits blind. A verifier grades after the step ends. The
verdict reaches the agent only in a later step. No intra-turn grading.

The learning claim here is subtle: external corrections must convert
into competence on items never graded before. How to implement this,
and how to demonstrate that real learning (not answer copying or
cache reuse) occurred, requires further study before any task in this
domain is built.

Draft mechanism (proposal only, under study):

- Feedback timing: after commit; consumed next turn.
- Mechanism sketch:
  - `tests/test.sh` calls a scoring script that writes two files:
    `/logs/verifier/reward.txt` (Harbor scoreboard, agent-invisible)
    and `/app/feedback.txt` (this turn's verdict, agent-visible).
  - The same script APPENDS one line per turn to
    `/app/history.jsonl` (append-only). History holds every past
    verdict, so feedback spans all steps, not just the last one.
  - `instruction.md` is static, minimal, and identical across steps.
    It does NOT point at specific files beyond the workspace root.
    Discovery of the workspace (history, notes) is part of the job.
  - Score = FIRST attempt of each turn. This prevents copying the
    previous corrected answer.
- Candidate learning evidence: first-attempt accuracy rising across
  steps; accuracy on holdout items never graded; exploration cost
  falling while accuracy holds.
- Open design questions:
  - Does an append-only verdict log plus agent notes constitute
    learning, or memory replay?
  - How much may the static instruction reveal about the workspace
    without solving part of the job?
  - What holdout construction proves generalization vs recall?
  - Does `--resume-trajectory` change the claim, and by how much?
- Status: NOT settled. Study item. No build until the questions above
  have answers.

### Domain 3 — Non-verifiable (closed)

No correctness signal exists at any point, during or after the step.
The agent sees only what exploration reveals: files, schemas, logs,
sensor views. Nothing grades its output.

- Feedback timing: none.
- Learning signal: pure efficiency. Fewer file opens, shorter paths,
  better priors at constant output quality. The environment itself
  (structure, layout, conventions) is the learnable object.
- Verification: compare cost metrics against turn 1 and against a
  stateless baseline. Output quality must not degrade while cost
  falls.
- Examples already in scope: codebase Q&A bank, web exploration bank,
  config typo hunt on a fixed tree.
- Status: mechanism clear.

## Measurement plan

Record for every turn, minimum:

```
turn, reward, env_actions, tokens, wall_sec, extra_metric
```

`extra_metric` is task-specific (files opened, probes used, path
length). Write a float per turn even if the trial headline uses
`multi_step_reward_strategy = "final"`.

Expected direction when learning works:

| Plot | Direction |
|---|---|
| First-attempt accuracy | up |
| Exploration cost (opens, probes, wrong tries) | down toward optimum |
| Actions/steps to done | down |

Three guards against shortcuts:

| Guard | Rules out |
|---|---|
| First-attempt scoring | copying corrected answers |
| Holdout tail (unseen family, last ~10%) | parroting stored answers |
| Cost curve | brute-force exploration as accuracy source |

## Run conditions

Same task, same steps, two conditions per agent:

| Condition | Chat | Files persist | Tests |
|---|---|---|---|
| Baseline | fresh each step | yes | file-based memory only |
| Main | `--resume-trajectory` | yes | in-context + files |

Instruction caveat: at high step counts the resumed chat grows long.
Instructions direct the agent to keep durable knowledge in
`/app/notes.md`; old chat turns are skippable. Otherwise context drift
reads as forgetting, which is a harness artifact.

## Approved task shortlist

Four environments. Four distinct learning objects. All reuse the
Tally skeleton: generated step dirs, engine under `/opt`, float reward
per step, verifier-written feedback for the next step.

### 1. Warden — opponent modeling (Domain 1)

Dark-Souls-style turn-based duel. One deterministic boss bot, seeded
state machine: fixed opening, telegraphed heavy attack one action
ahead, punishable sweep recovery, punishes repeated player moves.

- Interface: container CLI (`warden attack|block|dodge left|right|parry|potion`).
- One Harbor step = one fight. Death ends the step.
- Reward: `0.7 × boss_hp_removed_fraction + 0.3 × win`.
- Feedback: live boss responses in-step; post-fight log summary.
- Curves: death rate falls, win rate rises, actions-to-kill falls.
- Extension path: phase 2 below 50% HP, additional movesets, second
  boss sharing some habits. Still one environment, still deterministic.

### 2. Data Lake — D2C schema + hidden ontology (Domain 3)

One frozen direct-to-consumer brand. ~40–60 CSVs under `/data`,
cryptic names, terse columns, no data dictionary. Traps: cents vs
dollars, dual order timestamps, duplicate customers, cancelled orders.
The ontology (net revenue vs GMV, channel definitions, product
taxonomy, canonical snapshots) lives only in the verifier.

- Steps: one analyst question per turn from a 50–100 item bank with
  precomputed gold results. Holdout tail from an unseen family.
- Answer format: scalar, row set, or sorted list; exact match with
  epsilon tolerance.
- Feedback (level-dependent): expected vs got; optional error class.
- Second metric: files opened per turn; must fall while accuracy
  holds.
- Optional in-step grader CLI (`lake grade`, capped calls) lifts this
  task into Domain 1 for ablation runs.

### 3. Expense Desk — unwritten policy induction (Domain 3)

New hire submits expenses against an unrecorded company policy.
Engine: pure approval function over `{category, merchant, amount,
date, trip_id, receipts_attached, submit_delay_days}`. Hidden policy:
meal caps by city tier, no alcohol, receipt threshold, per-diem rules,
30-day window, client-entertainment exception.

- Steps: batch of 10 reports per turn. Agent decides
  approve/reject/fix (+ corrected amount).
- Reward: correct decisions / 10; partial credit for right decision,
  wrong amount.
- Feedback: true decision plus reason code (`over_cap`, `late_filing`).
  Codes reveal rule families without printing the policy.
- Siblings on the same engine shape: permits office, customs broker,
  refund desk.

### 4. Courier / Picker — spatial map learning (Domain 1)

One 64×64 grid. Walls permanent. Local sensors only (adjacent walls +
own coordinates). Two jobs on one simulator:

- Courier (A→B): start and goal change every step. Reward =
  `1 − (path_len − optimal)/budget`, 0 on timeout.
- Picker (fetch-and-return): robot starts at dock; item drops at a
  random reachable cell each step; retrieve and return. Success within
  budget; score = action count. Optimal ≈ 2 × distance.
- Actions counted inside the engine.
- Holdout: starts in an unvisited district after N steps. A mapper
  passes; a route memorizer fails.
- Diagnostic (unscored): wall-map IoU vs true grid.

## Domain coverage matrix

| Task | Domain | Learning object | Headline curve |
|---|---|---|---|
| Warden | 1 | rival behavior model | win rate up; actions-to-kill down |
| Data Lake | 2 (1 via grader) | schema + hidden ontology | accuracy up; file opens down |
| Expense Desk | 2 | unwritten policy | decision accuracy up |
| Courier/Picker | 1 | spatial map | actions-to-done down toward optimum |

## Implementation notes (Harbor)

- Step count/order are declared statically in `task.toml`
  (`[[steps]]`). Per-turn content is dynamic via
  `workdir/setup.sh` (before agent) and `tests/test.sh` (after).
  Generate identical step dirs with a script.
- Engine state lives in `/opt` (persists across steps, outside the
  agent workspace).
- `min_reward` aborts on failure only; there is no stop-on-success.
  Fixed episode budgets are accepted.
- Feedback levels remain a knob for Domain 2 tasks:
  level 0 none / level 1 value only / level 2 value + error class /
  level 3 in-step grader. Report all levels as separate conditions.

## Build order

1. Courier/Picker (Domain 1 flagship; continuous reward from turn 1).
2. Data Lake (Domain 2 headline claim; blocked until the Domain 2
   study settles the mechanism).
3. Expense Desk (Domain 2, same blocker as Data Lake).
4. Warden (Domain 1, richest engine).

Domain 1 tasks can start now. Domain 2 tasks wait on the study of the
post-release feedback mechanism: what evidence counts as learning,
how holdouts are constructed, and how much the instruction may reveal.

## Removed from the shortlist

Earlier stubs (auction, negotiation, blackjack, clicker, Hanabi-style,
ticket routing, form extraction, replenishment, shift scheduling, and
similar) are dropped from this document: low clarity on learning
signal or weak fit to the standalone-step constraint. Re-add only with
a domain declaration and a measurable curve.
