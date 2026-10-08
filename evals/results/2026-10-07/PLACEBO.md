# Placebo arm — how much of the completeness lift is just being asked?

**Result: PARTIAL, by the pre-registered bands.** Pre-registration (frozen before any spend):
[PLACEBO-PREREG.md](PLACEBO-PREREG.md). The run executed 2026-10-08 with the pre-registered
command and output path. The wording hash matched the frozen `42c55f8c6fc102f3` before the run
started.

| | without | **placebo** | with |
|---|---|---|---|
| mean completeness (7 cases × 3 samples, temp 0.7) | 0.577 | **0.857** | 0.982 |

- **Placebo vs without:** +0.280. A plain order to "ship production-complete code and
  self-review it" recovers **69%** of the lift.
- **Library vs placebo:** **+0.125**. That much is the library, not the asking.
- **Against the bands:** H1 (placebo ≤ 0.83) is not supported. The falsifier (≥ 0.90) is not met.

## Where the remaining gap sits — the informative half

| case | without | placebo | with | share of the lift the placebo reaches | placebo still missing |
|---|---|---|---|---|---|
| c1_ticket_api | 0.653 | 0.944 | 0.958 | 95% | — |
| c2_upload | 0.470 | 0.970 | 0.985 | 97% | storage |
| c3_emailjob | 0.742 | 0.970 | 1.000 | 88% | — |
| c4_login | 0.500 | 0.733 | 0.933 | 54% | transport, csrf, tests |
| c5_search | 0.583 | 0.833 | 1.000 | 60% | ratelimit, transport |
| c6_webhook | 0.517 | 0.733 | 1.000 | 45% | sizelimit, ratelimit, transport |
| c7_pwreset | 0.576 | 0.818 | 1.000 | 57% | transport, sessioninvalidate |

On generic completeness (c1–c3) asking is nearly enough. On the security-heavy cases (c4–c7)
asking closes about half of the lift. What it leaves out are the controls a model does not
think of unprompted:
- transport enforcement, in 4 of those 4 cases;
- rate limiting;
- CSRF;
- request size limits;
- session invalidation.

That is the library's distinct contribution on this set. It is also the outside review's
"verbosity confounder", measured: real for most of the headline +0.39, and not the whole of it.

## Configuration and spend

- **Models:** `anthropic/claude-sonnet-4.6` builds, `anthropic/claude-opus-4.8` judges. Same
  model ids, samples and temp as the compared runs (asserted from both files' `_meta`).
- **Spend:** **$6.08**, from the OpenRouter credit delta (used 817.0338 → 823.1179). The
  pre-registered estimate of $3–5 was wrong, too low by about 20–50%.
- **Wall time:** 3,514 s. The runner flagged 5.9× its previous run; this arm's outputs run to
  66k characters. No output was truncated: the longest is about 66k characters, under the
  32k-token cap.

## Limits

- **Cross-day:** the placebo ran 2026-10-08; the without and with arms are the recorded
  2026-09-23 runs (r1, r2 averaged). The model ids are identical. Whether a provider alias
  moved underneath them cannot be checked from here.
- **Placebo-only:** no same-day without or with arm, chosen to fit the budget. A three-arm
  same-day run (`--placebo-arm`) would remove the cross-day caveat.
- **Small set:** n = 7, all Python, 3 samples per case. One case flipping moves the mean by
  about 0.04.
