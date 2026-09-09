# Pre-registration — ROADMAP 43: GATE-ABSORPTION at n≥3, temp 0.7

**Written 2026-09-09, BEFORE the run.** Nothing has been executed against a live model
for this question. The arms, the flags and both abort guards already exist and were
watched to fail on 2026-09-06; what is new here is the power and the temperature.

This is a **new experiment, not a re-run.** ROADMAP 32 closed as *measured and
underpowered*: **+0.04** against a registered threshold of **+0.05**, with a measured
null band of **±0.03** at n=1. A number that lands between a project's own two bands
cannot be resolved by looking at it again, and it must not be resolved by quietly
adopting a threshold chosen after seeing it. So the decision rule is written down first
and the previous one is carried over unchanged.

## The question, unchanged from item 32

Does the router's terminal self-audit (BUILD step 4, mirrored into the runner as
`BUILD_WORKFLOW`) recover completeness *under competing context*? `--pad-rules 400`
adds 400 lines of genuine rules prose from skills the case does **not** load; `--no-gate-arm`
adds a fourth arm carrying that same padding with `BUILD_WORKFLOW` removed.

`GATE-ABSORPTION = mean(with+pad) − mean(pad-nogate)`.

## The arms

Four, on the existing 7 completeness cases:

| Arm | Rules context | `BUILD_WORKFLOW` | What it is for |
|---|---|---|---|
| `without` | none | — | the floor |
| `with` | the case's own skills | yes | the published baseline |
| `with+pad` | + 400 lines of unrelated rules | yes | item 25's arm |
| `pad-nogate` | + 400 lines of unrelated rules | **no** | the question |

## What changes, and why each change is not a rescue

The pre-registration for item 32 said H1 would not be rescued *by raising the padding,
changing the model, or re-reading the rubric*. None of those changes here.

| Knob | Item 32 | Here | Why it is not a rescue |
|---|---|---|---|
| samples | 1 | **3** | Power. Named in item 32's own "what would settle it". |
| temp | 0.0 | **0.7** | This repo measured that temp 0 is **not** deterministic and that its own noise floor is ±0.03 at n=1; averaging three temp-0 samples would re-sample a distribution the harness cannot see the width of. Also named in item 32's write-up. |
| padding | 400 | **400** | Unchanged — changing it was explicitly ruled out. |
| build model | `anthropic/claude-sonnet-4.6` | **unchanged** | Comparability to items 25 and 32 is the whole point. |
| judge model | `anthropic/claude-opus-4.8` | **unchanged** | Same. |
| rubric | the 7 committed cases | **unchanged** | Not re-read, not re-worded, not re-selected. |

## Predictions, with numbers, fixed before any call

**H1 — the gate absorbs the padding.** `GATE-ABSORPTION ≥ +0.05`, the *same* threshold
registered on 2026-09-06 and deliberately not moved toward the +0.04 already observed.

**H0 — the gate is not what absorbed it.** `GATE-ABSORPTION` inside **[−0.02, +0.02]**.
The band narrows from ±0.03 because the reported statistic is a mean of 3 samples per
arm per case: if the per-sample spread is what it was at n=1, the standard error of that
mean falls by √3 ≈ 1.7, so ±0.03 → ≈ ±0.017, rounded out to ±0.02. **This is the only
number derived rather than carried over, and it is derived from the sample count, not
from the result.**

**H2 — the padding hurts regardless.** Both padded arms fall ≥ 0.05 below `with`. Then
step 4 is oversold and the roadmap row saying the gate absorbs it is wrong.

### The dead zone, and the stopping rule

`GATE-ABSORPTION` in **(0.02, 0.05)** is the same dead zone item 32 landed in. Registered
now, before the run: **if it lands there again, the question is reported as unresolved at
this design and the escalation stops.** No n=5, no third padding size, no different model.
An experiment that needs three attempts to clear its own threshold is measuring something
smaller than its instrument, and the honest write-up says so. Re-opening it would need a
different *design* — a bigger rubric, cases with more room below the ceiling — and that
is a different pre-registration.

### The falsification condition

**H1 is refuted if `GATE-ABSORPTION < +0.05`.** It will not be rescued by raising the
padding, changing either model, re-reading the rubric, dropping a case, or reporting a
per-case subset as the headline. If H1 misses, the roadmap row is corrected in place.

## What could make this measure nothing

Recorded now so none of it can be discovered afterwards as an explanation for an
inconvenient result.

- **The ceiling.** `with` read **1.00** at temp 0 on this model. At temp 0.7 it will
  likely read slightly below 1.00, which *helps* — but if `with+pad` and `pad-nogate`
  both sit at the ceiling the run is **uninformative rather than null**, and must be
  reported that way. Item 32 registered this risk and it did not materialise (0.93).
- **The noise floor is a carried-over estimate, not a re-measurement.** ±0.03 at n=1 was
  measured on this harness; the √3 narrowing assumes the per-sample variance at temp 0.7
  is not larger than it was at temp 0. It plausibly *is* larger. The run reports
  `min`/`max` per arm per case, so the actual spread is in the artifact — and if the
  observed spread contradicts the assumed band, the band stated here is wrong and the
  write-up says so rather than keeping the convenient one.
- **Dilution, not conflict.** `rules_padding` refuses the case's own files but does not
  guarantee the padding *contradicts* the task. This measures dilution. It has never
  measured conflict, and the conflict question is ROADMAP 39.
- **7 cases is 7 cases.** Three samples deepens each observation; it does not widen the
  task set. A per-case result carrying the mean stays a per-case result.
- **An inert ablation.** The runner aborts if the `pad-nogate` prompt is byte-identical to
  the gated one, and `--no-gate-arm` without `--pad-rules` aborts too. Both guards were
  watched to fail on 2026-09-06.

## Cost and status

7 cases × 4 arms × 3 samples = **84 build calls + 84 judge calls**. This is live spend on
the operator's account; it was authorised on 2026-09-09 for this design, at this power,
with the thresholds above already written.

**Do not fold the result into item 32.** Item 32's +0.04 stands as published either way.
