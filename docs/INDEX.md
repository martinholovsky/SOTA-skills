# Find it fast — documentation index

Can't find where something is documented? Start here. Organized by **what you're
trying to do**, not by file. (Kept in sync by hand; if a link rots, open an issue.)

## Use the library

| I want to… | Go to |
|---|---|
| Install it (plugin or clone) | [README → Installation](../README.md#installation) |
| Make the skills apply to **every** prompt (always-on routing) | [README → Always-on routing](../README.md#always-on-routing-recommended) |
| Understand how a prompt gets routed to skills | [README → How it works](../README.md#how-it-works); [`skills/sota/SKILL.md`](../skills/sota/SKILL.md) |
| See example prompts (build & audit) | [README → Using it](../README.md#using-it) |
| Enforce the rules as git hooks | [README → Enforcing the gates](../README.md#enforcing-the-gates) |
| Use it with Codex / Gemini / other AGENTS.md agents | [README → Other AI agents](../README.md#other-ai-agents-codex-copilot-gemini-) |

## Keep the model applying the rules (context / "forgetting")

| I want to… | Go to |
|---|---|
| **Understand how the library keeps rules applied as context fills** (re-injection, principle 5, terminal re-read, gates) | [**CONTEXT-MANAGEMENT.md**](CONTEXT-MANAGEMENT.md) |
| Set up the per-prompt **re-injection hook** | [README → Always-on routing, layer 3](../README.md#always-on-routing-recommended) |
| Understand *why* a rule sometimes still gets dropped | [WHY-COMPLETENESS-RESIDUAL.md](WHY-COMPLETENESS-RESIDUAL.md) |

## Know whether it works (evidence)

| I want to… | Go to |
|---|---|
| See every measured number at a glance | [`evals/results/RESULTS.md`](../evals/results/RESULTS.md) |
| Read the measured case (vs. unguided + vs. competitors) | [WHY-IT-WORKS.md](WHY-IT-WORKS.md) |
| Check the lift isn't model-specific (cross-model) | [CROSS-MODEL.md](../evals/results/2026-07-22/CROSS-MODEL.md) |
| Run the evals myself | [`evals/README.md`](../evals/README.md) |
| See the SOTA-vs-competitor benchmark | [COMPETITOR-BENCHMARK.md](../evals/results/2026-07-13/COMPETITOR-BENCHMARK.md) |
| Read a shareable write-up of the key finding | [writeups/completeness-blind-spot.md](writeups/completeness-blind-spot.md) |
| See what the library does **not** lift (the honest +0.00s) | [AUDIT-PROCESS.md](../evals/results/2026-07-20/AUDIT-PROCESS.md) |
| Read the retraction + the retired anchoring hypothesis | [SILENT-FAILURE.md](../evals/results/2026-07-20/SILENT-FAILURE.md) |

## Contribute / operate the repo

| I want to… | Go to |
|---|---|
| Land a change (branch → PR → checks → merge) | [AGENTS.md → Landing a change](../AGENTS.md#landing-a-change) |
| Know the invariants CI enforces | [AGENTS.md → Invariants](../AGENTS.md#invariants-enforced-in-pre-commit-and-ci) |
| Full contribution conventions | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| Cut a release | [RELEASING.md](../RELEASING.md) |
| Keep fast-moving claims accurate (sweep runbook) | [MAINTENANCE.md](MAINTENANCE.md) |
| See what's planned / open | [ROADMAP.md](ROADMAP.md) |
| Report bad guidance or a leaked secret | [SECURITY.md](../SECURITY.md) |

## Reference

| I want to… | Go to |
|---|---|
| The full skill list + what each covers | [README → Skills](../README.md#skills) |
| The master router (routing table, principles, workflows) | [`skills/sota/SKILL.md`](../skills/sota/SKILL.md) |
| Release history | [CHANGELOG.md](../CHANGELOG.md) (older: [archive](CHANGELOG-archive.md), [archive-2](CHANGELOG-archive-2.md)) |
| Past audits | [AUDIT-2026-07-01](AUDIT-2026-07-01.md), [AUDIT-2026-07-10](AUDIT-2026-07-10.md) |
