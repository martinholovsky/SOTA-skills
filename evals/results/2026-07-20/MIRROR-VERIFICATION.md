# Verifying +0.39 against the workflow that actually ships

**Date:** 2026-07-20/21 · **Build:** `anthropic/claude-sonnet-4.6` ·
**Judge:** `anthropic/claude-opus-4.8` (blind) · 7 cases, 3× @0.7 per arm

## Why this run existed

`evals/run-completeness.py`'s `BUILD_WORKFLOW` is a **hand-compressed mirror** of the
router's BUILD steps 3–4 — not a live read. It is kept compressed deliberately so
results stay comparable with every historical run. But a mirror rots: the
falsification clause added to router step 4 in **#119** was missing from it for four
days, so the project's most-cited number was being measured against a workflow that
no longer shipped. Nothing failed. The eval quietly measured the wrong thing.

Found during the [audit-process work](AUDIT-PROCESS.md) §1, and fixed the only way a
measurement problem should be: measured, not assumed.

## Method

Two identical runs, one variable changed between them.

- **Arm A** — the drifted mirror, exactly as `+0.39` was originally measured.
- **Arm B** — mirror synced: the falsification clause ("if this were silently a
  no-op, would anything observable differ?") added, matching router step 4.

Everything else held constant: same cases, same models, same samples, same
temperature, same rubrics, same blind judge.

## Result — the headline holds

| | Arm A (drifted) | Arm B (**ships**) |
|---|---|---|
| without-library | 0.593 | 0.578 |
| **with-library** | **0.996** | **0.976** |
| **LIFT** | **+0.40** | **+0.40** |

**The `+0.39` figure was never wrong** — it was measured against stale text and
reproduces at +0.40 either way. The correct current number, measured against the
workflow that actually ships, is **0.58 → 0.98, +0.40**.

### Where the 0.02 went

| Case | A with | B with | Δ | B with-arm missing |
|---|---|---|---|---|
| c1_ticket_api | 0.97 | **0.86** | **−0.11** | pagination, transport, sizelimit |
| c3_emailjob | 1.00 | 0.97 | −0.03 | — |
| c2, c4, c5, c6, c7 | 1.00 | 1.00 | +0.00 | (none) |

The entire drop is **one case**. Five of seven remain perfect.

**Is it noise or a real salience cost?** Honestly: cannot tell from one run. The
recorded with-arm across-case sd is **±0.01**, and this shift is −0.02 — larger than
that band, but concentrated in a single case rather than spread, which is what
sampling variance usually looks like at n=7.

It also points the direction this project's own
[context-rot finding](../../../docs/WHY-COMPLETENESS-RESIDUAL.md) predicts: *adding*
guidance text can lower the salience of what is already there. That finding is why
principle 5 is deliberately short. So the dip is **not dismissed** — it is exactly
the effect we have measured before, and c1 losing three cross-cutting rubric items
(transport, sizelimit, pagination) is the classic signature.

**Resolving it needs a repeat run**, which is logged rather than done: the same B
configuration re-run 3× more, to see whether c1 recovers.

## What changed as a result

1. **The mirror is synced.** The eval now measures the workflow that ships. The
   published number becomes **0.98 / +0.40**.
2. **The drift class is closed.** `ROUTER_BUILD_SHA` pins a sha256 of the router's
   BUILD section; the runner **aborts** on mismatch rather than measuring unshipped
   text:

   ```
   MIRROR DRIFT: router BUILD section is 1e3a03ea86af389e, mirror pinned to
   71a9d78ea5e9e341. Re-sync it and set ROUTER_BUILD_SHA=..., or the eval will
   measure a workflow that is not shipped. Refusing to run.
   ```

   Watched to fire on a synthetic router edit, and the router restored, before being
   trusted. Changing router BUILD steps 3–4 now *forces* a decision instead of
   silently invalidating the headline.

## Limitations

- **One run per arm.** The −0.02 is not separable from sampling variance without a
  repeat; do not treat it as a measured cost of the falsification clause.
- 7 cases, 12-item rubrics — one case moving three items shifts the mean by ~0.036.
- Single build model and single judge pairing, as with every completeness run here.
- The mirror remains a **hand-compressed paraphrase**, not the router's literal
  prose. The hash guarantees someone *looks* when the router changes; it does not
  guarantee the paraphrase is faithful.
