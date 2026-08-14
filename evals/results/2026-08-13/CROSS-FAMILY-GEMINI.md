# Cross-family confirmation #2 — Google Gemini (2026-08-13)

**Build model:** `google/gemini-3.1-pro-preview` · **Judge:** `anthropic/claude-opus-4.8`
(blind, different family from the build model) · **Cases:** 7 completeness tasks

**Two runs.** n=1 at temp 0.0 ([cross-family-gemini.json](cross-family-gemini.json), $1.63) and
**n=3 at temp 0.7** ([../2026-08-14/cross-family-gemini-3x.json](../2026-08-14/cross-family-gemini-3x.json), $4.48,
1753 s) — the multi-sample protocol the other value dimensions use.

## Result

| Build model | Without | With SOTA | Lift |
|---|---|---|---|
| `anthropic/claude-sonnet-*` (original baseline) | 0.59 | 0.98 | +0.39 |
| `openai/gpt-5.1` (cross-family #1) | 0.44 | 0.88 | +0.44 |
| **`google/gemini-3.1-pro-preview`** (cross-family #2, n=1 temp 0) | 0.41 | 0.96 | +0.55 |
| **`google/gemini-3.1-pro-preview`** (**n=3, temp 0.7**) | **0.38** | **0.96** | **+0.58** |

Per case (without → with): c1 ticket-api, c5 search `0.30 → 1.00`, c6 webhook
`0.40 → 1.00`, c7 password-reset `0.36 → 1.00`. The with-library arm reached
**1.00 on every case that was scored below 0.41 without it**.

## What this settles, and what it does not

**Settles:** the completeness lift is not an Anthropic artefact and not a
two-lab coincidence. Three families from three labs, three positive lifts,
+0.39 / +0.44 / +0.55.

**Confirms the existing pattern rather than breaking it:** the lift tracks the
*baseline*, not the lab. Gemini's unguided arm is the lowest measured yet (0.41)
and takes the largest lift (+0.55); sonnet's is the highest (0.59) and takes the
smallest (+0.39). This is the same relationship the 5-domain breadth run found
across task types, now across model families. The honest statement remains: **the
library closes the gap to a near-ceiling result, so the worse the unguided arm,
the larger the lift** — it does not add +0.5 to everything.

**Now settled at 3×.** The n=1 caveat this file used to carry is discharged: the
multi-sample run reproduces the direction and the magnitude (+0.55 → **+0.58**),
**every one of the 7 cases is positive** (+0.52 to +0.67), and the two arms behave
exactly as the library's other dimensions do —

| | mean | max within-case sample spread |
|---|---|---|
| without-library | 0.38 | 0.18 |
| with-library | **0.96** | **0.10** |

The with-arm is both higher and steadier, and it scored **1.00 on all three
samples in 3 of 7 cases**. The unguided arm's own scores moved by up to 0.18
between samples of the same task, which is the case-by-case unreliability the
library removes rather than a measurement artifact.

**Model pinning:** `gemini-3.1-pro-preview` is a preview alias and may be
withdrawn or re-pointed. The measurement is pinned to the date, not to a stable
model identity — re-run rather than cite if the alias changes.

## Cost

n=3: **$4.48** actual, 1753 s. n=1: **$1.63** actual (`total_usage` before/after, read from the OpenRouter credits
API), against a ~$3 estimate. 634 s wall-clock over 7 cases × 2 arms.

The elapsed guard flagged `6340x slower than previous` on this run: the prior
recorded duration was a 0.1 s baseline with **no denominator**, i.e. a run that
did no work. The guard printed `[no denominator — bare seconds, weak evidence]`
alongside it, which is the guard behaving exactly as intended — it refused to let
a bare-seconds comparison read as a finding.
