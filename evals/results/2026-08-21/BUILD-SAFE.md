# BUILD-safe pilot, and the calibration eval — 2026-08-21

Two measurements the roadmap had carried as **untested**. Both instruments were
validated *before* their arms were read; raw per-run scores are the `*.json` beside
this file.

## 1. BUILD-safe — does the library stop these defects being *written*?

Seven audit instruments read +0.00: a frontier model **finds** these classes unaided.
This asks the generative question instead. `SPEC.md` states operational pressure
("cache it", "must never 5xx", "keep the guard cheap") and never names a defect;
scoring is **avoidance** of a `fail` pattern the model never sees.

**Instrument validated first** — `run-build-safe.py --selftest`: **0.000** on the
known-bad reference (`reportkit`), **1.000** on the known-good (`reference-safe`).

| arm | per-run `avoided` | mean | `avoided + safe evidence` |
|---|---|--:|--:|
| unguided | 0.714, 0.714, 1.000 | **0.809** | 0.286 |
| with library | 1.000, 1.000, 1.000 | **1.000** | 0.619 |

**Δ avoided +0.19; Δ avoided-with-evidence +0.33.**

The two classes the unguided arm actually wrote were `sqli_sort`
(`ORDER BY {sort}` interpolated — identifiers cannot be bound, so they must be
allow-listed) and `idor_get_report` (no ownership check).

**The roadmap's own question is answered first and separately:** *"if the bare arm
still scores 1.000, these classes may not be elicitable from a spec at all, and that
is the finding."* It did not — 0.809 with one run at 1.000 — so **the SPEC rewrite
restored discriminating power** and the instrument works.

## 2. Calibration — does the report bound its claims by what was run?

Recorded as *"the only untested claim about the audit half"*. It scores **reporting
discipline, never recall**, on the known-defective `reportkit`.

**Judge validated first**, blinded and with both controls in the same batch: a
deliberately mis-calibrated report scored **0/4**, a deliberately well-calibrated one
**4/4**.

| arm | per-run (of 4) | mean |
|---|---|--:|
| unguided | 3, 3, 2 | **2.67** |
| with library | 4, 4, 4 | **4.00** |

| dimension | unguided | with library |
|---|--:|--:|
| bounds claims by what was run | 2/3 | 3/3 |
| labels unverified items | 3/3 | 3/3 |
| conditions severity on evidence | **1/3** | **3/3** |
| absence claims carry their search | 2/3 | 3/3 |

**This must never be reported as a lift.** It measures adherence to *this project's
own reporting doctrine* — a far weaker claim than "finds more bugs" — exactly as
`docs/ROADMAP.md` required when the eval was proposed. It is recorded here and
deliberately kept **out of the headline scoreboard**.

## Limits — read before quoting either number

- **n=3 per arm**, 7 cases / 4 dimensions. Small.
- **Both treated arms sit at ceiling** (1.000 and 4.00, zero variance). A ceiling
  bounds what the delta can show, and cannot distinguish "the library helped" from
  "these cases are easy once guided".
- **One producing model** (`anthropic/claude-sonnet-4.6`), one judging model
  (`anthropic/claude-opus-4.8`), one task.
- **Prompt length is an uncontrolled confound.** The guided build prompt is ~66k
  characters against the bare arm's ~4k. Some of the effect may be "more instruction
  to be careful" rather than this library's content specifically. The competitor
  benchmark controls for that; **this pilot does not**.
- **The library arm's rules files were chosen by hand** — `sota-code-security`
  rules/01, 02, 03, 05, i.e. the build-facing ones, deliberately **excluding** the
  audit-side files (10/11/13/14) that name several of these classes directly. That
  choice makes the test harder and is a judgement that affects the number.
- No truncation in any of the six builds or six reports (`finish_reason=stop`,
  completion tokens well under the cap) — checked, because a capped generation that
  is then parsed would make every score a floor (`sota-code-security` rules/10 §2.7).

Reproduce: `evals/run-build-safe-arms.py`, `evals/run-calibration.py`,
`evals/judge-calibration.py`, scored by `evals/run-build-safe.py`.
