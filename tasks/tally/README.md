# Tally

The agent bets a color on each card in one shuffled deck. Later bets should get better as the agent tracks how many cards of each color remain.

## Task type

Verifiable. Each turn settles after the agent writes a bet. The next turn shows the revealed card in `/app/view.txt`. The agent cannot change the bet after that reveal.

## Environment

- Image: `ubuntu:24.04` with `python3`
- Network: `public`
- Agent timeout: 60 seconds per turn. Raise it with `--agent-timeout-multiplier`.
- Hidden deck: `/opt/tally/deck.txt`
- Public view: `/app/view.txt` (turn number and the last card only)
- Engine: [`environment/tally/game.py`](environment/tally/game.py)

Files in `/app` persist across the twelve turns. A new trial starts a new container and a new shuffle.

## Step design

One trial is twelve turns, `turn-1` through `turn-12`. One turn is one card. The deck has 4 red, 4 blue, and 4 yellow cards. It is shuffled once at the start.

Each turn the agent writes `{ "color": "red"|"blue"|"yellow" }` to `/app/bet.json`. The instructions are in [`steps/turn-1/instruction.md`](steps/turn-1/instruction.md). The same contract applies on every turn.

There is no separate holdout. The deck is small, and the last turns are the transfer check: a count of the remaining cards should beat a guess.

## Learning goal

The learning object is the count of remaining cards. Match rate should rise across the twelve turns. A fresh chat on every turn can still learn if it writes the counts to `/app`. In-context learning keeps the same chat across turns.

Compare baseline and in-context learning on the same deck order.

## Reward and cost

Each turn scores 1 for a color match and 0 for a miss. Harbor averages the twelve scores (`multi_step_reward_strategy = "mean"`). The points sum is that mean times 12.

`steps/*/tests/test.sh` reveals the card and writes `/logs/verifier/reward.txt` plus `reward.json` with `reward`, `tool_calls`, and `tokens`.

Harbor records these costs on the job:

| Metric | Source |
|---|---|
| `cost_usd` | Harbor agent result |
| `n_input_tokens`, `n_output_tokens` | Harbor agent result |
| `duration_sec` | Harbor step timing |

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
        ├── workdir/setup.sh
        └── tests/test.sh
```

## Running

Needs `OPENAI_API_KEY`. The model id is `openai/gpt-5.6-luna`.

```bash
alb run tally --system baseline
alb run tally --system icl
```

## Reporting

```bash
alb report tally-baseline
```

Writes `reports/latest.md`, `reports/latest.html`, and SVG charts for reward, cost, and tokens.
