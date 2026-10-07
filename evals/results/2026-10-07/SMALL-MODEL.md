# Small models — does the library still route and still lift? (2026-10-07)

**Headline: yes, on both instruments and both models.** An outside review (2026-10-06,
`docs/ADOPTION-LOG.md`) called the router-then-skills design *"brittle for any LLM other than the
absolute frontier"*. Measured on `anthropic/claude-haiku-4.5` and `google/gemini-3.8-flash`, both
pre-registered predictions held: small models **find** the right skills nearly as well as the
frontier did, and **apply** them with a lift as large as any measured (+0.47, +0.44), because their
unguided baseline is lower — the same pattern as every earlier family.

Pre-registration, frozen before any call: [small-models/PREREG.md](small-models/PREREG.md)
(sha256 of the frozen part `6c847f7eb1a03e96`; one dated deviation, D1).

## Result

| | `claude-haiku-4.5` | `gemini-3.8-flash` | frontier reference |
|---|---|---|---|
| **FIND** — routing recall over a gold skill set (10 multi-domain cases) | **0.925** (3 × temp 0.7) | **0.883** (3 × temp 0.7) | 0.975 — `claude-sonnet-4.6`, 1 × temp 0 ([ROUTING-RECALL](../2026-09-06/ROUTING-RECALL.md)) |
| routing precision · over-selected cases | 0.510 · 9/10 | 0.872 · 4/10 | 0.569 · 8/10 |
| **APPLY** — completeness, without → with the library (7 build tasks, blind `claude-opus-4.8` judge) | 0.45 → 0.92, **+0.47** (3 × temp 0.7; all 7 cases positive, +0.33…+0.57) | 0.53 → 0.97, **+0.44** (**1** × temp 0; all 7 positive, +0.33…+0.60) | `sonnet-4.6` +0.39 · `gpt-5.1` +0.44 · `gemini-3.1-pro` +0.58 |

No build was empty or truncated (shortest outputs 7,297 and 4,934 chars). Every case's unguided
arm missed the same cross-cutting items the frontier arms miss — rate limiting, transport,
logging, tests — which the library arm recovered.

## Against the predictions

- **H1 (APPLY), lift ≥ +0.30 for both: held** (+0.47, +0.44). The lift-tracks-the-baseline
  pattern holds below the frontier too: haiku's unguided 0.45 is lower than sonnet-4.6's 0.59, and
  its lift is larger.
- **H2 (FIND), recall ≥ 0.85 for both: held** (0.925, 0.883). Gemini Flash under-selected in 3 of
  10 cases (e.g. `mcp_server_audit` missed `sota-sandboxing`); Haiku over-selects (precision 0.51),
  which costs context, not coverage.

## What this does not test

Both instruments **paste text** — the catalogue of descriptions, or the loaded rules — into one
call. Neither drives a small *agent* with file tools, so "does a small model actually open the
router, then the right `rules/` file" is still unmeasured. That is the residual of the review's
claim; it would need an agentic harness (`sota-agent-evals`, separate repo).

## Deviation D1

The haiku completeness run cost **$5.58** against a $4.50 estimate; the budget guard (spend of
record = OpenRouter `total_usage` delta, checked before every run, operator cap $10) refused flash
at n = 3. Flash completeness ran at **n = 1, temp 0** — the 2026-08-13 n = 1 protocol — and is
reported as one sample per arm.

## Cost

**$7.24** total (routing $0.32 + $0.34, haiku completeness $5.58, flash completeness n=1 $1.00),
from the OpenRouter credits API before and after — [small-models/run-log.txt](small-models/run-log.txt).
Wall-clock: haiku completeness 2,205 s.

## Files

[PREREG.md](small-models/PREREG.md) · [routing-haiku.json](small-models/routing-haiku.json) ·
[routing-flash.json](small-models/routing-flash.json) ·
[completeness-haiku.json](small-models/completeness-haiku.json) ·
[completeness-flash-n1.json](small-models/completeness-flash-n1.json) ·
[run-log.txt](small-models/run-log.txt)
