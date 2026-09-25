# Routing check: `sota-golang` description "Go 1.25+" → "Go 1.26+" (2026-09-25)

**Why it ran.** The language-skill accuracy sweep changed one `description`. Go 1.27.0
shipped on 2026-08-19, which ended security support for 1.25, so `sota-golang`'s
frontmatter now reads `Go 1.26+`. That was the only frontmatter change in the sweep:
`git diff` of every `description:` line across `skills/*/SKILL.md` shows just this one.
The description is the whole auto-load classifier, so RELEASING.md §2c requires the
regression set before and after any edit to it.

**Before:** `evals/ROUTING-BASELINE` read `2026-09-21 1.000 anthropic/claude-sonnet-4.6`,
and no description had changed since then.

## Results (after the change)

| set | cases × samples × arms | correct | distractor picks | artifact |
|---|---|---|---|---|
| `desc-routing-regressions.jsonl` (the pinned mis-routes) | 4 × 3 × 2 | **1.000** both arms | 0.000 | `desc-routing-regressions-go126.json` |
| `desc-routing.jsonl` (the adversarial golden set, via `scripts/routing-baseline.sh`) | 10 × 3 × 2 | **1.000** both arms | 0.000 | `routing-baseline.json` |

Model: `anthropic/claude-sonnet-4.6`, temperature 0. All four regression cases routed as
pinned, 3 of 3 samples in each arm: `r1_token_count` → llm-engineering, `r2_absence_sweep` →
shell-scripting, `r3_local_vs_ci_gate` → devsecops, `r4_pwsh_injection` → shell-scripting.

**Reading.** No movement. Both sets sit at 1.00/1.00, which is the most a saturating set can
say. It cannot show that nothing changed, only that nothing dropped. The edit swapped
one version token and added no competing noun, so a drop was not expected. The run is the
check that confirms it.
