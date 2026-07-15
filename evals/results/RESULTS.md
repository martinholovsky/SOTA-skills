# Eval results — consolidated scoreboard

The single place to see every measured number, newest first. Each row links its
full writeup (method, per-case data, limitations). All runs are clean raw-API
(OpenRouter, no sota config), a **different** model grades each artifact **blind**
to which arm produced it, and every harness is in [`evals/`](../). Reproduce any
row from the command shown in its writeup.

## 1. Efficacy vs. an unguided model

Same model, same task, library loaded vs. nothing.

| Dimension | Without | With SOTA | Lift | Samples | Source |
|---|---|---|---|---|---|
| **Completeness** (7 build tasks) | 0.60 | **1.00** | **+0.39** | 3×, temp 0.7 | [MULTI-SAMPLE](2026-07-13/MULTI-SAMPLE.md) |
| **Freshness** (32 current-2026 facts) | 0.44 | **0.97** | **+0.53** | 3×, temp 0.7 | [MULTI-SAMPLE](2026-07-13/MULTI-SAMPLE.md) |
| Routing (20 tasks) | 0.90 | **1.00** | **+0.10** | 3×, temp 0.7 | [MULTI-SAMPLE](2026-07-13/MULTI-SAMPLE.md) |
| Audit (14 hard snippets) | 1.00 | 1.00 | +0.00 | 1× | [BASELINE](2026-07-10/BASELINE.md) |
| Cross-file audit (8-defect repo) | 1.00 | 1.00 | +0.00 | 2 models | [REPO-AUDIT](2026-07-13/REPO-AUDIT.md) |

The with-library arm is **near-zero variance** on every value dimension
(completeness ±0.01 across-case sd, routing/freshness ±0.00); the sampling wobble
is all in the unguided arm. Audit is +0.00 and reported, not hidden — a capable
model already recognizes vulnerabilities, even cross-file when the repo fits in
context. The real remaining audit frontier is an **agentic large-repo** audit
(too big to hold at once); logged in the [roadmap](../../docs/ROADMAP.md).

## 2. Live-agent validation

Does the paste-based completeness eval reflect a real router-driven agent?

| Test | Result | Source |
|---|---|---|
| 7 live sub-agents, real router BUILD workflow, blind judge | **0.987** (6/7 perfect) ≈ the 0.988 paste-simulation | [LIVE-BUILD](2026-07-13/LIVE-BUILD.md) |

The simulation is a faithful proxy, and the self-audit gate caught real bugs live
(a prod `/docs` exposure, an unbounded DB critical section, a task-cancellation leak).

## 3. Competitor benchmark — SOTA vs. the most popular libraries

Content-only (SOTA's self-audit **off**), same rubric, blind judge, on the 7
**backend** completeness tasks. Targets validated live via the GitHub API. The
lead is **backend-specific** — a frontend breadth run below shows it does not
generalize.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../../assets/benchmark-dark.svg">
    <img alt="Best-practice completeness on backend build tasks by library: SOTA-skills 99%, affaan-m/ECC 87%, PatrickJS/awesome-cursorrules 83%, alirezarezvani/claude-skills 81%, unguided model 58%." src="../../assets/benchmark-light.svg" width="100%">
  </picture>
</p>

One consolidated view — every competitor's standing in a single table. Scores are
**% of a fixed best-practice rubric the generated code actually implements**
(blind-judged); higher is better.

| Library | Stars | Completeness (7 backend tasks) | Confidence (3 tightest, 3×) | Gap vs SOTA-skills | This library vs SOTA-skills — won / tied / lost¹ |
|---|---|---|---|---|---|
| [**SOTA-skills**](https://github.com/martinholovsky/SOTA-skills) | — | **99%** | **98%** | — | — |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | ~230k | 87% | 87% | −12 pts | 0 / 2 / 5 |
| [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) | ~40k | 83% | 82% | −16 pts | 0 / 0 / 7 |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | ~23k | 81% | 82% | −17 pts | 0 / 1 / 6 |
| unguided model | — | 58% | 65% | −40 pts | — |

¹ **This library's record against SOTA-skills**, across the 7 build tasks (how many
that library scored *higher than* / *equal to* / *lower than* SOTA-skills,
single-sample). Read it on the library's own row: `0 / 2 / 5` on the
[affaan-m/ECC](https://github.com/affaan-m/ECC) row = ECC **won 0, tied 2, lost 5**.
**No competitor won a single task against SOTA-skills** (on backend).

**Breadth — the lead is backend-specific.** Re-running the same harness on 3
**React frontend** tasks tells a different story
([COMPETITOR-BENCHMARK](2026-07-13/COMPETITOR-BENCHMARK.md#breadth--does-it-generalize-frontend-run-2026-07-15)):

| Library | Frontend (3 tasks) | vs SOTA-skills |
|---|---|---|
| **SOTA-skills** | 97% | — |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | 97% | ±0 |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 97% | ±0 |
| [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) | 90% | −7 pts |
| unguided model | 77% | −20 pts |

On frontend, SOTA-skills **ties** ECC and claude-skills (and even lost one task) —
frontend completeness is easy enough (unguided already 77%) that any guidance
reaches the top. **So the head-to-head win is a *backend* result, not a general
one.**

SOTA-skills **wins or ties all 21 head-to-head cases and loses none.** The
confidence check confirms it isn't noise: gaps match the full run, and
**SOTA-skills' worst sample ≥ each competitor's best sample** on every tight case.
Competitors are legitimate (all beat an unguided model by +17 to +28 pts) but drop
the cross-cutting non-negotiables (rate limiting, transport, tests) — even the
~230k-star [affaan-m/ECC](https://github.com/affaan-m/ECC)
omits rate limiting on 3 of 7 tasks. Full method + honest limits (backend + frontend, content-only, bundle-size
asymmetry): [COMPETITOR-BENCHMARK](2026-07-13/COMPETITOR-BENCHMARK.md).

## 4. Skill-application decay over a long session

Does a rule loaded early stop being applied as the session grows?
([`run-decay.py`](../run-decay.py); the mechanisms that fight it live in
[docs/CONTEXT-MANAGEMENT.md](../../docs/CONTEXT-MANAGEMENT.md).)

| arm | K=0 | K=15 | K=30 turns of filler | Source |
|---|---|---|---|---|
| guidance at turn 1 | 1.00 | 1.00 | **1.00** (no decay) | [DECAY](2026-07-13/DECAY.md) |
| no guidance (control) | 0.40 | 0.40 | 0.40 | |

First run: **no decay at moderate scale** — an ~18.6K-token (~72 KB) guidance block held after 30
unrelated turns. This *bounds* the problem but doesn't find the breaking point (the
filler is too small to dilute the anchor); scaling the test up needs a top-up.
*(roadmap item 5, still open.)*

## Not yet measured (open)

- **Competitor breadth — DONE (backend + frontend).** The lead is backend-specific
  (SOTA-skills ties the field on frontend, above). Data pipelines / mobile / CLI
  remain untested, but the domain-dependence is already established.
- **As-deployed competitor comparison** — each library with its own method (not
  content-only). SOTA-skills' self-audit is *off* in this run, so an as-deployed
  run would *plausibly* favor SOTA-skills — but that is a prediction, **not
  measured** (a competitor's own method could help it too).
- **Full-7 multi-sample** of the competitor arms (only the 3 tightest done).

## The three-layer story

SOTA **lifts an unguided model** where it matters (completeness +0.39, freshness
+0.53); that lift **reproduces in a live agent** (0.99); and it **beats the most
popular competing libraries** head-to-head **on backend** (0.99 vs 0.81–0.87,
lead stable under sampling) — while honestly bounding it: on *frontend* SOTA-skills
ties the field, so the win is domain-specific, not general. Boundaries stated, not buried.
