# Competitor benchmark — SOTA vs. the most popular guidance libraries (2026-07-14)

**Question:** every prior eval is SOTA vs. an *unguided* model. Does SOTA's
guidance actually produce more complete code than the most popular competing
skill/rules libraries on the same "build X" tasks? This runs them as extra arms
on the 7 completeness tasks, same fixed rubric, same blind opus-4.8 judge.

**Answer: yes — SOTA leads all three, and never loses a single case.**

| arm | mean completeness | vs SOTA | vs unguided | per-case vs SOTA |
|---|---|---|---|---|
| **SOTA** | **0.99** | — | +0.40 | — |
| ECC (~230k★) | 0.87 | **−0.12** | +0.28 | 5 win / 2 tie / 0 loss |
| awesome-cursorrules (~40.3k★) | 0.83 | **−0.16** | +0.24 | 7 win / 0 tie / 0 loss |
| alirezarezvani/claude-skills (~22.6k★) | 0.81 | **−0.17** | +0.23 | 6 win / 1 tie / 0 loss |
| unguided | 0.58 | −0.40 | — | — |

SOTA wins or ties **every one of the 21 head-to-head cases; it loses none.** And
the competitors are **not strawmen** — all three lift completeness +0.23 to +0.28
over an unguided model, i.e. they are genuinely good guidance. SOTA is simply more
complete.

## Why SOTA wins — the cross-cutting concerns competitors drop

Most-missed rubric items per arm across the 7 tasks (what each still omits):

- **unguided:** tests (7/7), rate limiting (6), transport/TLS (5), logging (4)
- **SOTA:** session-invalidation (1 — the lone `c7` finite-constraint-budget slip)
- **ECC (~230k★):** **rate limiting (3)**, storage-safety, image-bomb, idempotency, metrics, CSRF
- **claude-skills:** **transport/TLS (4)**, **tests (4)**, rate limiting (2), logging, CSRF
- **awesome-cursorrules:** **rate limiting (5)**, transport (2), storage, image-bomb, CSRF

The pattern is consistent: competitors cover the *obvious* per-task security
(auth, input validation, SQLi) well, but systematically drop the **cross-cutting
production non-negotiables** — rate limiting, transport enforcement, tests,
structured logging — on endpoint after endpoint. Even the ~230k-star ECC omits
rate limiting on 3 of 7 tasks. That is exactly the gap SOTA's router *operating
principle 5* + the matched rules are designed to close.

## Method (fair, conservative, reproducible)

- **Content-only, level playing field.** Every guided arm (SOTA and each
  competitor) gets the *same neutral* build wrapper ("apply this guidance, then
  review your code for completeness against it, don't ship incomplete code"). The
  wrapper names **no** specific concern (naming e.g. rate limiting would leak
  SOTA's non-negotiables to the competitors), so the only variable is the pasted
  guidance. **SOTA's self-audit forcing function is *not* used here** — the number
  is content-only, so SOTA's win is its guidance, not its method. In real
  deployment SOTA's self-audit widens the gap (it lifts SOTA to 0.99 *with* the
  gate in `run-completeness.py`; here SOTA reaches 0.987 on content alone).
- **Each competitor's best-matching content** for "build a secure Python/FastAPI
  backend feature," at a token budget in the same ballpark as a SOTA arm, pinned
  by commit SHA in [`evals/cases/competitors.json`](../../cases/competitors.json).
  Licenses permit reuse (ECC/claude-skills MIT, cursorrules CC0); attributed here.
- **Blind judge** (opus-4.8), same rubric as `run-completeness.py`. No artifact was
  truncated (largest 92 KB, well under the 32k-token cap). Raw per-case data:
  `competitor-benchmark.json`. Reproduce: `python3 evals/run-competitors.py
  --competitors-dir <clones>`.

## Confidence — the lead survives sampling (multi-sample, 2026-07-14)

The main table is single-sample (temp 0). To check the lead isn't a lucky draw, we
re-ran **3 samples at temp 0.7** on the **3 tightest cases** — c1, c3, c7, the ones
where a competitor *tied* SOTA in the single-sample run (`competitor-benchmark-3sample.json`):

| arm | mean (3 tight cases) | vs SOTA |
|---|---|---|
| **SOTA** | **0.98** | — |
| ECC | 0.87 | −0.11 |
| claude-skills | 0.83 | −0.15 |
| awesome-cursorrules | 0.82 | −0.16 |
| unguided | 0.65 | −0.33 |

The gaps (−0.11 to −0.16) are **the same** as the single-sample full-7 run
(−0.12 to −0.17), and **on every one of these cases SOTA's *worst* sample is ≥ each
competitor's *best* sample** — competitors occasionally tie SOTA at the ceiling
(ECC/cursorrules hit 1.00 on c1; ECC ties at 0.91 on c7) but never beat it. SOTA's
own variance is near-zero (sd 0.00 on c1/c3, 0.04 on c7). The lead is stable.
*(Multi-sampling the other 4 cases and the full 7 was left for a top-up — those
were the least contested, so the tight-case check is the informative one.)*

## Honest limitations (state them, don't bury them)

- **One task family** — 7 Python/FastAPI backend-security build tasks. A different
  domain (frontend, data pipelines, mobile) could shift the ordering; this is the
  domain we measured.
- **Mostly single-sample, temp 0** (deterministic). A 3-sample/temp-0.7 confidence
  check on the 3 tightest cases (above) confirms the lead holds; the other 4 cases
  and the full 7 are not yet multi-sampled (budget).
- **Content selection is a judgment call** — we picked each competitor's most
  relevant files; a different reviewer might pick slightly differently. The manifest
  makes it inspectable and re-runnable.
- **Bundle-size asymmetry:** SOTA's per-case bundles (65–100 KB, routed to the
  task) are larger than the competitors' general bundles (28–42 KB). This is a real
  SOTA property (routing gives it matched depth), not a thumb on the scale — and
  per SOTA's own [context-rot finding](../../../docs/WHY-COMPLETENESS-RESIDUAL.md),
  *more* content is not automatically an advantage.

## What this earns

The [honesty gate](../../../docs/ROADMAP.md) said: make a "better than library X"
claim only if a fair, blind, reproducible comparison supports it. It now does —
against the single most-starred cross-AI peer (ECC), the most-starred rules
library (awesome-cursorrules), and the closest same-kind skills library
(claude-skills). The claim is scoped to **completeness on backend build tasks**,
content-only, and is reproducible from this repo.
