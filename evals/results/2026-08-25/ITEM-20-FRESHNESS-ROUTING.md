# Freshness and routing on a current flagship — ROADMAP item 20 (2026-08-25)

**Predictions were [pre-registered](PREREGISTRATION.md) and committed at `91ca8d9`,
before any API call.** One of them is refuted below, and that is the most useful part
of the run.

## Result

`evals/run-clean.py`, raw OpenRouter API (no `HOME`, no `CLAUDE.md`, no skill
registry), **`anthropic/claude-sonnet-5`**, `--samples 3 --temp 0.7` — the same
protocol as the 2026-07-12/13 originals on `claude-sonnet-4.6`.

| set | arm | `sonnet-4.6` (2026-07) | `sonnet-5` (2026-08-25) |
|---|---|---|---|
| **Freshness** (32) | without | 0.44 `[0.41/0.47/0.44]` | **0.69** `[0.69/0.72/0.66]` |
| | with | 0.97 `[0.97×3]` | **0.99** `[1.00/1.00/0.97]` |
| | **lift** | **+0.53** | **+0.30** |
| **Routing** (20) | without | 0.90 `[0.91/0.88/0.91]` | **0.87** `[0.86/0.88/0.86]` |
| | with | 1.00 `[1.00×3]` | **0.99** `[0.98/1.00/1.00]` |
| | **lift** | **+0.10** | **+0.13** |

Raw: [`freshness-sonnet5-3x.json`](freshness-sonnet5-3x.json),
[`routing-sonnet5-3x.json`](routing-sonnet5-3x.json). Cost ~$0.77, estimated at
~$0.77 up front from measured prompt sizes and live pricing.

## Scorecard against the pre-registration

| pre-registered | outcome |
|---|---|
| Freshness lift **≥ +0.30** | **held** — +0.30, at the boundary |
| Freshness **FALSIFIED IF lift < 0.15** | **not triggered — freshness has not expired** |
| Freshness with-arm **≥ 0.90** | held — 0.99 |
| Library-staleness alarm: with-arm **< 0.85** | **not triggered** — the with-arm *rose*, 0.97 → 0.99 |
| Freshness without-arm **≤ 0.60** | **REFUTED — 0.69** |
| Routing **FALSIFIED IF lift ≤ 0.02** | **not triggered — routing has not saturated** |
| Routing with-arm **≥ 0.98** | held — 0.994 |
| Routing lift **+0.04 to +0.12** | **+0.13 — marginally outside, on the high side** |
| Routing without-arm **0.88–0.96** | **0.867 — marginally outside, on the low side** |

## The refuted prediction is the finding

I predicted the freshness *baseline* would stay at or below 0.60 because "a training
cutoff is a knowledge gap that model progress does not close." **It moved 0.44 → 0.69.**

The mechanism is visible case by case. Comparing the two runs' miss lists (**note: the
runner records only the final sample's misses, so this comparison is last-sample vs
last-sample, while the recalls above are 3-sample means**):

- **8 facts `sonnet-5` now answers unaided that `sonnet-4.6` could not** — `f02 f03
  f07 f12 f19 f20 f26 f30`.
- **1 fact it newly misses** — `f09`.
- **10 missed by both** — `f01 f05 f10 f13 f14 f15 f16 f17 f28 f29`.

That is the training cutoff advancing over a **fixed** case set. The facts did not
change; the model's window moved to include a third of them.

**So the knowledge/salience dichotomy from item 17 was too coarse.** There are three
shapes, not two:

| shape | example | what happens as models improve |
|---|---|---|
| **knowledge gap, closed** | defect-avoidance (+0.19 → **+0.000**) | **expires** — the fact was always learnable and now is learned |
| **salience gap** | completeness (+0.39 → **+0.38**) | **durable** — the model knows it and still omits it under context pressure |
| **knowledge gap, renewable** | **freshness (+0.53 → +0.30)** | **erodes toward a floor, does not expire** — the cutoff advances into the set, but the world keeps producing facts beyond it |

## What this means for the freshness claim — and for the instrument

**The measured freshness lift is a function of how old the case set is relative to the
model's cutoff.** The set was authored around July 2026 and is unchanged; 10 of its 32
facts still sit outside `sonnet-5`'s window, and those are what produce the surviving
+0.30. On a set re-authored with facts from the *last* few months the lift would very
likely return toward +0.53 — **a prediction, not a measurement**, and deliberately not
claimed as a number.

The consequence is that **+0.30 is the floor of this claim, not its centre**: it is
what remains when a third of the questions have aged into the model. Re-authoring the
set is the honest way to keep measuring it, and is logged as follow-up work rather
than done here (it is a fresh authoring job with its own primary-source verification,
not a re-run).

## Routing: not saturated, and the blind spots are stable

Routing's falsifier (`lift ≤ 0.02`) did **not** trigger — the outcome its two
neighbouring instruments already had (`run-desc-routing.py` and every audit set both
read +0.00). The with-arm is effectively perfect (0.994); the *baseline* drifted
slightly **down** (0.90 → 0.87), which is what widened the lift.

**Read +0.10 → +0.13 as unchanged.** The pre-registration fixed the resolution up
front: 20 cases, so one fully-missed case is **0.05**, and the whole move is 0.03.
The honest statement is that routing holds at roughly **+0.10**, not that it improved.

Qualitatively it is the same picture as 2026-07-13: the unguided arm misses the
**rule-driven** cases, the ones where the right skill is not in the prompt's keywords.
All four of the original misses persist a model generation later — `r01` (testing),
`r02` (sandboxing), `r07` (code-security), `r09` (web-frameworks) — joined by `r15`
(code-security) and `r20` (devsecops). These are exactly the cross-cutting routes the
router's rules exist to force.

## The one with-arm miss, run down rather than waved through

`f02` — *"In the OWASP Top 10 2025, what is the A-number of Insecure Design?"* — is
missed by the with-library arm in **1 of 3** `sonnet-5` samples (answered `a05`), and
was missed by `sonnet-4.6` in **3 of 3**.

Per the pre-registration, a with-arm miss must be resolved to one of three causes
before the lift is reported. Checked, in order:

1. **Is the answer key right?** Yes. Verified against the primary source at run time:
   `owasp.org/Top10/2025/` lists `A06_2025-Insecure_Design` (and `A05_2025-Injection`,
   the wrong answer given).
2. **Did the library carry the fact?** Yes — `sota-code-security/rules/09` line 10
   states `A06:2025 (Insecure Design)`, and that file is exactly what the with-arm was
   handed for this case.
3. **Therefore:** neither a stale library nor a bad key. The model was given the
   correct fact in context and answered from a strong parametric prior anyway —
   *Insecure Design* was **A04** in the 2021 edition. In-context fact losing to a
   confident prior, on the one case in 32 where the two disagree.

No library change is warranted by this. It is recorded because a with-arm miss that is
never explained is indistinguishable from rot.

## Limits

- One model, one run each, 3 samples. `temp 0` is not deterministic here either — the
  established noise floor is **±0.03** at n=1 (`evals/README.md`, 2026-08-21).
- Both movements against the original protocol are within **one case** of the
  originals on the routing set (0.05/case) and are reported as unchanged accordingly.
- The freshness case set is **fixed and ageing**; see above. This is a property of the
  instrument, and it now bounds the claim.
- The 2026-07-12 freshness run's `_meta` is empty (the runner did not record model or
  temperature then), so its model is taken from
  [MULTI-SAMPLE.md](../2026-07-13/MULTI-SAMPLE.md), which states `sonnet-4.6`. The
  recalls and per-case misses in that JSON are directly comparable; the model
  attribution is documentary rather than machine-recorded.
