# Routing check — v1.54.0 cut: `sota-devsecops` and `sota-rust` descriptions changed (2026-11-01)

Two skill descriptions differ between `v1.53.0` and the release tree (compared as parsed
frontmatter, not diff lines): `sota-devsecops` (#644, the new rules/16 on fast CI) and `sota-rust`
(#642, Kani and Flux named). Checked per commit: #658 and #643 also edited those `SKILL.md` files,
body only. Per `RELEASING.md` §2c the regression set was run against the release tree.

## desc-routing-regressions (the required run)

`python3 evals/run-desc-routing.py --samples 3 --cases evals/cases/desc-routing-regressions.jsonl`
— `anthropic/claude-sonnet-4.6`, temp 0, 4 cases × 3 samples × 2 arms (with and without the
cross-reference text; the ablation removes 907 characters from 10 descriptions): **every case
correct 3/3 in both arms**, distractor picks 0. No case moved.

| case | expect | with-xref | without-xref |
|---|---|---|---|
| r1_token_count | `sota-llm-engineering` | 3/3 | 3/3 |
| r2_absence_sweep | `sota-shell-scripting` | 3/3 | 3/3 |
| r3_local_vs_ci_gate | `sota-devsecops` | 3/3 | 3/3 |
| r4_pwsh_injection | `sota-shell-scripting` | 3/3 | 3/3 |

`r3_local_vs_ci_gate` is the case closest to the changed `sota-devsecops` description, and it
held. No case targets `sota-rust`; the regression file admits only cases where a real mis-route
happened, and none has been recorded for it.

Output: [routing-release/desc-routing-regressions.json](routing-release/desc-routing-regressions.json).
Elapsed 26.8 s.

Cost: at most **$0.57** (OpenRouter `usage` 711.652 → 712.220 across the run). The counter is
account-wide and can lag, so this is an upper bound for the run, not its exact cost.
