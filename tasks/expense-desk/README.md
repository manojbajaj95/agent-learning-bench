# Expense Desk

Expense Desk is a proposed Harbor multi-step task for learning an unwritten
expense policy. It follows the design in
[`docs/task-ideas.md`](../../docs/task-ideas.md#3-expense-desk--unwritten-policy-induction-domain-3).
This directory contains the design only. It is not yet a runnable Harbor task.

## Goal

The agent acts as a new expense reviewer. On each Harbor step, it receives a
batch of ten reports. For each report, it must choose one result:

- approve;
- reject; or
- fix, with a corrected amount.

The written instructions do not include the company policy. The agent must
infer it from results across steps and apply it to new reports.

## Hidden policy

A pure approval function evaluates these report fields:

```text
category, merchant, amount, date, trip_id, receipts_attached, submit_delay_days
```

The fixed policy includes:

- meal caps by city tier;
- no alcohol;
- a receipt threshold;
- per-diem rules;
- a 30-day submission window; and
- a client-entertainment exception.

The policy and evaluator stay outside the agent workspace. The same policy is
used for the full trial.

## Episode and feedback

One step contains ten reports. The agent commits one batch before the verifier
runs. There is no in-step grader.

After settlement, feedback can include the true decision and one reason code,
such as `over_cap` or `late_filing`. The feedback is available on the next
step. It identifies a rule family without printing the full policy.

The agent can keep inferred rules in `/app/notes.md`. A persistent history must
append prior results instead of replacing them.

## Answer format

The agent writes `/app/decisions.json`:

```json
[
  {"report_id": "R001", "decision": "approve"},
  {"report_id": "R002", "decision": "reject"},
  {"report_id": "R003", "decision": "fix", "corrected_amount": 42.00}
]
```

Report identifiers and money precision must be stable so that grading is
deterministic.

## Reward and measurements

The main reward is the fraction of correct decisions in the batch. A `fix`
answer can receive partial credit when the decision is correct but the
corrected amount is wrong. The exact partial-credit weight must be set before
implementation.

Record these values for each step:

```text
turn, reward, env_actions, tokens, wall_sec, correct_decisions
```

The main learning curve is first-attempt decision accuracy over time. The
holdout tail must contain new reports, not copies of reports that already
received feedback.

## Evaluation conditions

Run the same report sequence in two conditions:

| Condition | Conversation | Files | Purpose |
|---|---|---|---|
| Baseline | Fresh at each step | Persist | Tests file-based memory only |
| Main | Resume across steps | Persist | Tests in-context learning plus files |

The report order, policy, feedback level, and timeout must match across both
conditions.

## Planned Harbor layout

```text
tasks/expense-desk/
├── README.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   └── expense_desk/           # Hidden policy engine and report bank
└── steps/
    └── batch-01 … batch-N/
        ├── instruction.md      # Stable review and output contract
        ├── workdir/setup.sh    # Publish reports and prior feedback
        └── tests/test.sh       # Score decisions and append feedback
```

Keep the hidden policy under `/opt`. Keep reports, notes, decisions, and released
feedback under `/app`.

## Design status

This is a post-release feedback task. The benchmark design document blocks its
implementation until the Domain 2 questions are settled: what counts as
learning, how the holdout proves generalization, and how much feedback the
agent can receive. Test feedback levels as separate conditions when the task is
implemented.
