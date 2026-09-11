# Skill-application decay over a long session — first run (2026-07-14)

**Question (roadmap item 5):** every other eval measures a *single* call. Does a
rule loaded early in a session stop being applied as the conversation grows — and
does SOTA's per-prompt reminder hook counter it? The literature says adherence
drops with turn count (Laban et al., "LLMs Get Lost in Multi-Turn Conversation");
this measures it directly.

## Method

`evals/run-decay.py` (clean raw OpenRouter API, blind opus-4.8 judge). A multi-turn
`messages` conversation loads the engineering guidance at **turn 1** ("apply this
to everything you build this session"), then **K turns of unrelated filler Q&A**
(off-topic, so it grows context/turn-count without reinforcing the guidance), then
a build task (the probe, `c6_webhook`). Arms:

- **anchor** — guidance at turn 1 only (measures decay as K grows).
- **reminder** — guidance at turn 1 + a short generic "remember the guidance from
  the start" on the probe turn (the analog of SOTA's `UserPromptSubmit` hook; names
  no concern, so no rubric leakage).
- **control** — no guidance (baseline).

## Result — no decay at this scale

| arm | K=0 | K=15 | K=30 |
|---|---|---|---|
| control (no guidance) | 0.40 | 0.40 | 0.40 |
| anchor (guidance at turn 1) | **1.00** | **1.00** | **1.00** |
| reminder (guidance + reminder) | 1.00 | 1.00 | 1.00 |

Decay (anchor K0→K30): **+0.00**. Reminder recovery: **+0.00** (nothing to
recover). An ~18.6K-token (~72 KB) guidance block loaded at turn 1 was **still fully applied
after 30 unrelated turns** — the guidance did not fade at this session length.

## Honest reading — this bounds the problem, it doesn't find the breaking point

The null result is real but limited by design: the filler is only ~3.2K tokens (~13 KB) at K=30,
tiny next to the ~18.6K-token guidance, so it can't meaningfully *dilute* the anchor —
the guidance still dominates context and the model keeps applying it. So the
finding is: **at moderate session length with a large, dominant guidance block,
there is no decay** (reassuring), but the test hasn't stressed the regime where
decay is expected (guidance pushed far back by much larger intervening context).

**To find the decay point, scale the test up** (`--depths` + a bigger filler
corpus, or a smaller/weaker anchor so intervening context can overtake it) — and
ideally interleave real *coding* turns rather than trivia, since semantically-close
distractors hurt more (per [WHY-COMPLETENESS-RESIDUAL.md](../../../docs/WHY-COMPLETENESS-RESIDUAL.md)).
That needs a larger token budget; the harness is ready for it. Roadmap item 5 stays
open. Raw data: `decay-c6.json`.

---

**Renumbered 2026-09-11 — this is now [ROADMAP item 49](../../../docs/ROADMAP.md).** Both
"item 5" references above were correct when written and are left as written; the ledger was
renumbered afterwards and *item 5* has meant the **6-month accuracy sweep** ever since, so
the pointer aimed at a calendar item nobody would connect to decay. Two corrections to the
paragraph above, from re-reading `run-decay.py` rather than this file: *"the harness is ready
for it"* is the **flag** half only — `--depths` past 30 is **refused** by a guard added
2026-08-16 (*"only 30 filler turns exist; the run would report a depth it never reached"*,
watched to fail at 60 and to pass at 30 on 2026-09-11), not silently capped. The blocking
half is the **filler corpus**: 30 turns is 13,001 chars ≈ 3.2K tokens against an ~18.6K-token
anchor, so it is smaller than the thing it is meant to dilute — which is the likeliest reason
this run found no decay at all.

## What the harness gives us

A reusable multi-turn decay probe (`run-decay.py`) with the three arms above,
plus the reminder arm that directly tests SOTA's `UserPromptSubmit` re-injection
design — the mechanism documented in
[docs/CONTEXT-MANAGEMENT.md](../../../docs/CONTEXT-MANAGEMENT.md). This is the first
time the library measures the temporal (not just single-call) dimension of rule
forgetting.
