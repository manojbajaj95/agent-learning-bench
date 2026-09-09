# Courier / Picker

Courier / Picker is a proposed Harbor multi-step task for spatial map learning.
It is a Domain 1 task: movement gives immediate and verifiable feedback.
This directory contains the design only. It is not yet a runnable Harbor task.

## Goal

The environment contains one fixed 64 by 64 grid. Walls do not change during a
trial. The agent can see only its coordinates and walls next to its current
cell. It must build a map from repeated jobs and use that map to take shorter
routes.

The simulator supports two job types:

- **Courier:** travel from a changing start cell to a changing goal cell.
- **Picker:** leave the dock, collect an item at a changing reachable cell, and
  return to the dock.

One Harbor step is one job. The map persists across all steps.

## Agent interface

The simulator provides movement actions and a local sensor result. Each action
returns the new coordinates and adjacent wall observations. Attempts to move
through a wall consume an action but do not change the position.

The true map and optimal path data stay outside the agent workspace. The agent
can keep its learned map and route notes under `/app`.

## Courier scoring

Courier uses a fixed action budget. Its reward is:

```text
1 - (path length - optimal path length) / budget
```

A timeout receives zero reward. Clamp the computed reward to the supported
Harbor reward range.

## Picker scoring

The Picker starts at the dock. The item appears at a random reachable cell. A
successful job collects the item and returns to the dock within the budget.
The main cost is the action count. The expected optimum is approximately twice
the shortest dock-to-item distance.

Before implementation, define one normalized Picker reward from success,
action count, and the optimal route. Always report the raw action count with
the reward.

## Measurements

Record these values for each job:

```text
turn, job_type, reward, env_actions, tokens, wall_sec, optimal_actions, success
```

The headline curve is actions to completion moving down toward the optimum.
Success must stay stable or improve while route length falls.

As an unscored diagnostic, compare the agent map with the true map and report
wall-map intersection over union. This shows whether route improvement comes
from a reusable map.

## Holdout

Reserve the last part of the job sequence for starts, goals, or item locations
in a district that earlier jobs did not visit. A route memorizer should fail
this tail. An agent that learned the map conventions and connected routes
should transfer better.

Use a fixed map and fixed job sequence when comparing agents. Generate a new
map only for a separate benchmark instance.

## Evaluation conditions

Run the same map and job sequence in two conditions:

| Condition | Conversation | Files | Purpose |
|---|---|---|---|
| Baseline | Fresh at each step | Persist | Tests file-based map memory only |
| Main | Resume across steps | Persist | Tests in-context learning plus files |

The map, jobs, action budgets, and timeouts must match across both conditions.

## Planned Harbor layout

```text
tasks/courier-picker/
├── README.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   └── courier_picker/         # Grid generator, simulator, and path oracle
└── steps/
    └── job-001 … job-N/
        ├── instruction.md      # Current job and stable action contract
        ├── workdir/setup.sh    # Reset position and publish the job
        └── tests/test.sh       # Settle job and write reward plus metrics
```

Keep the true map, job bank, and shortest-path oracle under `/opt`. Keep only
local observations, agent notes, and submitted routes under `/app`.

## Extension path

Start with one job type and one fixed map. Add the second job type only after
the first version gives a clear efficiency curve. Do not add moving walls or
new sensor types until the benchmark can separate map learning from route
memorization.
