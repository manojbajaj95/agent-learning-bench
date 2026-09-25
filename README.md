# Agent Learning Bench
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/manojbajaj95/agent-learning-bench)
> We define AGI as a system that can match the learning efficiency of humans.
>
> [ARC Prize](https://arcprize.org/)

## Why build this benchmark?

Most agent benchmarks score a finished job. This bench scores whether earlier jobs change later ones. The write-up is [Score the learning, not the job](https://mbajaj.me/blog/agent-learning-bench-score-the-learning-not-the-job).

The question is:

> Can an agent learn a stable environment and become more accurate, faster, or cheaper over repeated jobs?

The bench does not pick a learning mechanism. A system may change weights, a harness, stored experience, a world model, or code. The curves stay comparable.

Report these curves for each job:

- Outcome: does reward rise?
- Learning efficiency: does a successful job cost less?
- Sample efficiency: how many jobs until performance is useful?
- Retention: do new jobs erase an older skill?
- Holdout transfer: does the tail stay strong on unseen jobs?
- Repair: after a small environment change, does the system recover?

A final score cannot answer these questions. Each task reports a curve across steps.

## Task design

One trial contains one environment and many Harbor steps. Each step is one job, fight, question, or episode. Hidden engine state stays under `/opt`. A new trial starts a new container. Label the task `fixed` or `drift`, and `ordered` or `unordered`. The definitions are in the [task checklist](CONTRIBUTING.md#task-checklist).

Baseline starts each step with no chat memory, no agent files, and no traces. In-context learning is the system that keeps the chat.

## Learning systems

The official comparison is baseline and in-context learning, on the same task, model, and step order. Harbor's built-in [pi](https://pi.dev/) agent is the harness.

Baseline does not carry agent files or traces into the next step. In-context learning keeps the earlier chat. `systems.toml` also has a sessions recipe and an oracle. Those are not learning curves. To add a system, follow [Contributing a learning system](CONTRIBUTING.md#contributing-a-learning-system).

**Recipes live in [`systems.toml`](systems.toml).** The CLI reads that file. List them with:

```bash
uv sync
source .venv/bin/activate
alb systems
alb run tally --system baseline
alb run tally --system icl
```

- **baseline** — Harbor `pi`. Fresh chat each step. No agent files and no traces.
- **icl** — same `pi`, with `--resume-trajectory` so earlier turns stay in context.

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
| `fixed` or `drift` label | A world change being mistaken for learning |
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

## Contributing

Build a task in [Harbor](https://www.harborframework.com/docs) format. The task checklist is in [CONTRIBUTING.md](CONTRIBUTING.md#task-checklist). A new learning system is a table in [`systems.toml`](systems.toml). The rules are in [Contributing a learning system](CONTRIBUTING.md#contributing-a-learning-system).

## References

- [Score the learning, not the job](https://mbajaj.me/blog/agent-learning-bench-score-the-learning-not-the-job)
- [ARC Prize](https://arcprize.org/)
- [Harbor documentation](https://www.harborframework.com/docs)
