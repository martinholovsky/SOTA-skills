# Pre-registration — ROADMAP 32: separating "lean" from "lean plus the gate"

**Written and pushed 2026-09-06, BEFORE the run.** Nothing has been executed against a
live model for this question. The arm and both its guards exist and were watched to
fail; the API spend has not been made.

The reason for writing this first is specific to this experiment. Item 25's padded run
returned **−0.01**, and that number has already been *interpreted* in this repo — as
"context is not the constraint". If the follow-up runs before the prediction is
recorded, whatever comes back will read as confirmation of whichever half of the
sentence survives. So the numbers are below.

## What item 25 actually measured

`--pad-rules 400` adds 400 lines of genuine rules prose from skills the case does **not**
load (routing signal stripped) to the with-library arm, and asks whether competing
guidance degrades rule *application*. It read **−0.01** across 7 tasks.

The confound, found on the way out and left open as item 32: **that arm also carried
`BUILD_WORKFLOW`** — the four-step build workflow whose step 4 is the terminal
self-audit re-read, and whose entire documented job is recovering the cross-cutting
concerns a model drops under a long, dense task. Measured as the bulk of the library's
completeness lift.

So −0.01 supports *"lean **plus a terminal re-read** is robust to competing context"*.
It says nothing about context length on its own, and the two are worth separating —
because if the gate is what absorbs the padding, that is a considerably stronger
argument for step 4 than anything this project currently publishes.

## The arms

Four, on the existing 7 completeness cases, `--pad-rules 400 --no-gate-arm`:

| Arm | Rules context | `BUILD_WORKFLOW` | What it is for |
|---|---|---|---|
| `without` | none | — | the floor |
| `with` | the case's own skills | yes | the published baseline (0.62 → 1.00, +0.38 on `sonnet-5`) |
| `with+pad` | + 400 lines of unrelated rules | yes | item 25's arm, reproduced |
| `pad-nogate` | + 400 lines of unrelated rules | **no** | **the new arm** — the question |

The runner reports `GATE-ABSORPTION = mean(with+pad) − mean(pad-nogate)`: what the
terminal re-read recovers *under competing context*.

## Predictions, with numbers

**H1 — the gate absorbs it.** `pad-nogate` drops relative to `with`, and `with+pad`
does not. Threshold: **GATE-ABSORPTION ≥ +0.05**, with `pad-nogate` at least 0.05 below
`with`. This is the honest prediction and the one the roadmap row states.

**H0 — context length was never the constraint.** `pad-nogate` holds within noise of
`with`, and GATE-ABSORPTION lands in **[−0.03, +0.03]**. Then item 25's −0.01 *was* a
statement about context length, and the "load lean" framing loses its remaining
empirical support at this padding size.

**H2 — the padding hurts regardless.** Both padded arms drop by ≥ 0.05. Then the gate
is not sufficient either, and step 4 is oversold.

### The falsification condition, stated before the run

**H1 is refuted if GATE-ABSORPTION < +0.05.** I will not rescue it by raising the
padding, changing the model, or re-reading the rubric — those are separate experiments
needing their own pre-registration. If H1 misses, the roadmap row saying "the honest
one is that the gate absorbs it" is wrong and gets corrected in place.

## What could make this measure nothing

Recorded now so it cannot be discovered afterwards as an explanation for an
inconvenient result:

- **The noise floor is ±0.03 at n=1**, measured, and temperature 0 is *not*
  deterministic in this harness. A GATE-ABSORPTION of +0.02 is not a finding. Any
  result inside [−0.03, +0.03] is reported as a null, not as a direction.
- **A ceiling.** The `with` arm scores **1.00** on `sonnet-5`. An arm at the ceiling
  cannot show the gate *adding* anything, so GATE-ABSORPTION can only be produced by
  `pad-nogate` falling. If `pad-nogate` also reads 1.00, this experiment is
  uninformative rather than a null, and must be reported that way.
- **An inert ablation.** The runner aborts if the `pad-nogate` prompt is byte-identical
  to the gated one, and `--no-gate-arm` without `--pad-rules` aborts too. Both guards
  were watched to fail on 2026-09-06 — the first by running the flag alone, the second
  by making the ablation a no-op and confirming it refuses (an earlier attempt at that
  second probe did not land its own mutation and reported a false pass; the assertion
  it was testing is what caught it).
- **Padding that is not competing.** `rules_padding` already refuses to include the
  case's own files. It does not guarantee the padding is *contradictory*, only
  unrelated — so this measures dilution, not conflict, and the write-up must say so.

## Cost and status

7 cases × 4 arms = **28 build calls + 28 judge calls**, on top of the 21 the three-arm
form already costs. Not yet run: this is live model spend on the operator's account and
is theirs to authorise.

**Do not fold the result into item 25.** It is a different question, and item 25's
number stands as published.
