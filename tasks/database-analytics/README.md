# Database analytics

The agent answers 174 questions about one Formula 1 SQLite database. Accuracy should stay high while the number of SQL queries falls.

## Task type

Non-verifiable. The verifier compares `/app/answer.json` with the gold result after the step. That verdict does not return to the agent. The agent can run SQL and read the schema during the step.

## Environment

- Dataset in `environment/data/`: `formula_1.sqlite`, `questions.json`, and `gold.json`
- Gold SQL and answer formats are patched in this repo
- Network: `public`
- Agent timeout: 180 seconds per question
- Verifier timeout: 60 seconds
- Harbor steps and `task.toml` are in git

The database does not change between questions. Files in `/app` persist across the trial. A new trial starts a new container.

## Step design

One trial is 174 questions, `q-001` through `q-174`. One step is one question. Each question file has a required output block for `/app/answer.json`. The verifier strips whitespace and compares that file with the gold SQL result. `alb smoke` keeps the first 10 steps.

This task has no holdout tail. Later questions still use the same schema, so a falling query count on late questions is the transfer check.

## Learning goal

The learning object is the Formula 1 schema and the query patterns that match it. The expected curve is a flat or rising accuracy with fewer `db_queries` per question. Baseline starts a fresh chat each question. In-context learning resumes the same chat. Compare the two on the same question order.

## Reward and cost

Each question scores 1 when the answer matches and 0 when it does not. Harbor averages those scores (`multi_step_reward_strategy = "mean"`).

The verifier writes `/logs/verifier/reward.json`:

| Field | Meaning |
|---|---|
| `reward` | 1 or 0 for the answer file |
| `correctness` | Same match bit |
| `db_queries` | SQL queries issued on this step |
| `tool_calls` | Tool calls in the step trajectory |
| `tokens` | Prompt tokens plus completion tokens in that trajectory |

Harbor also records `cost_usd`, input tokens, output tokens, and step duration. Input tokens rise across an in-context run because the chat grows. Report that curve next to `db_queries`.

## Running

Needs `OPENAI_API_KEY`. The model id is `openai/gpt-5.6-luna`.

```bash
alb run database-analytics --system baseline
alb run database-analytics --system icl
```
