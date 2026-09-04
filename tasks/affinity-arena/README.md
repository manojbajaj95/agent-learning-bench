# Affinity Arena

Affinity Arena is a proposed verifiable Harbor multi-step task. It is currently
a design, not a runnable task.

The agent plays a sequence of deterministic 3-on-3 creature battles. Every
creature and move has one of six affinities, and attack damage depends on a
hidden affinity chart. The agent must infer that chart from observed damage,
retain what it learns across battles, and use it to draft teams and choose
actions.

## Learning objective

The learning object is a fixed 6 x 6 table:

```text
multiplier[attack affinity][defender affinity] = 0.5, 1, or 2
```

Each row and column contains two of each multiplier, so every affinity has
strengths and counters. An attack reveals one cell through its damage value.
The chart is generated from the trial seed and remains fixed for the entire
trial.

## Trial structure

- A trial contains 20 battles against the same hidden chart.
- Battles 1-15 use a main roster of 12 creatures, with every affinity
  represented twice.
- Battles 16-20 use a holdout roster with new creature names and movesets.
- Each battle offers the agent five creatures; it drafts three in order.
- The opponent team, offered pool, and chart are deterministic for a given
  seed and shared across evaluation conditions.
- A win, loss, or tick limit ends the battle. Only the first attempt counts.

The holdout roster tests whether the agent learned affinity relationships
rather than memorizing creature matchups.

## Battle rules

- Agent creatures have 100 HP; opponent creatures have 140 HP.
- Each creature has one affinity and three moves.
- Its same-affinity move has power 50; its other moves have power 36.
- Damage is `floor(power x multiplier)`.
- On each tick, the agent attacks or switches, then the opponent attacks.
- Switching consumes the agent's action, and the incoming creature takes the
  opponent's attack.
- When a creature falls, the next creature in draft order enters and the tick
  ends.
- The opponent never switches voluntarily. It selects the move that deals the
  most damage under the true chart, breaking ties by listed move order.

The agent can see rosters, affinities, move powers, HP, actions, and damage. It
cannot see multipliers, effectiveness labels, the chart, or the oracle.

## Agent interface

```text
affinity-arena status
affinity-arena draft <creature> <creature> <creature>
affinity-arena attack <move>
affinity-arena switch <creature>
```

`status` does not advance the battle. `draft` is accepted once, before the
first tick. `attack` and `switch` each advance one tick.

Every step gives the agent the same instructions:

1. Read `/app/world/RULES.md` and `/app/view.txt`.
2. Read persistent notes and prior session logs when available.
3. Draft a team and play until the battle ends.
4. Record useful observations in `/app/notes.md` and the inferred chart in
   `/app/affinity-chart.json`.
5. Stop without restarting the battle.

The chart file contains only observed cells and is used for diagnostics, not
as part of the reward.

## Evaluation

The primary reward measures the remaining HP margin:

```text
reward = clamp(
  0.5 + 0.5 x (agent HP remaining / 300 - opponent HP remaining / 420),
  0,
  1
)
```

Each battle also records:

| Metric | Meaning |
|---|---|
| `won` | Whether the opponent's full team was defeated |
| `ticks` | Number of ticks played |
| `oracle_ticks` | Ticks required by an optimal policy with the best draft |
| `opt_rate` | Fraction of draft and battle decisions in the oracle's optimal set |
| `regret` | Oracle reward minus agent reward for the matchup |
| `draft_ok` | Whether the draft can achieve the oracle's best value |
| `cells_seen` | Fraction of chart cells revealed during the trial |
| `belief_acc` | Correct chart entries divided by all 36 cells |
| `belief_cov` | Recorded chart entries divided by all 36 cells |
| `env_actions` | Draft and tick commands issued |

The expected learning signal is increasing reward, win rate, optimal-action
rate, draft quality, and belief accuracy, with decreasing regret and excess
ticks. `belief_acc` should rise with `cells_seen`, and performance should carry
over to the holdout roster.

## Evaluation conditions

All conditions use the same model, chart, and battle schedule:

| Condition | Conversation state | Persistent files |
|---|---|---|
| Baseline | Fresh conversation per battle | Yes |
| Pi sessions | Fresh conversation with prior session logs | Yes |
| In-context | Resumed trajectory | Yes |

An oracle run must win all 20 battles before the task is considered valid.

## Isolation and controls

The chart, schedule, battle state, and oracle live in a root-only directory.
The agent interacts through a restricted CLI and receives only the public
view and tick log.

The task uses these controls:

- deterministic battles and a seeded schedule;
- the same schedule across evaluation conditions;
- first-attempt scoring with no in-battle reset;
- a single irreversible draft;
- a holdout roster;
- no effectiveness labels or grader feedback during play; and
- hidden state that is unreadable by the agent.

