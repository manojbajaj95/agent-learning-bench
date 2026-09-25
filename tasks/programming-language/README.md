# Programming language

The agent solves twenty programming problems in one generated language. The token meanings stay fixed. Later problems should be solved on the first submission, with fewer local runs.

## Task type

Verifiable. `language-lab compile` and `language-lab run` return syntax errors, runtime errors, and integer output during the step. Hidden tests return only a pass count. The agent can edit the program before the step ends. Each problem allows 64 local calls and six hidden submissions.

## Environment

- Checked-in instance: seed 1, generator version 3, task version 0.3.0, `hidden` information
- Image: `ubuntu:24.04` with Python 3.12. No extra packages.
- The interpreter cannot import modules, call host code, or read files.
- Hidden language and tests stay outside the agent workspace.
- Notes and code: `/app/notes.md` and `/app/workspace/`
- Public traces: `/app/problems/`
- Commands: `language-lab status`, `compile`, `run`, `submit`

Files in `/app` persist across the twenty problems. A new trial starts a new container and an empty workspace. The same task directory repeats the same language.

## Step design

One trial is 20 problems. One step is one problem. The language does not change. The problem statement, examples, and hidden tests do.

| Steps | Phase | Role |
|---|---|---|
| 1–6 | Foundation | Storage, printing, small transforms |
| 7–12 | Practice | Arithmetic, counters, conditions |
| 13–16 | Transfer | New combinations of those idioms |
| 17–20 | Holdout | Pairwise sums, prefix sums, sum of products, triangular number |

The problem id on a command must match the current problem. A stale command cannot spend the next problem's first submission.

## Learning goal

The learning object is the language: token meanings, cell size, tape edges, input, output, and loop rules. First-submission correctness should rise. Local calls and submissions should fall on new problems, including the holdout. Baseline starts a fresh chat each problem. In-context learning resumes the same chat.

An early-to-late score change by itself is not enough. The phases are not matched difficulty blocks. Compare baseline and in-context learning on the same problems.

## Reward and cost

The reward is the fraction of hidden tests passed on submission 1. No submission scores 0. Later submissions can raise `solved`. They do not replace `reward`. Harbor averages `reward` over the twenty problems.

The verifier writes `/logs/verifier/reward.json`. The fields used for the curve are:

| Field | Meaning |
|---|---|
| `reward` | First-submission hidden-test fraction |
| `solved` | 1 if any submission passed every hidden test |
| `submissions` | Hidden submission count |
| `attempts_to_solve` | Index of the first perfect submission, or 0 |
| `local_calls` | Compile and run requests |
| `env_actions` | Compile, run, and submit requests |
| `holdout` | 1 on problems 17–20 |

Harbor records `cost_usd`, input tokens, output tokens, and step duration. Report `reward`, `local_calls`, and `env_actions` on the same chart.

## Details

The sections below keep the language rules, the full metric table, and the generation commands.

## Trial structure

```text
new container, one generated language
    problem 1 -> notes, code, helpers -> problem 2 -> ... -> problem 20
```

The token mapping, arithmetic, tape, input/output behavior, loop behavior,
boundary rules, and execution limits stay
fixed across all twenty problems. Problem statements, examples, hidden inputs,
and expected outputs change. Each compile/run/submission receives source in
the unfamiliar language. Every execution, including each hidden test, begins
with fresh zeroed cells and fresh input/output buffers.

Agent files persist in `/app/notes.md` and `/app/workspace/`. Public command
traces persist in `/app/problems/`. Host-language helpers and generators are
allowed; only the generated target-language source executes during grading.
The interpreter cannot call host code, import modules, or read files.

Independent Harbor trials use new containers with empty notes, workspace,
and sessions. Repeating a trial from the same task directory repeats the same
language and problem sequence. Generate another seed to change the language.
Harbor's own job/trial identifiers do not select this task's language seed.

## Language and information conditions

The language is a small tape-machine dialect. Its public source alphabet is
`abcdefgh`; the seed permutes the eight token meanings. ASCII space, tab, CR,
and LF are ignored. Other characters are syntax errors, including comments.

The following is contributor documentation, outside the agent image:

| Property | Behavior |
|---|---|
| Operations | Move right/left, increment/decrement, integer input/output, paired loop start/end |
| Cells | Initially zero, values modulo a seeded choice of 16, 32, or 256 |
| Tape | Seeded size of 8, 16, or 32 cells; initial pointer is cell 0 |
| Pointer boundaries | Seeded choice of wrapping or an index error |
| Input | Seeded choice: replace the current cell, or add the next integer to it; reduce modulo the cell modulus |
| Output | Append the current integer cell value, then either preserve or clear that cell (seeded); no ASCII conversion |
| Loops | Skip on zero; otherwise use a seeded manual-counter or consuming-counter rule |
| End of input | Reading beyond supplied input raises an error; unread input is allowed |
| Limits | 8192 source bytes, 128 input values, 128 output values, 100,000 executed instructions |

Loops test the cell at the current pointer, including at the closing delimiter.
An executed delimiter counts as an instruction. A taken closing jump continues
at the first body instruction; skipped bodies consume no instructions.
In `manual` mode, neither delimiter changes the cell; the body must eventually
make the tested cell zero to terminate. In `consume` mode, the delimiter reduces
a nonzero cell by one **before each body iteration**, including the first.
That decrement counts as part of the delimiter, not an extra instruction.
Both modes test the current pointer, even if the body moved it; no entry cell
is captured. Nested loops follow exactly the same rule. Limits use instruction
counts, not machine-speed-dependent timeouts.

These choices affect reusable programming idioms. Reading into reused storage
may need a clear; printing a live value may need a copy; counted loops may need
an explicit decrement. The rules are coherent across every problem and are
observable through local runs. There are no per-problem semantic switches or
arbitrary truth tables.

Information is selected at task generation:

| Mode | Information the agent receives |
|---|---|
| `hidden` (default) | Alphabet, source/input formats, limits, tool usage, and problem examples; no machine model or token meanings |
| `partial` | The same interface plus a tape-machine outline and operation inventory; possible input/output/loop behaviors are outlined, but their selected values, token meanings, modulus, tape size, and boundary behavior remain hidden |

The two conditions differ only in the information rendered into `/app/view.txt`
and experiment metadata. The seed generates identical language, problems,
examples, hidden tests, budgets, and grading in both modes. `hidden` still
provides enough interface information to issue meaningful experiments.

A future `given` mode can extend `language_game/view.py:information` using the
existing `Language` value. It need not change generation, interpreter semantics,
or scoring. `given` and program-output prediction diagnostics are not MVP modes.

## Curriculum and holdout

| Steps | Phase | Problems |
|---|---|---|
| 1–6 | Foundation | Constant output, echo, print twice, keep the newest value, successor, reorder three values |
| 7–12 | Practice | Addition, repetition, counting sequence, sequence sum, equality, scale/offset |
| 13–16 | Transfer | Stream echo, echo with total, conditional selection, count nonzero values |
| 17–20 | Holdout | Pairwise sums, prefix sums, sum of products, triangular number |

All twenty problem families are distinct. The first twelve establish storage,
printing, arithmetic, counters, and conditional idioms. The next eight combine
those constructs in new programs. For example, print-twice and repetition can
teach how to preserve a value while printing; prefix sums reuse that knowledge
while also consuming input and updating an accumulator. Sum of products combines
nested loops, copying, and reused input cells. Transfer and holdout each have a
seeded order; the prerequisite sequence remains fixed.

These phases are **not matched difficulty blocks**. Compare memory conditions
on the *same* seeded problems with the same budgets, then examine correctness,
costs, and retained helpers. An early-to-late score change alone is not evidence
of learning. Small domains and bounded loop counts keep compositions manageable,
but real-agent runs are needed to calibrate difficulty and budget.

Tests check that no earlier reference solution can pass an entire holdout
unchanged. Reusing a learned code generator is intended transfer. Tests also
hold the token mapping and algorithm fixed while deliberately applying an
incorrect input, output, or loop idiom: each semantic dimension has failures
both before transfer and on a holdout. This establishes semantic coverage,
not that all valid solutions must discover every private parameter. Conservative
clearing and copying can work across multiple variants and are legitimate.

Problems use small nonnegative integers with outputs fitting every cell variant.
Small input domains are exhaustively tested after excluding public examples;
larger domains use deterministic boundary cases and samples. Hidden cases are
deduplicated and equally weighted. The constant-output foundation problem has just one
possible input (the empty list), so its example necessarily overlaps grading.
Equality examples are selected only from negative cases: the unique positive
case is reserved for hidden grading, alongside negative cases. Its public and
hidden inputs remain disjoint.
Expected outputs come from mathematical Python functions independent of the
interpreter and reference-program builder.

## Agent interface and feedback

```bash
language-lab status
language-lab compile problem-01 < /app/workspace/solution.lang
language-lab run problem-01 '[1, 2]' < /app/workspace/solution.lang
language-lab submit problem-01 < /app/workspace/solution.lang
```

The problem ID must match the current problem, so a stale command cannot consume
the next problem's first submission. Source is passed on stdin: the agent's
unprivileged shell opens the file before sudo. The privileged entrypoint never
accepts arbitrary file paths.

`compile` returns syntax success or an error with a source position. `run`
returns integer output, instruction count, and a concrete error when one occurs,
such as `INDEX_ERROR: index -1 invalid`. Errors do not explain hidden rules.
Output produced before a runtime error is visible on local runs. Input values
may range over 0..65535 for exploratory probes, even when a problem's domain
is smaller. Each call starts a fresh machine.

Hidden submissions return only submission number, passed count, total count,
and score. They never return individual test results, test inputs, expected
outputs, runtime errors, or instruction counts. Tool process exit 0 means the
request was processed; inspect the returned JSON for program success.

Each problem allows 64 combined compile/run calls and six hidden submissions.
Failed local calls consume the local budget. `status` consumes neither budget.
Submission remains available after local calls run out. A perfect submission
or the sixth submission closes the problem. Only the verifier can advance it.

## Reward and metrics

The primary reward is **first-submission correctness**:

```text
reward = hidden tests passed on submission 1 / total hidden tests
trial reward = mean(reward across the twenty problems)
```

Local testing before submission is allowed. Syntax errors on the first
submission earn zero. Runtime errors fail the affected tests even if partial
output happens to match. Output lists must match exactly. No submission earns
zero. A submission is an immutable source snapshot, so subsequent file edits
cannot alter its score. Later submissions may improve eventual correctness
but do not replace the first reward.

For example, passing 4/10 tests and then 10/10 earns primary reward **0.4**,
with eventual `solved=1` and `attempts_to_solve=2`.

Each verifier writes numeric metrics to `/logs/verifier/reward.json`:

| Metric | Meaning |
|---|---|
| `reward`, `first_correctness` | First submitted program's hidden-test fraction, or zero |
| `first_solved`, `solved` | First-submission full success / any-submission full success |
| `best_correctness`, `last_correctness` | Best and last submitted fractions, or zero |
| `submissions` | Hidden submission attempts, including invalid source |
| `attempts_to_solve` | Index of first perfect submission; zero means unsolved |
| `submitted` | Whether the agent submitted at least once |
| `completed` | Whether the verifier settled the problem; distinct from solved |
| `local_calls` | Compile/run requests processed, including invalid inputs/source |
| `compiler_calls` | Source compilation attempts, including hidden submissions |
| `compiler_errors` | Compilation attempts rejected for syntax or source limits |
| `runtime_calls` | Local runs that reached execution; excludes hidden test executions |
| `runtime_errors` | Requests with runtime failure; a submission counts at most once |
| `env_actions` | Processed compile/run/submit requests |
| `tool_calls` | Those requests plus status calls; excludes rejected command shapes, stale IDs, and exhausted-budget requests |
| `turn`, `holdout` | Problem index and holdout indicator |

`tool_calls` counts this task's CLI, not every shell/file tool used by the LLM.
Token usage, model cost, and agent duration come from Harbor's existing result
records. Sum `solved` over steps for problems solved; Harbor's mean aggregation
reports the solve rate. Private `problem.json` verifier artifacts retain seed,
version, information mode, phase, family, and source submission snapshots.

The expected signals are improving first-submission correctness, high eventual
success, and fewer local calls/submissions on the same novel jobs across memory
conditions.
Report all curves together. An aggregate final score alone does not establish
learning, and missing/failed steps must be flagged rather than silently dropped.

### Alternative: completion with a retry penalty

An alternative scoring option for future experiments is Report check's
completion-with-retry-penalty reward. If the first fully correct submission is
number `k`, define:

```text
completion_reward = max(0.4, 1.0 - 0.15 * (k - 1))
completion_reward = 0 if no submission is fully correct
```

This gives 1.0 for first-try success, 0.85 for second-try success, and so on.
The example above would earn **0.85** under this option. It emphasizes reaching
a correct solution efficiently, while first-submission correctness emphasizes
performance before hidden-test feedback on the current problem.

The MVP uses first-submission correctness. The alternative is documented here
for future selection; there is no scoring CLI switch. Existing `solved` and
`attempts_to_solve` metrics allow reconstructing it without rerunning an agent.
Keep the scoring condition explicit in reports and compare like with like.

## Generation and reproducibility

Use Python 3.12 (the Ubuntu 24.04 image's Python series). No packages beyond
the standard library are required to generate a task or run the interpreter.

```bash
python3 tasks/programming-language/generate_steps.py
python3 tasks/programming-language/generate_steps.py --check
python3 tasks/programming-language/generate_steps.py --seed 42 --visibility hidden \
  --output tasks/programming-language/results/seed42-hidden
python3 tasks/programming-language/generate_steps.py --seed 42 --visibility partial \
  --output tasks/programming-language/results/seed42-partial
```

Separate outputs are complete runnable Harbor tasks and leave the checked-in
instance untouched. The generator verifies every reference program against
every generated example and hidden test before writing any task files.
Unexpected step files are preserved and reported by `--check`; no directories
are recursively deleted.

Like Affinity Arena, the generator uses private, named `random.Random` streams:

```text
programming-language-v3:<stream>:<seed>
    language
    problems
    schedule
    examples:<problem index>
    hidden-tests:<problem index>
```

It does not depend on process hash seeds, global random state, time, model
responses, or filesystem ordering. Problem inputs are generated once and stored
in the private manifest; submissions never resample tests. A golden manifest,
cross-process regeneration, and 100-seed checks guard reproducibility. Change
generator/interpreter version and task version when altering semantics, limits,
sampling, task contracts, or feedback. Keep old generated instances with the
matching implementation when reproducing older results. Version 3 reserves the
equality problem's positive case for hidden grading. The versioned RNG namespace
also changes generated languages and instances relative to version 2; compare
matched versions and keep earlier pilot tasks frozen. Interpreter semantics,
problem families, resource limits, and the scoring formula are unchanged.

## Running and reporting

Install the same development tool versions used by Affinity Arena:

```bash
python3 -m venv .venv
.venv/bin/pip install -r tasks/programming-language/requirements-dev.txt
```

With Docker running, first check the oracle (no model API key required):

```bash
.venv/bin/harbor run -p tasks/programming-language -a oracle \
  --job-name language-oracle --jobs-dir jobs -n 1 --max-retries 0
```

Use the same model and generated task across memory conditions. Export the
model provider's credentials through your shell; substitute its provider/model
identifier below. Use distinct job names for independent runs.

```bash
# Baseline: fresh conversation per problem, persistent files, ordered tools.
PYTHONPATH=tasks/programming-language .venv/bin/harbor run \
  -p tasks/programming-language -a language_agent.agent:SequentialPi -m PROVIDER/MODEL \
  --ak version=0.85.1 \
  --job-name language-baseline --jobs-dir jobs -n 1 --max-retries 0

# In-context: resume the conversation across problems, with persistent files.
PYTHONPATH=tasks/programming-language .venv/bin/harbor run \
  -p tasks/programming-language -a language_agent.agent:SequentialPi -m PROVIDER/MODEL \
  --ak version=0.85.1 \
  --resume-trajectory --job-name language-icl --jobs-dir jobs -n 1 --max-retries 0
```

`SequentialPi` inherits Harbor's Pi installation, model routing, usage accounting,
and conversation handling. Its extension preserves native `read`, `bash`, `edit`,
and `write` definitions, including prompt metadata, and executes tool batches in
order. This prevents concurrent writes and runs against the same source file.
It does not serialize background processes explicitly launched inside a shell.
Other Harbor agents remain supported. The repository's `pi_sessions` adapter adds
readable session history, but currently lacks this ordering fix; it is not a matched
control for these commands without composing the same extension.

After a Pi assistant error is found in the raw trace, this adapter refuses further
model calls in that trial. Harbor can still settle the remaining problems; those
results must be marked interrupted, not interpreted as a complete learning run.
On cancellation, it stops the expired Pi process and its ordinary children before
Harbor transfers logs or advances the problem. A cleanup failure also prevents
further model calls. Deliberately detached daemons are outside this cleanup's scope.
This is not a dollar spending cap or a replacement for provider retry settings.
`analyze.py` flags Pi assistant errors even when Harbor records no step exception.
The adapter is pinned to Pi 0.85.1. Free host and Docker preflights passed, including
installation of the corrected adapter and a real-process cancellation regression.

The optional Pi regression check requires Node 22.19+ and an isolated installation
of `@earendil-works/pi-coding-agent@0.85.1`. It uses scripted responses and no API key:

```bash
node tasks/programming-language/checks/pi_preflight.mjs \
  /path/to/node_modules/@earendil-works/pi-coding-agent
```

Replace `-p` with either generated condition directory for hidden/partial runs.
Use identical timeout multipliers and the same `--ak version=...` Pi version
for matched experiments. These commands invoke model APIs and use their quota.

```bash
python3 tools/report_runs.py --jobs-dir jobs --task programming-language --out-dir reports
python3 tasks/programming-language/analyze.py jobs/language-baseline jobs/language-icl \
  --require-complete --out-dir tasks/programming-language/results/comparison
```

The task-specific report preserves the shared summarizer's score/token/cost
handling and adds per-problem and phase metrics. Read the result's task metadata
and verifier artifacts to verify seed and information condition matches.

The ordinary baseline retains files and can learn. A real no-memory control
must start a fresh sandbox and conversation for each matched problem, as in
Affinity Arena's task-local `run_no_memory.py`. This MVP does not provide that
runner or describe fresh-chat runs as stateless. Its runtime/generation split
allows adding such a control without changing language semantics or grading.

## Isolation and lifecycle

The agent runs as an unprivileged user. The language, test bank, interpreter,
and authoritative state live under root-only `/opt/programming-language`.
The narrow sudo entrypoint uses isolated Python imports and accepts only public
commands. Public view/log parent directories cannot be replaced by the agent;
notes and workspace remain writable. State is locked and atomically written.

Harbor 0.22 runs setup hooks as the agent. The image initializes problem 1;
each root verifier freezes that problem's result and prepares the next one.
Setup only displays status. Repeated setup cannot reset attempts, and repeated
verification re-exports the frozen result without reopening or advancing jobs.
Verifier outputs are unreadable by the agent between problems. The log-access
repair is copied unchanged from Affinity Arena for resumed Harbor sessions.

Host-only `oracle.py` and `steps/*/solution/` are never copied into normal agent
images. Harbor uploads solution scripts only for oracle runs. The checked-in
seed is a public reproducibility fixture; use unpublished seeds for evaluation.
Network mode remains `public`, following existing tasks. Container permissions
address local information leakage, not external benchmark lookup or adversarial
timing side channels.

## Validation

```bash
.venv/bin/pytest tasks/programming-language/checks -m 'not docker' -q
.venv/bin/pytest tasks/programming-language/checks -m docker -q -ra
.venv/bin/ruff check tasks/programming-language
python3 tasks/programming-language/generate_steps.py --check
python3 tasks/programming-language/calibrate.py --check
```

Tests cover all 18 combinations of modulus/tape size/boundary behavior; all eight
input/output/loop combinations on the smallest tape and modulus; nested loops;
syntax, runtime, input and resource limits; cross-process determinism; all
reference solutions across 100 seeds; matched information conditions; novel
holdouts; observable and consequential semantics; first-score freezing; budgets;
concurrent submissions; and persistence/reset. Docker tests cover actual user
permissions, all twenty oracle steps, resumed-log access, and Harbor's full
oracle lifecycle in seed-1 hidden and seed-2 partial conditions. They explicitly
skip if Docker is unavailable. A cancellation regression checks that expired
agent processes and their children stop while an unrelated process survives.

`calibrate.py` is a **semantic coverage diagnostic**, not a scripted learning
agent. It validates every correct reference program, then holds the token map,
algorithm, hardware and tests fixed while generating programs with one wrong
semantic assumption. It records which problems fail. A correct map alone no
longer makes ordinary tape-machine idioms correct across all trials. No learner
receives reference algorithms, and this diagnostic reports no agent learning
score.

The current suite contains 64 local checks and five Docker checks. The reference
programs pass all examples and hidden tests across 100 seeds (2,000 problem
instances), including all eight input/output/loop variants on minimum hardware.
Coverage regressions check both equality branches and public/hidden separation
across 100 seeds in both information modes. Runtime tests submit a constant-zero
program, verify it cannot earn full credit, then verify a correct retry succeeds
without replacing the first-submission score.

## Limitations and next work

Equality grading has one positive and thirteen negative cases. A constant-zero
program earns 13/14 partial credit, but cannot solve the problem. Report full
solve rate alongside fractional correctness; the primary metric weights individual
tests equally and does not balance branches.

Real-agent pilots showed reusable loop/branch helpers, but runner interruptions
prevented a clean transfer evaluation. Sustained learning and a causal memory
benefit remain unverified. Run matched memory and information conditions on the
same seeded problems; fresh chats with persistent files are not a no-memory
control. A fresh-sandbox per-problem runner remains future work.

The curriculum is not calibrated to comparable difficulty across phases.
Print-twice can require copying and loops when output clears a cell; earlier
storage/retrieval and simple-loop practice may provide better prerequisites.
Any curriculum revision should preserve the novel holdout requirements and
be validated across all semantic variants.

Finite domains permit case enumeration and bounded unrolling. Modulus and boundary
variation are secondary: outputs fit the smallest modulus and reference programs
fit eight cells. Portable idioms that avoid identifying a private rule are valid.
`given` specification and output-prediction diagnostics remain future extensions.

## Layout

```text
tasks/programming-language/
├── README.md / instruction.md
├── task.toml / generate_steps.py
├── oracle.py / calibrate.py / analyze.py     # host-side tools
├── pyproject.toml / requirements-dev.txt
├── language_agent/                       # optional Pi ordering/timeout adapter
├── environment/
│   ├── Dockerfile / RULES.md / trial.json
│   ├── language-lab / public.py / admin.py
│   └── language_game/                     # interpreter, problems, runtime, views
├── checks/                               # author tests, not Harbor verifier hooks
└── steps/problem-01 … problem-20/
    ├── instruction.md
    ├── workdir/setup.sh
    ├── tests/test.sh
    └── solution/solve.sh
```

## Inspiration and provenance

Inspired by Lossfunk's [Frontier Coding Agents Use Metaprogramming to Adapt to
Unfamiliar Programming Languages](https://arxiv.org/abs/2606.10933), especially
interpreter feedback and reusable code generation. Their
[code license](https://github.com/Lossfunk/esolang-metaprogramming/blob/main/LICENSE)
is MIT. No Lossfunk code, problem data, interpreters, prompts, or harnesses are
reused here. The interpreter, problem bank, and reference programs are independently
implemented; runtime conventions and log permission repair come from this repository.
