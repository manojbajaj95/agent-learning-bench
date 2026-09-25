# Contributing

Read [Score the learning, not the job](https://mbajaj.me/blog/agent-learning-bench-score-the-learning-not-the-job) before you add a task or a system. The bench scores whether earlier jobs change later ones. It does not pick a learning mechanism.

Build a task in [Harbor](https://www.harborframework.com/docs) format. A task is ready when every item in the checklist is true.

## Task checklist

### README

The task README opens with all of these:

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

## Contributing a learning system

A learning system is one way to use earlier jobs. Add it as a `[systems.<name>]` table in [`systems.toml`](systems.toml). The CLI reads that file. Do not put the run recipe in Python, and do not copy Harbor flags into the README.

```toml
[systems.example]
summary = "One sentence. What this system keeps from earlier steps."
agent = "pi"
flags = ["--resume-trajectory"]
```

Fields:

| Field | Required | Meaning |
|---|---|---|
| `summary` | no | One sentence shown by `alb systems` |
| `agent` | yes | Harbor agent name, or `package.module:Class` |
| `flags` | no | Extra Harbor arguments. Default `[]` |
| `pythonpath` | no | `"."` for an agent in this repo |
| `needs_model` | no | Default true. Set false for a solver that makes no model call |

The official comparison stays baseline against the new system, on the same task, model, and step order. Baseline still starts each step with no chat, no agent files, and no traces.

Show the curves from the blog: outcome, cost, sample efficiency, retention, holdout transfer, and repair when the task has drift. A system that only raises a final average is not enough.

Sessions and oracle already live in `systems.toml`. They are not learning curves. Do not make a task depend on them.
