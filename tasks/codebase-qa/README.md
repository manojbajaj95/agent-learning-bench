# Codebase Q&A

Evaluate how an agent answers questions about one frozen Python repository (SWE-QA Flask, 48 questions).

The Flask snapshot and question bank are not in git. Download them, then generate Harbor steps. Harbor cannot run a slice of one task: `--n` sets how many steps `generate_steps.py` writes.

Needs `OPENAI_API_KEY`. Use the OpenAI id `gpt-5.6-luna` (dot, not hyphen).

## Download

From the repo root:

```bash
./tasks/codebase-qa/download.sh
```

This writes `tasks/codebase-qa/data/flask.jsonl` and `tasks/codebase-qa/data/repo/` (Flask at `85c5d93`). Do not commit that folder.

Then build steps (this also copies data into `environment/data/` for Docker):

```bash
python3 tasks/codebase-qa/generate_steps.py --n 10   # smoke
python3 tasks/codebase-qa/generate_steps.py --all    # all 48
```

`steps/` and `task.toml` are generated. They are gitignored.

Each step is scored by an LLM judge (`openai/gpt-5.6-luna`). The judge sees the question, the agent answer, and a hidden gold answer from SWE-QA. Paraphrase can still score high. Token overlap is not used.

Oracle writes the gold text, so a passing oracle run shows the judge is wired. A real agent is scored the same way. Judge traces are in `reward-details.json` after a job.

## Baseline

Harbor `pi`. Fresh chat each question.

```bash
harbor run -p tasks/codebase-qa -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5 \
  --job-name flask-baseline
```

## In-context learning

Same `pi`, with `--resume-trajectory`. Prior questions stay in the model context.

```bash
harbor run -p tasks/codebase-qa -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5 \
  --resume-trajectory \
  --job-name flask-icl
```
