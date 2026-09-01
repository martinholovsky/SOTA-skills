# Find it fast — documentation index

Can't find where something is documented? Start here. Organized by **what you're
trying to do**, not by file. (Kept in sync by hand; if a link rots, open an issue.)

## Use the library

| I want to… | Go to |
|---|---|
| Install it (plugin or clone) | [README → Installation](../README.md#installation) |
| Update a clone to the latest release | `scripts/update.sh` (an alias for `scripts/install.sh --update`); [README → Updating](../README.md#updating) |
| Make the skills apply to **every** prompt (always-on routing) | [README → Always-on routing](../README.md#always-on-routing-recommended) |
| Understand how a prompt gets routed to skills | [README → How it works](../README.md#how-it-works); [`skills/sota/SKILL.md`](../skills/sota/SKILL.md) |
| See example prompts (build & audit) | [README → Using it](../README.md#using-it) |
| Enforce the rules as git hooks | [README → Enforcing the gates](../README.md#enforcing-the-gates) |
| **Verify a repo is actually set up** (read-only: library reaching it, gates real not just configured, agent file *true*) | Run `scripts/verify-setup.sh` first (mechanical half), then [**VERIFY-SETUP.md**](VERIFY-SETUP.md) for the judgement half |
| Use it with Codex / Gemini / other AGENTS.md agents | [README → Other AI agents](../README.md#other-ai-agents-codex-copilot-gemini-) |
| Audit a defect that is **correct where you tested it** — a size-gated path no fixture crosses, a cache key narrower than the behaviour, a format read from one sample, an undeclared seam, an environment-dependent default | [`sota-code-security/rules/13`](../skills/sota-code-security/rules/13-context-dependent-silence.md) (split out of rules/11 §3, 2026-08-20) |
| Audit a control that is **not there** rather than inert — absent from the shipped artifact, standing as an instruction, never triggered, parked in observe-only, or a report claiming more than ran | [`sota-code-security/rules/14`](../skills/sota-code-security/rules/14-control-not-in-force.md) (split out of rules/10 §2.10–2.14, 2026-08-20) |
| Rebuild state from an event log — what **replay** silently requires (the `apply` step must be a pure function of state and event; capture non-deterministic answers *in* the event; gate outbound effects) | [`sota-architecture/rules/03` §6](../skills/sota-architecture/rules/03-distributed-systems-and-events.md) |
| Query **geospatial** data without losing the index — `ST_DWithin` vs a non-indexable `ST_Distance` in `WHERE`, and the `geography`/`geometry` units trap | [`sota-databases/rules/03`](../skills/sota-databases/rules/03-queries-and-indexes.md) |
| Keep the evidence a measurement produced — why piping a test run through `tail` destroys the traceback while keeping the summary, and what to do instead | [`sota-shell-scripting/rules/01` §3](../skills/sota-shell-scripting/rules/01-safety-baseline.md) — redirect to a file and read the file; `pipefail` fixes the status, not the output |
| Decide **which method a durable guard is written in** — AST vs a type-resolving index vs a cross-language matcher vs the runtime vs regex, and what to reach for when the language has no native parser | [`sota-testing/rules/02` §2.10](../skills/sota-testing/rules/02-test-design-quality.md) |
| Choose a **SAST engine** for a CI gate | [`sota-devsecops/rules/05` §5.1](../skills/sota-devsecops/rules/05-analysis-gates.md) — **Opengrep** (LGPL-2.1 fork of Semgrep CE, multi-vendor consortium, rule format compatible) + CodeQL. Note there is **no `opengrep ci`**: the CLI is `scan`, so a workflow copied from `semgrep ci` will not run |
| Find absence encoded as a value (`-1`, `0`, `""`) — why it type-checks, and the asymmetric-guard tell | [`sota-architecture/rules/02` §8a](../skills/sota-architecture/rules/02-domain-modeling-and-boundaries.md), plus a measured row in every language skill |

## Keep the model applying the rules (context / "forgetting")

| I want to… | Go to |
|---|---|
| **Understand how the library keeps rules applied as context fills** (re-injection, principle 5, terminal re-read, gates) | [**CONTEXT-MANAGEMENT.md**](CONTEXT-MANAGEMENT.md) |
| **Work out why a skill never fired at all** (skill *activation*) — only the frontmatter `description` auto-loads, so it is the whole trigger classifier; the body is inert until the Skill tool runs | [CONTEXT-MANAGEMENT → the precondition all six defenses assume](CONTEXT-MANAGEMENT.md#the-precondition-all-six-defenses-assume-measured-in-the-field-2026-08-05) |
| Set up the per-prompt **re-injection hook** | [README → Always-on routing, layer 3](../README.md#always-on-routing-recommended) |
| Understand *why* a rule sometimes still gets dropped | [WHY-COMPLETENESS-RESIDUAL.md](WHY-COMPLETENESS-RESIDUAL.md) |

## Know whether it works (evidence)

| I want to… | Go to |
|---|---|
| See every measured number at a glance | [`evals/results/RESULTS.md`](../evals/results/RESULTS.md) |
| Read the measured case (vs. unguided + vs. competitors) | [WHY-IT-WORKS.md](WHY-IT-WORKS.md) |
| Check the lift isn't model-specific (cross-model) | [CROSS-MODEL.md](../evals/results/2026-07-22/CROSS-MODEL.md) |
| See the third **cross-family** confirmation (Google, +0.55) | [CROSS-FAMILY-GEMINI.md](../evals/results/2026-08-13/CROSS-FAMILY-GEMINI.md) |
| Read the **real-repo** audit — real CVEs, +0.00, and how two arms got contaminated | [REAL-REPO-AUDIT.md](../evals/results/2026-08-13/REAL-REPO-AUDIT.md) |
| Check what the library covers for **business logic** flaws (all 10 WSTG-BUSL sub-tests, with depth scores) | [COVERAGE-BUSINESS-LOGIC-2026-08-13.md](COVERAGE-BUSINESS-LOGIC-2026-08-13.md) |
| Run the evals myself | [`evals/README.md`](../evals/README.md) |
| See the SOTA-vs-competitor benchmark | [COMPETITOR-BENCHMARK.md](../evals/results/2026-07-13/COMPETITOR-BENCHMARK.md) |
| Read a shareable write-up of the key finding | [writeups/completeness-blind-spot.md](writeups/completeness-blind-spot.md) |
| See what the library does **not** lift (the honest +0.00s) | [AUDIT-PROCESS.md](../evals/results/2026-07-20/AUDIT-PROCESS.md) |
| Understand why the **audit** half has no measured lift (**9 instruments, 4 designs** — closed 2026-08-14) | [UNSCOPED-AUDIT.md](../evals/results/2026-07-30/UNSCOPED-AUDIT.md) · [DEAD-PATH.md](../evals/results/2026-07-30/DEAD-PATH.md) |
| See a prediction written down **before** the run that killed it | [PRE-REGISTRATION.md](../evals/results/2026-07-30/PRE-REGISTRATION.md) |
| See why a **freshness** lift shrinks over time, and what restores it | [ITEM-20](../evals/results/2026-08-25/ITEM-20-FRESHNESS-ROUTING.md) (+0.53 → +0.30 as the set ages) · [ITEM-21](../evals/results/2026-08-25/ITEM-21-REFRESHED-FRESHNESS.md) (re-authored: **+0.67**) |
| Check whether **routing** still helps on a current model | [ITEM-20](../evals/results/2026-08-25/ITEM-20-FRESHNESS-ROUTING.md) — 0.87 → 0.99, and *not* saturated |
| See whether the library stops defects being **written** (not just found) | [BUILD-SAFE 2026-08-21](../evals/results/2026-08-21/BUILD-SAFE.md) — 0.81 → 1.00 on seven classes, with its five limits stated |
| Check how audit reports are scored for **calibration** (and why it is never reported as a lift) | [BUILD-SAFE 2026-08-21 §2](../evals/results/2026-08-21/BUILD-SAFE.md) · `evals/run-calibration.py` |
| See a measurement that **refuted one of this library's own claims** | [COMPLETENESS-PADDING.md](../evals/results/2026-09-01/COMPLETENESS-PADDING.md) — 400 lines of competing guidance cost **−0.01**, so the "load lean or lose applied rules" claim was withdrawn |
| Understand **why some lifts expire and others don't** (knowledge vs salience) | [WHY-SALIENCE-LASTS.md](WHY-SALIENCE-LASTS.md) — the prediction, and what would falsify it |
| Check whether a rule survives a prompt that argues **against** it (prompt-independence) | [`evals/run-prompt-independence.py`](../evals/run-prompt-independence.py) — same task at supportive / neutral / **competing** pressure, three arms |
| Read an eval that failed as an *instrument* rather than as a result | [BUILD-SAFE.md](../evals/results/2026-07-30/BUILD-SAFE.md) |
| See the edges of the do-not-reimplement rule (§3.9.6), as worked cases | [`evals/cases/reimplement.jsonl`](../evals/cases/reimplement.jsonl) — documentation, never run |
| Know what the audit hunts that a scanner can't (inert controls, **controls that block everything**, **a working control applied to part of its population**, **security prose the code doesn't keep**, unreached dependencies, stale decisions, refutation, absence claims) | [README → What the audit hunts](../README.md#what-the-audit-hunts-that-a-scanner-cant) |
| Set up a refutation that actually refutes — a **restricted refuter**, only the artifact crossing over, a **numeric confidence threshold** fixed in advance | [`sota/rules/03` §4a](../skills/sota/rules/03-audit-findings.md) |
| Report a **behavioural** finding (crash, race, agent-produced) — the N-of-N reproduction rule | [`sota/rules/03` §2](../skills/sota/rules/03-audit-findings.md) |
| Verify a **fix**, and read a repeat audit's **yield curve** across waves | [`sota/rules/01` §4](../skills/sota/rules/01-audit-methodology.md) |
| Fan out parallel agents without them **converging on the same finding** | [`sota-llm-engineering` rules/04 §7](../skills/sota-llm-engineering/rules/04-agents-tools.md) |
| Rate a finding: severity, **chain closure**, the diff baseline, evidence, refutation, the report template | [`sota/rules/03-audit-findings.md`](../skills/sota/rules/03-audit-findings.md) (scoping, tooling and hygiene stay in [`rules/01`](../skills/sota/rules/01-audit-methodology.md)) |
| Harden a tool that **ingests repositories it did not author** (scanner, SAST wrapper, review bot, agentic analyser) | [`sota-sandboxing` rules/05 §7](../skills/sota-sandboxing/rules/05-ai-agent-sandboxing.md) |
| Read the retraction + the retired anchoring hypothesis | [SILENT-FAILURE.md](../evals/results/2026-07-20/SILENT-FAILURE.md) |

## Contribute / operate the repo

| I want to… | Go to |
|---|---|
| Land a change (branch → PR → checks → merge) | [AGENTS.md → Landing a change](../AGENTS.md#landing-a-change) |
| Know the invariants CI enforces | [AGENTS.md → Invariants](../AGENTS.md#invariants-enforced-in-pre-commit-and-ci) |
| Understand why a doc that *describes* the gates can't quietly drift from them | **invariant 17** — it derives the count from `check-invariants.sh`'s own `[k/N]` markers and requires every stated count and restated coverage list to match; a number inside `"quotes"` is read as history, not a claim ([AGENTS.md → Invariants](../AGENTS.md#invariants-enforced-in-pre-commit-and-ci)) |
| See which conventions are *enforced* vs. prose, and why the rest aren't gated | [CONVENTIONS-LEDGER.md](CONVENTIONS-LEDGER.md) |
| **Prove the gates themselves can still fail** (a passing gate shows the tree is clean, not that the check works) | **`./scripts/check-invariants.sh --self-test`** — the front door. Its structural pass fails on any check that is neither probed nor declared unprobeable, then runs `scripts/check-negative-controls.sh`, which injects a known-bad per check and requires *the intended one* to complain; CI job *Negative controls* |
| **Check no eval runner has gone dead** (one raised before its first API call for three weeks; `--help` cannot see it) | **`python3 evals/smoke-runners.py`** — proves each runner can *start* and is **import-safe** (side effects behind `__main__`, so tooling that imports it does not run it), not that it is correct ([why](../evals/results/2026-08-27/ROUTING-REGRESSION-TOKEN-COUNT.md)) |
| Understand **how an eval set was built** before trusting a number from it | Every `evals/cases/*.jsonl` header states its **selection rule** and whether it is a **measurement** set (a lift may be reported, so cases must never be picked by a model's score) or a **regression** set (selection-by-outcome is the point) — `sota-llm-engineering` rules/01 §8 |
| Fix a **routing gap** — the right skill existed and the task never reached it | Fix the *trigger* (a skill's `description` is the only auto-loading text), then pin it with a **regression case** in `evals/cases/desc-routing-regressions.jsonl` — never in the measurement set |
| Add a check and not forget its known-bad | **Nothing to remember — it is invariant 19**, and it runs on every invocation (~50 ms). A check that is neither probed nor listed in the harness's *NOT COVERED* block fails the build, and the exempt set is **pinned**, so silencing it by exempting your new check is a deliberate edit a reviewer sees. It exists because the prose instruction it replaced did not stop invariant 18 shipping probe-less in its own commit (`sota-code-security` rules/12 §1b applied to us) |
| Understand why a `§` section reference can't quietly rot | **invariant 18** — invariant 8 resolves only `[text](file.md)` links, so ~1,300 prose `§` references were checked by nothing; it found six live defects on its first run and caught 27 more when `rules/10`/`rules/11` were split. **Scope is `skills/` only** — `docs/` references are still on trust ([AGENTS.md → Invariants](../AGENTS.md#invariants-enforced-in-pre-commit-and-ci)) |
| Full contribution conventions | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| Re-render a README diagram after editing its HTML (sizes, why `file://` fails) | [CONTRIBUTING.md → Rendered assets](../CONTRIBUTING.md#rendered-assets) |
| Check a repo's setup is real, not just configured | `scripts/verify-setup.sh` (deterministic) + [VERIFY-SETUP.md](VERIFY-SETUP.md) (the judgement half) |
| Cut a release | [RELEASING.md](../RELEASING.md) |
| Keep fast-moving claims accurate (sweep runbook + named high-rot targets) | [MAINTENANCE.md](MAINTENANCE.md) |
| See which external ideas were adopted/rejected and why | [ADOPTION-LOG.md](ADOPTION-LOG.md) |
| See what's planned / open | [ROADMAP.md](ROADMAP.md) |
| Report bad guidance or a leaked secret | [SECURITY.md](../SECURITY.md) |

## Reference

| I want to… | Go to |
|---|---|
| The full skill list + what each covers | [README → Skills](../README.md#skills) |
| The master router (routing table, principles, workflows) | [`skills/sota/SKILL.md`](../skills/sota/SKILL.md) |
| Release history | [CHANGELOG.md](../CHANGELOG.md) (older: [archive](CHANGELOG-archive.md), [archive-2](CHANGELOG-archive-2.md)) |
| Past audits | [AUDIT-2026-07-01](AUDIT-2026-07-01.md), [AUDIT-2026-07-10](AUDIT-2026-07-10.md) |
