# Pre-registration — the placebo arm (completeness)

Written 2026-10-07, **before any spend**. Source: an outside review's "verbosity / format
confounder". Its claim: the completeness lift measures "did the model output the boilerplate
we commanded", not the library.

## Question

How much of the completeness lift is the **library**, and how much is merely **being asked
for more**? The existing controls only half-answer it:
- a competing "skip the extras, no tests" prompt (+0.509) shows the library holds under
  pressure;
- the competing-library head-to-head (98.7% vs 84.9%) shows other guidance scores lower.

Neither gives the unguided model a plain instruction to be complete.

## Design (frozen)

- **Arm:** `placebo`. No library and no router text, only `PLACEBO_INSTRUCTION` before the
  task. sha256[:16] of the wording: `42c55f8c6fc102f3`. It is guarded against naming any rubric
  vocabulary (`PLACEBO_FORBIDDEN`), so it cannot act as a weak treatment arm.
- **Cases:** `evals/cases/completeness.jsonl`, all 7 (all Python).
- **Build and judge:** `anthropic/claude-sonnet-4.6` builds, `anthropic/claude-opus-4.8`
  judges, 3 samples, temp 0.7, max-tokens 32000. This is the configuration of the recorded
  2026-09-23 runs.
- **Run:** `python3 evals/run-completeness.py --placebo-only --samples 3 --temp 0.7
  --out evals/results/2026-10-07/placebo.json`.
- **Comparison:** the recorded 2026-09-23 runs (r1, r2) on the same model ids, judge and rubric:
  **without = 0.578, with = 0.982**, the mean of the two. The placebo arm never sees the
  router, so today's router edits cannot touch it.

## Predictions and falsifiers

- **H1 (the library is not just "asked for more"):** placebo ≤ **0.83**, so library over
  placebo ≥ +0.15.
- **Falsified if** placebo ≥ **0.90**, within 0.08 of the with-arm. In that case most of the
  lift is the instruction to be complete, and README, WHY-IT-WORKS and RESULTS must say so.
- **Between 0.83 and 0.90:** reported as *partial*. The lift is part instruction and part
  library, with each share stated.
- **What makes the run measure nothing:**
  - **a truncated artifact**, which scores as a floor. Check the `len` column against the cap.
  - **a judge that marks everything present.** The rubric and judge are unchanged from the
    runs that produced 0.578, so this is only a risk if the placebo saturates.
  - **a model-id alias that has moved since 2026-09-23.** Recorded as a limit, because it
    cannot be checked from here.

## Cost and gate

Estimated **$3–5** for 21 builds and 21 judge calls. That's unverified: the runner records
no cost, and the estimate is from list prices. Credit remaining on 2026-10-07: $7.97. **It runs
only on the operator's go-ahead**, because spend is the operator's decision.
