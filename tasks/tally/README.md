# Tally

Harbor multi-step task: a short color-betting card game.

Each turn is scored on its own (0 or 1). The trial score is the **sum** of twelve turns
(one bet per card). A new deck is shuffled when the environment starts.

See [`instruction.md`](steps/turn-1/instruction.md) for what the agent reads each turn.
Past session logs (when using the [pi-sessions](../../agents/pi_sessions/) agent)
are under `/app/sessions/`.

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
- Network: `public` (so agents can call the model API)
- Agent timeout: 60s per turn (raise with `--agent-timeout-multiplier` for pi)
- Engine: [`environment/tally/game.py`](environment/tally/game.py) (`shuffle` | `view` | `score`)
- `/app/sessions/`: empty at image build; filled by [pi-sessions](../../agents/pi_sessions/) on each turn shutdown

`steps/*/tests/test.sh` is a settle hook only (not a pytest/Reward Kit suite). It reveals
the card and writes `/logs/verifier/reward.txt`.

## Layout

```
tasks/tally/
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

Same model. Baseline is Harbor `pi`. Pi sessions adds session copy. In-context adds `--resume-trajectory`.
Needs `OPENAI_API_KEY`. Use the OpenAI id `gpt-5.6-luna` (dot, not hyphen).

### Baseline

Harbor `pi`. Fresh chat. No session files.

```bash
harbor run -p tasks/tally -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5
```

### Pi sessions

Same `pi`, plus session JSONL copied to `/app/sessions/`.

```bash
PYTHONPATH=. harbor run -p tasks/tally \
  -a agents.pi_sessions:PiSessionsAgent \
  -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5
```

### In-context learning

Same `pi` as baseline, with `--resume-trajectory`.

```bash
harbor run -p tasks/tally -a pi -m openai/gpt-5.6-luna \
  --resume-trajectory \
  --agent-timeout-multiplier 5
```

Pi often needs a higher agent timeout than terminus-2. Use `--agent-timeout-multiplier` if turns time out.

## Reporting

```bash
python3 tools/report_runs.py --jobs-dir jobs --task tally --out-dir reports
```

Writes `reports/latest.json` and `reports/latest.md` with points sum, mean reward, cost,
duration, and tokens.

## Note on learning

Harbor keeps the container filesystem across steps in a trial. Across trials the
container is new (new shuffle, empty `/app/sessions/`).

- **Baseline:** Harbor `pi`; fresh chat; `/app/sessions/` stays empty.
- **Pi sessions:** same `pi`, plus session JSONL copied into `/app/sessions/` on shutdown.
- **In-context:** Harbor `pi` with `--resume-trajectory`; same chat across turns.
