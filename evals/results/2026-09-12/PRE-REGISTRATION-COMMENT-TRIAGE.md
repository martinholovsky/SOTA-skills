# Pre-registration — comment triage against AACR-Bench

**Written before any model call.** Thresholds, predictions and void conditions are fixed
here; the results document may not move them.

## The question

Does loading this library's finding-quality rules — `sota/rules/03` §2 (evidence
standard) and §4 (adversarial verification: *state it as a falsifiable claim, prompt to
refute, default to REFUTED when ambiguous*) — improve a model's ability to tell a **real**
code-review comment from a **wrong** one?

## Why it is worth spending on

The library's audit-accuracy axis was **closed at +0.00 across nine instruments**, and the
precision instrument behind that was 30 claims scoring **1.00 in both arms**. A measure
that saturates has not shown the treatment does nothing; it has shown it cannot tell.
AACR-Bench (Alibaba Aone, **Apache-2.0**) is externally annotated, 2,145 comments over 200
PRs / 50 repos / 10 languages, and its negatives were written by other people's reviewers
and models rather than by us.

## Design

- **Set**: `evals/cases/comment-triage.jsonl`, 40 cases, **20 label-0 / 20 label-1 by
  construction**, seeded draw over the full 2,145, ≤2 cases per PR, code context frozen in.
- **Arms**: `bare` (judging prompt alone) vs `with` (same prompt + the §2/§4 excerpt).
  Identical case, identical code context, identical scoring. The only difference is the
  guidance block.
- **Samples**: 3 per case per arm, temp 0.7 (this repo's noise floor is ±0.03 at n=1,
  temp 0; n=3 at 0.7 is the house default).
- **Scoring**: objective. The model emits `VERDICT: REAL` or `VERDICT: NOT_REAL`; a
  response matching neither is a parse failure, counted and reported, never silently
  dropped.
- **Primary metric**: accuracy on the balanced set. **Chance = 0.500 exactly**, which is
  the reason for balancing — the source set's 70/30 base rate would otherwise hand a
  constant answer 0.70.

## Registered thresholds

| outcome | rule |
|---|---|
| **H1 supported** | `with − bare` **≥ +0.05** |
| **null** | `\|with − bare\|` **< 0.03** |
| **ambiguous** | between 0.03 and 0.05 — reported as underpowered, not as a result |
| **H1 refuted** | `with − bare` **≤ −0.05** |

## The trap this registration exists to catch

`rules/03` §4 says *default the verdict to REFUTED when the evidence is ambiguous*. On a
balanced set that instruction can raise the score **purely by making the model more
skeptical** — more label-0 caught, more label-1 wrongly rejected — which is a **bias
shift, not a skill gain**, and it would look like a lift on accuracy alone.

So the confusion matrix is **pre-registered as a primary output, not a diagnostic**:

- Report per-class recall for **both** classes in both arms.
- **A lift is only claimed if the with-arm does not lose more than 0.05 of label-1
  recall** relative to bare. If accuracy rises while label-1 recall falls past that, the
  registered conclusion is **"the guidance shifts the threshold, it does not improve
  discrimination"** — and that is reported as the finding.

## Void conditions

1. **Either arm ≥ 0.95 accuracy** → saturated, no lift claimable, same verdict as the
   instruments this set was built to replace.
2. **Parse failures > 10%** of calls in either arm → the harness is measuring its own
   prompt, void and fix.
3. **The two arms produce byte-identical prompts** → asserted in code before spending.

## Predictions (recorded so they can be wrong)

- Bare will land **0.60–0.75**. These are expert-labelled comments where roughly half the
  negatives are plausible-sounding AI output, which is the hard case for a model.
- The with-arm gains, but **modestly (+0.02 to +0.08)**, and the honest risk is the
  skepticism shift above rather than a null.
- **Prediction recorded 2026-09-12 before the first call.**

## What this cannot establish

One model, one day, 40 of 2,145 records, at a 28/12 AI/human comment mix. It measures
comment *triage*, which is the refutation half of an audit — not defect *discovery*.
