# ROADMAP 32 — separating "lean" from "lean plus the gate"

**Run 2026-09-06/07** · `run-completeness.py --pad-rules 400 --no-gate-arm` ·
`anthropic/claude-sonnet-4.6` build, `anthropic/claude-opus-4.8` judge · 7 tasks, 1 sample,
temp 0 · artifact `completeness-gate-absorption.json` ·
**pre-registered** in [PRE-REGISTRATION.md](PRE-REGISTRATION.md) and committed before any spend

## Result

| Arm | Rules context | `BUILD_WORKFLOW` | Mean |
|---|---|---|---|
| `without` | none | — | 0.60 |
| `with` | the case's own skills | yes | **1.00** |
| `with+pad` | + 400 lines of unrelated rules | yes | **0.97** |
| `pad-nogate` | + 400 lines of unrelated rules | **no** | **0.93** |

```
PAD-DELTA        = -0.03   (padding costs this much WITH the gate)
NOGATE-DELTA     = -0.07   (padding costs this much WITHOUT the gate)
GATE-ABSORPTION  = +0.04   (what the terminal self-audit recovers under competing context)
```

## Verdict against the registered thresholds

**H1 is refuted by the rule I registered.** It required `GATE-ABSORPTION ≥ +0.05`; the
measurement is **+0.04**. Its second condition — `pad-nogate` at least 0.05 below `with` —
*was* met (0.07). H0 required the result inside `[−0.03, +0.03]`; +0.04 is outside that too.

**So the result lands in the dead zone between my own two bands.** That is not a clean
null and I am not going to present it as one. It is an **underpowered experiment**: the
effect is in H1's predicted direction, of roughly the predicted shape, and too small to
bank at n=1 with a measured noise floor of ±0.03.

The pre-registration said I would not rescue H1 by raising the padding, changing the model
or re-reading the rubric. I am not doing any of those.

## What can honestly be said

- **The ceiling worry did not materialise.** I registered the risk that `pad-nogate` would
  also read 1.00, making the run *uninformative rather than null*. It read **0.93** — the
  arm moved, so the experiment did measure something.
- **Item 25 replicates.** Its `with+pad` was −0.01; here it is **−0.03**, same direction,
  same order of magnitude, on the same model.
- **Removing the terminal self-audit under competing context costs −0.07**, more than twice
  what the padding costs when the gate is present (−0.03). Directionally this supports
  *"lean plus a terminal re-read is robust"* over *"context length is free"* — but the
  margin is one noise-floor wide and must not be quoted as a lift.
- **Per case**, the ungated arm lost ground on 2 of 7 (`c3_emailjob` −0.09, `c4_login`
  −0.10) and was unchanged on 5. So a single-sample mean is carrying two observations.

## What would settle it

More samples at temp 0.7 (n ≥ 3), which is what this repo's own convention already says a
single-sample temp-0 result cannot substitute for. **That is a new experiment and needs its
own pre-registration** — the numbers above stay as published either way.

## Superseded 2026-09-10 — the follow-up ran, and one claim above does not survive

The n≥3 / temp-0.7 experiment this write-up called for was pre-registered and run:
[../2026-09-09/GATE-ABSORPTION-N3.md](../2026-09-09/GATE-ABSORPTION-N3.md). **H1 is
confirmed** — `GATE-ABSORPTION` **+0.062**, SE 0.019, 95% CI **[+0.024, +0.099]**, against
the same **+0.05** threshold registered here and deliberately never moved.

Everything above stands as published, with one exception that is corrected there rather
than edited here: **"Item 25 replicates" no longer holds at that power.** This run's
`with+pad` cost −0.03; at n=3 / temp 0.7 PAD-DELTA is **+0.01**, so with the gate on, 400
lines of competing rules prose cost nothing measurable. The −0.03 above was one
noise-floor wide and is exactly the kind of number this project's own conventions say not
to quote — including when it is convenient, as it was here.

## Status

**ROADMAP 32 is closed as measured-and-underpowered, not as answered.** The confound item
25 left behind is now quantified rather than hypothetical: the padded arm's −0.01/−0.03
*was* measured with the gate active, and turning the gate off does cost more. How much more
is not established at this power.
