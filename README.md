# Agent Learning Bench

> We define AGI as a system that can match the learning efficiency of humans.
>
> [ARC Prize](https://arcprize.org/)

## Why build this benchmark?

AI systems can score well on hard evaluations and still fail in simple, repeated work. They fix one bug and restore an earlier bug. They solve a familiar problem after extensive training but struggle to learn a nearby skill from a few examples.

This benchmark tests that claim directly:

> Can an agent learn a stable environment and become more accurate, faster, or more efficient over repeated jobs?

ARC-AGI-3 is the closest active benchmark for this question, but one benchmark cannot cover every form of learning. Agent Learning Bench adds longer and more varied environments. It also tries to reduce three common problems:

1. Short tasks can reward a simple append-only log instead of a reusable model of the environment.
2. Similar environments do not show whether a learning method works across domains.
3. Once researchers train against a fixed benchmark, high scores can reflect benchmark-specific tuning.

The aim is not another static capability test. The aim is to measure learning efficiency.

## What we need to test

A learning agent should improve on several axes:

- **Sample efficiency:** How much experience does it need before performance improves?
- **Continual learning:** Does knowledge from earlier jobs help on later jobs?
- **Generalization:** Does it apply learned structure to items that did not receive feedback?
- **Robustness:** Does it keep useful knowledge when the job changes within the same environment?
- **Exploration cost:** Can it maintain quality while using fewer actions, probes, file reads, or tokens?

A final score cannot answer these questions. Each task must report a curve across steps. Depending on the task, first-attempt accuracy should rise, exploration cost should fall, or actions to completion should move toward the optimum.

## Task design

One trial contains one fixed environment and many ordered Harbor steps. Each step is one job, fight, question, or episode. The environment and workspace persist across steps in a trial. A new trial starts a new container. Task authors should keep durable agent notes in `/app` and hidden engine state under `/opt`.

## Learning systems

The bench compares three systems. The task, model, and step order stay the same.
Harbor’s built-in [pi](https://pi.dev/) agent is the baseline harness. The other two systems add one thing on top of that same agent.

The container filesystem still persists in every system (for example `/app/view.txt`). That is the environment, not the learning system.

Needs `OPENAI_API_KEY`. Use the OpenAI id `gpt-5.6-luna` (dot, not hyphen). Pi often needs a higher agent timeout than terminus-2.

### Baseline

Harbor’s built-in `pi`. Fresh chat each turn. No session files. Turn 1 and turn 2 are independent.

```bash
harbor run -p tasks/tally -a pi -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5
```

### Pi sessions

Same `pi` agent, plus session copy. [pi-sessions](agents/pi_sessions/) writes each turn’s JSONL to `/app/sessions/`. Later turns can read those files.

```bash
PYTHONPATH=. harbor run -p tasks/tally \
  -a agents.pi_sessions:PiSessionsAgent \
  -m openai/gpt-5.6-luna \
  --agent-timeout-multiplier 5
```

### In-context learning

Same `pi` agent as baseline. `--resume-trajectory` continues the chat across turns. Harbor sets this on agents that declare `SUPPORTS_RESUME` (pi does). Earlier turns stay in the model context.

```bash
harbor run -p tasks/tally -a pi -m openai/gpt-5.6-luna \
  --resume-trajectory \
  --agent-timeout-multiplier 5
```

### Feedback domains

The timing and visibility of feedback define three task domains.

#### Verifiable tasks

The agent can observe correctness during the step. A wall blocks movement, an opponent responds to an attack, or a grader checks a candidate answer. The agent can react before it commits its final result.

These tasks test learning from direct interaction. If the environment offers a grader, task authors must cap or penalize calls so that brute-force search does not replace learning.

Examples: Affinity Arena and Courier / Picker.

#### Semi-verifiable tasks

The agent commits without a correctness signal. The verifier grades the result after the step, and the agent can receive limited feedback on a later step. There is no grading call during the attempt.

These tasks can test policy or ontology induction, but they need strong controls. Score the first attempt, keep an append-only feedback history, and reserve a holdout tail that never received direct corrections. Otherwise the task can measure answer copying instead of learning.

This design is still under study. We will not treat a semi-verifiable task as a benchmark result until its feedback and holdout design can separate generalization from memory replay.

Examples: Expense Desk and Data Lake without an in-step grader.

#### Non-verifiable tasks

The agent receives no correctness signal during or after a step. It learns only from the stable structure that it can inspect, such as a file tree, document corpus, website, or schema.

These tasks focus on efficiency. The benchmark can measure output quality, but it does not return the verdict to the agent. Quality must stay stable while file opens, navigation steps, probes, or tokens fall.

Examples: Corpus (Confluence wiki), codebase question answering, and web exploration.

### Evidence of learning

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

A good task has one clear learning object, a measurable improvement curve, enough steps to show a trend, and a holdout that tests transfer. It should not install the solution, reveal hidden state, or use a final aggregate score as its only result.

## Tasks

Tally, Report check, Affinity Arena, Database analytics, Codebase Q&A,
Corpus, and Web exploration are runnable. The other folders contain
task designs or early concepts.

| Task | Domain | Status | Learning object |
|---|---|---|---|
| [Tally](tasks/tally/) | Verifiable | Runnable sample | Card counts across twelve turns |
| [Affinity Arena](tasks/affinity-arena/) | Verifiable | Runnable | A hidden affinity chart across twenty battles |
| [Report check](tasks/report-check/) | Verifiable | Runnable | An unpublished house style guide, learned from review comments |
| [Courier / Picker](tasks/courier-picker/) | Verifiable | Design | A fixed spatial map |
| [Expense Desk](tasks/expense-desk/) | Semi-verifiable | Design, blocked by feedback study | An unwritten expense policy |
| [Corpus](tasks/corpus/) | Non-verifiable | Runnable | A frozen Confluence wiki map |
| [Codebase Q&A](tasks/codebase-qa/) | Non-verifiable | Runnable | Flask hierarchy and call patterns |
| [Database analytics](tasks/database-analytics/) | Non-verifiable | Runnable | Formula 1 schema and query patterns |
| [Web exploration](tasks/web-exploration/) | Non-verifiable | Runnable; external Shopping service required | WebArena-Verified Shopping structure and navigation across 187 tasks with `agent-browser` |

Download the Formula 1 database before you run Database analytics. See [`tasks/database-analytics/README.md`](tasks/database-analytics/README.md). Download Flask before you run Codebase Q&A. See [`tasks/codebase-qa/README.md`](tasks/codebase-qa/README.md). Download the Confluence wiki before you run Corpus. See [`tasks/corpus/README.md`](tasks/corpus/README.md). Before you run Web exploration, start the official external WebArena-Verified Shopping service, create its authentication state, and generate the 187 Shopping-only tasks. See [`tasks/web-exploration/README.md`](tasks/web-exploration/README.md).

Tally proves the Harbor multi-step setup, persistent workspace, per-step rewards, and run reporting. Report check is a house-style review loop with capped submissions. Affinity Arena is a sequence of creature battles against a hidden affinity chart, with a holdout roster. Database analytics, Codebase Q&A, and Corpus add a Reward Kit verifier and baseline vs `--resume-trajectory` runs. Web exploration runs the same learning conditions over the official WebArena-Verified Shopping service through `agent-browser`. Courier / Picker and Expense Desk currently document the intended task design but do not yet include runnable environments or verifiers.

## Contributing a task

Build tasks in [Harbor](https://www.harborframework.com/docs) format and submit them through this repository. A task proposal should state:

- its feedback domain;
- the stable object that the agent must learn;
- the expected learning curve;
- the per-step reward and cost metric;
- the baseline, pi-sessions, and in-context run commands; and
- the holdout or other control that rules out shortcuts.

Do not build a semi-verifiable task until its feedback policy can show generalization instead of answer replay.

## References

- [ARC Prize](https://arcprize.org/)
- [ARC-AGI documentation](https://docs.arcprize.org/)
- [ARC-AGI community leaderboard](https://arcprize.org/leaderboard/community)
- [Ilya Sutskever interview](https://www.youtube.com/watch?v=aR20FWCCjAs)
- [Ilya Sutskever interview transcript](https://www.dwarkesh.com/p/ilya-sutskever-2)
- [Harbor documentation](https://www.harborframework.com/docs)
