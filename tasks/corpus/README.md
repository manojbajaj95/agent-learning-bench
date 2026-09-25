# Corpus

The agent answers 64 questions about one frozen company wiki. Accuracy should stay high while the agent opens fewer wiki files.

## Task type

Non-verifiable. An LLM judge scores the answer after the step. That score does not return to the agent. The agent can read the wiki during the step.

## Environment

- Dump in `data/`: `questions.jsonl` and two Confluence zip files (about 5,189 pages)
- Source: EnterpriseRAG-Bench, confluence-only questions
- Network: `public`
- Agent timeout: 180 seconds per question
- Verifier timeout: 180 seconds. The judge needs `OPENAI_API_KEY`.
- Wiki path in the container: `/data/corpus`

`steps/` and `task.toml` are generated. They are gitignored. Patch gold in `questions.jsonl` (`gold_answer`). Patch wiki pages in the zip files. Then generate steps. A new trial starts a new container. Notes in `/app` persist across questions in one trial.

## Step design

One trial is 64 questions. One step is one question. Generate them from the repo root:

```bash
python3 tasks/corpus/generate_steps.py --n 10   # first 10 questions
python3 tasks/corpus/generate_steps.py --all    # all 64
```

Generation copies the dump into `environment/data/` for Docker. The wiki stays the full dump in both cases.

Questions 59–64 are the holdout. They use the same wiki and new questions. A notes file that only stores earlier answers should miss them. An agent that mapped the wiki should still find them.

The judge is `openai/gpt-5.6-luna`. It sees the question, the agent answer, and a hidden gold answer. A paraphrase can still score high. Token overlap is not the score. Oracle writes the gold text. Judge traces are in `reward-details.json`.

Replace the upstream dump with `./tasks/corpus/download.sh`. `alb prepare corpus` skips that download when `data/` already has files, then runs `generate_steps.py --all`.

## Learning goal

The learning object is the map of the frozen wiki. Accuracy should stay high on the holdout while `files_opened` falls. Baseline starts a fresh chat each question. In-context learning resumes the same chat.

## Reward and cost

Harbor averages the per-question reward (`multi_step_reward_strategy = "mean"`). The verifier writes `/logs/verifier/reward.json`:

| Field | Meaning |
|---|---|
| `reward` | Judge score for the answer |
| `correctness` | Same judge score |
| `files_opened` | Distinct `/data/corpus/...` paths in `pi.txt` or `trajectory.json` |
| `tool_calls` | Tool calls in the step trajectory |
| `tokens` | Prompt tokens plus completion tokens in that trajectory |

Harbor also records `cost_usd`, input tokens, output tokens, and step duration.

## Running

Needs `OPENAI_API_KEY`. The model id is `openai/gpt-5.6-luna`.

```bash
alb prepare corpus
alb run corpus --system baseline
alb run corpus --system icl
```
