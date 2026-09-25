# Poker

The agent plays heads-up no-limit Texas Hold'em against one sticky opponent. The opponent over-calls and donk-bets. The agent should exploit that leak across hands.

## Task type

Verifiable. During a hand the agent sees the opponent's actions and can change its next action before the hand ends.

## Environment

- Image: `ubuntu:24.04` with `python3`
- Network: `public`
- Agent user: `agent`. The CLI uses sudo to reach `/usr/local/libexec/poker-public`.
- Agent timeout: 180 seconds per hand
- Hidden state: `/opt/poker`
- Public status: `poker status`

Stacks persist across hands in one trial. A new trial starts a new container. See [`instruction.md`](instruction.md).

## Step design

One trial is 100 hands, `hand-001` through `hand-100`. One step is one hand. Blinds are 5 and 10. Both players start with 1000 chips. The button rotates. The match ends after 100 hands or when a player has 0 chips.

```text
poker status
poker act fold
poker act check
poker act call
poker act raise <to>
```

`poker act raise 30` means raise to 30. `status` does not advance the hand. Cards are shuffled each hand from the trial seed.

There is no holdout roster. Later hands are the transfer check: the same opponent leak applies to new cards.

## Learning goal

The learning object is the opponent's fixed leak: extra weight on call, and a penalty on check. Chip stack should rise as the agent stops paying off that pattern. Baseline starts a fresh chat each hand. In-context learning resumes the same chat. Files in `/app` persist in both conditions.

## Reward and cost

The trial score is the agent's chip total after the last hand (`multi_step_reward_strategy = "final"`). Each hand also writes `/logs/verifier/reward.txt` with that chip count, and `/logs/verifier/reward.json` with:

| Field | Meaning |
|---|---|
| `chips` | Agent stack after the hand |
| `profit` | `chips` minus 1000 |
| `hands_done` | Hands finished |
| `completed` | 1 when the hand settled |

Harbor records `cost_usd`, input tokens, output tokens, and step duration. The task does not yet write an action count into the reward file.

## Layout

```
tasks/poker/
├── task.toml
├── instruction.md
├── generate_steps.py
├── environment/
└── steps/hand-001 … hand-100
```

Regenerate steps after an engine change:

```bash
python3 tasks/poker/generate_steps.py
python3 tasks/poker/generate_steps.py --check
```

## Running

```bash
uv run --no-project --with pytest pytest tasks/poker/checks -q
python3 tasks/poker/generate_steps.py --check
alb run poker --system baseline
alb run poker --system icl
```

`harbor run -p tasks/poker -a oracle` checks that the hidden solution settles. Local probe, no Docker:

```bash
python3 tasks/poker/play.py
```
