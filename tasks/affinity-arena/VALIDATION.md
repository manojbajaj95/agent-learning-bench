# Validating Affinity Arena

Use the task README for installation and commands. This file records the
acceptance criteria and what to inspect after a run.

## Deterministic checks

The automated suite covers chart balance/reproducibility across 100 seeds,
six distinct attack/defense profiles, and structural variation beyond row/column
permutations of one table. It also covers roster and move balance, randomized
legal battles, knockout and switch order, damage rounding, terminal states,
draft validation, oracle comparisons against short exhaustive fixtures, and
full oracle trajectory replay.

Runtime checks cover invalid commands, concurrent drafts, status without
advancement, incomplete-attempt scoring, repeated settlement, belief parsing,
and public traces. Docker checks run the commands as the actual unprivileged
agent and verify private files, lifecycle commands, verifier output, and public
output directories cannot be accessed or modified inappropriately.

The pinned versions are Harbor 0.22.0 and Pi 0.85.1. Harbor loads the generated
task successfully. The Pi/session-extension installation has also been tested
without making model inference calls.

The regenerated default instance completed a full Harbor oracle trial with
**20/20 wins**, zero regret, and every draft/action optimal
(`jobs/arena-chart-v2-oracle`). Mean reward was 0.7485. All 22 tests, including
Docker permission checks and incomplete-attempt scoring, pass. Generated-file
and lint checks also pass.

Task version 0.2.1 repairs resumed-session permissions after Harbor transfers
log ownership to the host. The root verifier restores agent-group access only
inside `/logs/agent`, preserving host ownership for archiving. Symlinks,
multiply-linked files, and special files are skipped; private state and verifier
permissions remain unchanged. A Docker regression reproduces the original
failure, and a keyless Harbor probe checks session continuity across all twenty
resumed steps. The probe writes the same log paths as Pi but makes no model
calls and intentionally does not play battles.

The earlier Gemini run `gemini35-icl-seed1` completed only battle 1; battles
2–20 failed on log/session permissions. Its scores are not a learning curve.
A fresh Gemini run is still needed to validate real-model behavior after this fix.

## Offline calibration

Run:

```bash
python3 tasks/affinity-arena/calibrate.py --check \
  --out-dir tasks/affinity-arena/results/calibration-v2
```

This uses seeds 1–10, twenty battles per seed, and these policies:

- **Oracle:** exact search with the true chart.
- **Learner:** exact planning with remembered observations and `1×` for unknown
  cells; prefers observing an unknown cell when estimated action values tie.
- **Memoryless:** the same learner with observations cleared before each battle.

The learner is an observation-based reference policy, not an upper bound on
every possible exploration strategy. It does not infer unobserved cells from
the row/column balance or opponent-choice inequalities.

Measured v2 reward and win-rate means on 2026-09-06:

| Policy | Early reward (1–5) | Late reward (11–15) | Holdout reward (16–20) | Early wins | Late wins | Holdout wins |
|---|---:|---:|---:|---:|---:|---:|
| Oracle | 0.745 | 0.738 | 0.741 | 100% | 100% | 100% |
| Learner | 0.574 | 0.710 | 0.733 | 64% | 96% | 100% |
| Memoryless | 0.444 | 0.398 | 0.423 | 32% | 22% | 20% |

Learning improvement, transfer, and coverage are descriptive measurements,
without pass/fail thresholds. `--check` checks completeness and oracle
correctness only.

The learner's late-minus-early reward improvement was approximately 0.136.
Full per-seed, per-battle results are in
`results/calibration-v2/calibration.json`, with a readable summary alongside it.
No LLM learning claim follows from these simulator results.

An additional check on seeds 11–20 gave learner reward
**0.582 → 0.721 → 0.721** (early, late, holdout). Late/holdout win rates were
100%/94%; late-minus-early reward improvement was 0.139.
These results are in `results/validation-seeds-v2/`. Neither batch was used to
tune the replacement generator or the roster.

## Manual agent review

1. Run the oracle and confirm twenty wins, `draft_ok = opt_rate = 1`,
   `regret = 0`, and `ticks = oracle_ticks`. Oracle reward need not equal 1:
   its creatures can take damage even when playing optimally.
2. Set an API key in the shell and run the matrix command from the README.
   Use identical model settings and seed across baseline, sessions, and
   resumed-context conditions. No inference key was present during implementation,
   so the real-model matrix remains to be run.
3. Read `results/matrix/comparison.md`. Check that each job contains all twenty
   ordered battles with complete metrics and no infrastructure errors.
4. Compare battles 1–5 with 11–15. Look for reward, belief accuracy, optimal-action
   rate, and draft quality rising, with regret falling. Inspect ticks alongside
   wins: a quick loss can use fewer ticks than the oracle.
5. Compare battles 16–20 with 11–15. Check whether chart knowledge survives the
   new names and moves. The holdout tests transfer within the same chart; some
   previously unseen cells may still need probing.
6. Inspect a few early, late, and holdout traces. Harbor stores per-step
   observations and notes in `steps/battle-NN/artifacts/`, and authoritative
   audit data plus numeric scores under each step's verifier output. Confirm
   damage, HP, drafting, forced replacements, and chart notes agree.
7. Use `play.py` to exercise commands yourself. Try duplicate drafts, switching
   to the active creature, and acting after a knockout. A new invocation starts
   an independent local battle; it cannot change a scored Harbor trial.

The baseline has persistent files and can learn. The offline memoryless policy
is a separate calibration control. A single real-model matrix gives directional
evidence; record the observed curves without requiring a particular ordering
between the three conditions or a strictly increasing score at every battle.

## Reproducibility limits

Task version 0.2.0 uses chart generator v2. It replaces the ineffective cyclic
table mixer with randomized backtracking over balanced rows, enforcing column
balance and distinct attack/defense profiles. This is not a uniform sampler over
all balanced charts. Across 1,000 seeds, all charts had six distinct rows and
columns, with 21 different pairwise-row-agreement signatures; that signature
is invariant under row/column permutations. The regression test failed on v1.
Results from v1 are not comparable to v2 calibration or oracle results.

Generated matchups are conditioned on oracle winnability. Report this when
comparing instances. Keep seeds, task version, model, Pi version, and job IDs
with results. The matrix runner fingerprints runnable task inputs and preserves
existing jobs. Fresh generated seeds are preferable for independent evaluation;
the checked-in seed is a public development fixture.

The first battle is initialized in the image. Root verification freezes its
result and prepares the next battle; agent-visible setup hooks only display the
current view. This fits Harbor's actual user permissions without granting the
agent any reset or grading capability.
