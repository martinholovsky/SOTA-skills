# Competitor benchmark — SOTA vs. the most popular guidance libraries (2026-07-14)

**Question:** every prior eval is SOTA vs. an *unguided* model. Does SOTA's
guidance actually produce more complete code than the most popular competing
skill/rules libraries on the same "build X" tasks? This runs them as extra arms
on the 7 completeness tasks, same fixed rubric, same blind opus-4.8 judge.

**Answer: yes — [SOTA-skills](https://github.com/martinholovsky/SOTA-skills) leads
all three, and never loses a single case.** Scores are % of a fixed best-practice
rubric the generated code implements (blind-judged); higher is better.

| Library | Completeness | vs SOTA-skills | vs unguided | This library vs SOTA-skills — won / tied / lost¹ |
|---|---|---|---|---|
| [**SOTA-skills**](https://github.com/martinholovsky/SOTA-skills) | **99%** | — | +40 pts | — |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) (~230k★) | 87% | **−12 pts** | +28 pts | 0 / 2 / 5 |
| [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) (~40.3k★) | 83% | **−16 pts** | +24 pts | 0 / 0 / 7 |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) (~22.6k★) | 81% | **−17 pts** | +23 pts | 0 / 1 / 6 |
| unguided | 58% | −40 pts | — | — |

¹ Read on each library's own row: how many of the 7 build tasks *that library*
won / tied / lost against SOTA-skills (single-sample). `0 / 2 / 5` on the
`affaan-m/ECC` row = ECC won 0, tied 2, lost 5. No competitor won a single task.

SOTA wins or ties **every one of the 21 head-to-head cases; it loses none.** And
the competitors are **not strawmen** — all three lift completeness +0.23 to +0.28
over an unguided model, i.e. they are genuinely good guidance. SOTA is simply more
complete.

## Why SOTA wins — the cross-cutting concerns competitors drop

Most-missed rubric items per arm across the 7 tasks (what each still omits):

- **unguided:** tests (7/7), rate limiting (6), transport/TLS (5), logging (4)
- **SOTA:** session-invalidation (1 — the lone `c7` finite-constraint-budget slip)
- **[affaan-m/ECC](https://github.com/affaan-m/ECC) (~230k★):** **rate limiting (3)**, storage-safety, image-bomb, idempotency, metrics, CSRF
- **[alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills):** **transport/TLS (4)**, **tests (4)**, rate limiting (2), logging, CSRF
- **[PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules):** **rate limiting (5)**, transport (2), storage, image-bomb, CSRF

The pattern is consistent: competitors cover the *obvious* per-task security
(auth, input validation, SQLi) well, but systematically drop the **cross-cutting
production non-negotiables** — rate limiting, transport enforcement, tests,
structured logging — on endpoint after endpoint. Even the ~230k-star `affaan-m/ECC` omits
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
  deployment SOTA-skills also runs its self-audit (measured: SOTA reaches 0.99
  *with* the gate in `run-completeness.py`, vs 0.987 on content alone here).
  Whether that *widens* the lead in an as-deployed run is a prediction, **not
  measured** — a competitor deployed with its own method could improve too.
- **Each competitor's best-matching content** for "build a secure Python/FastAPI
  backend feature," at a token budget in the same ballpark as a SOTA arm, pinned
  by commit SHA in [`evals/cases/competitors.json`](../../cases/competitors.json).
  Licenses permit reuse (`affaan-m/ECC` + `alirezarezvani/claude-skills` MIT,
  `PatrickJS/awesome-cursorrules` CC0); attributed here.
- **Blind judge** (opus-4.8), same rubric as `run-completeness.py`. No artifact was
  truncated (largest 92 KB, well under the 32k-token cap). Raw per-case data:
  `competitor-benchmark.json`. Reproduce: `python3 evals/run-competitors.py
  --competitors-dir <clones>`.

## Confidence — the lead survives sampling (multi-sample, 2026-07-14)

The main table is single-sample (temp 0). To check the lead isn't a lucky draw, we
re-ran **3 samples at temp 0.7** on the **3 tightest cases** — c1, c3, c7, the ones
where a competitor *tied* SOTA-skills in the single-sample run (`competitor-benchmark-3sample.json`):

| Library | Completeness (3 tight cases) | vs SOTA-skills |
|---|---|---|
| [**SOTA-skills**](https://github.com/martinholovsky/SOTA-skills) | **98%** | — |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | 87% | −11 pts |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 82% | −15 pts |
| [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) | 82% | −16 pts |
| unguided | 65% | −33 pts |

The gaps (−0.11 to −0.16) are **the same** as the single-sample full-7 run
(−0.12 to −0.17), and **on every one of these cases SOTA's *worst* sample is ≥ each
competitor's *best* sample** — competitors occasionally tie SOTA at the ceiling
(`affaan-m/ECC` + `PatrickJS/awesome-cursorrules` hit 1.00 on c1; `affaan-m/ECC` ties at 0.91 on c7) but never beat it. SOTA's
own variance is near-zero (sd 0.00 on c1/c3, 0.04 on c7). The lead is stable.
*(Multi-sampling the other 4 cases and the full 7 was left for a top-up — those
were the least contested, so the tight-case check is the informative one.)*

## Breadth — does it generalize? (frontend, run 2026-07-15)

The result above is one task family (Python/FastAPI backend). To test whether the
lead generalizes, we ran the **same harness on 3 React frontend tasks** (login
form, searchable data table, image-upload-with-preview), each with an objective
10-item rubric (controlled inputs, accessible labels, loading/error/empty states,
XSS-safe rendering, cleanup, tests). Each competitor got its **best frontend
content** (`competitors-frontend.json`); [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills)
has no React-specific content, so it got its best general bundle — honestly noted.
`competitor-breadth-frontend.json`:

| Library | Frontend completeness (3 tasks) | vs SOTA-skills | Head-to-head (won/tied/lost vs SOTA-skills) |
|---|---|---|---|
| [**SOTA-skills**](https://github.com/martinholovsky/SOTA-skills) | **97%** | — | — |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | 97% | **±0** | 1 / 1 / 1 |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 97% | **±0** | 1 / 1 / 1 |
| [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) | 90% | −7 pts | 2 / 0 / 1 |
| unguided model | 77% | −20 pts | — |

**On frontend, SOTA-skills has no advantage** — it *ties* ECC and claude-skills at
97% (and even *lost* the login-form task, 90% vs their 100%, by missing controlled
inputs). The reason is structural, not a fluke: **the unguided baseline is far
higher here (77% vs 58% on backend)** because frontend completeness is *easy* — a
capable base model already knows React best practices (controlled inputs, labels,
escaping), so the small remaining gap (mostly missing tests) closes with almost any
"be thorough" guidance. Tellingly, claude-skills tied SOTA-skills **with no frontend
content at all**. SOTA-skills' big backend lead came from the cross-cutting
*production* non-negotiables (rate limiting, transport, idempotency) the base model
silently drops — and frontend has no equivalent set that competitors miss.

**Conclusion: the completeness lead is backend-specific and does NOT generalize to
frontend.** That is the honest scope, and it is exactly what a breadth test exists
to find.

## Honest limitations (state them, don't bury them)

- **Two task families measured, not more** — 7 Python/FastAPI backend tasks (SOTA
  leads) + 3 React frontend tasks (SOTA ties; see above). Data pipelines, mobile,
  CLI, etc. are untested; the backend-vs-frontend split already shows the lead is
  domain-dependent.
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
against the single most-starred cross-AI peer ([affaan-m/ECC](https://github.com/affaan-m/ECC)),
the most-starred rules library ([PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules)),
and the closest same-kind skills library
([alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills)).
But the breadth test **bounds** it: the claim is honestly scoped to
**completeness on *backend* build tasks** (content-only, reproducible). On
*frontend* SOTA-skills ties the field — so "SOTA-skills beats the popular
libraries" is true for backend and **must not** be stated as a general claim.
