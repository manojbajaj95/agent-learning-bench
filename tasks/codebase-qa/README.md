# Codebase Q&A

Evaluate how an agent answers questions about one frozen Python repository (SWE-QA Flask, 48 questions). Gold for q-030 is patched in this repo: `accessed` does not gate cookie `dumps`.

The dataset is in `environment/data/`: `questions.json`, `gold.json`, and `repo/` (Flask at `85c5d93`). Harbor steps and `task.toml` are in git. `alb smoke` keeps the first 10 steps.

Each step is scored by an LLM judge (`openai/gpt-5.6-luna`). The judge sees the question, the agent answer, and a hidden gold answer. Paraphrase can still score high. Token overlap is not used.

Needs `OPENAI_API_KEY`. Use the OpenAI id `gpt-5.6-luna` (dot, not hyphen).

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
