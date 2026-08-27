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

One trial contains one fixed environment and many ordered Harbor steps. Each step is one job, fight, question, or episode. The environment and workspace persist, so the agent can build knowledge over time. Task authors should keep durable agent notes in `/app` and hidden engine state under `/opt`.

We compare multiple learnign sytems / harness:

| Condition | Conversation between steps | Files between steps | What it measures |
|---|---|---|---|
| Baseline | Fresh | Persist | Learning through file-based memory |
| In-Context Learning | Resumed with `--resume-trajectory` | Persist | In-context learning plus file-based memory |

### Feedback domains

The timing and visibility of feedback define three task domains.

#### Verifiable tasks

The agent can observe correctness during the step. A wall blocks movement, a boss responds to an attack, or a grader checks a candidate answer. The agent can react before it commits its final result.

These tasks test learning from direct interaction. If the environment offers a grader, task authors must cap or penalize calls so that brute-force search does not replace learning.

Examples: Warden and Courier / Picker.

#### Semi-verifiable tasks

The agent commits without a correctness signal. The verifier grades the result after the step, and the agent can receive limited feedback on a later step. There is no grading call during the attempt.

These tasks can test policy or ontology induction, but they need strong controls. Score the first attempt, keep an append-only feedback history, and reserve a holdout tail that never received direct corrections. Otherwise the task can measure answer copying instead of learning.

This design is still under study. We will not treat a semi-verifiable task as a benchmark result until its feedback and holdout design can separate generalization from memory replay.

Examples: Expense Desk and Data Lake without an in-step grader.

#### Non-verifiable tasks

The agent receives no correctness signal during or after a step. It learns only from the stable structure that it can inspect, such as a file tree, document corpus, website, or schema.

These tasks focus on efficiency. The benchmark can measure output quality, but it does not return the verdict to the agent. Quality must stay stable while file opens, navigation steps, probes, or tokens fall.

Examples: Corpus, codebase question answering, and web exploration.

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
| Fresh baseline condition | Filesystem memory being mistaken for in-context learning |

A good task has one clear learning object, a measurable improvement curve, enough steps to show a trend, and a holdout that tests transfer. It should not install the solution, reveal hidden state, or use a final aggregate score as its only result.

More detail is in [`docs/task-ideas.md`](docs/task-ideas.md).

## Tasks

Only Tally is runnable today. The other folders contain task designs or early concepts.

| Task | Domain | Status | Learning object |
|---|---|---|---|
| [Tally](tasks/tally/) | Verifiable | Runnable sample | Card counts across twelve turns |
| [Warden](tasks/warden/) | Verifiable | Design | A deterministic boss policy |
| [Courier / Picker](tasks/courier-picker/) | Verifiable | Design | A fixed spatial map |
| [Expense Desk](tasks/expense-desk/) | Semi-verifiable | Design, blocked by feedback study | An unwritten expense policy |
| [Corpus](tasks/corpus/) | Non-verifiable | Approved design | A cryptic schema and hidden business ontology |
| [Codebase Q&A](tasks/codebase-qa/) | Non-verifiable | Early concept | Code hierarchy and dependencies |
| [Database analytics](tasks/database-analytics/) | Not yet assigned | Early concept | Production database structure |
| [Web exploration](tasks/web-exploration/) | Non-verifiable | Early concept | Website structure and navigation |

Tally proves the Harbor multi-step setup, persistent workspace, per-step rewards, and run reporting. Warden, Courier / Picker, Expense Desk, and Corpus currently document the intended task design but do not yet include runnable environments or verifiers.

## Contributing a task

Build tasks in [Harbor](https://www.harborframework.com/docs) format and submit them through this repository. A task proposal should state:

- its feedback domain;
- the stable object that the agent must learn;
- the expected learning curve;
- the per-step reward and cost metric;
- the baseline and main run conditions; and
- the holdout or other control that rules out shortcuts.

Do not build a semi-verifiable task until its feedback policy can show generalization instead of answer replay.

## References

- [ARC Prize](https://arcprize.org/)
- [ARC-AGI documentation](https://docs.arcprize.org/)
- [ARC-AGI community leaderboard](https://arcprize.org/leaderboard/community)
- [Ilya Sutskever interview](https://www.youtube.com/watch?v=aR20FWCCjAs)
- [Ilya Sutskever interview transcript](https://www.dwarkesh.com/p/ilya-sutskever-2)
- [Harbor documentation](https://www.harborframework.com/docs)
