# Tally (sample multi-step task)

Harbor multi-step sample: a short color-betting card game.

Each turn is scored on its own (0 or 1). The trial score is the **sum** of twelve turns
(one bet per card). A new deck is shuffled when the environment starts. The prompt does
not mention memory.

See [`instruction.md`](steps/turn-1/instruction.md) for what the agent reads each turn.

## Rules

- Deck: 12 cards — 4 red, 4 blue, 4 yellow
- Shuffle once at environment start (`/opt/tally/deck.txt`, not in `/app`)
- 12 turns: write `{ "color": "red"|"blue"|"yellow" }` to `/app/bet.json` each turn
- Settle after the agent acts: reveal the next card; match → 1, miss → 0
- View (`/app/view.txt`): turn number + last card only (no discard list)

Harbor uses `multi_step_reward_strategy = "mean"`. With twelve 0/1 turns and no early abort,
mean reward equals points sum / 12.

## Environment

- Base image: `ubuntu:24.04` + `python3`
- Network: `public` (so terminus-2 can call the model API)
- Agent timeout: 60s per turn
- Engine: [`environment/tally/game.py`](environment/tally/game.py) (`shuffle` | `view` | `score`)

`steps/*/tests/test.sh` is a settle hook only (not a pytest/Reward Kit suite). It reveals
the card and writes `/logs/verifier/reward.txt`.

## Layout

```
tasks/sample/
├── task.toml
├── environment/
│   ├── Dockerfile
│   └── tally/
│       ├── RULES.md
│       └── game.py
└── steps/
    └── turn-1 … turn-12/
        ├── instruction.md
        ├── workdir/setup.sh   # shuffle if needed, write view.txt, remove self
        └── tests/test.sh      # score bet → reward 0|1
```

## Running

```bash
harbor run -p tasks/sample -a terminus-2 -m openai/gpt-5.6-luna
```

Needs `OPENAI_API_KEY`. Use the OpenAI id `gpt-5.6-luna` (dot, not hyphen).
Do not pass `--resume-trajectory` if you want a fresh chat each turn.

## Reporting

```bash
python3 tools/report_runs.py --jobs-dir jobs --task tally --out-dir reports
```

Writes `reports/latest.json` and `reports/latest.md` with points sum, mean reward, cost,
duration, and tokens.

## Note on learning

Harbor keeps the container filesystem across steps in a trial, but starts a new agent
conversation each step by default. Across trials the container is new (new shuffle).
Across-run learning needs a harness with its own memory; this task measures what an
agent does with a frozen rule set and sparse reveals inside one trial.
