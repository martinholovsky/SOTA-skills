# Pre-registration — small-model evals (written 2026-10-07, before any call)

Question (from the 2026-10-06 outside review, claim 4): is the library's design "brittle" on
less capable models — do they fail to FIND the right skills, or fail to APPLY them?

Models: `anthropic/claude-haiku-4.5`, `google/gemini-3.8-flash` (OpenRouter ids, priced
$1/$5 and $0.75/$3.75 per M tokens on 2026-10-07). Judge for completeness: the runner's
default, `anthropic/claude-opus-4.8` (blind; different model from both builders).

Runs, in this order, each only if the budget guard allows:
1. `run-routing-recall.py --model M --samples 3 --temp 0.7` (FIND: 10 multi-domain cases,
   gold skill sets) — both models.
2. `run-completeness.py --build-model M --samples 3 --temp 0.7` (APPLY: 7 build tasks, with vs
   without the library, blind rubric) — haiku first, then flash.

Budget: operator cap **$10.00** total, spend of record = OpenRouter `/api/v1/credits`
(total_usage delta), checked before every run; a run starts only if spend so far + that run's
estimate <= cap. Estimates: routing ~$0.50/model; completeness ~$4.5/model (the 2026-08-14
gemini-3.1-pro n=3 run cost $4.48; small builders are cheaper, the judge is not).

Predictions:
- H1 (APPLY): lift (with − without) is positive for both models; predicted >= +0.30, because
  the measured lift has tracked the unguided baseline (+0.39/+0.44/+0.58) and small models
  should have lower baselines. **Refuted for a model if its lift <= 0.**
- H2 (FIND): routing recall >= 0.85 for both (frontier: 0.975). "Brittle routing" is supported
  for a model if recall < 0.75.
- Not tested: whether a small agent with file tools actually OPENS the files (progressive
  disclosure as navigation). Both instruments paste text; neither drives tools.

## Deviations (appended, never rewritten)

**D1 — 2026-10-07, after runs 1-3, before any flash completeness call.** The haiku completeness
run cost $5.58 against a $4.50 estimate; the guard correctly skipped flash at n=3 (would exceed
the $10 cap). Flash completeness is run at **n=1, temp 0.0** (the 2026-08-13 n=1 protocol) within
the remaining cap, and reported as n=1 — one sample per arm, direction only.
