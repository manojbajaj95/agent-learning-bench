# Poker

Harbor multi-step task: heads-up no-limit Texas Hold'em against a sticky opponent.

Each step is one hand. Stacks persist. The trial score is your chip total after
the last hand (`multi_step_reward_strategy = "final"`). Blinds are 5 / 10.
Both players start with 1000 chips.

The opponent uses fixed action incentives: extra weight on call, a penalty on
check. That yields over-calling and frequent donk bets. The agent must learn
that leak across hands. Baseline is a fresh chat each hand, so the prompt
shows the current hand only.

See [`instruction.md`](instruction.md) for the agent prompt.

## Rules

- Heads-up no-limit Hold'em
- Blinds 5 / 10, start 1000 chips each
- Button rotates; button posts the small blind
- `poker act raise 30` means raise **to** 30
- Match ends after 100 hands or when a player has 0 chips
- Cards are shuffled per hand from the trial seed

## Agent interface

```text
poker status
poker act fold
poker act check
poker act call
poker act raise <to>
```

`status` does not advance the hand. Hidden engine state is under `/opt/poker`.

## Environment

- Base image: `ubuntu:24.04` + `python3`
- Agent user `agent`; CLI goes through sudo to `/usr/local/libexec/poker-public`
- Network: `public`
- Agent timeout: 180s per hand

## Layout

```
tasks/poker/
├── task.toml
├── instruction.md
├── generate_steps.py
├── environment/
│   ├── Dockerfile
│   ├── RULES.md
│   ├── poker / public.py / admin.py
│   └── poker_game/          # engine, fish, oracle, runtime
└── steps/hand-001 … hand-100
```

Regenerate committed steps after an engine change:

```bash
python3 tasks/poker/generate_steps.py
python3 tasks/poker/generate_steps.py --check
```

## Running

```bash
uv run --no-project --with pytest pytest tasks/poker/checks -q
python3 tasks/poker/generate_steps.py --check
harbor run -p tasks/poker -a oracle
harbor run -p tasks/poker -a pi -m openai/gpt-5.6-luna --agent-timeout-multiplier 5
```

Local one-hand probe (no Docker):

```bash
python3 tasks/poker/play.py
```
