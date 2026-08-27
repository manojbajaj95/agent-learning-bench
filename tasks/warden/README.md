# Warden

Warden is a proposed Harbor multi-step task for opponent modeling. It is a
Domain 1 task: the environment gives immediate and verifiable feedback after
each action.

The task follows the design in [`docs/task-ideas.md`](../../docs/task-ideas.md#1-warden--opponent-modeling-domain-1).
This directory contains the design only. It is not yet a runnable Harbor task.

## Goal

The agent fights the same deterministic boss in a sequence of Harbor steps. One
step is one fight. The agent must learn the boss behavior from live combat
results and use that knowledge in later fights.

The boss uses a seeded state machine with these stable behaviors:

- a fixed opening;
- a heavy attack that is telegraphed one action before it lands;
- a sweep with a recovery window that the agent can punish; and
- a response that punishes repeated player moves.

The first fights should include exploration and deaths. Later fights should
show more wins and shorter paths to a win.

## Agent interface

The environment provides one command:

```text
warden attack
warden block
warden dodge left
warden dodge right
warden parry
warden potion
```

Each command returns the visible result of the player action and the boss
response. Death ends the current step. The boss implementation and internal
state stay outside the agent workspace under `/opt/warden`.

The agent can keep durable observations in `/app/notes.md`. This is important
for baseline runs that use a fresh conversation at each step.

## Episode and feedback

A setup hook resets the fight before each step. The boss policy stays the same
for the full trial. The agent receives two forms of feedback:

1. live combat responses after each command; and
2. a fight summary after the step.

This immediate action-to-reaction loop makes the task verifiable inside the
step. The agent does not need access to the Harbor verifier to learn.

## Reward

Each fight receives a float reward:

```text
0.7 × boss HP removed fraction + 0.3 × win
```

A loss can therefore show useful progress. A win always receives the full win
bonus. Harbor should use the mean step reward as the trial reward, while the
report keeps each step value for learning curves.

## Measurements

Record these values for each fight:

```text
turn, reward, env_actions, tokens, wall_sec, boss_hp_removed, won
```

The main learning curves are:

- death rate down;
- win rate up; and
- actions to kill down.

Accuracy alone is not enough. A brute-force agent can improve damage while
using more actions. The action curve shows whether the agent learns a more
efficient policy.

## Evaluation conditions

Run the same task in two conditions:

| Condition | Conversation | Files | Purpose |
|---|---|---|---|
| Baseline | Fresh at each step | Persist | Tests file-based memory only |
| Main | Resume across steps | Persist | Tests in-context learning plus files |

The boss seed, policy, and fight order must match across the two conditions.
The task must score the first fight attempt in each step. It must not permit a
fight reset inside the step.

## Planned Harbor layout

```text
tasks/warden/
├── README.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   └── warden/                 # CLI and deterministic boss engine
└── steps/
    └── fight-01 … fight-N/
        ├── instruction.md      # Same short combat goal for each fight
        ├── workdir/setup.sh    # Reset fight and write the visible status
        └── tests/test.sh       # Settle fight and write float reward
```

The step directories can be generated because their structure is identical.
The engine belongs in `/opt/warden`; agent notes and visible fight output belong
in `/app`.

## Extension path

Add complexity only after the first design gives a clear learning curve. The
first extension can add a second boss phase below 50% health. Later versions can
add another move set or a second boss that shares some behavior with the first.
These versions can test transfer without changing the core interface.
