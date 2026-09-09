# ROADMAP 12 — the routing measurement that replaced a file count

**Run 2026-09-09** · `evals/run-desc-routing.py --cases evals/cases/skill-split-code-security.jsonl`
· `anthropic/claude-sonnet-5` · 12 cases · 3 samples · temp 0.7 · both arms ·
**pre-registered** in [PRE-REGISTRATION-SKILL-SPLIT-ROUTING.md](PRE-REGISTRATION-SKILL-SPLIT-ROUTING.md),
committed before any call · artifacts `skill-split-routing.json` (before) and
`skill-split-routing-after-fix.json` (after)

## The question

`sota-code-security` does two jobs under one `description`, which is the entire auto-load
classifier: `rules/01–09` name vulnerability **classes**, `rules/10–15` verify a
**control** does something. Item 12's trigger used to be a file count. It fired on
2026-09-06 and the answer was still no — the tell that a count was a **proxy**. The
replacement trigger, written 2026-09-07: split when a routing measurement shows the
combined description mis-classifies verification-shaped tasks.

## Result — run 1, as shipped

| half | correct-pick (with-xref) | correct-pick (without-xref) |
|---|---|---|
| vulnerability-class (6 cases) | **1.000** | 0.833 |
| control-verification (6 cases) | **0.500** | 0.333 |
| **gap** | **+0.500** | +0.500 |

Against the registered thresholds — verification ≤ 0.70, vulnerability ≥ 0.90, gap ≥ 0.20
— **H1 is met on all three**. The three misses were unanimous, 3/3 each, and all three
went to the **same** neighbour:

| case | picks |
|---|---|
| `c1_inert_gate` (a CI grep step that never fails) | `sota-shell-scripting` ×3 |
| `c3_empty_comparand` (a baseline comparison over an empty baseline) | `sota-shell-scripting` ×3 |
| `c5_audit_ledger` (a shell script writing an audit trail) | `sota-shell-scripting` ×3 |

**The classifier matched the artifact, not the question** — the same shape as
`r1_token_count` in v1.38.0, where it matched the noun ("instruction file") over the
question ("how many tokens"). Here the artifact is *a script*, and every one of the three
misses names one.

## The cheap fix, tried first because the pre-registration said so

The registration recorded, before any number existed, that a result in H1's direction does
**not** license a split: the cheap fix — verification vocabulary in the existing
description — gets tried and re-measured first, and only a **surviving** gap argues that
one description cannot carry two jobs.

The existing description already contained `silent failure`, `fail-open` and
`no-op control` and still lost, so keywords were not the missing piece. What was missing
was a clause **claiming the question shape against the artifact**:

```
— AND whenever a control is already PRESENT and the question is whether it enforces
anything (a gate that never fails, an empty comparand), even when that control lives
in a shell script, a CI step or a config file.
```

Room for it came from keywords the description already carried in prose (`file upload`
vs `uploads`, `tool-call security` vs `LLM agents or tool-calling`), near-duplicates
(`zip bomb` vs `decompression bomb`) and one owned by a neighbour (`threat model`).
Final length **1016 / 1024**.

## Result — run 2, after the fix

| half | correct-pick (with-xref) | change |
|---|---|---|
| vulnerability-class | **1.000** | unchanged — the trims cost nothing |
| control-verification | **0.611** | **+0.111** |
| gap | **+0.389** | −0.111 |

`c1_inert_gate` moved from 0/3 to **2/3**. `c3` and `c5` did not move at all: still
`sota-shell-scripting` 3/3 in both arms.

## Verdict: do NOT split, and the residual is not what H1 claimed

The numbers still clear H1's bar. The **reason** does not survive reading them.

`c3` and `c5` are a baseline-comparison script and a shell audit ledger. The router's own
cross-cutting **rule 17** says a script that produces or verifies evidence is a security
control written in shell and needs `sota-shell-scripting` **plus** `sota-code-security`
rules/10, 12 and 15. So for those two cases `sota-shell-scripting` is not a wrong answer —
it is a **correct and incomplete** one, and a pick-one instrument has no way to say so.

The pre-registration listed this exact limitation before the run (*"`expect` is a
judgement… a low score is evidence about the **description**, not proof the model was
wrong"*), which is the only reason invoking it now is not a moved goalpost.

So the residual gap supports **"a top-1 metric cannot adjudicate a task the router itself
routes to two skills"**, not **"one description cannot carry two jobs"**. That is not an
argument for a split.

## What ships, and what item 12 becomes

- **Shipped:** the description fix. +0.111 on the verification half, 0.000 cost on the
  vulnerability half, measured both ways.
- **Item 12 stays OPEN**, with a trigger that is now measured rather than asserted:
  re-run `c3` and `c5` through `evals/run-routing-recall.py`, whose **set** metric can
  express "both skills". **Split only if the set metric shows `sota-code-security`
  omitted** — that would be the description failing to claim a job it owns. If the set
  metric loads both, the top-1 residual was an artefact of the instrument and item 12
  closes.
- The count-based trigger is dead either way. It fired, twice, and was never the reason.

## What this does not establish

- One model, one day, `sonnet-5`. A routing number is a gap between a description and a
  classifier and the classifier side moves.
- 12 cases with hand-picked distractors: distractor-pick here is an upper bound on
  confusability, not a population estimate.
- The two halves are matched on surface, not on difficulty. If the verification tasks are
  simply more abstract, that confound is in the number and this design cannot remove it.
