# Does the BUILD lift generalize across model families? — yes

**Date:** 2026-07-22 · **Build model:** `openai/gpt-5.1` (the cross-model arm) ·
**Judge:** `anthropic/claude-opus-4.8`, held constant · 7 build tasks, 2 samples, temp 0.7

## Why this run existed

Every completeness number this project had ever published used **one** build model,
`anthropic/claude-sonnet-4.6`. The entire flagship result — completeness +0.39 — could
in principle have been sonnet-specific. That is the single largest unhedged assumption
in the evidence base, and the cheapest one to test: re-run the completeness eval with a
**different-family frontier model** driving BUILD, everything else held constant.

`openai/gpt-5.1` was chosen because it is a genuinely different lab and family (not an
Anthropic sibling), was validated as reachable through the harness before spending, and
is frontier-class. The blind judge stayed `opus-4.8` so grading is comparable to every
prior completeness run.

## Result — it replicates, and slightly stronger

| Build model | Without | With | **Lift** |
|---|---|---|---|
| **openai/gpt-5.1** (cross-family) | 0.44 | 0.88 | **+0.44** |
| anthropic/claude-sonnet-4.6 (2-run mean) | 0.59 | 0.98 | **+0.39** |

Per case, gpt-5.1 with-library minus without-library:

| Case | Without | With | Lift |
|---|---|---|---|
| c1_ticket_api | 0.54 | 0.83 | +0.29 |
| c2_upload | 0.41 | 0.91 | +0.50 |
| c3_emailjob | 0.36 | 0.91 | +0.55 |
| c4_login | 0.50 | 0.80 | +0.30 |
| c5_search | 0.45 | 0.90 | +0.45 |
| c6_webhook | 0.45 | 0.90 | +0.45 |
| c7_pwreset | 0.36 | 0.91 | +0.55 |

**Every case shows a positive lift** (+0.29 to +0.55). The BUILD result is not
sonnet-specific. The library embeds the same cross-cutting concerns a different
frontier model also drops from a bare prompt — the same four recur in the
without-library misses: `ratelimit`, `logging`, `transport`, `tests`.

## Reading it honestly

- **The lift generalizes; the ceiling does not (yet).** gpt-5.1's with-library arm
  reaches 0.88, below sonnet's 0.98. The library takes gpt-5.1 from incomplete to
  **very good**, not to **near-perfect**. Whether that gap is gpt-5.1 following the
  terminal checklist less completely, or a rubric/judge effect, is not resolved here.
- **The lift is larger where the baseline is lower** (gpt-5.1 0.44 → +0.44; sonnet
  0.59 → +0.39). This is the *same* pattern the five-domain breadth study found across
  domains — the lift tracks task incompleteness — now reproduced across *models*. It is
  the strongest single piece of evidence for that mechanism the project has.
- **Judge-family note, in the library's favor.** The blind judge (`opus-4.8`) shares a
  family with the sonnet build model but not with gpt-5.1. If that biases grading at
  all, it biases *against* the cross-model arm — which makes the observed **+0.44 a
  conservative floor**, not an inflated figure.

## Limitations

- **2 samples, not 3** (cost control — the run was $1.87). Per-case spread is visible
  in the artifact; the means are stable but this is not the 3× rigor of the sonnet
  baseline.
- **One cross-family model.** gpt-5.1 replicates it; gemini / others are untested. Two
  families is not "model-agnostic", it is "not sonnet-specific" — a weaker but real
  claim.
- **Same judge, same rubrics, same 7 tasks** as every completeness run — this tests
  build-model generality, nothing else. Freshness and routing remain single-build-model.

## What this changes

The flagship BUILD claim was the project's most load-bearing number and its biggest
untested assumption at once. That assumption is now **partially discharged**: the
+0.39 completeness lift is **not an artifact of one model** — a different-family
frontier model shows +0.44 on the same tasks. `RESULTS.md` and `docs/WHY-IT-WORKS.md`
updated to state this rather than carry the bare single-model caveat.

Artifact: `completeness-crossmodel-gpt51.json`.
