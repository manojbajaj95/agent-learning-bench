# Corpus

Evaluate how an agent answers questions about one frozen company wiki
(EnterpriseRAG-Bench Confluence, 64 confluence-only questions).

The wiki dump and question bank are not in git. Download them, then generate
Harbor steps. Harbor cannot run a slice of one task: `--n` sets how many steps
`generate_steps.py` writes. The wiki stays the full Confluence slice either way.

Needs `OPENAI_API_KEY`. Use the OpenAI id `gpt-5.6-luna` (dot, not hyphen).

## Download

From the repo root:

```bash
./tasks/corpus/download.sh
```

This writes `tasks/corpus/data/questions.jsonl` and two Confluence zip files
(~5,189 pages). Do not commit that folder.

Then build steps (this also copies data into `environment/data/` for Docker):

```bash
python3 tasks/corpus/generate_steps.py --n 10   # smoke
python3 tasks/corpus/generate_steps.py --all    # all 64 confluence-only questions
```

`steps/` and `task.toml` are generated. They are gitignored.

Each step is scored by an LLM judge (`openai/gpt-5.6-luna`). The judge sees the
question, the agent answer, and a hidden gold answer. Paraphrase can still
score high. Token overlap is not used. The verifier also records `files_opened`
from the agent trajectory.

Oracle writes the gold text, so a passing oracle run shows the judge is wired.
A real agent is scored the same way. Judge traces are in `reward-details.json`
after a job.

The last ~10% of `--all` (questions 59–64) is a holdout tail. Same wiki, later
questions. A mapper should still find them; a notes file that only stores prior
answers should not.

## Baseline

Harbor `pi`. Fresh chat each question.

```bash
harbor run -p tasks/corpus -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5 \
  --job-name corpus-baseline
```

## In-context learning

Same `pi`, with `--resume-trajectory`. Prior questions stay in the model context.

```bash
harbor run -p tasks/corpus -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5 \
  --resume-trajectory \
  --job-name corpus-icl
```
