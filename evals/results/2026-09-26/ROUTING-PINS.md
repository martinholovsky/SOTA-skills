# Routing check: version pins removed from nine descriptions (2026-09-26)

**Why it ran.** The version-pin policy (invariant 38) removed a current-release or baseline
token from nine `description:` lines: c-cpp, code-security, llm-engineering and python lost a
"(2026 baseline)"-style label; dotnet, golang, jvm, php and ruby now name "supported" or "LTS"
releases rather than a number. The description is the whole auto-load classifier, so
RELEASING.md §2c requires the regression set after any edit to it.

**Before:** `evals/ROUTING-BASELINE` read `2026-09-25 1.000 anthropic/claude-sonnet-4.6`.

## Results (after the change)

| set | cases × samples × arms | correct | distractor picks | artifact |
|---|---|---|---|---|
| `desc-routing-regressions.jsonl` (the pinned mis-routes) | 4 × 3 × 2 | **1.000** both arms | 0.000 | `desc-routing-regressions-pins.json` |
| `desc-routing.jsonl` (the adversarial golden set, via `scripts/routing-baseline.sh`) | 10 × 3 × 2 | **1.000** both arms | 0.000 | `routing-baseline.json` |

Model: `anthropic/claude-sonnet-4.6`, temperature 0.

**Reading.** No movement. Both sets are saturated at 1.00/1.00, so they can show that nothing
dropped, not that nothing changed. The edits removed tokens and added no competing noun, so a
drop was not expected; the run is what confirms it.
