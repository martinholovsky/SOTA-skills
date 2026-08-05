# Adoption Log — external ideas evaluated for this library

A curated library earns trust by being deliberate about what it adopts. This log
is the audit trail for that: when an external repo, paper, or review suggests an
idea, it gets an entry here with a **verdict and a reason** — adopted, rejected,
deferred, or superseded — and, when adopted, a pointer to exactly where it landed.
A rejection recorded with its reason is as valuable as an adoption: it stops the
same idea being re-litigated every time someone finds the same popular repo.

The discipline is borrowed (see entry **2026-07-24 #5**) from the
[training-knowledge-vault](https://github.com/Eolas-bith/training-knowledge-vault)
lessons-log — its own best structural idea, applied to ourselves.

## How this log works

- **States:** `adopted` · `rejected` · `deferred` · `superseded`. Every entry
  ends in one of these — nothing stays `open` here; if it needs more thought it
  is `deferred` with the condition to revisit.
- **Observation before diagnosis.** State what the source *actually says* and
  what we *verified against our own tree* separately from the verdict. The
  temptation is to declare a "gap" from a keyword search; the rule is to read the
  candidate home file and confirm the idea is genuinely absent before adopting —
  a `rejected: already covered` verdict must cite the file:line that covers it.
- **Landed-in pointer, not a promise.** An `adopted` entry names the concrete
  change (rule file + section, or script + check) and the release it shipped in.
  This is the commit-hash-on-apply idea from the source vault, expressed as our
  version + PR rather than a bare hash. Adoptions land between releases, so write
  `unreleased` when the version isn't known yet — the release cut greps for that
  word and stamps it ([RELEASING.md](../RELEASING.md) §1).
- **Convergent ≠ adopted.** When an external repo independently arrives at
  something we already do, record it as `rejected: already ours` — it is
  validation, not a change. Do not manufacture a diff to "adopt" it.

## Log

| Date | Source | Idea | Verdict | Landed in |
|------|--------|------|---------|-----------|
| 2026-07-24 | [training-knowledge-vault](https://github.com/Eolas-bith/training-knowledge-vault) `vault-doctor.py` | Resolve internal Markdown links in CI so a move/rename can't leave dead links | **adopted** | `scripts/check-invariants.sh` invariant 8 · v1.19.1 |
| 2026-07-24 | training-knowledge-vault lesson L-022 | A prompt that references a schema in an unloaded file silently fabricates it — inline what the model must obey | **adopted** | `sota-llm-engineering/rules/02` §1 · v1.19.1 |
| 2026-07-24 | training-knowledge-vault lesson L-023 | "Do not surface" instructions over in-context data are not a control (attention leakage); segregate structurally | **adopted** | `sota-code-security/rules/10` §2.12 · v1.19.1 |
| 2026-07-24 | training-knowledge-vault L-002 + Phase-1 capture | Confidence-gate before acting on IOCs; capture symptoms, don't assert root cause | **rejected: already covered** | — |
| 2026-07-24 | training-knowledge-vault lessons-log loop | A locked, triaged, commit-tracked ledger for turning observations into curated changes | **adopted (as this file)** | `docs/ADOPTION-LOG.md` · v1.19.1 |
| 2026-07-24 | training-knowledge-vault (structure) | Per-file `volatility`, stable `id`s, personas, prompts, sessions, model-map | **rejected: non-fit** | — |
| 2026-07-24 | training-knowledge-vault (convergent) | `AGENTS.md` + tool adapters; nav-parity CI check; "encode the lesson as a check"; system-prompt token budgeting | **rejected: already ours** | — |
| 2026-07-24 | [swarm-forge](https://github.com/unclebob/swarm-forge) `engineering.prompt` | Separate the testable core from the environment-bound shell; only the core participates in coverage/mutation/complexity tooling | **adopted** | `sota-architecture/rules/02` §14 · v1.19.2 |
| 2026-07-24 | swarm-forge `hardender.prompt` | Differential mutation against a persisted manifest — gate on new survivors, not an absolute score | **adopted** | `sota-testing/rules/06` §6.3 · v1.19.2 |
| 2026-07-24 | swarm-forge `crap4go`/`crap4clj` tools | Complexity × coverage composite to rank where the next test belongs | **adopted** | `sota-testing/rules/07` §7.2 · v1.19.2 |
| 2026-07-24 | swarm-forge (convergent) | Scoped/diff mutation; mutation as a control probe; read survivors don't average; reviewer must not modify audited code; heartbeat on long runs; verify the other role ran the tool | **rejected: already ours** | — |
| 2026-07-24 | swarm-forge `engineering.prompt` Startup Tools | Resolve every tool at latest upstream each run; never reuse cached/vendored copies | **rejected: contrary** | — |
| 2026-07-28 | [claude-project-scaffold](https://github.com/martinholovsky/claude-project-scaffold) `templates/troubleshooting.md.tmpl` | A repo-resident Symptom → Diagnosis → Fix playbook where solved dev failures accrue | **adopted** | `sota-docs-workflow/rules/01` §9 · v1.19.3 |
| 2026-07-28 | claude-project-scaffold `templates/CLAUDE.md.tmpl` | A minimal four-block skeleton for the agent file (stack / commands / conventions / traps) | **adopted** | `sota-docs-workflow/rules/01` §7 · v1.19.3 |
| 2026-07-28 | claude-project-scaffold `templates/adr-index.md.tmpl` | An ADR `index.md` status table + sequential kebab-case numbering, committed with the code | **adopted** | `sota-architecture/rules/01` §4 · v1.19.3 |
| 2026-07-28 | claude-project-scaffold (gap it exposed, not content it had) | A fresh repo inherits nothing from an ambient/global agent setup — bootstrap order and canonical-file mechanics | **adopted** | `sota-docs-workflow/rules/01` §10 · v1.19.3 |
| 2026-07-28 | claude-project-scaffold README "Design Philosophy" + context-rot rationale | Include only what the agent would get wrong without it; short agent files beat bloated ones | **rejected: already ours** | — |
| 2026-07-28 | claude-project-scaffold `templates/adr-template.md` | Full ADR template with alternatives and consequences | **rejected: already covered** | — |
| 2026-07-28 | claude-project-scaffold `.claude/memory/`, `commands/`, `hooks/`, `presets/`, `scaffold.sh` | Generated slash commands, lint-on-edit hook, memory index, preset engine | **rejected: runtime-bound** | — |
| 2026-07-28 | Live agent session scaffolding [asterinas](https://github.com/asterinas/asterinas) (`aster-env.sh`) | A host-capability report: probe the machine, print per target what works and what each gap blocks | **adopted** | `sota-docs-workflow/rules/01` §6 · v1.19.4 |
| 2026-07-28 | Same session (`rust-post-edit.sh`, check-only by design) | Automation firing on an agent's edits must report, not rewrite — a rewrite stales the agent's own view of the file | **adopted** | `sota-docs-workflow/rules/01` §7 · v1.19.4 |
| 2026-07-28 | Same session — `docker`-only probe missed a running podman | Detect by capability, not by one implementation's name | **rejected: already ours** | — |
| 2026-07-28 | Same session — `tools/format_all.sh` exits 0 while checking nothing; `AGENTS.md` pins a stale toolchain; gate proven by making it fail; bash 3.2 empty-array and `set -e` in command substitution | Four rules of ours, independently rediscovered in the wild | **rejected: already ours** | — |
| 2026-07-28 | Two live verification runs on an [asterinas](https://github.com/asterinas/asterinas) clone | A read-only setup check: is the library reaching this repo, is its agent file true, are its gates real | **adopted** | `docs/VERIFY-SETUP.md` · v1.19.5 |
| 2026-07-28 | Same runs — a review workflow with 5/5 *skipped* runs | A control whose trigger never fires: all-skipped is not all-green | **adopted** | `sota-code-security/rules/10` §2.13 · v1.19.5 |
| 2026-07-28 | Same runs — 7/7 `make` targets resolved while the stated toolchain was 7 months stale | Verify an agent file's claims, not just that its commands exist | **adopted** | `sota-docs-workflow/rules/01` §7 · v1.19.5 |
| 2026-07-30 | A user-authored audit prompt for the "declared but not reached" class (CVEs/versions explicitly out of scope) | Trace every direct dep / registered module / plugin to a real entrypoint; prove "unreached" by deleting it and running the real build | **adopted** | `sota-devsecops/rules/03` §3.9 · v1.19.7 |
| 2026-07-30 | Same prompt | Leverage ratio: symbols called vs transitive modules inherited (<5 / >10 → replace-in-house candidate) | **adopted** | `sota-devsecops/rules/03` §3.9.4 · v1.19.7 |
| 2026-07-30 | Same prompt | Upstream health from a primary source fetched this session (`gh api` archived / `pushed_at` / contributor count), reported as dates | **adopted** | `sota-devsecops/rules/03` §3.9.5 · v1.19.7 |
| 2026-07-30 | Same prompt | Never reimplement an algorithm whose output is persisted and must stay comparable with stored data (fuzzy hashes, digests, tokenizers) | **adopted** | `sota-devsecops/rules/03` §3.9.6 · v1.19.7 |
| 2026-07-30 | Same prompt | A/B/C/D finding taxonomy (DELETE / REPLACE IN-HOUSE / KEEP / UNMAINTAINED-but-keep) with the successor named for D | **adopted** | `sota-devsecops/rules/03` §3.9.6 · v1.19.7 |
| 2026-07-30 | Same prompt | Negative claims need two independent methods; `file:line \| claim \| severity \| effort \| evidence`; mark the unverified | **rejected: already ours** | — |
| 2026-07-30 | Validating the above (`gh api` on 8 tool repos) | `gh api` follows renames silently — a 200 under the manifest's name is not evidence the project is still there; read `full_name` back | **adopted** | `sota-devsecops/rules/03` §3.9.5 · v1.19.7 |
| 2026-07-30 | Same validation — Ruby/.NET candidates are single-maintainer, low-adoption | Where no established tool exists, say so and go straight to the deletion proof rather than naming a fringe tool | **adopted** | `sota-devsecops/rules/03` §3.9.2 · v1.19.7 |
| 2026-07-30 | Two user-authored "silent-control & dead-path/dead-layer" audit prompts | **Duration, not result** — a stage reporting "nothing found" faster than its claimed work allows did not run; highest-yield tell, no code reading needed | **adopted** | `sota-code-security/rules/11` §2.1 + `sota-performance/rules/01` §9a · v1.19.8 |
| 2026-07-30 | Same prompts | **Scope of the check** — every gate prints how many items it examined; `0 checked, 0 failed, exit 0` is the family's signature | **adopted** | `rules/11` §2.2 + `scripts/check-invariants.sh` · v1.19.8 |
| 2026-07-30 | Same prompts | Scale-dependent silence: size-gated paths fixtures never cross; budgets that truncate **coverage** while reporting a normal result | **adopted** | `rules/11` §3.1 + `sota-testing/rules/03` §3.7a · v1.19.8 |
| 2026-07-30 | Same prompts | Stale-artifact no-op: a cache/tag/fingerprint key narrower than the behaviour — "what input can change while the key stays constant?" | **adopted** | `rules/11` §3.2 · v1.19.8 |
| 2026-07-30 | Same prompts | Format assumption from one sample; lenient parsers returning plausible-but-wrong values instead of raising | **adopted** | `rules/11` §3.3 · v1.19.8 |
| 2026-07-30 | Same prompts (the "assertions" entry in their gate list) | An `assert` is not a control: `-O`/`PYTHONOPTIMIZE`, `-DNDEBUG`, and Java's default-off assertions delete it in production | **adopted** | `rules/11` §4 + `sota-python`/`sota-c-cpp`/`sota-jvm` · v1.19.8 |
| 2026-07-30 | Same prompts | ACTIVE / LATENT / REFUTED labels; one *discriminating* proof per class; report REFUTED too | **adopted** | `rules/11` §5 · v1.19.8 |
| 2026-07-30 | Second prompt only | A fix that moves a detector's decision boundary needs known-bad/known-good validation before shipping | **adopted** | `rules/11` §5 · v1.19.8 |
| 2026-07-30 | Both prompts | Mutation-test every gate; vacuous tests; telemetry silence; comments are a hypothesis; the disqualifier list | **rejected: already covered** | — (`rules/10` §3, §2.9, §4; `sota-testing` rules/06 + rules/09) |
| 2026-07-30 | Second prompt's seed examples (target-repo `file:line` calibration) | Naming a specific repo's files as calibration anchors | **rejected: non-fit** | — (the library stays generic; the *classes* were adopted, the examples were not) |
| 2026-08-01 | A separate live agent session, three proposals handed over as analysis | A same-class checker (classifier/judge from the same model family) is **not** an independent layer — common-cause failure; escalate-only cascades are deductively worse | **adopted** | `sota-code-security/rules/08` §1 · v1.19.9 |
| 2026-08-01 | Same handover | A TEE does not fix a **completeness** gap — "never recorded" is a liveness failure, outside the confidential-computing guarantee | **adopted** | `sota-code-security/rules/04` §8 · v1.19.9 |
| 2026-08-01 | Same handover | A vendor control-plane API reporting `confidentialCompute: true` over an instance whose CC status is OFF | **rejected: already covered** | — (`rules/10` §2.2 line 102 "check the shipped artifact, not the checkout" + §2.11 shipped-artifact gaps) |
| 2026-08-04 | An inert-control audit prompt (classes 6–12), handed over as a spec | **Unearned claims in output are words as well as numbers** — `verified`/`reachable from`/`tainted`, severity or confidence from a constant; match the claim's *shape*, and read the sentence before counting it | **adopted** | `rules/10` §2.10 · unreleased |
| 2026-08-04 | Same prompt (class 8) | **The guard is an instance of what it guards** — a coverage test whose *scope* is narrower than the population and whose *predicate* the defect satisfies (`"auth=" in line` accepts `auth=None`); a tripwire nested in another gate's success branch; a denominator counting only survivors | **adopted** | `rules/11` §7.1 · unreleased |
| 2026-08-04 | Same prompt (class 11) | **Contract drift by interaction** — a producer/consumer seam *no schema declares*, where the trigger is a config-level backend/frontend swap and both sides' isolation tests pass | **adopted** | `rules/11` §3.4 · unreleased |
| 2026-08-04 | Same prompt (class 12) | Sample and read before you count; a control validated on inputs that **cannot** produce the failure proves nothing; when a wrapper reports an empty reason, go one layer down | **adopted** | `rules/11` §7.2 · unreleased |
| 2026-08-04 | Same prompt (class 9) | The *detection* half of test-environment leakage: **block egress and re-run**; the config object the SUT never reads; assertions that contradict the test's own name | **adopted** | `sota-testing/rules/02` §2.6 + checklist · unreleased |
| 2026-08-04 | Same prompt (class 7) | Run every script CI, a hook or a runbook references **before** reading any of them; record which produce output | **adopted** | `rules/11` §6 · unreleased |
| 2026-08-04 | Standard test-smells catalog ([testsmells.org](https://testsmells.org/pages/testsmells.html), after van Deursen et al.) | **Resource optimism** as its own smell, and *mystery guest* in its original external-resource sense — ours had narrowed the standard name to a readability defect | **adopted** | `sota-testing/rules/02` §2.7 · unreleased |
| 2026-08-04 | [GitHub Docs — Status checks](https://docs.github.com/en/pull-requests/reference/status-checks) | A **skipped job reports *Success*** and does not block a PR "even if it is a required check" — worse than §2.13's "all-skipped is not all-green" | **adopted** | `rules/10` §2.13 · unreleased |
| 2026-08-04 | Verified locally this session | `go test ./...` over a package with no test files exits **0** — the empty-denominator rule instantiated in the toolchain | **adopted** | `rules/11` §2.2 · unreleased |
| 2026-08-04 | Cross-skill sweep prompted by the same prompt | **A control parked in observe-only mode** (Kyverno `Audit`, PSA `warn`, WAF detection-only, `SCMP_ACT_LOG`, CSP report-only, DMARC `p=none`, `--soft-fail`) is inert as a *destination*; the staged rollouts existed, the inert-control framing did not | **adopted** | `rules/10` §2.14 · unreleased |
| 2026-08-04 | Same prompt (classes 7, 10, 12 — the covered remainder) | Dead instruments; record rot; the auditor's instrument as a control; negative-claim burden | **rejected: already covered** | — (`rules/10` §2.2/§2.13, `rules/11` §7.1–7.3; `rules/10` §2.9, `rules/11` §5 "comments are a hypothesis", `sota/rules/01` §6 decision ledger) |
| 2026-08-04 | Same prompt — candidates checked and found already ours | Alerting-pipeline dead-man's switch; admission `failurePolicy: Ignore`; `continue-on-error`/soft-fail gate steps; suppression-baseline rot; coverage-target gaming | **rejected: already ours** | — (`sota-observability` rules/04 + rules/02, `sota-kubernetes` rules/05, `sota-devsecops` rules/05, `sota-testing` rules/07 §7.2) |
| 2026-08-05 | Two commissioned research reports on inert controls ("Missing SOTA Audit Controls" = **A**; "The Inert-Control Class" = **B**) | **Per-target kill verification** — a guard protects a population; watching it reject one member says nothing about the other 19 (the 2-of-20 tripwire). 100% kill rate for a security gate | **adopted** | `sota-code-security/rules/12` §3 · unreleased |
| 2026-08-05 | Report B (Q3, instance 1) | **Metamorphic relation as a liveness oracle for a tool** — when you cannot state the correct output, state how it must *change*; the only diagnostic that catches an analyser emitting an empty-but-well-formed artifact | **adopted** | `sota-code-security/rules/11` §2.6 · unreleased |
| 2026-08-05 | Report B (Q5), verified against primary sources | **The standards gap**: SSDF PW.8.2/PO.3.3 and CRA Annex VII require a record that the scan *ran*; Scorecard's SAST check detects tool *presence* only; **none require evidence a gate can fail** | **adopted** | `sota-devsecops/rules/05` §5.6 · unreleased |
| 2026-08-05 | Both reports (Q1/Q2) | The cross-discipline lineage the library used unnamed: **proof test** (IEC 61508 dangerous-undetected), **positive control** (assay validity), **BITE** (aviation), **poka-yoke**, **vacuous satisfaction** (Ball & Kupferman), **the test oracle problem** (Barr et al., IEEE TSE 41(5), 2015) | **adopted** | `rules/12` intro + §3, `rules/11` §2.6 · unreleased |
| 2026-08-05 | Report A only — the one thing B missed | **EvoMap** (arXiv:2605.25815, 1.5M assets / 128K agents): "over 84% of approved assets bypass quality checks using vacuous tests (e.g. `console.log()`)" — hard data that self-supplied evidence collapses at scale. B asserts no such corpus exists | **adopted** | `sota-code-security/rules/12` §2.4 · unreleased |
| 2026-08-05 | Report A, Rule 3 | "Enforce a minimum **Mutation Score** threshold in CI" | **rejected: contrary** | — contradicts `sota-testing` rules/07 §7.2 ("never set a global percentage target — Goodhart's law is undefeated") and rules/06 §6.3 differential mutation (gate on *new survivors*, adopted 2026-07-24 from swarm-forge). B's per-gate kill rate is compatible and was adopted; A's global score is not |
| 2026-08-05 | Report B, R8 | **GSN / assurance-case notation** for critical controls | **rejected: non-fit** | — a notation, not a mechanism; its own cited critique (Leveson: arguments "assume the conclusion") points back at what we already run, `sota/rules/01` §7 adversarial refutation |
| 2026-08-05 | Report A, Rule 4 | Cryptographically **signed volumetric execution artifacts** verified by release gateways | **rejected: partial — insight kept, machinery dropped** | the insight (SLSA proves execution, never efficacy) landed in `sota-devsecops/rules/05` §5.6; the signing machinery is speculative and unbuilt |
| 2026-08-05 | Both reports — checked and found already ours | R2 execution evidence/volumetric assertions; R3 fail-closed gates; R6 assertion polarity + egress sandbox; R7 meta-monitoring/heartbeat; the **ML Test Score** rubric ("worth adopting wholesale") | **rejected: already ours** | — (`rules/11` §2.2/§2.4/§3.1, `rules/10` §2.1/§2.4/§2.6, `sota-testing/rules/02` §2.6–2.7, `sota-observability/rules/04:249`, and `sota-ml-engineering/rules/04:6` which has cited ML Test Score since before these reports) |

## Entries

### 2026-07-24 — training-knowledge-vault (Eolas-bith), five ideas

Source: <https://github.com/Eolas-bith/training-knowledge-vault>, read at full
depth (code + methodology docs), 2026-07-24. It is an Obsidian-based
agent-followable knowledge vault for analytical/CTI work — a *runtime agent OS*,
not a skills library — so most of its machinery targets problems we don't have.
The five ideas we surfaced and their dispositions:

1. **Internal link resolution in CI** *(adopted → invariant 8)*. Their
   `vault-doctor.py` resolves every `[text](file.md)` link and errors on a
   miss. **Verified gap:** `grep` over `scripts/` found no link resolution, and a
   dry run of the new check immediately surfaced **5 real broken links** in
   `evals/results/**` (`../../docs/…` where the tree needs `../../../docs/…`) —
   fixed in the same change. Scoped to `*.md` targets: broadening to every
   relative link false-positives on prose/code fragments matching `[x](y)` (e.g.
   `(x: T)`, `(std|default)`), with no rot-catching upside.

2. **Self-contained prompts** *(adopted → `sota-llm-engineering/rules/02` §1)*.
   Their L-022: a prompt that points at a schema in another file fabricates that
   schema whenever the file isn't in context. **Verified gap:** no equivalent
   rule in `rules/02` (which covers budget, caching, output schemas, but not
   *referencing out-of-context material*). Scoped carefully so it does not
   contradict our own on-demand rule loading — a coding agent has a loader/router;
   a model executing a prompt does not.

3. **Instruction ≠ control over in-context data** *(adopted →
   `sota-code-security/rules/10` §2.12)*. Their L-023: "do not surface" over
   private context is not protection — attention leakage shapes output even
   without quotation; segregate structurally. `rules/08` states the
   prompt-injection/authz-in-prompt pieces ad hoc; **the silent-control *class*
   framing** (delete the sentence → nothing observable differs → finding) was
   absent from `rules/10`. Added there with cross-refs to `rules/08` §1–2 and
   `rules/07` §2.

4. **Confidence-gate + observation-vs-diagnosis** *(rejected: already covered)*.
   Confidence-gating before auto-containment already lives in
   `sota-detection-engineering/rules/04` (`:175` auto-containment gate, `:124`
   high-confidence-only correlation). The "flag the symptom, don't assert root
   cause" nuance is marginally additive against `rules/06` §4 ("scope before you
   eradicate") and would be padding — which the library's own `rules/10` §5
   forbids ("say 'nothing found' rather than pad with weak findings"). Applying
   that discipline to ourselves: no change.

5. **The lessons-log loop** *(adopted as this file)*. Their strongest structural
   idea: Capture → Aggregate → Review → Apply with skills **locked** until an
   explicit apply step, triage states, and a commit hash recorded on application.
   We already had ad-hoc adoption tracking (memory + CHANGELOG); this file makes
   it an auditable ledger with the same discipline, minus the runtime machinery.

**Not surfaced as candidates (recorded for completeness):** per-file
`volatility` (we *retired* per-file freshness markers for a single root
`LAST-VERIFIED` on purpose — re-adopting would reverse a deliberate decision);
`id`/personas/prompts/sessions/model-map (vault-runtime concerns, no payoff for a
curated on-demand tree). Convergent-not-adopted: `AGENTS.md` + adapters (we use
symlinks), the nav-parity check (≈ our invariant 7 router-drift), "encode the
lesson as a new check" (≈ our per-audit new-invariant practice), and treating the
always-loaded context file as a token budget (≈ our incremental-loading thesis in
[CONTEXT-MANAGEMENT.md](CONTEXT-MANAGEMENT.md)).

### 2026-07-24 — swarm-forge (unclebob), three adoptions

Source: <https://github.com/unclebob/swarm-forge>, read at the source level on
2026-07-24 — `main` (documentary branch: shared constitution articles plus the
tmux/worktree orchestration scripts) and the runnable `six-pack` and
`adversaries` branches (role prompts). It is a **harness**: tmux session and git
worktree per role, a handoff daemon between agent inboxes, and a layered
"constitution" of `.prompt` files that agents are instructed to obey. Its
engineering content is thin by design — `engineering.prompt` is 45 lines and
`local-engineering.prompt` on `six-pack` is 5 — so the overlap with this library
is narrow but sharp where it exists.

1. **The testability boundary** *(adopted → `sota-architecture/rules/02` §14)*.
   `engineering.prompt:22-23` separates testable modules from ones that are
   "environmentally unsuitable" (GUI, external devices, hangs under automation),
   directs that the unsuitable region be minimized, and lets **only** testable
   modules participate in coverage, mutation, and complexity tooling.
   **Verified gap:** `grep -rni "humble object|near IO|adapter shell|untestable"`
   over `skills/sota-architecture/rules/*` and `skills/sota-testing/` returned
   **zero hits**. We had hexagonal ports/adapters (rules/02 §4) and the
   generated/vendored coverage exclusion (`sota-testing/rules/07:81`) but not the
   humble-object pattern that connects them — the design rule that makes every
   test metric interpretable. Landed as an explicit, machine-readable core/shell
   split with a shell-growth-is-an-architecture-finding clause, cross-referenced
   from both testing rules.

2. **Differential mutation against a manifest** *(adopted →
   `sota-testing/rules/06` §6.3)*. `hardender.prompt` always runs mutation
   differentially against a persisted manifest rather than scoring from scratch.
   **Verified partial gap:** rules/06:153 already had "scoped, not global — run
   on the diff", and the survivors-are-findings triage; the *baseline* mechanism
   that turns those into a CI gate on **new survivors only** (the mutation
   analogue of our coverage ratchet) was absent. Adopted with two conditions the
   source repo itself demonstrates the need for: pin the mutation engine beside
   the baseline, and never hand-edit it.

   The pinning condition is a live defect in the source. `engineering.prompt:4-6`
   instructs every role to resolve each tool at "latest available upstream" at
   its own startup and explicitly **not** to reuse cached or vendored copies, and
   none of the seven tool repos (`mutate4go`, `crap4go`, `dry4go`, `clj-mutate`,
   `crap4clj`, `dry4clj`, `Acceptance-Pipeline-Specification`) carries a single
   tag — verified via the GitHub API on 2026-07-24 — so "latest" is whatever HEAD
   is at that moment. Roles that start hours apart in one swarm can therefore diff
   a manifest across engine versions. Our rule states the invariant his prompt
   omits; his install policy is recorded below as `rejected: contrary`.

3. **Complexity × coverage composite** *(adopted → `sota-testing/rules/07`
   §7.2)*. His `crap4*` tools compute the CRAP-style composite (complexity
   weighted by how little of it is verified). **Verified gap:** cyclomatic
   complexity appeared once in the tree, at `sota-testing/rules/01:124`, as one
   input to a risk heuristic — nothing crossed it with coverage to *rank* where
   the next test belongs, which is the question rules/06 previously answered as
   "highest-risk modules". Adopted as a pointer for aiming mutation and review
   effort, explicitly not as a gate (it would Goodhart exactly like a coverage
   threshold).

**Rejected: contrary.** The Startup Tools policy — resolve every tool at latest
upstream on each run, never reuse cached, vendored, or preinstalled copies — is
the inverse of `sota-devsecops` pinning and provenance guidance, and it is what
breaks the differential baseline in item 2. Recorded so the idea is not
re-litigated from the same source.

**Rejected: already ours (six convergences).** Scoped/diff mutation
(`sota-testing/rules/06:153`); mutation as a control probe (`rules/06:158` plus
`sota-code-security/rules/10` §3, where ours additionally names the two traps
that make a green run lie); read survivors rather than average them
(`rules/06:180`); the reviewer must not modify the code under review
(`sota/rules/01-audit-methodology.md:342` §9, "read-only by default", which also
covers secret redaction and the re-audit loop his `reviewer.prompt` has no
equivalent of); a heartbeat on long-running verification so a hang is
distinguishable from work (`sota-shell-scripting/rules/04:147`); and checking
that the upstream role actually ran the tool or justified skipping it
(principle 6, evidence completion). Independent arrival at six of our rules from
a completely different starting point is validation — no diff manufactured.

**Not surfaced as candidates:** the role topology and file-based handoff protocol
(orchestration, not rules), the Gherkin/APS acceptance pipeline (specific to the
author's own tool repos), and the per-role commit byline. Also noted, not
adopted: the constitution's dimensions are entirely internal-quality — mutation,
complexity, duplication, coverage, dependency direction — with no security,
privacy, or operability content anywhere in the articles or role prompts. That is
a scope choice for a harness whose users supply their own project rules, and it
is precisely the axis this library covers; it implies no change here.

**Measurement status:** all three are content refinements adopted on reasoning,
**not measured**. Do not cite a lift for them. The testability-boundary rule is
the only one with a plausible claim to changing generated code; if a future
eval round has spare budget, it is the one worth a completeness case.

### 2026-07-28 — claude-project-scaffold (martinholovsky), three adoptions + one exposed gap

Source: <https://github.com/martinholovsky/claude-project-scaffold>, MIT, read at
full depth (2157 lines, last pushed 2026-04-14), 2026-07-28. It is an
**agent-context scaffolder**, not a repo scaffolder: it generates `CLAUDE.md`,
`.claude/{rules,memory,commands,hooks}`, an ADR directory, and preset-specific
smoke scripts, and touches none of LICENSE, `.gitignore`, CI, or branch
protection. That framing matters for what could be taken — most of its *stated*
philosophy is ground this library already held, and the largest thing we took is
something it does not contain.

**Adopted (3).** The **troubleshooting playbook** (`rules/01` §9) was the clean
gap: a `grep` for `Symptom|playbook|troubleshooting` across `sota-docs-workflow`
and `sota-observability` returned only the on-call/alerting sense — §5 runbooks
(`rules/01:130`), symptom-based paging (`sota-observability/rules/04:108`) —
never the dev-loop artifact where a solved local failure is written down so the
second encounter is a lookup. Our version adds the two disciplines the template
lacks: delete an entry once a root-cause fix makes it a false lead, and treat a
symptom reported three times as a signal to fix the code rather than document it
again. The **minimal agent-file skeleton** (`rules/01` §7) filled a smaller hole
— §7:196 said what content earns its place but gave no shape to hang it on. The
**ADR index and numbering** (`sota-architecture/rules/01` §4) likewise: we had
the format and the "an ADR without a downside is marketing" rule (`rules/01:93`)
but nothing on the directory, and a status column that is all `proposed` is the
cheapest possible read on a stalled decision process.

**The gap it exposed (the largest addition).** The scaffold exists because a new
repo has no agent context — but it treats that as a file-generation problem. The
underlying rule is broader and belongs in the library: an installed skills
library, a personal `~/.claude/CLAUDE.md`, and a house style guide are all
*ambient*, and a fresh repo, a teammate's clone, and a CI runner inherit none of
them. `rules/01` §10 states that, orders the two artifacts that must precede the
first commit (`.gitignore` + secret scanning, LICENSE) with the reason each is
expensive later, splits ambient-vs-repo content in both directions, and records
the `core.symlinks=false` failure mode — symlinks "checked out as small plain
files that contain the link text" (verified against `git help config`), which
silently reduces a symlinked `CLAUDE.md` to the string `AGENTS.md`.

**Rejected: already ours.** The README's "only include what Claude would get
wrong without it" and its context-rot rationale restate `rules/01` §7:196-202
almost phrase for phrase, and this library additionally *measures* the effect
(`docs/CONTEXT-MANAGEMENT.md`, the decay eval). Its ADR template is a longer
form of one we already carry, without the downside-required rule. Convergence,
not a change.

**Rejected: runtime-bound.** The 975-line `scaffold.sh`, the preset variable API,
the `PostToolUse` lint hook, the generated slash commands, and the
`.claude/memory/` index are executable harness machinery, and this library is
Markdown-only by construction — the same disposition the memory-bank and
worktree-lock ideas got in the dev-aid pass (PRs #112-114). The one idea inside
them that generalises, pushing critical invariants into deterministic gates,
was already the router's BUILD step 4 and is now restated for day zero in §10.

**Measurement status:** all four are content refinements adopted on reasoning,
**not measured**. Do not cite a lift. None is a plausible completeness-eval
candidate — they govern repo artifacts, not generated code.

### 2026-07-28 — a live agent session on asterinas, two adoptions

Source: a full Claude Code transcript of "scaffold this repo for development"
run against a clone of <https://github.com/asterinas/asterinas> (a Rust OS
kernel, 4304 commits), 2026-07-28. Not a repo of ideas — a *worked example*,
which makes it a different kind of source: what it produced under real
constraints is the observation, and the question is which parts generalise.

**Adopted (2).** The session's `aster-env.sh` is a **host-capability report** —
it probes the machine and prints, per `make` target, whether it works here and
what each gap blocks. It exists because the repo's canonical loop is a container
the host didn't have, so the agent repeatedly proposed `make kernel` and
repeatedly failed. That generalises to any repo whose documented dev loop
doesn't run on every supported host, and it is genuinely absent here: every
`preflight` in this library is CORS, `doctor` appears nowhere, and §6 covered
joiners rather than host deltas. Landed in `rules/01` §6 with the three
properties that make it work — probe capabilities rather than one
implementation's name, name what each gap blocks, and report rather than gate.

The second is smaller and less obvious: the session's post-edit hook is
**deliberately check-only**, and its header says why — a hook that reformats a
file *after* the agent wrote it invalidates the agent's view, so the next edit
fails or clobbers. Automation aimed at agents therefore reports and lets the
agent apply the fix; rewriting belongs at commit time or in CI, where nothing
holds a live view. Zero hits across the tree; landed in `rules/01` §7.

**Rejected: already ours (two clusters, both worth recording).** The session
self-corrected mid-run — it had probed for `docker` only and missed a running
podman. That is the same class as two defects fixed in the router the same day
(a bare `LICENSE` match missing `LICENSE-MPL`, a hardcoded
`.pre-commit-config.yaml` missing other hook managers), but the principle is
already stated at `sota/rules/01-audit-methodology.md` §"negative claims need
more proof": *a narrow search and a true absence produce identical output*. Three
instances in one day argue for **applying** it at each probe site, not for a new
rule — so it is recorded here as a convergence, with the router fix as the
application.

Separately, the run independently rediscovered four rules of ours: an upstream
`format_all.sh` that exits 0 while its BSD-sed extraction silently checks nothing
(`sota-code-security` rules/10, silent control failure, found in the wild); an
`AGENTS.md` pinning a toolchain three versions stale (`rules/01` §7, "a wrong
command silently corrupts every agent run"); proving the new gate by injecting
faults and watching it fail (our watch-a-guard-fail convention); and both bash
3.2 empty-array-under-`set -u` and `set -e` not firing inside command
substitution (`sota-shell-scripting` rules/01:126 and :48). All four are
validation, not change — but the last is worth noting as a *routing* miss rather
than a coverage one: the rules existed and were rediscovered by debugging.

**Measurement status:** both adoptions are content refinements taken on
reasoning, **not measured**. Do not cite a lift.

### 2026-07-28 — the verification prompt, and what running it twice taught

Source: two live read-only verification runs against a clone of
<https://github.com/asterinas/asterinas>, 2026-07-28 — the second run using a
prompt revised from the first run's own shortcomings. Neither run is an external
repo of ideas; the *artifact under test was our own instruction*, which makes
this the first entry where the observation is a measurement of our own output.

**Adopted (3).** `docs/VERIFY-SETUP.md` fills a hole the library created for
itself: `init-gates.sh` and `gen-agents-md.sh` set a repo up, and nothing ever
checked the result. The distinction it exists to enforce is that **"configured"
and "working" render identically** — a `.pre-commit-config.yaml` with no
installed hook, a scanner nobody has watched reject anything, a CI job whose
every run is skipped.

Four of its checks were **not** designed; they are the first run's limitations,
promoted:

1. *Claims, not just commands.* The first prompt asked only whether named
   commands exist. All seven `make` targets resolved — and the run found, on its
   own initiative, that the file's stated toolchain was seven months stale and
   its description of `make check` was wrong. That extension is now the
   instruction, and the underlying rule landed in `rules/01` §7.
2. *Three states for a hook*, not two: installed / configured-but-not-installed /
   nothing configured at all. The run had to invent `N/A — nothing to install`
   because the prompt offered no verdict that fit; an absent gate is a different
   finding from an inert one.
3. *Executed vs rejected.* Asked only "has it rejected anything", the run
   surfaced something better — a review workflow whose five most recent runs were
   all **skipped**, i.e. a trigger that never fires. That is a genuinely earlier
   failure than the inert-control class we already had, and landed as
   `sota-code-security` rules/10 §2.13.
4. *Can you land the fix?* The run volunteered that the repo was upstream, not
   the operator's — so every finding was an upstream PR, not local config. A fix
   list you cannot land is a different deliverable.

**Not adopted, worth recording.** The run's routing dry-run named 16 specific
rules files; all 16 were verified to exist. That is the check working, not a
change — but it is the reason the dry-run stays in the prompt: a routing
verification that accepted plausible-looking filenames would be the most
dangerous possible false pass.

**Measurement status:** all three are content refinements adopted on reasoning,
**not measured**. Do not cite a lift. `VERIFY-SETUP.md` is prose, not an
enforced invariant — nothing in CI checks that a downstream repo ran it.

### 2026-07-30 — an audit prompt with CVEs ruled out, and what the library couldn't answer

Source: a user-authored audit prompt for the **"declared but not reached"** class —
dependencies, modules, and plugins that are wired in and inert — with an explicit
exclusion: *do not report CVEs or versions, CI already covers that.* No external
repo involved; the artifact under test was the library's coverage of a question
posed from outside it.

That exclusion is what made the prompt useful. Strip CVEs and versions from
`rules/03-dependencies.md` and almost nothing remains that applies: the file's
268 lines were lockfiles, confusion, typosquats, SBOM, scanning, VEX, Renovate,
vendoring — the *vulnerable-shipped-code* question, start to finish. All eight
occurrences of `reachab*` in the file sat in §3.6 and its checklist line, and
every one of them means CVE-triage reachability: is the **vulnerable function**
reached. Whether a dependency is reached *at all* was not asked anywhere in the
library.

**Covered already (1 of 6, and covered well).** The prompt's requirement that
negative claims need two independent methods is stated three times over —
router principle 3, `sota/rules/01` §5, `sota-code-security` rules/10 §5 — plus
a refuter assigned specifically to absence claims (`rules/01` §7.5). So is the
finding format, the effort field, and "mark the unverified".

**The near-misses, which are the interesting part.** Three requirements had a
close relative that stopped one step short:

1. *Proof by construction.* rules/10 §3 is the identical epistemology — no-op the
   control body, run the suite, and it already names the two traps that make the
   result lie (the mutation didn't take; a missing dependency masked the path).
   It had simply never been pointed at a **removed package** instead of a
   disabled control. §3.9.3 is that same procedure re-aimed, and it inherits both
   traps in their dependency form (vendored copy still on disk, lockfile not
   regenerated; a suite that never exercised the path).
2. *Reachability.* `rules/01` §7 already uses reachability as a refutation lens —
   "dead code, an unregistered route… downgrades it to hardening debt" — to kill
   *findings*. Never to evaluate a *dependency*.
3. *The impossible-path trap* (a symbol referenced on a branch the live decoder
   cannot produce) is rules/10 §2.13 one layer down: there, a gate whose trigger
   never fires; here, a dependency whose reference is real but whose branch is
   unreachable. Both are cross-linked now, because the tell is the same — has it
   *ever executed*, not does it exist.

**Genuinely absent (2).** The leverage ratio existed only as a BUILD-time gate on
*adding* a dependency, in two languages (`sota-golang` rules/05, `sota-javascript-typescript`
rules/05) — no audit-side sweep, no threshold, nothing for Python/Rust/JVM/.NET/PHP/Ruby.
And upstream health was mandated *in principle* (operating principle 0) without a
single command; the "name the maintained successor" rule existed as this repo's own
authoring convention, never as guidance for auditing someone else's tree.

**One idea the library did not have in any form.** The KEEP bucket's prohibition
on reimplementing **an algorithm whose output is persisted and must stay
comparable with stored data**. "Don't roll your own crypto" is everywhere in the
library; this is a different failure mode — a reimplementation can be perfectly
*equivalent* and still invalidate every stored value it must compare against, and
nothing errors. It belongs in the silent-failure family, and it is cited as such.

**What validating the entry taught (2 more adoptions).** Every tool named in
§3.9.2 was checked live via `gh api repos/<owner>/<repo>` — the same command the
rule prescribes. Two results changed the rule:

- **`gh api` follows renames silently.** `repos/fpgmaas/deptry` answers as
  `osprey-oss/deptry`; `repos/icanhazstring/composer-unused` as
  `composer-unused/composer-unused`. Both are the URLs a manifest or a README
  would still carry. A 200 under the old name reads as "project fine, still
  there" when the project has in fact moved owners — so the rule now says read
  `full_name` back, and distinguishes a rename from a 404.
- **Ruby has no established tool, and .NET's is thin.** The candidates are
  5-star projects with **exactly one contributor each** (`gh api
  repos/<o>/<r>/contributors` → length 1), and the Ruby one's last push was
  2025-01-03 — over 18 months before this check. Naming
  them would have violated the no-rot-prone-recommendations convention within
  months. Saying *no established tool exists — go straight to the deletion proof*
  is both honest and the stronger instruction, since dynamic `require` and
  autoload defeat static analysis in Ruby by construction anyway.

**Measurement status:** all adoptions here are content refinements taken on
reasoning, **not measured**. Do not cite a lift. Note also what this entry does
*not* claim: the tool table is a fact about tools as of 2026-07-30, not a
recommendation with a shelf life — §3.9.2 tells the reader to re-verify before
trusting any row, which is the only maintainable posture for a table of eight
third-party projects.

### 2026-07-30 — two dead-path audit prompts, and the gate that caught itself

Source: two user-authored audit prompts on the same family — "Silent-Control &
Dead-Path Audit (general)" and a "Dead-Layer" variant carrying seed examples from
a real scanner codebase. Same five classes, same validation protocol; the second
adds sharper sub-cases.

**Coverage before: roughly two thirds.** `sota-code-security` rules/10 already
owned the spine — the falsification question (§1), silent-zero in three forms
(§2.1–2.4), the vacuous-control catalog, and the mutation procedure with the two
traps that make a green result lie (§3). `sota-testing` rules/09 already required
watching a security test fail. `sota-shell-scripting` rules/01 already covered
empty globs and exit-code masking. Those were logged **rejected: already covered**
rather than re-litigated.

**What was genuinely missing was the *hunt*, not the catalog.** rules/10 tells you
how to interrogate a control you are already looking at. Neither prompt's most
valuable idea was a class at all — it was a **diagnostic** that tells you *where*
to look without reading every line:

- **Duration, not result.** The library had nothing on wall-time-versus-claimed-
  work anywhere across 41 skills. It is the cheapest signal in the family and the
  only one requiring no code reading.
- **Scope of the check.** "0 checked, 0 failed, exit 0" — the observation that a
  gate must publish its *denominator*.

Three classes were also absent because they are **correctness, not security**,
and so had no natural home in a security-controls file: scale-dependent silence,
stale-artifact no-ops (a cache key narrower than the behaviour), and format
assumptions generalised from one sample. They landed in a new `rules/11` with
cross-refs into `sota-testing` (fixtures must cross the thresholds the code
branches on) and `sota-performance` (duration as a *correctness* signal).

**The gate caught itself.** Applying §2.2's diagnostic to this repo's own
`check-invariants.sh` produced a real **LATENT** finding: mutating the pathspec
`skills/*/rules/*.md` to match nothing made checks 2 and 10 print `ok` and the
script exit **0** having examined **zero files** — and check 6's tree recount did
not catch it, because the `SKILL.md` count it recounts was unaffected. Fixed the
same day: four checks now print their denominator and fail closed on an empty
scope, and the same mutation exits 1. An early cut of the fix printed `ok` on the
line *after* the failure note — misleading green, the precise defect the new file
warns about — which is itself the argument for watching a fix run rather than
trusting it.

**Verified rather than asserted.** Every `assert`-stripping claim was run:
`python3 -O` and `PYTHONOPTIMIZE=1` deleted a failing assertion (program printed
`passed`), `cc -DNDEBUG` did the same in C, and — with no JDK available locally —
Java's default-off behaviour was taken from Oracle's own guide rather than
memory. CMake's `Modules/Compiler/GNU.cmake` was read directly to confirm
`-DNDEBUG` reaches `RELEASE`, `RELWITHDEBINFO` *and* `MINSIZEREL`. The lenient-
parser examples (`parseInt("12abc") → 12`, `float("1_0") → 10.0`) are real output.

**Not adopted:** the second prompt's seed examples name a specific repo's files as
calibration anchors. The classes were adopted; the examples were not — the library
stays generic.

**Measurement status:** content refinements adopted on reasoning plus one measured
self-finding (the empty-scope defect, proven by mutation with before/after exit
codes). **No efficacy lift is claimed or measured. Do not cite one.**

### 2026-08-01 — three proposals from a handover session, two adopted

The two adoptions share a shape: **a control that is counted in a threat model
while being structurally incapable of covering the case it is counted for.**

**1. Same-class checkers (`rules/08` §1).** A classifier or judge drawn from the
same model family as the system it guards shares that system's blind spots by
construction, so the two do not multiply into defence in depth. The sharper half
is the escalate-only variant, which is wrong *deductively* rather than
empirically: a tier that only sees inputs the primary scored **uncertain** cannot
see an input the primary scored **confidently wrong** — the exact failure it was
added to catch. Its marginal recall on the hard class is bounded by the primary's
uncertainty coverage, not by its own accuracy, so a better second model does not
repair it. The rule's demand is therefore a measurement, not an architecture:
measure marginal recall **on the hard class specifically** before calling it a
layer. It closes onto `rules/10` §1 — a layer that adds nothing on the class you
care about is a control that looks enabled and does nothing.

**2. TEEs and completeness (`rules/04` §8).** §8 already separated integrity from
completeness for audit ledgers. The addition names the wrong turn people actually
take: reaching for confidential computing to fix "records that were never
emitted". Hardware can protect a record once it exists; nothing in the CC
guarantee compels a component to emit one. That is **liveness**, and
`sota-confidential-computing` rules/01 §2 (availability row) and rules/04 §7
already state it from the CC side — the cross-ref makes it reachable from the
crypto side, where the mistake is made.

**3. Rejected: already covered.** The third proposal — a vendor control-plane API
reporting `confidentialCompute: true` for an instance whose CC status is OFF — is
`rules/10` at the hardware layer. §2.2 already says outright *"check the shipped
artifact, not the checkout"* (line 102) and §2.11 is *"Shipped-artifact gaps"*,
whose whole subject is a control that is present where you look and absent where
it runs. A vendor's assertion about a machine is the checkout; the machine's own
attestation is the artifact. Adding a cloud-specific instance would narrow a
general rule to one provider's field name.

**Verification.** Every quoted claim in the handover was checked verbatim against
the files before editing (one grep of mine missed on case — the text is
`**Self-preference**` — so the handover was right and I was wrong). Both edited
files stayed under the 500-line cap (316 and 306), both kept `## Audit checklist`
as the last heading, and both gained a checklist item — an addition with no
checklist entry is a rule the audit pass cannot reach.

**Measurement status:** adopted on reasoning. **No efficacy lift is claimed or
measured. Do not cite one.**

### 2026-08-04 — an inert-control audit spec (classes 6–12), and the grep that lied

A handover spec proposing **seven inert-control classes** beyond the five this
library already carries. The verdict split three ways: two classes were already
covered end-to-end, four were covered as a *rule* but not as a *probe*, and the
genuinely new material was narrower — and sharper — than the spec's framing
suggested.

**The instrument failed first, which is the entry's real lesson.** The opening
sweep ran `rg -rn --no-heading -i "<pattern>" skills/`. In ripgrep `-r` is
`--replace`, so `n` became the replacement string: every match was overwritten
in the output (`provenance` → `n`, `delimiters` → `ns`) and line numbers
vanished. The output was plausible, and four "gaps" nearly shipped from it. It
was caught only by running a **positive control** (a known-present term that had
to hit) and a **negative control** (a nonsense term that had to miss) before
trusting anything — which is `rules/11` §7.2's own bar, applied to the auditor.
This is why §7.2 gained "sample and read before you count": the same session
later produced a second `-r` typo, and the correct grep run beside it exposed it
immediately.

**What was already covered, and stayed rejected.** Dead instruments (`rules/10`
§2.2 optional-dependency degradation, §2.13 "has it ever executed"), record rot
(§2.9 doc/code default drift, `rules/11` §5 "comments are a hypothesis",
`sota/rules/01` §6's decision ledger with its *re-measure it this session* rule),
and the auditor's-own-instrument framework (`rules/11` §7 in full). Five further
candidates surfaced by the cross-skill sweep were also already ours — the
alerting-pipeline dead-man's switch, `failurePolicy: Ignore`, soft-fail gate
steps, suppression-baseline rot, coverage-target gaming. Recording those stops
the next reader re-proposing them.

**What the gaps actually were.** Three of the four are *the audit half of a build
rule we already state*. `sota-testing` said "unit tests touch no sockets" in
three places and offered no way to find out that they do — hence the egress
block. `rules/10` §2.10 governed the numbers a tool prints and not the words —
hence the verification-verb half. `rules/11` §7 declared instruments to be
controls without ever turning the recursion on **guards** — hence §7.1's new
bullet, and the sub-shape that matters most is not scope but **predicate**: a
test that greps for `"auth="` passes on `auth=None`, so the guard's own check is
satisfied by the defect it exists to catch. Only §3.4 (contract drift by
interaction) was a class the library had no seat for at all: every contract rule
we own presumes a *declared* contract with a registry to compare against, and
this class is precisely what remains when none exists.

**Two facts verified against primary sources rather than the spec.** GitHub's
own docs state that a skipped job "will report its status as 'Success'" and
"will not prevent a pull request from merging, even if it is a required check" —
strictly worse than §2.13's existing "all-skipped is not all-green", so §2.13
now says so with the citation. And `go test ./...` over a package with no test
files exits **0**, run here this session; the widely-repeated claim that pytest
and Jest behave identically was *not* reproducible on this machine and was
deliberately left out rather than asserted.

**One correction to our own catalog.** `sota-testing` rules/02 used **mystery
guest** for a readability defect (hidden fixture data). In the standard
test-smells catalog the name means a test reaching an *external resource*, with
**resource optimism** as its sibling. Ours had quietly narrowed a standard term —
record rot in our own file, found while auditing for it. Both are now stated.

**Verification (2026-08-04 entry).** Every claim above was checked against the tree
before editing, with `file:line` for each. Both edited `sota-code-security` files
stayed under
the 500-line cap — but only just (**493** and **495**), after two rounds of
trimming when the first draft pushed `rules/11` to 505 and the gate caught it.
**That pair is now effectively full: the next addition to this family needs a
`rules/12` split, not another squeeze.** Invariant 6 also fired for real — the
+141 lines rolled the README's `~61k lines` to `~62k`, which is exactly the drift
that surface exists to catch.

**Measurement status:** adopted on reasoning. **No efficacy lift is claimed or
measured. Do not cite one.**

### 2026-08-05 — two research reports on the same eight instances, and why only one survived quoting

Two commissioned reports on inert controls, written against the same eight
evidence instances: **A** ("Missing SOTA Audit Controls") and **B** ("The
Inert-Control Class"). They converge on the same headline — *the missing layer is
a control that must be shown capable of failing* — and they are **not** of equal
quality. Every claim either report made that would become library text was
checked against a primary source first, and that check is the reason this entry
records four adoptions instead of thirteen.

**Where the reports disagreed, B was right.** Report A misquotes SSDF **PO.3.3**
as *"Configure tools to generate **evidence and** artifacts…"*; the actual clause,
extracted from the NIST SP 800-218 v1.1 PDF, reads *"Configure tools to generate
**artifacts**⁶ of their support of secure software development practices as
defined by the organization"*, with footnote 6 supplying the words A folded into
the clause: *"An artifact is 'a piece of evidence'."* B quotes it exactly, and
quotes **PW.8.2** and all three OpenSSF Scorecard checks verbatim — all confirmed
against `ossf/scorecard` `docs/checks.md`. A also over-generalises the vacuity
statistic: the "20%" is Ball & Kupferman quoting Beer et al., scoped to *"a new
**hardware** design"* and stating that vacuous passes *"always"* point to a real
problem; A reports it as spanning "hardware and software" and softens it to
"almost always". A's cross-discipline sourcing is weakest of all — aviation BITE
cited to two Scribd uploads and a flight-simulator datasheet, "silent control
failure" to a vendor homepage, alert fatigue to an unrelated GitHub repository.
The *reasoning* in A is sound; its **references are not load-bearing**, and the
misquote is recorded here so nobody re-derives PO.3.3 from that PDF.

**Report A nonetheless found the one thing B asserts does not exist.** B states
plainly that there is "no published corpus quantifying how often a scanner is
misconfigured to scan nothing, or a gate is silently inert", and no large-scale
study of monitors failing silently. A cites **EvoMap** (arXiv:2605.25815, HKUST,
May 2026), whose abstract — fetched and read — reports that across **1.5M assets
and 128K agents**, *"over 84% of approved assets bypass quality checks using
vacuous tests (e.g. `console.log()`)"*, because the platform accepted each agent's
own execution log as proof of correctness. That is the closest measured analogue
we have to this whole family, and it is now `rules/12` §2.4. A search-engine
summary of the same paper rendered it as "84% of **agents**"; the abstract says
**approved assets**. The number was taken from the abstract, not the summary.

**Three of the four adopted gaps are the same shape as last entry's.** Per-target
kill verification, the metamorphic liveness oracle, and the standards gap are all
cases where the library held the principle and lacked the *specific move*:
`rules/12` §3 said "introduce the defect and check" in the singular against a
guard that protects a population of twenty; `sota-testing` rules/06 §4 had
metamorphic relations as a property-based pattern with nothing connecting them to
a tool that emits zero; and `sota-devsecops` had the negative-control rule without
ever saying that **no framework asks for one**. The fourth adoption is pure
naming: the library had been describing proof tests, positive controls, BITE,
poka-yoke, vacuous satisfaction and the oracle problem for months without using
any of those words — `poka-yoke` and `oracle problem` returned **zero** hits
across all 41 skills before this change.

**Two rejections worth keeping.** Report A's Rule 3 — enforce a minimum mutation
score in CI — is **contrary** to a position adopted here on 2026-07-24: `rules/07`
§7.2 refuses global percentage targets on Goodhart grounds, and `rules/06` §6.3
gates on *new survivors* against a persisted manifest. B's equivalent (per-gate
kill rate, where 100% is the right bar because a gate that misses its own target
defect is void) is compatible and was adopted; A's global score is not, and the
distinction is the whole point. B's R8 (GSN assurance cases) is **non-fit** for
the reason B itself supplies: Leveson's critique that such arguments "assume the
conclusion" describes exactly the failure our `sota/rules/01` §7 refutation pass
exists to prevent, and a notation is not a mechanism.

**One thing both reports missed, which the library already has.** Neither applies
its own R1 recursively: a committed negative-control fixture is itself a control,
and it can be path-filtered, skipped, or — per `rules/10` §2.13 and GitHub's own
docs — *reported as Success because its job was skipped*. `rules/12` §3 is that
question. Neither report addresses the gate that fails correctly while nobody
reads the output, which is `rules/11` §7.1 and this repo's own v1.20.0 incident.

**Verification.** SSDF PO.3.3 / PW.7.2 / PW.8.2 and footnote 6 extracted from the
primary PDF; Scorecard's three checks fetched from `ossf/scorecard`
`docs/checks.md`; the EvoMap abstract and the Barr et al. citation (IEEE TSE
41(5):507–525, 2015, doi:10.1109/TSE.2014.2372785) confirmed; the Ball &
Kupferman text pulled and read at the quoted paragraph. **Not verified and
therefore not quoted as clause text:** IEC 61508 §3.8.5/§3.8.6 (paywalled — the
*concept* is named, no clause number is asserted), and the CRA Annex VII **point
number** (the sentence was confirmed against published copies of the regulation,
not EUR-Lex, which returned only recitals; the file says so at the point of use).

**Measurement status:** adopted on reasoning. **No efficacy lift is claimed or
measured. Do not cite one.**
