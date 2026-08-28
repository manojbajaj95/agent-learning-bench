# Database analytics

Evaluate how an agent queries a Formula 1 SQLite database (BIRD-SQL `formula_1`, 174 questions).

The SQLite file and question bank are not in git. Download them, then generate Harbor steps. Harbor cannot run a slice of one task: `--n` sets how many steps `generate_steps.py` writes.

Needs `OPENAI_API_KEY`. Use the OpenAI id `gpt-5.6-luna` (dot, not hyphen).

## Download

From the repo root:

```bash
./tasks/database-analytics/download.sh
```

This writes `tasks/database-analytics/data/formula_1.sqlite` and `dev_20251106.json`. The Mini-Dev zip is large. Do not commit that folder.

Then build steps (this also copies data into `environment/data/` for Docker):

```bash
python3 tasks/database-analytics/generate_steps.py --n 10   # smoke
python3 tasks/database-analytics/generate_steps.py --n 40   # medium
python3 tasks/database-analytics/generate_steps.py --all    # all 174
```

`steps/` and `task.toml` are generated. They are gitignored.

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
