# Agent Learning Bench

> We define AGI as a system that can match the learning efficiency of humans.
>
> [ARC Prize](https://arcprize.org/)

## Why build this benchmark?

AI systems can score well on hard evaluations and still fail at simple, repeated work. They fix one bug and restore an earlier bug. They solve a familiar problem after a lot of training, then struggle to pick up a nearby skill from a few examples.

This benchmark asks:

> Can an agent learn a stable environment and become more accurate, faster, or more efficient over repeated jobs?

ARC-AGI-3 is the closest active benchmark for that question, but it cannot cover every form of learning. Agent Learning Bench adds longer and more varied environments. It also tries to reduce three common problems:

1. Short tasks can reward a simple append-only log instead of a reusable model of the environment.
2. Similar environments do not show whether a learning method works across domains.
3. Once researchers train against a fixed benchmark, high scores can reflect benchmark-specific tuning.

The measurement is learning efficiency.

## What we need to test

A learning agent should improve on these axes:

- Sample efficiency: how much experience it needs before performance improves
- Continual learning: whether knowledge from earlier jobs helps on later jobs
- Generalization: whether it applies learned structure to items that did not receive feedback
- Robustness: whether it keeps useful knowledge when the job changes within the same environment
- Exploration cost: whether it can keep quality while using fewer actions, probes, file reads, or tokens

A final score cannot answer these questions. Each task must report a curve across steps. Depending on the task, first-attempt accuracy should rise, exploration cost should fall, or actions to completion should move toward the optimum.

## Task design

One trial contains one fixed environment and many ordered Harbor steps. Each step is one job, fight, question, or episode. The environment and workspace persist across steps in a trial. A new trial starts a new container. Task authors should keep durable agent notes in `/app` and hidden engine state under `/opt`.

## Learning systems

The bench compares three systems. The task, model, and step order stay the same. Harbor's built-in [pi](https://pi.dev/) agent is the baseline harness. The other two systems add one thing on top of that same agent.

The container filesystem persists in every system (for example `/app/view.txt`).

### Baseline

Harbor's built-in `pi`. Each turn is a fresh chat with no session files, so turn 1 and turn 2 are independent.

```bash
harbor run -p tasks/tally -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5
```

### Pi sessions

The same `pi` agent, with a copy of each session. [pi-sessions](agents/pi_sessions/) writes each turn's JSONL to `/app/sessions/`. Later turns can read those files.

```bash
PYTHONPATH=. harbor run -p tasks/tally \
  -a agents.pi_sessions:PiSessionsAgent \
  -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5
```

### In-context learning

The same `pi` agent as baseline. `--resume-trajectory` continues the chat across turns. Harbor sets this on agents that declare `SUPPORTS_RESUME` (pi does). Earlier turns stay in the model context.

```bash
harbor run -p tasks/tally -a pi -m openai/gpt-5.6-luna \
  --resume-trajectory \
  --agent-timeout-multiplier 5
```

## Feedback domains

Tasks are verifiable or non-verifiable, depending on whether the agent can check its work before the step ends.

### Verifiable

During the step, the agent can tell whether an answer or action is correct and change it before that step's agent loop ends. A wall can block a move, or an opponent can respond to an attack. A reviewer can accept or reject a report, and a grader can score a candidate answer.

If the environment has a grader, cap or penalize calls so that brute-force search does not replace learning.

Examples: Tally, Poker, Affinity Arena, Report check, and Courier / Picker.

### Non-verifiable

The agent does not get feedback on its work. The verifier can grade after the step, but that verdict never returns to the agent. The agent can only inspect the stable structure of the environment, such as a wiki, a codebase, a schema, or a website.

These tasks measure whether quality stays high while file opens, probes, navigation steps, or tokens fall.

Examples: Corpus, Codebase Q&A, Database analytics, and Web exploration.

## Evidence of learning

Every step should record at least:

```text
turn, reward, env_actions, tokens, wall_sec, extra_metric
```

The extra metric must describe the learning object. It can be files opened, wrong probes, route length, damage taken, or actions to a win.

Each task also needs these controls:

| Control | What it prevents |
|---|---|
| First-attempt scoring | Repeated grading until the answer passes |
| Holdout tail | Copying corrected answers |
| Cost curve | Brute-force exploration hidden by a correct final answer |
| Fixed environment per trial | Changes in the world being mistaken for learning |
| Fresh baseline condition | Session files or resumed chat being mistaken for no learning |

Give the task one learning object and enough steps that a curve can show a trend. Include a holdout that tests transfer. Do not install the solution, reveal hidden state, or treat a final aggregate score as the only result.

## Tasks

All tasks are runnable except Courier / Picker, which is a design only.

| Task | Domain | Learning object |
|---|---|---|
| [Tally](tasks/tally/) | Verifiable | Card counts across twelve turns |
| [Poker](tasks/poker/) | Verifiable | A sticky heads-up opponent across 100 hands |
| [Affinity Arena](tasks/affinity-arena/) | Verifiable | A hidden affinity chart across twenty battles |
| [Report check](tasks/report-check/) | Verifiable | An unpublished house style guide, learned from review comments |
| [Courier / Picker](tasks/courier-picker/) | Verifiable | A fixed spatial map (design only) |
| [Corpus](tasks/corpus/) | Non-verifiable | A frozen Confluence wiki map |
| [Codebase Q&A](tasks/codebase-qa/) | Non-verifiable | Flask hierarchy and call patterns |
| [Database analytics](tasks/database-analytics/) | Non-verifiable | Formula 1 schema and query patterns |
| [Web exploration](tasks/web-exploration/) | Non-verifiable | WebArena-Verified Shopping structure and navigation across 187 tasks with `agent-browser` |

## Contributing a task

Build tasks in [Harbor](https://www.harborframework.com/docs) format and submit them through this repository. A task proposal should state:

- whether it is verifiable or non-verifiable;
- the stable object that the agent must learn;
- the expected learning curve;
- the per-step reward and cost metric;
- the baseline, pi-sessions, and in-context run commands; and
- the holdout or other control that rules out shortcuts.

## References

- [ARC Prize](https://arcprize.org/)
- [Harbor documentation](https://www.harborframework.com/docs)
