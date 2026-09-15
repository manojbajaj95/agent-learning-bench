# Database analytics

Evaluate how an agent queries a Formula 1 SQLite database (BIRD-SQL `formula_1`, 174 questions). Gold SQL and answer formats are patched in this repo.

The dataset is in `environment/data/`: `formula_1.sqlite`, `questions.json`, and `gold.json`. Harbor steps and `task.toml` are in git. `alb smoke` keeps the first 10 steps.

Each `question.md` has an **Answer format** line. The verifier strips whitespace and compares `answer.json` to the gold SQL result.

Needs `OPENAI_API_KEY`. Use the OpenAI id `gpt-5.6-luna` (dot, not hyphen).

## Baseline

Harbor `pi`. Fresh chat each question.

```bash
harbor run -p tasks/database-analytics -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5 \
  --job-name f1-baseline
```

## In-context learning

Same `pi`, with `--resume-trajectory`. Prior questions stay in the model context.

```bash
harbor run -p tasks/database-analytics -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5 \
  --resume-trajectory \
  --job-name f1-icl
```
