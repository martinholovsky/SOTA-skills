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

- **States:** `adopted` · `rejected` · `deferred` · `superseded` · **`adopted with a
  correction`**. Every entry ends in one of these — nothing stays `open` here; if it
  needs more thought it is `deferred` with the condition to revisit. The fifth was added
  2026-08-16 for a real case: a proposal whose *substance* was right but whose *wording*
  would have licensed the opposite behaviour. Recording it as plain `adopted` would have
  hidden the edit from the person who wrote the proposal, and `rejected` would have been
  false. Use it when you ship an idea in materially different words, and say what you
  changed and why — the reasoning is the part that stops the original phrasing coming
  back.
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

> **Pointer translation, 2026-08-20.** `sota-code-security` `rules/10` and `rules/11`
> were split. Landed-in pointers in older rows are **left as written** — they record
> where an idea landed *at that release*, and rewriting them would falsify the history
> this log exists to keep. Translate with this map:
>
> | old | new |
> |---|---|
> | `rules/10` §2.10 | `rules/14` §1 (unearned claims in reporting output) |
> | `rules/10` §2.11 | `rules/14` §2 (shipped-artifact gaps) |
> | `rules/10` §2.12 | `rules/14` §3 (instruction standing in for a control) |
> | `rules/10` §2.13 | `rules/14` §4 (a control that never executes) |
> | `rules/10` §2.14 | `rules/14` §5 (parked in observe-only mode) |
> | `rules/11` §3.1–3.5 | `rules/13` §1–§5 (context-dependent silence) |
>
> Invariant 18 keeps *live* `§` references honest, but its scope is `skills/` only —
> which is why this note exists rather than a gate.


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
| 2026-08-04 | An inert-control audit prompt (classes 6–12), handed over as a spec | **Unearned claims in output are words as well as numbers** — `verified`/`reachable from`/`tainted`, severity or confidence from a constant; match the claim's *shape*, and read the sentence before counting it | **adopted** | `rules/10` §2.10 · v1.21.1 |
| 2026-08-04 | Same prompt (class 8) | **The guard is an instance of what it guards** — a coverage test whose *scope* is narrower than the population and whose *predicate* the defect satisfies (`"auth=" in line` accepts `auth=None`); a tripwire nested in another gate's success branch; a denominator counting only survivors | **adopted** | `rules/11` §7.1 · v1.21.1 |
| 2026-08-04 | Same prompt (class 11) | **Contract drift by interaction** — a producer/consumer seam *no schema declares*, where the trigger is a config-level backend/frontend swap and both sides' isolation tests pass | **adopted** | `rules/11` §3.4 · v1.21.1 |
| 2026-08-04 | Same prompt (class 12) | Sample and read before you count; a control validated on inputs that **cannot** produce the failure proves nothing; when a wrapper reports an empty reason, go one layer down | **adopted** | `rules/11` §7.2 · v1.21.1 |
| 2026-08-04 | Same prompt (class 9) | The *detection* half of test-environment leakage: **block egress and re-run**; the config object the SUT never reads; assertions that contradict the test's own name | **adopted** | `sota-testing/rules/02` §2.6 + checklist · v1.21.1 |
| 2026-08-04 | Same prompt (class 7) | Run every script CI, a hook or a runbook references **before** reading any of them; record which produce output | **adopted** | `rules/11` §6 · v1.21.1 |
| 2026-08-04 | Standard test-smells catalog ([testsmells.org](https://testsmells.org/pages/testsmells.html), after van Deursen et al.) | **Resource optimism** as its own smell, and *mystery guest* in its original external-resource sense — ours had narrowed the standard name to a readability defect | **adopted** | `sota-testing/rules/02` §2.7 · v1.21.1 |
| 2026-08-04 | [GitHub Docs — Status checks](https://docs.github.com/en/pull-requests/reference/status-checks) | A **skipped job reports *Success*** and does not block a PR "even if it is a required check" — worse than §2.13's "all-skipped is not all-green" | **adopted** | `rules/10` §2.13 · v1.21.1 |
| 2026-08-04 | Verified locally this session | `go test ./...` over a package with no test files exits **0** — the empty-denominator rule instantiated in the toolchain | **adopted** | `rules/11` §2.2 · v1.21.1 |
| 2026-08-04 | Cross-skill sweep prompted by the same prompt | **A control parked in observe-only mode** (Kyverno `Audit`, PSA `warn`, WAF detection-only, `SCMP_ACT_LOG`, CSP report-only, DMARC `p=none`, `--soft-fail`) is inert as a *destination*; the staged rollouts existed, the inert-control framing did not | **adopted** | `rules/10` §2.14 · v1.21.1 |
| 2026-08-04 | Same prompt (classes 7, 10, 12 — the covered remainder) | Dead instruments; record rot; the auditor's instrument as a control; negative-claim burden | **rejected: already covered** | — (`rules/10` §2.2/§2.13, `rules/11` §7.1–7.3; `rules/10` §2.9, `rules/11` §5 "comments are a hypothesis", `sota/rules/01` §6 decision ledger) |
| 2026-08-04 | Same prompt — candidates checked and found already ours | Alerting-pipeline dead-man's switch; admission `failurePolicy: Ignore`; `continue-on-error`/soft-fail gate steps; suppression-baseline rot; coverage-target gaming | **rejected: already ours** | — (`sota-observability` rules/04 + rules/02, `sota-kubernetes` rules/05, `sota-devsecops` rules/05, `sota-testing` rules/07 §7.2) |
| 2026-08-05 | Two commissioned research reports on inert controls ("Missing SOTA Audit Controls" = **A**; "The Inert-Control Class" = **B**) | **Per-target kill verification** — a guard protects a population; watching it reject one member says nothing about the other 19 (the 2-of-20 tripwire). 100% kill rate for a security gate | **adopted** | `sota-code-security/rules/12` §3 · v1.21.1 |
| 2026-08-05 | Report B (Q3, instance 1) | **Metamorphic relation as a liveness oracle for a tool** — when you cannot state the correct output, state how it must *change*; the only diagnostic that catches an analyser emitting an empty-but-well-formed artifact | **adopted** | `sota-code-security/rules/11` §2.6 · v1.21.1 |
| 2026-08-05 | Report B (Q5), verified against primary sources | **The standards gap**: SSDF PW.8.2/PO.3.3 and CRA Annex VII require a record that the scan *ran*; Scorecard's SAST check detects tool *presence* only; **none require evidence a gate can fail** | **adopted** | `sota-devsecops/rules/05` §5.6 · v1.21.1 |
| 2026-08-05 | Both reports (Q1/Q2) | The cross-discipline lineage the library used unnamed: **proof test** (IEC 61508 dangerous-undetected), **positive control** (assay validity), **BITE** (aviation), **poka-yoke**, **vacuous satisfaction** (Ball & Kupferman), **the test oracle problem** (Barr et al., IEEE TSE 41(5), 2015) | **adopted** | `rules/12` intro + §3, `rules/11` §2.6 · v1.21.1 |
| 2026-08-05 | Report A only — the one thing B missed | **EvoMap** (arXiv:2605.25815, 1.5M assets / 128K agents): "over 84% of approved assets bypass quality checks using vacuous tests (e.g. `console.log()`)" — hard data that self-supplied evidence collapses at scale. B asserts no such corpus exists | **adopted** | `sota-code-security/rules/12` §2.4 · v1.21.1 |
| 2026-08-05 | Report A, Rule 3 | "Enforce a minimum **Mutation Score** threshold in CI" | **rejected: contrary** | — contradicts `sota-testing` rules/07 §7.2 ("never set a global percentage target — Goodhart's law is undefeated") and rules/06 §6.3 differential mutation (gate on *new survivors*, adopted 2026-07-24 from swarm-forge). B's per-gate kill rate is compatible and was adopted; A's global score is not |
| 2026-08-05 | Report B, R8 | **GSN / assurance-case notation** for critical controls | **rejected: non-fit** | — a notation, not a mechanism; its own cited critique (Leveson: arguments "assume the conclusion") points back at what we already run, `sota/rules/01` §7 adversarial refutation |
| 2026-08-05 | Report A, Rule 4 | Cryptographically **signed volumetric execution artifacts** verified by release gateways | **rejected: partial — insight kept, machinery dropped** | the insight (SLSA proves execution, never efficacy) landed in `sota-devsecops/rules/05` §5.6; the signing machinery is speculative and unbuilt |
| 2026-08-05 | Both reports — checked and found already ours | R2 execution evidence/volumetric assertions; R3 fail-closed gates; R6 assertion polarity + egress sandbox; R7 meta-monitoring/heartbeat; the **ML Test Score** rubric ("worth adopting wholesale") | **rejected: already ours** | — (`rules/11` §2.2/§2.4/§3.1, `rules/10` §2.1/§2.4/§2.6, `sota-testing/rules/02` §2.6–2.7, `sota-observability/rules/04:249`, and `sota-ml-engineering/rules/04:6` which has cited ML Test Score since before these reports) |
| 2026-08-11 | [spanchain](https://github.com/ghostfactory-art/spanchain) `docs/arch/hash-chain.md` | **A partitioned chain must chain its partitions** — segmenting a ledger (epochs, rotated files, daily partitions) with a per-segment `prev_hash = NULL` reset makes deletion of a whole *interior* segment verify clean; their pre-fix verifier also reset its carried hash at the boundary | **adopted** | `sota-code-security/rules/04` §8 + checklist · v1.22.4 |
| 2026-08-11 | Same source — where the bug actually lived | A verifier that walks a sequence in chunks and **resets its carried state at the seam**: predicate right, traversal right, blind to the removal of a whole chunk — a fourth form of "the guard that is an instance of what it guards", and a seam axis for per-target verification | **adopted** | `sota-code-security/rules/12` §3 + checklist · v1.22.4 |
| 2026-08-11 | Same source — `canonical_encode` and its stated cause | Canonicalization fails in **two** directions: the library stated only forgery. A default map/JSON encoder is not canonical, so identical data hashes differently and the ledger reports tamper on untouched records — an alarm wrong on ordinary traffic gets muted. Name the spec (RFC 8785) and pin it with a known-answer vector, or the "verify off the storing system" requirement is two implementations free to disagree | **adopted** | `sota-code-security/rules/04` §8 + checklist · v1.22.4 |
| 2026-08-11 | spanchain README, "Replay validates Span Chain's integrity, not your agent's behavior" | A record-and-replay (cassette) harness re-executes nothing: it tests pipeline determinism, and as a CI quality gate it stays green through a prompt rewrite, a model swap or a retrieval change | **adopted** | `sota-llm-engineering/rules/01` §5 + checklist · v1.22.4 |
| 2026-08-11 | spanchain — six findings checked against our tree first | Unkeyed chain forgeable by a DB-write attacker; tail truncation invisible; unhashed projection columns; canonical preimage required; in-memory ingest buffer loses records with no gap (integrity ≠ completeness); offline verification | **rejected: already ours** | — `sota-code-security/rules/04` §8, six for six, arrived at independently: `:217` unkeyed, `:224` tail truncation, `:241` unhashed projection columns, `:244` canonical preimage, `:265` integrity ≠ completeness, `:279` off-system verification |
| 2026-08-11 | spanchain — pre-GF-703 telemetry inside `Repo.transaction`; GF-827 conditional terminal write; append-only store holding personal data; EU AI Act Art. 12 | Post-commit notification, compare-and-set instead of check-then-write, erasure from immutable stores, AI Act record-keeping | **rejected: already covered** | — `sota-ruby/rules/05:82`, `sota-databases/rules/05:175`, `sota-architecture/rules/02:127`; `sota-async-concurrency/rules/02` §"Check-then-act / TOCTOU"; `sota-privacy-compliance/rules/03:125`; `sota-code-security/rules/04:214` |
| 2026-08-11 | spanchain — dead-letter drops deliberately break `verify_ledger` ("a deliberate audit signal") | An integrity verdict that is routinely red for operational reasons trains operators to ignore it; a known gap should be a signed in-chain marker, not a hole | **deferred** | revisit if a second implementation shows the same design — one project's trade-off is not yet a rule |
| 2026-08-13 | Internal coverage audit — business-logic defect class ([COVERAGE-BUSINESS-LOGIC-2026-08-13](COVERAGE-BUSINESS-LOGIC-2026-08-13.md)) | Route the class by its own name: "business logic", "checkout", "refund", "state machine" appeared in **zero** of 41 SKILL.md descriptions, and "workflow" only in the CI/SOC/docs senses — descriptions are the only auto-loaded classifier | **adopted** | `sota-code-security` description, 998→1014 of 1024 · v1.22.4 |
| 2026-08-13 | Same audit — first draft | Add a BUILD rule + probe for WSTG-BUSL-07 "defenses against application misuse" | **rejected: already covered** | — covered under three other names: `sota-api-design/rules/07:211` (API6 flow throttles, explicitly not generic rate limiting), `sota-code-security/rules/07-data-exposure.md:96-99`+`:230` (security events + alerting on anomalies), `rules/02-authentication.md:213` (escalating friction), `sota-mobile/rules/04:94-99` (non-human client decision table). Residual is naming, not coverage |
| 2026-08-13 | Same audit — first draft | Add payment-specific money hazards for WSTG-BUSL-10 (currency, rounding, negative amounts, insufficient funds) | **rejected: already covered** | — `js-ts/rules/02:183,191,244`, `sota-databases/rules/01:232`, `sota-api-design/rules/01:285,302-303`, `sota-code-security/rules/06:183-197,218,226`, `rules/03:82,91`, and currency specifically at `rules/01-input-injection.md:28` ("currency matches account") |
| 2026-08-16 | Field-use handoff from a live build (private repo, brief kept outside this repo) | The auditor's **own verification one-liners** are uninstrumented instruments: unlinted shell run against the system under test, producing false findings *about the product*. Three in one session, all zsh joining/pipeline bugs the library already documents but nothing routed to | **adopted** | `sota/SKILL.md` rule 17 + `sota-code-security/rules/12` §2 · v1.22.6 |
| 2026-08-16 | Same brief | `set -e` **cannot be re-armed** inside a suspended call tree, and `$-` still reports `e` — an unfalsifiable control inside bash itself | **adopted** | `sota-shell-scripting/rules/01` §2 + audit checklist · v1.22.6 |
| 2026-08-16 | Same brief | "never open an issue" for `SECURITY.md` has **no private-repo exception**: GitHub's private vulnerability reporting is public-repo only, so the rule pointed at a feature that cannot be enabled | **adopted** | `sota-docs-workflow/rules/01` §8 table + carve-out + checklist · v1.22.6 |
| 2026-08-16 | Same brief | **Location-dependent silence** — a filter whose predicate matches the ambient environment (absolute path, hostname, locale), so a collection is correct on one machine and empty on another | **adopted** | `sota-code-security/rules/11` §3.5 (+4 ripple sites) · v1.22.6 |
| 2026-08-16 | Same brief | A pipeline the platform **refused** (billing) reports *failure*, not skipped, so the all-skipped test misses it; and nothing said how to prove a pipeline runs | **adopted** | `rules/10` §2.13 third state + `sota-devsecops/rules/01` §1.11 · v1.22.6 |
| 2026-08-16 | Same brief, optional finding 6 | Elaborate `rules/04` §8 with RFC 8785 float formatting (Python `repr` vs ECMAScript `Number::toString`) | **rejected: already covered** | — `rules/04:244` already states a default JSON encoder is not canonical and names float formatting specifically. Verified the divergence is real but **narrower than proposed**: Python `1e-05`/`1e+16` vs JS `0.00001`/`10000000000000000`, yet both agree at `1e21`. §8 is dense and `rules/04` sits at 340 lines; the warning already carries the actionable half (name a spec, pin a known-answer vector) |
| 2026-08-16 | Field-use handoff, live infrastructure session (brief kept outside this repo) | **`rules/12` §2.2 inverts for instruments that run over time.** "Abort on a missing result" is right for a one-shot scorer; in a watcher it kills the watch on the first transient read failure — and since silence is a watcher's normal state, a dead watcher and a waiting one are indistinguishable. Needs a **third state** (done / not-done / cannot-tell), a positively asserted terminal condition, a bound on consecutive unknowns, and an independent signal printed beside the verdict | **adopted** | `sota-code-security/rules/12` §2.2a + audit checklist · v1.22.7 |
| 2026-08-16 | Same brief | Validate **captured command output**, not just arguments: `!= "0"` is satisfied by `""`, `error`, `null` and any usage message, so a failed read reads as success | **adopted** | `sota-shell-scripting/rules/02` §2 · v1.22.7 |
| 2026-08-16 | Same brief — its own routing question | Put the finding in `sota-observability` rules/05 §8 (synthetic monitoring) instead of `rules/12` | **rejected: wrong owner** | — §8 is about probing a **running production service** end-to-end ("from outside your network, from the regions users are in", tagging synthetic traffic). This finding is the correctness of a verification instrument you wrote to check your own work, which is `rules/12` §2's stated subject. No pointer added either: it would imply a relationship that is not there |
| 2026-08-16 | Same brief — drafted wording changed on adoption | The draft said §2.2's rule "**inverts**" for pollers | **adopted with a correction** | — §2.2's *principle* (an unreadable result must never read as a terminal answer) is exactly what the tri-state preserves; only its *remedy* (abort) inverts. Shipped as "the principle holds, the remedy does not", because "the rule inverts" would license dropping §2.2 inside a watcher |
| 2026-08-16 | Own roadmap item (open since the 2026-07-13 competitor benchmark) | Run an **as-deployed** competitor comparison — each library loaded the way its users install it, rather than a hand-picked content bundle | **rejected: measures corpus size and a saturated retrieval path, not guidance quality** | — verified against the pinned clones: **ECC ships 889 `SKILL.md` + `.claude-plugin/marketplace.json`, claude-skills 777 + `.claude-plugin/`/`.codex-plugin/`**, so two of three deploy through *our own* mechanism at 20× our corpus (41). The measurement would land on library size, and on a description-selection layer `run-desc-routing.py` already scores **+0.00 / saturated** ([RESULTS](../evals/results/RESULTS.md) §5). No neutral executor exists either — simulating a loader none of them ships lets our choices decide the result; real per-plugin sessions are non-deterministic and hard to blind. A retrieval **miss** would also score as a content zero, which reads as rigged when published about a named third party |
| 2026-08-17 | [system-design-notes](https://github.com/liquidslr/system-design-notes) ch26 "Double-entry ledger system" | Money movement is modelled as **append-only entries that sum to zero**, at least two per movement — so a one-sided write is a rejected invariant, not drift | **adopted** | `sota-databases/rules/01` §"Ledgers" + checklist · v1.22.9 |
| 2026-08-17 | Same source, ch26 §Reconciliation + ch21 §Data monitoring and correctness | Where an external party holds authoritative state, a **periodic recompare against their own extract** is a required control, with a three-bucket break taxonomy (auto-adjustable / manual / unclassified) | **adopted** | `sota-architecture/rules/03` §5b + checklist · v1.22.9 |
| 2026-08-17 | Same source, ch27 (the invalid-choice table) | **Order multi-leg moves so partial completion is conservative** — debit before credit; a crash must leave value missing (recoverable), never duplicated (not) | **adopted** | `sota-architecture/rules/03` §5 + checklist · v1.22.9 |
| 2026-08-17 | Same source, ch27 §Event sourcing | The replay preconditions: the state machine must be **deterministic** (no wall clock, RNG, or external IO), and since commands are non-deterministic only the *event* log needs durability | **adopted 2026-08-21** | `sota-architecture/rules/03` §6 + three checklist items. Deferred 2026-08-17 as *one source's judgement call*; closed on operator instruction to work the open roadmap, and the substance verified against a primary source first — Fowler's *Event Sourcing* states the external-query problem directly (*"if I ask for an exchange rate on December 5th and replay that event on December 20th, I will need the exchange rate on Dec 5"*) and prescribes gateways disabled during replay. **Correction to the brief**: Fowler does not use the word *deterministic* nor discuss clock/RNG, so the rule is written from the mechanism (the `apply` step must be a pure function of state and event) with the citation attached only to the part it supports · v1.24.1
| 2026-08-17 | Same source, ch16/ch18 (geohash, quadtree, S2, the naive 2-D range query) | Geospatial modelling and indexing — SRID/geography-vs-geometry, `ST_DWithin` vs a hand-rolled bounding box, haversine in the `WHERE` clause defeating the index | **adopted 2026-08-21** | `sota-databases/rules/03`, new *Geospatial* section + two checklist items. **Adopted on operator instruction, not because the recorded condition fired** — that condition (a second source, or a real audit hitting it) is still unmet, and this is noted so the deferral record is not read as having been vindicated. Every claim verified against the PostGIS docs before writing: `ST_DWithin` "includes a bounding box comparison that makes use of any indexes" while `ST_Distance` is explicitly **non-indexable**; `geography` is always metres and assumes EPSG:4326 while `geometry` uses the SRID's units (degrees for 4326); PostGIS's own compact-vs-dispersed guidance; and the real costs of `geography` (trigonometry, and fewer functions supporting it natively) · v1.24.1
| 2026-08-17 | Same source, ch24 §Correctness verification (per-object checksums, scrubbing, erasure coding) | Detect silent at-rest corruption by storing checksums and re-verifying in the background | **rejected: vendor concern** | — the library's stance is use a vetted implementation; ZFS/Ceph/S3-class storage scrubs for you, and `sota-databases/rules/05:5` already requires rehearsed restores, which is the application-level check that matters. `sota-cloud-infrastructure/rules/05:88` covers the adjacent real risk (replication faithfully copies corruption) |
| 2026-08-17 | Same source, ch06 (Merkle-tree anti-entropy, vector clocks, sloppy quorum, W+R>N) | Replica divergence detection and conflict resolution | **rejected: datastore-internal** | — these are things Cassandra/Dynamo-class stores do *for* the application; no defect an application engineer can commit |
| 2026-08-17 | Same source, ch01/04/05/07–15/17–21/23/25 | Rate-limiter algorithms, consistent hashing, Snowflake IDs, watermarks & event-time, lambda/kappa + keep-the-raw-data, delivery semantics & the exactly-once myth, DLQ/retry/backoff, optimistic vs pessimistic locking, idempotency keys via unique constraint, never trust a client-supplied score or price, TSDB cardinality/downsampling, push-vs-pull metrics | **rejected: already ours** | — `sota-data-engineering/rules/03:148-155` (watermarks/event time/late data) and `rules/01:39-43` (raw lands immutably, replayability); `sota-architecture/rules/03` §3 (exactly-once myth), §7 (DLQ/backoff), §2 (idempotency keys); `sota-databases/rules/04:9-41` (lost update, FOR UPDATE, optimistic) and `:100-113` (idempotency via `ON CONFLICT`); `sota-code-security/rules/07:130` (prices/totals/balances recomputed server-side); `sota-observability` rules/02 + rules/04 |
| 2026-08-17 | Same source, ch06 "CAP — only two of the three can be achieved", "CA systems"; ch01 master/slave | The pick-two framing of CAP | **rejected: contrary** | — contradicts `sota-architecture/rules/03` §1, which is PACELC and **per-operation** ("balance reads are linearizable, product-view reads are eventually consistent with ≤5 s staleness"), not per-system. The terminology is also dated |
| 2026-08-18 | External session transcript — a session *applying* the library to Go subprocess sandboxing (the field-brief class) | **The allow arm.** An *enforcement* control (cap, quota, filter, allowlist, policy) set so tight it refuses the legitimate case passes every refusal test; "a negative control on the ENVIRONMENT is not a negative control on the CONTROL" | **adopted with a correction** | `sota-code-security/rules/12` §1a + checklist. The transcript put the near-miss at `rules/12` §2.2 (true — it is scoped to things that *classify*); the sharper finding is that `sota-testing/rules/09` §1 states the **opposite** in as many words ("the assertion is that the attack is *refused*, not that the happy path works"), and `sota-sandboxing/rules/01` R5.1's probe list is **entirely** denial arms. Counterweights added at both · v1.22.10 |
| 2026-08-18 | Same transcript | **`RLIMIT_AS` is unusable as a memory budget for VM-reserving runtimes** — use `RLIMIT_DATA` or the cgroup | **adopted with a correction** | `sota-sandboxing/rules/02` R7.2a + checklist, cross-referenced from `rules/04` §1.2. Correction: the transcript says `rules/04` "orders rlimits → cgroup budget, which walks straight into it" — it does not; that list is `RLIMIT_FSIZE`/`RLIMIT_CORE` and never named a memory rlimit. This is a **missing warning, not a wrong instruction**. Numbers re-measured here rather than taken from the report (Go 1.26 `VmSize` 1,227,204 kB at 2,376 kB RSS; Temurin 25 3,937,756 kB; both die under `ulimit -v 512M`; `ulimit -d` works in both directions) · v1.22.10 |
| 2026-08-18 | Same transcript | **No fresh cgroup for a child inside an existing container** — `memory.max` is recommended everywhere and is not available per-child | **adopted** | `sota-sandboxing/rules/02` R7.2b + checklist — a four-rung fallback ladder, plus the tell that makes it findable: the cgroupfs is `ro` while `cgroup.controllers` still lists `memory`, so **probe with `mkdir`, never by reading `cgroup.controllers`** (verified: podman `cgroupns=private`, `mkdir` → `Read-only file system`, remount → `Permission denied`) · v1.22.10 |
| 2026-08-18 | Same transcript | **A refactor that moves code out of a gate's scope makes the gate pass without changing risk** (`govulncheck ./...` stops at module boundaries) | **adopted with a correction** | `sota-devsecops/rules/05` §5.6 + checklist. Sharper than proposed: the committed negative control of that very section **does not catch this** — the known-bad stays in scope, the gate keeps proving it can fail, and the risky code leaves. Framed as the *temporal* form of `sota-code-security/rules/11` §2.2 ("the same gate's green today does not cover the scope it had yesterday") with a mechanical check: fail when a gate's enumerated denominator **drops**. Mechanism verified by execution — `go list ./...` in a module containing a nested `go.mod` omits it · v1.22.10 |
| 2026-08-18 | Same transcript | **Advisory applicability as a fourth triage axis** — "only 32-bit platforms are affected" is neither reachability, exposure, nor KEV/EPSS | **adopted** | `sota-devsecops/rules/03` §3.6 + checklist. Landed with the OpenVEX justification named from the closed list (`vulnerable_code_not_present` / `vulnerable_code_not_in_execute_path`, verified against the OpenVEX spec) rather than as free prose · v1.22.10 |
| 2026-08-18 | Same transcript | **Cross-reference at point of need** — `sota-sandboxing/rules/04` §5 covers subprocess hygiene and pointed at no language skill, so the Go `cmd.WaitDelay` trap the session hit sat unreachable in `sota-golang/rules/05:98` | **adopted with a correction** | `sota-sandboxing/rules/04` R5.3a + checklist. Correction: the class is **not** uniform across languages, as the transcript implies — verified this session that Python 3.14's `subprocess.run(timeout=)` fires on schedule with a pipe-holding grandchild, while Go's `Wait` does not. So the rule is "read *this* language's subprocess section", not "beware timeouts" · v1.22.10 |
| 2026-08-18 | Same transcript — its two self-reported misses | `cmd.WaitDelay`; zsh not word-splitting unquoted expansions in a verification one-liner | **rejected: already ours** | — `sota-golang/rules/05:98-101` states the first verbatim. The second is covered **twice**: routing rule 17 *and* `sota-code-security/rules/12` §2 ("the smallest instrument is the command you just typed"). Two independent statements, neither fired — that is the salience effect of [WHY-COMPLETENESS-RESIDUAL](WHY-COMPLETENESS-RESIDUAL.md), where adding the missing rule measurably made adherence *worse*. Deliberately **not** restated a third time; the fix taken instead was the placement fix (R5.3a) |
| 2026-08-18 | Found while validating the above cross-references | `sota-rust` has **zero** coverage of `std::process::Command` — subprocess/exec hygiene for Rust exists only in `sota-sandboxing/rules/04` R5.1's one-line table | **adopted** | `sota-rust/rules/05` §9 *Running external programs — `std::process::Command`*, seven rules with audit probes, shipped **v1.22.11** (2026-08-19). **This row said `deferred` until 2026-08-21** — the work landed two days after the deferral and nobody came back to the log, which is the failure mode a landed-in pointer exists to prevent. Verified before correcting: the section exists at `rules/05:221` and its checklist carries six subprocess probes · v1.22.11
| 2026-08-19 | The 2026-08-18 deferral above, worked | **`sota-rust` subprocess execution** — seven rules (`Command` argv semantics, argument injection, the Windows `.bat` CVE, a dropped `Child`, deadlines, unbounded output buffering, env/program resolution) with four audit probes | **adopted** | `sota-rust/rules/05` §9 + checklist, cross-referenced from `rules/04` cancellation and `sota-sandboxing/rules/04`. Nothing was carried over from the Go or Python rules: every behaviour was measured on rustc 1.97.1 / tokio 1.53, and the deferral's own warning paid off — **`tokio::time::timeout` fires on schedule (unlike Go) but does not kill the child (unlike what "the timeout worked" implies)**, a third behaviour neither neighbour would have predicted. Two ripple corrections: `sota-sandboxing/rules/04` R5.1's "beware `.arg` vs `.args` splitting" was **wrong** (measured: neither splits) and R5.3a's pointer list gained Rust · v1.22.11 |
| 2026-08-19 | Field brief from a session applying the library (`sota-skills-lessons-2026-08-18-writeback-and-delivery.md`), finding 1 | **A write-back controller's success log is a claim about intent, not about a commit.** Measured: an image-update controller logged `Committing 1 parameter update(s)` / `updated=1 errors=0` every reconcile for ~15 min across ~7 cycles while pushing nothing; cause established by removing the trigger and watching a commit appear in 84 s | **adopted** | `sota-kubernetes/rules/04` §7 + checklist, cross-referenced from `sota-code-security/rules/10` checklist and the README inert-control bullet · v1.22.11 |
| 2026-08-19 | Same brief, finding 2 | **A `now` vs `offset X` pair is two samples, not a trend** — and more persuasive than one, which is what makes it dangerous. Measured: a p99 read 0.40 s now vs 8.83 s at 24 h (a "22x win") on a series that swings 0.11–13.40 s across the day, while the load-invariant absolute count was flat | **adopted with a correction** | `sota-observability/rules/02` §4a + checklist, pointer from `sota-performance/rules/01`. Correction: the brief frames it as an absence, and it is worse than that — **five existing rules *demand* before/after numbers** (`sota-rust/rules/06:197`, `sota-php/rules/06:126`, `devsecops/rules/03` ×3) with nothing saying what makes such a pair trustworthy. Scoped deliberately to **production telemetry**: the devsecops before/after counts are deterministic build outputs, where the trap does not apply · v1.22.11 |
| 2026-08-19 | Same brief, finding 3 ("`sota-sandboxing/rules/04` contains **no** reference to the language skills") | Cross-reference domain → language at the spawn call | **rejected: already ours** | — and the claim is false at the brief's *own* anchor commit: `90500b5:skills/sota-sandboxing/rules/04:189-190` already read "read that language's subprocess section… `sota-golang` rules/05 §3, `sota-python` rules/05 §2". It landed in `182ad9b`, which the brief itself credits in its "already landed" table, and #240 extended it with Rust. The stale-install hypothesis does not rescue it either: `~/.claude/skills` is a symlink farm into the repo and is byte-identical |
| 2026-08-19 | Same brief, finding 4 (a delivery observation offered for discussion, not as an edit) | Its headline — "prefer a check that runs the thing over one that reasons about it" | **adopted with a correction** | `sota-testing/rules/07` §3. The valuable part was not the headline but the **contradiction its evidence exposes**: that bullet said "never assert wall-clock durations" with no carve-out, while the brief's one unit test that caught a live defect *was* a wall-clock assertion (300 ms budget, 30.28 s actual). Now carved out — where the deadline **is** the behaviour, elapsed time is the only oracle; assert it with an order-of-magnitude margin, not a percentage one. Its other two suggestions were **not** taken: moving BUILD step 4 earlier would break a measured placement (and the router has six lines of headroom), and the hook-vs-typed-instruction note is a docs question for the delivery pass · v1.22.11 |
| 2026-08-19 | Operator question alongside the brief — "are pre-commits updated by update.sh as well?" | **"Installed" is per hook TYPE, not per repo.** Measured on pre-commit 4.6.0: adding a *hook* to a config runs without re-installing; adding a *stage* (`pre-push`) writes no hook file, so the gate silently never runs — and `verify-setup.sh` check 9 cannot see it, because the `pre-commit` hook file is present and it counts files | **adopted** | `verify-setup.sh` check 9a (exact stage-token matching — `commit-msg` is a substring of `prepare-commit-msg`), a negative-control probe (harness now **22/22**), `install.sh` re-running the idempotent `pre-commit install` on `--update`, plus README/AGENTS.md/VERIFY-SETUP.md. Found by asking a question about a script, not by reading a rule — and the first cut of the new check aborted its own script under `pipefail` while exiting 0, caught only by running it · v1.22.11 |
| 2026-08-19 | Operator instruction — "fix *nothing checks a document that describes the checks*" | **Invariant 17**: a doc's stated invariant/check count, and its restatement of the negative-control coverage lists, must match what the scripts print | **adopted** | `scripts/check-invariants.sh` [17/17] + probe. Authority derived from the script's own `[k/N]` markers. A count inside `"quotes"` is read as history, so a correction note can still record what a document *used* to say — supersede-don't-edit, made mechanical. The **probe count is deliberately not gated**: a static count reads 13 against an actual 23 · v1.22.12 |
| 2026-08-19 | Roadmap item 9, approved by the operator | **A `pre-push` stage for this repo** — it prescribed one and had none | **adopted** | `.pre-commit-config.yaml`. Runs the invariants at pre-push because that is the first local moment the diff-based 11/14 have a commit to read. Every hook now pins `stages:` explicitly — measured: a hook with no `stages:` key runs at *every* configured stage, which is the doubling the item warned about · v1.22.12 |
| 2026-08-19 | Roadmap item 8, worked | **The Node row was written from recall** | **adopted with a correction** | `sota-sandboxing/rules/04` R5.1 + `sota-javascript-typescript/rules/05`. The row was *right* but incomplete: Node now ships **DEP0190** deprecating args-with-`shell:true`, and Node's `timeout` fires on schedule while leaving the grandchild alive **and reporting `err = null`**. Java remains unmeasured — the JDK is absent here — and is recorded as open rather than asserted · v1.22.12 |
| 2026-08-19 | Reading invariant 17 back the day after it shipped | **A stated count and the actual list drift independently** — correcting "runs N checks" everywhere while forgetting a table row leaves every count claim in agreement | **adopted** | `check-invariants.sh` [17] now asserts `AGENTS.md`'s table and `CONTRIBUTING.md`'s list each enumerate **1..N with no gaps**; watched to fail both ways and to pass after restore. Residual stated in CONTRIBUTING item 17: it does **not** check that row 12 and item 12 describe the same invariant, because matching prose across two deliberately different granularities is not mechanically checkable · v1.22.13 |
| 2026-08-19 | Field brief from a session applying the library — a recon profile that came back empty | **A cap on a generator's *output*, then parsed.** `rules/10` §2.7 covers truncating input *into* an inspector; the inverse — an unset `max_tokens` truncating a JSON document that is then `json.loads`-ed — is the same family and the rule text, example and checklist all point at input | **adopted with a correction** | `sota-code-security/rules/10` §2.7 (the mirror + checklist), `rules/11` §2.2 (the tell: produced size landing on its cap; a parse-error offset needs the document length), `sota-llm-engineering/rules/02` (set `max_tokens` explicitly, assert `output_tokens < max_tokens`) + the three index surfaces that said "truncation before inspection". Correction: the brief reads the class as unstated, and it is stated — for LLM output only, at `sota-llm-engineering/rules/02:199` and `rules/04:251` ("truncated output never parsed as valid"), in a skill an inert-control pass never loads. What was genuinely absent is the **general** producer form, the **unset-default** variant (no truncation operator to grep for, so §2.7's own procedure walks past it), and the size-vs-cap arithmetic — `rules/05:147` alerts on a `stop_reason=max_tokens` spike, which is the metadata tell, not the arithmetic one · v1.22.14 |
| 2026-08-20 | Field brief from a session applying the library — three ideas | **A `--self-test` mutation harness as a mode of the tool**, so "this check can go red" is a property of the health suite rather than of whoever last edited it | **adopted with a correction** | `sota-code-security/rules/12` §1b + checklist, `sota-cli-ux/rules/03` §2a + checklist, two SKILL.md index rows. Correction: the *class* is covered three times over (rules/12 §1 mutation probe, §2.1 "the instrument that cannot fail" — which is literally a mutation harness reading every non-zero exit as a catch — and `sota-devsecops/rules/05`:311 "every gate ships a committed known-bad"). What was absent is the **packaging**: everywhere the library states it, the probe is a committed fixture plus a separate job, i.e. a convention someone must remember when adding a check. Nothing said to make it a mode of the tool, where a check with no declared known-bad *fails the self-test* · v1.23.0 |
| 2026-08-20 | Same brief, idea 3 | **Gateway access logs, still absent — which is why "is this graph feature used?" was answered by measuring the corpus instead** | **adopted with a correction** | `sota-observability/rules/05` §7a + checklist, cross-ref from `sota-api-design/rules/02` §5 step 4, observability SKILL.md row. Correction: the requirement is **already stated**, at `sota-api-design/rules/03`:227 ("without per-field usage data you can never delete anything") and `rules/02`:100 ("You cannot sunset what you can't attribute") — so the accurate verdict is *unreachable, not absent*: it lives in `sota-api-design`, which an observability or platform task never loads, and `sota-observability` mentions access logs exactly once (`rules/05`:56) and only to *exclude* the health endpoint from them. The genuinely new part is the **residual** the brief's incident actually produced — the substitute measurement. `grep -rniE "proxy (metric\|measure)\|answers a different question" skills/` returned zero hits · v1.23.0 |
| 2026-08-20 | Same brief, idea 2 (deferred, then answered the same day with a measured field report) | **The in-band sentinel — a value from the domain standing in for absent** | **adopted** | `sota-architecture/rules/02` §8a (**the class, stated once, language-neutral**), `sota-python/rules/02` §2a (worked example) + checklist greps, `sota-databases/rules/01` *Modeling hygiene* + checklist (persistence half), one-line pointer in `sota-python/rules/03` §12, two SKILL.md rows. Confirmed absent by two searches before writing (`sentinel` → 23 hits, all unrelated; `return -1|in-band|magic (number|value)` → nothing on the class); nearest prior coverage was `sota-c-cpp/rules/04`:25 (one banned-API row) and `sota-performance/rules/05`:170 (the principle, stated once and scoped to cached absence). **Filed to databases `rules/01` rather than the reporter's suggested `rules/02`**: how absence is encoded is a modeling decision, and `rules/02` is migrations. **Scope corrected on review**: the first cut filed the class inside `sota-python`, which would have hidden a language-neutral defect from nine other language readers — the per-language part is the *detector*, not the class. Now a §8a in architecture plus a **measured** row in each of Go, Rust, C/C++, JVM, JS/TS, .NET, PHP, Ruby, and a pointer from Swift. The reporter's measurement is what made it writable — see the entry · v1.23.0 |
| 2026-08-20 | Operator question — "if `sota-code-security` is close to full, can't you split it… maybe `-audit` and `-build`?" | **Split the files, not the skill — and gate `§` references first** | **adopted with a correction** | `scripts/check-invariants.sh` invariant **18** + `scripts/lib/check-section-refs.py` + harness probe 18 (24 probes), then `rules/13` (from `rules/11` §3) and `rules/14` (from `rules/10` §2.10–2.14): 497→357 and 496→362 lines. **Correction, with the measurement**: a skill split buys **no** headroom — invariant 1 enumerates per *file*, so the files arrive unchanged — and build/audit is the wrong axis here because invariant 2 welds an `## Audit checklist` onto all 259 rules files. The build-vs-audit framing is recorded as declined in `docs/ROADMAP.md` item 12, with the defensible seam (classes vs verification) and its router-line cost. The check went first **because the split is what creates the hazard**, and it found six live defects before a single line moved, then caught 27 the split itself broke · v1.23.0 |
| 2026-08-20 | Field brief from a session applying the library — a refinement of `rules/14` §1 | **Computed is not enough — compute it from what you *returned***, and site the claim in the **consumer** | **adopted** | `sota-code-security/rules/14` §1 + two checklist items, with cross-refs added at `rules/11` §2.4 (silence is not evidence of health — *and neither is speech*, when the claim is sited upstream of the effect) and §2.5 (an emission proves the line it sits on ran, not that its result survived the suffix of the function). Verified absent before writing: `git grep` for *site the claim* / *in the consumer* / *derived from the value received* returned only unrelated hits (Go interface placement, backpressure, registry pinning); *intermediate vs returned value* and *the log is the only witness* returned nothing; and `rules/12` §1's probe says only "run the suite" · v1.23.1 |
| 2026-08-20 | **Self-audit of the same day's own work** — "do we have gaps elsewhere?" | Four classes shipped 2026-08-20 were stated only where the incident happened, and were **unreachable from the skills that need them** | **adopted** | `sota-devsecops/rules/05` §5.6 + checklist (a negative control belongs in a `--self-test` **mode of the runner**, not only as a fixture beside it — that file is the canonical home for "every gate ships a known-bad" and a DevSecOps reader never loads `rules/12`), `sota-observability/rules/01` §5 (**"at completion" is load-bearing** — a mid-function line attests only that the line ran; site the claim where the value is consumed), `sota-testing/rules/06` §6.3 (**mutate and read the output, not the suite** — every other probe in that section ends in "run the tests", which cannot answer whether the report is truthful), and `sota-code-security/rules/12` §1b.1 (**a planned change is a legitimate source of a gate**). Verified absent in all four before writing · v1.24.0 |
| 2026-08-20 | Operator question — "are there other bright ideas like this we should adopt?" | Three refinements of the same day's `--self-test`, which collapsed into one gate: **run it always**, **fail closed**, and **pin the exempt set** | **adopted** | `scripts/check-invariants.sh` invariant **19** + harness probe 19 (25 probes, 14 of 19). The third is the one with teeth: without a pin, "every check is probed or declared unprobeable" is satisfied by adding your new check number to the exempt list. Measured first — the structural pass costs **49 ms**, which is what makes "always" defensible. It caught **itself** on introduction. Also derived probe 17's mutation instead of pinning the invariant count, after that literal went stale twice in one day · v1.24.0 |
| 2026-08-20 | Field brief — *a method hierarchy for authoring durable guards* (one session on a 38k-test Python codebase) | **Auditing and authoring are different activities**: the library states a method default for the search and none for the guard the search leaves behind | **adopted with one addition** | `sota-testing/rules/02` §2.10 + three checklist items, cross-referenced from `sota-code-security/rules/10`'s absence bullet; **formatter reflow** added as a fourth mutation-did-not-take cause in `sota-testing/rules/06` §6.3 and `sota-code-security/rules/12` §1. Both of the brief's "not a duplicate" citations verified **accurate** (rules/10:286-292 and rules/06:169), and the gap confirmed: all seven `AST` mentions in `skills/` are about auditing, RAG splitting, Python `match`, or a coincidental Cypher relationship name — **none about authoring**. My addition: **name the parser per language**, because "no parser at hand" is precisely when people reach for regex · v1.24.0 |
| 2026-08-21 | Field brief — *a pipeline is an evidence hazard, not only an exit-status hazard* (three destroyed measurements in one session) | `pipefail` and `${PIPESTATUS[0]}` fix the **status**; nothing in the library said a pipe also destroys the **output**, and the two need different fixes | **adopted** | `sota-shell-scripting/rules/01` §3 + a checklist grep, cross-referenced from `sota/rules/01`'s evidence standard. All three of the brief's citations verified accurate (`rules/01`:47, `rules/01`:124, router `:197`), and the gap confirmed by two independent sweeps. **Reproduced before writing** — and the first reproduction was *wrong*, keeping the cause because it sat last; rebuilt pytest-shaped (cause at the top, summary last), `tail -12` destroyed the `AssertionError` while `1 failed, 38265 passed` survived · v1.25.0 |
| 2026-08-21 | An outside assessment of this library, three criticisms | (1) AUDIT is *mostly performative* at +0.00; (2) high friction — Day Zero *halts*, and the rules force production rigour on a throwaway script; (3) completeness collapses if the model skips the self-audit | **one adopted, two rejected as false** | Checked each against the tree. **(1) conceded and already published** — README:138 and :281 say the audit half *"adds nothing a good model doesn't already do"*, in our own words, across nine instruments. **(2a) false** — the router says *"say it once … then get on with the task"* and *"Offer, never perform"*; no halt exists. **(2b) TRUE and the only one that lands** — a search for a proportionality rule found exactly one hit, in `sota-docs-workflow/rules/05`, which a quick-script task never loads. Now router **operating principle 9**, with a measured re-baseline. **(3) false** — the ablation reads base 0.60 → +rules 0.89 → +self-audit 0.93 → +principle 5 0.99, so dropping the self-audit leaves **+0.29**, not a collapse · v1.26.0 |
| 2026-08-25 | Operator question — "would it help if we rewrite skills files to TOON format?" | [TOON](https://github.com/toon-format/toon) (Token-Oriented Object Notation) as the on-disk format for `skills/*/SKILL.md` and `skills/*/rules/*.md`, to cut context cost | **rejected: measured 1.9% on the best case** | — · TOON's baseline is **JSON**, and Markdown already does its one trick. Converted the router routing table (42 rows, the largest table in the library) to TOON tabular form: **9,992 → 9,802 bytes, 1.9%** — and table rows are **3.1%** of the library (1,955 of 63,885 lines across 300 instruction files), so library-wide that is ~0.06%. Measurement and the cost side in the entry below |
| 2026-08-27 | **Correction to the 2026-08-26 intake** — that report was read to line 318 of **428** | Findings **8 and 9** sat in an addendum below where the reading stopped, so they were never assessed. The "seven findings" recorded on 2026-08-26 is **incomplete, not wrong** | **both now adopted** | Found only because the follow-up brief cross-referenced *"findings 1-9"* and the count disagreed with mine. **A page-at-a-time read of a long file needs its length checked first** — `grep -c` before believing you have the whole thing. Both are in `sota-code-security/rules/10` · v1.29.3 |
| 2026-08-27 | Original report, finding **8** — a flag that parses is not a feature that works | Build-tag-gated features leave the interface compiled in and the implementation stubbed; `--help` describes the source tree, not your binary | **adopted** | `rules/10` **§2.15** + an audit item. Verified absent (two sweeps); the nearest kin is `rules/11` §4's compiled-out `assert`, now cross-referenced. Concrete instance kept: Homebrew `cosign` v3.1.2 lists `--sk` and returns `opening piv token: unimplemented` · v1.29.3 |
| 2026-08-27 | Original report, finding **9** — the same mistake made defensively | The falsification question **cannot** catch a control that is *correctly enforcing the wrong predicate*: something observable does differ, so it answers "yes" and the control is still wrong | **adopted — this is the named rule the follow-up asked for** | `rules/10` §1 now carries **the proxy question** beside the falsification question, with the reporter's four-instance table. Its discriminating half is the second clause — *who can change one without the other, and would I find out?* Not vacuous: it names an observable (no signal on divergence). The class entry stays `rules/14` §4a · v1.29.3 |
| 2026-08-27 | Follow-up brief **A** — a control whose cost contradicted a decision an hour old | A new control that spends a scarce resource per use can reintroduce friction an earlier decision removed; both artifacts are locally correct and no test sees the gap | **adopted** | `sota-architecture/rules/01` **§4a** + an audit item, placed beside the ADR section because the fix is *grep your own decision records*. Verified absent in two sweeps · v1.29.3 |
| 2026-08-27 | Follow-up brief **B** — rehearse a costly command before handing it to a human | A YubiKey PIN blocks after **three** attempts; a command composed from `--help` burned round-trips before a free file-based-key rehearsal got it right | **adopted, narrowed** | `sota-cli-ux/rules/03` + an audit item. **Partially covered already** — `rules/01`:117 covers confirming *your own* destructive commands and `sota-shell-scripting/rules/04`:57 the gate-then-act one-liner; what was absent is rehearsing a command you hand to a *human* on a limited-attempt device, and stating the cost in the handover · v1.29.3 |
| 2026-08-27 | Follow-up brief **C** — never batch a mutation with exploratory reads | A `generate-key` batched after two reads destroyed the key the first read had just printed | **adopted** | `sota-shell-scripting/rules/04` **§1a** + an audit item, next to the existing `&&`-not-`;` rule. Adopted **on reasoning, not reproduction** — the hardware is not available here, but the claim that reads around a mutation describe stale state is structural. Records that it cuts against the efficiency habit of batching independent calls · v1.29.3 |
| 2026-08-27 | Follow-up brief **D** — a durable note records an invariant, not an observation | A handover note recorded an observed capability that an ordinary refactor falsified an hour later, in the direction that makes an agent ask for help it does not need | **adopted** | `sota-docs-workflow/rules/01` **§11** + an audit item. Directly applicable to agent memory files, which is why it is stated as *name what would falsify it* · v1.29.3 |
| 2026-08-27 | Found while adopting finding 8 — **invariant 18 checks the wrong half** | A `§` reference I wrote pointed at `rules/11` §5 when the content is in §4. The gate passed, because §5 exists | **recorded, not gated** | Invariant 18 verifies a reference **resolves**, not that it points at the right content — the proxy shape, in our own gate, on the same day we adopted a rule about it. Not gatable: "is this the right section?" is semantic. The mitigation is the rule now in `rules/10` §1 — the reference was fixed by reading the heading, not by trusting the gate · — |
| 2026-08-27 | **Operator question — "should we generalize some rules? fix all issues found on the way"** | Whether the rule-17 / rule-21 shape deserves a general meta-rule, plus a sweep for anything else broken | **generalisation REJECTED as vacuous; the mechanism adopted instead** | A meta-rule ("any domain can hide anywhere") carries no routing signal and would cost router lines — rules 17 and 21 work *because* they name a concrete surface. What generalises is the **loop**: a routing gap should end as a regression case, now stated in the router's gap-reporting section and backed by `cases/desc-routing-regressions.jsonl` + a `--cases` flag. The sweep found a real one: `run-build-safe-arms-guided.py` prepended **world-writable `/tmp`** to `sys.path` (vestigial) and crashed with a raw `IndexError` instead of usage. Also produced `evals/smoke-runners.py`, watched to fail before being gated · v1.29.0 |
| 2026-08-27 | **Operator question — "how come you violated a rule the library already had?"** | The token-counting rule was in `sota-llm-engineering/rules/02` §2 the whole time, and a maintenance task never reached it | **adopted — a ROUTING fix, measured** | **UNREACHABLE, not absent**, the same verdict shape as v1.22.14. Diagnosed from three surfaces: the skill `description` (the only auto-loading text, and the whole classifier) carried `token budget` but not `count`/`tokenizer`/`measure`; the routing-table row said *"**Building** LLM features"*; cross-cutting rules 5 and 8 both said *"AI/LLM **features**"* — and the task was repo maintenance. A second source also missed: the bundled `claude-api` skill has a *"how many tokens is X"* trigger that only fired later, on an unrelated API error. Fixed in all three places plus new router **rule 21**, shaped as a sibling of rule 17 (*model facts hide in your own tooling*). **Proved, not asserted**: a regression case routed to `sota-docs-workflow` **3/3** before and `sota-llm-engineering` **3/3** after ([write-up](../evals/results/2026-08-27/ROUTING-REGRESSION-TOKEN-COUNT.md)) · v1.29.0 |
| 2026-08-27 | Found while building that proof | `run-desc-routing.py` **could not execute at all** — an ablation guard called `.splitlines()` on the list `catalogue()` returns, raising before the first API call | **adopted (defect fixed)** | The guard landed 2026-08-05 in PR #223, *an instrument audit*; the last recorded run of this eval is 2026-07-13 — **before** it. A guard added to prevent a fake null made the instrument unrunnable, and nothing re-ran it to notice (`sota-code-security` rules/12). Fixed and **watched in both directions**: 9 descriptions differ normally, a neutered `XREF_RE` yields 0 and still aborts · v1.29.0 |
| 2026-08-27 | Same work — a rule of ours that read as forbidding good practice | `rules/01` §8 banned selecting eval cases by outcome, full stop — which on a plain reading forbids **regression** cases | **adopted (rule refined)** | Selection-by-outcome poisons a *measurement* set and is the entire point of a *regression* one. §8 now draws the line, with a checklist item, and the regression cases live in their own file behind a new `--cases` flag so they cannot be averaged into the published A/B. Found by the fix tripping the rule I had written hours earlier · v1.29.0 |
| 2026-08-27 | **This session operating the repo** — Dependabot could not pass CI | A gate whose scanner needs a secret **fails on bot PRs**, because Dependabot branches are same-repo (so "trusted run" conditions are true) while its token is denied repository secrets — and the tempting fix, exempting `dependabot[bot]`, silently removes the control on exactly the PRs that change the dependency graph | **adopted** | `sota-devsecops/rules/01` **§1.10a** + two audit-checklist items. Verified absent first: rules/01 covered the *security* direction (`pull_request_target`, fork PRs, SHA pinning) but not this operational trap. Includes the two sub-traps hit here — the **value shape** (a secret must carry the form the consumer reads: pipe-joined regex, not the file's on-disk layout) and **what the bot maintains narrowly** (it rewrites the trailing `# vX.Y.Z` beside a pin and nothing else, so a version in a prose comment goes stale on the next bump) · v1.28.1 |
| 2026-08-27 | Same session — the token-count error | "Count tokens with the provider's counter, never another vendor's tokenizer" | **rejected: already covered — but the MAGNITUDE was understated, and that is adopted** | `sota-llm-engineering/rules/02`:74 already said it, exactly: *"Measure with the provider's token counter… Never use another provider's tokenizer."* **The library was right and this session broke the rule anyway** — using `o200k_base` for a Claude budget, then *rejecting* the correct Anthropic figure with a sanity check calibrated on the wrong tokenizer. What was wrong is the stated size: rules/02 said **15–20%+**, and measurement on markdown-dense text gives **54%** (16,934 via `count_tokens` vs 10,995 via `o200k_base`), with a chars/4 doc estimate **60%** under. Magnitude corrected in place with the measurement · v1.28.1 |
| 2026-08-27 | Same session — two lessons **considered and NOT added**, recorded so they are not re-litigated | (a) a local harness that mutates a worktree **at HEAD** can pass while CI fails on your working tree; (b) a limit you keep paying deserves one measurement before you pay it again | **rejected: repo-specific / too meta for a rules file** | (a) is a property of *this* harness's design, not a general practice — it is recorded in `evals/README.md` and the memory instead. (b) is engineering judgement rather than a checkable rule; it drove ROADMAP item 4 and the router refactor, and a rules file cannot probe "did you measure the constraint?". Both remain true and useful; neither earns skill text · — |
| 2026-08-26 | **Field brief from a session applying the library** — seven defects it did not prevent, one session building a gate-ledger script (Rust + bash) | Six gaps in `sota-shell-scripting` / `sota-code-security`, plus two routing changes. **Finding 2: a rule in this library, followed literally, produces a vacuous pass** | **all seven adopted, one narrowed, one correction added** | Three falsifiable claims **reproduced on this machine before adopting**: `$( )` newline stripping glues composed records; BSD `chmod 700 -- dir` fails with *"No such file or directory"* while `mkdir -p --` succeeds alongside it; and `git rev-list -3` exits **129** into a process substitution, yielding `count=0` and a "nothing to check" exit 0. Landed: `sota-shell-scripting/rules/01` §2 (newline stripping) and `rules/02` §4/§5/§9 (proc-sub status, `--` portability, unordered selection, keyed-store upsert); `sota-code-security/rules/14` §4a (proxy predicate) and `rules/12` §2.1 (probe scope, now **five** failure modes). Every one shipped with its audit-checklist half in the same change · v1.28.0 |
| 2026-08-26 | Same brief — finding 3 (`--` is not portable) | Claimed as an unqualified gap | **adopted with a correction** | The hedge already existed — `sota-golang/rules/05`:91 says *"Use `--` end-of-options **where the tool supports it**"*. So the verdict is **UNREACHABLE, not absent**: correct guidance sitting in a skill a shell task never loads. Landed in `sota-shell-scripting/rules/02` §5 with the macOS reproduction and a pointer to the sibling · v1.28.0 |
| 2026-08-26 | Same brief — **a correction the brief did not make** | Its remedy for finding 2 uses `out="$(cmd)"`, which is command substitution — and therefore **re-introduces finding 1** | **adopted with an addition** | The remedy survives only because `<<<` puts a trailing newline back, and it buffers the whole producer output in memory. Both caveats are now stated beside the GOOD example, so applying fix 2 cannot silently reintroduce bug 1. Found by reading the two findings against each other rather than in sequence · v1.28.0 |
| 2026-08-25 | [awesome-ai-plugins](https://github.com/hashgraph-online/awesome-ai-plugins) listing invitation, and the `plugin-scanner` run it triggered on this repo | Their scanner reported **8 findings on SOTA-skills**: 7 high + 1 low | **one adopted, seven rejected as false positives** | Reproduced locally with `plugin-scanner==2.0.1116` and checked every one rather than assuming. **Adopted: `DEPENDABOT_MISSING` (low) was correct** — `.github/dependabot.yml` added, scoped to `github-actions` (the only third-party surface: `actions/checkout`, SHA-pinned in 5 places). **Rejected: all 7 highs.** 3× `DANGEROUS_DYNAMIC_EXECUTION` match the word *eval* before a parenthesis in **docstring prose** (`grep -rn 'eval(' evals/*.py` → no matches; only `re.compile`); 4× `HARDCODED_SECRET` are the OpenAI `sk-` prefix inside ordinary English — *ri**sk-r**eduction*, *di**sk-m**anaged* — plus a snippet that *generates* a prefixed token and the deliberately-vulnerable audit fixture. Both regex bugs reported upstream on the PR · **listing PR merged 2026-08-26**; the deliberately un-bumped pin drew Dependabot **#281** (merged 2026-08-27, now `v7.0.1` = latest), proving the automation runs · v1.27.0 |
| 2026-08-25 | Same scanner run — the *class* behind its false positives | A pattern-based control's false-positive rate is a property you must measure on your own corpus before trusting its verdict | **rejected: already covered** | `sota-detection-engineering/rules/04` §1 (*"Alert fatigue is the dominant failure"*, *"Precision over recall at the alert tier"*) and §2 (*"Tune by adding context, not by deleting detections"*) already own this class. The scanner episode is an **instance**, not a new class — recorded so it is not re-litigated as a gap · — |
| 2026-08-25 | **This session's own eval work** (ROADMAP item 21) | Building an eval set out of the cases a model got wrong measures the selection, not the system | **adopted** | `sota-llm-engineering/rules/01` §8 + an audit checklist item. Distinct from the **contamination** bullet already there: that tunes the *prompt* against the set, this builds the *set* from outcomes. Found by nearly doing it — 10 of the old 32 freshness cases still discriminated and reporting those alone would have produced a large number measuring nothing · v1.27.0 |

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
worktree-lock ideas got in the earlier orchestration-project pass (PRs #112-114).
The one idea inside
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

### 2026-08-11 — spanchain (ghostfactory-art), three adopted, three rejected, one deferred

Source: <https://github.com/ghostfactory-art/spanchain> — an Elixir/OTP hash-chained
audit ledger for AI agent runs (MIT, v0.x, 1 star, created 2026-06-06, last push
2026-06-15). Read: `README.md`, `docs/arch/hash-chain.md`, `docs/arch/eval-and-replay.md`,
`docs/arch/open-questions.md`, plus repo metadata and the commit list via `gh api`.

**Why a 1-star project was worth reading.** Its architecture docs state the *limits* of
its own crypto rather than the marketing version — the README says "immutable,
cryptographically verifiable" while `hash-chain.md` says an attacker with DB write can
recompute a clean chain. Six of its lessons are already in `sota-code-security/rules/04`
§8, arrived at independently on both sides; that convergence is the reason to trust the
three that were **not** there.

**The three adopted are one incident, one omission, and one sentence.** The incident
(their GF-666) is an interior-segment deletion that verified clean because each epoch
restarted `prev_hash = NULL` *and* the verifier reset its carried hash at the boundary —
so it landed twice, as a ledger rule in `rules/04` §8 and as a fourth guard form in
`rules/12` §3, since the defect was in the checking, not the writing. The omission is
that every canonicalization mention in the library framed it as an attacker problem; the
false-alarm direction (non-deterministic encoder → tamper reported on untouched records →
alarm muted → inert control) was absent, and no file named a canonicalization spec. The
sentence is the README's "Replay validates Span Chain's integrity, not your agent's
behavior", which generalises to any cassette harness wired into a CI quality gate.

**Verification.** RFC 8785 confirmed at rfc-editor.org (JSON Canonicalization Scheme,
June 2020, Informational, Independent Submission). The Go quote is verbatim from the
language specification, "For statements with range clause"; the Elixir quote is verbatim
from the `Map` documentation. **Not verified and therefore not asserted:** the ">32 keys
switches to a HAMT" threshold their doc gives as the cause — the official Elixir docs
state only that map entries follow no order, so `rules/04` says the order "may change
with size as the map switches internal representation" and gives no number.

**Not usable as an audit fixture.** The obvious hope — a real repo with a real defect,
which [`ROADMAP.md`](ROADMAP.md) records as the only remaining route to measuring audit
recall — does not survive contact: the public history is 18 commits starting from a
squashed `Initial release — Span Chain v0.1.0` (2026-06-07), so the pre-fix verifier is
not in it. Only the narrative is.

**Measurement status:** adopted on reasoning. **No efficacy lift is claimed or measured.
Do not cite one.**

### 2026-08-17 — system-design-notes (liquidslr), three adopted, two deferred, four rejected

Source: <https://github.com/liquidslr/system-design-notes> — 12.3k stars, 2.4k forks,
created 2024-12-24, last push 2026-08-12. Read: all 29 Markdown files (~356 KB of prose;
the other ~83 MB is figures), plus repo metadata via `gh api`. It is chapter notes on
*System Design Interview — An Insider's Guide* (Vol 1+2), which its own README states.

**The licence decides the shape of every adoption here.** `gh api` returns
`"license": null`, and a recursive tree scan for `licen|copying|copyright` finds nothing —
the root holds only `.gitignore` and `Readme.md`. So the repo is all-rights-reserved *and*
derivative of a copyrighted book, while this library ships CC BY 4.0. Nothing was copied:
no text, no tables, no figures, and not the chapter structure, which is the book's. What
was taken is the *idea class*, re-derived and re-worded here, and the credit belongs to
the idea rather than to this repo. That constraint is worth recording because it will
recur — notes-on-a-book repos are a large and popular genre, and most of them are
unlicensed.

**Interview-prep material is a weak source, and the yield reflects that.** Twenty-three of
the twenty-eight chapters produced nothing: rate-limiter algorithms, consistent hashing,
Snowflake IDs, quorum arithmetic, watermarks, lambda/kappa, delivery semantics, DLQs,
optimistic locking and idempotency keys are all already ours, in most cases in more
operational detail than the source carries. One chapter is actively **contrary** — ch06
teaches CAP as "pick two of three" with a "CA system" category, where `rules/03` §1 is
PACELC and per-operation. The three adoptions all come from the Vol-2 financial chapters
(26–28), which is the part of the book with a domain the library had not modelled.

**The gap they exposed is money, specifically.** The library had `debit` and `double-entry`
at **zero** hits across `skills/`, confirmed by a second sweep on the concepts
(`accounting|two legs|sums to zero|money movement`) that returned only unrelated matches.
It knew a great deal *about* money — float money is banned in five language skills, prices
must be recomputed server-side, `UPDATE ... WHERE balance >= x` is the atomic-claim
pattern, counters are not idempotent so use "ledger rows with unique keys"
(`sota-databases/rules/04:117`) — but nothing said how to **model** the ledger those rules
kept gesturing at, and nothing carried the balanced-pair invariant that turns a one-sided
write into a constraint violation. Half the rule was already there for a different reason;
the half that makes the database reject the bug was missing.

**Reconciliation was present eight times and absent as a rule.** Every existing hit is
domain-bound: orphaned accounts (`sota-identity-access/rules/04:51`), a webhook consumer's
backfill API (`sota-api-design/rules/06:119`), pipeline row counts
(`sota-data-engineering/rules/02:103`), GitOps drift. None of them generalise, and the
general statement is the one that matters — it is the **completeness** check on a seam
where §2–§4 only buy integrity, which is the same integrity-vs-completeness distinction
`sota-code-security/rules/04` §8 already draws for audit ledgers. It also inherits that
file's failure mode, so §5b ends by pointing at `rules/11` §2.2: a reconciliation that has
never reported a break has the inert-control signature, and must print its denominator on
*both* sides.

**Verification — the DDL was executed, not just read.** The
[PostgreSQL CREATE TRIGGER reference](https://www.postgresql.org/docs/current/sql-createtrigger.html)
says a constraint trigger may only be `AFTER` and `FOR EACH ROW`, and that `DEFERRABLE
INITIALLY DEFERRED` fires it at end-of-transaction rather than end-of-statement. The
rule's schema and trigger were then run verbatim on **PostgreSQL 17.11** in a throwaway
container, with the negative control first — because a deferred check that quietly fires
at statement time would still *pass* a happy-path test:

- one-sided write → `INSERT 0 1` **succeeds**, and the transaction fails at `COMMIT`
  ("journal … unbalanced in USD: sums to -500"). That asymmetry is the whole proof that
  the deferral is real;
- legs of −500/+499 rejected; a journal netting to zero **across** USD and EUR rejected —
  which is the claim that the check must group by currency;
- replaying the same operation conflicts on `journals.external_id`, while NULL
  `external_id` repeats freely for internal journals;
- `BEFORE` and `FOR EACH STATEMENT` are **syntax errors**, so a reader who ignores those
  two restrictions is stopped rather than silently downgraded.

**Corrected during the review, not asserted:**
the first reading of ch16/ch18 was written up as a geospatial coverage *gap*;
`sota-databases/rules/03:40` already lists geometry under GiST, so the entry says "thin,
not absent" and the idea is deferred rather than adopted.

**Sample size is one.** Every adoption rests on a single book's treatment, which the log's
own discipline would normally push toward `deferred`. They were taken anyway because none
of the three is a project's trade-off: double-entry bookkeeping predates computing,
reconciliation is standard practice wherever two ledgers meet, and debit-before-credit is a
statement about which failure states are recoverable, not a preference. The two ideas that
*are* judgement calls — the event-sourcing determinism clause and geospatial — are deferred
with the condition to revisit.

**Not added to the top-10.** `sota-architecture`'s non-negotiables list is exactly ten and
curated; neither new rule displaces anything on it.

**Measurement status:** adopted on reasoning. **No efficacy lift is claimed or measured.
Do not cite one.**

### 2026-08-19 — a recon profile that came back empty, and the half of §2.7 that was missing

**Source.** A field brief from a session applying the library: an LLM-backed reconnaissance
step reported `Relevant CWEs: 0, Confidence: 0%` on a codebase that was not empty, and the
result was then cached against the source-tree hash so every later run reused the failure.

**The chain, as reported and reproduced by the reporter.** Four links, and only the first is
a bug in the ordinary sense: (1) the call passed no `max_tokens` and silently inherited a
chat-sized `4096` default; (2) the provider returned a **syntactically incomplete** document —
4,843 characters ending mid-array, no exception, no flag; (3) the parser's
`except (json.JSONDecodeError, Exception)` converted the hard failure into a *valid* empty
profile — correct type, in-range confidence, empty lists, indistinguishable from "this
codebase has no notable CWEs"; (4) a downstream threat model was built on the empty profile
and persisted.

**Three of the four links were already covered**, which is why the brief is worth logging
rather than just fixing: `rules/10` §2.4 (swallowed exceptions on the enforcement path) is a
direct hit on link 3, `rules/10` §2.3 names exactly this shape ("distinguish *empty because
configured empty* from *empty because parsing dropped everything*"), and `rules/11` §1 ("zero
is a legitimate answer") explains why the failure survived: `0 CWEs / 0% confidence` is a
shape a healthy run also produces.

**What was not covered — link 1.** `rules/10` §2.7 is the nearest rule and its text, its
example (`scan(payload[:8192])`) and its checklist line all point at truncation **into** an
inspector. An auditor following it literally greps every `[:limit]` on a scan input and walks
straight past a `provider.complete()` with no `max_tokens`. Adopted as the mirrored half of
§2.7, framed on the tell that makes it findable: **there is no truncation operator to grep
for** — the cap lives in a default the call site never names.

**Correction to the brief.** It reads the class as unstated; it is stated — for LLM output
only, at `sota-llm-engineering/rules/02:199` ("Check `stop_reason` before parsing.
`max_tokens` → truncated JSON") and `rules/04:251` ("truncated output never parsed as valid").
So the accurate finding is not *absent* but *unreachable*: the rule lives in a skill an
inert-control audit never loads, and it is scoped to one producer type. The brief's second
claim — "nothing says check the output-token count against the cap" — survives with a caveat:
`rules/05:147` alerts on a **spike in `stop_reason=max_tokens`**, which is the metadata tell,
and depends on a wrapper that surfaces `stop_reason` at all. The arithmetic tell
(`output_tokens == max_tokens`) was genuinely nowhere, and is now `rules/11` §2.2 — it is the
cheapest check in this family and costs one comparison.

**The diagnostic sub-lesson, adopted verbatim in substance.** The reporter first argued
*against* truncation from "4,096 output tokens, failure at char 3,023", reasoning that 4,096
tokens should yield 12–16k characters — sound reasoning, wrong conclusion, because 3,023 was
the last character of the document. **A parse-error offset is uninterpretable without the
document length.** Landed alongside the tripwire in `rules/11` §2.2, which is the denominator
section: an offset is a numerator.

**Measurement status:** adopted on reasoning and on the reporter's reproduction. **No efficacy
lift is claimed or measured. Do not cite one.**

### 2026-08-20 — three ideas from a session applying the library; two adopted, one deferred on placement

The intake shape from `docs/MAINTENANCE.md` again: a session that *used* the library
hands back what it found missing. Two of the three were already covered as classes and
missing as **mechanisms**, which is the correction worth recording — a keyword search
would have closed both as "already covered" and shipped nothing.

**1. `--self-test` as a mode, not a harness.** The library states the mutation probe
(`rules/12` §1), states that an instrument must be watched to produce a wrong answer
(§2.2), states that every gate needs a committed known-bad (`sota-devsecops/rules/05`
§5.6), and even names this exact failure — §2.1's *"a mutation harness reporting 18/18
controls caught while every run died before the test suite started"*. In all of it the
probe is an artifact **beside** the checks. The brief's claim is about ownership: a
harness in a separate CI job proves today's checks can fail and says nothing about the
check added next week, because joining it is a convention enforced by prose and a
reviewer. Put the probe inside the tool and a check with no declared known-bad fails
the self-test, which moves the property from a person to the suite.

This repository is the worked example, and it is on the wrong side of its own new rule:
`scripts/check-negative-controls.sh` is a separate CI job, the "add your known-bad here
too" instruction lives as a sentence in `AGENTS.md`, and "12 of 17 invariants are
probed" — the gap being reported only because the harness prints it.

**Closed later the same day.** That paragraph was written as an argument for someone
else to act on; the argument was good enough to act on immediately.
`check-invariants.sh --self-test` now fails on any check that is neither probed nor
declared unprobeable, deriving both sets from the harness so there is no second list to
drift (ROADMAP item 14). The counts above are left in quotes as what was true that
morning — invariant 17 reads a quoted number as history, not a claim — and the current
figures are 24 probes, 13 of 18.

**2. Gateway access logs.** Filed as absent; it is *unreachable*. `sota-api-design`
rules/02 §5 step 4 and rules/03 §11 both state the requirement, one of them in the
brief's own words ("without per-field usage data you can never delete anything"), and
`sota-observability` — which owns the telemetry pipeline under router rule 12 — mentions
access logs once, to say the health endpoint should be excluded from them. Second
release running, the accurate verdict is a **skill boundary**, not a coverage hole.

The reusable part is the half the incident produced and no rule stated: with the signal
absent, the question got answered from the **corpus**, which measures whether data
shaped like the feature *exists* rather than whether anyone *requests* it. Those differ,
and the error has a direction — stored data outlives its last reader, so the substitute
over-reports use and argues for keeping the feature. That generalises (commit count for
maintenance, manifest presence for reachability — `sota-devsecops/rules/03` §3.9 — a
dashboard existing for someone opening it), so it landed as a class in
`sota-observability/rules/05` §7a rather than as a line in the deprecation pipeline.

**3. The in-band sentinel — deferred on placement for one turn, then adopted.** The
class was clearly absent (searches in the table row) and clearly the kind of thing this
library exists for, but the layer was unknown, and a rule filed to the wrong layer ships
a detector nobody runs against the code that has the defect. The reporter came back with
a declaration, a caller, and — the part that decided the rule's shape — a **measured
per-field distribution** over 505,079 real rows.

What that measurement changed, and why the rule would have been wrong without it:

- The obvious rule is *"lint for `-1` in this field"*. Sound on five of the eight fields
  the reporter measured (0 legitimate negatives, 9–99.95% sentinel), and **100% false
  positive on two of them**, where the upstream producer emits `-1` legitimately (an
  index meaning "not an argument"). One converter, one sentinel constant, eight fields,
  **heterogeneous domains** — so the rule keys on the **declaration** (a producer
  returning the same constant from a not-found branch and an `except` branch), and a
  value lint is added only per-field, behind a domain declaration that in practice does
  not exist yet. Writing that declaration down is part of the fix, not a prerequisite
  for it.
- On the two ambiguous fields the sentinel is **unrecoverable in principle**: a stored
  `-1` could be the producer's real value or a converted empty, and no amount of
  downstream care can tell. That is the argument for `NULL`/omitted-property in the
  persistence half — a graph or document store has native absence, so writing a sentinel
  *discards* information the store would have kept for free.
- The reporter checked all four failure modes I proposed and returned **three noes with
  evidence** (no aggregates over the field in a 2,141-query catalog; 0 of 16,631 findings
  displaying a negative line; no sorts) and one yes: **comparison against a threshold**,
  in 102 clauses across 41 rule files using line-number ordering as a temporal proxy. The
  three noes are what let the rule say *check the queries that order or compare first*
  instead of listing every hazard equally.

**The tell the rule is built on is the reporter's, and it is the best part of the brief:
the author knew.** In the guard they found, the *collection* side of a comparison is
filtered against the sentinel (`x > 0`) and the *scalar* on the other side of the same
`<` is not. Sentinel-filtering is applied per-site, so it lands wherever the author was
thinking about it and is omitted everywhere else — which makes an **asymmetric guard** a
far better audit signal than the sentinel constant, and it is visible in a diff. The
`if line_num:` presence check above it is defeated by the same value, since `-1` is
truthy.

**Scope honestly recorded, from the reporter's own framing:** static reachability plus a
measured input rate (the field is empty in 9.2% of nodes), with no before/after showing a
specific result gained or lost. **Latent with measured exposure, not active.** The rule
is written to that standard — it claims the predicate flips, not that a given finding was
missed.

**Scope corrected on review — the first cut filed it in the wrong place.** I put the
class inside `sota-python` and justified it with "the producer is a function return and
the greps are per-language". That justifies per-language **detectors**; it does not
justify a per-language **class**, and filing it there would have hidden a universal
defect from nine other language readers. The library already has the pattern for this —
router cross-cutting rule 18, *"cryptography fans out — there is no single crypto
skill"*. So: the class is stated once and language-neutrally in `sota-architecture`
rules/02 §8a (next to *value objects and invariant-encoding types*, which is the same
idea for a different axis), and each language skill carries the row that is actually
specific to it.

**Every language row was run, not recalled** — the [[cross-language-summary-tables-are-unverified]]
lesson, applied deliberately after a Rust row in `sota-sandboxing` rules/04 shipped wrong.
Seven of nine on a local toolchain (Python 3.14.6, Go 1.26.5, Node 24, PHP 8.5.8, Ruby
4.0.6, rustc 1.97.1, clang 21), two from primary docs because no JDK or .NET SDK is
installed here (Java SE 21 API docs; learn.microsoft.com `Int32.TryParse`, .NET 10) and
labelled as such in the text. Two results changed the content rather than confirming it:

- **The C row is platform-dependent, and I would have written it as universal.**
  `(char)EOF == EOF` is **true** under the default signed `char` on x86-64 Darwin and
  **false** under `-funsigned-char` (the default on ARM/PowerPC Linux) — so the classic
  `getchar` bug is invisible on many developers' machines. And the diagnostic runs the
  wrong way for them: clang emits `-Wtautological-constant-out-of-range-compare` only in
  the *broken* configuration. That is `sota-code-security` rules/11 §3.5
  (location-dependent silence), cited in place.
- **JS `NaN` is better-behaved than `-1`, which inverts the obvious advice.** Measured:
  `NaN > 20` and `NaN < 20` are **both false** (and `NaN === NaN` is false), so `NaN`
  *poisons* and can never silently win a comparison; `-1 < 20` is **true**, so `-1`
  *lies*. `parseInt`'s `NaN` is therefore the safer of the two sentinels. Also recorded:
  `-1 ?? fallback` is `-1`, so `??` does not rescue a sentinel.

Also measured and used: PHP's `strpos("abc","a") == false` is **true** while `=== false`
is false — the canonical instance, and the reason PHP's row is the strictest; Ruby's
search methods return `nil` (clean) while `"12abc".to_i` is `12` (silent partial parse);
Rust's `None::<i32>.unwrap_or(-1)` is `-1`, which is how the sentinel re-enters a
language that had designed it out; Go's `strings.Index` → `-1` is documented and
idiomatic, so its row is about *undocumented* ones and about dropping `Atoi`'s error.

**Not landed, and why:** the audit-sweep half belongs in `sota-code-security` rules/10
§2 or rules/11 §3, which are the files that catalogue exactly this shape. Both are at
**496 and 497 lines against the 500 cap**, so adding a class there means reflowing one
of them — a separate change with its own review, not a squeeze. The detectors live in
the two rules files' audit checklists meanwhile, so the audit half is not missing, only
filed further from where a sweep would look.

**Measurement status:** adopted on reasoning. **No efficacy lift is claimed or
measured. Do not cite one.**

### 2026-08-20 — a refinement of rules/14 §1, from the session that hit it

`rules/14` §1 already said every reported number must be **computed from the artifact it
produced**, not printed as a literal. The brief's claim is that this passes a defect it
should catch, and the worked instance is convincing: `len(mandatory)` logged beside the
computation kept printing `1 adjudicated` after `return mandatory + sampled` became
`return sampled`. The count was computed, from a real collection, at a line that really
ran. It was still false, because the collection it counted no longer left the function —
and **nothing about the emission was wrong**, which is exactly why nothing about the
emission changed.

Three parts, all adopted:

- **Compute it from what you returned**, not from an intermediate that is later
  discarded. This is the narrowing the existing rule lacked: "the artifact it produced"
  is satisfied by an intermediate.
- **A function cannot attest to its own return value** — every emission site has a
  *suffix* (a filter, an early return, an exception path, a reassignment) that can drop
  or reshape the result after the line is written. Hence: **site the claim in the
  consumer**, derived from the value received. That is the reporting-output twin of
  `sota-kubernetes` rules/04 §7, adopted at v1.22.11 for write-back controllers — a
  success log is a claim about what was *decided*, not about what *landed*. The class
  generalising across two unrelated domains is the argument for stating it plainly.
- **Probe by mutating the application and reading the output, not the suite.** `rules/12`
  §1's probe answers *is this tested*; this asks *does the log tell the truth*. They come
  apart precisely where it matters — an **unattended run has the log as its only
  witness**, so a log unchanged by the mutation is itself the finding.

**Verified absent before writing**, three independent searches: *site the claim* /
*in the consumer* / *derived from the value received* returned only unrelated hits (Go
interface placement, consumer backpressure, registry digest pinning); *intermediate
value vs returned value* returned nothing on the class; *only witness* / *unattended*
returned one shell-scripting hit about install scripts. `rules/12` §1 step 2 reads
"Run the suite" and nothing else.

**The footnote is the best evidence in the brief.** The reporter's first test for this
defect **failed on its own explanatory comment**, which quoted the log line it was
hunting for — matching the *words* instead of the *emission*. That is precisely the
keyword-vs-shape trap `rules/14` §1 already warns about, committed while writing the
detector for that very paragraph. Recorded in place, because a rule that catches its own
author while he is implementing it needs no further argument for being stated.

**Measurement status:** adopted on reasoning and the reporter's observed behaviour. **No
efficacy lift is claimed or measured. Do not cite one.**

### 2026-08-20 — authoring vs auditing, and the guard that matched its own comment

A field brief proposing a method hierarchy for **authoring** durable guards: AST as the
floor for structural claims, execution for behavioural ones, mutation on both, regex only
where no parser exists.

**Both "this is not a duplicate" citations were checked and both are accurate** — which
is worth recording, because the failure mode of a well-argued proposal is usually its
citations (see 2026-08-05, where one of two reports did not survive quoting).
`sota-code-security/rules/10`:286-292 does carry *"a negative claim needs more proof than
a positive one"* together with the *"second independent method (grep **and** AST/call-graph
**and** a mutation run)"* wording, and `sota-testing/rules/06`:169 does warn that the
mutation may not have taken. The brief's point is that **both govern the search, not the
guard** — and that is right. The distinction the library was missing is one of *lifetime*:
an audit search is discarded the day it runs; a guard is a standing claim re-evaluated on
every commit by people who will not re-derive it, so it deserves the stronger default.

Gap confirmed independently: all seven `AST` mentions in `skills/` are about auditing, RAG
chunk-splitting, Python `match` destructuring, or a Cypher relationship type that happens
to be spelled `[:AST*]`. None is about the method a guard is written in.

**The strongest evidence is a recurrence, not the argument.** Failure mode 1 — *a guard
matched its own explanatory comment*, a regex for `Scanner\s*\(` flagging the file that
documented in a comment that the call had been removed — is the **second independent
report of that exact shape in one day**. The earlier one was a test that failed on its own
comment because the comment quoted the log line it hunted for. Two different people, two
different guards, the same trap, hours apart. That is a class, not an anecdote.

**Adopted with one addition.** The brief's hierarchy is stated as written, including its
honest limit (AST does not resolve types, so a name collision reads as live — a **false
negative**, the more dangerous direction, and the output stays a candidate list rather
than a verdict). What it does not say, and what decides whether the rule is followed:
**name the parser, per language.** AST is free in Python/Go/Rust/Ruby and an install away
elsewhere, and "no parser at hand" is exactly the moment someone reaches for regex — so
the parser choice belongs in the same decision as the guard, not in a later one.

**Formatter reflow** is adopted as a fourth mutation-did-not-take cause alongside the
environmental three. It is the most common cause in any repo running `ruff format`,
`black` or `prettier`, and the one least likely to be caught by an environmental
checklist, because nothing about the environment is wrong.

**A finding about our own instrument, from writing this up.** Invariant 18 rejected the
new §2.10 — it read a backticked configuration value, `` `16` ``, as the `` `NN` ``
rules-file shorthand and reported `rules/16 ... does not exist`. A false positive on
correct prose, which is the failure that gets a gate switched off. The shorthand now has
to sit **immediately** before the `§` (the only way it is ever actually written), while
the explicit `rules/NN` form keeps its wide window. Verified discriminating: pointing
`` `02` §9 `` still resolves to `sota-threat-modeling/rules/02`, which has a §9, from a
file that has only §1–§7. References resolved: 1,363 → 1,368.

**Measurement status:** the brief's 74 → 61 orphan-candidate figure is the reporter's,
on their codebase, and is quoted as such. **No efficacy lift is claimed for the library.**

### 2026-08-21 — the pipe keeps the number and throws away the evidence it is wrong

`sota-shell-scripting` rules/01 §3 already covered the status half correctly, and the
brief says so rather than claiming novelty: `$?` after a pipeline is the last stage's,
`${pipestatus[1]}`/`${PIPESTATUS[0]}` are the fixes, and the preamble prescribes
`set -euo pipefail`. All three citations checked and all three accurate.

**What was genuinely absent is the second failure mode of the same construct.** Every
existing line treats a pipeline as a hazard to the *exit status*. It is equally a hazard
to the *output*, and `pipefail` does nothing for that half — a run can have a perfectly
correct exit status and have thrown away the only copy of the diagnostic explaining it.
Two independent sweeps found nothing on it; the one near-miss
(`sota-cli-ux/SKILL.md`:57, `tool cmd > out.txt 2> err.txt`) is about testing a CLI's
output contract, not about preserving your own measurement.

**The asymmetry is the reason it deserves a rule rather than a tip.** `tail` is *selected*
to keep the summary line. So the surviving output is the number, and the destroyed output
is the traceback, the warnings and the stderr context — precisely the material that would
tell you the number is not to be trusted. The line most likely to be quoted in a report is
the line the truncation is designed to preserve. That is the `rules/10` silent-control
shape (a result that looks identical whether or not the thing worked), reached from the
harness side instead of the product side.

**Reproduced before writing, and the first attempt was wrong.** A nine-line script with
the `AssertionError` last "survived" `tail -3` — which would have supported the opposite
conclusion. Rebuilt to the shape the brief actually describes (200 progress lines, cause
at the top, summary last, as pytest prints): `tail -12` destroyed
`AssertionError: expected 16, got 4` while `1 failed, 38265 passed` came through intact;
redirected, both were present and the cause was one `grep` away with no re-run.

**Adopted partly on first-hand evidence from the same session.** This session ran the
negative-control harness through `| tail -N`, hit `FAIL: 1 of 24 mutations were not
caught`, and could not tell *which* — so the four-minute harness was re-run twice more,
each time with a different filter, to recover output that had already been produced. That
is the brief's failure mode 1 in miniature, committed while adopting the rule against it.

**Scope kept narrow, as the brief asked.** Not "never use `tail`" — watching a log or
sampling a file is fine. The rule applies where output is **evidence for a claim**, and
the tell is whether recovering it would mean re-running the job.

**A fourth case, added by the reporter after the rule shipped (2026-08-21).** A `grep`
filter hid a guard that had *fired*: `tool compare … | grep -E "baseline|current|LOST|GAINED"`
discarded the line `!! GRAPH CHANGED: 245827 -> 245808 REACHING_DEF edges`, and the
conclusion forming from what survived was that the guard was inert — a defect report about
working code. This **generalises the rule** rather than adding an instance: the hazard is
not `tail`, it is that **a filter written before you know what the output contains is a
filter chosen to exclude the surprise**. `grep` is the more dangerous form precisely
because it reads as *selective* rather than *lossy*. Folded into `rules/01` §3 with a
second checklist item; the remedy is unchanged and now stated as the general one —
**redirect first, filter the file afterwards**.

**Measurement status:** adopted on reasoning, a verified reproduction, and first-hand
recurrence. **No efficacy lift is claimed or measured.**

### 2026-08-25 — TOON as the skill-file format: 1.9% on the best case

**The proposal.** Rewrite the library's instruction files from Markdown into
[TOON](https://github.com/toon-format/toon), a compact serialization format marketed on
token savings, to reduce what a task pays to load them.

**What the source actually says**, fetched at evaluation time rather than recalled. TOON is
"a compact, human-readable encoding of **the JSON data model** that minimizes tokens", and
JSON is its baseline throughout: **42.6% fewer tokens than JSON** on its mixed-structure
benchmark, **58.7% fewer than formatted JSON** on flat data — but **5.9% *more* than CSV**.
Its own "when not to use it" list is explicit: *"structures are deeply nested or
non-uniform"*, *"arrays are semi-uniform"*, *"data is purely tabular"* (CSV is smaller).
Nothing in the README addresses prose, because prose is not in the JSON data model.

**What the library is.** Across the 300 tracked instruction files (41 `SKILL.md` + 259
`rules/*.md`, 63,885 lines): **1,955 table rows — 3.1%**. Everything else is headings
(4,040), bullets and numbered imperatives (11,543), blank lines (10,032), fenced code, and
sentences. Only **two** files anywhere have more than 40 table rows.

**The measurement, on the best case available.** The router's routing table
(`skills/sota/SKILL.md`, 42 rows — tied with `sota-threat-modeling/rules/02` as the largest
table in the library) converted mechanically to TOON tabular form:

```
markdown  9,992 bytes
toon      9,802 bytes   →  1.9%
```

That is the **ceiling**, on 3.1% of the content — library-wide roughly **0.06%**. The
converter quoted every prose cell but did not escape embedded quotes; doing so correctly
only makes the TOON larger, so the error is in the favourable direction.

**Why 1.9% is a ceiling and not a starting point.** TOON's win over JSON *is* hoisting
repeated keys into one header row and dropping per-record punctuation. **A Markdown table
already does exactly that.** There is nothing left to reclaim — what remains in each cell is
English, and TOON's encoding of a sentence is the sentence, in quotes. The 42.6% headline
measures the distance from JSON to Markdown-grade density, which this library already has.

**The retrieval benchmark does not transfer.** TOON's accuracy figure (**72.2% vs JSON's
71.4%**, ±2.8, on 244 questions across 4 models) is *data retrieval* — "what is field X in
record Y". These files are **imperatives**, not records. Our own measured lift is a
**salience** lift (+0.38 completeness on `claude-sonnet-5`; the model knows the content and
drops it under context pressure — [docs/WHY-COMPLETENESS-RESIDUAL.md](WHY-COMPLETENESS-RESIDUAL.md)).
Salience comes from imperative prose carrying its reason and its exception — *do X because Y,
except when Z*. A row has no column for the *because* or the *except*, and those are the
parts that make a rule get applied. **This is reasoning, not a measurement** — see below.

**The cost side, which is not small.** A format change breaks invariant 2
(`## Audit checklist` as the last line), 8 (Markdown link resolution), 18 (every
`§` reference), 10 and 15 (rules-index parsing in both directions), and 4
(frontmatter) — plus negative-control probes built on hardcoded Markdown literals,
plus `ROUTER_BUILD_SHA`, which aborts the evals on router drift. The Agent Skills guidance the 500-line cap derives from is Markdown by
contract.

**And the binding constraint is not tokens.** It is the **500-line** cap on skill files and
the **1024-char** description cap — neither of which TOON moves, because it does not shorten
prose by lines. The lever the router already names is the real one: **load fewer files**,
because attention degrades with length and near-duplicate distractors (BUILD step 2).

**Where the shape genuinely does fit — and still is not a win.** Audit findings
(`file:line | rule | severity | effort | fix`) are a uniform record set, exactly TOON's
sweet spot. But that is emitted *output*, not skill files, and it is already pipe-delimited
— i.e. CSV, which TOON's own README says is smaller.

**Measurement status.** The 1.9% is **bytes, not tokens** — no tokenizer was available in
this environment, and the byte ratio is a proxy for a token claim. It is reported as such;
the direction is not in doubt at this magnitude, but the figure is not a token count. The
composition counts (3.1%, 63,885 lines, 300 files) are exact `grep -c` results over
`git ls-files`. **No efficacy comparison was run** — the verdict is that the token win does
not exist to justify the cost, *not* a measured finding that TOON degrades adherence. The
salience argument above is reasoning from an already-measured mechanism, and would need
`evals/run-completeness.py` to become a claim. **Revisit if** a tokenizer-based measurement
on a real load ever shows materially more than the byte ratio predicts.

### 2026-08-25 — a listing invitation, a scanner, and seven false positives

An external catalogue ([awesome-ai-plugins](https://github.com/hashgraph-online/awesome-ai-plugins),
120 stars, Apache-2.0, actively merging outside contributions) invited a listing. The
submission itself is one README line; the interesting part is what their CI did next.

**Their `plugin-scanner` ran against this repo and failed on `high:7`.** Rather than
argue for a waiver, the findings were **reproduced locally** at the same pinned version
and worked through one at a time. Seven of eight were false positives, and two of the
three patterns are upstream bugs that will hit other submissions:

- **`DANGEROUS_DYNAMIC_EXECUTION` ×3** — the rule fires on *eval* followed by a
  parenthesis, and matched **English prose in docstrings**: "the in-session eval (where
  …", "The completeness eval (run-completeness.py)". Verified absent by two independent
  greps: no `eval(`, and no `exec(`/`compile(`/`__import__(` anywhere — only
  `re.compile`. Any project shipping an *evaluation* harness will trip this.
- **`HARDCODED_SECRET` ×4** — the OpenAI `sk-` prefix matching inside ordinary words:
  *ri**sk-r**eduction* (four times) and *di**sk-m**anaged*. A word boundary before
  `sk-` clears them. The two content matches are intentional: a snippet teaching readers
  to give generated keys an identifiable prefix, and the deliberately-vulnerable
  `audit-hard.jsonl` fixture whose answer key literally includes `hardcoded-secret`.

**The one accurate finding was adopted.** `DEPENDABOT_MISSING` was right, and
`.github/dependabot.yml` now watches `github-actions` — the only third-party supply-chain
surface here, since the library is Markdown and every script is stdlib-only.

**The config was checked for inertness before being written**, because a Dependabot file
watching nothing is exactly the shape `sota-code-security` rules/10 warns about: the repo
pins `actions/checkout` at `9c091bb2…` = **v7.0.0**, while the latest release is
**v7.0.1** (2026-07-20). So there is real work waiting, and **the pin was deliberately
left un-bumped**: Dependabot's first PR is the evidence the automation actually runs.
Bumping it by hand would have removed the only cheap proof available.

**A local-vs-CI discrepancy worth recording.** The local run reported `high:8`, CI `high:7`.
The difference is a gitignored `.env` in the working copy — never committed on any branch
(`git log --all -- .env` is empty). A working-tree scan and a clone scan are not the same
measurement, and reconciling the two is what confirmed there was no leak.

**Measurement status:** no efficacy claim. The scanner analysis is a verified reading of
eight findings, and the two regex bugs were reported upstream rather than worked around.

**Outcome, recorded 2026-08-28 — both open loops closed, and one of them was a prediction.**
The listing PR (their #155) **merged 2026-08-26**: the library is now catalogued outside
this repo for the first time, which is the only concrete movement ROADMAP item 1 has had.
And the pin left un-bumped on purpose paid out — Dependabot opened **#281** on 2026-08-25
and it merged 2026-08-27, so every workflow now reads
`actions/checkout@3d3c42e5…  # v7.0.1`, which `gh api repos/actions/checkout/releases/latest`
confirms is the current release. The automation is proven to run *by having run*, not by
inspection of its config.

The lesson is in the delay, not the result. A deliberate experiment writes down its
prediction and then depends on somebody coming back to read it; both of these sat resolved
for a day or two while the note still read as pending, and the roadmap's open-items list
knew about neither. **An experiment with no scheduled read-back is indistinguishable from a
note.** When you leave something un-fixed as evidence, say where the result will be
recorded and who looks.

### 2026-08-26 — seven defects the library did not prevent

A session that *used* the library reported seven defects in code written while the
relevant skill was loaded. The brief's own framing is the useful part: **the check
verified a neighbouring property, not the property that broke.** A gate validating an
encoding while the defect is in the composition; a probe mutating a fixture the writer
never touches; a control whose predicate reads a setting adjacent to its real dependency.

**Reproduced before adopting**, because a brief's technical claims are claims:

```
$( ) stripping   -> "b: 2c: 3"                        composed record glued
chmod 700 --     -> "chmod: --: No such file or directory"   (BSD /bin/chmod)
mkdir -p --      -> succeeds on the same system        which is what disguises it
git rev-list -3  -> exit 129, count=0, "nothing to check", exit 0
```

**Finding 2 is the one that matters most, and it is ours.** `rules/02` §4 recommended
process substitution over a pipe — correctly, because a pipe loses variable updates — and
stopped there. It never said that the trade swaps a *visible* bug for an *invisible* one:
a process substitution's exit status is unreachable, `pipefail` does not apply, and a
failed producer yields zero lines, so the loop reports success over an empty set. That is
the vacuous-pass shape `rules/11` exists to find, arriving through a shell rule that
recommends it.

**Finding 5 is the highest-value class.** A control gated on `commit.gpgsign` — a proxy
that agreed with the real dependency (`user.signingkey`) for months — stopped producing a
signature at the exact moment that signature became the only per-change attestation, and
still logged success with a *stale* explanation. It is a **coupling** defect: the
control's own site never changed, so neither per-file review nor a per-gate probe can see
it.

**Finding 7 explains why the other six survived a green suite** — a probe licenses
confidence only over the path it actually traverses, and this one exercised the encoder
while the defects lived in the composition, the predicate and the write path.

**Two constraints the reporter could not know, and how they were handled.** The router is
at **500/500 lines** and invariant 1 fails at 501 — verified by adding a line and watching
`OVER 500 (501 lines)` fail the build — so both routing additions were paid for by
compressing existing text rather than appended. And editing router BUILD step 4 tripped
`ROUTER_BUILD_SHA`: the completeness eval's hand-compressed mirror **aborted**, as
designed. The mirror was re-synced with the new clause and the hash updated —
re-hashing alone would have been the exact drift the guard exists to prevent.

**Consequence to carry forward:** the completeness treatment arm now contains one extra
clause, so the next run is **not strictly comparable** to the +0.38 measured on
2026-08-21. Stated here rather than discovered later.

**Measurement status:** adopted on reasoning plus three verified reproductions. **No
efficacy lift is claimed** — nothing here has been measured against an eval.
