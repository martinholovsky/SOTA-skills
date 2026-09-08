# The regression set caught a live regression on its second run

**Date:** 2026-09-08 · **Instrument:** `evals/run-desc-routing.py --cases
evals/cases/desc-routing-regressions.jsonl` · **Model:** `anthropic/claude-sonnet-5` ·
**Samples:** 3 per case per arm · **Temp:** 0.0 · **Cases:** 2 · **Arms:** with-xref /
without-xref

This is a **regression set, not a measurement set**. Selection by outcome is the point here
and would be a defect in a measurement set, so these numbers must never be averaged into the
A/B in `desc-routing.jsonl` (`sota-llm-engineering` rules/01 §8).

## Why it ran

`r2_absence_sweep` was added in v1.36.2 to pin a routing fix and shipped **unrun** — the
before/after cost live calls that had not been authorised, and the entry said so rather than
assuming the number. Running it was authorised on 2026-09-08.

## Result

| case | arm | run 1 | run 2 (after the fix below) |
|---|---|---|---|
| `r1_token_count` | with-xref | **0.67** — picks: skill-security, llm-engineering, llm-engineering | **1.00** |
| `r1_token_count` | without-xref | **0.00** — picks: skill-security ×3 | **1.00** |
| `r2_absence_sweep` | with-xref | **1.00** — shell-scripting ×3 | **1.00** |
| `r2_absence_sweep` | without-xref | **1.00** — shell-scripting ×3 | **1.00** |
| summary | with-xref | 0.833 | **1.000** |
| summary | without-xref | 0.500 | **1.000** |

Distractor-pick was 0.000 everywhere, in both runs.

**`r2_absence_sweep` passes 3/3 in both arms**, which is what it was written to pin: the
v1.36.2 description rewrite routes an ad-hoc-sweep question to `sota-shell-scripting`. Note
what it does *not* show — both arms score 1.00, so this case says nothing about
cross-references. That is correct rather than disappointing: the v1.36.2 fix was to the
**description**, which both arms carry.

## The finding: `r1_token_count` had regressed, and had been regressed for a day

`r1` was pinned on 2026-08-27 reading `sota-llm-engineering` **3/3**. On this run the
without-xref arm read `sota-skill-security` **3/3** — a complete inversion.

**Cause, established by reading the two descriptions rather than inferring:**

| token in r1's task | `sota-skill-security` | `sota-llm-engineering` |
|---|---|---|
| "instruction file" | **2** occurrences | **0** |
| "token" | 0 | 7 |
| "budget" | 0 | 8 |

`sota-skill-security` shipped in **v1.35.0 (2026-09-07)** and owns *"any skill, plugin,
ruleset or agent file an agent loads as instructions"*. r1's task asks *"How many tokens is
this 484-line Markdown **instruction file**? … compare it against the recommended size
**budget**"*. **The classifier matched the noun and not the question**: the new skill claims
the object, the correct skill claims the measurement, and the object won.

This is the cost of adding a skill that no static check can see. Invariants 4, 7 and 15
verify a description exists, is short enough and is indexed; **nothing checks whether it
takes traffic from a neighbour**, and the only instrument that could was a regression set
nobody had run.

## Fix

One keyword, on the side that owns the *question*: `instruction file size` added to
`sota-llm-engineering`'s trigger list (description 998 → **1021** chars, cap 1024 —
invariant 4 re-run). No change to `sota-skill-security`, which is correct about its own
subject. Re-run: **1.00 in both arms, both cases.**

## Honest limits

- **n=3 per case per arm.** Enough to see 0/3 invert to 3/3; not a precision estimate.
- **Run 1 is not a clean "before" for r2** — it is after v1.36.2 shipped. r2 has no
  measured pre-fix arm, and the entry in `evals/README.md` should keep saying so.
- **The r1 regression was found, not predicted.** It had been live since v1.35.0 and was
  invisible for a day because the set is run explicitly, never in CI.
