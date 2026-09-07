# Affinity Arena

Affinity Arena is a runnable, verifiable Harbor multi-step task. The checked-in
instance uses seed 1 and chart generator v2 (task version 0.2.1).
See [VALIDATION.md](VALIDATION.md) for measured results
and manual acceptance checks.

The agent plays a sequence of deterministic 3-on-3 creature battles. Every
creature and move has one of six affinities, and attack damage depends on a
hidden affinity chart. The agent must infer that chart from observed damage,
retain what it learns across battles, and use it to draft teams and choose
actions.

## Learning objective

The learning object is a fixed 6 x 6 table:

```text
multiplier[attack affinity][defender affinity] = 0.5, 1, or 2
```

Each row and column contains two of each multiplier, so every affinity has
strengths and counters. An attack reveals one cell through its damage value.
The generator constructs balanced charts with distinct attack and defense
profiles for all six affinities. The chart is generated from the trial seed
and remains fixed for the entire trial.

## Trial structure

- A trial contains 20 battles against the same hidden chart.
- Battles 1-15 use a main roster of 12 creatures, with every affinity
  represented twice.
- Battles 16-20 use a holdout roster with new creature names and movesets.
- Each battle offers the agent five creatures; it drafts three in order.
- The opponent team, offered pool, and chart are deterministic for a given
  seed and shared across evaluation conditions.
- A win, loss, or tick limit ends the battle. Only the first attempt counts.

The holdout roster tests whether the agent learned affinity relationships
rather than memorizing creature matchups.

## Battle rules

- Agent creatures have 100 HP; opponent creatures have 140 HP.
- Each creature has one affinity and three moves.
- Each affinity appears equally often across the roster's moves. The two
  creatures of each affinity have different secondary affinities.
- Its same-affinity move has power 50; its other moves have power 36.
- Damage is `floor(power x multiplier)`, with no additional bonuses. Logs show
  full damage even on knockouts; HP is clamped at zero.
- On each tick, the agent attacks or switches, then the opponent attacks.
- Switching consumes the agent's action, and the incoming creature takes the
  opponent's attack.
- When a creature falls, the earliest living creature in original draft order enters and the tick
  ends.
- The opponent never switches voluntarily. It selects the move that deals the
  most damage under the true chart, breaking ties by listed move order.
- The battle ends when either team is defeated or after 30 ticks. Invalid
  actions do not advance time. Names are case-sensitive.

The agent can see rosters, affinities, move powers, HP, actions, and damage. It
cannot see multipliers, effectiveness labels, the chart, or the oracle.

## Agent interface

```text
affinity-arena status
affinity-arena draft <creature> <creature> <creature>
affinity-arena attack <move>
affinity-arena switch <creature>
```

`status` does not advance the battle. `draft` is accepted once, before the
first tick. `attack` and `switch` each advance one tick.

Every step gives the agent the same instructions:

1. Read `/app/world/RULES.md` and `/app/view.txt`.
2. Read persistent notes and prior session logs when available.
3. Draft a team and play until the battle ends.
4. Record useful observations in `/app/notes.md` and the inferred chart in
   `/app/affinity-chart.json`.
5. Stop without restarting the battle.

The chart file contains only observed cells and is used for diagnostics, not
as part of the reward. Use attack affinities as outer keys and defender
affinities as inner keys, e.g. `{"Amber": {"Basalt": 2}}`. Omit unknown cells.
Malformed entries are ignored. Helper files can be written in `/app/workspace/`.

## Evaluation

For a completed battle, the primary reward measures the remaining HP margin:

```text
reward = clamp(
  0.5 + 0.5 x (agent HP remaining / 300 - opponent HP remaining / 420),
  0,
  1
)
```

An unfinished attempt, including no draft, receives zero. Harbor averages
`reward` over the twenty steps; diagnostics do not contribute to that score.
The oracle maximizes reward, then minimizes ticks; optimal sets use both criteria.

Each battle also records:

| Metric | Meaning |
|---|---|
| `won` | Whether the opponent's full team was defeated |
| `completed` | Whether the attempt reached a terminal state |
| `ticks` | Number of ticks played |
| `oracle_ticks` | Ticks required by an optimal policy with the best draft |
| `opt_rate` | Fraction of draft and battle decisions in the oracle's optimal set |
| `regret` | Oracle reward minus agent reward for the matchup |
| `draft_ok` | Whether the draft can achieve the oracle's best value |
| `cells_seen` | Fraction of chart cells revealed during the trial |
| `belief_acc` | Correct chart entries divided by all 36 cells |
| `belief_cov` | Recorded chart entries divided by all 36 cells |
| `env_actions` | Draft and tick commands issued |

The expected learning signal is increasing reward, win rate, optimal-action
rate, draft quality, and belief accuracy, with decreasing regret and excess
ticks. `belief_acc` should rise with `cells_seen`, and performance should carry
over to the holdout roster.

## Evaluation conditions

All conditions use the same model, chart, and battle schedule:

| Condition | Conversation state | Persistent files |
|---|---|---|
| Baseline | Fresh conversation per battle | Yes |
| Pi sessions | Fresh conversation with prior session logs | Yes |
| In-context | Resumed trajectory | Yes |

An oracle run must win all 20 battles before the task is considered valid.
The baseline can learn through files and public battle logs; it is not the
offline memoryless policy.

## Validation and reproducibility

```bash
.venv/bin/pytest tasks/affinity-arena/checks -m 'not docker' -q
.venv/bin/pytest tasks/affinity-arena/checks -m docker -q
.venv/bin/ruff check tasks/affinity-arena agents/pi_sessions/agent.py
python3 tasks/affinity-arena/generate_steps.py --check
python3 tasks/affinity-arena/calibrate.py --check \
  --out-dir tasks/affinity-arena/results/calibration-v2
python3 tasks/affinity-arena/analyze.py jobs/arena-oracle --require-complete
```

Calibration compares an exact oracle, a persistent observation learner, and
the same learner forgetting between battles over seeds 1–10. `--check` checks
only data completeness and exact-oracle correctness. Reward changes, transfer,
and coverage are descriptive measurements, without arbitrary pass/fail cutoffs.
The offline learner's mean late-minus-early reward change is +0.136.
See [VALIDATION.md](VALIDATION.md) for interpretation and the manual review checklist.

Generate another complete instance without changing the default:

```bash
python3 tasks/affinity-arena/generate_steps.py --seed 2 \
  --output tasks/affinity-arena/results/seed-2
```

Every generated matchup is oracle-winnable. The generator uses seeded random
construction, integer damage/score arithmetic, and stable action ordering.
It never recursively deletes generated directories. Host-side trial data and
oracle scripts are authoring assets, not public agent observations.

## Isolation and controls

The chart, schedule, battle state, and oracle live in a root-only directory.
The agent interacts through a restricted CLI and receives only the public
view and tick log.

The agent runs as an unprivileged user. The sudo entrypoint accepts only the
four gameplay commands and uses isolated Python imports. Public output
directories resist replacement; notes and workspace remain writable. State
updates are locked and atomic. Verification freezes each result, so later
notes or repeated verification cannot change the score.

Harbor 0.22 executes setup hooks as the agent. The image initializes battle 1;
the root verifier settles each battle and prepares the next. Setup displays
the current view. Verifier outputs remain unreadable by the agent between steps.

The task uses these controls:

- deterministic battles and a seeded schedule;
- the same schedule across evaluation conditions;
- first-attempt scoring with no in-battle reset;
- a single irreversible draft;
- a holdout roster;
- no effectiveness labels or grader feedback during play; and
- hidden state that is unreadable by the agent.


## How to play

Run these commands from the repository root.

### Manual CLI (no API key)

Requires Python 3.12+; no Docker or extra packages are needed:

```bash
python3 tasks/affinity-arena/play.py --seed 1 --battle 1 --reveal-after
```

At `arena>`, draft three offered creatures, then attack with your active
creature's moves. For seed 1, battle 1, try:

```text
draft Gorm Vale Wick
attack Spore
```

Other commands: `switch <benched-creature>`, `status`, `rules`, and `quit`.
Names are case-sensitive. Keep playing until the battle ends; `--reveal-after`
then shows the hidden chart. Change `--battle 1` to `--battle 2` for the next
matchup. Each launch is an independent battle with fresh state.

### API agent (Gemini 3.5 Flash)

Requires a running Docker daemon. Install dependencies once, then enter your
key privately in Bash (it will not be echoed or saved in shell history):

```bash
python3 -m venv .venv
.venv/bin/pip install -r tasks/affinity-arena/requirements-dev.txt
read -rsp "Gemini API key: " GEMINI_API_KEY
export GEMINI_API_KEY
echo
```

Run a fresh 20-battle trial with conversation history and notes preserved:

```bash
PYTHONPATH=. .venv/bin/harbor run -p tasks/affinity-arena \
  -a agents.pi_trajectory:PiTrajectoryAgent \
  -m google/gemini-3.5-flash --ak version=0.85.1 \
  --resume-trajectory --agent-timeout-multiplier 5 \
  --job-name arena-gemini-1 --jobs-dir jobs -n 1 --max-retries 0
```

This uses your API quota/billing. Use a new job name for each run. To browse
traces, run `.venv/bin/harbor view jobs --port 8080` in another terminal and open
<http://localhost:8080>. Select the job, trial, and battle. The wrapper exports
each battle's trajectory after the agent finishes that battle; it does not
stream individual tokens. Pi's execution and conversation resume are unchanged.
Version 0.2.1 fixes log permissions between resumed battles; rerun older failed
trials under a new job name rather than using their scores as learning results.
After the trial, generate the learning report:

```bash
.venv/bin/python tasks/affinity-arena/analyze.py jobs/arena-gemini-1 \
  --require-complete --out-dir tasks/affinity-arena/results/gemini
```

Read `results/gemini/comparison.md` inside this task folder. Compare early
(1–5), late (11–15), and holdout (16–20) rewards, chart accuracy, and regret.
Learning gain is late minus early average reward; this measures use of memory,
not model-weight training. Check the report for incomplete attempts or errors.

To compare existing runs, pass multiple job directories to `analyze.py` before
`--out-dir`. Omit `--require-complete` to inspect an incomplete run; its report
still flags the issue. Report generation makes no API calls.

Older runs made with `-a pi` have native logs but no viewer trajectory. Convert
a finished run once, then refresh the viewer (no rerun or API key needed):

```bash
.venv/bin/python tools/convert_pi_trajectories.py jobs/gemini35-icl-seed1-fixed \
  --pi-version 0.85.1
```

Existing trajectory files and original logs are preserved.

## Oracle and OpenAI comparison runs

Check the oracle without an API key:

```bash
.venv/bin/harbor run -p tasks/affinity-arena -a oracle \
  --job-name arena-oracle --jobs-dir jobs -n 1 --max-retries 0
```

Set `OPENAI_API_KEY` in your shell, then supply a model ID available to your
account. Keep credentials out of task files, command arguments, and commits.

```bash
.venv/bin/python tasks/affinity-arena/run_matrix.py \
  --model openai/YOUR_MODEL_ID --prefix arena-seed1
```

The runner checks the oracle, then runs baseline, pi-sessions, and resumed Pi
in fresh containers using the same task and pinned Pi version. It stops on
incomplete trials or infrastructure errors and writes comparison reports under
`tasks/affinity-arena/results/matrix/`. Use a new `--prefix` for each experiment.
Add `--dry-run` to inspect commands without credentials or API calls.

For a custom **Responses-compatible** endpoint, also set `OPENAI_BASE_URL`
(including `/v1` where required). The runner supplies Harbor's
`--ak model_api=openai-responses` and uses your model ID unchanged. The endpoint
must support streamed Responses and tool calls. Include that same agent argument
when invoking Harbor directly with a custom base URL. Chat Completions-only
endpoints are outside this runbook.
