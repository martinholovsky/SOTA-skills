# Pre-registration — ROADMAP item 20, freshness + routing on a current flagship

**Written and committed BEFORE the run**, per router operating principle 0:
*"Before measuring, state what result would falsify the claim. If no obtainable
result could, the experiment is theatre."* Item 20's own instruction repeats it —
*"state the prediction first so the run can falsify it."*

## What is being re-measured, and why it is open

Item 17 established that a measured lift is **per-claim, not library-wide**:

| claim | measured on | result |
|---|---|---|
| defect-avoidance | `claude-sonnet-4.6` → `claude-sonnet-5` | +0.19 → **+0.000 — expired** |
| completeness | `claude-sonnet-4.6` → `claude-sonnet-5` | +0.39 → **+0.38 — holds** |
| **freshness** | `claude-sonnet-4.6` only | **+0.53 — never re-measured** |
| **routing** | `claude-sonnet-4.6` only | **+0.10 — never re-measured** |

The two open rows are this run.

## Protocol (identical to the original, so the arms are comparable)

- Runner: `evals/run-clean.py` — raw OpenRouter API calls, no `HOME`, no
  `CLAUDE.md`, no skill registry, so the without-arm is genuinely library-free.
- Sets: `cases/freshness.jsonl` (**32** cases) and `cases/router.jsonl` (**20**).
- `--samples 3 --temp 0.7` — the original protocol
  ([2026-07-13/MULTI-SAMPLE.md](../2026-07-13/MULTI-SAMPLE.md)); freshness was 3×
  on 2026-07-12, routing 3× on 2026-07-13, both on `anthropic/claude-sonnet-4.6`.
- Model: **`anthropic/claude-sonnet-5`** — confirmed present on OpenRouter's live
  model list at run time, and the same model the completeness re-baseline used, so
  this run sits directly beside it in the table above.
- Costed before starting, as item 20 asks: with-arm prompts measured at **84,193**
  (freshness, 26 skill files pasted) and **11,440** (routing, the router pasted)
  approx. tokens; ~293k input + ~18k output total; at the live sonnet-5 price of
  **$2.00/$10.00 per Mtok** that is **~$0.77**.

## Predictions and falsifiers

### Freshness — predicted DURABLE

**Reasoning.** A training cutoff is a *knowledge* gap that model progress does not
close: a stronger model trained to the same date still does not know what happened
after it. This is the opposite of defect-avoidance, which expired precisely because
it was a knowledge gap *inside* the cutoff that a better model closed on its own.

- **Predict:** without-arm **≤ 0.60**, with-arm **≥ 0.90**, lift **≥ +0.30**.
- **FALSIFIED IF lift < 0.15** — the newer model already knows these facts unaided,
  and freshness expires the way defect-avoidance did. This is a real possible
  outcome, not a strawman: `sonnet-5` postdates `sonnet-4.6` by ~4 months, and some
  of these facts may now sit *inside* its cutoff.
- **A SECOND, DISTINCT failure to keep separate:** with-arm **< 0.85** means the
  **library** has gone stale, not that the lift is gone (`LAST-VERIFIED` reads
  **2026-07-08**, seven weeks before this run). If that happens it must be reported
  as a library-freshness defect and the missed cases named — **never** rolled into
  the lift number, which would blame the model for our own rot.

### Routing — predicted to HOLD, small, near the noise floor

**Reasoning.** The original was without **0.90** → with **1.00** = **+0.10**. The
headroom is only 0.10 to begin with, and two neighbouring routing-family instruments
have already saturated at +0.00 (`run-desc-routing.py`, the description-catalogue
A/B; and every audit set). Saturation here is a live hypothesis.

- **Predict:** with-arm **≥ 0.98**, without-arm **0.88–0.96**, lift **+0.04 to +0.12**.
- **FALSIFIED IF lift ≤ 0.02** — routing has saturated on a current flagship, and the
  +0.10 claim expires like defect-avoidance did.
- **Granularity note, stated up front so it cannot be rationalised afterwards:** 20
  cases, so one fully-missed case moves recall by **0.05**. A 3-sample mean resolves
  ~0.02–0.03. Any lift below **0.05** is one case and must be reported as such.

## Rules binding this run

1. **The without-arm is a free negative control for the measurement itself.** It
   cannot see the library. Read it *before* interpreting the with-arm
   (`evals/README.md`, 2026-08-21 convention).
2. **No file the runner reads live may be edited while a run is in flight.**
3. **Whatever comes back gets published**, including a refuted prediction. Both
   falsifiers above name a specific number; neither is unreachable.
