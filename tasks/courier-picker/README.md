# Courier / Picker

The agent learns one fixed map by walking it. Later jobs should use shorter routes. This directory is a design only. It is not a Harbor task yet. `alb prepare courier-picker` rejects it.

## Task type

Verifiable. A move into a wall fails at once. The agent sees the new cell and the walls next to it, and can choose another move in the same job.

## Environment

Planned container:

- One fixed 64 by 64 grid for the whole trial
- The agent sees its coordinates and the walls next to the current cell
- True map, job bank, and shortest paths live under `/opt`
- Notes and the learned map live under `/app`
- A blocked move spends an action and does not change the cell

## Step design

One step is one job. The map persists across jobs. Two job types are planned:

- Courier: go from a new start cell to a new goal cell.
- Picker: leave the dock, collect an item, and return to the dock.

Build one job type and one map first. Add the second job type after that curve is clear.

The holdout is the last part of the job list. Those starts, goals, or item cells sit in a district the earlier jobs did not visit. A route memorizer should fail that tail. An agent that learned the map should transfer.

Use one map and one job order for every compared run. A new map is a new benchmark instance.

## Learning goal

The learning object is the wall map. Success should stay high while actions move down toward the shortest path. Baseline starts a fresh chat each job. In-context learning resumes the same chat. Files in `/app` persist in both conditions.

## Reward and cost

Courier reward, clamped to the Harbor range:

```text
1 - (path length - optimal path length) / budget
```

A timeout scores 0.

Picker still needs one normalized reward from success, action count, and the optimal route. Always report the raw action count with that reward.

Each job should record:

```text
turn, job_type, reward, env_actions, tokens, wall_sec, optimal_actions, success
```

`tokens` and `wall_sec` come from the Harbor job. An unscored map check can report wall-map intersection over union. That check shows whether a shorter route came from a reusable map.

## Planned layout

```text
tasks/courier-picker/
├── README.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   └── courier_picker/
└── steps/job-001 … job-N/
```
