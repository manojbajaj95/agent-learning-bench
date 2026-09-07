# Web exploration

Evaluate how an agent learns one frozen company intranet (Kestrel Depot, 30 jobs).

The site is fictional. A model cannot answer from training memory. Jobs mix
fact questions and form posts. Harbor cannot run a slice of one task: `--n`
sets how many steps `generate_steps.py` writes.

Needs `OPENAI_API_KEY`. Use the OpenAI id `gpt-5.6-luna` (dot, not hyphen).

## Build steps

From the repo root:

```bash
python3 tasks/web-exploration/generate_steps.py --n 10   # smoke
python3 tasks/web-exploration/generate_steps.py --all    # all 30
```

`steps/` and `task.toml` are generated. They are gitignored.

The agent browses with `web get <path>` and `web post <path> field=value ...`.
The CLI returns HTML. Gold facts and form checks stay under `/opt/web` (mode 600).

Each step is scored by a programmatic check. A question step matches the gold
string. A form step matches the posted fields and the confirmation code. The
verifier also records `pages_visited` and `tokens` from the agent trajectory.

Oracle writes the gold text for questions. For forms, Oracle posts the fields
and writes the confirmation code. A passing oracle run shows the verifier is
wired.

The last 3 jobs of `--all` (jobs 28-30) are a holdout tail. Same site, facts
that live only on News posts. A mapper should still find them. A notes file
that only stores prior answers should not.

## Environment

- Base image: `ubuntu:24.04` + `python3` + `sudo`
- Network: `public` (so agents can call the model API)
- Agent timeout: 180s per job (raise with `--agent-timeout-multiplier` for pi)
- Engine: [`environment/web/web.py`](environment/web/web.py)
- Site tree: [`environment/web/pages.py`](environment/web/pages.py) (hidden)
- `/app/sessions/`: empty at image build; filled by [pi-sessions](../../agents/pi_sessions/) on each turn shutdown

## Layout

```
tasks/web-exploration/
├── instruction.md
├── questions.json
├── generate_steps.py
├── environment/
│   ├── Dockerfile
│   └── web/
│       ├── web.py      # get/post/publish/costs
│       └── pages.py    # hidden page tree
├── tests/
│   ├── test.sh
│   ├── reward.toml
│   └── correctness/check.py
└── steps/              # generated
```

## Baseline

Harbor `pi`. Fresh chat each job.

```bash
harbor run -p tasks/web-exploration -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5 \
  --job-name web-baseline
```

## In-context learning

Same `pi`, with `--resume-trajectory`. Prior jobs stay in the model context.

```bash
harbor run -p tasks/web-exploration -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5 \
  --resume-trajectory \
  --job-name web-icl
```
