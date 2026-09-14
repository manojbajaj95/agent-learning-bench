# Programming language lab

Solve the current problem in `/app/view.txt`. All twenty problems use the same
language. Every execution starts fresh; the language does not change.

Write your source in `/app/workspace/`. You may use any installed host language
to create helpers, tests, or code generators. The submitted source must be in
the lab's language. The interpreter has no access to your files or host programs.

## Commands

Replace `problem-01` below with the current problem ID from `/app/view.txt`.

```bash
language-lab status
language-lab compile problem-01 < /app/workspace/solution.lang
language-lab run problem-01 '[1, 2]' < /app/workspace/solution.lang
language-lab submit problem-01 < /app/workspace/solution.lang
```

`compile` checks source syntax. `run` executes source with your input list and
returns a JSON object containing output, executed-instruction count, and an
error if one occurred. Both compile/run failures and successes consume one
local call. A failed program may have produced partial output before its error.
Tool process exit 0 means the request was processed: inspect the JSON `error`
field or submission `score` to determine program success.

Source uses the alphabet in the view; ASCII spaces, tabs, CR and LF are ignored.
Inputs are JSON lists of integers in 0..65535, at most 128 values. Outputs are
integer lists. A run accepts at most 8192 source bytes, executes at most 100,000
instructions, and emits at most 128 integers. Reaching the source end finishes
execution; a runtime error makes that test fail. Extra or missing output fails.

## Submissions and scoring

Each problem permits 64 combined compile/run calls and six hidden submissions.
`status` uses neither budget. Submissions evaluate a saved snapshot of your
source and return only passed count, total count, and score. They do not reveal
hidden inputs, expected outputs, individual results, or execution diagnostics.
No problem ID, filename, or host program is passed to the submitted program.

**Your first hidden submission fixes the problem's reward:** the fraction of
hidden tests it passes. Local experiments before that submission do not fix
the reward. You may revise and submit again to learn from feedback; eventual
correctness and attempts to solve are recorded separately. A syntax-error first
submission earns zero. No submission earns zero. Editing the source file after
submitting cannot change the saved submission or its score.

A perfect submission or the sixth submission closes the problem. Stop when it
closes, or when you decide to finish the step. Only the harness advances to the
next problem. You cannot restart a problem or restore its budgets.

## Keeping what you learn

Your `/app/notes.md`, `/app/workspace/`, and public traces under `/app/problems/`
persist through this trial. Prior sessions are under `/app/sessions/` when the
agent harness supports them. Record useful observations and retain reusable
helpers. Test whether a working pattern still behaves correctly when you combine
it with other operations. Independent trials start with empty notes, helpers, and sessions.
