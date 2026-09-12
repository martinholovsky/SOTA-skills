# Pre-registration — ROADMAP 48: does routing survive a change of task shape?

**Written 2026-09-12, BEFORE any model call**, committed before the run. The runner and the
four cases were written first and the arms asserted to differ; nothing has been scored.

## The claim being tested

Four independent observations say the skill set gets fixed by a session's opening frame and
is not revisited when the work moves — and none of them is a trigger defect: the description
matched, the rule existed, it was simply never loaded. This asks whether that reproduces.

## Design

Two arms over the **same** shape-B prompt and the **same** catalogue:

| arm | context | role |
|---|---|---|
| **fresh** | the shape-B prompt alone | the ceiling — what `run-desc-routing.py` measures |
| **shifted** | two turns of genuine shape-A work, then the identical prompt | the treatment |

**ROUTING-SHIFT = fresh − shifted.** Objective scoring: exact skill-name match, no judge.
4 cases × 2 arms × **3 samples**, temp 0.7, `claude-sonnet-4.6`. 24 calls.

Cases derive one-to-one from the four recorded observations — docs→shell verification,
docs→test-suite diagnosis, shell→CI/gate reproduction, build→evidence-script verification.
None was invented to be hard and none selected by a model's score.

## Thresholds, fixed now

- **ROUTING-SHIFT ≥ +0.25** — the effect reproduces; routing is frame-dependent and the
  re-injection clause shipped in v1.40.4 has something real to do.
- **|ROUTING-SHIFT| < 0.25** — not reproduced *at this size*. With 4 cases one case is 0.25,
  so nothing finer is interpretable and I will not pretend otherwise.
- **ROUTING-SHIFT ≤ −0.25** — prior context *helps* routing, which would be worth more than
  the original claim.

## Prediction, recorded before seeing anything

**ROUTING-SHIFT ≥ +0.25.** Four field observations is a lot of smoke. But the observations
come from sessions with a Skill tool and real cost to re-routing, and this harness has
neither, so I hold it loosely.

## The risk that would void the reading, stated first

**A ceiling/floor squeeze.** `run-desc-routing`'s fresh arm scores ~0.90 on its own cases. If
the **fresh** arm here is not clearly high, a small delta is a floor artefact rather than a
null — **read the fresh arm before the delta**. Conversely if both arms sit at 1.00 the
instrument had no room to show anything and the run bounds nothing.

## What it cannot establish

1. **It measures what the model *says* applies, not what it loads.** No Skill tool exists in
   an eval. Same proxy `run-desc-routing` already publishes on; labelled, not hidden.
2. **4 cases, one model, one day.** A direction at best.
3. **Two prior turns is a weak frame** compared with the real sessions, which ran for hours.
   A null here does not clear the real behaviour — it bounds what two turns can do.

## Status

Not yet run.
