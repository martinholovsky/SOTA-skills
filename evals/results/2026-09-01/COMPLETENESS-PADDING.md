# Does competing guidance cost *rule application*? — ROADMAP 25, completeness half

**Date:** 2026-09-01 · **Build:** `anthropic/claude-sonnet-4.6` · **Judge:**
`anthropic/claude-opus-4.8` (blind) · **Runner:** `evals/run-completeness.py --pad-rules 400`
· **Artifact:** `completeness-padding.json` · 7 tasks, 1 sample, temp 0.

## The question

ROADMAP 25's routing half asked whether real competing guidance in the router degrades
*retrieval*, and read **null** (0.992 vs base 1.000, 2026-08-27) — but published its own
limit: routing is retrieval-ish, its table sits in the prompt, and the metric is at ceiling.
The half that mattered was **rule application under a long build**, and it was untouched.

It mattered because this project had been asserting an answer to it. `sota/rules/02` §1 said
a long context of similar-looking guidance *"measurably reduces how many rules the model
applies"*, and the router's BUILD step 2 said the same. Neither had a run behind it.

## Method

Three arms per task, same judge, same rubric:

| arm | rules context |
|---|---|
| `without` | nothing — the bare task |
| `with` | the case's own rules files + principle 5 + the BUILD self-audit |
| `with+pad` | the same, **plus 400 lines of genuine rules prose from skills the case does not load** |

The padding is real guidance, not filler — dense imperative prose of exactly the kind that
competes for attention. Every routing signal is stripped (`sota-*` names, `rules/NN`) and the
absence is **asserted**, so the padded arm cannot differ by retrieval, only by attention.
Guards refuse a short corpus, a leaked skill name, or padding drawn from the case's own files.

## Result

| case | without | with | **with+pad** | pad-delta |
|---|--:|--:|--:|--:|
| c1_ticket_api | 0.67 | 1.00 | **1.00** | +0.00 |
| c2_upload | 0.64 | 1.00 | **0.91** | **−0.09** |
| c3_emailjob | 0.73 | 1.00 | **1.00** | +0.00 |
| c4_login | 0.50 | 1.00 | **1.00** | +0.00 |
| c5_search | 0.60 | 1.00 | **1.00** | +0.00 |
| c6_webhook | 0.50 | 1.00 | **1.00** | +0.00 |
| c7_pwreset | 0.64 | 1.00 | **1.00** | +0.00 |
| **mean** | **0.61** | **1.00** | **0.99** | **−0.01** |

The library lift re-baselines at **+0.39** (0.61 → 1.00), which is the 2026-08-26 treatment
arm's first clean measurement and matches the original +0.39 on this model.

**Six of seven cases are unchanged.** The single move is `c2_upload`, which lost exactly one
criterion of eleven (`reencode` — re-encoding an uploaded image rather than trusting its
declared type). One criterion, one case, one sample.

## What it says

**The null is the finding, and it lands on us.** Four hundred lines of genuine competing
guidance cost **−0.01** in rule application. `sota/rules/02` §1 and the router's BUILD step 2
both asserted a measurable degradation; neither had measured it, and the measurement does not
support it. Both have been corrected rather than quietly left standing.

**Where the original claim came from, and why the generalisation failed.** It was extrapolated
from [WHY-COMPLETENESS-RESIDUAL](../../../docs/WHY-COMPLETENESS-RESIDUAL.md), where adding a
**relevant** rule to a checklist made application *worse* and a short reminder fixed it. That
result stands and is not challenged here. The step from "adding a relevant rule can hurt" to
"any extra context reduces applied rules" is the part that was never tested, and it is the
part that failed.

**The most useful reading is conditional.** The padded arm ran **with the step-4 self-audit
active** — the terminal re-read that exists precisely to recover dropped cross-cutting
concerns. So the defensible claim is *"lean plus a terminal re-read is robust to 400 lines of
competing context"*, not *"context length is free"*. Nobody has run padding with the gate
**off**, and that is the experiment that would separate the two.

## Limits

- **The `with` arm is at ceiling** (1.00 on all seven). The metric can show a drop — `c2` did
  — but it cannot show an improvement, and a ceiling compresses whatever effect exists.
- **One padding size.** 400 lines was chosen to match the routing half so the two are
  comparable. 800 or 1,600 might read differently, and this run does not exclude that.
- **One sample per cell at temp 0**, so a −0.09 on one case is a single observation, not a
  rate. Per `sota/rules/03` §2 it is not enough to build on; it is enough to refuse a claim
  in the opposite direction.
- **The gate was on.** See above — this measures lean-plus-gate, not lean alone.
- **One model, one judge, seven tasks.**

## Status

**ROADMAP item 25 is closed.** Both halves now read null: real competing guidance is
indistinguishable from inert filler on routing (2026-08-27), and costs −0.01 on rule
application (this run). What remains open is a *different* question the run surfaced — the
same padding with the self-audit gate disabled — recorded as its own item rather than folded
into a closed one.
