# WebArena Shopping Benchmark Design

## Goal

Replace the fictional `tasks/web-exploration` environment with a Harbor multi-step benchmark over all 187 strictly Shopping-only WebArena-Verified tasks. Measure whether the same Pi agent becomes more accurate and efficient as it learns one fixed storefront.

## Fixed choices

- Dataset and evaluator: WebArena-Verified, pinned to one released version.
- Site filter: exactly `sites == ["shopping"]`; exclude every cross-site task.
- Task count: all 187 tasks, in one deterministic order shared by every condition.
- Browser interface: the official `agent-browser` CLI and its bundled skill.
- Conditions: baseline Pi, `PiSessionsAgent`, and Pi with `--resume-trajectory`.
- Authentication: load the benchmark-provided authenticated state before each task; the agent never performs login or receives credentials.
- Isolation: restore Shopping to its canonical snapshot before each task while preserving agent learning state.
- Scope: repository code and documentation only. Machine-level Docker and Harbor installation remains a documented prerequisite; `agent-browser` is installed inside the task image.

## Architecture

The Shopping site runs as the official WebArena-Verified Docker service outside Harbor's agent container. Its application and environment-control endpoints are reachable from the Harbor container through configured URLs.

`tasks/web-exploration` contains:

- a generator that reads the pinned WebArena-Verified dataset and emits 187 Harbor steps;
- a Harbor environment image with Pi prerequisites, `agent-browser`, Chromium, WebArena-Verified, and small task/reset scripts;
- a single static agent instruction;
- verifier glue that evaluates official task outputs;
- setup and smoke-validation documentation.

No custom browser abstraction, task judge, copied ground truth, or three-condition orchestration framework is introduced.

## Step lifecycle

For each Harbor step:

1. Call the WebArena environment controller to restore the canonical Shopping snapshot and wait until healthy.
2. Create a fresh isolated `agent-browser` session.
3. Load the official authenticated browser state without exposing credentials to the agent.
4. Start HAR recording.
5. Publish the task ID, intent, and rendered Shopping start URL under `/app`.
6. Run Pi. Pi uses `agent-browser` commands and writes the WebArena-Verified structured final response.
7. Stop HAR recording.
8. Evaluate the task with the pinned WebArena-Verified evaluator.
9. Write the scalar correctness reward and browser metrics to `/logs/verifier/reward.json`.
10. Close and discard browser task state.

The next step receives a restored site and fresh browser state but retains the condition's learning state.

## Learning state

| Condition | Preserved across tasks |
|---|---|
| Baseline Pi | `/app/notes.md` and ordinary workspace files |
| Pi Sessions | baseline files plus copied `/app/sessions/*.jsonl` |
| Resumed trajectory | baseline files plus Harbor-resumed conversation context |

Site database mutations, cookies, tabs, and task-local browser state are not learning state and are reset.

## Metrics

Reuse Harbor's existing per-step and per-trial metrics:

- input, cache, and output tokens;
- model-reported USD cost;
- agent and trial duration;
- verifier reward and exceptions.

Add only metrics Harbor cannot infer:

- unique Shopping URLs visited, derived from the HAR;
- `agent-browser` command count, derived from the Pi trajectory.

Correctness remains the official WebArena-Verified score. Infrastructure failures are errors, not zero-reward agent failures.

## Failure handling

Fail the step explicitly when:

- the Shopping reset or health check fails;
- authenticated state cannot be loaded;
- HAR recording cannot start or stop;
- the agent response is missing or invalid;
- the official evaluator fails.

An ordinary incorrect agent response receives the evaluator's zero reward.

## Validation

The smallest required checks are:

1. Dataset check: exactly 187 tasks and every task has `sites == ["shopping"]`.
2. Generation check: task IDs, order, instructions, and Harbor manifest are reproducible.
3. Environment check: reset, health, authenticated state, and one page navigation work.
4. Evaluator check: one known-valid fixture passes and one invalid response fails.
5. Isolation check: a site mutation disappears after reset while `/app/notes.md` remains.
6. Three-condition smoke run: the same three task IDs run once in each condition before any full benchmark.

## Running policy

Full runs are separate sequential Harbor jobs with identical model, dataset order, site snapshot, and timeout settings:

- `webarena-shopping-baseline`
- `webarena-shopping-sessions`
- `webarena-shopping-icl`

The full comparison is 187 tasks per condition, 561 model-backed step executions total. Full paid runs require explicit approval after smoke-run costs and context behavior are inspected.

## Constraints

- The official slim Shopping image is approximately 17.8 GB, exceeding the earlier lightweight preference; this is accepted in exchange for using established WebArena tasks.
- All official Shopping tasks require authenticated state, but login is handled by setup rather than treated as an agent task.
- A 187-step resumed trajectory may reach model context limits. The smoke run must verify Harbor/Pi behavior; no custom summarizer is added unless evidence shows it is necessary.
