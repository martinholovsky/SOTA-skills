# Routing regression run for the `sota-code-security` description change

**2026-09-09** · `evals/run-desc-routing.py --samples 3 --temp 0.0 --cases
evals/cases/desc-routing-regressions.jsonl` · `anthropic/claude-sonnet-5` · both arms ·
artifact `desc-routing-regressions.json`

This is the run `RELEASING.md` §2c prescribes and **invariant 29** gates. It was triggered
by this session's edit to `sota-code-security`'s `description` (ROADMAP 12): a clause
claiming the control-verification question, paid for by trimming ten keywords the
description already carried in prose or that a neighbouring skill owns.

A description is the whole auto-load classifier, so **trimming** a keyword is as much a
routing change as adding one — that is the half a "did you add a skill?" check would miss.

## Result — no regression

| case | arm | picks | correct |
|---|---|---|---|
| `r1_token_count` | with-xref | `sota-llm-engineering` ×3 | **1.00** |
| `r1_token_count` | without-xref | `sota-llm-engineering` ×3 | **1.00** |
| `r2_absence_sweep` | with-xref | `sota-shell-scripting` ×3 | **1.00** |
| `r2_absence_sweep` | without-xref | `sota-shell-scripting` ×3 | **1.00** |
| summary | both arms | — | **1.000**, distractor-pick **0.000** |

`r1_token_count` pins the v1.38.0 fix (the classifier had matched *"instruction file"* over
*"how many tokens"*); it still holds. `r2_absence_sweep` pins the v1.36.2 fix routing an
ad-hoc-sweep question to `sota-shell-scripting` — worth watching here in particular,
because this session's edit pushed `sota-code-security` **towards** shell-shaped and
CI-shaped tasks. It did not take `r2`'s traffic.

## What this does not cover

Two regression cases is two regression cases. The set pins the mis-routes that have
actually happened; it cannot tell you about a neighbour whose traffic has never been
measured. The broader composition check is `run-routing-recall.py`, run the same day at
**recall 0.975** — unchanged from before this edit, so the trims cost the set metric
nothing either.
