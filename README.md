# Agent Learning Bench
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/manojbajaj95/agent-learning-bench)
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

One trial contains one fixed environment and many ordered Harbor steps. Each step is one job, fight, question, or episode. Hidden engine state stays under `/opt`. A new trial starts a new container.

Baseline starts each step with no chat memory, no agent files, and no traces. In-context learning is the system that keeps the chat.

## Learning systems

The bench compares systems on the same task, model, and step order. Harbor's built-in [pi](https://pi.dev/) agent is the baseline harness. Other systems add one thing on top of that same agent.

Baseline does not carry agent files or traces into the next step. In-context learning keeps the earlier chat.

**Recipes live in [`systems.toml`](systems.toml).** The CLI reads that file. List them with:

```bash
uv sync
source .venv/bin/activate
alb systems
alb run tally --system baseline
alb run tally --system icl
```

- **baseline** — Harbor `pi`. Fresh chat each step.
- **sessions** — same `pi`, plus [pi-sessions](agents/pi_sessions/) copies each session JSONL to `/app/sessions/`.
- **icl** — same `pi`, with `--resume-trajectory` so earlier turns stay in context.
- **oracle** — Harbor oracle. Writes the hidden solution. No model.

To add a system, add a `[systems.<name>]` table in `systems.toml`.

## CLI

Install the Typer CLI with [uv](https://docs.astral.sh/uv/), then run `alb` from an active venv:

```bash
uv sync
source .venv/bin/activate   # Windows: .venv\Scripts\activate
alb --help
```

Commands: `prepare`, `smoke`, `run`, `upload`, `report`, `systems`, `tasks`.

```bash
alb systems
alb prepare database-analytics
alb smoke database-analytics --system baseline
alb run database-analytics --system icl
alb upload database-analytics-icl
alb report database-analytics-icl
```

Systems come from [`systems.toml`](systems.toml). Smoke is the first 10 steps. `prepare` skips `download.sh` when `data/` already has files. Extra Harbor flags go after `--`.

```bash
alb run tally --system icl -- --force-build
```

Reports go to `reports/latest.md`, `reports/latest.html`, and SVG charts.

## Feedback domains

Tasks are verifiable or non-verifiable, depending on whether the agent can check its work before the step ends.

### Verifiable

During the step, the agent can tell whether an answer or action is correct and change it before that step's agent loop ends. A wall can block a move, or an opponent can respond to an attack. A reviewer can accept or reject a report, and a grader can score a candidate answer.

If the environment has a grader, cap or penalize calls so that brute-force search does not replace learning.

Examples: Tally, Poker, Affinity Arena, and Report check.

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
| Fresh baseline condition | Memory, files, or traces being mistaken for no learning |

Give the task one learning object and enough steps that a curve can show a trend. Include a holdout that tests transfer. Do not install the solution, reveal hidden state, or treat a final aggregate score as the only result.

## Tasks

All tasks are runnable except Sokoban, which is a design only.

`fixed` means the environment is the same on every run. `drift` means the environment changes from run to run. `ordered` means step order matters. `unordered` means any step order is the same task.

| Task | Domain | Labels | Learning object |
|---|---|---|---|
| [Tally](tasks/tally/) | Verifiable | drift, ordered | Card counts across twelve turns |
| [Poker](tasks/poker/) | Verifiable | drift, ordered | A sticky heads-up opponent across 100 hands |
| [Affinity Arena](tasks/affinity-arena/) | Verifiable | fixed, ordered | A hidden affinity chart across twenty battles |
| [Report check](tasks/report-check/) | Verifiable | fixed, ordered | An unpublished house style guide, learned from review comments |
| [Programming language](tasks/programming-language/) | Verifiable | fixed, ordered | One generated language, learned through interpreter feedback across twenty programming problems |
| [Corpus](tasks/corpus/) | Non-verifiable | fixed, unordered | A frozen Confluence wiki map |
| [Codebase Q&A](tasks/codebase-qa/) | Non-verifiable | fixed, unordered | Flask hierarchy and call patterns |
| [Database analytics](tasks/database-analytics/) | Non-verifiable | fixed, unordered | Formula 1 schema and query patterns |
| [Web exploration](tasks/web-exploration/) | Non-verifiable | fixed, unordered | WebArena-Verified Shopping structure and navigation across 187 tasks with `agent-browser` |
| [Sokoban](tasks/sokoban/) | Verifiable | fixed, ordered | One fixed board across episodes (design only) |

## Task checklist

Use this list for every new task. A task is ready when every item is true.

### README

The README opens with all of these:

- [ ] A short brief
- [ ] Verifiable or non-verifiable
- [ ] The environment
- [ ] The step design
- [ ] The learning goal
- [ ] The reward and the cost metrics
- [ ] Two labels: `fixed` or `drift`, and `ordered` or `unordered`

### Labels

- [ ] `fixed`: the environment is the same on every run
- [ ] `drift`: the environment changes from run to run. Say what changes
- [ ] `ordered`: step order matters. Later jobs must not be easier only because they come later
- [ ] `unordered`: any step order is the same task

### One learning object

Score the learning, not only the finished job. Earlier jobs must reveal structure that later jobs can reuse.

- [ ] Jobs share one world
- [ ] Jobs are related, and they are not copies of one prompt
- [ ] The task does not depend on another task
- [ ] The horizon is long enough for a curve
- [ ] A holdout tail uses the same world and new jobs
- [ ] The task has room for quality to rise or cost to fall
- [ ] A later check retests an earlier skill, or one small environment change tests repair

### Baseline keeps nothing

A baseline step starts with no chat memory, no agent files, and no traces. Check the words the agent reads, and check the environment.

- [ ] The step instruction does not mention notes or sessions
- [ ] The rules copied into `/app` do not mention notes or sessions
- [ ] The environment does not leave notes, session logs, or traces for the next baseline step
- [ ] In-context learning is the only official system that keeps the chat
- [ ] Oracle only checks that a solution exists. It is not a learning curve

### Score and cost

- [ ] `reward.txt` is the learning score for that step
- [ ] `reward.json` includes that score and a cost metric for the learning object
- [ ] The cost metric can fall while quality stays high, such as files opened, actions, queries, or iterations
- [ ] The first scored attempt fixes the reward
- [ ] The solution and the hidden state stay out of the agent view

### Run and report

- [ ] `alb prepare` downloads once, then does nothing when the task is already present
- [ ] A smoke slice does not rewrite the real task
- [ ] Baseline and in-context learning use the same task, model, and step order
- [ ] `alb report` takes one job and draws that job only
- [ ] `alb upload` takes that same job
- [ ] The report shows the curves for that job: outcome, cost, sample efficiency, holdout transfer, and repair when the task has drift

## Contributing a task

Build the task in [Harbor](https://www.harborframework.com/docs) format. Follow the task checklist above before you submit it.

## References

- [ARC Prize](https://arcprize.org/)
- [Harbor documentation](https://www.harborframework.com/docs)
