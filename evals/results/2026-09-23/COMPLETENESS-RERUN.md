# Completeness re-run against the current router (ROADMAP 63)

**Result: the published +0.39 holds.** Two-run mean **0.58 → 0.98, lift +0.41**. The
per-run lifts were +0.39 and +0.42.

## Why this was run

Router BUILD step 2 gained a standing `sota-shell-scripting` rules/06 load on 2026-09-22. That
moved `ROUTER_BUILD_SHA` a92b0177acadec05 → **273a969bbe2994e4**. The mirror was re-read
clause by clause and the hash was bumped alone, so the treatment arm was unchanged and +0.39
was not invalidated. It had not been *measured*, though. The stated obstacle ("no API key") was
false for a working tree, which reads `OPENROUTER_API_KEY` from `./.env`.

## Configuration (from each file's `_meta`, not from the command line)

The configuration matches the baseline row in `RESULTS.md` (`2026-07-20/MIRROR-VERIFICATION.md`):

| field | value |
|---|---|
| build model | `anthropic/claude-sonnet-4.6` |
| judge model | `anthropic/claude-opus-4.8` (blind to arm) |
| samples / temp | 3 / 0.7 |
| runs | 2 |
| `router_build_sha` | `273a969bbe2994e4`, the current router |
| optional arms | none (`pad_rules` 0, `no_gate_arm` false) |

Each run covers 7 cases × 3 samples = **21 artifacts per arm**, so 42 per arm over both runs.

## Numbers (recomputed from the JSON, not copied from the runner's printout)

| run | without | with | lift |
|---|---|---|---|
| r1 | 0.589 | 0.978 | +0.389 |
| r2 | 0.566 | 0.987 | +0.421 |
| **mean** | **0.577** | **0.982** | **+0.405** |

| case | without (r1 / r2) | with (r1 / r2) | lift (2-run mean) |
|---|---|---|---|
| `c1_ticket_api` | 0.67 / 0.64 | 0.94 / 0.97 | +0.31 |
| `c2_upload` | 0.52 / 0.42 | 0.97 / 1.00 | +0.52 |
| `c3_emailjob` | 0.73 / 0.76 | 1.00 / 1.00 | +0.26 |
| `c4_login` | 0.50 / 0.50 | 0.93 / 0.93 | +0.43 |
| `c5_search` | 0.60 / 0.57 | 1.00 / 1.00 | +0.42 |
| `c6_webhook` | 0.57 / 0.47 | 1.00 / 1.00 | +0.48 |
| `c7_pwreset` | 0.55 / 0.61 | 1.00 / 1.00 | +0.42 |

The lift is positive in every case in both runs. The without-library arm again drops the same
cross-cutting items the original measurement named, **rate limiting, transport and tests** in
most cases, so the mechanism and not just the number has held.

## What this does and does not establish

- It **re-measures** +0.39 on the model it was published for (sonnet-4.6), against the current
  router. It says nothing new about other models. The sonnet-5 row stands on its own run.
- Two runs of three are the same power as the baseline. The +0.02 difference (0.39 → 0.41) is
  within the run-to-run spread seen here (0.39 vs 0.42) and **is not a finding**.
- As before, this measures the BUILD workflow with the skills pasted in. It cannot see
  routing, because the eval short-circuits it by construction (see the pin comment in
  `evals/run-completeness.py`).
