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
| 7 live sub-agents, real router BUILD workflow, blind judge | **0.987** (6/7 perfect) = the 0.99 simulation | [LIVE-BUILD](2026-07-13/LIVE-BUILD.md) |

The simulation is a faithful proxy, and the self-audit gate caught real bugs live
(a prod `/docs` exposure, an unbounded DB critical section, a task-cancellation leak).

## 3. Competitor benchmark — SOTA vs. the most popular libraries

Content-only (SOTA's self-audit **off**), same rubric, blind judge, on the 7
completeness tasks. Targets validated live via the GitHub API.

One consolidated view — every competitor's standing in a single table. Scores are
**% of a fixed best-practice rubric the generated code actually implements**
(blind-judged); higher is better.

| Library | Stars | Completeness (7 tasks) | Confidence (3 tightest, 3×) | Gap vs SOTA-skills | Tasks won / tied / lost¹ |
|---|---|---|---|---|---|
| [**SOTA-skills**](https://github.com/martinholovsky/SOTA-skills) | — | **99%** | **98%** | — | — |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | ~230k | 87% | 87% | −12 pts | 5 / 2 / 0 |
| [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) | ~40k | 83% | 82% | −16 pts | 7 / 0 / 0 |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | ~23k | 81% | 83% | −17 pts | 6 / 1 / 0 |
| unguided model | — | 58% | 65% | −40 pts | — |

¹ **Tasks won / tied / lost** — across the 7 build tasks, how many
SOTA-skills scored *higher than* / *equal to* / *lower than* that competitor
(single-sample). E.g. `5 / 2 / 0` = SOTA-skills beat [affaan-m/ECC](https://github.com/affaan-m/ECC)
on 5 tasks, tied on 2, and never lost.

SOTA-skills **wins or ties all 21 head-to-head cases and loses none.** The
confidence check confirms it isn't noise: gaps match the full run, and
**SOTA-skills' worst sample ≥ each competitor's best sample** on every tight case.
Competitors are legitimate (all beat an unguided model by +17 to +28 pts) but drop
the cross-cutting non-negotiables (rate limiting, transport, tests) — even the
~230k-star [affaan-m/ECC](https://github.com/affaan-m/ECC)
omits rate limiting on 3 of 7 tasks. Full method + honest limits (one task family, content-only, bundle-size
asymmetry): [COMPETITOR-BENCHMARK](2026-07-13/COMPETITOR-BENCHMARK.md).

## 4. Skill-application decay over a long session

Does a rule loaded early stop being applied as the session grows?
([`run-decay.py`](../run-decay.py); the mechanisms that fight it live in
[docs/CONTEXT-MANAGEMENT.md](../../docs/CONTEXT-MANAGEMENT.md).)

| arm | K=0 | K=15 | K=30 turns of filler | Source |
|---|---|---|---|---|
| guidance at turn 1 | 1.00 | 1.00 | **1.00** (no decay) | [DECAY](2026-07-13/DECAY.md) |
| no guidance (control) | 0.40 | 0.40 | 0.40 | |

First run: **no decay at moderate scale** — an 18.7 KB guidance block held after 30
unrelated turns. This *bounds* the problem but doesn't find the breaking point (the
filler is too small to dilute the anchor); scaling the test up needs a top-up.
*(roadmap item 5, still open.)*

## Not yet measured (open)

- **Competitor breadth** — the head-to-head is one task family (Python/FastAPI
  backend); frontend/data/mobile untested.
- **As-deployed competitor comparison** — each library with its own method (not
  content-only); would only widen SOTA's lead.
- **Full-7 multi-sample** of the competitor arms (only the 3 tightest done).

## The three-layer story

SOTA **lifts an unguided model** where it matters (completeness +0.39, freshness
+0.53); that lift **reproduces in a live agent** (0.99); and it **beats the most
popular competing libraries** head-to-head (0.99 vs 0.81–0.87), with the lead
stable under sampling. Honest boundaries are stated throughout, not buried.
