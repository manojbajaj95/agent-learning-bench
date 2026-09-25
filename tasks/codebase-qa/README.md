# Codebase Q&A

The agent answers 48 questions about one frozen Flask repository. Quality should stay high while the agent opens fewer files on later questions.

## Task type

Non-verifiable. The judge scores the answer after the step. That score does not return to the agent. The agent can read the repository during the step.

## Labels

`fixed`, `unordered`. The repository stays the same on every run. A question does not depend on the questions before it.

## Environment

- Dataset in `environment/data/`: `questions.json`, `gold.json`, and `repo/` (Flask at `85c5d93`)
- Gold for q-030 is patched here: `accessed` does not gate cookie `dumps`
- Network: `public`
- Agent timeout: 180 seconds per question
- Verifier timeout: 180 seconds. The judge needs `OPENAI_API_KEY`.
- Harbor steps and `task.toml` are in git

The repository does not change between questions. Notes in `/app` persist across the trial. A new trial starts a new container.

## Step design

One trial is 48 questions, `q-001` through `q-048`. One step is one question. The agent writes the answer for that question. `alb smoke` keeps the first 10 steps.

The judge is `openai/gpt-5.6-luna`. It sees the question, the agent answer, and a hidden gold answer. A paraphrase can still score high. Token overlap is not the score.

This task has no holdout tail yet. Oracle writes the gold text. A passing oracle run shows that the judge is wired. Judge traces are in `reward-details.json`.

## Learning goal

The learning object is the Flask layout and its call patterns. Accuracy should stay high while tool calls and tokens fall. Baseline starts a fresh chat each question. In-context learning resumes the same chat. Compare the two on the same question order.

## Reward and cost

Harbor averages the per-question reward (`multi_step_reward_strategy = "mean"`). The verifier writes `/logs/verifier/reward.json`:

| Field | Meaning |
|---|---|
| `reward` | Judge score for the answer |
| `correctness` | Same judge score |
| `tool_calls` | Tool calls in the step trajectory |
| `tokens` | Prompt tokens plus completion tokens in that trajectory |
| `files_opened` | Distinct `/data/repo/...` paths in the agent log |

Harbor also records `cost_usd`, input tokens, output tokens, and step duration.

## Running

Needs `OPENAI_API_KEY`. The model id is `openai/gpt-5.6-luna`.

```bash
alb run codebase-qa --system baseline
alb run codebase-qa --system icl
```
