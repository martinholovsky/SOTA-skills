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
  correction`**. **A deferral carries a machine-readable marker so its status is checkable:
  write `**DEFERRED —` followed by the revisit condition on the same line, and when it
  resolves change that marker in place rather than recording the outcome only in a later
  entry.** Invariant 27 asserts every `**DEFERRED —` marker names a trigger, and that
  nothing else in the repo calls an item deferred that this log no longer marks. Added
  2026-09-09 after the roadmap said *"the deferred row"*, singular, while three existed and
  one had been resolved the day before in a different entry — the same restated-status drift
  invariant 26 exists for. Every entry ends in one of these — nothing stays `open` here; if it
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
- **Two independent sources before a principle goes cross-cutting.** An idea that
  earns a place in one domain skill needs only to be right there. Promoting it to
  a *cross-cutting* home — an operating principle in the router, a clause in
  `sota/rules/*`, an addition to the universal non-negotiables — costs every task
  in the library some attention, and that cost is paid whether or not the task is
  the one the idea was about. So the bar is evidence from **two independent
  sources**: two skills where the same principle recurs, or one external source
  plus a defect of ours it explains. One source, however well argued, lands in the
  narrowest home that fits and waits for the second. (Adopted 2026-08-31 from
  ECC's `rules-distill`, which applies the same 2+ bar to promoting a principle
  out of a skill into a rule file.)

## Log

> **Pointer translation, 2026-08-20.** `sota-code-security` `rules/10` and `rules/11`
> were split. Landed-in pointers in older rows are **left as written** — they record
> where an idea landed *at that release*, and rewriting them would falsify the history
> this log exists to keep. Translate with this map:
>
> | old | new |
> |---|---|
> | `rules/16` §2.10 | `rules/14` §1 (unearned claims in reporting output) |
> | `rules/16` §2.11 | `rules/14` §2 (shipped-artifact gaps) |
> | `rules/16` §2.12 | `rules/14` §3 (instruction standing in for a control) |
> | `rules/16` §2.13 | `rules/14` §4 (a control that never executes) |
> | `rules/16` §2.14 | `rules/14` §5 (parked in observe-only mode) |
> | `rules/11` §3.1–3.5 | `rules/13` §1–§5 (context-dependent silence) |
> | `rules/12` §2, §2.1–2.4 | `rules/15` §2… (instruments) — 2026-09-06 |
> | `rules/12` §3 | `rules/15` §3 (the guard that is an instance of what it guards) |
> | `sota-devsecops` `rules/05` §5.6 | `sota-devsecops` `rules/09` §1–§5 (gates that hold) |
> | `sota-devsecops` `rules/03` §3.9, §3.9.1–3.9.7 | `sota-devsecops` `rules/10` (the file), §1–§7 — 2026-09-07 |
> | `rules/02` §2, §3 (sessions, JWT) | `rules/17` §2, §3 (numbers kept) — 2026-09-25 |
> | `rules/04` §8 (tamper-evident logs) | `rules/18` §1 — 2026-09-25 |
> | `sota-jvm` `rules/04` §3 (XML and XXE) | `sota-jvm` `rules/07` §1 — 2026-09-25 |
> | `sota-golang` `rules/05` §8 (supply chain) | `sota-golang` `rules/08` §1 — 2026-09-25 |
> | `sota-rust` `rules/05` §9 (external programs) | `sota-rust` `rules/08` §1 — 2026-09-25 |
> | `sota-python` `rules/05` §9, §10 (supply chain, static analysis) | `sota-python` `rules/08` §1, §2 — 2026-09-25 |
> | `sota-javascript-typescript` `rules/05` §"Command injection via child_process", §"SSRF and server-side validation" | `sota-javascript-typescript` `rules/08`, same section names — 2026-09-25 |
>
> Invariant 18 keeps *live* `§` references honest, but its scope is `skills/*/*.md`,
> `skills/*/rules/*.md`, `evals/*.py`, `evals/README.md`, `scripts/*.sh` and
> `scripts/lib/*.py` (widened 2026-09-04; this sentence said "`skills/` only" until
> 2026-09-07, which was the check's *original* scope, not its current one). It still does
> not read `docs/`, `evals/cases/*.jsonl`, `README.md` or `CHANGELOG.md` — which is why
> this note exists rather than a gate.


| Date | Source | Idea | Verdict | Landed in |
|------|--------|------|---------|-----------|
| 2026-09-13 | This repository's own session of 2026-09-12, measuring itself | **A saturated measure is a fact about the instrument, not the system** — both arms at the ceiling means the eval cannot discriminate, which is a different claim from "the capability is solved" | **adopted** | `sota-llm-engineering/rules/01` §8a + its checklist. Self-intake, and it cost us something to learn: this library closed its audit-accuracy axis at +0.00 across **nine** instruments whose precision measure read **1.00 in both arms**, and wrote *"do not build a tenth — recall and precision are both exhausted"* into three documents. A tenth, built on an **externally annotated** benchmark, put both arms **near chance**. The lift replicated; *exhausted* was wrong for four months, and the instruction not to measure again is what made it self-sealing. Rule confirmed absent first with two vocabulary sweeps and a positive control — `saturat*` appeared nowhere in the skill that owns eval design |
| 2026-09-12 | [alibaba/open-code-review](https://github.com/alibaba/open-code-review) (Apache-2.0) | **Position drift** — a review comment that is right about the defect and wrong about where it is; reported from two years of production review as one of three dominant failure modes of language-driven review | **adopted** | `sota/rules/01` §4b. Confirmed absent first with two independent vocabulary sweeps and a positive control: `rules/03` §2 already *required* the location be "exact, clickable, reproducible" and nothing anywhere *checked* it — the library's most common gap shape, a stated rule with no probe. Strong internal corroboration: **invariant 18** exists because ~1,300 prose `§` references in this repo drifted silently, and 20 more were caught during one rules-file split. Placed **before** `rules/03` §4 on a cost argument: the check is mechanical and takes seconds, refutation is expensive, and a finding that cannot be located does not deserve a refuter |
| 2026-09-12 | [alibaba/open-code-review](https://github.com/alibaba/open-code-review) (Apache-2.0) | **Deterministic partitioning of a large changeset** — enumerate units mechanically, bundle files that must be judged together, give each bundle isolated context, report the denominator | **adopted** | `sota/rules/01` §1a. We covered only the *authoring* half (`sota-docs-workflow` rules/03: keep PRs small); the reviewer's half — what to do when the large PR exists anyway — was missing, the same audit-half-of-a-build-rule shape. Matches this library's own measured **completeness residual**. The rule's sharp edge is ours, not theirs: **partitioning is not sampling**, because "is this change safe to merge" has no defensible sample |
| 2026-09-12 | [alibaba/open-code-review](https://github.com/alibaba/open-code-review) (Apache-2.0) → [AACR-Bench](https://huggingface.co/datasets/Alibaba-Aone/aacr-bench) (Apache-2.0) | **An external, non-saturating precision instrument** — 2,145 expert-labelled review comments over 200 PRs / 50 repos / 10 languages, 1,505 correct and 640 incorrect | **adopted** | `evals/run-comment-triage.py` + `evals/cases/comment-triage.jsonl`. Our audit-precision instruments **saturate** (30 claims, 1.00 in both arms), so the axis was closed for want of a measure that could discriminate, not because precision was proven. **Validating the claim corrected it**: the repo README presents this as "1,505 annotated ground-truth issues" implying defect *detection*; the dataset's own card says it is a comment-*triage* set for intercepting low-quality comments. Different instrument, and the one we actually needed |
| 2026-09-12 | [alibaba/open-code-review](https://github.com/alibaba/open-code-review) (Apache-2.0) | **Deterministic path-scoped rule matching** (`.opencodereview/rule.json` binds a rule to a path glob) as more stable than language-driven rule selection | **adopted in principle, not in mechanism** | Not implementable here: Claude Code's skill activation *is* description-based and the platform owns that layer, so we cannot bind rules to paths. But their critique is **independently confirmed by our own measurement the same day** — a single token ("gate") moved an unrelated case 3/3 to the wrong skill ([ROUTING-FIX-DEVSECOPS](../evals/results/2026-09-12/ROUTING-FIX-DEVSECOPS.md)). Recorded so the position is not re-litigated: where a rule *can* be bound deterministically to a path, prefer that over a classifier |
| 2026-09-12 | [alibaba/open-code-review](https://github.com/alibaba/open-code-review) (Apache-2.0) | **A "reflection module" that intercepts low-quality review comments** before they reach the author | **rejected: already covered** | `sota/rules/03` §4 (adversarial verification) is exactly this, including the harder instruction their design implies — *default the verdict to REFUTED when the evidence is ambiguous* (`rules/03`:258-310). The novelty is not the idea but the **instrument**, taken separately in the AACR-Bench row above. Their benchmark figures (higher precision than a general agent, ~1/9 the tokens) are **vendor self-reported and not reproduced here** |
| 2026-07-24 | [training-knowledge-vault](https://github.com/Eolas-bith/training-knowledge-vault) `vault-doctor.py` | Resolve internal Markdown links in CI so a move/rename can't leave dead links | **adopted** | `scripts/check-invariants.sh` invariant 8 · v1.19.1 |
| 2026-07-24 | training-knowledge-vault lesson L-022 | A prompt that references a schema in an unloaded file silently fabricates it — inline what the model must obey | **adopted** | `sota-llm-engineering/rules/02` §1 · v1.19.1 |
| 2026-07-24 | training-knowledge-vault lesson L-023 | "Do not surface" instructions over in-context data are not a control (attention leakage); segregate structurally | **adopted** | `sota-code-security/rules/16` §2.12 · v1.19.1 |
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
| 2026-07-28 | Same runs — a review workflow with 5/5 *skipped* runs | A control whose trigger never fires: all-skipped is not all-green | **adopted** | `sota-code-security/rules/16` §2.13 · v1.19.5 |
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
| 2026-08-01 | Same handover | A vendor control-plane API reporting `confidentialCompute: true` over an instance whose CC status is OFF | **rejected: already covered** | — (`rules/16` §2.2 line 102 "check the shipped artifact, not the checkout" + §2.11 shipped-artifact gaps) |
| 2026-08-04 | An inert-control audit prompt (classes 6–12), handed over as a spec | **Unearned claims in output are words as well as numbers** — `verified`/`reachable from`/`tainted`, severity or confidence from a constant; match the claim's *shape*, and read the sentence before counting it | **adopted** | `rules/16` §2.10 · v1.21.1 |
| 2026-08-04 | Same prompt (class 8) | **The guard is an instance of what it guards** — a coverage test whose *scope* is narrower than the population and whose *predicate* the defect satisfies (`"auth=" in line` accepts `auth=None`); a tripwire nested in another gate's success branch; a denominator counting only survivors | **adopted** | `rules/11` §7.1 · v1.21.1 |
| 2026-08-04 | Same prompt (class 11) | **Contract drift by interaction** — a producer/consumer seam *no schema declares*, where the trigger is a config-level backend/frontend swap and both sides' isolation tests pass | **adopted** | `rules/11` §3.4 · v1.21.1 |
| 2026-08-04 | Same prompt (class 12) | Sample and read before you count; a control validated on inputs that **cannot** produce the failure proves nothing; when a wrapper reports an empty reason, go one layer down | **adopted** | `rules/11` §7.2 · v1.21.1 |
| 2026-08-04 | Same prompt (class 9) | The *detection* half of test-environment leakage: **block egress and re-run**; the config object the SUT never reads; assertions that contradict the test's own name | **adopted** | `sota-testing/rules/02` §2.6 + checklist · v1.21.1 |
| 2026-08-04 | Same prompt (class 7) | Run every script CI, a hook or a runbook references **before** reading any of them; record which produce output | **adopted** | `rules/11` §6 · v1.21.1 |
| 2026-08-04 | Standard test-smells catalog ([testsmells.org](https://testsmells.org/pages/testsmells.html), after van Deursen et al.) | **Resource optimism** as its own smell, and *mystery guest* in its original external-resource sense — ours had narrowed the standard name to a readability defect | **adopted** | `sota-testing/rules/02` §2.7 · v1.21.1 |
| 2026-08-04 | [GitHub Docs — Status checks](https://docs.github.com/en/pull-requests/reference/status-checks) | A **skipped job reports *Success*** and does not block a PR "even if it is a required check" — worse than §2.13's "all-skipped is not all-green" | **adopted** | `rules/16` §2.13 · v1.21.1 |
| 2026-08-04 | Verified locally this session | `go test ./...` over a package with no test files exits **0** — the empty-denominator rule instantiated in the toolchain | **adopted** | `rules/11` §2.2 · v1.21.1 |
| 2026-08-04 | Cross-skill sweep prompted by the same prompt | **A control parked in observe-only mode** (Kyverno `Audit`, PSA `warn`, WAF detection-only, `SCMP_ACT_LOG`, CSP report-only, DMARC `p=none`, `--soft-fail`) is inert as a *destination*; the staged rollouts existed, the inert-control framing did not | **adopted** | `rules/16` §2.14 · v1.21.1 |
| 2026-08-04 | Same prompt (classes 7, 10, 12 — the covered remainder) | Dead instruments; record rot; the auditor's instrument as a control; negative-claim burden | **rejected: already covered** | — (`rules/16` §2.2/§2.13, `rules/11` §7.1–7.3; `rules/16` §2.9, `rules/11` §5 "comments are a hypothesis", `sota/rules/01` §6 decision ledger) |
| 2026-08-04 | Same prompt — candidates checked and found already ours | Alerting-pipeline dead-man's switch; admission `failurePolicy: Ignore`; `continue-on-error`/soft-fail gate steps; suppression-baseline rot; coverage-target gaming | **rejected: already ours** | — (`sota-observability` rules/04 + rules/02, `sota-kubernetes` rules/05, `sota-devsecops` rules/05, `sota-testing` rules/07 §7.2) |
| 2026-08-05 | Two commissioned research reports on inert controls ("Missing SOTA Audit Controls" = **A**; "The Inert-Control Class" = **B**) | **Per-target kill verification** — a guard protects a population; watching it reject one member says nothing about the other 19 (the 2-of-20 tripwire). 100% kill rate for a security gate | **adopted** | `sota-code-security/rules/12` §3 · v1.21.1 |
| 2026-08-05 | Report B (Q3, instance 1) | **Metamorphic relation as a liveness oracle for a tool** — when you cannot state the correct output, state how it must *change*; the only diagnostic that catches an analyser emitting an empty-but-well-formed artifact | **adopted** | `sota-code-security/rules/11` §2.6 · v1.21.1 |
| 2026-08-05 | Report B (Q5), verified against primary sources | **The standards gap**: SSDF PW.8.2/PO.3.3 and CRA Annex VII require a record that the scan *ran*; Scorecard's SAST check detects tool *presence* only; **none require evidence a gate can fail** | **adopted** | `sota-devsecops/rules/05` §5.6 · v1.21.1 |
| 2026-08-05 | Both reports (Q1/Q2) | The cross-discipline lineage the library used unnamed: **proof test** (IEC 61508 dangerous-undetected), **positive control** (assay validity), **BITE** (aviation), **poka-yoke**, **vacuous satisfaction** (Ball & Kupferman), **the test oracle problem** (Barr et al., IEEE TSE 41(5), 2015) | **adopted** | `rules/12` intro + §3, `rules/11` §2.6 · v1.21.1 |
| 2026-08-05 | Report A only — the one thing B missed | **EvoMap** (arXiv:2605.25815, 1.5M assets / 128K agents): "over 84% of approved assets bypass quality checks using vacuous tests (e.g. `console.log()`)" — hard data that self-supplied evidence collapses at scale. B asserts no such corpus exists | **adopted** | `sota-code-security/rules/12` §2.4 · v1.21.1 |
| 2026-08-05 | Report A, Rule 3 | "Enforce a minimum **Mutation Score** threshold in CI" | **rejected: contrary** | — contradicts `sota-testing` rules/07 §7.2 ("never set a global percentage target — Goodhart's law is undefeated") and rules/06 §6.3 differential mutation (gate on *new survivors*, adopted 2026-07-24 from swarm-forge). B's per-gate kill rate is compatible and was adopted; A's global score is not |
| 2026-08-05 | Report B, R8 | **GSN / assurance-case notation** for critical controls | **rejected: non-fit** | — a notation, not a mechanism; its own cited critique (Leveson: arguments "assume the conclusion") points back at what we already run, `sota/rules/01` §7 adversarial refutation |
| 2026-08-05 | Report A, Rule 4 | Cryptographically **signed volumetric execution artifacts** verified by release gateways | **rejected: partial — insight kept, machinery dropped** | the insight (SLSA proves execution, never efficacy) landed in `sota-devsecops/rules/05` §5.6; the signing machinery is speculative and unbuilt |
| 2026-08-05 | Both reports — checked and found already ours | R2 execution evidence/volumetric assertions; R3 fail-closed gates; R6 assertion polarity + egress sandbox; R7 meta-monitoring/heartbeat; the **ML Test Score** rubric ("worth adopting wholesale") | **rejected: already ours** | — (`rules/11` §2.2/§2.4/§3.1, `rules/16` §2.1/§2.4/§2.6, `sota-testing/rules/02` §2.6–2.7, `sota-observability/rules/04:249`, and `sota-ml-engineering/rules/04:6` which has cited ML Test Score since before these reports) |
| 2026-08-11 | [spanchain](https://github.com/ghostfactory-art/spanchain) `docs/arch/hash-chain.md` | **A partitioned chain must chain its partitions** — segmenting a ledger (epochs, rotated files, daily partitions) with a per-segment `prev_hash = NULL` reset makes deletion of a whole *interior* segment verify clean; their pre-fix verifier also reset its carried hash at the boundary | **adopted** | `sota-code-security/rules/04` §8 + checklist · v1.22.4 |
| 2026-08-11 | Same source — where the bug actually lived | A verifier that walks a sequence in chunks and **resets its carried state at the seam**: predicate right, traversal right, blind to the removal of a whole chunk — a fourth form of "the guard that is an instance of what it guards", and a seam axis for per-target verification | **adopted** | `sota-code-security/rules/12` §3 + checklist · v1.22.4 |
| 2026-08-11 | Same source — `canonical_encode` and its stated cause | Canonicalization fails in **two** directions: the library stated only forgery. A default map/JSON encoder is not canonical, so identical data hashes differently and the ledger reports tamper on untouched records — an alarm wrong on ordinary traffic gets muted. Name the spec (RFC 8785) and pin it with a known-answer vector, or the "verify off the storing system" requirement is two implementations free to disagree | **adopted** | `sota-code-security/rules/04` §8 + checklist · v1.22.4 |
| 2026-08-11 | spanchain README, "Replay validates Span Chain's integrity, not your agent's behavior" | A record-and-replay (cassette) harness re-executes nothing: it tests pipeline determinism, and as a CI quality gate it stays green through a prompt rewrite, a model swap or a retrieval change | **adopted** | `sota-llm-engineering/rules/01` §5 + checklist · v1.22.4 |
| 2026-08-11 | spanchain — six findings checked against our tree first | Unkeyed chain forgeable by a DB-write attacker; tail truncation invisible; unhashed projection columns; canonical preimage required; in-memory ingest buffer loses records with no gap (integrity ≠ completeness); offline verification | **rejected: already ours** | — `sota-code-security/rules/04` §8, six for six, arrived at independently: `:217` unkeyed, `:224` tail truncation, `:241` unhashed projection columns, `:244` canonical preimage, `:265` integrity ≠ completeness, `:279` off-system verification |
| 2026-08-11 | spanchain — pre-GF-703 telemetry inside `Repo.transaction`; GF-827 conditional terminal write; append-only store holding personal data; EU AI Act Art. 12 | Post-commit notification, compare-and-set instead of check-then-write, erasure from immutable stores, AI Act record-keeping | **rejected: already covered** | — `sota-ruby/rules/05:82`, `sota-databases/rules/05:175`, `sota-architecture/rules/02:127`; `sota-async-concurrency/rules/02` §"Check-then-act / TOCTOU"; `sota-privacy-compliance/rules/03:125`; `sota-code-security/rules/04:214` |
| 2026-08-11 | spanchain — dead-letter drops deliberately break `verify_ledger` ("a deliberate audit signal") | An integrity verdict that is routinely red for operational reasons trains operators to ignore it; a known gap should be a signed in-chain marker, not a hole | **DEFERRED — revisit if a second implementation shows the same design — one project's trade-off is not yet a rule. **Evidence checked 2026-08-28: still 1 shipped instance** — see the trigger ledger under the 2026-08-11 section below; check that before re-deriving the search |
| 2026-08-13 | Internal coverage audit — business-logic defect class ([COVERAGE-BUSINESS-LOGIC-2026-08-13](COVERAGE-BUSINESS-LOGIC-2026-08-13.md)) | Route the class by its own name: "business logic", "checkout", "refund", "state machine" appeared in **zero** of 41 SKILL.md descriptions, and "workflow" only in the CI/SOC/docs senses — descriptions are the only auto-loaded classifier | **adopted** | `sota-code-security` description, 998→1014 of 1024 · v1.22.4 |
| 2026-08-13 | Same audit — first draft | Add a BUILD rule + probe for WSTG-BUSL-07 "defenses against application misuse" | **rejected: already covered** | — covered under three other names: `sota-api-design/rules/07:211` (API6 flow throttles, explicitly not generic rate limiting), `sota-code-security/rules/07-data-exposure.md:96-99`+`:230` (security events + alerting on anomalies), `rules/02-authentication.md:213` (escalating friction), `sota-mobile/rules/04:94-99` (non-human client decision table). Residual is naming, not coverage |
| 2026-08-13 | Same audit — first draft | Add payment-specific money hazards for WSTG-BUSL-10 (currency, rounding, negative amounts, insufficient funds) | **rejected: already covered** | — `js-ts/rules/02:183,191,244`, `sota-databases/rules/01:232`, `sota-api-design/rules/01:285,302-303`, `sota-code-security/rules/06:183-197,218,226`, `rules/03:82,91`, and currency specifically at `rules/01-input-injection.md:28` ("currency matches account") |
| 2026-08-16 | Field-use handoff from a live build (private repo, brief kept outside this repo) | The auditor's **own verification one-liners** are uninstrumented instruments: unlinted shell run against the system under test, producing false findings *about the product*. Three in one session, all zsh joining/pipeline bugs the library already documents but nothing routed to | **adopted** | `sota/SKILL.md` rule 17 + `sota-code-security/rules/12` §2 · v1.22.6 |
| 2026-08-16 | Same brief | `set -e` **cannot be re-armed** inside a suspended call tree, and `$-` still reports `e` — an unfalsifiable control inside bash itself | **adopted** | `sota-shell-scripting/rules/01` §2 + audit checklist · v1.22.6 |
| 2026-08-16 | Same brief | "never open an issue" for `SECURITY.md` has **no private-repo exception**: GitHub's private vulnerability reporting is public-repo only, so the rule pointed at a feature that cannot be enabled | **adopted** | `sota-docs-workflow/rules/01` §8 table + carve-out + checklist · v1.22.6 |
| 2026-08-16 | Same brief | **Location-dependent silence** — a filter whose predicate matches the ambient environment (absolute path, hostname, locale), so a collection is correct on one machine and empty on another | **adopted** | `sota-code-security/rules/11` §3.5 (+4 ripple sites) · v1.22.6 |
| 2026-08-16 | Same brief | A pipeline the platform **refused** (billing) reports *failure*, not skipped, so the all-skipped test misses it; and nothing said how to prove a pipeline runs | **adopted** | `rules/16` §2.13 third state + `sota-devsecops/rules/01` §1.11 · v1.22.6 |
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
| 2026-08-19 | Field brief from a session applying the library — a recon profile that came back empty | **A cap on a generator's *output*, then parsed.** `rules/16` §2.7 covers truncating input *into* an inspector; the inverse — an unset `max_tokens` truncating a JSON document that is then `json.loads`-ed — is the same family and the rule text, example and checklist all point at input | **adopted with a correction** | `sota-code-security/rules/16` §2.7 (the mirror + checklist), `rules/11` §2.2 (the tell: produced size landing on its cap; a parse-error offset needs the document length), `sota-llm-engineering/rules/02` (set `max_tokens` explicitly, assert `output_tokens < max_tokens`) + the three index surfaces that said "truncation before inspection". Correction: the brief reads the class as unstated, and it is stated — for LLM output only, at `sota-llm-engineering/rules/02:199` and `rules/04:251` ("truncated output never parsed as valid"), in a skill an inert-control pass never loads. What was genuinely absent is the **general** producer form, the **unset-default** variant (no truncation operator to grep for, so §2.7's own procedure walks past it), and the size-vs-cap arithmetic — `rules/05:147` alerts on a `stop_reason=max_tokens` spike, which is the metadata tell, not the arithmetic one · v1.22.14 |
| 2026-08-20 | Field brief from a session applying the library — three ideas | **A `--self-test` mutation harness as a mode of the tool**, so "this check can go red" is a property of the health suite rather than of whoever last edited it | **adopted with a correction** | `sota-code-security/rules/12` §1b + checklist, `sota-cli-ux/rules/03` §2a + checklist, two SKILL.md index rows. Correction: the *class* is covered three times over (rules/12 §1 mutation probe, §2.1 "the instrument that cannot fail" — which is literally a mutation harness reading every non-zero exit as a catch — and `sota-devsecops/rules/05`:311 "every gate ships a committed known-bad"). What was absent is the **packaging**: everywhere the library states it, the probe is a committed fixture plus a separate job, i.e. a convention someone must remember when adding a check. Nothing said to make it a mode of the tool, where a check with no declared known-bad *fails the self-test* · v1.23.0 |
| 2026-08-20 | Same brief, idea 3 | **Gateway access logs, still absent — which is why "is this graph feature used?" was answered by measuring the corpus instead** | **adopted with a correction** | `sota-observability/rules/05` §7a + checklist, cross-ref from `sota-api-design/rules/02` §5 step 4, observability SKILL.md row. Correction: the requirement is **already stated**, at `sota-api-design/rules/03`:227 ("without per-field usage data you can never delete anything") and `rules/02`:100 ("You cannot sunset what you can't attribute") — so the accurate verdict is *unreachable, not absent*: it lives in `sota-api-design`, which an observability or platform task never loads, and `sota-observability` mentions access logs exactly once (`rules/05`:56) and only to *exclude* the health endpoint from them. The genuinely new part is the **residual** the brief's incident actually produced — the substitute measurement. `grep -rniE "proxy (metric\|measure)\|answers a different question" skills/` returned zero hits · v1.23.0 |
| 2026-08-20 | Same brief, idea 2 (deferred, then answered the same day with a measured field report) | **The in-band sentinel — a value from the domain standing in for absent** | **adopted** | `sota-architecture/rules/02` §8a (**the class, stated once, language-neutral**), `sota-python/rules/02` §2a (worked example) + checklist greps, `sota-databases/rules/01` *Modeling hygiene* + checklist (persistence half), one-line pointer in `sota-python/rules/03` §12, two SKILL.md rows. Confirmed absent by two searches before writing (`sentinel` → 23 hits, all unrelated; `return -1|in-band|magic (number|value)` → nothing on the class); nearest prior coverage was `sota-c-cpp/rules/04`:25 (one banned-API row) and `sota-performance/rules/05`:170 (the principle, stated once and scoped to cached absence). **Filed to databases `rules/01` rather than the reporter's suggested `rules/02`**: how absence is encoded is a modeling decision, and `rules/02` is migrations. **Scope corrected on review**: the first cut filed the class inside `sota-python`, which would have hidden a language-neutral defect from nine other language readers — the per-language part is the *detector*, not the class. Now a §8a in architecture plus a **measured** row in each of Go, Rust, C/C++, JVM, JS/TS, .NET, PHP, Ruby, and a pointer from Swift. The reporter's measurement is what made it writable — see the entry · v1.23.0 |
| 2026-08-20 | Operator question — "if `sota-code-security` is close to full, can't you split it… maybe `-audit` and `-build`?" | **Split the files, not the skill — and gate `§` references first** | **adopted with a correction** | `scripts/check-invariants.sh` invariant **18** + `scripts/lib/check-section-refs.py` + harness probe 18 (24 probes), then `rules/13` (from `rules/11` §3) and `rules/14` (from `rules/16` §2.10–2.14): 497→357 and 496→362 lines. **Correction, with the measurement**: a skill split buys **no** headroom — invariant 1 enumerates per *file*, so the files arrive unchanged — and build/audit is the wrong axis here because invariant 2 welds an `## Audit checklist` onto all 259 rules files. The build-vs-audit framing is recorded as declined in `docs/ROADMAP.md` item 12, with the defensible seam (classes vs verification) and its router-line cost. The check went first **because the split is what creates the hazard**, and it found six live defects before a single line moved, then caught 27 the split itself broke · v1.23.0 |
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
| 2026-08-29 | The `/security-review` prompt itself, extracted from the CLI bundle **and** the live 2.1.251 binary (one line differs in 10.5k chars, so the extraction is current) | Its architecture, not its categories: find in one pass → **one filter sub-task per finding, in parallel** → drop anything scoring **< 8/10**. The filter sub-tasks run *restricted*: *"do not use the bash tool or write to any files"* | **adopted** | Its 5 category groups are a **subset** of the library (only `tabnabbing` and `XS-Leaks` have zero hits in `skills/`, and its own prompt says not to report those). The transfer is the **confidence gate + restricted refuter**, which `sota/rules/03` §4 lacks. Also recorded because two of its **17 hard exclusions and 12 precedents** contradict us on purpose and must not be adopted: *"including user-controlled content in AI system prompts is not a vulnerability"* (vs `sota-code-security` rules/08) and *"memory safety issues … are impossible in rust"* (vs `sota-rust` rules/03 `unsafe`). Its exclusion list is a **PR-noise policy, not a security taxonomy** · **Landed:** `sota/rules/03` §4a — the confidence gate and the restricted refuter · v1.30.1 |
| 2026-08-29 | [`anthropics/defending-code-reference-harness`](https://github.com/anthropics/defending-code-reference-harness) (Apache-2.0 — text reusable with attribution; per convention we take the **idea class** only) | The grader reproduces in *"a fresh container the find agent hasn't touched"*, and *"the only thing that crosses over from the find agent to the grader is the proof of concept it produced"* | **adopted** | Sharper than ours. `sota/rules/03` §4 already says *a separate agent, or … fresh context* — it never bounds **what crosses the boundary** to a single artifact, which is the part that stops the refuter inheriting the finder's reasoning · **Landed:** `sota/rules/03` §4a, *bound what crosses to a single artifact* · v1.30.1 |
| 2026-08-29 | Same harness | **N-of-N reproduction**: a find agent runs the ASAN binary *"until a given input produces a crash 3 out of 3 times"* | **adopted** | **Zero** coverage — no repeat-count rule anywhere in `skills/`. Uncomfortable beside ROADMAP 18, where this repo measured its own noise floor at ±0.03 and still never wrote the rule that a stochastic finding needs a repeat count · **Landed:** `sota/rules/03` §2 + a checklist item · v1.30.1 |
| 2026-08-29 | Same harness | **Partition before you fan out**: a recon agent proposes a partition *"so that parallel find agents explore different areas instead of converging on the same bug"* | **adopted** | Zero coverage (every `fan-out` hit in `skills/` is async concurrency). This is the mechanism behind ROADMAP 16's fan-out lesson stated from the other side: N unpartitioned agents do not give N chances, they give one chance N times · **Landed:** `sota-llm-engineering/rules/04` §7 + a checklist item — the addition is the *invisible* half: N agents reporting one finding reads as corroboration · v1.30.1 |
| 2026-08-29 | Same harness | **The multi-wave yield curve**: *"the number of findings will likely go down, but the complexity will likely also go up"* — plus recording prior findings in `known_bugs` to steer later runs | **adopted** | Zero coverage. The inference is the useful half and the README does not state it: a **flat count across waves means the waves were not independent**, which makes the curve a check on the harness rather than a report on the code · **Landed:** `sota/rules/01` §4 + a checklist item · v1.30.1 |
| 2026-08-29 | Same harness | **A patch must defeat a fresh finder**, not just the original PoC: the grader confirms the code builds, the PoC no longer crashes, the test suite passes, *and* *"a fresh find agent can't find a way around the fix"* | **adopted with a correction** | Partially covered: `sota/rules/01` §4's re-audit loop says *re-run the same tools at the new commit*. The fourth leg is variant analysis by construction, and it is the one that catches a fix which only closes the reported input · **Landed:** `sota/rules/01` §4, **folded into** the existing re-audit loop rather than added beside it — the loop was not missing, it was too weak · v1.30.1 |
| 2026-08-29 | Same harness — four ideas **considered and rejected** | Threat-model-scoped scanning; gVisor + API-only egress around the agent pipeline; ASAN builds for C/C++; proving the pipeline on a known-vulnerable reference target before trusting it | **rejected: already covered** | In order: router §AUDIT step 2 (*"Threat model first … its output prioritizes the rest"*) · `sota-sandboxing/rules/05` R2.1 + R4.1 · `sota-c-cpp/rules/02` · `sota-code-security/rules/12` §2.2 (*two references, both in CI*). The sandboxing row is worth more than a rejection: the harness is an **independent implementation of `sota-sandboxing` rules/05 §7**, shipped the same day — it ingests a repository it did not author, builds and executes it, and isolates exactly where §7 says to · — |
| 2026-08-29 | **Two audits of one third-party project, run side by side** — a full-repo audit using this library vs. Claude Code's diff-scoped `security-review` | **Falsify the quantifier in the security prose.** Both audits' strongest evidence was a sentence: *"containment is applied at every target walk"* (9 of 61), *"no function-calling, no shell, no subprocess — this RCE mechanism is NOT APPLICABLE"* (tools on by default; a shell command executed on the host in the reproduction), a docstring promising the container cannot read `.env` (nothing enforced it). All three had been **true when written** | **adopted** | `sota-code-security/rules/14` §7 + a checklist item, and an AUDIT-checklist item in `sota/rules/01`. Zero prior coverage: `rules/14` §1 owns numbers a **tool prints at runtime**, not sentences a human wrote. The pass is mechanical — grep for `every/all/never/no/only/cannot/not applicable`, rewrite each with a denominator, count. A wrong **NOT APPLICABLE** is the worst form: it cancels the next reader's own investigation, which is how one survives years of review · v1.30.0 |
| 2026-08-29 | Same pair — the **through-line** both audits reached independently | A control that is neither inert nor missing: it **works**, on part of the population it is credited with. `escapes_target` guarding the file *listing* and not the four channels twelve lines away that read file *bodies*; `disable_tools=True` at 2 call sites of 6; a path guard on 9 target walks of 61 | **adopted** | `sota-code-security/rules/14` §6. Closest prior art is `rules/12` §3 (*"verify per target, not once"*) — but that owns a **guard's** population and is found by injecting a defect per member; this owns a **mitigation's**, where the tests pass for the honest reason that they exercise the guarded member. Neither pass finds the other's version. The fix is a **census, not a search**: enumerate the protected *operation*, mark each site, report the ratio · v1.30.0 |
| 2026-08-29 | Same pair — the **mechanism** behind the row above | `disable_tools=False` as a default: when the safe value is opt-in, partial application is not a risk but a schedule — every new call site starts unguarded | **adopted** | `sota-code-security/rules/14` §6a. No prior coverage (`grep -i 'secure.by.default\|safe default'` over `sota-code-security` + `sota-sandboxing` returned nothing). Rule: a parameter selecting a trust boundary **defaults to the closed side**, keyword-only. The property worth preserving is not *"the default is safe"* but *"the count of privileged call sites is a `grep -c` away"* — which is what makes §6's census cheap enough to run · v1.30.0 |
| 2026-08-29 | The **diff-scoped** review's rating discipline | Refuse a severity until the chain's legs are named in code — reach, **primitive**, boundary crossing, channel. It downgraded its own candidate on three independent legs (no Swift toolchain in the image; `go build ./...` runs no generator/test/`main`; staging lands in a `0700` dir the operator already owns) | **adopted** | `sota/rules/03` §1 hard rule 3, plus a **chain-closure** fourth lens in §4's refutation pass. `rules/01` §7's *reachability* lens asked only whether input arrives, never what then executes or what boundary the effect crosses. The higher-yield half is the inverse: when every leg coexists in one path, that is what the report leads with · v1.30.0 |
| 2026-08-29 | Same review — *"filing a High here would be filing a High against the fix"* | On a diff, rate against the code the change **replaced**, not against perfect: the pre-change path ran the same build unsandboxed on the host, as the operator | **adopted** | `sota/rules/03` §1 hard rule 4. Absent from the severity model, and the failure mode is not theoretical — rating a hardening PR as a regression teaches authors that hardening attracts findings, which is how the next mitigation does not get written. Guarded against over-application: the residual gap is still reported at its own severity, against the *codebase* rather than the diff · v1.30.0 |
| 2026-08-29 | Same review — how it found the only finding it shipped | A **refuted finding is a template**: it hands you the pattern *and* the leg that was missing. Sweeping the pattern outward found the same staging in an unchanged module where the analysis step compiles the target and runs its build scripts with no network isolation — three legs at once | **adopted** | `sota/rules/03` §4 step 5. §7 previously said survivors ship and the rest are dropped **with the refutation recorded** — and stopped there. Direct evidence for the gap: the full-repo audit, with strictly more scope, **missed** the module the diff-scoped review found by sweeping · v1.30.0 |
| 2026-08-29 | Both audits — the surface neither library section owned | A tool that ingests **repositories it did not author** (scanner, SAST wrapper, review bot, agentic analyser) runs on a maintainer's machine with that identity's credentials, and the target is the attacker | **adopted** | `sota-sandboxing/rules/05` §7 + routing rule 13. A genuine **routing gap**: `rules/05` owned *model output*, `sota-code-security/rules/09` owned *parsers*, `sota-devsecops/rules/03` owned *your own dependencies* — nothing owned this composition. Four legs, typically owned by four people: link-dereferencing staging, "static" analysis that evaluates target-controlled build metadata, an LLM step spawned tools-live with the parent's `cwd`, egress on by default. Written as *verify for your exact command and flags*, not as a per-tool verdict table — this repo has been burned by unmeasured cross-language rows · v1.30.0 |
| 2026-08-29 | Same pair — six moves **considered and rejected** | Refutation-before-reporting; the reachability and severity-inflation lenses; an evidenced "verified clean" section; inert/vacuous controls; archive symlink entries; the agent lethal trifecta | **rejected: already covered** | In order: `sota/rules/03` §4 (both audits produced a refuted-findings section *because of* it) · §4's lens list · §5.6 positive observations · `sota-code-security/rules/10`+`/11`+`/12` §3 · `rules/09` §2 and `rules/01`:100-107 · `sota-sandboxing/rules/05` R1.2. Recorded so they are not re-litigated · — |
| 2026-08-29 | Same pair — a caveat on the comparison itself | | **noted, not a finding** | The two runs are **not comparable instruments** and the log should not be read as a scoreboard: one was full-repo (27 findings, reproductions re-run), the other diff-scoped (one candidate, refuted). "Fewer findings" is a property of scope, not of quality. What transferred was the *reasoning moves*, which is the only axis on which they can be compared · — |
| 2026-08-27 | Same session — two lessons **considered and NOT added**, recorded so they are not re-litigated | (a) a local harness that mutates a worktree **at HEAD** can pass while CI fails on your working tree; (b) a limit you keep paying deserves one measurement before you pay it again | **rejected: repo-specific / too meta for a rules file** | (a) is a property of *this* harness's design, not a general practice — it is recorded in `evals/README.md` and the memory instead. (b) is engineering judgement rather than a checkable rule; it drove ROADMAP item 4 and the router refactor, and a rules file cannot probe "did you measure the constraint?". Both remain true and useful; neither earns skill text · — |
| 2026-08-26 | **Field brief from a session applying the library** — seven defects it did not prevent, one session building a gate-ledger script (Rust + bash) | Six gaps in `sota-shell-scripting` / `sota-code-security`, plus two routing changes. **Finding 2: a rule in this library, followed literally, produces a vacuous pass** | **all seven adopted, one narrowed, one correction added** | Three falsifiable claims **reproduced on this machine before adopting**: `$( )` newline stripping glues composed records; BSD `chmod 700 -- dir` fails with *"No such file or directory"* while `mkdir -p --` succeeds alongside it; and `git rev-list -3` exits **129** into a process substitution, yielding `count=0` and a "nothing to check" exit 0. Landed: `sota-shell-scripting/rules/01` §2 (newline stripping) and `rules/02` §4/§5/§9 (proc-sub status, `--` portability, unordered selection, keyed-store upsert); `sota-code-security/rules/14` §4a (proxy predicate) and `rules/12` §2.1 *(now `rules/15` §2.1 — split out 2026-09-06)* (probe scope, now **five** failure modes). Every one shipped with its audit-checklist half in the same change · v1.28.0 |
| 2026-08-26 | Same brief — finding 3 (`--` is not portable) | Claimed as an unqualified gap | **adopted with a correction** | The hedge already existed — `sota-golang/rules/05`:91 says *"Use `--` end-of-options **where the tool supports it**"*. So the verdict is **UNREACHABLE, not absent**: correct guidance sitting in a skill a shell task never loads. Landed in `sota-shell-scripting/rules/02` §5 with the macOS reproduction and a pointer to the sibling · v1.28.0 |
| 2026-08-26 | Same brief — **a correction the brief did not make** | Its remedy for finding 2 uses `out="$(cmd)"`, which is command substitution — and therefore **re-introduces finding 1** | **adopted with an addition** | The remedy survives only because `<<<` puts a trailing newline back, and it buffers the whole producer output in memory. Both caveats are now stated beside the GOOD example, so applying fix 2 cannot silently reintroduce bug 1. Found by reading the two findings against each other rather than in sequence · v1.28.0 |
| 2026-08-25 | [awesome-ai-plugins](https://github.com/hashgraph-online/awesome-ai-plugins) listing invitation, and the `plugin-scanner` run it triggered on this repo | Their scanner reported **8 findings on SOTA-skills**: 7 high + 1 low | **one adopted, seven rejected as false positives** | Reproduced locally with `plugin-scanner==2.0.1116` and checked every one rather than assuming. **Adopted: `DEPENDABOT_MISSING` (low) was correct** — `.github/dependabot.yml` added, scoped to `github-actions` (the only third-party surface: `actions/checkout`, SHA-pinned in 5 places). **Rejected: all 7 highs.** 3× `DANGEROUS_DYNAMIC_EXECUTION` match the word *eval* before a parenthesis in **docstring prose** (`grep -rn 'eval(' evals/*.py` → no matches; only `re.compile`); 4× `HARDCODED_SECRET` are the OpenAI `sk-` prefix inside ordinary English — *ri**sk-r**eduction*, *di**sk-m**anaged* — plus a snippet that *generates* a prefixed token and the deliberately-vulnerable audit fixture. Both regex bugs reported upstream on the PR · **listing PR merged 2026-08-26**; the deliberately un-bumped pin drew Dependabot **#281** (merged 2026-08-27, now `v7.0.1` = latest), proving the automation runs · v1.27.0 |
| 2026-08-25 | Same scanner run — the *class* behind its false positives | A pattern-based control's false-positive rate is a property you must measure on your own corpus before trusting its verdict | **rejected: already covered** | `sota-detection-engineering/rules/04` §1 (*"Alert fatigue is the dominant failure"*, *"Precision over recall at the alert tier"*) and §2 (*"Tune by adding context, not by deleting detections"*) already own this class. The scanner episode is an **instance**, not a new class — recorded so it is not re-litigated as a gap · — |
| 2026-08-25 | **This session's own eval work** (ROADMAP item 21) | Building an eval set out of the cases a model got wrong measures the selection, not the system | **adopted** | `sota-llm-engineering/rules/01` §8 + an audit checklist item. Distinct from the **contamination** bullet already there: that tunes the *prompt* against the set, this builds the *set* from outcomes. Found by nearly doing it — 10 of the old 32 freshness cases still discriminated and reporting those alone would have produced a large number measuring nothing · v1.27.0 |
| 2026-09-02 | **Field brief** — a Python service calling LLMs for structured verdicts (proposal 1) | `.get(k, default)` on a dict you did not construct is the silencing mechanism: four defects where the consumer named one key and the producer (a *model*) emitted a synonym, each running for weeks as a plausible constant. `rules/13` §4 described the seam but as **layout** drift with a deterministic producer | **adopted** | `sota-code-security/rules/13` §4a + checklist. The novel half is that no static check closes a seam whose producer samples field names from a distribution — the sound detector is a **runtime unconsumed-key diff**. Reporter's framing that a defaulted read is *always* wrong was narrowed: `sota-api-design` rules/02 §3 (tolerant reader) still holds, the addition is that it ignore **audibly** · v1.31.2 |
| 2026-09-02 | Same brief — whole-document rejection over one bad field | A schema that rejects a document over one enum synonym is a **recall** control; rejection yields an absent document, not a better one | **adopted with a correction** | `sota-llm-engineering/rules/02` §6 — amending the bullet **of ours that caused it** (*"reject into an explicit error path"*). The reporter's rule as written would have licensed laundering attacker input, so it carries the boundary it lacked: salvage-and-record for a model you invoked, still **reject** at a trust boundary (`sota-code-security` rules/09 §4) · v1.31.2 |
| 2026-09-02 | Same brief (proposal 2) — test output and production telemetry sharing one sink | 215 of 226 log files were test fixtures; the dangerous case is not the false positive but the **destroyed true finding**, which argues more persuasively because the contaminated aggregate carries the larger n | **adopted** | `sota-code-security/rules/11` §2.7 (audit half) + `sota-observability/rules/05` §8a (build half). Reporter's *"n jumping by an order of magnitude is contamination, not power"* was narrowed to an **unexplained** jump — widening one shard to all shards legitimately multiplies n · v1.31.2 |
| 2026-09-02 | **This repo's own eval harness**, checked because the brief above predicted the shape | `evals/results/durations.tsv` was that shared sink: **46 of 60 rows sub-10s aborts (77%)**, 3 of 14 real runs compared against one, and `rules/11` §2.1 — the diagnostic the ledger exists to implement — inert for the most-run runner. Cause: `run-build-safe.py` called `note_work()` *before* its `--selftest` branch | **adopted** | Fixed before the rule was written, so §2.7 ships with two independent instances rather than one report: `note_complete()`, an `ok`/`partial` ledger column, `_previous()` returning only completed rows, printed lines stating their own exclusion filter, and a `smoke-runners.py` gate (watched to fail). Also `run-router-length.py` no longer overwrites a past-dated result file · v1.31.2 |

| 2026-09-03 | **Field brief** — `sota-skills-lessons-2026-09-03-zsh-nomatch.md`, from a first-party documentation-staleness sweep that read as clean | zsh's `NOMATCH` (on by default) makes an **unquoted glob in a flag value** (`grep --include=*.md`) abort the command, where bash passes the word through literally — and with the customary `2>/dev/null` the broken probe is **byte-identical to a genuine no-match** (empty stdout, exit 1), so an audit sweep cannot tell "the tree is clean" from "my search never ran" | **adopted** | `sota-shell-scripting/rules/01` **§3a** + checklist item, plus a cross-ref from `sota-code-security/rules/12` §2 (a quoting bug is a fourth reason a probe never fires, and the only one with no usage error). Placed as `3a` rather than renumbering: **49** `§` references point into rules/01 and four external files cite `§3` by name, including the router. **All four measured commands reproduced** (zsh 5.9 / bash 5.3.15 / Darwin 25.6.0), and both side-claims verified — all 11 `scripts/*.sh` carry a bash shebang (so the brief's refusal to propose a shellcheck rule is right: it could not fire), and `skills/` contains **0** unquoted globs in flag values (the practice was already modelled, only the rule was missing). **Went beyond the brief:** whether the rest of the command list survives depends on the callee — an external command continues, a **builtin** aborts the whole list — so the exit status may never reach you either · v1.32.0 |

| 2026-09-03 | **Field brief** — `sota-skills-lessons-2026-08-16b-poller-tristate.md`, revisited (a standing debt flagged by the 2026-09-03 brief) | A watcher needs **four** states, not three: `GONE` — the target no longer exists — is **terminal and knowable**, not unknown. Collapsing it into UNKNOWN trades a false success for a false alarm and the watch never ends | **adopted** | `sota-code-security/rules/12` §2.2a + checklist. **The "still not applied" label was too strong and is corrected here**: §2.2a already carried the brief's substance (fail-open vs fail-closed-by-aborting, DONE/NOT-DONE/UNKNOWN, assert-positively, the independent cross-check). Only the fourth row was missing — the 2026-09-03 brief's `grep GONE` was the right probe and found exactly the real gap. Kept tight: `rules/12` is at **494/500** and now the library's tightest file · v1.32.1 |
| 2026-09-03 | **This session's own near-miss** (PR #308) | An eval whose treated arm never reads the changed file returns `+0.00`, and that null is **structural, not a result** — indistinguishable from a real one | **adopted** | `sota-llm-engineering/rules/01` §8 + checklist. `run-desc-routing.py` was proposed to measure a **router-body** change; it builds its catalogue from frontmatter `description`s and never loads the body. Caught by reading the runner before spending, not by the number looking wrong after. Distinct from the convention already in `evals/README.md` — *an arm that cannot see the treatment is a free negative control* — which is the same fact used **deliberately**; the difference is entirely whether you chose it · v1.32.1 |

| 2026-09-04 | **This session's own release work** | Nothing checked that a CHANGELOG version ever got a **git tag**. Invariant 5 checks a tag is never *ahead* of VERSION; the other direction was unguarded | **adopted** | **Invariant 21** + probe. It had already failed **twice** — v1.30.0 (2026-08-29) and v1.31.2 (2026-09-02) each had a CHANGELOG section, a VERSION bump and a merge, with no tag and no release; both found by enumerating the CHANGELOG against `git tag`, not by any gate. All three CONVENTIONS-LEDGER filters passed. The top entry is exempt (tagged after the merge, RELEASING §4), and the check **skips with a note** on a tagless shallow checkout rather than failing every version at once · v1.32.2 |
| 2026-09-04 | Same session — invariant 18's scope | `§` references in `evals/` and `scripts/` were never scanned; **27 of them live there and one had already rotted** (`check-invariants.sh` cited `rules/16 §2.12` for the argument that a convention must become a gate — that content had moved to `rules/14` §3) | **adopted** | Widened `check-section-refs.py` to the **live tooling** (runners, scripts, `evals/README.md`), not `evals/results/**` — those are superseded-not-edited history. **Two corrections while widening**: a git pathspec matches across `/`, so `evals/*.md` dragged in every dated write-up (fixed with `:(glob)`); and outside `skills/` there is no containing skill, so a bare `rules/NN §X` is **skipped rather than guessed** — fail open, because a gate that false-positives on correct prose gets disabled · v1.32.2 |
| 2026-09-04 | What the widened gate found on its first run | `run-adjudication.py` had been **dead since 2026-08-29**: its ablation target moved to `sota/rules/03` in the v1.30.0 split while the runner still read `rules/01`, so its guard aborted every ablated run | **adopted (defect fixed)** | The guard behaved perfectly — it refused rather than returning an unablated corpus and reporting a fake +0.00. What failed is that **nobody could see it**: `smoke-runners.py` renders every `SystemExit` as `ok (guard fired or usage printed)`, which cannot distinguish "needs args" from "fires always". The runner now reads both files (ablation verified live: 6,649 chars removed, title gone), and the smoke harness **prints the exit message** so a permanent guard is legible · v1.32.2 |


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
   `sota-code-security/rules/16` §2.12)*. Their L-023: "do not surface" over
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
   `sota-code-security` rules/16 §2.13.
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
   cannot produce) is rules/16 §2.13 one layer down: there, a gate whose trigger
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
block. `rules/16` §2.10 governed the numbers a tool prints and not the words —
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
and it can be path-filtered, skipped, or — per `rules/16` §2.13 and GitHub's own
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

#### Trigger ledger for the deferred row *(a deferred trigger needs somewhere to accumulate)*

The deferred item is the *design*: a known operational gap left as a hole, so an integrity
verdict runs routinely red. The trigger is **a second implementation that ships it**. This
list exists so the next check is a read rather than the same search again — it was
re-derived from scratch on 2026-08-28, across 74 later intake rows, to produce these three
lines.

| checked | candidate | counts? |
|---|---|---|
| 2026-08-28 | **Private-project gate-ledger** (2026-08-26 brief, finding A): `chain` treats an unsigned head as failure, while the same repo had already rejected a hardware tap per commit — the steady state is a verdict red for an operational reason | **No — near-miss.** Same failure mode arriving *accidentally*, caught by a human before shipping (*"no, pls change it"*). Recorded as the cost-profile lesson in `sota-architecture` rules/01 §4a. Second occurrence of the mechanism, not a second implementation |
| 2026-08-28 | **This repo's Dependabot gate** (ROADMAP 22): `Repository invariants` failed on bot PRs for a purely operational reason | **No — counter-example.** Exempting `dependabot[bot]` *would* have been this exact design; the cause was fixed instead (its own secret store) |
| 2026-08-28 | Scanner false-positive class (2026-08-25) | **No** — already rejected as covered by `sota-detection-engineering/rules/04` §1 |
| 2026-09-05 | **Field brief** — `sota-proposal-2026-09-05.md`, from one engineering session on a static-analysis pipeline; every claim measured by execution in that session | **The aggregate that masks the detection.** A positive control summed every list field on an analysis result and asserted the total was non-zero. The result type mixes the engine's *derived inputs* with its *findings*, and preprocessing populates the inputs on any real graph — so the assertion is green whether or not detection works: `breaks` was empty on **all nine** cells where the engine was registered as controlled, and **12 of 35 controls were green on a result containing zero detections** | **adopted** | `sota-code-security/rules/10` **§2.16** + checklist, with a pointer from `sota-testing/rules/09`. **Home changed from the brief's `rules/11`** — placed with §1's falsification question, asked of a *field* rather than a control, and the line budget decided it (`rules/11` reached 499/500 with it, leaving no room for the checklist bullet the section needs). Duplicate check ran against the two nearest sections and both miss it: `rules/11` §2.2 is the *denominator*, and here the denominator was healthy; `rules/12` §2.1's *(now `rules/15` §2.1)* "instrument that cannot fail" is a scorer returning a plausible number whatever it is handed, and this one *could* fail, just never for the reason it existed. The **second-order half is the more valuable one and is kept**: when the honest assertion turns green cells red with no evidence of a regression, that manufactures a red build out of a measurement gap — assert on what the engine does produce and give the empty field its own recording test · v1.32.3 |
| 2026-09-05 | Same brief | **The empty comparand.** A differential oracle computes `lost = baseline - current`; with an empty baseline, `lost` is empty for **every** possible input, forever — the check returns the pass value unconditionally while examining a full, healthy current set and reporting a large, truthful denominator. Four of twelve committed reference sets were in that state | **adopted** | `sota-code-security/rules/11` **§2.2a** + checklist, plus the application in `sota-testing/rules/06` §6.3 (a mutation-survivor baseline is exactly this shape). Genuinely absent: **two independent concept sweeps** across all of `skills/` (`empty baseline|golden|approved set|reference set`, then `no new findings|diff against|comparand|set(old)|previous run`) returned **0 hits**. §2.2's remedy provably does not fire — the zero is on the other operand. **One addition beyond the brief**: the check must assert the reference *loaded*, not merely that it is non-empty, since a baseline file that failed to parse yields the same empty set through a different door · v1.32.3 |
| 2026-09-05 | Same brief | **Mutate the EXPECTATION, not the code.** Leave the SUT and the fixture alone and point one assertion at a plausible wrong expected value; still passing means the assertion is keyed to something true that is not evidence. Three controls asserted an engine found the `system` call planted in a fixture; re-pointed at `popen`, two failed correctly and one passed | **adopted** | `sota-testing/rules/06` **§6.3** as a fourth mutation probe + two checklist items, with a three-line pointer from `sota-code-security/rules/12` §1. **Home changed from the brief's first preference**: `rules/12` was at 494/500 and could not hold the section. Distinct from `rules/12` §1 (mutates the control), §2.1 (probe mutates a *fixture* rather than the runtime artifact) and `sota-testing/rules/02` §2.7's tautological test (expected value *computed* by the same logic — here it is a literal and the **key** is what fails). The **fan-out corollary is the sharpest part and has no equivalent anywhere** (`grep -rn 'fan-out' skills/` → 0 hits): an assertion keyed on a value the producer emits for a whole *category* rather than the matched member can never discriminate · v1.32.3 |
| 2026-09-05 | Same brief | **The scoped gate is not the gate** — a local whole-package run of "the same" linter is not evidence the gate is clean, because the gate's invocation is a different question | **adopted with a correction** | `sota-devsecops/rules/05` **§5.6** + checklist. **Reproduced here before adopting** (mypy 2.3.1, minimal package, both invocations on one tree at one moment): `mypy src/pkg/` → exit 1, `mypy --ignore-missing-imports --no-error-summary --follow-imports=silent src/pkg/a.py` → exit 0. **The correction is the mechanism.** The brief states that `--follow-imports=silent` on a changed-file subset *"infers differently"*; what reproduces is **error suppression for modules outside the named file set**, and in the *opposite* direction to the one reported. The rule therefore ships **direction-agnostic** — neither verdict is authoritative for the other — and names three independent levers (file selection, flags, a stale `.mypy_cache`) instead of asserting one mypy inference claim we could not isolate. Distinct from §5.6's existing content, which is the inverse: there the gate's scope drifts *away* from code that still exists; here the code is fully in scope and the human's re-run asks a different question · v1.32.3 |
| 2026-09-05 | Same brief, observation (a) | An invariant test that **quantifies universally in its name while iterating one item** — `test_every_tracked_phase_is_also_reported` over a single-element literal. Third sighting in one codebase | **adopted** | `sota-testing/rules/02` **§2.7** as a named smell + checklist. **Home changed from the brief's suggestion of `rules/14` §7**, which is explicitly about *sentences nobody executes*; this belongs with the executable test smells, and the aggravating factor — the test **passes**, so it reads as the enforcement of the claim its name makes — is the line worth writing · v1.32.3 |
| 2026-09-05 | Same brief, observation (b) | A static guard's blind spot should be stated **at the guard**: an AST scan read a phase name off the first *positional* argument, so one caller passing it as a keyword satisfied the invariant trivially | **adopted as a generalization of existing text** | `sota-code-security/rules/12` §2.1 *(now `rules/15` §2.1 — split out 2026-09-06)*. Not a new entry — the section already said *"state the traversed path in one line beside the probe"*, which is the same instinct; it now reads *"beside the probe — or beside the scan"* and carries the positional-argument blind spot as its second worked example. Recording it as plain `adopted` would have implied a section that does not exist; `rejected: already covered` would have lost the concrete tell, which is reusable and is the shape this repo's own AST invariants have · v1.32.3 |
| 2026-09-05 | **Evaluating the brief above** (not from the brief) | Two audit-checklist bullets had been sitting **inside a code fence** in `sota-code-security/rules/11` §2.2 since PR #226 (2026-08-16), rendering as example gate output. Found while checking the brief's duplicate claim for the empty-comparand class — one of the stranded bullets was the item nearest to it | **adopted (defect fixed + gated)** | Bullets moved into the Audit checklist, and **invariant 22** added: no `- [ ]` inside a code fence in a skill file. Nothing was close enough to catch it — invariant 2 tracks fence state but only to stop a fenced *heading* satisfying "ends with an Audit checklist", invariant 10 checks a rules file is *indexed* rather than that its contents reached anyone, and the line count never moved. All three CONVENTIONS-LEDGER filters pass; watched to fail on a re-injection of the original defect and to pass once fixed, before being wired in. Sweep found exactly **2 instances across 303 skill files** · v1.32.3 |
| 2026-09-06 | **This session's own roadmap sweep** — re-testing every open item's trigger rather than the item | Nothing checked that a CHANGELOG version heading has its **link reference**. Invariant 21 checks it has a git *tag*; the two fail independently, and a heading with no ref is **not a broken link** — Markdown renders it as literal text, so invariant 8 (which resolves `[text](file.md)` inline links) never sees it | **adopted** | **Invariant 23** + probe. Four consecutive releases (1.31.2, 1.32.0, 1.32.1, 1.32.2) had shipped without one. It went further than the roadmap row proposed: **sets, not counts** — at build time all three CHANGELOG files' heading and ref counts matched *exactly*, so a count check would have been just as green with two versions swapped; **both directions**, since moving a section without its ref is one edit producing two defects and no count change; and each ref must end in `/releases/tag/v<its own version>`, because all **75** already follow that one form so a deviation is a typo. Watched to fail on all four shapes including inside an archive file. **29 probes, 18 of 23** · v1.33.0 |
| 2026-09-06 | Same sweep — the CONVENTIONS-LEDGER | Invariants **20 and 21 had no row in either of the ledger's gate tables**; 22's landed 2026-09-05 and theirs did not exist | **adopted** | Three rows written (20, 21, 23), each with its incident, its silence argument and **what the gate does not check**, read out of `check-invariants.sh` rather than from the CHANGELOG. This is the **fourth** time this file has drifted from the checks it describes, and invariant 17 cannot catch it — 17 checks stated counts and 1..N enumerations in `AGENTS.md`/`CONTRIBUTING.md`, not whether the ledger's *tables* are complete. Left as a habit rather than a gate, per the ledger's own three filters: "is this table complete" is not mechanically checkable without deciding what counts as a row · v1.33.0 |
| 2026-09-06 | Same sweep — three stale triggers in one pass | **A deferral's trigger goes stale the same way a rule does**, and the roadmap table is the least-gated prose in the repo | **adopted (corrections landed in place)** | Item 1 asked for a salience piece **written five days earlier** ([WHY-SALIENCE-LASTS.md](WHY-SALIENCE-LASTS.md), 2026-09-01, linked from README *and* INDEX). Item 32 said *"nothing — the flag exists"* about an ablation flag that **did not exist**: `--pad-rules` did, the `BUILD_WORKFLOW` removal did not, and it had to be written. Item 12 carried a rules-file count of 261 against a tree with **262**. Re-tested and genuinely not met: items 5, 12's sixth-file trigger, and the deferred spanchain row. Same class as the items 25/26 closures, which found it twice on 2026-09-01; this pass found it three more times in a single reading of one table · v1.33.0 |
| 2026-09-06 | **This session's own gate work** (ROADMAP 35) | `AGENTS.md` states a <200-line rule *about itself* — it symlinks to `CLAUDE.md`/`GEMINI.md` and loads into every session — and nothing checked it. It had been breached **twice in two days** (201, 202), each time by adding an invariant's own table row | **adopted** | **Invariant 24** + 2 probes. The item's real content was a **decision, not a check**: gating a *target* is a category error, so cap-vs-target had to be settled first. It is a **cap** (the file already stated it as an imperative with a named escape — move detail to `CONTRIBUTING.md` — which is invariant 1's shape), and the sentence calling it *"ungated"* was what changed. **Beyond the item**: the gate also asserts the symlinks, because the cap only *matters* while they make the file load — `sota-code-security` rules/10 §1's proxy question aimed at one of our own gates. Watched to fail on four shapes, then **caught its own author on the first run** · v1.33.1 |
| 2026-09-06 | Same session (ROADMAP 36) | A new eval capability can ship without reaching `evals/README.md` — `--no-gate-arm` did, documented in the root README's index and in `--help` but not in the harness's own front door. Invariant 14 accepts a declared term in README **or** INDEX, so either satisfies it | **adopted with a correction** | **Invariant 25** + probe, as a **ratchet**. **Both designs the roadmap row proposed were wrong, and finding that out was the work.** The strict form was *measured first* — it opens red on **27** pre-existing (file, flag) pairs, nearly all generic plumbing, and a gate that opens red on things it does not care about is one someone disables. The "cheaper alternative" of adding `evals/README.md` to invariant 14's resolution set was rejected *on reading*: a third accepted location makes 14 **looser**, so it would have weakened the gate it was meant to reinforce. The ratchet **fails closed on an empty scan** (`rules/11` §2.2a — the rule this library added four days earlier, applied to its own newest gate) · v1.33.1 |
| 2026-09-06 | **Field brief** — a live container-pipeline incident (gate escape and verdict legibility), 6 proposals + an addendum | (1) A gate only gates if failing it makes the artifact **unconsumable** — publish a candidate the deploy watcher provably cannot match, promote after the last gate. (2) A failure verdict that lives only in an ephemeral executor's log **does not exist**. (3) A step copied between **sibling pipelines** rebinds to names the destination never declares | **adopted (1, 3)** · **adopted with a correction (2)** | `sota-devsecops/rules/09` §3, §4 (the file this release split out of `rules/05` §5.6) and `rules/01` **§1.11a**. **The correction is factual and was checked against the Kubernetes docs before landing**: the brief cites the 4096-byte kubelet cap on a termination message, but the total across containers is **12KiB divided equally** — 12 containers means **1024 bytes each**, and CI pods have init containers and sidecars, so the stated budget is optimistic in exactly the environment the rule is for. `FallbackToLogsOnError` (2048 bytes / 80 lines, whichever is smaller) added as the cheaper option the brief did not mention. All three absence claims re-verified at HEAD: 0 hits for the termination-message mechanism, and the 3 + 1 hits for the others were unrelated (Action retagging, Go module versioning, a TLS cert) · v1.34.0 |
| 2026-09-06 | Same brief, addendum proposals 4 and 5 | (4) A classifier whose **fallback branch is unreachable** speaks with false confidence. (5) An aggregate over **time** hides a burst exactly as an aggregate over a population hides a finding | **adopted as extensions, not new sections** | **Both were aimed at the wrong neighbour, and reading the text is what showed it.** (4) went to `rules/15` §2.2, which already required *"a negative control for anything that classifies"*; genuinely new are **test the definitive signal first** and **default the unknown case to the safe classification**. (5) went to `rules/11` §2.1 as a cross-reference: `sota-observability` rules/02 §4 already says averages hide what matters, so the gap was **UNREACHABLE, not absent** — that rule is about *designing* a metric and nothing routes a debugger to it. The reusable half survives either way: **12 µs and 12 s are different mechanisms with identical counts** · v1.34.0 |
| 2026-09-06 | Same brief, addendum proposal 6 | A failing command piped into a consumer still produces **plausible output** — `skopeo inspect` fails, `sha256sum` hashes empty stdin, and the guard gets `e3b0c44…`: non-empty, well-formed, never equal to a real digest, so it refused every publish | **adopted** | `sota-shell-scripting/rules/01` + checklist. Genuinely absent (1 unrelated hit). **Its own caveat is the part worth keeping**: *do not pattern-match the fix* — the same guard written with `--format` and no pipe yields a genuinely empty string, so its `[ -n "$var" ]` is correct and a grep sweep would "fix" working code · v1.34.0 |
| 2026-09-06 | **Executing the above** — the reference cost of a reactive split, measured | Can `rules/12` be split *reliably*? | **yes, with a named residual** | Two splits landed (`rules/12` → `rules/15`, `rules/05` §5.6 → `rules/09`). **16 `§` references needed repointing and invariant 18 caught 10** — the other **6 resolved fail-open** against a co-named skill, the residual documented after the `sota/rules/01` split. And **22 bare `rules/12` pointers carry no section at all**, which *no* gate can see: each was walked by hand and decided on meaning, 15 moved. The gate makes a split safe, not automatic — budget the hand-walk. Also found by the walk: a `README.md` link whose **text and target disagreed** (`rules/15 §2.2a` pointing at `12-verifying-the-verifier.md`), which invariant 8 passes because it only checks that a link *resolves* · v1.34.0 |
| 2026-09-06 | **External assessment #1** — an outside review of the library, 10 proposed gaps | Missing skills for agent engineering, change management, browser verification, **MCP security**, incident response, product/requirements, feature flags, dependency drift, more languages, **skill supply-chain trust** | **partly adopted; five rejected with evidence** | **Adopted**: `sota-skill-security` (0 hits on two concept sweeps — and the sharpest point, since this repo *is* an instruction-injection mechanism), change-surface discipline (`PR decomposition` 0, generated-file policy 0, "unrelated files" 0 — its own first pass would have missed this, the 11 apparent hits were `sota-ux-writing` matching *"no blame"* in error copy), flag **lifecycle/debt** (`feature flag` 20 and `canary` 21 but `flag debt|flag lifecycle` **0**). **Rejected**: incident response (`sota-detection-engineering/rules/06-incident-response-validation.md` and `sota-privacy-compliance/rules/06` both exist and the router routes to them by name); Scala/Elixir/IDP (`README.md:476` declares them out of scope); MCP/agent/browser as new skills — see the row below · v1.35.0 |
| 2026-09-06 | **External assessment #2** — a response to my rebuttal, proposing `Effective Coverage = Content × Routing Recall` and a `sota-skill-routing-and-composition` meta-skill | Knowledge is present but **fragmented and unreachable**; the next frontier is the router, not the catalogue | **adopted as a question, then REFUTED by measuring it** | The decomposition is right and the diagnosis is wrong. Built `run-routing-recall.py` + 10 gold-set cases and measured: **recall 0.975**, and the three shapes both assessments called missing skills — MCP audit, subagent delegation, browser verification — route at **recall 1.00**. The knowledge is not unreachable. **The reframing was mine**, offered to correct assessment #1, adopted by assessment #2, and neither of us had a number. What the measurement *does* show is **over-selection: precision 0.569 overall, 0.45 against gold sets transcribed from the router's own composition rules — the model loads roughly twice what the router says to load** — while two single-skill controls score 1.00/1.00, so it is selective when the task is narrow. Full write-up and caveats: [ROUTING-RECALL](../evals/results/2026-09-06/ROUTING-RECALL.md) · v1.35.0 |
| 2026-09-06 | Same, the **`routing contract` YAML** proposal (`covers:` / `requires:` / `often_composed_with:` in skill frontmatter) | Declare composition structurally so the router can expand dependencies and detect conflicts | **rejected: would be inert** | Skill frontmatter is two fields, `name` and `description`, and **only the description auto-loads** — it is the entire trigger classifier and the body is inert until the Skill tool fires. Custom keys would be read by **nothing** while looking exactly like a routing system, and invariant 4 would pass it: `sota-code-security` rules/10's silent-control-failure class, committed by this library against itself. Also **not absent** — the router already carries **21 hand-written cross-cutting composition rules**. The reachable version is structure in the router body plus a gate that checks it against the tree, and the measurement above says it is not needed yet · v1.35.0 |
| 2026-09-06 | Both assessments name **Superpowers** as the methodological competitor | *"a complete agentic software-development methodology, not merely a best-practices library"* | **adopted as a measurement, not a claim** | Added to `evals/cases/competitors.json` at a pinned SHA. We had a head-to-head instrument aimed at three other repos and **not** at the one the comparison actually rests on (`grep -ri superpowers evals/ docs/ README.md` → 0). Repo, MIT licence and SHA `b36e0829` read from the GitHub API rather than from the assessment, and all four listed files verified to exist at that SHA. **Caveat recorded in the manifest**: it is process guidance and the completeness cases score domain best practices in a built artifact, so a low score is evidence about fit to *this measure*, not about the project · v1.35.0 |
| 2026-09-07 | **Implementing my own recommendation** — the flag-lifecycle item | I had told the operator `flag debt`/`flag lifecycle` returned **0 files**, and recommended adding flag lifecycle to `sota-architecture` | **rejected: already covered — my recommendation was wrong** | `rules/06` §6 already requires every flag to have an **owner, a description and an expiry/removal ticket at creation**, removal within weeks of 100%, the 2^N stale-flag anti-pattern, kill switches, local evaluation with a hard default, and audited flips. **I searched for the words, not the concept** — the same mistake the first external assessment made, and I made it while correcting them. What *is* genuinely absent is narrower: nothing links a progressive rollout to **version skew**, so a 6-line note now states that two app versions run at once and the **contract step must be ordered after flag removal** — contracting while the old path is still reachable is the outage that presents as *"the rollback made it worse"* · v1.35.0 |
| 2026-09-07 | Same session — the **change-surface** item | `PR decomposition` 0, generated-file policy 0, "unrelated files" 0 | **adopted** | `sota-docs-workflow/rules/03` **§5a** + 4 checklist items: no drive-by reformats (they destroy the diff *and* misattribute `git blame`), a stated generated-file policy with generated lines in their own commit, decomposition **by reviewability rather than line count**, migrations sequenced so every commit is independently deployable, revert-vs-fix-forward decided by blast radius, and keeping mechanical moves separate so `git bisect` does not land on a 4,000-line reformat · v1.35.0 |
| 2026-09-07 | Same session — `sota-skill-security` | 0 hits on two concept sweeps; the repo is itself an instruction-injection mechanism | **adopted** | New skill, 3 rules files. Its own cap check caught the author: the first description was **1308 chars against the 1024 cap**, i.e. a skill that would have been installed, correct, and **silently never loaded** — which is the failure `rules/03` §1 of that very skill warns about. Trimmed to 984 · v1.35.0 |
| 2026-09-09 | **Field brief from a separate project's audit work** — P3 | The rules/10–15 cluster is thorough about controls that are WRONG, INERT or ABSENT and never treats one that is **correct and then edited** — an integrity axis, not a correctness one | **adopted** | `sota-code-security/rules/12` **§1c** + §1c.1 and 3 checklist items. The brief's three claimed-absent strings were absent (verified with positive controls in the same invocation), but the novelty case rests on what the greps could not answer: **§1b was the real test** and reads as the same idea — *where the probe lives* — while its threat is **neglect** (a check added next week with no known-bad) and §1c's is **an adversary with write access**. `rules/14` §8 is a *benign* neighbour overwriting a control's **output**; §1c's actor is the constrained principal and the target is the control's own **code**. `editable install` already hit three files in the cluster — the brief's own mechanism — and all three are about whether a *test mutation* landed. The section names that boundary explicitly rather than leaving the next reader to find it · v1.39.0 |
| 2026-09-09 | **Same field brief** — P4 | Every bullet in *Generator and suite discipline* is about a **red** oracle (tautology, reproducible failures, runtime budget); none is about how much to believe a **pass** | **adopted with a correction, and split in two** | `sota-testing/rules/06` + 1 checklist item. **The correction:** the proposed bullet would have landed directly under *"keep the printed seed"* and read as its contradiction, so it now names that bullet and resolves it — *pin the seed to reproduce a failure, vary the seed to earn a pass* — and disclaims the ~100-case budget bullet below it as well, since "run several seeds" otherwise reads as pressure on the inner loop. **The split:** "run several seeds" is near-common-knowledge; *a cleared oracle surfaces a different class because the loud defect was generating noise that hid quieter ones* is the half nothing else in the library says, and it carries the brief's sharpest detail — the survivors ran in the **opposite direction** from what the tool was built to find. One bullet would have buried it · v1.39.0 |
| 2026-09-10 | **Blog tip, 365tipu.cz #3314** — *alternating Codex and Claude Code over one project; each may read different instructions* (idea taken, no text — an all-rights-reserved blog) | The cross-tool instruction-file problem, plus Claude Code's `@AGENTS.md` import, `/context` as the did-it-load check, and `/import` being a one-time copy | **adopted in part, after validating every claim against the vendor docs — the blog was right and incomplete** | `sota-docs-workflow/rules/01` §10 + `docs/VERIFY-SETUP.md` check 4a · v1.40.0. **The core problem was already covered** (§7 "maintain one canonical file… symlink or include rather than fork", and §10's three-option trade-off list), so the general tip is *rejected: already covered*. What was **not** covered and is now: (a) the **native `@AGENTS.md` import**, which Claude Code's own docs recommend over a symlink and which costs no hop — §10 listed a one-line pointer as "the safest default", a ranking this corrects; (b) **Windows needs Administrator or Developer Mode to create a symlink**, a second failure mode beside the `core.symlinks` one §10 already had; (c) three **silent** non-load paths, including an external import whose approval was **declined once and never asked again**; (d) `/context` → *Memory files* and the `InstructionsLoaded` hook as the verification, which is this library's own *presence is not loading* thesis aimed at agent docs. Items (b), (c) and the import limits (4 hops, code-span skipping) came from **code.claude.com/docs/en/memory**, not the blog — the blog's claims were checked there rather than adopted on trust. **Correction 2026-09-10, same day:** a first draft of §10 and of `gen-agents-md.sh` asserted Gemini CLI had *no* import directive and gave `GEMINI.md` prose instead. **Wrong** — `gemini-cli` `docs/reference/memport.md` is an entire page about `@file.md` imports, and `docs/cli/gemini-md.md` documents a `context.fileName` **list** that accepts `AGENTS.md` outright. The bad claim came from reading two docs that happen not to mention it: an absence needs a second method with a *different failure mode*, and two shallow reads of one doc set is not that — the same error this library's own rules/06 §2 describes, committed while writing about it |
| 2026-09-10 | **Operator question — "gemini-cli was replaced by antigravity-cli"** ([developers.googleblog.com](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/)) | Whether the library's Gemini CLI / `GEMINI.md` guidance is still current | **adopted — a freshness defect, and it inverted the design decided an hour earlier** | `gen-agents-md.sh` (`--legacy-gemini`), `sota-docs-workflow/rules/01` §7, `README.md` · v1.40.0. **Two primary sources, one of them measured on this machine.** (1) Gemini CLI 0.59.0 headless now exits `IneligibleTierError: This client is no longer supported for Gemini Code Assist for individuals … migrate to the Antigravity suite` — so the retirement (2026-06-18, free/Pro/Ultra) is in force, not pending. (2) Antigravity's own bundled docs, on disk at `~/.gemini/antigravity-cli/builtin/skills/agy-customizations/docs/rules.md`, say it discovers *"Directory-Based Rules (`GEMINI.md` / `AGENTS.md`)"* — **the successor reads `AGENTS.md` natively.** So `GEMINI.md` went from a default sibling to opt-in behind `--legacy-gemini`, and **Claude Code is now the only mainstream tool needing a pointer at all**. The lesson is the repo's own EOL policy earning its place: the tool lists named a CLI that had stopped serving individuals three months earlier, and nothing in CI can see a tool going away |
| 2026-09-10 | **Field brief from a session that USED the library** — an agent exhausted the machine's process table with backgrounded wait loops | Whether "blast radius" as this library states it covers a resource other than disk | **adopted — and the sharpest shape yet: TWO of our own rules came one predicate short** | `sota-shell-scripting/rules/06` **§4** + its checklist half · v1.40.1. **Measured:** a day of `while …; do …; sleep 60; done &` loops left **≈10,700 orphaned `/bin/sh`**; at failure `ps -A | wc -l` read **11,463** against a `kern.maxprocperuid` of **11,136**. **Why the existing rules missed it:** §1 has the `pgrep -f` self-match and says such a loop *"never exits"* — but frames the cost as a **burned timeout**, not unbounded spawning; §3 bounds blast radius and is **entirely disk** (its field report is a 40 GB copy; its checklist asks for `df -h` and `du -sh`, never process headroom). Novelty re-verified with positive controls in the same invocation: `fork failed`, `process table`, `resource temporarily`, `ulimit -u` → **0 files** in `skills/`; `fork bomb` → 1, `sota-sandboxing` rules/01, a **different subject** (assuming an untrusted *workload* may fork-bomb and testing containment). **The detail worth the rule:** it does not degrade, it hits a ceiling and every tool fails at once — *including cleanup*, since `ps -o ppid`, `killall` and even `echo` in a fresh shell all need to fork, and `kill` being a builtin does not help when each command spawns its own shell. **Caveat recorded, not papered over:** parentage was never measured — `ps -o ppid` could not fork by the time it was tried — so the rule is written around the **mechanism** (unbounded backgrounded loops spawn per tick and nothing reaps them), not around a proven parent chain. **SUPERSEDED same day — the caveat resolved AGAINST this attribution:** parentage was checked afterwards and the ≈10,700 `/bin/sh` belonged to a **self-recursive `PATH` shim**, not to the wait loops; deleting one file took the count to 691. §4's mechanism and remedies stand unchanged (an unbounded backgrounded wait is independently a real way to fill the table), but its **figures are now labelled as the signature rather than as evidence for its own cause**, and the two causes are cross-referenced both ways. See the next row |
| 2026-09-10 | **Session self-intake** — I reported "20 PRs" from a `gh pr list --limit 20` query while stripping attribution from PR bodies; the real population was **330**, and a second scope error followed it | Whether this library says anywhere that a listing tool's page is not a population | **adopted — the absence was clean under two searchers and five terms** | `sota-shell-scripting/rules/06` **§5** + its checklist half · v1.40.1. **Measured 2026-09-10** on a repo with 330 merged PRs: `gh pr list --state merged --json number | wc -l` → **30** (a *default* cap, no flag typed), `--limit 20` → 20, `--limit 1000` → **330** — all three **exit 0 with empty stderr**, so the order-of-magnitude shortfall has no signal at all. **Why the existing rules missed it:** §2 covers a searcher that *silently traverses less than you think*, which is a defect-shaped absence; this is **policy** — the tool did exactly what was asked, and the two ways to get it wrong are the cap you never set and the cap you set for a **different question** and left in the scrollback. Novelty controls in the same invocation: `pgrep` → 4 files, `positive control` → 5, `wc -l` → 16 (searcher works); `--limit`, `default page`, `first page of`, `gh pr list` → **0 files** under both `grep` and `ugrep -R`; all 6 `paginated` and 40 `truncat` hits are about *designing* an API or *rendering* output, never consuming a listing. **The second finding came from writing the fix:** the server-side count read **330** and the `--paginate` example read **339**. The pagination was correct and the **predicate** was wrong — `state=closed` includes 9 closed-unmerged PRs — so the corrected command had quietly begun answering a different question than the one it replaced. That reconciles exactly (330 + 9), and it is the return on a second method having a *different* failure mode (`sota-code-security` rules/11 §7): had the two agreed, nothing would have been learned; had only the fixed one run, **339 would have shipped as the merged total**. Both halves are in the rule, the cap-equality control (`n -eq limit` ⇒ treat as a page) is stated as the only signal the tool gives, and every shipped command was run against the live repo before landing |
| 2026-09-10 | **Field brief from a session that USED the library** (round 2) — a fuzzing harness's temp `bin/` shim directory, placed first on `PATH`, held a `sed` shim that called `sed` and re-entered itself forever | P5: whether the library covers a **non-adversarial** `PATH` shadow — a dir you control, holding a file you wrote, shadowing a command your own file calls. P6: whether `rules/06` §4's field figures belong to a different cause | **P5 adopted with a correction · P6 adopted — the brief was right and it refuted my own attribution** | `sota-shell-scripting/rules/03` **§3a** + 3 checklist lines, and a correction block in `rules/06` §4 · v1.40.1. **P5 — why it was absent:** §3 was written *entirely* from the attacker angle ("Attack: attacker-writable dir earlier in PATH"), and `fork bomb` hits only `sota-sandboxing` rules/01, about **containing hostile code**. The mirror is not adversarial, which is why nobody looks for it. Novelty re-verified with positive controls in the same invocation (`PATH hygiene` → 2 files, `fork bomb` → 2, `command -v` → 3): `self-recurs`, `re-invoke`, `wrapper that calls`, `shadows what it calls` → **0 files**; `LD_PRELOAD` → 2, both merely *unset-lists* in a privileged preamble, never a recursion namespace. **The correction:** the brief states "there is no recursion limit, because each level is a new process". True for shims and aliases, **false for shell-function overrides** — those are ONE process and the shell bounds them. Measured: bash `FUNCNEST` is **unset by default**, so `f(){ f; }; f` exits **139 (SIGSEGV)**; zsh's `FUNCNEST` defaults to **700** and errors cleanly at exit 1. So three namespaces, **two failure modes** — and the rule now says why that matters: **the bounded form is the one you will try first**, it blows up locally, and it reads as "the shell protects me" right before you ship the unbounded one. The brief's other two falsifiable claims both reproduced: `command`/`builtin` terminates a function wrapper, and Python `str.format` raises `KeyError: 'a#@'` on `${a#@}` **inside a `#` comment** (the outer layer does not know what a shell comment is). **P6 — settled from the commit, as the brief asked:** the figures are from that same incident, and #342's own row recorded that parentage was unmeasured. The tell was in the evidence all along — a `zsh` wait loop spawns `zsh`, `sleep` and `pgrep`, never 10,700 **`/bin/sh`** — so the refuting detail was sitting inside the number I published. **A plausible culprit you already have in mind is exactly when to demand the evidence, not when to skip it** |
| 2026-09-10 | **Field brief from a session that USED the library** (round 3) — a security-tooling session reporting three proposals against `sota-testing`, each with a field report | Whether the mutation control probe covers the **revert**; whether §7.4's parallel rule misleads on two *independent* runs; whether any rule covers a threshold measured on one population and asserted over a pool | **4 of 4 adopted — including the brief's own "left to the reviewer" item** | `sota-testing/rules/06` §6.3 (2 bullets), `rules/07` §7.4 (2 bullets) + new **§7.9**, `rules/04` §4.8 (1 bullet), 4 checklist lines · v1.40.1. **All three absences re-verified independently** with positive controls in the same invocation (`mutation` → 8 files, `ratchet` → 3, `quarantine` → 4): the revert half (`revert the mutation|restore the file|stranded|git checkout --`) → **0**; two concurrent runs (`concurrent run|two runs|shared database|another session`) → **0**; pooled thresholds → only tangential hits (`sota/rules/03` on correlation across a population, `rules/07`'s coverage-denominator checklist line — about what is *measured*, not about a floor diluted by new data). **Proposal B is the highest-value shape there is: a rule of OURS pointing the wrong way.** §7.4 ends *"failures unique to parallel runs are isolation bugs, never 'just rerun'"* — correct for workers inside one invocation, and the **opposite** of correct for two whole suites contending on a database neither owns, where re-running the subset in isolation is the right diagnosis. The scope was never stated, so the nearest rule actively forbids the correct move. Now scoped, with the doubled **skip** count named as the tell and parentage (not process name) as the instrument — the same instrument as `sota-shell-scripting/rules/06` §4 and `rules/03` §3a, which is now three independent incidents pointing at one diagnostic. **Proposal C reproduced arithmetically before adoption** (17/1203 = 1.41% pooled, 17/712 = 2.39% ex-population, per-population 7.5/3.0/1.7/0/0), and its proposed `max(share) >= floor` fix was checked to pass on that same data. The rule's sharpest line is the brief's: **dilution is the one cause a pooled metric cannot distinguish from the cause its author imagined** — the control fired saying "a family has probably gone inert" with no source line changed in eight days. **The item the brief declined to propose was adopted too:** a stopped runtime turned 30 tests into skips with **0 failed** — §4.8 covered a bench producing *empty output*, never a **green run that ran fewer tests**, and the only moving number was a count. **Invariant 18 earned its keep mid-edit**, catching a bare `§6.3` in `rules/07` that resolved nowhere because that section lives in `rules/06`. **Routing note recorded, not actioned:** the brief reports invoking the router once at session start and never re-routing as the session changed shape — it declined to call this a trigger defect and so do I, but it is the second observation of *route-per-task-shape, not per-session* and is worth a roadmap item if it recurs |

**Status: 1 shipped instance, 1 near-miss, 1 refusal — trigger NOT met.** Coverage as of
this check: the *generic* half is owned twice over (rules/04 §1 alert fatigue; `sota-
observability/rules/06` — *"broken telemetry that the team trusts is worse than a known
gap"*). The *specific* half — encode the known gap as a marker inside the structure, so the
verdict stays green and the gap stays auditable — is **absent**, confirmed by two
differently-worded sweeps of `skills/`. That is what a second instance would buy.

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
rather than just fixing: `rules/16` §2.4 (swallowed exceptions on the enforcement path) is a
direct hit on link 3, `rules/16` §2.3 names exactly this shape ("distinguish *empty because
configured empty* from *empty because parsing dropped everything*"), and `rules/11` §1 ("zero
is a legitimate answer") explains why the failure survived: `0 CWEs / 0% confidence` is a
shape a healthy run also produces.

**What was not covered — link 1.** `rules/16` §2.7 is the nearest rule and its text, its
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

**Every language row was run, not recalled** — the *cross-language summary tables are
unverified* lesson, applied deliberately after a Rust row in `sota-sandboxing` rules/04 shipped wrong.
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
(Merge dates below are **UTC**, as `gh pr view --json mergedAt` reports them: #155 at
`13:34Z` reads as the 26th anywhere west of UTC+11, but #281 at `07:57Z` flips to the 26th
west of UTC−8. A bare date is a claim with a hidden timezone in it.)
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

### 2026-08-31 — ECC, second pass: the mandatory twin, the loop's boundary, and a token heuristic we had already measured

[affaan-m/ecc](https://github.com/affaan-m/ecc) ("Everything Claude Code", MIT) read
whole at **`a104765`** — 68 agents, 286 skills, 94 commands, hooks, cross-harness
adapters. Not a first encounter: the repo is a pinned competitor in
`evals/cases/competitors.json` at `ed38744`, where it scored **0.87 to our 0.99** on
the completeness tasks (2026-07-14). This pass asked the other question — not "does it
beat us", but "what does it know that we don't". It is a breadth library where we are a
depth one; ~6 of 286 skill files carried the value, which is itself the finding about
where to look in a large catalogue.

**Adopted with a correction — a *required* tool call stated only in the prompt.**
ECC's `agent-architecture-audit` asks "can the model skip a required tool and still
answer?" and prescribes code-gating. My first read called this an uncovered gap; it is
not, quite. `rules/14` §3 already owns *instructions standing in for controls*, and
names tool gating explicitly. But every example there is **prohibitive** — "never
reveal", "only call this for admins" — and its remedy is *remove the material from the
context*, which cannot repair a **missing step**. The mandatory direction is a distinct
bug with a distinct fix (the harness refuses to finalize without the result; the skip
gets counted) and brings a second silent failure §3 does not cover: the model narrating
a call it never made and reasoning from the invented result. Landed as
`sota-llm-engineering` rules/04 §2 with a pointer from `sota-code-security` rules/14 §3.
Recorded as a correction rather than an adoption because the source's framing — "a gap"
— would have had us restate rules/14 in a second place.

**Adopted — the done-criterion and its boundary are written together.** From
`loop-design-check`, the strongest file in the repo. "All tests pass" as a loop's exit
condition is a licence to delete the failing test; the antibody is stating the boundary
("no test file deleted or weakened") in the same breath as the goal. With it: prefer
**reconciliation over assertion** for an exit condition (an assertion can be loosened, a
diff against an external reference cannot), the judge is not the builder and the builder
cannot edit the acceptance criteria, a retry cap escalates to a human, and clarification
is front-loaded because a loop will not stop to ask at 03:00 — it commits a guess and
runs it to completion. We had Goodhart (rules/01 §8) and "grading your own homework"
(rules/01 §3) separately; nothing assembled the loop-design version. Landed as
`sota-llm-engineering` rules/04 §3a. Its lineage claims (Wiener's two-level feedback;
two named blog posts) were **not** verified and are not reproduced — the mechanism
stands on its own.

**Adopted — memory admission precedence.** `agent-architecture-audit` Q7: can the
agent's own monologue become persistent memory? `sota-code-security` rules/08 already
covers memory *poisoning* (gate writes, provenance-tag, user-scope) — verified present
at `rules/08:87–91`, so the security half was ours. The correctness half was not: an
agent's own inference admitted as an observation, and no precedence rule when a user's
correction meets an earlier agent assertion. The symptom is a correction that will not
stick. Landed as `sota-llm-engineering` rules/04 §5.

**Adopted — ask for a fact to produce, not a judgment to make.** From `gateguard`,
whose thesis is that "are you sure?" always returns yes but "list every file that
imports this module" forces a Grep, and the *investigation* is what changes the output.
Our BUILD step 4 is self-evaluation in form; the falsification question was already
close. Landed as `sota/rules/02` §4 as a third question: write each gate item as an
artifact you must return, not a yes/no about your own work. **Their headline number is
not adopted and is not cited** — "+2.25 points" is two tasks, LLM-judged, n=1 each.
Supporting evidence for the framing came from the source contradicting itself: ECC
ships `gateguard` ("LLM self-evaluation doesn't work, experimentally verified") *and*
`agent-self-evaluation` (the agent rates its own output 1–5 on five axes).

**Adopted — collect deterministically, then judge.** `rules-distill` names the pattern
we use unnamed: scripts enumerate exhaustively, then the model judges over the complete
set. Inverting them is how an audit acquires a confident blind spot, and the miss is
invisible because a finding list looks identical whether the census was 12 of 12 or 12
of 61. Landed as `sota/rules/01` §3. The same file's **2+ sources** bar for promoting a
principle out of a skill is adopted as an intake rule above.

**Adopted — a verdict's reason must be self-contained.** `skill-stocktake` bans
"unchanged" as a reason and requires a Retire to name what covers the need instead. We
had the specific case (`rejected: already covered` must cite file:line); this
generalises it to every verdict we record, with a worked table. Landed as `sota/rules/03`
§3.

**Adopted — the summary posture is capped by the worst blocker standing.**
`production-audit` caps a numeric score at 69 while authz is missing or a payment
webhook is non-idempotent, and at 84 while CI is red or the critical path is untested.
We publish prose posture rather than a score, so the cap is expressed in words: no
executive summary reads better than "not ready" with an unfixed Critical in the list.
Its companion — **"evidence not obtained: what would change confidence"** as a named
section — is the ask-shaped half of our exclusions list. Both landed in `sota/rules/03`
§5.

**Rejected: contradicted by our own measurement — the token heuristics.**
`context-budget` estimates with `words × 1.3` and `chars / 4`; `token-budget-advisor`
builds a four-level depth menu on the same arithmetic and advertises "~85–90% accuracy
(±15%)" for a method with no tokenizer in it. This is precisely the shortcut measured at
a **54% under-count** against Anthropic's `count_tokens`
(`sota-llm-engineering` rules/02 §2, lines 74–79) — and under-counting in the direction
that makes you think you have room. Kept here as the field example that rule now has.

**Rejected: contradicts existing rules — the AGENTS.md hard numbers.** "80%+ coverage
required" is the global percentage target `sota-testing` rules/07 §7.2 argues against by
name ("80% chosen-by-committee says nothing — the *which* 20% is everything"); "always create new objects, never mutate" as a CRITICAL cross-language rule is
wrong in the Rust, Go and C++ hot paths our language skills cover.

**Rejected as a mechanism, kept as a known-bad — the per-agent "Prompt Defense
Baseline".** A fixed six-line anti-injection preamble is pasted into all 68 agent files.
It is a prompt-level defence against a prompt-level threat: `rules/14` §3 is exactly the
class, and the boilerplate is a textbook instance of a control that looks like
enforcement across 68 files and enforces nothing.

**Deferred — per-skill run telemetry.** `scripts/lib/skill-evolution/health.js` records
run outcomes to JSONL, computes a rolling success rate, and flags a skill as `declining`
past a threshold. It addresses a real problem of ours (the library has no telemetry and
learns nothing from use unless someone reports it). Deferred, not rejected: it needs run
outcomes we do not collect, and any implementation must stay local-only and opt-in —
this library ships no network. **Revisit if** a local `--record` flag on the eval runners
would produce the same signal without a new collection surface.

**Noted, no action — domain coverage they have and we do not**: agent payment protocols
(x402), DeFi/AMM security, prediction-market oracles, on-device foundation models,
homelab networking, netmiko/Cisco automation, healthcare EMR/CDSS. Out of scope by
design. The two worth watching are **on-device/edge model deployment** (we touch it only
in `sota-mobile` rules/03) and agent-to-agent payment authorization.

**Measured, not asserted.** Items 1, 2 and 5 above are behavioural claims about what a model
does under pressure, so they were put to a new instrument rather than reasoned about:
`evals/run-prompt-independence.py`, built for this intake from ECC's `skill-comply`. Under a
**competing** prompt (6 cases × 3 samples, temp 0.7) the library reads **0.491 → 1.000,
+0.509**, with the with-library arm perfect in **18 of 18** runs; the three cases these new
rules touch move **+0.426** pre→post against **+0.074** of sampling noise measured on three
byte-identical control cases in the same run. Full method, both runs, and a null that was
opened and withdrawn the same day:
[PROMPT-INDEPENDENCE](../evals/results/2026-08-31/PROMPT-INDEPENDENCE.md).

### 2026-08-31 — a stack-specific prompt template, and the eight fields our profile never asked for

A user-supplied "Enhanced Prompt Engineering Template & Context Management" brief (dated
2025-04-02, written for a Nuxt / FastAPI / SurrealDB / Kubernetes app) offered as intake.

**Rejected as skill content: already ours, and structurally not a skill.** All 21 of its
sections map onto existing skills — §8 API design → `sota-api-design`, §12 → `sota-privacy-
compliance`, §13–14 → `sota-observability`, §16 → `sota-api-design` rules/05, §17 →
`sota-api-design` rules/01, §19 → `sota-code-security`, §20 → `sota-testing`, §21 →
`sota-devsecops`. It adds no engineering knowledge. It is also a **stack profile** by
construction: it names a concrete stack and a location, which `CONTRIBUTING.md` forbids in
`skills/` and which operating principle 4 already routes to `profiles/<you>.md`.

**Rejected, and now double-sourced: the global coverage target.** "Coverage: Target [e.g.
80%]" is what `sota-testing` rules/07 §7.2 argues against by name. This is the **second
independent source in one day** to state it — ECC's `AGENTS.md` says "80%+ coverage
required". Two sources converging on the same bad practice is evidence the rule needs
stating more loudly, not evidence to soften it; the new **Testing conventions** profile
section now states the ratchet alternative at the point where a reader would otherwise
write "80%".

**Rejected: the always-pasted brief** — *and one of the two grounds I gave has since been
withdrawn.* "Reference this brief at the beginning of your prompts", 21 sections including
pasted code snippets, was rejected on (a) the "measured load-lean finding" in `sota/rules/02`
§1 and (b) §6's pasted signatures rotting silently against the code.

**Ground (a) does not survive.** It was never measured, and when it was measured **the same
day** — 400 lines of genuine competing guidance added to the completeness arm — it read
**−0.01**
([COMPLETENESS-PADDING](../evals/results/2026-09-01/COMPLETENESS-PADDING.md)). The claim is
withdrawn from `rules/02` §1 and from the router, and it is withdrawn from here too: citing a
number to justify a rejection and then refuting the number hours later is precisely the shape
this log exists to make visible.

**The rejection still stands on ground (b), which is unaffected**: pasted signatures drift
from the code with nothing to catch it (`sota-llm-engineering` rules/04 §5, don't resend what
you can reference), and a 21-section brief re-pasted every turn is a maintenance burden whose
staleness is invisible. **A profile is consulted; a brief is pasted** — that distinction is
the design difference, and it is an argument about *freshness*, not about attention.

**Adopted: what it exposed in `profiles/example.md.template`.** The useful question was not
"adopt this" but "does our profile ask for what this asks for?" It did not. Two independent
methods were run and **they disagreed, which is the finding**:

- *Derived* — every one of the 40 domain skills mapped against the template's 8 sections,
  looking for skills with no field carrying their project-specific choices. Produced:
  design/frontend, migrations & test data, testing, API conventions, LLM/AI.
- *Observed* — the section headings a real in-use profile had grown beyond the template.
  Produced: stack mapping, data classification, internal names, detection posture.

The two lists do not overlap at all. Derivation found what the *library* needs told; use
found what a *person* reached for and had to invent. Either method alone would have
reported roughly half the gap, and the derived half remains the weaker evidence because
nothing has yet used it. Eight fields landed: **Stack mapping** (generalising a line that
existed only inside Observability), **Design system & frontend conventions**, **Migrations,
seeding & test data**, **Testing conventions**, **API conventions**, **LLM / AI features**,
**Data classification**, **Internal names — never in public output** (which is this repo's
own leak lesson written down as a profile field, pointing at the CI denylist that enforces
it), plus **SLO/budget** and **detection-posture** lines folded into existing sections
rather than given their own. Template 76 → 172 lines; every new section says "delete if it
does not apply", because a template nobody finishes is worse than a short one.

Considered and not added: a docs/release-workflow section (commit convention is already
under Security conventions, and branching is visible in the repo) and per-skill sections for
mobile, ML, confidential computing and CLI — all conditional enough that the `Projects`
table already covers them.

### 2026-09-07 — pinning as a freshness decision, and the watcher you had to write yourself

Source: a field brief from a session that used the library to pin and deploy a Caddy-based
API gateway (Coraza WAF + rate limiting) on self-hosted Kubernetes. Fifth brief of this
shape; the predecessor landed as v1.34.0. Four proposals, **all four adopted — two of them
`adopted with a correction`**, because two supporting claims did not survive reproduction.

**Verified before adopting, per this log's own rule.** Every "0 hits" claim was re-run and
then the candidate home file was *read*, not grepped: `sota-devsecops` rules/03 §3.1 and
§3.7 in full, rules/09, `sota-golang` rules/07 §4 and rules/05 §8, `sota-code-security`
rules/15 §2–§2.2a. Three of the brief's own falsifiable claims were reproduced against
primary sources rather than accepted: MVS semantics at go.dev/ref/mod, Renovate
`customManagers` and the Dependabot options reference, and the GitHub API behaviour for a
tag-only repo.

**Adopted #1 — a pin nothing can see is a freeze, not a pin.** `sota-devsecops` rules/03
**§3.7.1** (new). §3.7 audited only the *absence* of update automation and assumed
Renovate/Dependabot as the mechanism; nothing addressed a version string the bot cannot
parse — `xcaddy build v2.11.4 --with plugin@v0.1.0` in a `RUN` line, and the same shape in
Bazel/Make args, `go install tool@version`, and `pip install x==y` inside a Dockerfile.
Pinning converts an unreviewed drift into an unreviewed freeze and **both states are
silent**. `customManager|regexManager` returned **0 hits across all 42 skills**, so the
supported fix was unstated as well as the problem. Confirmed against primary sources
2026-09-07: `customManagers` is the current Renovate option and takes an explicit
`datasourceTemplate`; Dependabot's ecosystems are manifest-shaped and it has **no**
regex-manager equivalent (it reads a Dockerfile's `FROM`, not its `RUN` args). Nearest
prior coverage, none of which closes it: rules/01 (keep Actions pins fresh with Renovate —
right obligation, but only where a bot can see the pin), rules/03 §3.8 (vendored code rots
invisibly to manifest-reading scanners — same shape, different mechanism), and
`sota-architecture` rules/01 §4 (an experiment with no scheduled read-back). Worth noting
the library already audited the *opposite* direction of the identical construct —
`sota-golang` rules/07 flags floating `go install foo@latest` as MEDIUM — so it covered the
unpinned half and not the frozen half.

**Adopted #2, with a correction — a bespoke version watcher inherits the publishing
conventions of what it watches.** `sota-devsecops` rules/09 **§6** (new), deliberately
*not* rules/03: this is inert-control material and rules/03 had 49 lines of headroom.

Both of the brief's failure modes are real and neither was stated: a watcher querying
`GET /repos/<o>/<r>/releases/latest` gets a 404 from a tag-only project and skips that
entry silently forever, and a "more than one minor behind" threshold reported **OK** for the
`v2.11.4 → v2.11.5` patch that was the entire reason the pin existed. Reproduced against
the live API 2026-09-07: `mholt/caddy-ratelimit` has **0** releases, the single tag `v0.1.0`,
and `releases/latest` answers `404 Not Found` — which also confirms rules/03 §3.9.5's
"recent `pushed_at`, no release in two years" rule firing exactly as written (`pushed_at`
2026-06-12).

This is the **unreachable-not-absent** shape. `sota-code-security` rules/15 §2.2a already
carries a substantial treatment of instruments that run over time — the four-state
DONE/NOT-DONE/GONE/UNKNOWN model, the blindness counter, cross-checking against an
independent signal — and §2.2's known-bad/known-good references would have caught the 404
entry. But it lives in a different skill, and someone writing a version watcher loads
`sota-devsecops`. So §6 states the version-watching instance and **points at rules/15
§2.2a** rather than restating it; the threshold axis is the genuinely new half.

*The correction:* the brief's supporting caveat was that `sort -V` might be missing from the
watcher's container. Measured the same day rather than repeated: the *inversion* is real
(`sort` ranks `v2.9.1` above `v2.11.4`; `sort -V` gets it right), but **BusyBox 1.37.0 in
`alpine:latest` does support `-V`** — it is simply absent from the terse usage line. So the
rule ships as *verify the comparator in the image it runs in*, with the measurement stated
in both directions, rather than as *alpine lacks it*.

**Adopted #3, with a correction — in Go, `require` is a FLOOR, not a ceiling.**
`sota-golang` rules/07 **§4**, with a pointer from rules/03 §3.7.1. `minimal version
selection|MVS` returned **0 hits across all 42 skills**, confirmed by reading: §4 covered
the `go`/`toolchain`/`tool` directives and mentioned `replace` only as "temporary at best",
and rules/05 §8 cited `proxy.golang.org` for sumdb verification alone. Verified at
go.dev/ref/mod: MVS tracks "the highest required version of each module" and required
versions "are minimum versions and may be increased automatically", so a `require` cannot
cap a non-leaf dependency.

*The correction:* the brief said "to actually cap, you need `replace` **or** `exclude`". The
reference says an excluded version's requirement is *redirected to the next higher version* —
`exclude` moves selection **up**, so it cannot cap either. Shipping the sentence as written
would have taught a wrong remedy. **Only `replace` caps**, and that is what §4 now says. The
floor half is kept, because it is the half that makes the rule useful: raising a `require` is
the correct way to force a CVE fix, and it goes inert once upstream requires it anyway.

**Adopted #4, with its own premise corrected — pin while the pin is still a no-op.**
Folded into rules/03 **§3.7.1** rather than given its own subsection, on the 500-line cap
(see below). The idea: pin when the pinned version is already what resolves, so the pin is
provably inert and no later regression can be blamed on it; prove it with an SBOM diff;
never pin and upgrade in one change; and read the version from the resolver that will
actually run (`proxy.golang.org/<module>/@latest`) rather than GitHub `releases/latest`,
which answers a different question.

*The premise that failed:* the brief called this "the same reasoning as one-variable-at-a-time
elsewhere in the library". It is not — `one variable at a time|change one thing|confound|two
changes at once|isolate the change` returns **0 hits across all 42 skills**. The reasoning it
appealed to does not exist here, which made the proposal slightly *larger* than advertised,
not smaller. Stated explicitly in §3.7.1 rather than cited.

**Rejected: already ours — three, reported by the brief as signal rather than proposals.**
`sota-devsecops` rules/03 §3.9.5 (`03-dependencies.md:389-391`, the recent-push/stale-release
rule) fired verbatim in the field; `sota-code-security` rules/15 §2.1
(`15-instruments-and-guards.md:96-108`, a probe that exercises a neighbouring property)
covers the `curl -H "Host:"` case, where the header does not set TLS SNI so a `000` measured
handshake rejection rather than the service; and router principle 3 (a negative claim needs
more proof) is what caught all three of the brief's own probes, each of which failed *toward*
a false negative. No change to any of the three. The SNI case is offered in the brief as a
candidate transport-layer example for §2.1, whose examples are all artifact-shaped — not
taken here, because §2.1 is already at the length where an added example costs more than it
teaches.

**Landed:** `sota-devsecops/rules/03` §3.7.1, `sota-devsecops/rules/09` §6, and
`sota-golang/rules/07` §4, each with its audit-checklist half in the same change · v1.35.2

**A note the cap forced.** `03-dependencies.md` was at 451/500 and is now **487**. That
decided two placements in this change — the watcher rule went to rules/09 (343 → 394) and
Proposal 4 lost its own subsection — and it is the second consecutive session in which the
cap, not the argument, chose where text lives. The offload is §3.9 (the inert-dependency
sweep, ~167 lines), and it is deliberately **not** bundled here: 42 references to `§3.9`
exist outside the file, and mixing a split with an adoption makes both harder to review.
Opened as a roadmap item.

### 2026-09-08 — the agent's own tooling as an attack surface, from two independent sources

Two intakes landed together because they turned out to be the same subject approached from
opposite ends: a **field brief** from a session that used this library on an unrelated
repository and then had an incident there, and a **review of [trailofbits/skills](https://github.com/trailofbits/skills)**
(83 skills, 7.0k stars, requested by the operator). Neither knew about the other; both are
about what an *agent's own tooling* does to controls the rest of the library assumes.

**Licence, checked before anything was planned.** `trailofbits/skills` is **CC-BY-SA-4.0**
(read from the GitHub API, not the README). Share-alike is **incompatible with this
library's CC BY 4.0** for text reuse, so this intake takes **idea classes only** — no
wording, no examples, no tables carried over. Same rule as the unlicensed-source cases
above, reached by a different route: there the text could not be taken because nothing
granted it, here because taking it would relicense us.

#### From the field brief — both proposals adopted, both reframed

**Adopted with a correction — never-persist-raw** (`sota-secrets-management` rules/03
**§2.1**). The brief's argument is right and was absent: redacting types need producer
control, so for **text whose producer you do not own** — a swept corpus, shell history, a
crash dump, an agent transcript — the guidance silently degrades to shape-scrubbing alone,
and shape-scrubbing is an enumeration. Its evidence is the strongest kind: a shape-redaction
fix that **its own regression test defeated on the first run** (a GitLab PAT and a Slack
webhook URL), and later a Vast.ai key that is **bare 64-character hex with no prefix at
all** — unmatchable by any prefix rule, and inseparable by a generic entropy rule from a
hash, a UUID or a minified bundle. The rule now says: persist a digest plus a structural
skeleton, and it states the shape channel as a real if narrow disclosure rather than
claiming zero leak.

*The correction:* the brief described the library as having **two** tiers and asked for its
rule to be inserted "as item 3". The list has **three** — item 3 is already a *never log*
category rule (full env, full headers, connection strings). They had read lines 56–60 and
the list continues past them. The new tier is item 4 with its own subsection, and the
argument is stronger for it: item 3 is *also* an enumeration, just of categories rather
than shapes.

**Adopted with a correction — the agent session transcript is a credential store**
(`sota-secrets-management` rules/04 **§7**). Verified observation, not inference: a harness
loaded a repo's `.env` into context under a header claiming *"project instructions, checked
into the codebase"*, and each clause was falsified with a command — untracked
(`git ls-files --error-unmatch`), gitignored (`git check-ignore -v`), no `@`-import, mode
`600`. Four live keys then sat verbatim in `~/.claude/projects/**/*.jsonl`. The rule covers
what no checklist carries: inventory the path, scope the scan before running it, treat any
tool that reads the directory as a secret-processing tool, and note that **a tool whose
input path is outside the repo has a surface that changes with no commit to the repo**. It
also carries the brief's own severity discipline — owner-only to owner-only on one machine
is an expanded surface, **not** a disclosure — because the same arc had already ordered one
unnecessary rotation by reading a scanner's rule *names* instead of its *values*.

*The correction:* the brief reported that **nobody** covers this, from a `grep -li
transcript` that returned five files. `rules/04`:149 — **the very file it proposed** —
already said "AI tool transcripts", in the leaks-outside-git runbook. Its own sweep missed a
hit in its own target, which is the sandbox-filtered-recursion fault the brief itself
documents in its §5, biting a third time in one session. So this shipped as *extend the
existing clause* (which now points at §7) rather than as a new orphan section — the
`UNREACHABLE, not absent` shape once more, here at one clause's distance rather than one
skill's.

**Two further corrections to the brief's framing**, recorded because they change how the
next one should be read. Its §1 concluded the installed tree is "a build artifact" with an
upstream repo somewhere; `~/.claude/skills/` is in fact **41 symlinks into this repo**, so
it was reading live current files — better for the proposal than it claimed. But one
directory has **no symlink**: `sota-skill-security`, added in v1.35.0 the same day. Its
41-directory sweep therefore ran with the single most relevant sibling excluded — the skill
that owns *anything an agent loads as instructions*, which is precisely the mechanism of its
own P2. **An install that is 41 of 42 symlinks is a coverage claim's denominator, and
nothing reported it.**

#### From trailofbits/skills — one defect of ours, three additions

**The finding: a rule of ours is unsafe at a sink it does not name.** `sota-devsecops`
rules/01 §1.5 teaches `env:` indirection as *the* fix for expression injection. That is
correct for a **shell** sink — the value stops being script text. It is not a fix for a sink
that consumes the value as **instructions**: an AI-agent prompt, a template engine, an
`eval`, an LLM tool-call argument. Reachability is unchanged, and the `${{ }}` that
reviewers and `zizmor`/`actionlint` key on is *gone*, so the dangerous configuration now
reads as clean YAML. §1.5 now names the sink class its defence neutralises. This is the
highest-value shape in the ledger — an external source identifying a rule of ours that
*causes* the miss — and it arrived from a repo review rather than a field brief.

**Adopted: AI coding agents are CI actors holding your token** (`sota-devsecops` rules/01
**§1.5a**). Zero coverage, confirmed by reading after a corrected sweep: triggers a
non-collaborator can fire, following the value rather than the syntax, tool allowlists
judged by what their members *compose* into rather than by name (`echo "$(env)"`), sandbox
and auto-approve flags read as the control they are, and agents invoked two `uses:` levels
down spending the caller's token.

**Adopted: constant time is a property of the emitted code** (`sota-code-security` rules/04
**§6.1**). The library already had the *wiping* half — `memset` is dead-store-eliminated, so
`explicit_bzero` exists (`sota-c-cpp` rules/04 §4) — and never generalised it. Secret-
dependent `/` and `%` lower to variable-latency instructions; "I made the divisor constant
so it strength-reduces" is a hope, since that is an optimiser courtesy that varies by
compiler, target and level, and `-Os`/`-Oz` are both the levels that betray it and the
levels shipped binaries use. So: read the disassembly across the matrix you ship, and verify
a hand-written multiply-shift over the **whole input domain** — an off-by-a-power-of-two
reciprocal agrees for millions of inputs before it diverges.

**Adopted: a scanner's default configuration can exclude its most valuable detector**
(`sota-code-security` rules/15 §2.2). Distinct from the threshold *you* chose being too
coarse (`sota-devsecops` rules/09 §6, landed 2026-09-07): here you chose nothing and the
silence is the vendor's — a default run that is quiet about early-exit MAC comparison, the
most common real timing bug. Print the effective configuration beside the verdict and name
the detector families that did not run.

**Rejected: already ours.** Their `variant-analysis`, `fp-check` and `second-opinion` are
our `sota/rules/01` §4 re-audit sweep, `rules/03` §4 refutation, and the independent-refuter
rule respectively. `supply-chain-risk-auditor` is `sota-devsecops` rules/03. `insecure-defaults`
is covered by the no-fallback-secret rule (`sota-secrets-management` rules/03 §1).

**Deferred, with the trigger written down** — two classes that survived a coverage check but
need a read this intake did not have room for:

- **RESOLVED 2026-09-09 (was deferred): `sharp-edges` — misuse-resistant API design as a
  control you *own*.** The trigger was met and read: `sota-code-security` rules/14 §6a and
  rules/02 already hold the substance, so it is **rejected as new material and adopted as a
  pointer** in `sota-api-design` rules/01 §13, where an API is designed. Original reasoning
  kept below.
- **`sharp-edges` — misuse-resistant API design as a control you *own*.** Their framing
  ("the pit of success"; secure use is the path of least resistance) exists in our library
  **11 times as a consumer-side heuristic** — *choose* a misuse-resistant library — and, on
  a file-level sweep, **not in `sota-api-design` at all**. Revisit condition: read
  `sota-api-design` rules/01 and rules/07 in full and confirm the producer-side rule is
  genuinely absent before writing it. Do not adopt their rationalisation table's text.
- **RESOLVED 2026-09-11 (was deferred): `vulnerability-triage-brocards` — triaging an
  *incoming* report. The trigger was executed and the gap is REAL.** rules/04 was read in
  full (131 lines, all five sections and the checklist). It carries the CVD **obligation** —
  *"a published intake (`security.txt`, a disclosure address/portal) and a documented
  handling process"* under Annex I Part II — and the **outbound** Article 14 clocks (24h
  early warning / 72h notification / 14-day and 1-month finals). It does **not** carry the
  discipline in between: how to decide whether an inbound claim is real, reproducible,
  in-scope and exploitable. That is not a cosmetic hole, because Article 14's clock runs from
  **awareness**, and an unresolved inbound report is exactly the state where "are we aware
  yet?" is undecided — the file's own line *"a clock that depends on someone happening to
  notice is already blown"* names the failure and stops one step short of the process that
  prevents it. Confirmed absent from rules/03 (SSDF) as well, whose four practice groups
  cover *having* a disclosure process, not running one. Opened as **ROADMAP item 50** and **written the same
  day** as `sota-security-compliance` rules/04 **§3a**, with its audit-checklist half and the
  `SKILL.md` front-door row; item 50 is closed · v1.40.2 It was tracked before it was written
  precisely so it could not become the thing this log exists to prevent — an idea judged
  real and then quietly untracked. **Licence note that constrains the writing:** the
  source is CC-BY-SA-4.0, so idea classes only — and in the event none is needed, since the
  gap above was derived from reading our own rules/04, not theirs. Original reasoning kept
  below.
- **`vulnerability-triage-brocards` — triaging an *incoming* report.** Our coverage of
  coordinated disclosure is the *obligation* (`sota-security-compliance` rules/03 and
  rules/04 under SSDF and the CRA); the triage discipline for a report someone else sent you
  — a CVE claim, a bug-bounty submission, a finding from an agentic discovery pipeline —
  was not found. Revisit condition: confirm against `sota-security-compliance` rules/04 that
  the CRA's reporting obligations do not already carry it.

**Landed:** `sota-secrets-management/rules/03` §2.1 and `rules/04` §7,
`sota-devsecops/rules/01` §1.5 and §1.5a, `sota-code-security/rules/04` §6.1 and
`rules/15` §2.2, with cross-references from `sota-code-security/rules/08` and
`sota-skill-security/rules/02`, each with its audit-checklist half in the same change · v1.36.1

### 2026-09-08 — the early stage's green light, and deleting a fallback safely

Sixth field brief in this series, from removing an orphaned CI CronJob and repairing the
monitoring gap that had hidden it (self-hosted Kubernetes, Argo Workflows, VictoriaMetrics).
**All four proposals adopted**, plus the minor it offered without one. It also opens by
confirming the previous intake's verdict from the outside: pointing its watcher proposal at
`sota-code-security` rules/15 §2.2a rather than restating it was right, *and the reason it
missed that section is the reason the note gives — it lives in a skill that workflow never
loads*. That is the **UNREACHABLE** diagnosis being confirmed by the person it was made about.

**Every 0-hit check reproduced**, run with an array and a positive control (285 files
matching a string known to be present) rather than an unquoted expansion — the discipline
`sota-shell-scripting` rules/01 §3 got sharpened for the day before.

**Adopted #1 — the stage that reports success is not the stage that failed**
(`sota-code-security` rules/14 **§4b**, sibling to §4). §4 is a control whose *trigger never
fires*; this is a control that ran, failed, and said so in a field nobody read while a
different field on the same screen read as success. `total active targets: 144 /
workflow-controller targets: 1` reads as working; the next line was `health=down`. **The
earliest stage's signal is the one that looks like a summary**, because it is a count and it
renders first — and the split generalises well past metrics: enumerate-vs-process,
connect-vs-authenticate, resolve-vs-fetch, schedule-vs-execute, register-vs-invoke. Its
corollary earned its own bullet: **repairing an inert control needs an output delta, not a
green light** — three affirmative signals were green while nothing was collected, and only
`0 → 54` series separated repaired from broken. Cross-referenced *against*
`sota-observability` rules/05 §7a rather than merged with it: §7a is the case where the right
instrument does not exist and a proxy answers a neighbouring question; here every instrument
existed and was correct, and the reader stopped at the first affirmative one.

**Adopted #2 — the sharpest of the four, because it corrects a rule shipped the day before**
(`sota-devsecops` rules/10 **§3a**, plus a clause in §6 bucket A). `rules/10` — created
2026-09-07 — proves a candidate unreached and deletes it on that evidence. Sufficient for a
dependency, whose job is to be *called*. **Not** sufficient for anything whose job was to be
*available*: **unreached is exactly what a healthy fallback looks like**, so the deletion
proof returns the same green for "safely obsolete" and for "the safety net nobody has needed
yet". The field case decided on a different question entirely — the orphaned cache was
deletable only because the registry mirror that replaced it was 3.3 hours old, inside its
24-hour refresh window; **had it been stale the correct action was the opposite one**, and
the "dead" cache was the only thing between a stale advisory DB and a green scan gate. The
rule now demands the successor be named and measured this session, or the finding is KEEP.
Note the brief also spotted that `successor` appeared in `rules/10` only for naming a
maintained fork (§6 bucket D) — a good read of our own text.

**Adopted #3 — two config traps that make a correct-looking observability change collect
nothing**, split across the two files that own the mechanics. **A port declaration does not
state the protocol spoken on it** (`sota-observability` rules/02 §7): a container advertising
`metrics:9090` says nothing about TLS, and scraping HTTP where HTTPS is served returns
`400 Client sent an HTTP request to an HTTPS server`, which reads as a broken exporter. Probe
both ways first; where the certificate is self-signed by the component's own issuer no CA
bundle can verify it, so skip verification *explicitly and with the reason written beside the
flag*. And **what you wrote is not what lands** (`sota-kubernetes` rules/04 §7a): a
transformer can override the `namespace:` in your manifest, after which a namespaced lookup
returns nothing — which reads as *"never applied"*, not *"wrong place"*. Render and grep the
render; `kubectl get <kind> -A` before any absence claim.

**Adopted #4 — an N-of-N correlation across the whole population is still not a mechanism**
(`sota/rules/03` §2, placed immediately before the existing N-of-N material). This is the
placement that matters: §2 already says *"a reproduction you ran once is a coincidence you
have not ruled out"* and asks for N-of-N, so a reader could reasonably carry that authority
across to a *correlation* — where it does not hold. Repeating an **observation** N times
bounds noise; observing that N members **share a property** bounds nothing, because you have
not touched the thing that would implement it. 8 of 8 working scrape objects sat in one
namespace and the only one elsewhere collected nothing — a perfect correlation, and the
inference from it was wrong; one query against the collector's target list refuted it. Named
as the population-level twin of `sota-code-security` rules/15 §2.1 ("generalised from one
sample"), which is how the brief framed it.

**Adopted — the minor, offered without a proposal.** GitOps prune-by-omission: the functional
deletion of a managed object is removing it from the *rendered set*, not deleting its files.
Landed as the third bullet of `sota-kubernetes` rules/04 §7a, because it belongs with "what
you wrote is not what lands" — and it carries a corollary the brief did not draw: an object
can be **functionally gone while its manifest is still in the repository**, which is a
false-negative for anyone auditing by file.

**Evidence strength, recorded as the brief itself framed it** — this is why the log has a
verdict column rather than a checkmark. #2 rests on **one case that turned out fine**, which
is weaker than an incident: the reasoning is general, the failure was not observed. #4 is a
**near-miss caught before acting**, not a defect that shipped. #1 and #3 come from a single
monitoring stack; the *shape* of #1 generalises to any discovery-then-collect pipeline, the
specifics of #3 are Kubernetes-flavoured and are placed in the Kubernetes and observability
skills accordingly rather than promoted anywhere cross-cutting. **None of the four met the
two-independent-sources bar for a cross-cutting home, and none was given one.**

**Landed:** `sota-code-security/rules/14` §4b, `sota-devsecops/rules/10` §3a + §6 bucket A,
`sota-observability/rules/02` §7, `sota-kubernetes/rules/04` §7a, `sota/rules/03` §2 — each
with its audit-checklist half in the same change · v1.36.3

### 2026-09-08 — a status can be true of the wrong subject, and the commands you type to check

Two intakes, landed together because they are the same failure at two altitudes: a
**proposal** from a static-analysis repo (six false OKs in one session, each measured), and a
**field report** from a detection-engineering session (three items and a sharpening). Both
are about statements that are *correct* and still mislead.

**Adopted — the general rule** (`sota/rules/03` §2). The evidence standard already says to
validate a claim against a primary source. This adds: **validate what the claim is ABOUT.**
Every one of the six instances was literally true — *"exit 0"* of the wrapper, *"no
advisories"* of the database that was opened, *"the harness returned no result"* of a
container that never started, *"38,861 passed"* of the tree fifty minutes earlier. 0 hits for
`name the subject|what the OK is about`, confirmed with a live control. This is not the
semipredicate problem: the value is unambiguous and the **subject** has quietly shifted, so a
reader cannot detect it by looking harder at the number.

**Adopted — the six instances, placed by mechanism rather than kept together:**
`sota-shell-scripting` rules/01 **§2a** (a background job's completion signal is about the
launcher — measured at 17 seconds into a 41-minute run, and the two shell-level rules we had
are both about *your* shell, not the orchestration layer that reads the result);
`sota-code-security` rules/13 **§6** (an empty result that never names its store — 6,491
advisories in one SQLite file and every default reader opening another, proven by the same
call returning **13** and **0**); `sota-testing` rules/04 **§4.8** (a harness that could not
start is indistinguishable from one that found nothing, and only the second is a conclusion
about the target); `sota-testing` rules/07 **§7.7** and **§7.8** (a long run is scoped to the
revision it started from, and *when a ratchet fires the fix is never to re-record it* — the
failure message offers exactly the action that destroys the signal); `sota-devsecops`
rules/07 **§7.7** (prune/`fstrim` on a shared runtime is a change needing a restart and a
smoke test, plus enumerate foreign-owned resources first).

**Adopted — the field report's three, and its sharpening:** `sota-shell-scripting` rules/06
**§3** (an ad-hoc command can *destroy* what it was checking — 40 GB copied into a container
on a host at 99%, cascading into a corrupted runtime and ~64 GB of lost images; we covered
ad-hoc commands producing false findings and never producing damage);
`sota-detection-engineering` **§8** (provenance, and **separating the attack's mechanism from
the author's instrumentation** — a rule keyed on a paper's `.payload` name and printed marker
detects the demo; 0 hits across all 8 files for `provenance|cite|arxiv|demo|scaffold`, control
live); `sota-code-security` rules/14 **§8** (a *real* control reverted by a neighbouring
automated step into a state that is legitimate in another phase — "timestamped only" is
correct between releases, so only `--require-signature` separated them). It went to rules/14
rather than rules/10 because **rules/10 had 16 lines of headroom** and cramming it there
would have been the cap choosing the placement again.

**The sharpening was measured rather than accepted, and it got sharper.** The report proposed
strengthening "verify absences" to "control the search with a term known to exist, **in the
same invocation**", and warned that `grep -r` is wrong for trees containing symlinks. Both
hold, with precision the report did not have:

- `-r` skips symlinked directories **met during traversal**; `-R` follows them; a symlink
  passed *as the argument* is followed by both. So it is the **nested** case.
- **Tool choice is not the fix.** On one tree with four matches: `rg` defaults found **1**,
  the environment's `grep` found **3**, explicit flags found **4**. Swapping to ripgrep would
  have made the under-report *worse*.
- **The `grep` in that environment was a shell function** running `ugrep -G --ignore-files
  --hidden -I --exclude-dir=.git …`, except that any `-z`/`-Z` argument was routed to
  `command grep` — **BSD grep**, where `-z` means null-data rather than *search archives*. So
  `grep --version` and `command grep --version` named different programs and one flag decided
  which ran. Read from the wrapper's definition, not inferred.

That is why the rule shipped as **name your searcher, its flags and its exclusions in the
same sentence as the count**, with a capability note (ugrep's `--bool`, verified working;
`rg`'s speed and gitignore defaults; `ast-grep` for constructs regex cannot see) rather than
a recommendation to install anything.

**Rejected — "check whether ugrep is installed" in `verify-setup.sh`.** A presence check is
the wrong shape: the library requires no searcher, and a check that is routinely N/A for a
non-problem is the kind people learn to skip. The idea nonetheless passes all three of
[CONVENTIONS-LEDGER](CONVENTIONS-LEDGER.md)'s filters — it has already failed twice this
week, it fails silently, and it is mechanically checkable — so it is **ROADMAP 45** as a
*behavioural* probe to be decided, not dismissed.

**Found while landing this, in our own text:** the v1.36.3 checklist edit to `sota/rules/03`
had merged two lines into `…file:line@commit,**Finding quality**` and duplicated the bullet
below it. It shipped. Repaired here — a scripted insert whose replacement text contained its
own anchor, which is the class of bug that only re-reading the file catches.

**Landed:** `sota/rules/03` §2, `sota-shell-scripting` rules/01 §2a + new **rules/06**,
`sota-code-security` rules/13 §6 and rules/14 §8, `sota-testing` rules/04 §4.8 and rules/07
§7.7–§7.8, `sota-devsecops` rules/07 §7.7, `sota-detection-engineering` rules/01 §8 — each
with its audit-checklist half in the same change · v1.38.0

### 2026-09-12 — private-project field report II: a retraction of report I, and three new findings

`FIELD-REPORT-PRIVATE-2026-09-12.local.md`, same session as report I, filed as a separate
document **specifically because report I was already being implemented** — which it was, in
an open PR, when this arrived. That is the right call and worth naming: an addendum appended
to a document someone is working from does not reach them.

**RETRACTION, and it landed in time.** Report I's *"invoke a linter with the project's own
flags"* proposal was **wrong**, and the reporter found it themselves. `sota-devsecops`
rules/09 §5 — *"The scoped gate is not the gate — reproduce the invocation, not an
equivalent"* — already states it better, with a reproduced mypy example and the three levers
that produce divergence. Verified here before acting. The clause had already been written
into `sota-shell-scripting` rules/03 §7 and was **removed**, replaced by a one-line
cross-reference to the skill that owns it. Two homes for one rule is how they drift.

**The reviewer's share of that mistake, recorded because it is the more useful half.** This
library's intake procedure says to verify a claimed gap before adopting, and it was verified
— *within the file the report named*. What was never asked is **which skill owns the topic**.
A keyword search for the reporter's phrasing ("project's own flags") returns nothing from a
library that covers the idea thoroughly under different words. **A negative claim about the
library needs the same positive control as a negative claim about a codebase**: identify the
owning skill and read its section headings before concluding nothing covers it. Report I was
scrupulous about this for the codebase (`rg --follow`, positive control, because
`~/.claude/skills` is 42 symlinks) and failed at it for the library; so did the review.

**Adopted — `sota-code-security` rules/15 §3a: the guard that correctly declines, and says
nothing.** Verified absent (rules/10 catalogues *inert* controls; rules/11 covers paths never
reached; nothing covers a branch that is reached and mute). A stray editor `.swp` file made
one conjunct of a three-clause guard false, so a clean 23-of-23 gate run wrote **no evidence
record and printed nothing** — in a ledger whose whole purpose is telling a gated commit from
a `--no-verify` push. **The fixes are opposites**: an inert control must start enforcing,
this one must keep refusing and start explaining. Review tell: a multi-clause `if` with no
`else`.

**Adopted — `sota-devsecops` rules/09 §4: a warning on a *passing* run needs its transport
verified.** §4 was about failure diagnostics dying with an ephemeral executor; this is the
worse case, because **every wrapper that suppresses output suppresses it on success**, and a
warning is by definition emitted on a run that otherwise passed. Verified here against the
installed **pre-commit 4.6.0** rather than the report's word:
`pre_commit/commands/run.py:217` reads `if verbose or hook.verbose or retcode or
files_modified:`, so a seventeen-minute twenty-three-gate run reaches the terminal as the
word `Passed`. The constructive half is kept: the problem was found by a **durable
artifact** (a ledger query), which is an argument *for* §4's thesis.

**Adopted — `sota-shell-scripting` rules/06 §2b: an empty command substitution removes the
filter.** Verified absent. `ps -p "$(pgrep …)"` with no match expands to `ps -p ""`, which
ignores the filter and prints **every process**, exit 0. Quoted correctly, so not SC2086.
It is the mirror of §2/§2a's distrust-an-absence material — **an implausibly large result is
the same tell as a suspiciously clean zero** — and is placed beside them for that reason.

**Cap pressure, recorded rather than absorbed.** The natural home for the declining-guard
rule was `rules/10`, at **484 of 500 lines**. Putting it there would have let the line cap
choose the shape of the writing, which this library has now watched happen twice, so it went
to `rules/15` §3 (guards) instead. That is the **second** class queued behind a rules/10
split — the over-firing control deferred on 2026-09-11 is the first. Opened as **ROADMAP 55**.

**Report I's other four proposals stand unchanged** and are recorded in the entry below.

**Landed:** `sota-code-security/rules/15` §3a, `sota-devsecops/rules/09` §4,
`sota-shell-scripting/rules/06` §2b, and the rules/03 §7 retraction — each with its
audit-checklist half and index rows in the same change · v1.40.4

### 2026-09-12 — private-project field report (2026-09-11): six adopted, one corrected, one later retracted

`FIELD-REPORT-PRIVATE-2026-09-11.local.md`, untracked by the same convention as its three
predecessors — this repo is public, the product it describes is not. A session building
changed-path gate selection and a hash-chained evidence ledger, which produced **six harness
errors and zero product defects**, and noticed that the six were one class.

**Every coverage claim was re-verified here before adopting**, with `git grep` over the
tracked tree rather than the reporter's `rg --follow` over symlinks — a different failure
mode, which is what operating principle 3 asks for — and a positive control in the same
sweep. All held except one, corrected below.

**Adopted — `sota-code-security` rules/15 §2.1, a sixth failure mode, and the one that
matters.** The five there describe instruments that are *durably* wrong (generalised from one
sample, cannot fail, exercises a neighbouring property). None described **the temporal
asymmetry**: during verification the harness is almost always *newer* than the subject, so the
prior belongs on it — and rarely lands there, because a harness fault and a real finding
arrive through the same channel, a red result. The load-bearing half is the tell: **not that
the result is red, but that it is implausible.** Two of the six produced a *red self-test on
correct code*, the most expensive false signal available when the artifact under construction
is a control whose own failure mode is silence. Heading renamed Five → Six (checked: the
phrase appears nowhere else).

**Adopted — `sota-shell-scripting` rules/06 §2a: `rg -r` is `--replace`.** Verified absent (0
hits for `rg -r`; the single `--replace` hit is `git filter-repo` in
`sota-secrets-management`). It is the `grep -r` symlink trap **inverted**, which is why the
reflex survives: `grep -r` fabricates a false *absence*, `rg -r` fabricates false *content* —
real lines, real paths, every match rewritten to the next argument, exit 0. The reporter hit
it twice in one session **after writing it into their own rules file**, which is the evidence
for §2.1's "budget for noticing an implausible result, not for remembering the trap".

**Adopted — rules/05 §3a: sourcing a script to test one function relocates it.** `BASH_SOURCE`
appeared **zero** times across all 41 skills. Both obvious moves fail and the *second* is
silent: sourcing a copy puts `BASH_SOURCE` in the scratchpad, the script's own
`cd -- "$REPO_ROOT"` moves you out of the repository, and every `git` call in every function
then fails — emitting a correct, well-written diagnostic about healthy code. Recommended fix
is in the script (`[[ ${BASH_SOURCE[0]} == "$0" ]] && main "$@"`), not the test.

**Adopted with a correction — rules/04: killing a backgrounded build orphans its children.**
The report said "nothing in a shell/ops context". **Not quite**: `rules/05` §3 already carries
`trap 'trap - TERM; kill -TERM -- -$$'`. But that is the *inside-the-script* frame — a script
forwarding a signal to its own group — and the reporter's case is an operator killing a
background job from outside, which is a different reach even though it is the same mechanism.
Recorded as **present but unreachable**, and the new text cross-references rules/05 rather
than restating it. The consequence is the adoptable part: an orphaned compiler contends for
`target/` and **the next run's failure is attributed to the change under test**.

**Adopted — rules/12 §1: the commonest cause of "the mutation did not take".** The bullet
listed editable installs, copied trees, stale bytecode, cached images and formatter reflow —
all environmental. The commonest cause for anyone scripting a mutation is that **the
substitution matched nothing** (a regex that misses, a `sed` delimiter colliding with the
pattern). Its fix is also *stronger* than the existing one and is now given first: assert the
pattern is present **before** writing, which fails at mutation time rather than at
interpretation time.

**Adopted — router principle 7.** It said "your earlier prose in this session is not a primary
source". It now adds: **neither is a verbatim copy of a file injected into context earlier in
it.** A quoted file reads as primary evidence in a way a summary does not, which is what makes
it the easier mistake. Note for future edits: principle 7 sits **inside** `principle5()`'s live
extraction in `run-completeness.py`, so this text flows into the completeness treatment arm by
design.

**Adopted, then RETRACTED the same day — the first of the two "marginal" rules/03 §7 items.** (See the report II entry above: `sota-devsecops` rules/09 §5 already owns it, and the clause was removed.) The second item stands.

**Superseded text, kept for the reasoning:** §7's example
prescribes `shfmt -d -i 2 -ci .`; in a 4-space repo, with `-w` usually nearby, a contributor
copying it verbatim **reformats every shell file in the tree**. The rule now says to reproduce
the gate's own invocation and marks the example as an example. The second item supplies the
missing *reason* for `--severity=style`: SC2006 is classed style and catches backticks inside
an unquoted heredoc, where they are live command substitution in help text.

**Recorded, not adopted as a rule — the checklist-over-narrative observation (report §7).**
rules/15 §2.1's fixture-vs-runtime-artifact bullet found a real latent defect in a
security control that had been green since it was written: a ledger self-test that hashed a
committed vector and **never called the encoder that writes records**, so reordering two
`printf`s would have left every check green while every new record diverged from the vector
pinning it. The detail worth keeping: that repo's own `AGENTS.md` *already warned* the gate was
"precise about the wrong thing", accurately, and had been read many times. It took applying the
rule as a **procedure** to convert the warning into a found defect. That is evidence for the
audit-checklist form over the narrative form, and it is why the checklist half of every
adoption above was written in the same change.

**Not proposed, and agreed:** no new skill, no change to the `grep -r` symlink material, no
routing-table change — router rule 17 fired correctly and is what found the ledger defect.

**Landed:** `sota-code-security/rules/15` §2.1 + `rules/12` §1, `sota-shell-scripting/rules/03`
§7, `rules/04`, `rules/05` §3a, `rules/06` §2a, router principle 7, each with its
audit-checklist half and its `SKILL.md` index row in the same change · v1.40.4

### 2026-09-11 — MadAppGang/magus, a Claude Code plugin marketplace: two adopted, one deferred, one item opened, the rest already ours

Reviewed at the operator's request. **Licence checked first, from the GitHub API rather than
the README: MIT** — permissive, so unlike the CC-BY-SA-4.0 intakes above there is no
text-reuse constraint. None was needed anyway; both adoptions are written from our own
measurements. Source: [MadAppGang/magus](https://github.com/MadAppGang/magus), 15 plugins,
416 markdown files, `skills/skill-authoring/` the directly-comparable artifact.

**Provenance caveat, checked rather than assumed.** Its strongest claims cite evidence the
repository does not publish: `benches/skill-index/` (the "IDX-1" measurement behind *"say
read this file, never invoke this skill"*) does not exist, and neither do
`scripts/skill-budget-check.ts` nor `scripts/dev-skill-inventory.ts` — two of the three
commands its own *"Before reporting done"* block tells a reader to run. Not gitignored;
absent. That does not make the guidance wrong, and much of it is very good, but it means the
measured claims cannot be reproduced from what ships — so they are recorded below as
**unverified**, never asserted. Its README is also heavy unsubstantiated marketing
("$2.3M in value", "zero rollbacks"); ignored, and a reminder of `sota-copywriting`'s
claim-substantiation rule.

**Adopted — a description length cap is enforced in one of two shapes, and they need
different checks.** `sota-skill-security` rules/03 §1 said *"exceeding it can make the loader
skip the skill entirely… do not assume truncation"* — correct as far as it goes, and it
frames **skip** as the failure while warning against assuming the other one. magus argues
Claude Code does the opposite: it **silently shortens** descriptions, so the skill loads and
the matcher only ever saw the surviving prefix. We now name both shapes, say they are
indistinguishable from the inside, and give the check for each (a skip is *did it load at
all?*; a truncation is *compare the text the model got against the file*). Two corollaries
came with it and are the practically useful part: **order the description capability-first**,
because that is free and works before you know which shape applies, and — where the listing
budget is **global across everything installed** — *your* matching degrades because of
*someone else's* bloat, which makes "it stopped triggering and we changed nothing" a corpus
symptom rather than a bug in the skill that went quiet.

**Adopted — prove the description separately from the body, and keep the arm that tells you
to delete.** New `rules/03` §1a. Run the same task twice, model-routed and invoked **by
name**: named works / routed fails is the *description*; both fail is the *body*. We had the
two instruments (`run-desc-routing.py`, `run-completeness.py`) and had never written the
diagnostic down, so the two defects stayed easy to mistake for each other. The half worth
more than the diagnostic is the **no-skill baseline** kept in the comparison: it is the only
arm that can say a skill has stopped earning its tokens, and *"worse than baseline → cut
it"* is a disposal rule this library has never had — in four months it has never removed
guidance on evidence. It also lands on a clock we already believe in: base models improve
underneath a skill, which is [measured-claims-expire](ROADMAP.md) seen from the content side
rather than the number side.

**Adopted in the same section — routing is the wrong mechanism for a requirement.** *"If a
workflow genuinely requires 100% invocation, use a hook or a validation gate."* One sentence,
and it is the general rule behind a choice **ROADMAP 48** is currently parked on (whether
the per-task-shape re-route belongs in the router body or the re-injection hook). Description
matching is a classifier and classifiers have a false-negative rate; that is fine for depth
and not fine for anything security-, safety- or compliance-relevant.

**Opened as ROADMAP 52, not adopted — the budget arithmetic is about us.** magus states the
listing budget as `context_tokens × 4 × fraction (default 0.01)`, verified against Claude Code
**2.1.223**. This machine runs **2.1.268** and the CLI is bundled inside another application
where the binary could not be located, so **the formula is unverified here**. What we did
measure is ours: **37,330 characters** across 42 descriptions, **40 of 42** carrying a
`Trigger keywords:` tail at roughly the last 35% of the text, and — observed directly, not
inferred — those descriptions arriving **complete** in a 1M-context session (two tails
compared byte-for-byte against disk). If the formula holds, 1M gives a 40,000-char budget we
fit with ~7% headroom and 200k gives 8,000, where we are **4.7× over** and the trigger
vocabulary is the first thing cut. That is too consequential to adopt on an unreproduced
claim and too consequential to drop.

**ADOPTED 2026-09-21 as `sota-code-security` rules/10 §5 + two checklist items — the
over-firing control.** *The trigger fired and nobody came back.* It was parked on
*"rules/10 is at **484/500** and putting it there would let the line cap choose the
placement"*; ROADMAP 55 split the file on **2026-09-12**, taking it to **230/500**, and
the deferral sat unread for nine days with its stated blocker false. Found by a
`/sota-resume` pass re-testing each deferral's TRIGGER rather than its subject.** magus's search-redirect hook documents a failure mode we
cover only in one direction. Ours is the inert control that looks enabled and does nothing
(rules/10). Its mirror is a control that fires **too broadly**, degrades the outcome it was
meant to protect, and *appears to work the whole time* — their reviewers' point that a
blanket grep-deny enforces worse behaviour, because ripgrep genuinely beats an index for a
literal you can already spell. Real, and not placed today on purpose: rules/10 is at
**484/500** and putting it there would let the line cap choose the placement, which this
library has already watched happen twice.

**Rejected — already covered, with the citation each time.** Most of its
`references/routing-eval.md` is practice we measure already: *run every prompt at least three
times, triggering is stochastic* (our noise-floor work — a null at n=1 is not a null);
*record model and harness, re-run after an upgrade* (`sota-skill-security` rules/02 §2, and
the whole measured-claims-expire result); *judges sharing an input share its defects, so
convergence is not corroboration* (router operating principle 3, which says independence must
mean a different **failure mode**); *periodically re-run the no-skill condition* (adopted
above only because we lacked the **disposal** half, not the observation). Also rejected: its
**250-character description ceiling**. It is coherent inside their architecture — per-plugin
routers with most skills hidden — and incoherent in ours, where 42 listed descriptions *are*
the classifier and there is no hidden tier to demote into. Adopting the number without the
architecture would delete trigger vocabulary and call it discipline.

**Landed:** `sota-skill-security/rules/03` §1 and new §1a, four audit-checklist bullets, and
the `SKILL.md` rules-index row · ROADMAP 52 opened · one deferral with its trigger · v1.40.2

### 2026-09-09 — the private-project field report in full, and one of its claims corrected

The full report behind the 2026-09-08 summary that landed in v1.38.0
(`FIELD-REPORT-PRIVATE-2026-09-08.local.md`, untracked by the same convention as its
predecessor — the repo is public, the product it describes is not). **Most of it was already
landed from the summary**; this entry records the four remainders and the one claim that did
not survive measurement.

**Adopted — router operating principle 3, and this is the one that matters.** The principle
already said a negative claim needs *"a second independent method"*. The report shows why
that is necessary and not sufficient: **both its methods were `grep -r`**, so both agreed on
zero and both were wrong, because `-r` does not follow symlinks met during traversal and
`~/.claude/skills/` is 42 of them. *"Independent" has to mean a different **failure mode**,
not a different phrasing.* The remedy is a **positive control in the same invocation** — a
term you have already seen there. This is a correction to an existing cross-cutting principle
that could otherwise license the wrong move ("I used two methods, so I am safe"), which is a
different and lower bar than promoting a new principle, so the two-independent-sources rule
does not block it.

**Adopted — three sharpenings the summary did not carry.** Build output is the trap for the
blast-radius rule (`target/`, `node_modules/`, `.venv/`, `vendor/` reach tens of gigabytes and
are exactly what a naive recursive copy takes — redirect output instead of copying), and **a
full disk is not a clean failure**: on a VM-backed runtime the guest disk is a sparse file on
the host's, so host exhaustion surfaces inside the VM as I/O errors that corrupt the
filesystem and image store, minutes later, in an unrelated command. For detections: **enforce
the citation** the way a runbook link is enforced, since optional provenance is absent by the
time anyone needs it; and **record what the rule cannot see** — the same paper that supplied
the technique described a wrapper variant evading all three of its own signals, and writing
that down is what stops the rule being credited with coverage it lacks.

**Corrected — "prefer `rg`, which follows symlinks by default".** It does not. Measured
2026-09-08 on a tree with four matches (plain, hidden, gitignored, behind a symlinked
directory): **`rg` defaults found 1**, the environment's `grep` found 3, and only
`rg --hidden --no-ignore --follow` found 4. Recommending ripgrep as the fix would have made
the under-report *worse*. The library text already says this correctly (rules/06 §2) because
it was measured before being written rather than accepted from the report — the same
discipline this log asks of every intake, applied to an intake that was right about everything
else.

**Placement differences, recorded so the reporter can see the reasoning.** Two of the four
went somewhere other than proposed: the blast-radius rule to `sota-shell-scripting`
**rules/06** rather than rules/03, because rules/06 was created in the same release for
exactly this class (the commands you type rather than commit) and rules/03 is about *secrets
and injection* in scripts; and the reverted-by-a-neighbour shape to `sota-code-security`
**rules/14** rather than rules/10, because rules/10 had **16 lines of headroom** and putting
it there would have let the line cap choose the placement — which this library has now watched
happen twice.

**Not proposed, and agreed:** no new skill, no change to the detection content (its
benign-baseline guidance was followed and the rule measured 0 false positives across 4,487
binaries in three distributions), and no change to the `.local.md` convention.

**Landed:** `sota/SKILL.md` principle 3, `sota-shell-scripting/rules/06` §3 *(now `rules/08` §3)*,
`sota-detection-engineering/rules/01` §8 — each with its audit-checklist half in the same
change · v1.39.0

### 2026-09-13 — private-project field report III: six adopted, one sharpened into two, one reported as evidence only

`FIELD-REPORT-PRIVATE-2026-09-13.local.md` — one session on a private cross-platform EDR
(Linux eBPF sensor, CO-RE across two kernels, a supported-platform matrix). Eight failures,
seven proposals. **Its framing is what makes it unusually useful: for four of the eight, the
relevant rule was already in context and was broken anyway** — so those four are evidence
about *rule shape*, not about coverage, and the report says so, including that its author's
own instinct ("add a clause telling me to check") is the thing that already failed.

**Every falsifiable external claim reproduced, 2026-09-13.** Seven of seven distro rows from
`endoflife.date` (Alpine 3.20 EOL **2026-04-01** vs current 3.24; openSUSE Leap 15.6 EOL
**2026-04-30** vs 16.0; Ubuntu 26.04 LTS; Debian 13; RHEL 10; kernel 6.17 superseded).
`MAX_BPF_STACK 512` at `include/linux/filter.h:100` and the verbatim verifier string
`"combined stack size of %d calls is %d. Too large"` at `kernel/bpf/verifier.c:5401`.
`clippy::needless-borrows-for-generic-args` present, **style group, warn-by-default**, in the
installed clippy 0.1.97. IPE present at tag `v6.12` and absent at `v6.11`, which is what makes
the report's `ipe`-in-a-6.1-config tell load-bearing. Not reproduced, and labelled as such in
the text: the Alpine 3.20-vs-3.24 `CONFIG_BPF_LSM` flip (needs both images) and every
event internal to the private repo.

**Adopted, with two placement corrections.**

- **The EOL date as the forcing function** (proposal 1) → `sota/SKILL.md` principle 1 plus
  `sota-devsecops` rules/03 **§3.9**. The strongest item in the report and the only failure a
  *user* had to catch three separate times. Its mechanism generalises past versions: **demand
  a second value that cannot be produced from plausibility.** A recalled version number
  arrives with no felt uncertainty, so every rule triggering on doubt is structurally unable
  to fire; an EOL date cannot be recalled, so requiring the column forces the lookup. Adopted
  with the reporter's corollary intact — a lapsed row is **removed, not corrected**, because
  an EOL branch can answer the *opposite* of the current one rather than a staler version of
  it (measured: 5 of 7 rows stale in one pass).
- **The denominator where a positive control is unavailable** (proposal 2) →
  `sota-shell-scripting` rules/06 §2, **not** `sota-code-security` rules/15 as proposed. The
  general idea is already ours in three shapes — a gate printing its denominator (rules/11
  §2.2), an empty store result carrying its inventory (rules/13 §6), and *control the search
  in the same invocation* (rules/06 §2). **What was genuinely missing is the reporter's own
  argument**: a positive control needs a term you already know is present, so it is
  unavailable for an **extraction or fetch into a blob you have never opened** — which is
  where five of their six instances lived. It is a generalisation of rules/06 §2's existing
  paragraph, so it went there rather than starting a fourth home.
- **A style lint's premise on a constrained target** (proposal 3) → `sota-rust` rules/07
  **§1a**. A real gap: `sota-rust` had nothing on eBPF, `no_std`, embedded or WASM. Adopted
  with the linguistic tell the report identified, which is the transferable half — *"mechanical",
  "trivial", "just a rename", "style only"* are classifications that license skipping analysis
  and are applied **before** the analysis that would justify them.
- **The gate that stops at the artifact** (proposal 3, second half) → `sota-devsecops`
  rules/09 **§2a**, a new section. §2 covered the *lateral* blind spot (code moved out from
  under a path expression) and nothing covered **depth**: four gates green on an object the
  kernel verifier then refused. Folded in the mirror-image trap already known here — a gate
  whose reach is bounded by what the *subject* checks first, fixed with a dummy credential.
- **Population-selector drift** (proposal 4) → `sota-shell-scripting` rules/09 **§5a**, a
  sibling to §5 rather than the rules/13-or-11 the report offered. Placement reasoning, since
  it was a close call: all three instances are ad-hoc shell commands, and §5 is already *"the
  listing tool answered your question about one page"*. The distinction earning a section is
  that §5 returns **less of the right population** while this returns **all of a neighbouring
  one** — nothing truncated, exit 0, no rule broken. Distinct from `sota-observability`
  rules/05 §7a (no instrument exists, a proxy substitutes) and from rules/14 §4 (every
  instrument correct, the reader stopped at the first affirmative one); cross-referenced both.
- **The suspiciously clean result** (proposal 5b) → `sota-code-security` rules/15 §2.1. A true
  sharpening: the existing text trains the reader on *red* and *implausible* results, and this
  is the **inverse** — a perfect correlation, 15 for 15, that reads as strong evidence. Kept
  the reporter's own distinction that a denominator would *not* have caught it; different
  failure, different control, and collapsing them would weaken both.
- **Commercially-interested sources** (proposal 6) → `sota/SKILL.md` principle 3 plus
  `sota/rules/03` §2. **Zero coverage across three concept sweeps** — the only adjacent text
  is `sota-copywriting` rules/04, which is the opposite direction (disclosing *your own*
  material connection under the FTC guides). Framed structurally rather than tonally:
  independent sources converging is evidence; sources converging on the conclusion that sells
  their product is **one hypothesis held by several interested parties**.

**Reported as evidence, no change made (proposal 7, and the reporter proposed none).** A
pipeline written for *display* (`| tail -30`) had a status `echo` appended as an afterthought,
so the construct was never classified as "the status path" and the exit-code rule did not
attach. This is a **fourth** data point for a claim the library already makes — *a warning
about a reflex does not disable the reflex* — in a different tool, from someone with the text
in context. Recorded because the aggregate is the argument: if this library ever weighs
"add another warning" against "change the default construct", four independent reproductions
say the warning is not the lever.

**A correction to the report's targeting, which cost nothing here but would have elsewhere.**
Two proposals named `sota-code-security` rules/03; that file is **authorization**. The text
quoted alongside them (*"a negative claim needs more proof than a positive one"*) is
`sota/SKILL.md` principle 3, and the evidence standard is `sota/rules/03` §2. The two `rules/03`
are different files in different skills. Checked against the library rather than the named
path — the procedure this log has been burned by twice.

**Housekeeping, flagged rather than fixed.** `sota-shell-scripting` rules/06 is now at
**500/500** and is the next split candidate; do it by the **citation seam** (where its § refs
cluster), never by heading count. No new skill, no `description` change, so the routing
classifier is untouched.

**Landed:** `sota/SKILL.md` principles 1 and 3 · `sota/rules/03` §2 ·
`sota-devsecops/rules/03` §3.9 and `rules/09` §2a · `sota-rust/rules/07` §1a ·
`sota-shell-scripting/rules/06` §2 and §5a · `sota-code-security/rules/15` §2.1 — each with
its audit-checklist half in the same change.


### 2026-09-13 — a claim from field report III, checked late and found false

Report III's §8 ("What worked") described a known-bad that **decayed silently as the codebase
improved** — the probe depended on a suppression existing, and the suppression became
unnecessary — and said of it: *"That failure mode … is already in the library."*

**It was not.** Verified 2026-09-13 with a positive control (`known-bad` returns 9 hits in
`sota-code-security` rules/12, so the instrument works) across two vocabulary sweeps and then
by reading the headings of the skill that would own it. The closest coverage, **rules/12 §1b**,
is the *drifted literal*: a known-bad that no longer matches, which the standard guard —
*assert the mutation took* — catches by design. The decay case is its blind sibling: the
mutation applies cleanly, the tree really changes, that guard passes, and the result still does
not cross the threshold.

**What makes the correction cheap to justify is that the class then happened here, in this
session, while the report was being implemented.** Offloading the invariants table took
`AGENTS.md` from 199 lines to 169 and silently disarmed probe 24, which appended exactly one
line to breach a 200-line cap. The improvement and the disarming were the **same edit**. Landed
as **rules/12 §1d** with its audit-checklist half.

**The reviewer's share, which is the reusable part.** During the intake I accepted §8 as
"already ours" without checking, because §8 was labelled *what worked* rather than a proposal —
so it never entered the verification path the seven numbered proposals went through. **A report's
non-proposal sections make claims about the library too, and they arrive without the framing
that triggers a check.** Same shape as the 2026-09-12 lesson one entry up, one level further
out: there I verified the gap in the file the reporter named instead of the library; here I did
not verify at all, because the sentence was not shaped like a request.

**Landed:** `sota-code-security/rules/12` §1d · v1.42.0


### 2026-09-13 — a rule this repository wrote for itself, put through the intake it had skipped

`sota-code-security` rules/12 §1d was authored here, from a live incident in this session, and
was about to ship on green gates. An independent adversarial pass — prompted to **kill** it,
defaulting to REFUTED, citing file:line — returned **11 findings**. Recorded because the
*procedure* gap is the finding, not the rule.

**All 30 invariants were green on all 11 defects.** They check structure: the line cap, a
checklist present, `§` references resolving. **Nothing in this repository checks whether a
rule is true**, which is exactly why an external proposal goes through this ledger — and a
self-authored one never enters it.

Five classes, each worth reusing:

- **Over-generalised from the single case in hand.** *"Every probe against a numeric threshold
  has this shape"* was refuted by four probes in the harness the rule itself cites; the
  deciding property is a delta **smaller than the threshold**. Two of those counterexamples
  became the rule's own named remedies, so the attack improved it rather than only trimming it.
- **Unmeasured rhetoric asserted as fact** — deleted under operating principle 0.
- **A citation that resolves but does not support the sentence citing it.** `rules/15` §2.1
  grounds its prior on *recency of authorship*; this case inverts that. **Invariant 18 proves a
  `§` reference resolves and can never prove the target says what the citing sentence claims** —
  worth stating plainly, because the green check invites the opposite conclusion.
- **A default that inverted an existing tool's semantics**, which would have taught readers to
  dismiss the very failure the tool exists to reveal.
- **A self-contradiction shipped across two files in one branch**: the probe comment and the
  CHANGELOG called the class *"the shape the library already names"* while this ledger, in the
  same branch, correctly recorded that it did not.

**What survived, and it is the load-bearing half:** the decay framing itself. `AGENTS.md` was
**exactly 199 lines** at the commit that introduced probe 24, so the probe was effective at
birth and genuinely decayed — refuting the alternative that it was born broken. The reviewer
added a sharpening the rule now carries: its margin was **one line** from day one, so it was
never robust, only fitted to the subject's momentary state.

**Standing change:** a rule authored *and* adopted in the same session is the highest-risk
change in a PR, not the safest, and gets the adversarial pass the AUDIT workflow already
prescribes for findings.

**Landed:** `sota-code-security/rules/12` §1d rewritten · §1b gains a fourth bullet so §1d is
reachable at the point of need · `sota-shell-scripting/rules/05` §3b · v1.42.0


### 2026-09-13 — the gap the last entry named, closed as invariant 31

The entry above recorded a procedure gap: **all 30 checks asserted structure, consistency or a
declaration, and none looked at whether a rule is true.** It then stated a "standing change" in
prose — *a rule authored and adopted in the same session gets the adversarial pass* — and
stopped there.

**That is the failure this repository has a rule against.** `sota-code-security` rules/14 §3 is
*a natural-language instruction standing in for an enforced control*, and it is the reason
invariant 11 exists. The standing change lived at one line of `docs/ADOPTION-LOG.md` and
nothing read it. Verified before acting: a sweep of `scripts/` for it returned nothing.

**What is and is not gateable, decided rather than assumed.** *"Is this rule true"* is
semantic, and the ledger's own argument applies — a fuzzy gate produces false positives, gets
disabled, and leaves you worse off than the prose. So the general form was **rejected**, and
the mechanical part gated instead: whether the rule reached the ledger at all. An external
proposal always does; a self-authored one never does.

Against this ledger's three filters: **has it failed** (yes — §1d, eleven defects on green
gates), **does it fail silently** (yes, completely), **is it mechanically checkable** (yes,
diff-based like 11/14/29).

**The exemption is the part that decides whether it survives.** This repo splits rules files
regularly and a split re-adds every heading it carries. A heading that existed in any rules
file at the merge base is therefore exempt — without it the check fires on every split, opens
red, and gets disabled. Probed both ways: **31** fails on new text, **31b** requires the
exemption to *hold* and to say so. 31b needed a new helper, because a bare green proves
nothing when a skipped check is also green.

**What it does not do, stated so nobody reads more into a green tick than it carries:** it
proves a ledger line exists, never that the reasoning in it is sound, and never that the rule
is correct. It makes the intake unskippable; it does not make it good.

**Landed:** invariant 31 + probes 31/31b + `probe_committed_green` · v1.42.0


### 2026-09-13 — `rules/05` §3b corrected: `sed -i` is safe only on BSD

The rule shipped hours earlier said *`perl -pi` converts a symlink, BSD `sed -i` refuses*,
with GNU `sed` explicitly marked **not verified** because it was not installed on the machine
where the measurement was taken. The operator asked for it to be verified. It was, in
throwaway containers:

| implementation | `-i` on a symlink | exit |
|---|---|---|
| BSD sed (macOS) | refuses | 1 |
| **GNU sed 4.9** (Debian) | **silently converts** | **0** |
| **BusyBox sed 1.37.0** (Alpine) | **silently converts** | **0** |
| perl -pi 5.34.1 | silently converts | 0 |

**The unverified row was carrying the rule's advice.** With GNU unknown, the contrast read as
*perl is dangerous, sed is safe* — and the text said so, calling BSD's refusal "a feature".
With GNU and BusyBox measured, the real finding is a **platform split that runs the wrong
way**: the safe behaviour exists only on the machine a developer tests on, and CI has the
dangerous one. A rule that told you to prefer `sed -i` would have made that worse.

**The lesson is about the label, not the tool.** Marking a row *"not verified"* is honest and
it does **not** make the surrounding advice safe — the advice was already resting on the
unmeasured cell. When an unverified value would change the recommendation, it is not a caveat,
it is a blocker: measure it or do not give the recommendation. Containers made this a
two-minute check that was skipped because the local box lacked the binary.

**Landed:** `sota-shell-scripting/rules/05` §3b rewritten with all four implementations, its
audit-checklist half, plus README, `docs/INDEX.md` and the CHANGELOG entry that carried the
refuted contrast · v1.42.0


### 2026-09-13 — private-project field report II: three adopted, one corrected in adoption, one deliberately not a rule

`FIELD-REPORT-PRIVATE-2026-09-13-II.local.md`, same session as report I, filed separately
because the two are **different in kind** — and the distinction is the report's own and worth
keeping. Report I's findings were about **instruments**: readers returning empty, searches
answering a neighbouring question, stale versions, each fixed by a denominator or a control.
These four are about **reasoning that survived contact with a passing test**: the tool worked,
the output was read correctly, and the conclusion was still wrong.

**Every falsifiable claim reproduced before adoption.**

- **§3 reproduced exactly, to the NVR.** `podman run almalinux:8` → `kernel-headers-4.18.0-553.162.1.el8_10`,
  6160-line header, `BPF_MAP_TYPE_RINGBUF=1`, `BPF_PROG_TYPE_LSM=1`,
  `BPF_MAP_TYPE_PERF_EVENT_ARRAY=6` — same numbers the report published. A kernel numbered
  **4.18 carrying upstream 5.7/5.8 features**.
- **§1's inlining mechanism confirmed generally**, rustc 1.97.1, with a control: a plain
  single-call helper is absent from the assembly at `opt-level=3` (grep count 0, versus 2 at
  `-O0`), while an `#[inline(never)]` neighbour still shows three call sites — so the absence
  is real rather than a search artefact.
- **§2 confirmed and CORRECTED** — see below.

**§2 adopted with a correction, and the correction makes the rule cheaper to follow.** The
report says a verifier prints its stack depth *"only when it rejects"*, so the remedy is to
**induce the failure**. Reading `kernel/bpf/verifier.c`: the rejection path does emit
`combined stack size of %d calls is %d. Too large`, but a **successful** load emits
`stack depth max %d` from `print_verification_stats()`, gated behind `BPF_LOG_STATS` in the
caller-supplied `log_level` (uapi `bpf.h`). **The margin exists on the happy path; you have to
ask for it.** Shipped as `rules/15` §2a with "look for the verbose/stats mode first, induce the
failure only where none exists" — the report's principle, a better remedy. Its generalisation
to linters, validators and admission controllers is untouched and is why this was the
highest-reach item.

**§4 proposes no rule, and that was accepted as stated.** It argues that a rule broken by
people who have read it needs a **changed construct, not a stronger warning**, and offers its
own worked example. Landed in `CONTRIBUTING.md` rather than a rules file, because it is
guidance about **how this library is written** — skills are for people building software.

**A premise correction, small and the same shape as report I's.** §4 says *"the library
already says this, in its `rg -r` note"*. The `rg -r` note is in the **operator's global
`CLAUDE.md`**, not in `skills/`. The library states the same lesson in `rules/15` §2.1 (*"the
reflex comes from muscle memory that a note does not reach"*). The proposal is unaffected —
but it is twice now that a report has located one of our rules in the wrong file, which is
worth the reporter knowing.

**Independent corroboration this reviewer can add.** §4a's exit-code trap was hit **twice more
on our side the same day**: a `; echo "EXIT=$?"` that made a failed push's wrapper report
success, and a `gh pr checks --watch` that returned `exit 0` while all four checks were still
pending. Five data points across two parties moves §4 from "medium-high, but it is
meta-guidance" to something the repo now acts on.

**Landed:** `sota-rust/rules/07` §1b · `sota-code-security/rules/15` §2a ·
`sota-devsecops/rules/03` §3.9 extended · `CONTRIBUTING.md` authoring principle — each with its
audit-checklist half where it has one · v1.42.0


### 2026-09-13 — two lessons taken out of an operator's global agent file, before thinning it

Not an external report and not a field brief: an audit of the **operator's own
`~/.claude/CLAUDE.md`**, prompted by asking what in it might conflict with this library or
cause it to be skipped. Measured: **366 of 411 lines (89%)** duplicate library content, and
**15 of 19** rules tested are already in `skills/`. Two were not, and they are taken here
**before** anything is removed from that file — an idea that lives in one person's always-loaded
config is invisible to everyone else, and deleting it without intake loses it.

- **`sota-devsecops/rules/09` §2b — which binary, and over what.** A third axis of gate reach
  beside §2 (scope drifted sideways) and §2a (reach stops at the artifact): the **identity**
  of the tool that produced the verdict, and the **extent** it was pointed at. Both invisible
  in a green tick, neither leaving a diff. Two measured halves — a Homebrew `cargo` shadowing
  a rustup shim so `cargo fmt --check` exited 0 while ignoring every nightly-only config key,
  and `--manifest-path` narrowing coverage so local passed what CI rejected.
- **`sota-devsecops/rules/03` §3.6a — a clean run from one scanner is not coverage for
  another's question.** `govulncheck` 1 advisory vs Dependabot 19 alerts on the same tree,
  neither wrong: reachability-of-a-symbol versus version-in-the-graph. The library had the
  **triage** half (§3.6, prioritise reachable findings) and not the inverse — that a clean
  scan from one tool silently substitutes its question for the other's. Includes the
  second-order finding: merging a bot's bump is not closing the advisory it cites.

**One live divergence found and NOT resolved here, deliberately.** The operator's file and
`sota-shell-scripting` rules/06 §2 both carry a `grep -r`/`-R` symlink table, and they
disagree: the global one has two columns (*ugrep `-r` skips, `-R` follows*), while the
library later refined it to **symlinked dir as the argument** versus **met in traversal** —
where ugrep `-r` *follows* an argument and skips only what it meets while walking. Following
the older table, a sweep whose **root** is a symlink behaves opposite to expectation. Flagged
to the operator rather than silently picking a reading, because one of the two measurements
should be re-run rather than deferred to.

**The general point, which is why this is in the ledger at all:** *"two homes for one rule is
how they drift"* (recorded here 2026-09-12) applies to an operator's config as much as to two
files in this repo — and the always-loaded copy is the one that is **not** gated by invariants
18, 22, 30 or 31, not measured, and not updated when the library learns something.

**Landed:** `sota-devsecops/rules/09` §2b · `sota-devsecops/rules/03` §3.6a — each with its
audit-checklist half · v1.42.0


### 2026-09-13 — the last four lessons out of the operator's global file, each re-verified

The remaining four from that audit — the ones an earlier pass had wrongly counted as already
covered. **That miscount is the first thing worth recording**: a loose pattern sweep reported
15 of 19 rules duplicated, and opening the hits showed four were false positives (the
"JS-rendered" hit was a passing *example* inside our own text; "hard links" matched an
unrelated `fs.protected_hardlinks` sysctl; five "cannot distinguish" hits were all other
subjects). **Counting grep hits is not checking coverage** — the same lesson this log recorded
on 2026-09-12, arriving through a different door.

Each was re-verified rather than taken on the operator's word:

- **`sota/rules/01` §3 — an empty page is a fact about your fetcher.** Reproduced live:
  `evals.mitre.org/results/enterprise` → HTTP 200, 3,150 bytes, **2 words** of visible text;
  the API behind it → 1.85 MB, **124,872 words**. The remedy (look one level down for `/api/`,
  `__NEXT_DATA__`, a sitemap) is what turns a four-pass "unreachable" into a source.
- **`sota-llm-engineering/rules/01` §8a — a completeness rubric cannot tell "correctly
  declined" from "omitted".** Verified against **our own retained artifact**
  (`evals/results/2026-09-12/`): a guided arm scored **0.00 on ten items** for asking a
  security-relevant clarifying question its guidance prescribes. Carries the harder half — an
  eval storing only `artifact_len` cannot diagnose its own anomaly, so retain the artifact.
- **`sota-shell-scripting/rules/05` §3c — a hard link does not survive an atomic rename.**
  Executed: same inode, then `mktemp`+`mv` leaves the link holding **v1** while the file reads
  **v2**, no error and no broken link; `ln` on a directory refuses outright. Strictly worse
  than a symlink, whose failure is loud. Sits beside §3b, the same family.
- **`sota-devsecops/rules/03` §3.6b — a scanner built against an older toolchain fails as
  noise.** Mechanism verified in a container: an older toolchain meeting newer-declaring source
  emits a message that **names the version skew**, not the project. The specific
  stdlib-path symptom stays labelled field-reported rather than asserted.

**And the intake reproduced a trap it was intaking.** Checking whether the rubric finding
existed here, `rg -ril "clarifying question"` rewrote every match to the literal `il` — `-r` is
`--replace` — so the output showed our own eval artifact reading *"one il that affects security
scope"*. Files were fine; the command lied. Caught because the result was **implausible**, which
is the fifth instance this session of the claim that a warning about a reflex does not disable
the reflex, and the fourth recorded occurrence of this exact flag.

**Landed:** `sota/rules/01` §3 · `sota-llm-engineering/rules/01` §8a ·
`sota-shell-scripting/rules/05` §3c · `sota-devsecops/rules/03` §3.6b — each with its
audit-checklist half · v1.42.0


### 2026-09-13 — executable claims get re-run in CI, and the harness refuted a shipped rule on its first run

Operator question: several of this session's findings were only visible when something was
*run* — should the library test all of its claims, and require it of every intake?

**"All" was the wrong scope and saying so was the useful part.** 218 claims across 92 skill
files say *measured*; most are **not executable** — network reads of third-party sites, runs
costing live API calls, facts about a kernel. Worse, some are values that **change by
design**: asserting today's `endoflife.date` rows would make CI red on a *correct* world, and
a flaky gate gets disabled, leaving you worse off than the prose. So the gate covers
**deterministic and platform-split** claims only.

**Platform-split is why CI runs it on Linux *and* macOS.** BSD `sed` refuses a symlink where
GNU converts it; BSD `grep` skips a symlinked dir that GNU and ugrep follow. A single runner
can only confirm its own half — and the unseen half is exactly where the guidance was wrong
(`rules/05` §3b shipped saying *"`sed -i` refuses"*, true only on BSD).

**It earned its keep immediately: claim 8 failed on the first run, and the RULE was wrong.**
`rules/06` §2b claimed `ps -p ""` *"ignores the filter and prints every process, exit 0"*.
Measured on BSD `ps` **and** procps-ng 4.0.4: **both reject it, exit 1.** The implausibly
large result the rule describes is real but comes from `-a`/`-x` overriding `-p`, which
happens with a perfectly valid pid (944 of 944 here). The class survives in a sharper form,
now measured and in the rule: an empty value makes a **pattern** flag match everything
(`git log --author=""` → 373 of 373, `grep -e ""` → 3 of 3) and an **identifier** flag reject
it or match nothing. That distinction is more useful than the original and would not have been
found by reading.

**The convention, in `CONTRIBUTING.md`:** every intaken claim records *how* it was verified;
executable-and-deterministic ones ship the check; and — the part that has actually bitten —
**when an unverified value would change the recommendation, it is a blocker, not a caveat.**

**Two defects in the harness itself, both found by watching it fail rather than reading it:**
a hardcoded expectation in a failure message printed the self-contradictory *"expected
defaults=1 follow=2; got defaults=1 follow=2"* (the message drifted from the comparison — now
both read the same variables), and the first version of claim 8 tested a simplified command
the rule never made.

**First CI run, and the denominator was the finding — not the exit status.** Both jobs
reported success while executing **8 of 11** on Linux and **9 of 11** on macOS: neither runner
ships `ugrep` or `ripgrep`, so the two claims about the searchers this library *recommends*
skipped on both and had still only ever run on one laptop. Green and hollow, in the gate built
to prevent exactly that. Closed by installing them on the Linux leg (apt; brew on the macOS
runner costs minutes and that leg already carries the BSD rows that justify it).

**What the two runners did confirm, cell by cell, which is the whole argument for scope (b):**
`sed -i` on a symlink — **GNU converts silently at exit 0**, **BSD refuses at exit 1 with the
link intact**; `grep -r` on a symlinked dir — **GNU skips in traversal and follows an
argument**, **BSD skips both and follows an argument only with a trailing slash**. Each runner
proves its own half; neither could have proved the other's.

**Landed:** `scripts/check-claims.sh` (11 claims at the time, 2 runners; it grows — run it for the count) · a `claims` CI job ·
`CONTRIBUTING.md` convention · `sota-shell-scripting/rules/06` §2b **corrected** · v1.42.0


### 2026-09-13 — the nineteenth rule, found by refusing to delete on a tally

Thinning the operator's global `CLAUDE.md` meant deleting 19 shell rules on the grounds that
the library now covered them. **Verifying each one individually rather than trusting the
running tally found that 18 did and one did not**: *an assignment prefix does not reach a
process substitution.* Two concept sweeps with a positive control confirmed it was absent —
and it is a **secrets** rule, so deleting it would have removed the only copy of a live
security caveat.

**My first reproduction refuted the claim, and my test was the thing that was broken.**
`MY_VAR=secret bash -c 'cat <(./h)'` printed the value, apparently contradicting the rule —
because the prefix was on the *wrapper* shell, whose environment children inherit. A second
malformed test used a bare `VAR=x;` assignment that is never exported. Tested faithfully,
**with a control line proving a prefix does reach a plain command**, the rule holds exactly
as written, in bash and zsh alike. Without that control the `UNSET` would have been
indistinguishable from a broken helper.

Landed as `sota-shell-scripting` rules/03 **§2a**, with the executable check shipped
alongside it (claim 11 in `scripts/check-claims.sh`, both shells) — the convention added
hours earlier, applied to its first new rule.

**The reusable part is the deletion discipline.** A tally is not a verification: "15 of 19
covered" was wrong twice in this exercise, first by four (loose pattern matching) and then by
one (a rule nobody had checked individually). **Before deleting the last copy of anything,
resolve each item to the section that replaces it** — the check costs a minute and the
failure is silent and permanent.

**Landed:** `sota-shell-scripting/rules/03` §2a + `scripts/check-claims.sh` claim 11 · v1.42.0


### 2026-09-14 — private-project report III: a principle corrected, and a reporter who refuted their own mechanism

`FIELD-REPORT-PRIVATE-2026-09-14.local.md`. Four proposals about **epistemics under
correction pressure** rather than tooling — which is why a library heavy on *"your instrument
is a control"* did not catch them.

**The highest-value item was not one of the four.** Reviewing the report's coverage method
surfaced that it searched *"one instance | a single observation"* — with a positive control
returning four files, so the instrument was sound — while the corpus says **"one sample"** in
six files, including a *named failure mode* at `rules/15` §2.1. Working instrument, wrong
vocabulary, false absence.

That lands as a **correction to operating principle 3**, not a new rule, and the distinction
matters: principle 3 said *"'independent' means a different failure mode, **not a different
phrasing**"* — written to stop two `grep -r` runs over a symlink farm counting as two methods,
and correct for that. But it is the one place a reader goes to check an absence, and it read
as *phrasing does not matter*. It now carries the reporter's formulation: **a control proves
the instrument works; it does not prove the query asks the corpus's question.** Correcting a
shipped principle that points the wrong way in an adjacent case clears a lower bar than
promoting a new rule — the same verdict shape as 2026-09-09.

**The reporter refuted their own mechanism, and the report is better for it.** §2 originally
asserted that a push rejection quoted the value it had itself just written because an
idempotent retry failed its precondition. Asked for the reproduction, they built it, stated
the falsifier first, and **failed twice** — the old-value comes from the server's
advertisement rather than `refs/remotes/`, and the client short-circuits when the remote
already equals the target. Both harnesses used git's **local** transport, which has no HTTP
layer and therefore no retry: *the environment could not reach the defect*, which is
`sota-code-security` rules/10 arriving at their own experiment.

So the **mechanism is labelled unverified in the rule**, and the wide generalisation — any
idempotent retry can report failure about its own success — is recorded as **plausible and
unproven**. What shipped is the observation alone: a command exited non-zero while its write
had landed. That licenses *"read the resource back before acting on a failed mutation"*
without needing the mechanism, and is a **smaller claim with wider reach** than the one first
offered.

**Placements, two of which moved.** §1 (the retraction bar) went to **operating principle 0**,
not `sota/rules/03` as proposed: *"a retraction is a claim"* is governed by *validate every
claim*, applies in every mode rather than only to audit findings — and `rules/03` had four
lines of slack, which must not be what decides a home. §2 and §4 went to
`sota-shell-scripting/rules/01` as **§2b** and an extension of **§2a**, siblings of "a
background job's completion signal is about the launcher": §2a is a status about the wrong
*subject*, §2b a status about the right subject at the wrong *scope*. §3 became the **third
bullet** of `rules/15` §2.1, beside the two existing members, with a cross-reference from
`rules/13` §3 — its distinction is that both existing members are about a *thing you built*
generalising, and this one is about a **sentence**.

**Checked and found NOT drifted:** `sota-testing` rules/07:232 and `sota-shell-scripting`
rules/01 §2a both cover the background-job complement — but the former is a *pointer* to the
latter, which is the library working correctly rather than two homes for one rule.

**§5, added after the first four, and it explains the other four.** *A failed reproduction is
an absence claim.* `rules/12` §1a already demands an **allow arm** beside a deny arm for any
control, and already states the governing line — *"an arm like that exercises the environment
and passes whether or not the control exists at all."* Nothing pointed that requirement at an
**experiment**, which is why it was skipped. Filed as **§1a.1**, an extension, on the
reporter's own recommendation — and their coverage check this time used the corpus's
vocabulary (`allow arm` → 2, `negative control` → 4, `known-good` → 8, all reproduced here),
which was §3's lesson applied one item later.

The genuinely new half is the **reporting** consequence: *"it did not reproduce"* is a
negative claim under principle 3's heavier burden, but **it does not feel like a search**, so
the rule never fires — a refutation is offered as a result rather than as a not-found and
passes unchallenged in a way *"no instances of X"* would not. The tell is cheap: **a null that
arrives instantly and identically on both runs**; a real refutation usually costs something.
Principle 3 now points at it, since that is the rule that should have fired.

**And §2's mechanism is no longer unverified — which made something we shipped hours earlier
wrong.** The reporter built a third harness (alpine 3.22, git 2.49.1) with a real
`git-receive-pack --stateless-rpc` behind a minimal smart-HTTP server, POST delivered twice,
**and a control arm** (`DOUBLE=0`). Control: exit 0, ref advances, no quote. Test: exit
non-zero, **the write lands**, the error quotes the value just written and names the stale
old-value as expected — all four predicates of the field signature. `sota-shell-scripting`
rules/01 §2b said *"the mechanism is NOT established"*; it now records the reproduction,
attributed and dated, **as field-reported rather than measured here** — the harness lives in
the reporter's scratchpad and was not rebuilt on this side. The wider generalisation stays
**plausible and not established**: one protocol reproduced is not the class, and the rule
depends on none of it.

**Landed:** `sota/SKILL.md` principles 0 and 3 · `sota-shell-scripting/rules/01` §2a extended
and §2b · `sota-code-security/rules/15` §2.1 third bullet · `rules/12` §1a.1 · `rules/13` §3
cross-reference · v1.42.0

## 2026-09-14 — An external adversarial audit: 2 of 5 technical claims landed, and every line number was invented

> **Correction, 2026-09-14 (same day, closure pass):** *"every line number was invented"* is
> an overstatement and is retracted. Re-checked at closure: the report's citation of
> `evals/run-desc-routing.py:3–22` **resolves correctly** — those lines are the docstring
> describing the descriptions-only A/B, which is exactly what it cited them for. Of the
> anchors verified during the session that one was right and the rest were wrong, and **not
> every anchor was verified**. The accurate claim is *"nearly every anchor checked was
> wrong, including one past end of file and one whose target says something else"* — which
> still supports treating the report as leads rather than findings, and does not support the
> absolute. Recorded rather than edited away: the overstatement also reached two commit
> messages (`b127d03`, `32094b9`), which are immutable.

**Source:** an unsolicited third-party audit report of the library (model-generated, vendor
unstated in the artifact), covering factual errors, routing coverage, over-claims and
contradictions. Read it as **field-brief intake**, not as a verdict: it opened **3 of 271**
rules files and 12 files total, and said so honestly in its own "what I could not check".

**The headline is a calibration finding about the report itself.** Every count it asserted
was exact — 271 rules files, 42 skills, 313 files, 21 eval runners, 31 invariants, and the
`v1.41.2` tag it named does exist. Every *line number* was wrong. The routing table it
quoted four rows from sits at `skills/sota/SKILL.md:152–196`; it cited 219–261, and its four
row citations (227/247/249/255) land in cross-cutting-rules prose. The dependency claims live
at `rules/03:17,18,107,338`; cited as 205/206/256/352. One citation ran **past end of file**:
`sota-kubernetes/rules/04-gitops-controllers.md` is 214 lines, cited 199–282. One said
something the target does not say: `CONVENTIONS-LEDGER:193–194` was offered as evidence of
"incorrect attempts to bump the verification stamp" and is actually the Samples-column /
invariant-13 passage about a retracted `+0.07`. The pattern is not invention — the quoted
*strings* are real and were plainly read — it is **real content with fabricated coordinates**,
which for a report whose format is `file:line` makes most findings unverifiable without
redoing the work. Treat an unanchored audit as a set of leads; re-derive each anchor.

**Adopted (4).**

1. **`poetry install` fails open on a *missing* lock** — `rules/03` §3.1. The report's stated
   mechanism was wrong (it blamed `--no-root`, which was never the claimed check) but its
   conclusion was right. Measured here on Poetry 2.4.3 in a scratch venv rather than read off
   a doc page: a **desynced** lock exits **1**, so the cell's "(lock checked)" was correct for
   staleness; **no lock at all** resolves fresh, installs, writes a lock and exits **0** — this
   section's own BAD pattern at a green build. `poetry check --lock` exits 1 in both cases and
   now goes first. Generalised into the bullet as the question to ask of every cell in that
   column: *what does it do when the lockfile is absent rather than wrong?*
2. **pnpm guidance was two majors stale, in two files** — `rules/03` §3.4 *and*
   `sota-javascript-typescript/rules/05` §, which the report never opened. `onlyBuiltDependencies`
   was **removed in v11** (replaced by `allowBuilds`), and the current line is v12. The report
   said "deprecated in newer pnpm 10", which is the right direction and the wrong specifics.
   Both sites now also carry `strictDepBuilds` (default `true` since v10.3.0) — the half that
   exits non-zero rather than warning. **This is the [field-brief intake] rule firing again:
   verify a claimed gap against the LIBRARY, not the file the report named.**
3. **The Go row overstated `go.sum` and `-mod=readonly`** — a *sub*-point of a finding that is
   otherwise refuted (below). `go.mod` pins and `go.sum` authenticates; `-mod=readonly` has been
   the default since **Go 1.16**, so prescribing it implies a control that is already on, and
   `go mod verify` checks only the local download cache. The row now names the control that
   earns its place: CI failing on a dirty `go mod tidy` diff.
4. **The timing-oracle claim was stated unconditionally** — `sota-code-security/rules/04` §6.
   "recovers secrets byte-by-byte" is the worst case, not the guarantee. Rewritten to the
   strength the primary sources support (Python's *"designed to prevent timing analysis"* plus
   its types/lengths caveat; libsodium's *"the goal is to mitigate side-channel attacks"*),
   while keeping the fix unconditional. This is principle 3 applied to our own prose.

Plus one over-claim: **README** asserted "every fast-moving claim web-verified against a
primary source" with no date attached, and the pnpm miss is the counterexample. Now qualified
by the `LAST-VERIFIED` stamp, pointing at operating principle 1.

**Rejected (4), with the primary source that killed each — do not re-litigate.**

- *"Go is presented as frozen when the prescription only checks integrity"* — **refuted.**
  [go.dev/ref/mod](https://go.dev/ref/mod#minimal-version-selection): *"MVS is deterministic,
  and the build list doesn't change when new versions of dependencies are released."* A
  committed `go.mod` + `go.sum` **is** a frozen build; the proposed remedy (vendoring, or a CI
  diff of `go list -m all`) is ceremony. Confirmed against the local toolchain (go1.27.1):
  `go help build` — *"the go command acts as if `-mod=readonly` were set."*
- *"The Go row contradicts its own 'require is a floor, not a cap' prose"* — **refuted, a
  misread.** That line (`rules/03:338`, not 352) is about reading the version you are pinning
  **to** from `proxy.golang.org/<module>/@latest`. It makes no claim about build determinism.
- *"Native desktop Swift has no owner"* — **refuted.** `sota-mobile`'s **frontmatter
  description** — the actual auto-load classifier, and the only text `run-desc-routing.py`
  reads — says "Swift as a language … **in any target** including server-side Swift". The
  report read the terser router *table* row while claiming a descriptions-only method.
- *"'The durable value is cross-cutting correctness' is broader than the evidence"* —
  **refuted as characterised.** `WHY-IT-WORKS:234` (not 250–253) says the durable value "is
  making cross-cutting concerns **salient at the moment of writing**", directly after the
  measured omissions (tests 7/7, transport 5, rate limiting 5) and directly before a "Method
  and limits →" link. The paraphrase dropped the mechanism and the limits.

Also not adopted: its **10 "routing collisions"**, which are the router's cross-cutting rules
1/2/6/9 working as designed — the report concedes this and scores them as defects anyway; and
its **"+0.10 routing vs 0.80 descriptions-only" contradiction**, since `RESULTS.md:336` already
names §5 as "the path a skill **auto-loader** uses … distinct from the router table §1
measures", and that 0.80 is over 10 *adversarially-confusable* cases against 20 ordinary ones.
Different populations, already stated. The summary row label could carry the distinction; that
is a labelling nit, not a contradiction.

**A lesson this session owes its own rules, and it is not the report's.** The first pass of
this intake reported that `poetry install` *warns* on a desynced lock — read off a doc page's
summary, published as mechanism, and **wrong**. Running it took two minutes and inverted the
finding. That is `sota-shell-scripting`'s standing rule (suspect the harness, run the thing)
and the [in-place-edit] retraction of 2026-09-14 in the same shape, one day apart: **a
documentation page describes intent; only execution reports behaviour.** The correction also
surfaced the zsh `${PIPESTATUS[0]}` trap live — it printed empty, and only a second raw-exit
measurement carried the result.

**Landed:** `sota-devsecops/rules/03` §3.1 (Python + Go rows, two new bullets) and §3.4 (pnpm) ·
`sota-javascript-typescript/rules/05` (pnpm, second site) ·
`sota-code-security/rules/04` §6 · `README.md`

## 2026-09-14 — Four routing silences from the external audit: one taken as scope, one as an honest boundary, one deferred, one rejected

Continues the intake above. The audit's §2 claimed four domains with no owning skill. All
four were re-derived here rather than accepted, with a positive control on the sweep
(`goroutine` → 16 files) so a zero means absence and not a broken instrument.

**What the sweep actually found**, which is more differentiated than the report's "no named
owner" for all four:

| claim | measured | verdict |
|---|---|---|
| PowerShell | **0 of 42 descriptions** name it; 4 incidental files, none teaching it | **adopted as scope** |
| CUDA / GPU | one incidental sentence in `sota-performance/rules/02` ("GPU kernel launches") | **deferred** |
| embedded / RTOS | `sota-c-cpp` already carries MISRA C:2025 and freestanding builds — **half-owned** | **boundary stated** |
| compiler / JIT | 33 files, all about *consuming* a JIT (OPcache, JVM warmup, YJIT) | **rejected** |

**Adopted — PowerShell, as scope rather than a new skill.** `sota-shell-scripting`'s own
premise is that shell hides in CI blocks, entrypoints and Makefile recipes; on a Windows
runner that is PowerShell, and the skill silently stopped applying. That is a hole inside a
skill we already ship, so the argument does not depend on who raised it. New `rules/07`
(248 lines), the description extended within the 1024-char cap, and the fix pinned as
`r4_powershell_windows_ci` — because the router says a routing gap ends as a **test**, not a
report.

Every claim in the file is from Microsoft Learn, and the research **changed the guidance
twice**, which is the argument for doing it rather than writing from recall:

- The headline defect is not the one you would guess. `$ErrorActionPreference = 'Stop'` reads
  as the `set -e` equivalent and **is not**: `$PSNativeCommandUseErrorActionPreference`
  defaults to **`$false`**, so a failed `git`/`docker`/`terraform` does not stop the script.
  A control that is present and inert — `sota-code-security` rules/10, arrived at from the
  primary docs rather than from the pattern.
- **A first draft of §4 was wrong and got caught before it shipped.** GitHub Actions runs
  `pwsh -command ". '{0}'"`, and Microsoft documents `-Command` as deriving the exit code from
  whether *the last command* set `$?` — so the draft rule was "a pwsh step's verdict comes from
  its last statement." GitHub's own docs then showed it prepends `$ErrorActionPreference =
  'stop'` and appends `if ((Test-Path -LiteralPath variable:\LASTEXITCODE)) { exit
  $LASTEXITCODE }` for the **built-in** shell keywords. The real rule is the inverse of the
  draft: the built-in shell is safe and a custom `shell:` string silently removes both. One
  more fetch separated a useful rule from a confidently wrong one.

**Boundary stated, not built — embedded/RTOS.** Half-ownership is worse than none: a C++ RTOS
driver routes to `sota-c-cpp` today and gets language-layer advice with no statement of what
is missing. Its Purpose section now says what it covers (MISRA, CERT, freestanding, banned
APIs, hardened flags) and what no skill here owns — ISRs and reentrancy, DMA coherency, MMIO
and `volatile` against a peripheral, RTOS scheduling and priority inversion, WCET, linker
scripts. Cost: one paragraph. It converts a silent mis-route into a stated limit.

**Deferred — CUDA / GPU engineering. Revisit trigger: a field brief from a session that
actually hit GPU work, or a second independent request.** It is a real discipline (occupancy,
coalescing, warp divergence, host/device sync) and we have one incidental sentence, but doing
it badly is worse than not doing it, and its freshness cost is high against a stamp that
sweeps twice a year.

**Rejected — compiler / JIT construction.** Consuming a JIT is already covered correctly in
four language skills. Building a compiler is not "an application, service, or codebase" in the
router's sense and the audience overlap is small. Recorded so it is not re-litigated.

**The caveat that belongs on all four: demand is unevidenced.** Nobody hit a PowerShell task
and found nothing — a model-generated audit imagined fifteen tasks. That is the weakest source
shape this project has data on (it opened 12 of 313 files, and nearly every citation anchor
checked was wrong — see the correction at the head of this entry),
against field briefs from sessions that *used* the library landing 56 of 60. PowerShell was
taken on its internal merits; the other three wait for someone to actually need them.

**Landed:** `sota-shell-scripting/rules/07` (new) · its `SKILL.md` index and description ·
`sota/rules/04` library map · `sota-c-cpp/SKILL.md` Purpose · `evals/cases/desc-routing-regressions.jsonl`

### 2026-09-14, same session — the PowerShell *routing* claim was refuted by measurement, including our own version of it

The entry above adopted PowerShell partly on a routing argument: **0 of 42 descriptions named
it**. That number is correct and it is **not** evidence of a routing gap. Measured against the
pre-change tree ([POWERSHELL-ROUTING](../evals/results/2026-09-14/POWERSHELL-ROUTING.md)):

| phrasing | before | after |
|---|---|---|
| "PowerShell **script**" + `$ErrorActionPreference` + CI | **1.00** | 1.00 |
| ".ps1", "deploy step", terraform/docker — no "script"/"shell" | **1.00** | 1.00 |
| "**pwsh** automation", "**injection** risk" | **0.00** | **1.00** |

Two of three phrasings never needed the fix. The catalogue already routed them from "shell
scripting … CI scripts … entrypoint script". **The absent string was not an absent
capability** — [[measure-before-you-agree]] in its exact documented shape: *a grep answers
"does this string appear", never "is this idea covered".* We made that error while correcting
an audit that made the same one, one step earlier in the same chain.

**The first regression case was therefore invalid and was discarded.**
`r4_powershell_windows_ci` was written from the grep and pinned nothing — 1.00 in both arms,
before and after — inside a set whose SELECTION RULE says a mis-route "actually happened". It
is replaced by `r4_pwsh_injection`, an observed 0.00 → 1.00. A regression case that cannot
fail is the same defect class as a gate that cannot fail.

**What survives, restated honestly:** the *content* gap justified the work and was never in
question (0 files taught PowerShell). The *routing* gap is real but narrow — it needs a task
that names PowerShell without shell/script vocabulary **and** carries a competing signal.
Neither the audit nor our first pass had located it.

**Two probe defects surfaced by this branch, both fixed, both the same class as 11c above:**

- **Probe 28 went INERT.** It mutated `SELECTION RULE` only `if $. < 40` while the gate greps
  the whole file, so one prose mention of the token further down re-satisfied it. Pinned to
  the subject's *shape*. Now mutates every occurrence.
- **Probe 14b reported EXEMPTION DID NOT HOLD against a passing invariant 14.** It builds a
  synthetic *release* on top of whatever branch is under test; on a branch that edits a skill
  description, **invariant 29 correctly fires** and a green probe requires the whole gate
  green. The probe now declares a routing check in its own fixture, so 14 is the only thing it
  tests. Reproduced by hand in a worktree — invariant 14 printed `ok (1 terms declared, all
  resolve)` the entire time.

**Deliberately not done: invariant 28 was left alone.** Its `grep -qi` over the whole file is
wider than its intent, the same shape as invariant 11's hatch. But the incident here was in
the **probe**, and the probe is fixed; changing a gate with no incident behind it is what this
ledger argues turns gates flaky. Recorded so the looseness is known, not forgotten.

## 2026-09-14 — Three rules from the session's own failures, and the one that must NOT become a rule

Intake from a session *applying* the library, which this ledger takes on the same terms as an
external source. Three of this session's own mistakes were checked against the library before
being written up — one of them turned out to be **licensed by a rule**, which is a worse
finding than a gap.

**1. Principle 0 sent a behaviour question to the documentation.** Its taxonomy reads
"official docs … (for versions, specs, CVEs, **tool capabilities**), or a reproduced behavior
(for **bugs**)". *"What does `poetry install` do when the lock is missing?"* is a behaviour
question that reads as a tool capability, so the rule pointed at the docs — and Poetry's page
says a desynced lock produces a "Warning" while the tool exits **1**. A mechanism published
from that summary had to be retracted mid-session. Principle 0 now carries the distinction: a
doc page states intent, only running it reports behaviour, and a two-minute install settles
it. The nearest prior coverage — `sota-code-security` rules/12 §1, "assert the documented
default equals the parsed default" — is about structural tests for your *own* control's
config, not about citing a vendor doc as evidence of runtime behaviour.

**2. The routing-gap instruction never said to watch the case fail first.** It required a
regression case as proof but not that the case be *observed failing* on the pre-change tree.
Result, measured the same day: a case written to pin a PowerShell "routing gap" scored 1.00 in
both arms before *and* after, pinning nothing, because **an absent string is not an absent
capability** — a model routes on meaning and grep cannot answer reachability. The repo's own
doctrine ("watch it fail first, print your denominator, skip rather than guess") lived in
`check-invariants.sh`'s header and had never been applied to routing cases.

**3. `sota-shell-scripting` rules/01's checklist had no item for a VERDICT read through a
pipe.** The audit half of a build rule stated in three places. Its neighbours cover
*measurements* piped into a filter and background launchers; the pass/fail case — the one
reported to a human — was missing. Added with the structural fix rather than another warning:
the verdict-bearing command runs alone and unpiped, status captured on the next line,
filtering as a separate invocation.

**And the one that is deliberately NOT a new rule.** The same exit-status defect fired twice
in this session while the *rule* existed in three places (`sota-devsecops` rules/09 §5,
`sota-shell-scripting` rules/06's table, and the operator's own always-loaded agent file). A
fourth copy is the anti-pattern, not the fix — the library's own line applies: *a warning
about a reflex does not disable the reflex.* What was missing was the **audit half** (item 3)
and a mechanical habit, which belongs in the operator's memory, not here.

**Nor is it gateable, and the reason generalises.** `shellcheck -S style` already runs in CI
and SC2181 flags the `$?` form in committed shell — it reports nothing because there is
nothing to find. Both failures were in **ad-hoc commands that are never committed**. A repo
gate's reach stops at the tree; a defect that lives only in a transcript is outside every
gate in this repo by construction. That is the useful generalisation: before proposing a gate,
ask where the defect *lives*, not just whether it is mechanically checkable.

**Landed:** `sota/SKILL.md` principle 0 and the routing-gap paragraph ·
`sota-shell-scripting/rules/01` audit checklist

## 2026-09-15 — EDR field report: a git range that invents security regressions, a scanner that reads what git hides

Source: a field report from a session *applying* the library on a private security product
(kernel sensor + backend, Rust) at v1.42.1. Three findings plus a "what worked" census. Every
falsifiable claim was reproduced here before a verdict — two survived, one was adopted with a
correction to the report's own reasoning, and one proposal was rejected on the library's own
stated grounds.

### 1. `git diff main..pr` is not what the PR changes — **adopted**

**What the source says.** Triaging a bot-opened dependency PR, the reporter ran
`git diff main..pr-branch` on a lockfile, read a TLS library as being downgraded past the
previous day's advisory fix, wrote that into a commit message and drafted a PR comment. The
PR did not touch that dependency. `A..B` compares two *tips*, so everything `main` gained
after the fork renders as a deletion on the branch's side.

**Verified here, not taken on trust.** Reproduced in an isolated repo (git 2.55.0) with the
control arm: two-dot shows `-lib = "2.0.1"`, merge-base and three-dot show only the real
change. Then the discriminating case, which the report did not run — a branch four commits
behind its base: local two-dot reported **15 files, 742 deletions**; three-dot and GitHub's
compare API both reported **zero files changed**. The branch had changed nothing.

That left one claim resting on inference — that `gh pr diff` and the "Files changed" tab use
merge-base semantics — so it was measured directly rather than shipped: on a public PR **42
commits behind its base**, `gh pr diff --name-only`, the `pulls/:n/files` endpoint and a
three-dot compare each returned **11** files while the opposite direction returned **33**. The
rule states what was measured, not what the endpoint is documented to do.

**Coverage claim checked against the library, not the named file.** Positive control
(`--replace`) returned 3 files, so the instrument worked. The report's terms (`two-dot`,
`three-dot`, `tip-to-tip`, `what a PR changes`) return 0; vocabulary it did not try
(`origin/main..`, `diff baseline`) returns hits that were **opened rather than grepped** —
`sota-secrets-management` rules/04:48 uses `--log-opts="origin/main.."` and
`sota-shell-scripting` rules/01:190 uses three-dot `rev-list`, neither about diff semantics.
The owner file had **zero** `git diff` guidance in 275 lines. Genuine gap.

**Added beyond the proposal: why the habit survives.** The same token means different things
to different subcommands — `git log main..feature` is *correct* (commits in feature, not
main) while `git diff main..feature` compares tips. Verified both. The report proposed only
"two-dot is wrong", which contradicts the reader's working experience of `log` and
`rev-list`; without the asymmetry the rule reads as false and gets discarded. This is also
why `origin/main..` appears *correctly* elsewhere in our own library as a log range.

**Landed:** `sota-docs-workflow/rules/03` new **§3a**, plus the **audit half** — a checklist
item asking which range produced any "removes/downgrades/reverts" claim. The audit half is
the shape this library most often ships without.

### 2. Prose bypasses validate-before-assert — **rejected as a text change; recorded as evidence**

**What the source says.** Two false dependency claims minutes apart, both in explanatory
prose rather than in a tool call, the second contradicting a table the reporter had printed
themselves one paragraph earlier. Proposal: one sentence in `sota/SKILL.md` principle 0
naming the prose case — *"the claims that escape validation are the ones that felt like
narration."*

**Verdict: rejected, and the reporter half-argued the rejection themselves** — they graded it
*medium* confidence that the wording helps, noting it is "one more sentence in a file I had
already loaded and did not apply." That is the whole case. Principles 0 and 7 already cover
this, and principle 0 already names the mechanism the reporter identified (*"the moment after
being corrected is the highest-risk moment in a session"*) — both failures landed in exactly
that window. A rule that was **loaded and broken** is an adherence failure, not a coverage
gap, and this library's own recorded anti-pattern is answering one with another copy of the
text. The 2026-09-14 entry above rejected an identical shape for identical reasons.

**The cost is not zero, which is the other half of the reasoning.** `sota/SKILL.md` is the
only file loaded in *every* session; it sits at 470 of 500 lines, and its measured cost is
tokens-per-load, not line count. Spending that budget on a sentence its own author doubts is
the worst available trade.

**The occurrences are accepted as evidence** and are not in doubt — both refuted by registry
metadata fetched in-session. Treat the two as **one correlated observation** (same session,
same topic, minutes apart), as the report itself asks.

### 3. A working-tree secret scan does not honour `.gitignore` — **adopted with a correction**

**What the source says.** A gate went red on secret scanning: history pass clean over 328
commits, working-directory pass 22 hits, all in one untracked **gitignored** log dump left in
the repo root by tooling, all false positives on `key=value` shapes, with `git status` clean
throughout. `gitleaks dir` treats the path as a plain directory.

**Verified — and the first attempt refuted a true finding.** Planting the canonical AWS
documentation key returned "no leaks found", because gitleaks allowlists it. With a positive
control the result inverted: the same planted credential (`glpat-` shape) in a *visible*
untracked file and in a **gitignored** one both returned `leaks found: 1`, `git status
--porcelain` empty throughout, on gitleaks 8.30.1. An unverified absence would have thrown
away a correct report — the failure mode `sota/SKILL.md` principle 3 exists for.

**The correction.** The report states that in the target repo `*.local.md` "is not ignored".
**False** — `git check-ignore -v` names `.git/info/exclude:10`, so it *is* ignored, via the
mechanism agent scaffolding conventionally uses rather than the tracked `.gitignore`. The
load-bearing half of the finding is untouched and is the half worth keeping: **ignore status
is irrelevant, because a directory scanner never consults it.** The correction matters
because the report's framing invites the wrong fix (add an ignore rule), which would not have
prevented the red gate.

**Landed:** `sota-secrets-management/rules/04` scanner hygiene + an audit-checklist item
(triage a red working-tree scan **by file** before reading any diff — the reported session
lost its first ten minutes suspecting the commit); and `commands/sota-report.md`, whose own
instruction said to write the report into the repo root and justified it with a fact about
**SOTA-skills**. That is a self-inflicted defect in our own tooling: the caveat "yours may
not be" was already in the text and changed nothing about the instruction.

### 4. "What worked" — **recorded, no change proposed**

A 5–0 split: every code-level error was caught by a mechanical control (a derived-number test
that caught a stale metric *and then* a hand-maintained enumeration the author did not know
existed; a docs-contract test; `clippy -D warnings`; the secret gate; mutation probes that
each reddened a *different* test). No prose-level error was caught by anything. Consistent
with this library's own position that a control ending in an exit code is worth more than a
paragraph — and it is the strongest available argument for the negative-control harness. One
session on one repo with unusually good gates; recorded as observational, not as a lift.

### Considered by the reporter and NOT proposed — reviewed, all three upheld

`rg -E` is `--encoding` (correctly withheld: it fails **loudly** with a usage error, and
`rules/06`'s value is that every entry is a *silent* failure); `str.replace` no-ops
(correctly identified as already covered, and as a second instance of finding 2); bot PRs
bypassing CI (correctly judged a property of one repo's workflow config). Reviewing this
section is worth the time — on past reports it is where the reporter's judgement is
best-calibrated, and here it needed no overturning.

## 2026-09-15 — Two more field reports: the library's own checklists were manufacturing findings

Two independent reports at v1.42.1 — one from a static-analysis pipeline, one from a systems
project. Four proposals, all four adopted, every falsifiable claim reproduced here first. The
sharpest is **finding 3**: the defect was in *our* text, shipped in nine skills, and no gate
could see it.

### 1. `rg -rn` silently drops the line numbers you asked for — **adopted**

**Third independent occurrence**, all with `rules/06` §2a installed and two with it loaded in
context. §2a's existing tell is *"the content was implausible"*, which requires judging
unfamiliar code — weakest exactly when you need it. The reporter proposed a mechanical
replacement and it reproduced here on the same ripgrep 15.2.0: `-rn` parses as `-r n`, so the
`-n` is eaten as the replacement template and the output comes back `path:content` instead of
`path:LINE:content`. **If you typed `-n` and the line numbers are missing, the content has
been rewritten** — checkable with no knowledge of the file.

The calibration line matters as much as the tell: three reporters, rule installed each time.
The lever is not stating it louder. Recorded in §2a so the next proposal to "make it bolder"
has something to read.

### 2. "Suspiciously slow" indicts the measurement — **adopted**

`sota-performance` rules/01 §9a covered *"is any stage suspiciously **fast**?"* — one
direction only. The reporter extrapolated a 6x test-suite regression from a backgrounded run
and **wrote it to a durable memory file** before discovering the cause: backgrounded jobs on
that harness carry `nice 5` while the foreground shell is `nice 0`, under load 5.9–8.6.

**Coverage verified with a control**, and with vocabulary the report did not try: `nice` hits
2 files, both false positives (*"nice backstop"*, *"Nice — your first deploy"*); `renice`,
`scheduling priority`, `noisy neighbo` → 0. §9a read in full rather than grepped — genuinely
one-directional. One correction to the report's own numbers: its control `suspiciously fast`
is **1** file exactly, not 2 (`suspiciously` in any form is 4); the conclusion is unaffected.

**The asymmetry worth keeping:** §3 item 5 already says "pin the environment", and it does
not reach this case because it is framed for a deliberate benchmark. This reporter was
running a suite and glancing at a clock.

### 3. Our own audit checklists shipped a finding-manufacturing idiom — **adopted, 13 sites fixed**

**The library was the source of the defect.** `cmd … 2>/dev/null || echo "missing X"` was
shipped in the audit checklists of **nine skills**. The `||` arm is meant to mean *"the
pattern was absent"*; it fires on **every** non-zero exit, and `2>/dev/null` has already
destroyed the evidence of which. Reproduced with a control arm:

```
grep -rnE 'Werror|/WX' CMakeLists.txt cmake/ Makefile_absent 2>/dev/null || echo "no -Werror"
  CMakeLists.txt:1:add_compile_options(-Werror)      <- the match
  no -Werror                                          <- and the verdict contradicting it
exit 2 = unreadable/missing path · exit 1 = genuinely absent · `||` cannot tell them apart
```

`ls a b c 2>/dev/null || echo "missing"` has the identical bug and was also shipped — `ls`
prints what it found *and* exits non-zero. **The failure is directional: it manufactures
findings about someone else's codebase**, which an auditor then files.

**Fixed at every site** (13 lines across `sota-c-cpp`, `sota-dotnet`, `sota-golang`,
`sota-jvm`, `sota-php`, `sota-python`, `sota-ruby`): `grep` sweeps now use a single root with
`--include` globs, so no missing-path branch exists; `ls` checks pipe to `grep -q .`, so the
verdict fires only when nothing was found. Both replacements verified in **both** directions.
Three surviving `2>/dev/null ||` instances are legitimate and were left: a documented
best-effort write to `/dev/termination-log`, and a `pip-audit` fallback chain.

**Why no gate caught it:** a checklist line is a control, and nothing in this repo executes
the shell inside a fenced block. That is a genuine gap, recorded rather than papered over.

### 4. A search pattern beginning with `-` is parsed as a flag — **adopted as §2c**

`rg -c -F '- [ ]' . 2>/dev/null` reported nothing where there were 65 matches; the pattern was
consumed as a flag, `rg: unrecognized flag -` went to the suppressed stderr, and `$?` after a
pipeline reported the last stage. Reproduced exactly (exit 2, empty output; `-e` returns the
real answer).

**Strengthened beyond the report with a differential it did not run.** The report's `printf`
instance did not reproduce on first attempt, which looked like a refutation. It is
**shell-dependent**: bash 5.3 builtin `invalid option` exit 2 · zsh 5.9 builtin **succeeds**
exit 0 · `/usr/bin/printf` `illegal option` exit 1 · `/bin/sh` exit 2. A contributor who
tests this in zsh concludes the trap is imaginary — which is why the rule now carries the
table rather than a single example.

### Structural consequence: `rules/06` was at exactly 500 lines

All four proposals target it, and it had **zero** headroom. Split at the seam its *citations*
name, not its headings: the §2 family carries **25** citations (§2 15, §2b 6, §2a 4) against
§5's 10 and §3+§4's 8 — so §3 and §4 (blast radius, process-table exhaustion) moved to a new
**`rules/08-ad-hoc-side-effects.md`**, keeping their section numbers. Coherent on theme too:
`rules/06` is now *"the check returned the wrong answer"*, `rules/08` is *"the check did
damage"*. Invariant 18 caught **7** references broken by the move, including three inside the
moved file itself and one in `check-negative-controls.sh`; invariants 10 and 15 caught the
missing index and library-map rows. Historical CHANGELOG and ADOPTION-LOG citations were left
alone — they are records, correct when written.

### Considered by the reporters and NOT proposed — all upheld

A `sota-resume` / `sota-devsecops` scope conflict (the router's narrower-wins rule already
resolves it; the residue — that the tie-break is phrased for two *domain* skills while this
was *process* vs domain — is one case and does not license a rule change). `sota-resume`'s
"ALREADY DONE is usually the largest class" being false on one unusually disciplined repo
("usually", n=1). And making the `rg -r` warning louder, which §2a's own history refutes.

**One success recorded with no change proposed:** a reporter ran `type grep` at session start
and found it shimmed to `ugrep --ignore-files`, which honours `.gitignore` — every gitignored
path would have been silently outside a 5,663-file inventory. The positive-control rule paid
for itself; worth knowing which mechanisms do.

## 2026-09-15 — `rg --no-ignore` is a decoy, not a fix (operator's own measurement)

Source: the operator's always-loaded agent file, which had accumulated a measured `rg` trap
locally. That file's own standing instruction is that traps belong in the library rather than
in it, so this is intake from the same session that produced the finding.

**The claim.** `rules/06`'s searcher-exclusion table already showed `rg` defaults finding
**1 of 4** and `rg --hidden --no-ignore --follow` finding **4 of 4**. What it did not say is
that **`--no-ignore` alone does not rescue hidden directories** — and that it is the flag
people reach for, because it sounds like "stop excluding things".

**Reproduced here**, four arms on one fixture (hidden dir, gitignored file, plain file):

```
rg -l PAT .                   -> 1 match   (1 file searched)
rg -l --no-ignore PAT .       -> 2 matches (2 files searched)  <- MORE files, still no .claude/
rg -l --hidden PAT .          -> 2 matches (21 files searched) <- finds the hidden one
rg -l --hidden --no-ignore .  -> 3 matches                     <- all of them
```

The operator's own figures on a real repo: **1042 files vs 404** under `--no-ignore` while
missing the same matches; `--hidden` takes 404 → 576 files and 2 → 4 matching files.

**Why it is worth a row rather than a footnote.** The failure is *confidence-increasing*: the
run that misses the matches searches strictly more files than the default, so the operator
comes away more sure of the absence. Same family as `grep -r` over symlinks. The concrete
casualty named in the report is an agent-rules tree — `rg PAT .` never enters `.claude/`,
`.github/` or `.githooks/`, which is precisely where an audit of agent instructions would
look.

**Landed:** `sota-shell-scripting/rules/06` §2 table (one row) plus a short paragraph.

**Structural note, recorded because it will block the next contributor.** `rules/06` is now
at **499 of 500 lines** — one line of headroom, immediately after being split earlier the
same day (§3/§4 → `rules/08`). The §2 family is the file's centre of gravity and keeps
growing because it is where search traps land. **The next addition needs a second split, not
a squeeze**, and the seam should again be chosen by citation weight rather than heading
tidiness.

## 2026-09-16 — Findings 5 & 6: scaffolding is a distinct blind spot, and one of our own rules was platform-blind

Source: two further findings appended to the 2026-09-15 static-analysis report. Both are
**"rule in context, broken anyway"** — the category rejected as a text change earlier the same
day. These are adopted, and the difference is the reason.

### Why these are adopted where the earlier one was rejected

The EDR report's finding 2 proposed a sentence about *prose vs commands* and its own author
graded it medium — it restated principle 0 in a file already loaded and unapplied. **These two
carry a mechanical tell instead of an exhortation**: *"the tell is `&&` after a pipeline"* is
checkable against text you already have, and greppable. That is the same property that made
the `rg -rn` line-number tell worth adopting while "state it louder" was not.

They also **narrow the hypothesis usefully**, as the reporter argues: the reflex fires on
commands *whose output you will believe*, and not on commands that merely **orchestrate**.
That is testable and more actionable than "prose vs commands". Graded, as the reporter asks,
as **one observation with two instances**, not two findings.

### 5. A piped exit status let a red gate run a push — **adopted**

`make ci 2>&1 | tail -10 && git push origin main`. The gate failed; the push ran, because a
pipeline's status is the last stage's. Reproduced: `(exit 1) | tail -1; echo $?` → `0`, and
`&&` fires. The push then started a *second* concurrent gate run that collided with the first
over a shared test binary (`Text file busy`), and the visible symptom was a kernel conformance
test failing to observe an event it had caused — **indistinguishable from a product race**, in
a suite already carrying four undiagnosed intermittent failures. The tell was **duration:
1599s against ~757s for identical code minutes earlier.** Had the reporter re-run to green and
moved on, a fifth phantom flake would have joined the four.

Landed in `rules/01` §3 beside the existing `PIPESTATUS` material — which stated the mechanism
correctly and was, by the reporter's account, read that same turn.

### 6. A `pgrep -f` waiter that matched its own argv — **adopted, and it corrected OUR rule**

The reporter's waiter never exited. `rules/01:145` already said so. **But our rule stated it
universally, and it is platform-scoped** — found while reproducing, not from the report:

```
Linux, procps-ng 4.0.6 : loop Terminated by timeout  -> self-matched, never exits
macOS, BSD pgrep       : loop exited after 0 iterations -> no self-match
```

Positive control on macOS confirms `pgrep -f` *does* find a separate carrier process, so the
macOS negative is about the **watcher**, not a broken instrument. **A macOS operator who tests
this concludes the trap is imaginary and ships the loop into Linux CI** — the same shape as
the `printf` leading-dash differential adopted hours earlier, and as `-r` over symlinked dirs,
which this file already states per binary. The rule now names both.

**Method note worth keeping.** The first three reproduction attempts were **confounded by my
own orphaned process** — a malformed `cat >` waiting on stdin, whose argv carried the pattern
and made a healthy loop look like it self-matched. `ps -axo pid=,ppid=,command=` localised it
(*parentage before blame*, `rules/03` §3a). The confound was the entire effect: after killing
the orphan, the same arm exited cleanly. **A reproduction that confirms the rule you expect is
exactly when to check what else is in the process table** — and the orphan was itself
scaffolding, which is the finding.

## 2026-09-16 — Closing the gate gaps the posture audit found: invariants 32 and 33

Source: an audit of this repo's own control surface, prompted by the 2026-09-15 field reports.
Four gaps were named; two are closed here as gates, one is closed as a settings change the
repo cannot make for itself, and one is **not closeable and is stated as such**.

### Gap 1 — two CI jobs could not block a merge — **handed to the operator**

`Executable claims (ubuntu-latest)` and `(macos-latest)` run on every PR and were **not
required status checks**: the claims could stop holding and the PR would still merge. This is
the 2026-08-05 incident repeating (that one: `Negative controls` and `Shell lint` ran and could
not block). The API call is a repository-settings write and was refused to the agent, so it is
handed over with the exact command. **`AGENTS.md` no longer states the number** — it rotted
precisely because a job was added and never made required, so it now points at
`gh api … /branches/main/protection` instead.

### Gap 2 — the guidance's shell was linted by nothing — **closed as invariant 32**

`cmd … 2>/dev/null || echo "missing X"` shipped in the audit checklists of nine skills. The
gate flags it inside **prescriptive** fences only.

**The design changed under measurement, twice.** The first plan was "shellcheck every fenced
block", on the stated assumption that it would have caught the 13 sites. **It would not** —
`shellcheck -S style` exits **0** on the exact line, because the defect is semantic, not
syntactic. That claim was published in the audit summary and is **retracted here**. The second
measurement killed the general form too: extracting all 161 `sh`/`bash` blocks and running
`shellcheck -S error` yields **19** complaints, nearly all artifacts of a *fragment* (`local`
outside a function, half a loop shown for illustration). A gate that opens red gets disabled
(rules/12 §2), so the gate that shipped is narrow and targeted.

**Known-good / known-bad, both measured before writing the check:** 0 hits on today's tree,
**13** on `81b437a~1` — exactly the sites fixed in #386. Two probes, because the check must
tell its own documentation from its input: `rules/06` §2d *demonstrates* the broken form inside
a ```console transcript, and a gate that fired on that would make the section unwritable.

### Gap 3 — "nothing checks whether a rule is true" — **not closeable; scope stated**

Left open deliberately. "Is this claim correct" is semantic, and this ledger's own argument is
that a fuzzy gate gets disabled and leaves you worse off. What *is* tractable is the executable
slice: `scripts/check-claims.sh` runs the library's executable claims as real commands — run
it for the count, which is deliberately written nowhere because it grows — and invariant 32 now
covers one recurring shell idiom. **That slice was widened the same day** (see the next entry). **Invariant 31 gates the record, not the truth** — that
remains the honest description, and the residual is named in `docs/WHY-COMPLETENESS-RESIDUAL.md`
terms rather than papered over with a gate that cannot fail.

### Gap 4 — uneven enforcement density — **closed as invariant 33, a declaration**

`skills/**` (70,200 lines) carries ~20 of the checks; `commands/**` — 494 lines of instructions
an agent **executes every session** — carried two, and nobody had decided that.

**A ratio was considered and rejected.** An invariants-per-KLOC floor is arbitrary: the right
number for a two-file asset directory is not the right number for 70k lines of instructions,
and a threshold nobody can defend gets tuned until it passes. Invariant 33 instead requires
every top-level area to appear in a **Coverage by area** table with the gates that cover it
**or a stated reason it is thin** — the same declaration shape as 19 (known-bad or pinned
reason), 27 (deferral names a trigger) and 28 (case set declares its selection rule).

**Why it earns a gate**, against this ledger's three filters: it has already failed
(`commands/` arrived 2026-09-14 under-covered); it fails silently (an ungated area is
indistinguishable from a covered one); it is mechanically checkable (enumerate, compare). And
the rate says it recurs — **ten areas in the repo's first three months**, about one per ten
days.

**The table states two gaps rather than hiding them:** `.github/` `run:` blocks are unlinted
(shellcheck reaches `*.sh` only — the same class 32 closes for skills, not gated because
extracting YAML scalars reliably is more machinery than two blocks justify), and `evals/`
Python is unlinted beyond the scorer tests. A row that says "thin, and here is why" is the
point of the gate.

## 2026-09-16 — Widening the executable-claims slice, and two defects it found in itself

Follow-on to the gate audit: gap 3 ("nothing checks whether a rule is true") is not closeable
in general, but its **executable slice** is, so the slice was widened from the filesystem and
quoting traps it already covered to **every silently-false-answer claim landed on 2026-09-15/16**.

**The selection rule**, stated so the set cannot quietly become "whatever was easy": a claim
earns a test if getting it wrong **changes a conclusion someone acts on**. Not "interesting" —
*load-bearing*. Nine added, each naming the rule it backs:

| # | claim | backs | why it is load-bearing |
|---|---|---|---|
| 12 | `rg -rn` parses as `-r n`; content rewritten, line number gone | rules/06 §2a | fabricates false *content* |
| 13 | a pattern beginning with `-` is parsed as a flag | rules/06 §2c | clean zero, reason on suppressed stderr |
| 14 | `\|\| echo` fires on grep's exit 2 as well as 1 | rules/06 §2d | manufactures findings about other people's code |
| 15 | `pgrep -f` self-match is **platform-split** | rules/01 §3 | a macOS-green test ships a never-exiting loop into Linux CI |
| 16 | a pipeline's status is the last stage's | rules/01 §3 | let a red gate run `git push` |
| 17 | leading-dash `printf`: bash rejects, zsh accepts | rules/06 §2c | a contributor testing in zsh concludes the trap is imaginary |
| 18 | `--no-ignore` does not reach a hidden dir | rules/06 §2 | searches *more* files while missing the same matches |
| 19 | two-dot `git diff` renders main's commits as deletions | `sota-docs-workflow` rules/03 §3a | invents a supply-chain regression |
| 20 | a directory secret scan ignores `.gitignore` | `sota-secrets-management` rules/04 | a gate fires on a file `git status` never shows |

**Two defects found by watching it fail, both in the new tests rather than the rules.**

1. **Claim 16 failed on its first run** (`rc=1`, not 0) — and the rule was right. This harness
   runs under `set -uo pipefail`, where a pipeline's status *is* the leftmost failing command's,
   so the test measured **the harness's own options** rather than a default shell. It now runs
   the arm in `bash -c`. The instrument was the confound, which is the same shape as the claim
   it was testing (`sota-code-security` rules/15: your instrument is a control).
2. **Claim 20 skipped on a failed positive control** — the fixture was `glpat-` plus twenty
   `A`s, too entropy-poor for the rule to fire, so it was **inert**. The control caught it,
   exactly as it caught the allowlisted AWS documentation key the day before. The fixture is
   now assembled from `/dev/urandom` at runtime, which also keeps a credential-shaped literal
   out of the repo.

Both were caught because the harness was run and read, not because it was written carefully.
**Measured after the fixes: 22 run, 0 skipped, 0 failed** — up from 11 run / 2 skipped — on a
macOS host carrying ugrep, ripgrep, zsh and gitleaks.

**Scope corrected the same day, during closure.** "On macOS" was the wrong attribution: the
run count tracks the **toolchain, not the platform**. The same commit on CI reports **15 run /
7 skipped** on its macOS runner and **21 run / 1 skipped** on ubuntu, because a missing binary
skips with a printed reason instead of passing silently — which is the harness behaving
correctly. A reader checking CI against "22 on macOS" would have concluded the record was
wrong. The count stays out of the prose deliberately; run the script and read its
denominator.

## 2026-09-16 — External audit of v1.42.1: 18 findings verified, 18 fixed

Source: a commissioned adversarial audit against the v1.42.1 zip, dated 2026-09-15. Verified
against **current main**, not the audited tree.

### The citation check first, because the last external audit failed it

The 2026-09-14 external audit had **every line number invented**. This one does not: **10 of
10 spot-checked citations resolve to real text at the cited lines**, and the two locally
reproducible findings (F1's greps, F12's arithmetic) reproduce exactly. That difference is
why this one was worked through in full rather than sampled.

### Verified by primary source or execution, then fixed

| # | finding | how it was settled |
|---|---|---|
| F1 | Next.js audit greps find nothing | **Reproduced**: BRE parens are literal → exit 1; the `(?!…)` command errors. Corrected commands verified on the same fixture |
| F2 | anonymous-auth "bridge" to `system:authenticated` | K8s docs: anonymous gets `system:anonymous` + `system:unauthenticated`; `system:authenticated` only on success |
| F4 | `updateTag` allowed in Route Handlers | Next.js docs: *"can **only** be called from within Server Actions"*, with an explicit throw example |
| F5 | "functions and class instances can't cross" | React: `Date`, `Map`, `Set`, promises, JSX and **Server Functions** are serializable |
| F6 | `ipBlock` matches pod IPs (Cilium-scoped file) | Cilium: *"CIDR-based selectors do not match in-cluster entities"* by default |
| F7 | PgBouncer "breaks LISTEN/NOTIFY, temp tables" | Feature matrix: `LISTEN` Never but **`NOTIFY` Yes**; `ON COMMIT DROP` temp tables **Yes** |
| F8 | Django "works in dev, serializes in prod" | Django **raises `SynchronousOnlyOperation`**; blocking needs `DJANGO_ALLOW_ASYNC_UNSAFE` |
| F9 | CRA routes presented as a categorical split | Art. 32(1) offers Module A; 32(2) triggers only where standards are *"not applied or applied only in part"* |
| F10 | standalone link text cited as 2.4.4 | 2.4.4 (A) permits link text **plus programmatically determined context**; standalone is 2.4.9 (AAA) |
| F11 | dotenv "wins over the platform" | **Executed** on dotenv 17.4.2: default `config()` leaves an already-set var alone |
| F12 | "54% under-count" | Under-count is **35%**; 54% is the inverse direction |
| F13 | "wrong for four months" | 2026-08-14 → 2026-09-12 = **29 days** |
| C1 | "never hold a lock across an await" | Contradicts `sota-rust` rules/04, which prescribes `tokio::sync::Mutex` for exactly that case |
| C2 | detached-task example | Its callback only discards from a set; never observes the exception the sibling skill requires |
| C3 | freshness policy says "never state current version" | `sota-php`'s **description** said "8.5 current" |
| R2 | DMARC ownership invisible to routing | Description had **0** mentions of SPF/DKIM/DMARC/email; body names DMARC 12× |
| G1 | no embedded/RTOS owner | The file already says *"No skill in this library owns those today"* — in the body, after loading |
| O1 | self-audit sold as separately measured | `workflow = BUILD_WORKFLOW if gate else "\\n\\n"` drops **all four** steps |

**Two fetch failures worth recording, both caught by reading rather than trusting.** The
EUR-Lex page returned empty twice — *a fact about the fetcher, not the source*
(`sota/rules/01` §3) — so F9 was settled from two mirrors of the Article 32 text. And the
first of those mirrors produced a "Key Findings" conclusion that **contradicted the verbatim
paragraph it had just quoted**; the quote was right and the summary was backwards, which is
principle 7 in miniature. A second source confirmed the quote.

### Why the description fixes were compressions and not splits

Asked directly. **Splitting relieves the 500-line *file* cap and does not relieve the 1024-char
*description* cap**, because splitting a description means adding a skill — and the shared
listing budget is already ~**38,240 chars against an 8,000 default** (README). Over budget,
skills render name-only and cannot be auto-selected at all, so a 43rd skill degrades the other
42. `sota-c-cpp` and `sota-network-security` therefore paid for their new terms by dropping
duplicates (`MISRA`, `CERT C`, `memory safety` each appeared twice in one string;
`WireGuard` and `169.254.169.254` likewise). A dedicated embedded/RTOS skill remains the
*full* fix for G1 and is a separate project; what shipped is the audit's own stated interim.

### Not fixed here

F3 (Tokio cancellation-safety classification) is left for a follow-up: the correction needs
the per-operation table copied from the Tokio `select!` docs rather than a one-line edit, and
getting it half-right is worse than the current wording. O2–O5, R1 and G2 are design and
scope arguments rather than factual errors; they are recorded, not actioned, and O2's missing
arm is already conceded in the runner's own docstring.

## 2026-09-16 — F3 closed: the Tokio cancellation-safety table, copied rather than paraphrased

Deferred from the external-audit intake above because it needed the per-operation list, not a
one-line edit. Transcribed from the `select!` docs
([cancellation safety](https://docs.rs/tokio/latest/tokio/macro.select.html#cancellation-safety),
read 2026-09-16).

**Three errors in one bullet, and the two that matter are inversions**, not omissions:

- **`Notify::notified` was listed as cancel-safe.** Tokio lists it as **not** safe.
- **"`Mutex::lock` is safe"** — Tokio lists `Mutex::lock`, `RwLock::read`, `RwLock::write`
  and `Semaphore::acquire` as **not** safe.
- **`recv()` was attributed to `watch`.** The cancel-safe `watch` method is **`changed()`**;
  the sibling channels use `recv()`, which is exactly why the slip is easy.

**The repair is not just the list — it is the two *reasons*.** Tokio gives separate causes,
and the audit was right that collapsing them mislabels the severity. Partial-I/O
(`read_exact`, `read_to_end`, `read_to_string`, `write_all`) loses **bytes** and
desynchronises a stream. The lock/semaphore/notify row loses only **progress**: the docs say
these *"use a queue for fairness and cancellation makes you lose your place in the queue"* —
nothing is corrupted. So the audit checklist now rates them differently and says plainly that
**reporting a fairness-queue cancellation as data loss is a false finding**. A rule that
over-rates a severity manufactures work in someone else's repo, which is the same failure
class as invariant 32's idiom.

The table is dated and marked per-version, because the classification is a property of the
tokio release, not of async Rust.

## 2026-09-16 — F2's second half, settled with a browser after WebFetch fell back to recall

The external-audit intake recorded F2 as verified on its **first** half only: anonymous
requests get `system:anonymous` + `system:unauthenticated`, quoted exactly. Its **second**
half — that Kubernetes binds `system:public-info-viewer` to *both* groups by default, which is
what makes "bound to a broad group" unable to carry Critical on its own — came back from a
**truncated page**, where the fetcher said so and answered from recall instead. That was
recorded as unconfirmed and the claim shipped anyway on the audit's say-so.

**Re-fetched with Playwright**, reading the default-bindings table out of the DOM rather than
asking a model to summarise it:

| role | binding, verbatim |
|---|---|
| `system:basic-user` | `system:authenticated` group — *"Prior to v1.14, this role was also bound to system:unauthenticated by default."* |
| `system:discovery` | `system:authenticated` group — same v1.14 note |
| `system:public-info-viewer` | ***"system:authenticated and system:unauthenticated groups"*** — *"Introduced in Kubernetes v1.14."* |

**The claim holds.** And the recall fallback had a **factual error in it**: it listed
`system:discovery` as bound to both groups, which has been false since v1.14. Shipping on that
summary would have put a wrong default into a severity judgement.

**Landed:** `sota-kubernetes/rules/02` — the binding is now quoted rather than paraphrased, and
a new bullet carries the **v1.14 boundary**, which inverts the check on an old cluster: before
v1.14 `basic-user` and `discovery` *were* bound to `system:unauthenticated`, so on a pre-1.14
cluster that is the shipped default and on a current one it is a finding. Version numbers as
semantic boundaries are exactly the permitted use under this repo's no-rot-prone-pins rule.

**Method, now a standing instruction:** when a fetch returns empty, truncated, or a summary
that contradicts its own quotes, **escalate to the browser tools on the same URL** rather than
routing around it to a mirror. Two instances this session — this one, and EUR-Lex returning
empty twice, where the mirror used instead produced a conclusion contradicting the paragraph it
had just quoted.

## 2026-09-16 — EDR report II: the finding was already landed, the *version it cited* was not

Source: `FIELD-REPORT-EDR-2026-09-16`, the successor to the 2026-09-15 EDR report. Its stated
finding — a status-discarding pipe in scaffolding (`| tail && git push` after a red gate) and a
self-matching `pgrep -f` waiter — **was already intaken and shipped** when the same material
reached this session as a direct paste: `sota-shell-scripting` rules/01 §3 carries the
scaffolding paragraph and the `&&`-after-a-pipeline tell, and rules/08 §4 covers the waiter.
The report explicitly proposes nothing for the second instance on the grounds that restating it
*"would make the library worse"*, which is the right call and is upheld.

**What the report caught that we did not: a version that never existed.** Its header notes the
installed tree *"contains `rules/08`, whose header says it split out at v1.43.0"*. There is no
v1.43.0. The split shipped in **v1.42.2**. The sequence is the defect: the version was written
into the prose when the file was created, **guessing** the next cut would be a minor; at the
cut it was correctly determined to be a *patch*, and nothing went back for the
forward-references. A reader following that pointer looks for a release that does not exist.

**Swept, not spot-fixed — and the sweep found two older ones.** Comparing every `v1.X.Y` in
tracked markdown against `git tag -l`:

| reference | claimed | actually shipped in |
|---|---|---|
| `rules/08` header, `rules/06` ×2, library map, INVARIANTS.md | `v1.43.0` | **v1.42.2** (5 sites, this session's) |
| `sota-shell-scripting/rules/05` header — split out of `rules/01` | `v1.36.4` | **v1.37.0** (pre-existing) |
| ADOPTION-LOG — `sota-code-security/rules/12` §1d landed | `v1.41.3` | **v1.42.0** (pre-existing) |

Both older ones are the same shape: a version written before the cut decided it.

**Gateable, and measured before proposing.** The naive predicate — every `vX.Y.Z` in prose must
be a tag — is **not viable**: 35 distinct unresolved strings, nearly all legitimate
third-party versions (Harbor `v2.5.1`, `actions/checkout` `v7.0.1`). That gate opens red and
gets disabled. Narrowed to **our own `v1.*` namespace** it resolves to 4 distinct strings: the
two real defects above and `v1.2.3`/`v1.2.4`, unambiguous placeholder image tags in devsecops
examples. So a gate is viable *if* those placeholders move out of the `v1.*` namespace first —
**recorded as a measured proposal, not built**, because it needs that cleanup and the decision
is the maintainer's.

**The aside the report offers is also kept:** `sota-devsecops` rules/09 covers what a *green*
gate is worth; the converse is that a **red** gate's log is truncated by the next run, so
without archiving it the cause is unrecoverable. That is what made this incident attributable
rather than a fifth phantom flake. Not actioned here — it belongs beside rules/09's existing
material and deserves its own read of that file.

## 2026-09-16 — The red gate's log, and a correction the reporter shipped after we did

Two items from the same source: the 2026-09-16 EDR report's closing aside, and an update the
static-analysis reporter made to a finding we had **already landed**.

### 1. Re-running a failed check destroys the evidence — **adopted as `rules/11` §4a**

`sota-devsecops` rules/09 §4 already required a gate that *classifies* its own failure to
publish that verdict durably, because the executor is reaped. **This is the harder case: the
gate did not know why it failed.** The line that explained the incident —
`cp: cannot create regular file '/tmp/<bin>': Text file busy` — is incidental output nobody
designed as a diagnostic, and the natural next action, running it again, is what deletes it.

The visible symptom was a kernel conformance test failing to observe an event it had caused:
**indistinguishable from a product race**, in a suite already tracking four unexplained
intermittent failures. Re-running to green would have added a fifth. **A flake you cannot
explain is often not a flake — it is an unread log**, and a "known intermittent" list built
that way is a list of runs whose evidence was overwritten.

**Structural:** `rules/09` was at **498 of 500**. Split at the seam the content itself draws —
§1–§3 ask *does the gate fail, and does failing matter*; §4–§6 ask *can anyone find out why* —
so the evidence half moved to **`rules/11-after-the-gate-fails.md`**, keeping section numbers.
Invariant 18 caught **12** references broken by the move, including four inside the moved and
remaining files themselves; invariants 10, 15 and 6 caught the missing index row, library-map
row and file count. Every one was repointed and re-checked, not assumed.

### 2. "6x slower" was **1.41x** — the reporter corrected it after we shipped

`sota-performance` rules/01 §9a landed on 2026-09-15 carrying that report's figure: a lane at
2% after twelve minutes extrapolated to a **6x** regression. **The run finished at 3190s =
53m10s — 1.41x.** The reporter updated the report and, to their credit, says the update is the
more useful half.

**Two errors were stacked, and the one we shipped as the lesson was the smaller.** The nice
penalty is real and worth ~41%. The 6x came from somewhere else entirely: **arithmetic on a
progress percentage**. A test runner's early progress is dominated by collection and
front-loaded heavy cases, so it is not linear and multiplying it out means nothing.

§9a now leads with that, because it generalises further than the harness detail: *a percentage
that moves non-uniformly is a progress indicator, not a clock, and the first 2% of a suite is
its least representative slice.* Recorded as a **correction to shipped text**, not a new
finding — and as evidence for keeping the "date every number to its source" discipline, since
the number that needed revising was one we had already published.

## 2026-09-21 — gap-check 2 of 9: sota-golang against gosec, and a denominator that was wrong three times

**The denominator took four attempts, and the library corrected me.** For the record, because
the failure mode is the point:

| source | answer | what was wrong |
|---|---|---|
| `strings` on the gosec binary | **61 IDs** | dismissed as containing false positives — **it was right** |
| official docs rules index | 7 | my fetcher read only the sidebar |
| `rules/rulelist.go` @ v2.29.0, summarised by fetch | 38 | dropped G601 |
| `rules/rulelist.go` @ v2.29.0, **curl + parsed locally** | 39 | correct, but **only half the registry** |

The resolution came from the skill under audit: `sota-golang` cites **G113, G115, G118,
G408**, none of which are in `rulelist.go`. That is because **gosec keeps two registries** —
`rules/rulelist.go` (39) and `analyzers/analyzerslist.go` (22), the SSA/taint-based checks.
**39 + 22 = 61, reconciling exactly with the binary extraction I had rejected as implausible.**

A denominator taken from `rulelist.go` alone silently omits every taint-analysis check
(G701–G710) and the whole modern HTTP set (G119–G124) — which is where the real gaps were.

### Adopted

| gap | gosec | landed |
|---|---|---|
| cookie security attributes — `SetCookie` 0 hits, `HttpOnly`/`SameSite` 0 across the skill | G124 | `rules/04` §4a |
| open redirect, and **client-side header propagation across a redirect to another host** | G710 G119 | `rules/04` §4b |
| temp files + file/directory permission modes | G303 G301 G302 G306 G307 | `rules/05` §4a |
| `ssh.InsecureIgnoreHostKey`, and `encoding/gob` on untrusted input | G106 G408 G709 | `rules/05` §4b |
| the skill's own note called G113/G118/G408 "rules" | — | corrected to **analyzers**, with both registry sizes stated |

**Rejected**: crypto clusters (G401/G405/G501–G507, G407) — already delegated at `rules/05`:215
*"algorithm choice and parameters are owned by sota-code-security 04"*, which is the
delegation this same session had to **add** to `sota-python`. Go was already right.
Also rejected: G102 bind-all (infra), G116 trojan-source (language-agnostic), G504 net/http/cgi
(legacy), G707 SMTP injection (niche).

### A shipped check that could never fire

The first permission grep was
`(WriteFile|Mkdir(All)?|Chmod)\([^,]+, *0o?…` — `[^,]+` cannot span the **second** comma, so
it could not match a three-argument `os.WriteFile(p, b, 0o644)` at all. Caught by running it
against a fixture, not by review. The replacement flags a mode where either the group or
other digit is non-zero, verified to flag `0o644/0o755/0o640/0o660` and pass `0o600/0o700`.

**Invariant 6 then caught the README hero line count** (70k → 71k) on the same change, which
is the count-bearing-surface gate doing exactly its job.

## 2026-09-21 — the first external-guide gap-check: sota-python against Bandit's own test registry

**Intake shape: a gap-check against an external authoritative enumeration**, the method this
library already used for Go (OWASP Go-SCP) and Rust (ANSSI). **Denominator: 75 tests**, read
from Bandit 1.9.4's own registry (`plugins_by_id` + `blacklist_by_id`) rather than its docs
page — **the docs page returned ~50 tests with B3xx/B4xx missing entirely and B324 misfiled
under B2xx**, so the published list would have produced a wrong denominator in both
directions.

Swept as 29 concept clusters over all 8 `sota-python` files (2,210 lines). **20 of 29 clusters
already covered**, several thoroughly — `rules/05` alone carries deserialization bans,
subprocess argv, SQL parameterisation, path traversal, zip/tar slip, randomness, XML/SSRF and
a dedicated §7a on `assert` under `-O`.

| gap | bandit | verdict |
|---|---|---|
| PEP 594 removals — no coverage of the 3.13 stdlib cliff | B312 B401 | **adopted** → `rules/01` §7a |
| no crypto delegation pointer, despite router rule 18 | B304 B305 B413 | **adopted** → `rules/05` §6a |
| temp-file creation and permissions | B103 B108 B306 | **adopted** → `rules/05` §4a |
| paramiko host-key policy | B601 B507 | **adopted** → `rules/05` §6b |
| debug console mechanism (Django settings already covered) | B201 | **adopted, scoped down** → `rules/05` §8a |
| snmp · httpoxy · bind 0.0.0.0 · trojansource | B508 B509 B412 B104 B613 | **rejected** — too narrow, CGI-era, infra-owned, or language-agnostic |

### The method's own two false positives, which is why the rule exists

Grep flagged **exec/eval** (1 hit) and **XXE** (1 hit) as gaps. Opening the files killed
both: §1 is "Deserialization & code execution bans", and §7 names `defusedxml` *and*
`lxml.etree.XMLParser(resolve_entities=False, no_network=True)`. The counts were regex
artifacts. **Grep answers "does this string appear", never "is this idea covered"** — and a
third finding was scoped down the same way, because Django's `DEBUG=False` turned out to be
covered already at `rules/07` §2, leaving only the mechanism uncovered.

### What was verified rather than recalled

- **PEP 594 is Final; its `Python-Version: 3.11` header is the DEPRECATION version and the
  removals landed in 3.13** — the distinction that gets misread, and the reason the section
  states both.
- `tempfile.mktemp` is *"Deprecated since version 2.3"* with the TOCTOU reason quoted from
  the stdlib docs; `mkstemp` guarantees owner-only permissions and no creation race given
  `O_EXCL`. **The docs do not state an octal mode, so the rule does not claim `0o600`.**
- **paramiko's default is `RejectPolicy` — safe.** The defect is opting *out* via
  `AutoAddPolicy`, so the rule is written as "do not opt out", not "fix the default".
- Werkzeug's debugger executes arbitrary code with `evalex`, **is PIN-protected by default**,
  and its own docs call the PIN *"not meant to entirely secure the debugger"* — so the rule
  calls it friction, not a control, rather than claiming unauthenticated RCE.

**All eight shipped checklist greps were run against a known-bad and a known-good fixture**
before landing: each fired on the bad file and none on the good one, with `mkstemp` and
`usedforsecurity=False` correctly excluded.

**Meta-finding worth keeping: the most valuable result was not a security finding.** Bandit's
`telnetlib` test surfaced the PEP 594 cliff, which is an upgrade hazard, not a vulnerability.
An external enumeration finds things its own category does not describe — which is the
argument for running this against the other eight languages.

## 2026-09-21 — ROADMAP 57, first of five: the Python public-API section

**Adopted** → `sota-python` rules/03 §13 "Public API surface — what you are promising", the
reference section for item 57. The gap was measured rather than assumed: before this,
`__all__`, `__slots__` and `keyword-only` each returned **0 hits across all seven
`sota-python` rules files**, and `deprecat` returned 2 incidental mentions.

Scope is Python *mechanism*, with the shared design rules left to `sota-architecture`:

- **`__all__` controls exactly one thing and it is not privacy** — the `import *` name list
  and the documented surface. The usual accident is re-exporting an import
  (`from .internal import Session`) into a module with no `__all__`.
- **A leading underscore promises nothing to the interpreter**; only `__name` in a class body
  is mechanically different, and name mangling exists to avoid subclass collisions, not to
  prevent access.
- **Keyword-only parameters are an API decision** — a positional parameter is a promise about
  *order* you can never change.
- **`__slots__` is directional**: adding it to a released class is breaking, removing it is
  not. Subclasses without their own `__slots__` regain a `__dict__` and the saving is gone.
- **Deprecate with a decorator, not a docstring** — `warnings.deprecated` warns at runtime
  *and* makes type checkers flag call sites.

**Two facts fetched rather than recalled**, both from primary sources at time of writing:
PEP 702 is **Status: Final, Python-Version: 3.13**, and `warnings.deprecated` carries
*"Added in version 3.13"* in the stdlib docs — so the rule is gated at 3.13+ with
`typing_extensions` named for older floors, which matters because this skill sets no hard
floor and tells the reader to match the project's.

**The checklist block was tested before shipping.** Its first draft used `grep -Lq`, where
`-q` suppresses the output `-L` exists to produce — a check that silently reports nothing.
Rewritten as `grep -q … || echo`, run against a fixture with one compliant and one
non-compliant module, and watched to name exactly the non-compliant one.

## 2026-09-21 — item 58 closed by the measurement it asked for, and the checklist-format split deferred

**Item 58 closed as (c).** The row opened with "jvm and .NET are 3–4× thinner than their
peers" and the measurement it asked for refuted its own framing: per 100 rules-lines .NET
(10.6) and jvm (10.5) carry the highest actionable-audit-item density in the library and
rust, the second-largest skill, is lowest at 4.6. Splitting `sota-jvm` is **rejected on the
record** — it adds a skill and moves the description classifier to fix a deficit that is not
there. Worked examples for jvm/.NET (1.0–1.1 per 100 lines against 2.7–3.8 at the top) are
**deliberately not a row**: optional polish that nobody must act on is a recurring reminder,
which is the reason item 1 was retired.

**ADOPTED 2026-09-23 on operator instruction — the audit-checklist body format is now
uniformly tickable **across the nine language skills**, and `--assert-format` keeps it that
way. **Scope, stated because the heading could be read wider:** the gate and the conversion
cover the LANGUAGE TIER only. Measured 2026-09-23, **14 files in 2 domain skills**
(`sota-web-frameworks` 7, `sota-ml-engineering` 7) still carry a ```bash block in their
checklist, and nothing gates them. **SUPERSEDED later on 2026-09-23 — see "the checklist
gate widened to every skill" below: all 14 converted, and the gate now covers every skill.**
The trigger's second arm
had effectively fired: a `- []`-only count returned 0 for seven of nine skills, and on
2026-09-22 a concept-matrix pass mis-parsed fenced blocks and reported `sota-golang` as
lacking API/design probes it plainly has — two mechanical readers, two wrong answers,
from the format alone. The operator did not wait for a third.**

*The original deferral text follows, superseded — it is kept because it records why the
item was parked, and its classification contains an error worth preserving:* Three forms
are in use — tickable `- [ ]` (rust, js/ts), fenced shell block (python, jvm, .NET, c/c++,
php), prose+commands (golang, ruby) — and invariant 2 gates only the heading.
**CORRECTION 2026-09-23: golang and ruby were never "prose+commands".** That row was
written from reading, not measuring; `extract_items.py` reports both as fenced, so the
conversion covered **seven** fenced skills, not five. The argument for unifying is that AUDIT mode instructs the model to "verify your
diff satisfies every item", and only the tickable form is enumerable.

**That argument is an inference from reading AUDIT mode's wording, not a measurement**, which
is exactly why this is deferred rather than actioned: unifying is a rewrite of seven skills,
and this library's own rule is that a change of that size needs a number behind it. Recorded
here so the next session finds the reasoning instead of rediscovering the split.

## 2026-09-21 — the language tier measured, and a "3–4× thinner" claim of my own that did not survive it

**Intake shape: a session auditing the library's own structure**, continuing the SSO thread
below. Building the section×language matrix raised the question of whether the nine language
skills should be aligned. Four measurements, and the third **refuted a claim this log had
recorded the day before**.

| finding | verdict |
|---|---|
| `SKILL.md` structure across all 9 language skills | **no gap** — all nine carry Purpose · BUILD · AUDIT · Rules index · Top-10, each with exactly 10 items. `sota-javascript-typescript` is uniformly *compressed* (70 lines), not incomplete |
| API / design absent in python, js/ts, php, ruby, c/c++ | **stands** — ROADMAP 57. Fits as sections in existing files (210–307 lines of headroom each), so no new files, no library-map churn, no description change, no routing impact |
| "jvm and .NET are 3–4× thinner" | **REFUTED AS FRAMED** — see below. ROADMAP 58 corrected rather than closed |
| the audit-checklist **body** format | **three forms** across nine skills, unrecorded until now |
| renaming rules files to a consistent scheme | **rejected on cost** — 390 citations name the descriptive filename (`rules/NN-name.md`) against 2,945 using the number alone |

### The refutation: line count was measuring the wrong thing

Measured on actionable audit items and worked examples per 100 rules-lines:

| skill | rules lines | audit items | items/100 | examples/100 |
|---|---|---|---|---|
| dotnet | 564 | 60 | **10.6** | 1.1 |
| jvm | 619 | 65 | **10.5** | 1.0 |
| ruby | 1053 | 85 | 8.1 | 1.3 |
| c/c++ | 910 | 72 | 7.9 | 1.4 |
| php | 1118 | 85 | 7.6 | 2.7 |
| python | 1986 | 138 | 6.9 | 3.3 |
| golang | 2128 | 140 | 6.6 | 2.9 |
| js/ts | 1729 | 104 | 6.0 | 3.8 |
| rust | 2057 | 94 | 4.6 | 1.8 |

**jvm and .NET carry the highest audit-item density in the library.** They are not
audit-poor; they are the densest per line. The bounded, specific deficit is **worked
examples** — 1.0 and 1.1 per 100 lines against 2.7–3.8 for php, golang, python and js/ts.
"3–4× thinner" was true of line count and false of everything line count was standing in for.

**Two honesty notes on the instrument, both recorded rather than smoothed over.** The first
count returned **0 checklist items for seven of nine skills** while invariant 2 guarantees
every rules file has an `## Audit checklist` — the regex assumed one format. That artifact is
what exposed finding four. And the two formats are **not comparable on this metric**: a
`- [ ]` item can bundle several commands while a fenced block counts per line, so the
jvm/.NET-vs-peers comparison is sound (all shell-block) and rust's last place is not evidence
of anything.

### The audit-checklist format split, and why it is not cosmetic

Three forms: tickable `- [ ]` (rust, js/ts), fenced shell block (python, jvm, .NET, c/c++,
php), prose-plus-commands (golang, ruby). Invariant 2 gates the *heading*; nothing gates the
body. AUDIT mode instructs the model to "verify your diff satisfies every item" — a checkbox
list is enumerable and a prose block is not, so the split has a functional consequence and is
not a style preference. **Not resolved here**: unifying it is a rewrite of seven skills and
needs a decision, not a side effect.

## 2026-09-20 — an SSO coverage question, and the routing measurement that refuted the framing

**Intake shape: an operator question about coverage.** Asked what the library held on SSO
attack classes (`aud` logic errors, open redirect, login CSRF, `response_type=token`,
`code_challenge_method=plain`, SAML crypto/XML flaws, Golden SAML, replay), a read of the
files found seven of eight covered, often deeper than asked. The follow-up question — *are
you sure it will be reached?* — is what produced the work.

| finding | verdict |
|---|---|
| Golden SAML named once library-wide, as a risk label, with no mechanics, defenses or detection | **adopted** → `sota-identity-access` rules/01 §7 + `sota-detection-engineering` rules/07 |
| `sota-identity-access` rules/01's Audit checklist has no `state`/CSRF item, so an SSO audit walking it is never prompted for the one control that lives in another skill | **adopted** → checklist item pointing at `sota-code-security` rules/02 §4 |
| SSO routing was untested — `sota-identity-access` was the expected pick in **0 of 84** cases | **adopted as a case set**, `evals/cases/desc-routing-sso.jsonl` |
| "SSO content may be unreachable" | **REFUTED BY MEASUREMENT** — 5/5 cases route correctly, 3/3 samples each, `correct=1.000` |
| adding SAML/federation triggers to `sota-detection-engineering`'s description | **rejected** — the measurement shows it already routes 3/3 without them; an absent string is not an absent capability, and the churn would compete for `sota-identity-access`'s traffic |
| RP-side ID-token claim validation as a routing case | **excluded, recorded as a boundary finding** — rules/01 §3 is titled "at the RP" while router rule 10 sends app-level JWT validation to `sota-code-security` rules/02-03. Contested ownership is not a routing defect |

### The result that mattered, and why it changes the shape of the fix

`sso5_forged_saml_detection` routes to `sota-detection-engineering` **3/3 — a skill that
held zero SAML content**. Routing delivered the task correctly and the destination was
empty. That separates a **routing** gap from a **content** gap, which the original framing
had conflated, and it decided the fix: add content, touch no description. The same
correction the PowerShell case recorded on 2026-09-14 (a claimed routing gap that already
routed at 0 of 42 descriptions naming the term), arrived at independently and by the same
instrument.

### What was verified rather than recalled

T1606.002 *Forge Web Credentials: SAML Tokens*, its SolarWinds/APT29 and AADInternals
procedure examples, and the **rotate-the-signing-certificate-twice** mitigation come from the
ATT&CK page, fetched at time of writing. The AD FS auditing knobs
(`Set-AdfsProperties -AuditLevel`, the *Audit Application Generated* policy, Activity-ID
correlation) come from Microsoft's own AD FS auditing documentation. A recalled claim that
**event IDs 1200/1202 are "token issuance" was wrong** — 1202 is *validated a new credential*
— so the detection is written by its *shape* (a valid sign-in with no matching IdP event)
rather than around event IDs that vary by AD FS version.

## 2026-09-18 — a field report from the session that wrote the commands, and the three of seven it earned

**Intake shape: a session reporting on itself.** The session that built `/sota-audit` and
`/sota-deep-audit` filed a field report against its own work. Seven findings; the report
**declines to propose a change for four of them**, and that restraint is the reason the other
three are worth taking.

| finding | verdict |
|---|---|
| a verdict label typed beside the command that refutes it | **adopted** → `rules/06` §2e |
| a word-boundary escape that is a property of the machine | **adopted** → `rules/06` §2f |
| a release-simulating fixture inheriting other release gates | **adopted** → `sota-devsecops` rules/09 §2 |
| a `§` shorthand resolving to the wrong document | **adopted, as a stated limit** in the checker's header, not a gate |
| a pipeline masking a verdict's exit status | rejected — covered in three places and loaded at the time |
| gating an unassigned variable in a fence | **rejected by measurement** — 131 uses across 19 files, nearly all legitimate placeholders |
| a rule for hostile-re-reading your own new text | rejected — semantic, and invariant 31 exists because a fuzzy truth gate gets disabled |

### §2e — the unconditional twin of §2d

§2d covers `cmd 2>/dev/null || echo "missing X"` and its worked example already annotates the
symptom: *"it printed the match AND the verdict that contradicts it"*. What was missing is the
form with no condition at all — `cmd; echo "^ 0 = ..."` — which is **strictly worse**, because
§2d's fires only on a non-zero exit and this one fires always. Four instances in one session,
each contradicted by the output directly beneath it; the costly one asserted a rule was absent
from the library one line above output proving it was present.

### §2f — and the question that falsified two drafts of it

First written as *"git grep is a third engine"*, then as *"`\b` is a GNU extension, not
POSIX"*. **Both were wrong about the axis**, and the operator's question — *from which version
does this behave this way?* — is what exposed it. There is no version: three older gits match
`\b` and the newest does not. The differential (three libcs, four git versions, control
passing in every row) and `nm -u` on the binary show `git grep` calls the **platform's** regex,
so the dialect belongs to the machine. The GNU and BSD word-boundary forms are mutually
exclusive, so neither is portable. **Recorded because the retraction is the useful part**: two
plausible mechanisms were published before the measurement, and the measurement cost one
command per row.

### The split that paid for the space

`rules/06` was at **498 of 500**. §5 and §5a — a lister returning a page as a population, and
a selector answering a neighbouring question — moved to **`rules/09`**, keeping their numbers,
as `rules/08` did before them. That freed 106 lines for §2e and §2f.

**The split's own hazard fired immediately**, which is the argument for doing it with the gate
running: two bare `§2` refs inside the moved text had been resolving to their containing file,
and invariant 18 flagged them the moment they landed in a file with no §2. A third citation —
`rules/06 §4`, pointing at a section that moved to `rules/08` two releases ago — is **invisible
to invariant 18** because the `§` sits on a different line from the file name, so it fails
open. Found by hand-reading every sectionless pointer; corrected to `rules/08` §4.

## 2026-09-18 — four defects a session produced, and what only two of them earned

**The session that built `/sota-audit` and `/sota-deep-audit` produced four defects of its
own.** That is the intake: not an outside report, but the thing this log exists to catch —
ideas arriving from a session that *used* the library. Each was put through this file's three
filters (has it already failed · does it fail silently · is it mechanically checkable), and
**two of the four earned a change. The other two are adherence, and a rule for them would make
the library worse.**

| defect | failed? | silent? | mechanically checkable? | verdict |
|---|---|---|---|---|
| a fence used `$BASE` and never assigned it | yes | yes — `0`, exit `0` | **no** | **rejected by measurement** |
| a spelled count drifted (*four things* → five) | yes | yes | **yes — the gate already exists** | adopted: declare it |
| wrong internal pointers, a claim outrunning its source | yes | yes | no — semantic | no change |
| the harness under-reported its own coverage | yes | yes | **yes, at run time** | adopted: self-check |

### Rejected by measurement: gating an unassigned variable in a fence

The defect was real — `/sota-audit` shipped a scope fence whose `$BASE` was printed and never
captured, giving `0, exit 0`, a clean denominator for a branch with five commits. The obvious
gate is "a prescriptive `sh`/`bash` fence may not use a variable it never assigns". **Measured
before proposing it: 131 uses across 19 files**, and the sample is `$DIGEST`, `$MSG`, `$PID`,
`$f` — reader-supplied placeholders, which is the normal idiom of a documentation snippet.
A gate that opens red gets disabled, so this one is rejected on the same ground as two of
invariant 34's candidate designs. The fix stays where it belongs: `sota-shell-scripting`
rules/06 §2b already covers the class, and the shipped fence now demonstrates the guard.

### Adopted, using a gate that already existed

The *four things → five things* drift is invariant 30's exact shape, and invariant 30 scans
every tracked `*.md`, which includes `commands/`. It was never declared, so nothing watched it.
Four counts in the two new commands now carry `<!-- count-check: … -->` markers. **No new
machinery** — the gap was a missing declaration, not a missing gate.

### Adopted: a control that asserted its own coverage instead of counting it

`check-negative-controls.sh` printed `COVERED: … (28 of 31)` while it had probes for 32, 33 and
34. Invariant 17 *requires* `AGENTS.md` and `CONTRIBUTING.md` to restate that line, so one
stale literal reached both front doors and then **rejected the correct correction** when the
measured number (61 probes, 31 of 34) was written in. That is `sota-code-security` rules/14 §1.

**The literal was kept, deliberately.** Invariant 17 parses it out of the file and invariant 19
reads the per-id reasons under it; deleting it broke both, measured. And a *static* check cannot
replace it — grepping the call sites under-reads, **27 against a true 31**, because the
diff-based probes are nested inside functions. That is why `AGENTS.md` already said only running
it is authoritative. What was missing was anything comparing the declaration to the run, so the
harness now derives the covered set from the probes that actually executed and **fails if its
own COVERED line disagrees**. The control exists at the only moment the truth does.

**Its first run was a false alarm, and the lesson is worth more than the fix.** It reported
`probes ran for 27 invariants, but the COVERED line declares 31` — against a declaration that
was right. Probes reach the gate through **three** functions and only `probe()` had been
instrumented, so the diff-based checks (11, 14, 29, 31, routed through `probe_committed()` and
`probe_committed_green()`) were invisible to it. **27 is the same number a static grep of the
call sites produced**, for the same reason. A control written to stop a number being asserted
rather than counted was itself counting a third of the evidence: `rules/14` §6, a real control
applied to part of its population, committed inside the fix for `rules/14` §1. The comparison
had been unit-tested both ways beforehand, which is the only reason the failure read as a
miscount instead of as real drift.

### Not adopted: a rule for the two adherence failures

A wrong claim landing in four places is `/sota-close` step 1 ("find where the claim went"). The
hostile-re-read defects — a pointer saying *"the next section"* after two sections were inserted,
a claim quietly upgrading the rule it cited — are semantic, and invariant 31 exists precisely
because a fuzzy truth gate gets disabled. Both rules are already written. **A further copy is the
anti-pattern**, and the same conclusion was reached for the two slips made while verifying this
session: a pipeline masking a verdict's exit status, and `ps -axo … -p "$pid"` listing every
process, are covered verbatim in `sota-shell-scripting` rules/06 §1 and §2b.

## 2026-09-18 — a private audit command, and the gap analysis that justified taking it

**The intake is my own command, which this log treats on the same terms as an external one.**
`deep-audit` had been sitting untracked in `~/.claude/commands/` since July — used, never
reviewed, never gated. The question that surfaced it was the right one to ask of any candidate:
*is there something it finds that the thing we just shipped cannot?*

**The answer was measured, not asserted.** Against the router's own seven-step AUDIT workflow:

| router AUDIT step | `/sota-audit` as written | `deep-audit` |
|---|---|---|
| 1 recon | ✓ | ✓ |
| 2 threat model first | absent | partial (lens 3) |
| 3 per-domain passes | ✓ item-by-item | ✓ |
| 4 silent-control pass | ✓ | ✓ |
| **5 decision ledger** | **absent** | ✓ with re-measurement |
| 6 findings | ✓ | ✓ |
| **7 refute** | **weakened to self-refutation** | ✓ separate agent |

Step 5 was not thin, it was **zero**: every `decision` hit in `commands/sota-audit.md` was about
asking the operator a question or updating a ledger row after a fix. A term census would have
reported four hits and looked like coverage — `grep` answers *does this string appear*, never
*is this idea covered*, so the hits were read rather than counted.

**The split that decided the packaging.** Two of the four gaps are *scale* problems and two are
*missing passes*. Missing passes get fixed in place — the decision ledger, `rules/01` §4a's
"where else does this project's knowledge live", and §1a's partition-don't-skim all landed in
`/sota-audit`. Only **independence** (a refuter that is not the context that produced the
finding) and **a forward look at the plan** actually need the heavy command, and that is now the
whole justification for its cost, stated in the command itself so a reader can decline it.

**Adopted with three corrections, none cosmetic.**

- **`ultracode` as the first body line** — a harness-specific keyword for opting into
  multi-agent orchestration. This library is cross-harness (`AGENTS.md` is symlinked for other
  tools), and *keep it generic* is a standing convention. Replaced with a capability test.
- **Unannounced cost.** It fans out across many agents and is installed at user level, so it is
  reachable from every project. It now states the cost up front and shows the plan and split
  **before** spending anything.
- **Unasked repo writes.** It wrote a dated report and a roadmap patch by default. That is the
  same call already settled against for `/sota-audit`: most repositories a command runs in are
  not the author's to leave artifacts in. Both artifacts are opt-in.

Rule text was not copied across either: the command cites `sota` router `rules/03` §1, §3, §4
and §4a rather than restating them, which is what keeps `commands/` out of the "carrying rule
text" half of its coverage-table trigger (`docs/CONVENTIONS-LEDGER.md`).

## 2026-09-16 — Invariant 34, because I reintroduced the bug I had just fixed

**This entry exists because a warning did not disable a reflex, and the evidence is my own.**
Earlier today I swept seven references to versions that never existed and wrote a commit
message naming the mechanism: *"the version was written into the prose when the file was
created, guessing the next cut would be a minor."* **Three hours later I did it again** — the
`rules/09` split wrote `v1.42.3` into three live files, and v1.42.3 does not exist.

| claimed | reality | when |
|---|---|---|
| `v1.43.0` × 5 sites | shipped in **v1.42.2** | this session |
| `v1.36.4` | **v1.37.0** | pre-existing |
| `v1.41.3` | **v1.42.0** | pre-existing |
| `v1.42.3` × 3 sites | **still unreleased** | this session, *after* fixing the above |

Four occurrences, two of them hours apart by the same author with the mechanism written down
in between. Against this ledger's three filters that is not a close call: it has already
failed (repeatedly), it fails silently (a version reads as authoritative; nothing resolves it),
and it is mechanically checkable.

### The scope was the design work, and it was measured before the check was written

- **"Every `vX.Y.Z` must be a tag"** — *rejected by measurement*. 35 distinct unresolved
  strings, nearly all legitimate third-party versions (`actions/checkout` v7.0.1, Harbor
  v2.5.1). That gate opens red and gets disabled, which is this file's own standing argument.
- **"Our own `v1.*` namespace"** — closer, but still fires on placeholder image tags and module
  specs (`ghcr.io/myorg/app:v1.2.3`, `require foo v1.2.3`) across six unrelated rules files.
  **Rewriting those to suit a gate is letting the gate drive the content**, so that was
  rejected too.
- **Grammar** — adopted. Our own claims read *at* / *in* / *since* / *until* / the ledger's *·*
  before the version. A placeholder never does. Measured on this tree: **49 claim-shaped
  references, 0 unresolved**, with the instrument's own positive control being that non-zero
  hit count.

`CHANGELOG.md` and `docs/ADOPTION-LOG.md` are **exempt**: a record *quotes* a wrong version
while correcting it — as the table above does — and gating them would make the correction
unwritable. Same distinction checks 22, 31 and 32 draw.

**Two probes**, because the scope *is* the check: 34 asserts it catches a claim-shaped
reference, 34b that it stays silent on a placeholder image tag in the same namespace. Without
34b the scope is a checkbox nobody has shown to work.

**The fix when it fires is never to invent a number.** Write `· unreleased`; `RELEASING.md`
step 1 already sweeps for that marker. The three live sites were corrected that way rather
than by guessing again.

## 2026-09-21 — field report, cross-platform EDR agent: three findings, one of which found a defect in our own snippet

Source: a session that **used** the library at v1.43.1 (symlink install) to ship a telemetry
feature on a Rust + eBPF endpoint sensor. Filed as `*.local.md`, git-ignored. Highest-yield
intake shape, per the priorities table. **Every falsifiable claim was reproduced here before
any verdict** — the reporter's own numbers, and our own text.

| idea | verdict | landed in |
|---|---|---|
| rules/06 is unreachable by subject routing, because the task is never *about* checking | **adopted** | router BUILD step 2 (standing load) + `sota/rules/02` §1a (the reasoning, the cost, and a falsifier) |
| an evidence grade does not propagate from a premise to a conclusion drawn in the same breath | **adopted** | `sota/rules/03` §2, plus the §2 checklist item |
| the exit-status rule does not name the agent harness as a consumer | **adopted with a correction** | `sota-shell-scripting/rules/01` §2a + §3 snippet + checklist. **Placement corrected**: the report filed it under §3, which is *Quoting*; the exit-status material is §2/§2a, and §2a already owned the harness-as-consumer idea for background jobs |
| §2f's positive control is filed under a symlink heading and gets skipped | **adopted** — it had predicted this, and it recurred | `sota-shell-scripting/rules/06` §2 heading + the control paragraph + §2f's closing |
| a new rule about benchmarking on a controlled host | **rejected — already covered**, and the reporter reached the same verdict unprompted | `sota-performance/rules/01` covers warmup and multiple samples; one exotic case (VM uptime) is not a library gap |
| an eBPF skill | **rejected** — one session, and the reporter argued against it himself |

**What we reproduced, rather than took on trust.**

- **The word-boundary failure, on this machine**: `git grep -cE '\b(TODO|FIXME|XXX|HACK)\b'`
  over the tracked tree returns **0 files**; the same sweep without `\b` returns **58**.
  git 2.55.0, Darwin 25.6.0 — matching `rules/06` §2f's measured row exactly.
- **§2f is at `rules/06:388`**, as cited.
- **The duplicate check that mattered.** Finding 3 reads as a naming gap; opening the file
  showed `rules/01` §2a *already* covers the harness consumer for background jobs, with the
  same field-reported *"completed (exit code 0)"*. So it is an adoption **with a correction**,
  not a new rule — and checking that claim is what surfaced the defect below.

**The defect this intake found in our own text.** `rules/01`'s recommended snippet read

    cmd > out.txt 2>&1; echo "EXIT=$?"        # status preserved AND output preserved

and **"status preserved" is false of the compound's own status**, which is the `echo`'s. The
library was recommending, in a comment, the exact shape the reporter broke and §2a warns
about elsewhere in the same file. Corrected to capture (`rc=$?`) and re-raise (`exit "$rc"`),
with the distinction stated: *recorded in a log* is not *returned to a caller*. **Evaluating
someone else's claim of a duplicate forced the closest read of our own page, and that is
where the finding was** — the fourth time this ledger records that pattern.

**The cost we accepted, stated plainly.** The router edit moves `ROUTER_BUILD_SHA`
(`a92b0177acadec05` → `273a969bbe2994e4`). The mirror was re-read clause by clause first: the
change lands in BUILD steps 1–2, which `BUILD_WORKFLOW` does not model (the eval pastes the
skills, so routing and file selection are short-circuited), so the hash was bumped **alone**,
no re-sync — recorded at the pin. The treatment arm is therefore unchanged and the published
+0.39 is not invalidated, but **it has not been re-run against the current router**, because
this repo holds no API key. **CORRECTION 2026-09-23: that reason was wrong.** The *public,
committed* repo holds no key and CI has none, but a maintainer's working tree does — every
runner reads `OPENROUTER_API_KEY` from the environment or `./.env` (gitignored; verified 0
tracked, 0 commits in history). The re-run was available all session and was not done. The
claim it guards — that +0.39 has not been re-measured against the current router — still
stands; only the stated obstacle was false. **SUPERSEDED 2026-09-23: re-measured** at
`273a969bbe2994e4` with the baseline configuration: +0.39 and +0.42 over two runs, mean
0.58 → 0.98 (+0.41). It holds (`evals/results/2026-09-23/COMPLETENESS-RERUN.md`, ROADMAP 63). The standing load is justified by a mechanism and not by a
number, and `rules/02` §1a carries the falsifier that would take it back out.

## 2026-09-21 — the over-firing control: a deferral whose blocker had been false for nine days

**Adopted** as `sota-code-security` rules/10 **§5** + two checklist items. The idea is the
mirror of the file's whole subject: rules/10 covers a control with **too little** effect, and
this is a control with **too much** — one that fires on cases it was never meant to catch,
degrades the outcome it exists to protect, and looks like it is working throughout, because
*the thing that happens is what success looks like*. The metric asymmetry is the core of it:
firing count goes **up** as an over-firing control gets worse.

**Why this is a `/sota-resume` finding rather than a fresh intake.** The row was deferred on
2026-09-11 with an explicit, checkable trigger — *"revisit when `sota-code-security` rules/10
is split"* — and an explicit blocker: *"rules/10 is at **484/500** and putting it there would
let the line cap choose the placement"*. **ROADMAP 55 split the file on 2026-09-12**, taking
rules/10 to **230/500**. The trigger fired the next day and nobody came back for nine days.
Nothing reports this: invariant 27 asserts a deferral *names* a trigger, never that the
trigger is still unmet. Re-testing each deferral's **trigger** rather than its subject is
what surfaced it — the same lesson this ledger recorded on 2026-09-06 for three stale
roadmap triggers, now repeated one layer down.

Written from the mechanism rather than from the source's wording; the reviewers' original
observation (a blanket deny on a search *tool* enforces a worse substitute than a deny on the
unsafe *behaviour*) survives as the worked shape, in our own words.

## 2026-09-21 — ROADMAP 57, second of five: the c/c++ public-surface section, and 59's denominator banked

**The gap was measured, not assumed, and the measurement nearly said the opposite.** Across
the 8 files of `sota-c-cpp`, `pimpl`, `header hygiene`, `include-what-you-use`,
`inline namespace`, `visibility`, `soname` and `forward declar` each returned **0 files**
(positive control: `RAII`, 4 files). **`ABI` returned 7 files** — non-zero, which under this
method means open them rather than assume. All seven are incidental: error codes *at* an ABI
boundary (`rules/01` §7), SIMD alignment (`rules/03`), a `--addon=cert` invocation, and a
severity table. **Nothing covered ABI as an API-design constraint**, which is the one C/C++
adds that no other language in this tier has.

**Landed in** `sota-c-cpp/rules/01` **§9** + five checklist probes. Scoped to the C/C++
*mechanism*, with the shared design rules left to `sota-architecture` rules/02 and
`sota-api-design`, per §57's own instruction:

- the **source-compatible-but-ABI-breaking table** — adding a data member (even `private`),
  adding the first virtual, reordering members, changing a default argument, changing an
  `inline` body. The through-line is that the *loud* case (a changed signature → changed
  mangled name → link error) is the safe one, and every silent case is a layout change;
- **`pimpl`** with the trap that bites everyone who tries it: `~Widget() = default` **in the
  header** instantiates `unique_ptr`'s deleter against an incomplete `Impl` and fails to
  compile, so the destructor and moves must be declared there and defined in the `.cpp`;
- **stdlib types in exported signatures.** Fetched rather than recalled: libstdc++ has had
  **two ABIs since GCC 5.1**, selected by `_GLIBCXX_USE_CXX11_ABI`, and mixing them surfaces
  as *"undefined references to symbols that involve types in the `std::__cxx11` namespace or
  the tag `[abi:cxx11]`"* — quoted from GCC's own dual-ABI page;
- **header hygiene** — forward-declare, no file-scope `using namespace`, guards,
  `-fvisibility=hidden` by default, macros have no namespace.

**Every shipped grep was run against a known-bad and a known-good header first, and one
failed.** The stdlib-type probe originally included `unique_ptr|shared_ptr` and therefore
flagged **this section's own recommended `pimpl` header** — a check that fires on the
guidance beside it. Narrowed to the container types, retested: 2 hits on the bad header, 0 on
the good. A `grep -rLn` was also corrected to `grep -rL` (`-n` is meaningless with `-L`).

**A hostile re-read of the section found a defect in it, after it was written and adopted.**
The ABI table's signature row said a changed signature fails **loudly**, because the mangled
name changes. True of C++ — and **false at exactly the boundary this section recommends**:
`extern "C"` has no mangling, so a changed C signature still resolves, links clean, and hands
the old caller's arguments to the new function. The one remedy offered for the stdlib-ABI
problem was the one place the safety net is absent, and the section did not say so. Now a
table row of its own plus a paragraph: version a C boundary by hand, `_v2` rather than an
edit. **Every invariant was green before and after** — nothing in this repo checks whether a
rule is *true*, which is why a rule gets a second adversarial read after adoption, not before.

**ROADMAP 59, same session, deliberately NOT swept.** Its denominator was derived twice and
reconciled — cppcheck **2.21.0**, `--errorlist` unique ids = **342**, the same dump grouped by
severity = **342** with buckets summing exactly — and the gosec two-registry lesson repeats:
the **addons are a separate list**, `misra.py` alone holding **132** rule functions. At 4.5×
the Python set, the cluster-sweep is the session the row budgets for it, and half a sweep is
worse than none. Recorded in [LANGUAGE-TIER.md](LANGUAGE-TIER.md) so the next session starts
past the step that has now failed twice.

## 2026-09-21 — `$?` volatility: the bash half of a rule PowerShell already had

**Operator intake, mid-session.** I had put the "capture `rc=$?` on the very next line"
constraint into a private memory file; the operator's correction was that it is not a fact
about me, it is **a rule for building and auditing shell scripts**. Reverted from memory,
written here.

**Checking where it belonged found the asymmetry.** `sota-shell-scripting/rules/07`
(PowerShell) already carries it as both a rule (*"`if ($?)` after anything other than the
immediately preceding native command"*) **and** an audit probe (*"Is `$?` read anywhere other
than immediately after the command it describes?"*). The **bash** half had neither — only a
passing mention inside an unrelated `rules/01` checklist item. Same class as the
`sota-rust` subprocess gap: the rule exists for one language and not its neighbour.

**Landed in** `rules/02` **§3a** + an audit checklist probe mirroring the PowerShell one.

**The measured part, which is counter-intuitive and is why this is worth a section.** The
habit that fixes the neighbouring bug causes this one:

| form | captured status |
|---|---|
| `local rc=$?` | **7** — `$?` expands before `local` runs |
| `local rc; rc=$?` | **0** — the `local rc;` declaration is itself a command |

SC2155 (*"Declare and assign separately to avoid masking return values"*, quoted from
shellcheck's own output) is **correct for command substitution**, where `local out=$(cmd)`
hides `cmd`'s status. Applying the same split to a `$?` capture **breaks** it. Same mechanism
— `local` has an exit status — opposite remedy. Measured 2026-09-21 on **bash 5.3.15, zsh,
dash and sh**: all four agree, so it is the rule rather than a dialect quirk. Also measured:
an intervening `echo` gives 0, and so does a bare `[ -n "x" ]`.

**The probe is labelled a locator, not a verdict** — it hits correct captures too, and the
fixtures showed that, so the item tells the auditor to read the two lines above each hit
rather than treating a hit as a finding.

## 2026-09-21 — the concept matrix: item-granularity alignment, and its measured error rate

**Operator request:** map what each skill has uniquely, decide what should be standard across
all languages, align it, and give the library a real template. This entry covers the *mapping*
instrument and the first verified gap; alignment and the template are ROADMAP 60 and 61.

**Why a new instrument rather than extending page 5.** `gen-skill-map.py` maps topic x
language at **file** granularity — that is how ROADMAP 57 was found, and it is structurally
blind to a concept missing *inside* a file that exists. Both of the day's other findings were
of exactly that shape (the `$?` rule in bash, the ABI section in c/c++), and no file-level view
could have reported either, because every skill involved *had* the relevant file.

`scripts/gen-concept-matrix.py` + `scripts/lib/extract_items.py`: every Audit-checklist item in
the tier, classified into **41 declared concepts**, reported as concept x language presence.

**Two design decisions worth recording.**

- **Presence, not counts.** `gen-skill-map.py`'s own docstring warns the two checklist body
  formats are not comparable by volume (a checkbox bundles several commands; a fence counts per
  line). *Presence* is format-agnostic, so the incomparability that blocks counting does not
  apply — which is why this asks a presence question and never prints a total.
- **A fence comment plus its commands is ONE item.** The first run classified bare `grep` lines
  with no prose and reported **go as lacking API-design probes** while `02-design.md` plainly
  has them. Grouping raised classification from 49–78% to 67–93% and removed that false row.

**The measured error rate, published because it is the number that decides how to read the
output: 3 of the 4 candidates checked by opening the file were vocabulary artefacts.** php SQL
injection (the file says *"SQL built from strings"*, not "sql injection"), rust deserialization
(the matcher lacked `serde`), rust suppression (the matcher wanted `#[allow`, the text writes
`#![allow`). Each was fixed in the matcher in the same change — **the vocabulary is the thing
being built**, and a dead candidate is how it gets built. So the output is a **candidate
generator**, never a gap list, and the file says so above its own results.

**The one that survived — ROADMAP 60.** Six of nine languages probe *"someone silenced the
analyser"*; **jvm, .NET and c/c++ do not**, confirmed by reading every checklist in all three.
Each has a prominent mechanism (`@SuppressWarnings`/`NOSONAR`, `#pragma warning disable`/
`<NoWarn>`, `// NOLINT`/`cppcheck-suppress`). It matters because a suppression is how a green
gate stops meaning anything — `sota-code-security` rules/10's subject, one layer down.

**Honest limits, stated in the script's own header rather than here alone:** it answers "does
this wording appear", never "is this idea covered"; every run prints a per-skill denominator;
`--show-unmatched` lists what the vocabulary could not classify, because an item this file
cannot classify is a hole in the file, not evidence about the skill.

## 2026-09-22 — ROADMAP 60 closed: the analyser's escape hatch, in jvm, .NET and c/c++

The gap the concept matrix found on 2026-09-21, closed. One checklist block per skill, in each
tooling/CI file. **The row demanded the syntax be verified rather than recalled** — three
mechanisms, three spellings, and a wrong one ships a probe that can never fire. It was, and
two of the verifications changed what shipped:

| skill | how the syntax was established |
|---|---|
| jvm | **Run.** JDK 21.0.12 in a container (no local JRE — `javac` on this host is a stub that errors with "Unable to locate a Java Runtime") |
| .NET | **Microsoft's own in-source-suppression docs** — no local `dotnet` |
| c/c++ | **Run.** cppcheck 2.21.0 locally; clang-tidy's forms from the LLVM docs (no local binary) |

**Two measured facts that a recalled rule would have missed.**

- **`@SuppressWarnings` is category-scoped, and the differential proves it.** A method
  annotated `@SuppressWarnings("unchecked")` still emitted **both** `[rawtypes]` warnings while
  the `unchecked` one vanished; the unannotated method emitted all three. So an auditor must
  read the *argument*, not the annotation — and `@SuppressWarnings("all")` is its own finding.
- **A `// cppcheck-suppress` comment is inert unless `--inline-suppr` is passed.** Measured:
  without the flag both planted warnings still fired. With it, `memleak` was suppressed and
  `nullPointerOutOfMemory` was **not**, because the comment must sit on the line before the
  line the warning is *reported* on, which is not always the line you expect. So the probe
  checks the **flag** before it reads the comments — a whole tree of suppression comments can
  be decoration.

**The bulk forms are the half a per-site grep never finds**, and each skill probes them: SpotBugs
`excludeFilterFile` and Checkstyle suppression XML; `GlobalSuppressions.cs`, `<NoWarn>` in a
`Directory.Build.props` that covers a whole solution, and `.editorconfig`
`dotnet_diagnostic.*.severity = none`; cppcheck `--suppressions-list` and
`#pragma GCC diagnostic ignored`. **Microsoft's own word for the bulk case is "baselining"**
(*"Suppressing all current violations is sometimes referred to as baselining"*), and a large
`GlobalSuppressions.cs` with uniform timestamps is its signature — the analyser's verdict on
that code was never read by anyone.

**Every shipped grep was run against known-bad and known-good fixtures, and one was broken.**
`NOLINT(NEXTLINE|BEGIN)?[^(]` matched 1 of 2 blanket forms: a bare `// NOLINT` at **end of
line** has no character after it, so `[^(]` cannot match. Corrected to `([^(]|$)`, retested at
2 of 2, and confirmed still to discriminate — on a file with one scoped `NOLINT(check)` and one
bare `NOLINT` it matches only the bare one. **This is exactly the failure the roadmap row
predicted**, caught by the fixture rather than by review.

**Confirmed by the instrument, not by assertion:** `gen-concept-matrix.py` now reports
`suppressing a linter / type check` as present in **9 of 9**.

## 2026-09-22 — first concept-matrix triage: 2 real gaps, 6 artefacts, 3 delegations

Working ROADMAP 61's blocker (*"triage the candidates first, or the template freezes today's
gaps"*). Eleven cells opened; the verdicts are in
[LANGUAGE-TIER.md](LANGUAGE-TIER.md#triage-ledger--candidates-opened-and-what-they-turned-out-to-be).

**Both survivors are the same shape: the BUILD rule exists and the PROBE does not.**

- **jvm path traversal** — `rules/04:86` already said *"canonicalize and verify the result
  stays under an allowed root (`Path.normalize()` + `startsWith`)"*, and **no checklist in the
  skill probed it**. Added, with zip slip alongside: an archive entry name is attacker-
  controlled, and normalizing without then comparing is a no-op.
- **js/ts SQL injection** — `rules/05:178` says *"never interpolate into SQL (parameterized
  queries only)"* inside a *"same family"* aside, and the checklist had **no SQL probe at
  all** in a skill whose own SKILL.md lists *"untrusted input reaching eval/innerHTML/exec/
  SQL"* as CRITICAL. Added, including `$queryRaw` (parameterized) vs `$queryRawUnsafe` (not),
  which differ by one word.

This is the **third independent instance** of that shape in two days — after the `$?` rule
(bash had neither half, PowerShell had both) and the analyser escape hatch (ROADMAP 60). It is
invisible to a file-level matrix, invisible to a reader of the prose, and invisible to every
gate we have: **nothing checks that a stated rule has a way to be detected.**

**A delegation is not a gap, and the instrument was reporting it as one.** rust, js/ts and
c/c++ have no TLS probe because router cross-cutting rule 18 puts transport/PKI in
`sota-network-security` rules/06 library-wide. Three skills were being flagged for *obeying
the router*. The concept is now `conditional`, with the reason recorded at the declaration so
a later reader does not "fix" it.

**The matcher is part of the artefact.** Six candidates died on reading, and each one's
vocabulary hole was closed in the same change — `prepared` never matches `prepareStatement`
(prepare+statement, no `d`), `child_process`/`Process.Start` were absent, `Path.Combine` was
absent. The candidate list is a **queue that shrinks as it is worked**, not a scoreboard, and
a dead candidate that leaves the matcher untouched will simply be re-derived next run.

## 2026-09-22 — ROADMAP 61 closed: a template, and the ratchet that is the real half

**The operator's decision was "a real template plus a gate", and the gate turned out to be
the load-bearing half** — worth recording, because the template was the part that was asked
for and is the part that will not hold on its own.

**Why a template alone cannot work.** It is read **once**, when a skill is created. Every
drift this library has measured happened *afterwards*: ROADMAP 57's four missing API/design
sections, ROADMAP 60's three missing suppression probes, and the two probe-less rules found
in triage the same morning. A document that is read once cannot defend against the next
edit, and prose has already failed this exact test (which is CONVENTIONS-LEDGER's first
filter — *has it already failed?* — satisfied).

**So the enforcement is `gen-concept-matrix.py --assert-universal`**, wired into the CI
invariants job: **12 concepts pinned at 9/9**, failing if any language stops probing one.
Watched to fail first — stripping `rubocop:disable` from `sota-ruby`'s checklist produced
`REGRESSED: suppressing a linter / type check now absent from: ruby`, and it passed again on
restore. The floor deliberately includes `suppressing a linter / type check`, which only
reached 9/9 that same day: **the gate's first job is to defend work that was just done**,
which is when a regression is cheapest to make and least likely to be noticed.

**`docs/SKILL-TEMPLATE.md`** carries the skeleton — frontmatter (and that the `description`
is the *whole* routing classifier, inert body notwithstanding), the body spine, the rules-file
shape, the language file spine, the 12 universal concepts as a checklist, and the pre-PR
steps. It states in its own opening that it is **not** the gate and names what is.

**It lives in `docs/`, not `skills/`,** and the reason is mechanical: every gate enumerates
skills with `git ls-files skills/*/SKILL.md`, so a template under `skills/` would be counted
as a real skill by invariants 6, 10 and 15 and would have to satisfy the 500-line cap and the
`## Audit checklist` requirement.

**One thing the template can only ask for, because nothing can yet gate it:** *for every rule
you write, how would an auditor detect a violation?* Three instances in two days shipped a
BUILD rule with no probe. The template makes it a reviewer's question; making it a gate needs
a way to tell "this rule needs a probe" from "this rule is prose", which is not yet solved.

## 2026-09-22 — ROADMAP 57 closed: API/design in js/ts, php and ruby, every claim run

The last three of five. Each section is scoped to the language **mechanism**, with the shared
design rules left to `sota-architecture` rules/02 and `sota-api-design`, per §57's own
instruction. **Every load-bearing claim was executed, not recalled** — all three runtimes were
available, so there was no excuse for a doc-derived rule:

| claim | measured |
|---|---|
| `"exports"` encapsulates a package | **Node 22.22.1** — entry resolved; `require('pkg/lib/internal.js')` failed **`ERR_PACKAGE_PATH_NOT_EXPORTED`** |
| PHP `readonly` rejects writes | **8.5.9** — `Error: Cannot modify readonly property V::$x` |
| PHP narrows/widens asymmetrically | widening a parameter **accepted**; narrowing is **fatal** at class declaration (*"must be compatible with"*) |
| adding a method to a released interface | **fatal** for existing implementers (*"contains 1 abstract method"*) |
| Ruby `private` and `def self.` | **4.0.6, differential** — instance method raised `NoMethodError`, the class method was **still callable** |
| Ruby `private_constant` | `NameError: private constant B::SECRET referenced`; a bare constant is reachable with no declaration |

**The three languages needed different amounts of writing, which only measuring showed.**
js/ts and php had nothing: `"exports"` appeared only in rules/07 as *packaging*, and php's
`semver` mention was a **consumer** constraint (`^` ranges), a different question from what a
publisher may ship. Ruby already covered semver honesty (`rules/04`) and
`respond_to_missing?`, so its section is narrower and inverted to Ruby's actual default —
**nothing is hidden**, so the audit question is not *"what did we export"* but *"what did we
fail to hide"*.

**A probe that does not discriminate is labelled, not shipped as if it did.** Ruby's
bare-constant locator fires on a *correct* file too, because `private_constant` usually sits on
the **next** line and `grep -v` is line-scoped — verified against a fixture that does exactly
that. It now says so and prints two counts to compare instead.

**And the gate was watched to fail — after a first attempt that was itself inert.** Stripping
`interface`/`final`/`readonly` from php's checklist did **not** trip `--assert-universal`,
because the text still said *"Public surface"* and *"deprecated"*, which the matcher also
accepts. Mutating against the matcher's **actual** vocabulary produced
`REGRESSED: public API surface & evolution now absent from: php`, and restore returned it to
green. **The first mutation looked like a passing gate and was a broken probe** — the exact
failure the negative-control harness exists to catch, met here by hand.

`public API surface & evolution` is now pinned in `UNIVERSAL_FLOOR` (13 concepts), so the five
sections written over two days cannot silently regress.

## 2026-09-22 — gap-check 3 of 9: sota-c-cpp against cppcheck's 342 checks

Denominator **342**, reconciled two ways the day before and re-confirmed here by parsing
`--errorlist` (342 of 342 parsed). MISRA remains a **second registry** (132 rule functions in
`misra.py`) that this skill delegates to by name.

**The twelve obvious clusters were all already covered** — buffer/bounds, null, uninitialised,
leak/UAF, integer, resource, STL/iterator, class/ctor, format string, banned APIs, exception
safety, style — 3 to 6 files each, against a control of 4. **The gaps were entirely in the
unclustered tail**, which is the part a keyword clustering throws away and the reason the
method says to look at it rather than report a tidy cluster table.

**Four closed, as `rules/01` §8a — construction and destruction, all measured on clang 17:**

| trap | measured |
|---|---|
| virtual call in a constructor | dispatched to **BASE**, not the derived override — the derived vtable is not installed yet. Pure-virtual there is UB |
| initialiser list order | members init in **declaration** order, not list order. `M() : b(1), a(b+10)` read `b` before it existed — and the value **changed with the build**, `a=70261` at `-O0` vs `a=10` under `-DNDEBUG`, which is the UB signature |
| `assert` with a side effect | `assert(++n == 1)` left `n==1` normally and **`n==0` under `-DNDEBUG`** — the increment is gone in the build you ship |
| self-assignment in `operator=` | rule of five says *declare* all five; it does not say the bodies are correct |

**Invariant 32 rejected my own probe, twice, and both rejections were right.** The first shipped
a grep with stderr discarded and an or-echo announcing absence — the exact `rules/06` §2d
anti-pattern, written hours after I had cited that rule elsewhere in the same file. Rewritten
to branch on the exit code and keep stderr. The **second** rejection was of the *comment*
explaining the fix, because it spelled the pattern out literally: the same trap invariant 30's
header records against itself. Refer to such a pattern by name, never by its characters, in
prose that shares a file with the check.


## 2026-09-23 — the checklist format unified: 362 items, 7 skills, one form

Operator instruction, closing a deferral whose second arm had effectively fired. All nine
language skills now use tickable `- [ ]` bullets — **the language tier only; 14 files in
`sota-web-frameworks` and `sota-ml-engineering` remain fenced and ungated** (*superseded the
same day: see the next entry*); `gen-concept-matrix.py --assert-format`
runs in CI and rejects a fenced checklist.

**Why the format was never cosmetic.** AUDIT mode tells the model to *"verify your diff
satisfies every item"*, which cannot be followed against a shell block. Two mechanical readers
had already been wrong because of it: a `- []`-only count returned **0 for seven of nine**
skills, and a concept-matrix pass reported `sota-golang` as lacking API/design probes that its
`02-design.md` plainly has.

**The conversion was mechanical and the review was not.** `scripts/lib/unify_checklist.py`
groups each `#` comment with the commands under it — the same grouping `extract_items.py`
uses — and leaves non-shell fences alone. Content preservation was asserted per file: the
prefix before `## Audit checklist` must be **byte-identical**, and every command line in the
original must still appear. Final result: **362 items, 0 commands lost** — counted with
`extract_items.py` after the final conversion. **CORRECTION 2026-09-23: the commit message
and the first draft of this entry said 377.** That figure was a sum of the converter's
per-run reports taken mid-process, before the grouping fixes changed item boundaries —
arithmetic on a remembered number rather than a count of the result.

**Three bugs, and the first was destructive.** The first draft returned only the text from the
heading onward and **truncated six `sota-dotnet` files to their checklists** — caught by a line
count, not by the item count, which still matched. Restored from the commit; the converter now
asserts the prefix survives. Then: a wrapper that counted backticks for parity **split a
command across two lines** when the command itself contained a backtick (php's
`` grep -rn '`' `` probe), fixed by treating a code span as atomic; and shell line
continuations (`\`) being emitted as two commands, plus `# ^ trailing note` comments becoming
the *heading of the next probe* — 16 of each across the tier.

**The conversion also exposed a latent defect no gate could see.** `sota-c-cpp` `rules/01`
cited `rules/06 §2d` meaning **`sota-shell-scripting`**'s, but inside a code fence — where
invariant 18 never looked. As prose it resolved against c/c++'s own `rules/06` and failed
immediately. Qualified with its skill name. A reference hidden in a fence is unchecked.

**Measured side effect:** concept-classification coverage rose in every converted skill
(c/c++ 73→83%, jvm 92.5→95.2%, go 78.7→84.5%), because a bullet carries the prose a bare
command line did not.

## 2026-09-23 — the checklist gate widened to every skill, and a fourth format it could not see

**Intake shape: a `/sota-resume` pass, on operator instruction.** The entry above recorded its
own scope limit (14 fenced files in two domain skills, ungated) without opening a row for it.
Closed the same day rather than tracked.

**Measured first, over every skill:** 275 rules files in 42 skill directories (the router's four
included). The 14 fenced files matched the recorded figure exactly. The same pass found a
**fourth body format** that no entry had named: three `sota-architecture` files
(`04`, `05`, `07` — 50 items) wrote their checklists as plain `- ` bullets, which
`extract_items.py` reads as **zero items**. The language-only gate tested
`kinds and kinds != {"box"}`, so an empty checklist was a pass. That is the fail-open shape
this repo's gates are built against: an empty scope that verifies nothing and exits 0.

**What changed.**
- `gen-concept-matrix.py --assert-format` now walks `skills/*/rules` **per file**, fails a
  file with zero items as well as a non-tickable one, fails closed on an empty scope, and
  prints its denominator. **Watched to fail** against an export of the pre-change tree
  (exit 1, 17 of 275 files named: the 14 fenced and the 3 plain-bullet files). After the
  conversion it passes (exit 0, `275 rules files across 42 skills`).
- 14 files converted with `scripts/lib/unify_checklist.py`, **81 items**. Every original fence
  line (217) was checked for survival in the new text, and 217 of 217 were found. The one
  flagged by the check was a colon the converter drops by design, which also showed the check
  could fail.
- The three architecture files were tick-boxed in place (17 + 19 + 14 bullets → the same
  counts as `- [ ]` items).

**The converter has one more mis-grouping, which the entry above did not list.** A `#` comment written
directly under a command, with no blank line between them, is that command's *note*. The
converter promoted it to the **heading of a new, command-less item** unless it began with
`^`. Six sites were fixed by hand (ml-engineering 01/03/04/05, web-frameworks 01 and 03).
In web-frameworks 03 an `NB` caveat had become the heading of an unrelated probe, attached to
a command it does not describe. **Found by listing every converted item that had no command**,
not by the content check, which passed while the structure was wrong. The converter itself is
**not** fixed: every checklist it can reach is now converted and the gate stops a fence coming
back. The review step is recorded here so the next person to run the converter knows to do it.

## 2026-09-23 — two field reports that were never taken in: 2026-09-12-III and 2026-09-14-II

**Intake shape: a `/sota-resume` pass that read the local reports line by line.** An earlier
inventory the same day had called every report "processed" because each one's *date* appeared
in this log. The dates were there because **sibling** reports from the same days had been taken
in. `FIELD-REPORT-PRIVATE-2026-09-12-III.local.md` and `…-2026-09-14-II.local.md` had no entry at
all: `12-III` and `14-II` had 0 hits in the tree. Each proposal was then evaluated against the
current code, not against the report's own claim of novelty.

### 2026-09-12-III — six findings: five adopted, one adopted with a correction

| finding | verdict | landed / why |
|---|---|---|
| §1 checking each precondition is not checking the operation | **adopted with a correction** | `sota-code-security` rules/16 §2.15 already carried the remedy ("invoke it once against the real thing"). It lacked the *why*: preconditions do not compose and their list is unbounded. Added there. **Rejected** for router principle 0 (detail belongs in `rules/`, and principle 0 already requires reproduced behaviour) and as a new `rules/15` section (a duplicate of §2.15, in a file at 497/500) |
| §2 a skip condition taken from the subject's own error text | **adopted** | `sota-testing` rules/04 §4.8, beside the environment-gated-skip bullet it sharpens, pointing back at `rules/15` §2.4. Placed there because `rules/15` has 3 lines of headroom |
| §3 a cleanup tool's "reclaimable" | **adopted, partly already covered** | The definition was at `sota-shell-scripting` rules/09 §5a. "Prefer the narrow command, whose failure mode is freeing nothing" was not, and is added at `sota-devsecops` rules/07 §7.7 |
| §4 pruning a base image pinned only by a moving tag | **adopted** | `sota-devsecops` rules/07 §7.7, plus a checklist item. The mechanism was **verified, not taken on trust**: `podman build --help` gives `--pull` a default of `missing`, so the cache is the only pin |
| §5 `modprobe` exits 0 for a built-in module | **adopted** | `sota-testing` rules/04 §4.8. Verified in kmod source: `module_is_inkernel()` in `libkmod-module.c` treats `KMOD_MODULE_BUILTIN` as already present |
| §6 the borrowed bad state | **adopted** | `sota-code-security` rules/12 §1d as a second decay construction, plus a checklist item. §1d's three fixes (overshoot, absolute value, pin the threshold) do not reach it, which is why it is a separate construction |
| "a self-test that re-runs after restoring mislabels the failure" | **not an item** | The reporter says it is covered, and `rules/12`'s "asserts the **named** check caught it" does cover it |

### 2026-09-14-II — one finding: adopted, and it was wider than reported

**A passing positive control proves the instrument, not the scope.** It is stated canonically at
`sota-shell-scripting` rules/06 §2, with a checklist clause. The report named `/sota-report`
check A plus two sibling commands. The sweep found **four** commands telling the reader to draw
the control "in that scope": `/sota-audit`, `/sota-close`, `/sota-resume` and `/sota-report`.
*(CORRECTION 2026-09-23, same day: only `/sota-audit` and `/sota-close` used the phrase "in
that scope" (`git show v1.44.0:<file> | grep -c 'in that scope'` gives 1, 1, 0, 0).
`/sota-resume` and `/sota-report` gave the same instruction in other words, so all four still
needed the clause; the quotation was wrong, not the fix.)*
Each gains one clause and a pointer, deliberately not a restatement, because the reporter's own
caution was that a longer check A gets run less.

**The proposed glob change is not an item.** The example glob the report quotes was never in
the command text (`git show 2f41631:commands/sota-report.md` has no `glob`).

**Why this one is worth recording beyond the rule.** The same session that took it in had
committed the failure an hour earlier. It declared the local reports processed from a check
drawn inside the wrong scope (report dates rather than report contents), and separately read a
confident 0 from a `git grep -E '\b…'` that could not match on this machine. Both were caught
only by a control drawn from outside the searched scope.

## 2026-09-23 — an open measurement with no trigger: the competitor benchmark's full-7 multi-sample

**Intake shape: a `/sota-resume` sweep for untracked open items.** `evals/results/RESULTS.md`
listed "Full-7 multi-sample of the competitor arms (only the 3 tightest done)" under *Not yet
measured (open)* since 2026-07-13. It had no ROADMAP row and no revisit condition, which makes
it a silent drop wearing an "open" label. Operator decision 2026-09-23: defer it, with a
trigger.

- **DEFERRED — revisit trigger: the next time the competitor benchmark is re-run for any
  reason** (a new competitor, a model change, a head-to-head claim being re-cited), multi-sample
  all 7 cases in that same run instead of paying for a separate top-up. Reasoning: the 3
  multi-sampled cases were chosen as the **tightest**, and SOTA's lead held on every one with
  near-zero variance (sd 0.00 on c1/c3, 0.04 on c7; `COMPETITOR-BENCHMARK.md`). The remaining 4
  are the least contested, so sampling them answers no open question, and spending on a
  measurement with no question behind it is what this log exists to prevent.

## 2026-09-23 — the router-activation proposal of 2026-08-05 gets a ledger entry, and P7 a verdict

**Intake shape: closing a local proposal whose verdicts existed only in a release entry.**
`ROUTER-ACTIVATION-PROPOSAL.local.md` had **no row here**. Its outcomes were recorded only in
`CHANGELOG.md` `[1.22.0]`. Recorded now so the next reader does not re-derive them.

| proposal | verdict | where |
|---|---|---|
| P1 triggers for code you do not own (PR, diff, upstream) | **adopted** · v1.22.0 | `skills/sota/SKILL.md` description |
| P2 a mid-session drift clause | **adopted** · v1.22.0 | router description ("including mid-session"), plus the hook's "route now" |
| P3 principle 7, restate from the primary source | **adopted, reworded** · v1.22.0 | router principle 7 |
| P4 principle 8, publishing under someone else's name raises the bar | **adopted** · v1.22.0 | router principle 8, plus `sota-docs-workflow` rules/03 §8 |
| P5 a falsification precondition on principle 0 | **adopted** · v1.22.0 | router principle 0 |
| P6 routing as a numbered rule in the hook | **adopted** · v1.22.0 | `scripts/install.sh` hook text |
| P7 `sota-docs-workflow` leads with docs and hides its collaboration half | **rejected on measurement** · 2026-09-23 | Pre-registered, 18 of 18 collaboration tasks routed to it from the description alone ([P7-COLLAB-ROUTING](../evals/results/2026-09-23/P7-COLLAB-ROUTING.md)). The original miss is better explained by the measured task-shape effect (ROADMAP 48) than by the description, so no description change was made. *(Qualified 2026-09-23: "better explained" is a hypothesis this eval cannot test, since it sees description selection only; the results doc states it as "more likely", and so does this row now.)* |

## 2026-09-23 — page 5's blank cells: five undeclared, six a real gap, one not applicable

**Intake shape: the operator read the skill map and said "I still see blank spots".** Twelve
cells on page 5 (section × language) were blank. Each one was checked against the skill
behind it rather than against `docs/LANGUAGE-TIER.md`, which called all twelve principled.

| cells | verdict | resolution |
|---|---|---|
| Typing: rust, jvm, go | **declaration gap** | The row already counts c/c++'s "type-system leverage", and by that definition rust `01 §3–4` (newtype, typestate), jvm `02 §1` (nullability is part of the type, which is .NET's NRT cell) and go `02 §5` (generics) all qualify. Declared in the map |
| Memory / UB: go | **declaration gap** | `05 §7` "unsafe and cgo policy", with a checklist probe. Declared |
| Web / HTTP: rust | **declaration gap** | `05 §7` "Service-edge defaults" (axum/tower). Declared |
| Memory / UB: jvm, python, js/ts, .NET, php, ruby | **adopted: a real gap** | Every GC language has an escape hatch into raw memory, and only go covered its own. The class is stated once in `sota-code-security` rules/06 §3 with per-language detectors (the host-key shape), and each skill has a section and a probe. Every mechanism was checked against its vendor's documentation: JEP 454 (FFM final in JDK 22, `--enable-native-access`, `ALL-UNNAMED`), JEP 471 (`Unsafe` memory access deprecated for removal, JDK 23), .NET `AllowUnsafeBlocks` (default `false`, and also required by `[LibraryImport]`, .NET 7+), Python's `ctypes` warning, Node's `Buffer.allocUnsafe` warning, PHP `ffi.enable` (default `"preload"`), and Fiddle's own README |
| Web / HTTP: c/c++ | **not applicable** | There is no mainstream C/C++ web stack to be idiomatic about. It is now drawn as `n/a` with its reason in the page legend, instead of blank |

**The structural fix.** A blank cell could not say whether it meant "does not apply" or
"nobody wrote it", and 11 of these 12 were the second kind. `gen-skill-map.py` now refuses to
draw an unexplained blank: every cell names a section or carries an entry in
`NOT_APPLICABLE` with its reason. CI already regenerates the map on every run. The guard was
watched to fail on a copy with the `n/a` entry removed. The ten new probes were each run
against a known-bad and a known-good fixture under ugrep and BSD grep. Three were wrong in
their first draft (a `\x27` that POSIX ERE cannot express, an `ffi.enable` probe that
flagged the safe default, and a gemspec probe the fixture never exercised), and all three were
fixed before commit.

**The measurement that had called it "correct, not a gap"** counted UB *vocabulary* (14 and
6 mentions against ~0) and so measured the wrong thing. The hazard in a GC language is not
use-after-free in its own code; it is the call that leaves the runtime.

## 2026-09-23 — five proposals from this session's own field report: all adopted

**Intake shape: a field report written by the session that did the work**
(`FIELD-REPORT-SOTA-SKILLS-2026-09-23.local.md`, reviewed and corrected by its author before
intake; the operator chose rows 1–5 of its recommendation table).

| # | finding | verdict | landed |
|---|---|---|---|
| F1 | A gate printed a denominator and still went blind: it counted files while its predicate read fenced blocks (167 → 110 after a format refactor, 16 broken probes unseen) | **adopted** | `sota-devsecops` rules/09 §2 ("count the unit the predicate reads, not the container") plus a checklist item. Applied to this repo's own check 32, which now prints blocks and inline spans read |
| F2 | `n=$(… \| grep -c .)` under `set -euo pipefail` aborts silently on zero; the fix was already an aside in rules/02 | **adopted, promoted** | `sota-shell-scripting` rules/02 §4, its own bullet naming the substitution form, plus a probe. The probe was run over this repo's scripts: 4 hits, **0 defects** (two scripts do not use `-e`, and one count is guarded by a non-empty test), so the checklist item asks both deciding questions |
| F3 | A PR's CI proves only the arm its own diff shape selects | **adopted** | `sota-devsecops` rules/09 §2c, plus a checklist item |
| F4 | `\b` in `git grep -E` gives a confident zero on macOS | **adopted as a pointer** | `/sota-resume` (its list of confident-zero failure modes, now five) and `/sota-close` (its tells, now three), each pointing at the existing `sota-shell-scripting` rules/06 §2f. No new rule text |
| F5 | Rewriting a running script changes what it executes | **adopted** | `sota-shell-scripting` rules/05 §3d, plus a checklist item. Reproduced both arms before writing |

**Deferred, with a trigger:** a repository lint gate for F2's shape.

- **DEFERRED — revisit trigger: a second occurrence of an unguarded `grep -c` substitution
  aborting a `-e` script in this repo.** It passes the three filters (it has failed, it fails
  silently, it is mechanically checkable), but a new invariant costs a probe, doc-count updates
  and CI time, and the probe run over this repo's scripts found 0 live defects in 4 candidates.

**Found while implementing, not taken here:** reconciling check 32's new block count (109)
against a regex count (110) exposed a ```` ```sh ```` fence nested inside a ```` ```markdown ````
fence in `sota-docs-workflow` rules/01. A CommonMark parser (markdown-it-py) confirms that the
`## §4` heading at source line 107 renders **inside a code block spanning lines 105–164**. It is
outside this intake's rows and is reported to the operator separately.

## 2026-09-24 — concept-matrix triage, second pass: the four already-checked languages

**Intake shape: an open queue with no row and no trigger**, found by a `/sota-resume`
inventory (`docs/LANGUAGE-TIER.md`, "Not yet triaged … for the next pass"). Operator decision
2026-09-24: fold it into ROADMAP 59. Each language's gap-check triages its own cells, and the
cells of go, c/c++, python and ruby are triaged here. Full table in `docs/LANGUAGE-TIER.md`,
"Second pass, 2026-09-24".

| cell | verdict | landed |
|---|---|---|
| c/c++ SQL injection | **adopted: probe for a stated rule** | `sota-c-cpp` rules/04 §3 names the whole-statement C APIs and SQLite's `%s` vs `%q`, plus a checklist item |
| c/c++ authn/authz | **adopted: new section** | `sota-c-cpp` rules/04 §7, relinquishing privileges (CERT POS36-C, POS37-C, Linux `setuid(2)`), plus a checklist item |
| python supply-chain provenance | **adopted: probe for a stated rule** | `sota-python` rules/05 checklist: token env vars, and the publish action's `password` and `attestations: false` inputs |
| 7 cells | **vocabulary artefact** | `scripts/gen-concept-matrix.py` matchers widened; each probe already existed |
| 3 c/c++ cells | **rejected: delegated or covered as a class** | backpressure (`sota-async-concurrency`), deserialization and DoS (`rules/04` §2 plus `sota-code-security` rules/06) |

**What running the probes caught, rather than reading them.** Two of the three new probes
were wrong on their first draft, and both were caught by the known-good fixture:
- The python probe used a `grep -A8` window after the publish step. It reached a later
  docker-login step's `password:` and reported a registry credential as a PyPI token. It is
  now an `awk` scan that stops at the next step.
- The c/c++ bare-call probe matched the continuation line of a multi-line `if`. Requiring the
  trailing `;` removed it.

All three probes return a hit on the known-bad fixture and none on the known-good one, under
both ugrep 7.8.4 and BSD grep 2.6.0 (the `awk` probe under macOS `awk`). **Sources, each read
at intake:**
- CERT POS36-C and POS37-C, on CERT's own site;
- the Linux `setuid(2)` page on man7.org;
- SQLite's `printf.html`, `c3ref/exec.html` and `c3ref/bind_blob.html`;
- libpq's `libpq-exec.html`;
- the MySQL C API pages for `mysql_real_query` and `mysql_stmt_prepare`;
- `pypa/gh-action-pypi-publish` `action.yml` (`attestations` defaults to `'true'`);
- `uv publish --help` (`UV_PUBLISH_TOKEN`) and twine's docs (`TWINE_PASSWORD`).

## 2026-09-24 — gap-check 5 of 9: sota-rust against the ANSSI Secure Rust Guidelines

The denominator is **60**, derived twice:
- the source's reco blocks give **61** IDs, with the English and French lists identical;
- the rendered checklist page gives **60**.

The difference is `LIBS-UNSAFE`, a `TODO` inside an HTML comment: the renderer drops it and a
source grep counts it. That is the gosec lesson at the scale of one row. The guide is under
the Licence Ouverte 2.0, which is permissive, and IDs and ideas were taken, not text. No clippy
registry was derived.

**Buckets: 26 covered (one stale), 6 covered as a class, 1 rule stated with no probe, 2
deliberately not a rule, and 25 real gaps, all closed.** The gaps were not scattered. They
were three whole sections the skill never had.

| gap | landed | what made it real |
|---|---|---|
| The FFI boundary (13 IDs) | `sota-rust` rules/03 §3b plus a probe | `improper_ctypes` warns on `String`/`&str` but **is silent on a `#[repr(u8)]` enum or a `bool` parameter** (measured). A single out-of-range value arriving from C is immediate UB, per the Reference |
| Leak APIs (7 IDs) | rules/03 §3c plus a probe | `clippy::mem_forget` fires only on types with drop glue. Set to deny, it failed on `mem::forget(Vec)` and said nothing about `Box::leak` in the same file (measured) |
| The build outside `Cargo.toml` (4 IDs) | rules/07 §4a plus three probes | `RUSTFLAGS='-C overflow-checks=off'` beat `[profile.release] overflow-checks = true`, and so did a `.cargo/config.toml` in a **parent directory**. A parent-dir `rustc-wrapper` ran on `cargo check` |
| `assert!` and `debug_assert!` | rules/02 §5 plus a probe | a `debug_assert!` that fired under `cargo test` was silent under `--release` |
| `mem::uninitialized` and `mem::zeroed` | rules/03 checklist | the rule existed and the probe did not. `invalid_value` is silent on a generic `T` (measured) |

**One correction.** rules/02 said a panic unwinding out of `extern "C"` is UB and Critical.
Since 1.81 it aborts. It is now High (a DoS), with UB kept for an MSRV below 1.81 and for
foreign exceptions.

**Re-measured by the integrating session, not taken from the agent's report:**
- **The 1.81 abort:** `rustc` 1.97.1 gave exit 134 with "non-unwinding panic", and a
  `catch_unwind` around the call did not catch it. The 1.81.0 release post names the change.
- **`RUSTFLAGS`:** a release build with `overflow-checks = true` panicked on overflow (exit
  101). With `RUSTFLAGS='-C overflow-checks=off'` it wrapped to 0 and exited 0.
- **Probes:** the agent's harness extracts each probe's exact text from the committed files.
  All **22** fixture arms pass under ugrep and under BSD grep (44/44). The rules/01 `pub`-field
  probe is not in that harness; it was tested separately and scored 2 hits on bad, 0 on good,
  under both greps. The agent's report said "26/26 per grep". The difference is not
  reconciled, so this entry records only what was re-run.

**Two first drafts were wrong and were fixed before commit.** A `grep -r … . .cargo` exited 2
under ugrep when `.cargo` did not exist, and double-reported under BSD grep, which enters
hidden directories that ugrep skips (measured). An ancestor-walk probe's exit status was
always 0.

**Concept matrix:** rust's module-boundaries cell was real. The `pub`-field bypass of a
validating constructor had a rule and no probe, and is now closed in rules/01. SQL and logging
were vocabulary artefacts, fixed in `gen-concept-matrix.py`. Rust now classifies 82 of 102
items, and none of its cells is a candidate. Its temp-file and host-key findings (`russh`
rejects unknown keys by default; `ssh2`'s `handshake()` accepts any) are held for the shared
classes in `sota-code-security`.

## 2026-09-24 — gap-check 6 of 9: sota-jvm against find-sec-bugs, 144 patterns, 16 gaps closed

**The denominator is find-sec-bugs 1.14.0, the SpotBugs security plugin: 144 BugPatterns from
121 detectors.** Three derivations agree as sets:
- the source registry, on `master` and at `version-1.14.0`;
- the XML inside the released jar from Maven Central (its SHA-1 matched the published `.sha1`);
- SpotBugs 4.10.4 loading that jar on Temurin 25.0.4 in a container.

A fourth derivation, the pattern strings the Java source actually emits, found 143. The one
missing is `SQL_INJECTION`, which is registered but never emitted. LANGUAGE-TIER's claim that
"jvm has no queryable local tool" was re-tested and is wrong for this machine: the host has no
JDK, but podman runs the tool in one command.

| verdict | n | notes |
|---|---|---|
| covered | 30 | |
| covered as a class | 9 | |
| delegated | 27 | code-security rules/01 §10–11, /02, /05, /07; sota-mobile rules/04 §4.6–4.7; network-security |
| rejected: not a rule | 36 | Scala 11, and source markers 15. Six are single legacy libraries. Three were measured obsolete on JDK 21/25: the Security Manager, NUL-byte paths, and `SSLContext("SSL")`. One is FSB's own low-confidence heuristic |
| **adopted: real gap** | 39 patterns, 16 gaps | each fact read from JDK, Spring, Tomcat, Servlet, JavaMail, Angus or Commons Email source/docs, or measured on Temurin 21.0.12/25.0.4 |
| held for the shared temp-file class | 1 | file permissions (operator decision, 2026-09-24) |
| open, no owner in any skill | 2 | LDAP anonymous bind; XML built from strings. Raised to the operator in the 2026-09-24 resume report |

**The measured facts nobody had written:**
- On JDK 21.0.12 a caller's XSLT ran `System.getProperty` by default; 25.0.4 refused it.
- `Validator` echoed a local file in its error message.
- The JDK 25 strict JAXP template did not stop a `SchemaFactory` `xs:include`.
- `(a+)+$` is linear on current JDKs, while `^(a{1,2}){1,60}$` took 9.1 s at 41 characters.
- `java.net.URL` reads `file:`, and the JDK `HttpClient` refuses it.
- `File.createTempFile` creates `rw-r--r--`, while `Files.createTempFile` creates `rw-------`.
  This is held for the temp-file class.

**The dominant shape was not a missing rule.** In 9 of the 16 gaps `sota-code-security`
already owned the class and only the JVM spelling was absent, the same shape as ruby's
`VERIFY_NONE`. Five were a rule stated with no probe. The JVM host-key spellings (JSch, MINA
SSHD) were absent from `sota-jvm` although the shared rule names them, and are now carried in
rules/04 §4.

**Re-measured by the integrating session:**
- The agent's harness passes **116/116**: 29 probes, each on a known-bad and a known-good
  fixture, under ugrep and BSD grep.
- Its crosscheck script reads the git diff and reports **0** added probe commands that were
  not run verbatim.

**Concept matrix:** jvm's backpressure cell was real (the `Executors` shortcuts use unbounded
queues) and is now closed in rules/03 §2. Its supply-chain cell was half real: a checksum
verification probe was added. The DoS cell was closed by the ReDoS work. The matcher fixes are
in `gen-concept-matrix.py`, and jvm classifies 59 of 64 items.

## 2026-09-24 — gap-check 7 of 9: sota-javascript-typescript against eslint-plugin-security and Semgrep's JS/TS rules

**Intake shape: a gap-check against two external, tool-backed enumerations.** Denominator
**15 + 214**, each derived twice and reconciled item by item. eslint-plugin-security: 14 rules
exported by the npm 4.0.1 package against 15 on `main`. The delta is `detect-invisible-characters`,
which is unreleased. Semgrep OSS `javascript/`+`typescript/`: 214 rules parsed from source
against 212 served by the registry. The delta is one path lower-cased by the registry, plus two
unpublished MCP rules. Security subset: 189. The Semgrep rules are under the Semgrep Rules
License, so **idea classes only; no rule text taken**.

**229 items classified:** 81 covered, 38 covered-as-class, 34 delegated, 28 deliberately not a
rule (each with a measured or source-read reason), 48 closed. The 48 collapse to **14 gap
classes and one correction**:

| gap | verdict | landed |
|---|---|---|
| server-side template raw output (EJS/Pug/Handlebars/Mustache) | **adopted** | rules/05, new section; measured on each engine |
| template source and view name as injection sinks | **adopted** | same; EJS/Pug template source executed `process.version`; Express 5 rendered `../upload` from outside `views/` |
| hand-built HTML; `.replace` string pattern replaces the first match only | **adopted** | same |
| shell passed as argv; `shelljs` | **adopted** | rules/05 command injection |
| request-chosen `require`/`import()` (`data:` URLs run with no file) | **adopted** | same |
| "use `safeLoad`" | **adopted with a correction** | js-yaml ≥4 removed it and made `load` safe; the old line was stale |
| `jwt.decode`/`decodeJwt` do not verify | **adopted** | rules/05 tokens |
| NoSQL operator injection; Express 4 vs 5 query parser | **adopted** | rules/05; measured, plus mongoose `sanitizeFilter` run |
| Ajv `allErrors`, untrusted schemas | **adopted** | rules/05; Ajv security docs |
| `cors({origin:true})`, unanchored regex origin | **adopted** | rules/05; measured |
| invisible identifiers (U+3164) and bidi controls in source | **adopted** | rules/05, new section; measured |
| `node:crypto` AEAD: `update()` before `final()`, missing `authTagLength`, removed `createCipher` | **adopted** | rules/04, new section; measured, DEP0182/0106/0115 |
| Node spellings of TLS/`ssh2`/gRPC verification opt-outs | **adopted as detectors** | rules/04, new section; the class stays in `sota-code-security` rules/04 §5 |
| server-side headless browsers (`goto` as SSRF, string `evaluate`) | **adopted** | rules/04, new section; `file://` and loopback measured with a headless shell |
| path traversal had a rule and no probe | **adopted (audit half)** | rules/05 checklist |

**Deliberately not rules:** `detect-buffer-noassert` (`noAssert` removed, measured),
`detect-pseudoRandomBytes` (DEP0115: identical to `randomBytes`),
`detect-no-csrf-before-method-override` (`method-override` is POST-only by default, read in its
source), X-Frame-Options value injection (Node rejects CR/LF, measured), `X-XSS-Protection`, a
single vendor SDK, and directory listing (an opt-in middleware; recorded, not closed).

**Every probe was run against known-bad and known-good fixtures under ugrep and BSD grep:
28/28.** A harness negative control failed as it should. One probe was wrong in its first
draft: byte-range brackets that ugrep reads as UTF-8 matched 1 of 3 bad files. It was rewritten
as literal alternatives. **Three new sections went to rules/04, not rules/05**, because 05
would have passed the 500-line cap. They were moved by a script asserting the rest of the file
byte-identical.

**Re-measured by the integrating session:**
- The agent's harness passes **28/28**: 14 probes, each on freshly rebuilt bad and good
  fixtures, under ugrep and BSD grep.
- Its verbatim check finds all 14 tested commands in the shipped files.
- The `safeLoad` correction checks out against upstream js-yaml's own CHANGELOG: *"Removed
  deprecated `safeLoad()`, `safeLoadAll()` and `safeDump()` exports."*
- One pending wording fix from the agent was applied: `rejectUnauthorized` is described as an
  option of `https`/`tls` and of agents that forward it. The earlier "most HTTP clients" was
  unverified.

**Concept matrix:**
- The deserialization, event-loop and memory-safety cells were vocabulary artefacts, fixed in
  `gen-concept-matrix.py`. js/ts classifies 92 of 123 items.
- **Resource lifecycle is a real gap left open:** rules at 02 (`using`/`Symbol.asyncDispose`)
  and 03 (`cursor.close()` in `finally`), with no checklist probe.
- N+1 is delegated to `sota-databases` (router rule 3). Property-based testing is prose only
  and not security-relevant.

## 2026-09-24 — gap-check 8 of 9: sota-php against Psalm and Semgrep, 84 checks, 7 gap clusters closed, temp files decided

**Intake shape: an external, tool-backed registry, two of them.** Psalm 6.18.0's taint issue
types (**19**: `src/Psalm/Issue/Tainted*.php`, the `TaintKind` constants and
`docs/running_psalm/issues/` agree. On a planted fixture the tool itself emitted 13 of the 19; why it did not emit Sql, Sleep and Xpath was not investigated) and
semgrep-rules `php/` (**65**: a text parse and semgrep 1.177.0's own loader agree). Semgrep's
rules are under the Semgrep Rules License, so only rule *ideas* were taken, no text. **The
second-registry lesson repeated**: Psalm's issue list names 19 kinds, but its sinks live in
`InternalTaintSinkMap.php` and stub annotations, and that half held `tempnam`, `getimagesize`,
`sleep` and `fetchObject` — three of the gaps.

| class | verdict | landed |
|---|---|---|
| request-chosen class, session key, property (`new $class`, `fetchObject`, `$_SESSION[$k]`, `$guarded = []`) | **adopted: a real gap** | `sota-php` rules/02 §5. Measured on 8.5.9: `SplFileObject` read a file, `fetchObject` ran a constructor, a session key flipped `is_admin` |
| LDAP empty-password bind, `ldap_escape` flags, XPath quoting | **adopted: a real gap** | `sota-php` rules/02 §6. php.net + php-src `ldap.c` (no guard) + RFC 4513 section 5.1.2; `DOMXPath::quote()` (8.4+) measured |
| `setcookie()` carries none of the session cookie's defaults | **adopted: a real gap** | `sota-php` rules/04 §1a. Measured: a bare `Set-Cookie` beside a hardened `PHPSESSID` in one response |
| secrets in stack-trace arguments and `phpinfo()` | **adopted: a real gap** | `sota-php` rules/04 §5a. `#[\SensitiveParameter]` measured; the official image loads no php.ini, so `zend.exception_ignore_args` is off there |
| `base_convert()` on tokens | **adopted: a real gap** | `sota-php` rules/04 §3. 1,000 tokens → 1 distinct output |
| TLS off beyond `CURLOPT_SSL_VERIFYPEER` | **adopted: a real gap** | `sota-php` rules/03 §5. Five spellings measured against a local server |
| `max_execution_time` does not bound `sleep()`/IO | **adopted: a real gap** | `sota-php` rules/04 §5. Measured on macOS and Linux; `request_terminate_timeout` defaults to 0 |
| SSH host keys (phpseclib, ext-ssh2) | **adopted: the PHP detector for the shared class** | `sota-php` rules/03 §5, pointing at `sota-code-security` rules/04 §5. Neither library checks a host key by default (read from source) |
| 4 single-framework or tool-mechanism rules | **rejected: deliberately not a rule** | `laravel-unsafe-validator`, `wp-ajax-no-auth…`, `empty-with-boolean-expression`, `TaintedCustom` |

**Temp-file hygiene: the trigger fired.** `sota-php` has 0 hits for `tempnam`, `tmpfile`,
`sys_get_temp_dir`, `umask`, `chmod` (control 21/21 outside scope), so the condition recorded in
LANGUAGE-TIER ("if that repeats in Ruby *and* PHP") is met. Per the operator's 2026-09-24
decision it becomes a shared class in `sota-code-security` with per-language detectors; no
per-language section was written. The PHP detector and measured forms are in the gap-check notes.

Every new probe was run against a known-bad and a known-good fixture under ugrep and BSD grep
and required to catch **every** planted instance (28/28). That rule caught one: a `sleep` probe
whose `[^)]*` could not cross an `(int)` cast passed a "catches something" check while missing
the commonest form.

**Re-measured by the integrating session:**
- The agent's harness extracts each probe from the committed files and passes **28/28**
  (14 probes, bad and good fixtures, under ugrep and BSD grep).
- The temp-file absence reproduces on the tree: 0 hits in `sota-php` for `tempnam`, `tmpfile`,
  `sys_get_temp_dir` and `umask`, while the control (`mktemp`) is found in 9 skill files.
- One overstatement in the agent's draft was corrected above. Psalm emitted 13 of its 19
  taint types on the fixture, not all of them.

**Not taken here, for a later pass:** the shared TLS detector in `sota-code-security` rules/04
§10 has a PHP token (`CURLOPT_SSL_VERIFYPEER,\s*0`) that caught 0 of 6 planted PHP TLS-off
lines. The same goes for a PHP row for the shared host-key rule. Both are shared-file edits,
batched with the other languages' host-key rows.

## 2026-09-24 — temp-file and permission hygiene becomes a shared class

**The recorded trigger fired** (`docs/LANGUAGE-TIER.md`, "revisit trigger: the PHP
gap-check"): PHP lacked temp-file guidance too, making **six of nine** language skills with
none. **Operator decision 2026-09-24: a class stated once, with per-language detectors**, the
same design as host-key verification in `sota-code-security` rules/04 §5. The alternative,
per-language sections, was rejected because it would give six copies to drift. Python's and
Go's existing sections stay, since they carry library detail.

| item | verdict | landed |
|---|---|---|
| name-then-create, hand-built temp paths, widened modes (CWE-377/378/379) | **adopted as a shared class** | `sota-code-security` rules/06 §6.1, plus a checklist item |
| per-language unsafe and safe forms | **adopted** | §6.1's table: C/C++, Python, Go, Ruby, Rust, Java/Kotlin, Node, PHP. .NET's row lands with its gap-check |
| traps inside the safe APIs | **adopted** | Java `File.createTempFile` 0644; Rust `tempfile::tempdir()` 0755; PHP `tempnam()`'s silent fallback directory. All measured by the gap-check agents |

**The eight detectors were run by the integrating session**, taking the exact text from the
file, against a known-bad and a known-good fixture per language. Each gave 2 hits on bad and 0
on good, under ugrep and BSD grep (32 runs). Sources for the C half: the macOS `mktemp(3)` page
(*"particularly dangerous from a security perspective"*) and `tmpnam(3)`'s SECURITY
CONSIDERATIONS; MITRE's titles for CWE-377, 378 and 379, fetched.

## 2026-09-24 — gap-check 9 of 9: sota-dotnet against the NetAnalyzers Security rules, 13 gaps closed

**Intake shape: a tool-backed registry, derived three ways.** The .NET analyzer's own
`AnalyzerReleases.Shipped.md` (dotnet/sdk) and a reflection dump of the .NET 10 SDK's analyzer
DLLs agree on **94** Security-category rules, ID for ID; the dotnet/docs index lists 92 (it
still carries CA2109, removed in the 8.0 release, and omits CA3005/CA5404/CA5405). The SYSLIB
obsoletion list was used as the second registry. "`.NET` has no queryable local tool" was
re-tested and is false: the SDK container ships the analyzers and builds fixtures.

| # | gap | verdict | landed |
|---|---|---|---|
| G1 | Security CA rules ship disabled (70) or Hidden (24); `latest-Recommended` fired 4 of 14 planted violations, `AnalysisModeSecurity=All` 10; an editorconfig category line only raises enabled-by-default rules | **adopted, measured; corrects the skill's own BUILD step** | rules/06 §2 + probe; SKILL.md BUILD 3 |
| G2 | BinaryFormatter compat package + switch re-arm it on .NET 9+ | **adopted, measured** (both halves needed) | rules/04 §2 + probe |
| G3 | DataSet/DataTable as a deserializer; JavaScriptSerializer+SimpleTypeResolver | **adopted** | rules/04 §2 + probe |
| G4 | JWT TokenValidationParameters switched off (CA5404/5405) | **adopted** (defaults read in IdentityModel source) | rules/04 §7 + probe |
| G5 | Cookies carry no attributes by default | **adopted, measured** | rules/04 §7 + probe |
| G6 | Open redirect | **adopted** | rules/04 §7 + probe |
| G7 | Html.Raw / HtmlString / MarkupString | **adopted** | rules/04 §7 + probe |
| G8 | Verb-less actions answer GET, which antiforgery skips | **adopted, measured** (GET 200 vs POST 400 under global AutoValidateAntiforgeryToken; CA5395 stays silent under that global filter and fires only once a controller carries `[ValidateAntiForgeryToken]`) | rules/04 §7 + 2 probes |
| G9 | Path.Combine drops the root; Zip Slip via per-entry ExtractToFile | **adopted, measured** | rules/04 §3 + 2 probes |
| G10 | Hard-coded TLS protocol | **adopted** | rules/04 §5 + probe |
| G11 | Legacy Rfc2898DeriveBytes ctor = SHA-1 × 1000 | **adopted, measured; corrects the skill's own recommendation** | rules/04 §5 + probe |
| G12 | Regex match timeout is infinite by default | **adopted** (runtime source) | rules/04 §3 + probe |
| G13 | Target framework past end of support (concept-matrix cell) | **adopted** | rules/06 checklist |

**Not a rule, with reason:** System.Web-only rules (CA5363/5365/5368), .NET Framework
switches (CA5361), XSLT script / XslTransform (CA3076/5374), XAML (CA3010), one cloud vendor's
legacy storage SDK (CA5375-5377), CAS-era CA2119, CA2153 (ignored on .NET Core+), CA2109
(removed). **Held, no verdict:** CA3011/CA5392/CA5393 (DLL load path; no owner in the library)
and SYSLIB0003 (CAS attributes compile and enforce nothing).

Every probe (16) was run against a known-bad and known-good fixture under ugrep and BSD grep;
two first drafts failed on the fixture and were rewritten before commit (the editorconfig probe
exited 2 on a missing path; the notes-only SSH.NET detector missed a two-client file).

**Re-measured by the integrating session:**
- The agent's harness passes **15/15 under ugrep and 15/15 under BSD grep**.
- G1's counts were re-read from the container build logs, not taken from the report:
  - the default build: 0 CA warnings;
  - `latest-Recommended`: 6 distinct IDs, of which 4 are security (CA5350, CA5351, CA5359,
    CA5397) and the other two are CA1050 and CA1850;
  - the `.editorconfig` category line: the same 4;
  - `AnalysisModeSecurity=All`: 10.
- The staged CA5395 wording fix, which the agent's pre-commit hook had refused before a ledger
  entry existed, lands here.
- .NET's temp-file row is added to `sota-code-security` rules/06 §6.1. Its detector gives 2
  hits on bad and 0 on good under both greps.

**Matcher: a whole class, not a cell.** .NET's command-injection cell was a vocabulary
artefact of a general kind. Checklist items store probes as escaped regex (`Process\.Start`),
so a matcher written for `process.start` never matches them. `gen-concept-matrix.py` now also
matches the backslash-stripped text, as a union, so no existing match can be lost. Measured:
.NET's command-injection cell flipped to present, rust gained one classified item, and nothing
else moved.

## 2026-09-24 — ROADMAP 59 closing pass: shared host-key rows, and a PHP TLS token that missed

**Intake shape: findings the language gap-checks handed back for the shared classes.** Each was
read from the library's own source by the gap-check agent, and each is written once in
`sota-code-security` rules/04 §5, the host-key class decided on 2026-09-23.

| library | verdict | what the source says |
|---|---|---|
| Rust `russh` | **adopted as a detector row** | `check_server_key` defaults to `Ok(false)` and rejects. The finding is an override returning `Ok(true)`, and the crate's own test handler is one |
| Rust `ssh2` | **adopted as an absence** | `Session::handshake()` checks no host key. Verification needs `known_hosts()` and `check_port` |
| PHP phpseclib | **adopted as an absence** | `login()` never compares the key, and the KEX signature is checked only in `getServerPublicHostKey()`, which nothing in the library calls (4.0.1; 3.x not read) |
| PHP ext-ssh2 | **adopted as an absence** | no known-hosts support. `ssh2_fingerprint()` defaults to MD5 |
| .NET SSH.NET | **adopted as a detector row and an absence** | `CanTrustHostKey` returns true with no `HostKeyReceived` handler, and `HostKeyEventArgs` starts `CanTrust = true` |

**The shared TLS row's PHP token was too narrow.** `CURLOPT_SSL_VERIFYPEER,\s*0` matches one
spelling. The PHP gap-check measured five ways to turn verification off. The row now matches
`SSL_VERIFYPEER`/`SSL_VERIFYHOST`/`verify_peer`/`verify_peer_name` set to `false` or `0` in call
or array form, plus `allow_self_signed => true`.

**Re-measured by the integrating session, with the text taken from the file:**
- The widened PHP pattern hit **6 of 6** planted TLS-off lines and **0** of the safe ones,
  under ugrep and BSD grep. The old token hit 0 of the same 6, because none used its exact
  `, 0` form.
- The checklist's host-key regex, extended with `CanTrust = true`, hit the bad SSH.NET
  fixture and missed the pinned-fingerprint one.
- The russh probe hit an `Ok(true)` handler and missed one that returns
  `check_known_hosts(…)`.

My first extraction of the PHP pattern for that test cut it short at `(true|1)`. A second one
left the row's `(PHP)` annotation on, which zsh read as a glob group and did not strip, and
that scored 5 of 6. Both were artefacts of how I extracted the pattern, not of the pattern
itself. The figure above is from a third extraction that took the whole line.

## 2026-09-24 — concept-matrix triage, third pass: the queue closes

**Intake shape: the last cells of ROADMAP 59's candidate queue.** Every cell opened; the full
table is in `docs/LANGUAGE-TIER.md`, "Third pass, 2026-09-24". Of 17 language cells, **12 were
real**, **2 were vocabulary artefacts** and **3 were delegated**.

| cell | verdict | landed |
|---|---|---|
| logging: jvm, python, .NET | **adopted: probe for a stated rule** | each skill said "don't log secrets" and never probed it. Probes add the language's own leak paths: record `toString`/`ToString`, dataclass `repr`, EF Core `EnableSensitiveDataLogging` |
| logging: ruby | **adopted: rule and probe** | `sota-ruby` rules/03 §8: `Data`/`Struct#inspect`, and Rails `filter_parameters` as a neutral example |
| logging: php | **vocabulary artefact** | `#[\SensitiveParameter]` probe at rules/04 §5a. The stated log-injection rule (rules/02 §4) got its probe in the same change |
| date and time: rust, go, c/c++, jvm, .NET | **adopted: rule and probe** | no skill of the five said anything about clocks. Each now separates the monotonic interval clock from the wall clock, in its own spelling |
| N+1: .NET | **adopted: rule and probe** | rules/01 pointed to an N+1 rule that did not exist; EF Core lazy loading was named nowhere in the library |
| N+1: js/ts | **adopted: probe for a stated rule** (quadratic half) | spread-accumulator `reduce`; the N+1 half stays with `sota-databases` |
| resource lifecycle: js/ts | **adopted: probe for a stated rule** | `finally`/`await using` release of handles, cursors and pooled clients |
| N+1: go | **vocabulary artefact** | rules/06's `O(n²)` probe; the matcher lacked the superscript |
| N+1: c/c++, jvm; module boundaries: php | **rejected: delegated** | `sota-databases` rules/03 and `sota-performance` rules/02 name Hibernate and JPA; `sota-architecture` rules/01 §2 names deptrac |

**What running the probes caught, rather than reading them.** The harness took its 26
commands verbatim from the committed diff and ran each on a known-bad and a known-good fixture
under both greps. Two of the 26 were wrong on the first run:
- go's `grep -rn 'time\.Parse('` exited **2 under ugrep** (a literal `(` outside `-E`) and
  passed under BSD grep. It is now `grep -rnF`.
- ruby's `[^#]*#\{` could not reach a second interpolation and missed the known-bad
  entirely. It is now `.*#\{`.
Reading caught two more. The python field probe flagged the correct `field(repr=False)`, and
three probe notes claimed a clean result on message text that the regex does match. After the
fixes: **52/52**, 26 commands × 2 greps.

**The matcher errs both ways.** Tracing each match to its substring found six **false
presences**: `slog` inside `syslog`, `n+1` inside a `find` command, `clock` in "wall-clock
bound", and `import` inside `DllImport`. Each hides a real absence that the candidate list
cannot show. They are recorded, not fixed.

**Sources, each read or run at intake:**
- Rust std `SystemTime`/`Instant` docs (rustc 1.97.1), and a compile proving E0599;
- `go doc time` (go1.27.1), plus a run;
- the C++ draft `[time.clock.steady]` and `[time.clock.system]`, POSIX `localtime`, CERT CON33-C, and Linux `clock_gettime(2)`;
- Java SE 25 javadoc for `Record`, `System`, `LocalDateTime`, `SimpleDateFormat` and `DateTimeFormatter`, plus Kotlin's data-class docs;
- Microsoft Learn for `DateTime.Now`, C# records, `EnableSensitiveDataLogging`, and EF Core lazy loading, efficient querying and split queries;
- `docs.ruby-lang.org` `Data`, the Rails configuring guide, and the rails/rails `filter_parameter_logging.rb.tt` template;
- runs on Temurin 25, the .NET 10 SDK, Ruby 4.0.6, Python 3.14.6, PHP 8.5.9 and Node 22.22.1.

**Re-measured by the integrating session:**
- The harness's command list was re-extracted from the agent's committed diff (26 commands)
  and re-run: **52/52**.
- Go's `t == t.Round(0)` printed `false` on a fresh run, the trap the go probe names.

## 2026-09-24 — concept-matrix fourth pass: the matcher's false presences

**Intake shape: the matrix's own present cells.** The third pass found six cells lit by a
substring accident. This pass printed the substring behind every present cell
(`gen-concept-matrix.py --explain all all`) and found the class was far wider: `/dev/null`,
`uv.lock`, `// SAFETY:`, "concurrency", "results", "iterator invalidation", `-fsanitize`.
Two **pinned** floor concepts were 9/9 only by accident on c/c++ — vulnerability scanning
("safety-standard analysis") and input validation. Of 28 cells that went absent, **17 were
real**, **7 were vocabulary artefacts** and **4 were delegated or covered as a class**.

| cell | verdict | landed |
|---|---|---|
| c/c++: logging, vuln scanning, provenance, input validation | **adopted: probe for a stated rule** (logging: rule and probe) | rules/04 §2, §3; rules/06 §5 — CWE-117; `URL_HASH`/`GIT_TAG` from CMake's docs; OSV-Scanner's `conan.lock` row |
| python: data race, autoescape, assert-as-authz, unbounded queue, money | **adopted: probe for a stated rule** | rules/01 §8, rules/05 §1 and §7a, rules/04 §9, rules/03 §12; Jinja2 3.1.6 and 3.14.6 runs |
| jvm: numeric | **adopted: rule and probe** | rules/01 §1: `new BigDecimal(0.1)`, `equals` vs `compareTo`, `divide` without scale — JDK 25 run |
| php: date/time | **adopted: probe for a stated rule** | rules/01 §5; PHP 8.5.9 run (`modify` mutates) |
| ruby: resource lifecycle, backpressure | **adopted: rule and probe** | rules/01 §7 block form; rules/05 §2 `SizedQueue` — Ruby 4.0.6 runs |
| ruby: module boundaries, profiling | **adopted: probe for a stated rule** | rules/01 §7 `require_relative`; rules/05 §8 |
| .NET: module boundaries | **adopted: probe for a stated rule** | rules/02 §6 `InternalsVisibleTo`, csproj item measured on SDK 10.0.401 |
| js/ts: provenance | **adopted: probe for a stated rule** | rules/05 npm supply chain: tokens vs trusted publishing (npm docs) |
| php absence; python, js/ts version floor; js/ts data race, allocation; go provenance, input validation | **vocabulary artefact** | strpos truthiness; `requires-python`; `engines.node`; check-then-act; unbounded `Map` cache; `GOSUMDB`/`go mod verify`; `MaxBytesReader` |
| rust N+1; php task leaks, backpressure, provenance | **rejected: delegated / covered as a class** | `sota-performance` rules/02; FPM shared-nothing; `pm.max_children`; install-time-code probe |

**Four probes never ran.** A PCRE `(?!…)` lookahead inside `grep -E` exits 2 under BSD grep
and ugrep alike: .NET and jvm "Mutable static state", jvm "Data-race smells", and php's XSS
probe — which also discarded stderr, so it reported nothing. Rewritten as ERE plus `grep -v`.

**Measured:** 20 items, 41 commands extracted from the committed files, each on a known-bad
and a known-good fixture: 82/82 under BSD grep, 82/82 under ugrep. `--assert-universal` exits
0 with 24 pinned concepts and exit 1 when a non-9/9 concept is pinned.

**Re-measured by the integrating session:**
- The agent's harness passes **82/82 under BSD grep and 82/82 under ugrep**: 41 commands
  extracted from the committed files, each on a known-bad and a known-good fixture.
- `--assert-universal` exits 0 with 24 pinned concepts. The agent's saved failure run shows it
  exiting 1 with a concept pinned that is not 9/9.
- A PCRE lookahead inside `grep -E` exits 2 under both BSD grep 2.6.0 ("repetition-operator
  operand invalid") and ugrep 7.8.4 ("invalid syntax"), so the four probes that used one
  could never have reported anything.
- The README hero count moved from ~72k to ~73k lines. The agent made this one edit outside
  its file bounds because invariant 6 blocked the commit, and it asked for it to be reviewed.
  It is the gate's own arithmetic (72,534 lines), not a judgement.

**The matcher's listing threshold hides a concept that is missing almost everywhere.** A
universal concept becomes a candidate only when five or fewer languages lack it. A count over
all 32 universal rows found one concept hidden that way: `numeric precision & money`, at 3/9.
It is recorded as ROADMAP 65 rather than triaged here.

## 2026-09-24 — ROADMAP 65: the absence the matcher could not list

**Intake shape: the matrix's own listing rule.** `gen-concept-matrix.py` listed a universal
concept as a candidate only when five or fewer languages lacked it, and no rationale was
recorded anywhere. Operator decision: list every absence. A new MOSTLY ABSENT block carries
6-9 missing; CANDIDATE GAPS is unchanged. Its first run listed exactly one concept,
`numeric precision & money` at 3/9. All six absent cells were real.

| cell | verdict | landed |
|---|---|---|
| rust, c/c++, .NET, php, ruby: numeric | **adopted: rule and probe** | rust rules/01 §3; c/c++ rules/03 §2 (C++ [conv.fpint], C11 6.3.1.4, UBSan run); .NET rules/01 §1 (Math.Round docs, SDK 10 run); php rules/01 §4 (php.net: BcMath\Number and RoundingMode 8.4+, bcmath.scale "0"); ruby rules/01 §7 (4.0.6 run) |
| go: numeric | **adopted: probe for a stated rule** (plus a money bullet) | rules/05 §1 stated the JSON-to-float64 loss; §5 money bullet; go1.27.1 run |
| all six: covered as a class by `sota-code-security` rules/06 §1 | **rejected** | its probe is a question with no command, and it names none of the language traps (truncating casts, default rounding modes, JSON to float, bcmath scale) |

**Measured:** 6 items, 17 commands extracted from the committed files, each on a known-bad
and a known-good fixture: 17/17 under BSD grep 2.6.0, 17/17 under ugrep 7.8.4.
`--assert-universal` exits 0 with 25 pinned concepts and exit 1 when a 6/9 concept is pinned.

**Two matcher alternatives were dead or false.** `toFixed` never matched (items are
lowercased first), and `rounding` lit js/ts from "surrounding". Fixing the second left a
js/ts floating-promise probe with no concept at all (classified 92 -> 91): a vocabulary hole,
not a skill gap.

**Re-measured by the integrating session:**
- The agent's harness passes **34/34**: 17 commands, under ugrep and BSD grep.
- `--assert-universal` exits 0 with 25 pinned concepts, and the new MOSTLY ABSENT block reads
  `(none)`.
- The language facts behind the new bullets reproduce locally:
  - rustc 1.97.1 gives `(19.99f64*100.0) as i64` = **1998**;
  - Ruby 4.0.6 gives `-7/2` = **-4** and `2.5.round` = **3**;
  - PHP 8.5.9 gives `(int)(19.99*100)` = **1998** and `bcdiv("1","3")` = **"0"**.

## 2026-09-24 — ROADMAP 64: three unowned classes become shared classes in sota-code-security

**Operator decision 2026-09-24: all three are owned by `sota-code-security`**, each stated once
with per-library detectors, the design of host keys (rules/04 §5) and temp files (rules/06 §6.1).

| item | verdict | landed |
|---|---|---|
| LDAP bind with an empty password used as a login (RFC 4513 section 5.1.2), plus anonymous bind for lookups (find-sec-bugs `LDAP_ANONYMOUS`) | **adopted as a shared class** | rules/02 §9, a per-client table (PHP, JNDI, .NET S.DS.P, python-ldap, ldap3, go-ldap, ldapjs/ldapts, net-ldap), 7 detector rows, a checklist item |
| XML built from strings (CWE-91, find-sec-bugs `POTENTIAL_XML_INJECTION`) | **adopted as a shared class** | rules/01 §11 bullet beside LDAP/XPath, 7 detector rows, a checklist item |
| native library search-path loading (CWE-427; CA5392, CA5393, CA3011) | **adopted as a shared class** | rules/06 §3.1: Windows, .NET, glibc/musl, macOS, Python, Java, Node; 7 detector rows plus a binaries row; a §7 starter row; a checklist item |

**Measured, not recalled.** The PHP gap-check listed the empty-password bind as NOT verified.
It is now: OpenLDAP 2.6.14 refuses it by default (53, "unauthenticated bind (DN with no
password) disallowed") and accepts it with `allow bind_anon_dn`, and PHP, JNDI, .NET (Linux),
python-ldap, ldapjs, ldapts and net-ldap all report success, including PHP for a DN that does
not exist. ldap3 and go-ldap refuse an empty password client-side, but ldap3 turns an empty
*username* into an anonymous bind that succeeds on the default server. Active Directory's
`DenyUnauthenticatedBind` defaults to 0 ([MS-ADTS]). XML injection reproduced in seven
languages; CDATA wrapping does not stop it. Library planting reproduced on glibc, musl and
macOS: glibc treats an empty `LD_LIBRARY_PATH` entry as the CWD and musl did not; macOS
searches the CWD for a bare `dlopen` name; a relative `RUNPATH` and a relative
`java.library.path` both loaded the CWD's copy.

**Detectors:** 21 rows extracted from the committed files, each on known-bad and known-good
fixtures: 67/67 under ugrep and 67/67 under BSD grep. The first run failed one fixture (a
trailing colon followed by a space) and the row was widened.


**Re-measured by the integrating session:**
- The agent's detector harness passes **134/134**: 21 rows extracted from the committed file,
  each on known-bad and known-good fixtures, under ugrep and BSD grep.
- The XML class reproduces in Python:
  - a string-built document with the payload `bob</name><role>admin</role><name>x` yields
    roles `['admin', 'user']`;
  - the escaped one yields `['user']`;
  - a CDATA-wrapped payload that closes the section early yields `['admin', 'user']` again,
    so CDATA is not a fix.
- Operator decision 2026-09-24: all three classes live in `sota-code-security`. LDAP is in
  rules/02 because an empty-password bind is a login bypass, and rules/01 already owns LDAP
  injection. XML is in rules/01, beside the injections it resembles. Native search paths are in
  rules/06 §3, the native-code escape hatch. The library map lists file titles, not sections,
  so it needs no change.

## 2026-09-24 — closure pass: a measurement table overwritten, and a fifth lookahead probe

**A dated measurement had been edited instead of superseded.** `docs/LANGUAGE-TIER.md`'s depth
table ("Depth, measured 2026-09-23") had its rows overwritten one language at a time as each
gap-check landed. The later concept-matrix passes then added items to most skills, so every
row was stale, including the rows edited that same day.
- **Found by** re-running both derivations: `cat skills/sota-<lang>/rules/*.md | wc -l`, and
  the "items read" column of `gen-concept-matrix.py`. For example, python read 2,152 / 65 in
  the table against **2,194 / 72** now, and .NET read 721 / 53 against **787 / 58**.
- **Fix:** the 2026-09-23 table is restored from `git show 1be09d3:docs/LANGUAGE-TIER.md`, and a
  re-measured table stands beside it with the commands that produced it.

**A fifth lookahead probe.** `sota-testing` rules/03's mock check used `(?!\.)`, with no tool
named. It exits 2 under `grep -E` and under ugrep (measured), and `rg`'s default engine has no
lookaround either, so the check could never report anything. It is replaced with
`jest\.mock\(['"][^.]`, which gave 2 hits on the bad fixture and 0 on the good one under ugrep
7.8.4 and BSD grep 2.6.0. A sweep of all 317 tracked skill files for `(?!`, `(?=`, `(?<!` and
`(?<=` now finds only prose describing the old bug. The control, this entry's own new note,
was found.

**Checked and left standing:** "no recorded rationale" for the concept matrix's old ≤5 cap
(ROADMAP 65, the fifth pass). It was asserted after reading only the code. Since then, the
introducing commit `e1b20d8`'s message, the original script (no comment at the cap) and the
matrix's ledger entry have all been read. None states a reason, so the claim holds.

## 2026-09-24 — a field report that was never taken in: the platform session of 2026-09-16

**Intake shape: a `/sota-resume` pass that matched each local report's findings against this
log by content, not by date.** `FIELD-REPORT-PLATFORM-2026-09-16.local.md` (a backlog pass on
an infrastructure/GitOps repo, written at v1.42.1) appears nowhere in this log. Its three
proposal markers had no coverage: `obviat` and `multios` returned 0 hits, and the table-pipe
pattern's one hit (`sota-javascript-typescript` rules/05) is unrelated. The control
(`heredoc`, 4 files) was found. The other three local reports from 09-15 and 09-16 are logged
above: EDR 09-16 by filename, EDR 09-15 and static-analysis 09-15 by their findings (a pattern per
finding, each with a ledger hit). The operator chose
option (a) for all three.

| # | finding | verdict | landed |
|---|---|---|---|
| F1 | `/sota-resume` §2 had no class for an item whose gap is **covered by a different mechanism**, so it lands in READY, the one class that leads to building. The report's session nearly shipped a 96h backup alert beside a 25h rule that already covered the job | **adopted** | `commands/sota-resume.md` §2: ALREADY DONE becomes **ALREADY DONE / OBVIATED**. A READY item that adds a new control must name the incumbent control, and the incumbent is tested by firing it at the target. README's two class lists updated |
| F2 | `cmd \| python3 - <<'PY'`: bash discards the piped data, and zsh's default-on `MULTIOS` prepends it to the program | **adopted** | `sota-shell-scripting` rules/06 §1: a table row, a rule and a checklist sweep. Reproduced before writing: zsh 5.9 `1 2`, `unsetopt multios` `2`, bash 3.2.57 and 5.3.15 `2`, `sh` `2`, and the report's `NameError: name 'false'` at `<stdin>` line 1. The sweep matched both bad fixtures and neither good one, under ugrep and BSD grep |
| F3 | A `\|` inside backticks in a table cell still splits the cell | **adopted with a correction** | `sota-docs-workflow` rules/02 §1 plus a checklist probe. **The correction:** the report says the row renders as extra cells. On GitHub's own renderer (`gh api markdown`, mode `gfm`), the code span breaks and the **overflow cell is dropped** to fit the header, so content disappears and the table does not get wider. The report's naive-split caveat held, and a second one turned up: a regex false-positives on adjacent code spans (`` `a` \| `b` ``). The probe is therefore a perl span walker, run verbatim from the file against four row shapes (plain, bad, escaped, adjacent spans) |

**Found while implementing, not taken here:** the F3 probe, run over this repo's 424 tracked
`.md` files, flags 17 table rows with an unescaped pipe inside a code span. Three were rendered
through GitHub and all three lose content. The worst is `sota-shell-scripting` rules/01's
`Left of && / ||` row, whose explanation cell renders empty (a second row there is flagged too). The others are in
`sota-threat-modeling` rules/02 (six rows of grep patterns), `sota-async-concurrency` rules/02,
`sota-shell-scripting` SKILL.md, `docs/INDEX.md` and six rows of this log. Reported to the
operator, not fixed here.

## 2026-09-25 — OWASP, item by item: the intake method, a June pass that was never logged, and the template made binding

**Intake shape: an operator-supplied list of 19 OWASP projects, checked in full rather than
by name.** The operator's framing is the lesson: *touching a project once is not implementing
its guidance.* A name sweep had found ASVS in 7 files, WSTG in 3 and Go-SCP in the ledger,
and I first called four of them "already covered" on that basis. None was: the June pass (below)
compared ASVS by **17 chapters** against **345 requirements**, took **2** items from Go-SCP's
table of contents, and filtered the cheat sheets to one private stack, which skipped every
Java, .NET, PHP and Ruby sheet.

**The June 2026 OWASP pass, recorded here for the first time.** PRs #19 and #22–#29
(2026-06-28) gap-checked the library against the Cheat Sheet Series, ASVS 5.0 at chapter level
(16/17 covered; V17 WebRTC closed in #28), WSTG (which produced `sota-testing` rules/09 in
#29) and Go-SCP. It was recorded only in a private memory file and in commit titles, so its
decisions were invisible to the next reader. One of them stands and is recorded now:
**organisational/GRC material (SAMM maturity scoring, security-champion programmes,
training, culture) is out of scope — this is a code-building library, not a GRC framework.**
The 2026-09-25 mapping still compared those items and lists them as `out_of_scope`, so the
decision is visible item by item rather than assumed.

**The method (all artefacts in the git-ignored `offline/owasp-gap-2026-09-24/`; sources are
CC BY-SA, so no text enters this CC BY repo — ids and our own wording only).**

- **Denominators from source files, each reconciled to an independent count:** ASVS 5.0.0 345,
  AISVS 1.0 191, WSTG 114, SCVS 87, LLMSVS 70, SCSVS 220, MASVS 24, MASTG 292, SAMM 90,
  DSOMM 251, Cornucopia 160, Secure Headers 106, SCP-QRG 214, Champions 10, plus 5,265
  practices extracted from prose (121 cheat sheets, 4 of them deprecation stubs; Go-SCP; the
  threat-modeling playbook; Proactive Controls 2024; the Code Review Guide v2 PDF) —
  **7,439 items**. Three mismatches were reconciled to a named cause before use, plus one
  count-passing defect (every Champions item's text read "What").
- **Per item:** covered (a cited `skills/…:LINE` the agent read) · partial · missing (≥2
  searches in different vocabulary) · out_of_scope. Every missing/partial was re-argued by a
  refuter told to find coverage; a BM25 shortlist over 3,270 library sections widened recall
  past grep's vocabulary (control: all 12 ASVS WebRTC items shortlisted `sota-api-design`
  rules/05).
- **Result:** 4,808 covered · 1,858 partial · **498 missing** · 275 out of scope. Hand checks:
  `covered` held in **44 of 50** (88%, so gaps are understated), `missing` in 4 of 4
  controlled searches. One mapping batch invented placeholder ids for 57 items; the
  aggregator's id check rejected them and the batch was re-run.
- **Synthesised into 847 themes** (205 high · 470 medium · 172 low), every one of the 2,356
  gap rows in exactly one theme, then placed against each target skill's real sections. The
  adoption itself follows in later PRs, each re-verifying its gaps against the tree.

**Adopted with this entry — the template becomes binding for language skills.** The
operator's instruction: *a section that is universal across languages joins the template,
and the template is what every future coding skill is built from.* Checking it found the
template stale — `docs/SKILL-TEMPLATE.md` listed **12** universal concepts while
`UNIVERSAL_FLOOR` pinned **25** — and a hole: the floor check sees only the nine languages in
`LANGS`, so a tenth language skill would never be checked. Now:

- the template lists all 25, and states the rule: a rule added to one language skill goes to
  all nine plus the floor, to some plus a `conditional:` concept, or stays with a reason in
  `LANGUAGE-TIER.md`;
- **invariant 35** fails when the template's list and the floor differ (it has already
  drifted once, silently, so it passes all three of the ledger's filters);
- **invariant 36** fails when a router row reading "Any … code" is not in `LANGS`, or the
  reverse. It has **not** failed in the wild; it was added on operator instruction because it
  is cheap and loud, and that exception is recorded here so it is not mistaken for the norm;
- `CONTRIBUTING.md` now sends a new skill's author to the template; `docs/INDEX.md` no
  longer says "12".

**Also recorded:** a false statement found while updating the counts. CONTRIBUTING said that
on 2026-09-15 "every one of the 34 checks was green"; invariant 34 was added later (#400), so
each count bump had quietly rewritten a historical sentence. It now reads "every check then
in force".

## 2026-09-25 — three splits ahead of the OWASP adoption (ROADMAP 66, step 2)

**Why now, and why these three.** The placement pass for the 847 OWASP gap themes projected
three rules files past the 500-line cap: `sota-code-security` rules/02 (317 → ~549), rules/04
(431 → ~521) and `sota-jvm` rules/04 (452 → ~506). The operator approved splitting first, as
reviewed PRs with no rule-text change, so each adoption PR lands in a file with room.

**The seams, chosen by where the incoming lines land and what the library cites.**
- rules/02 §2 Sessions + §3 JWT → **rules/17 sessions & tokens**, numbers kept (several
  numbered sections). They take 67 of rules/02's incoming high/medium lines, so both files
  keep room: rules/02 242, rules/17 90.
- rules/04 §8 tamper-evident logs → **rules/18**, renumbered to §1 (a single section). It
  receives none of the incoming lines and is a self-contained topic: rules/04 352, rules/18 94.
- `sota-jvm` rules/04 §3 XML → **rules/07 XML**, renumbered to §1, which the placement pass
  had already proposed: rules/04 399, rules/07 66.

**Verified:** every line deleted from a source reappears in its new file except the two
renumbered headings (a scripted diff check); the moved checklist bullets (6, 3, 3) went with
their sections. Invariant 18 caught 14 broken `§` references (3 of them my own pointer text);
an explicit sweep found the rest it cannot see — rules/17's header citing `rules/02 §2`
(passing silently), and bare pointers in both SKILL.md top-10s and in the router's
cross-cutting rules 17 and 18, which now name rules/18. Historical text (this log, and two passages in
ROADMAP's history prose) is left as written and translated by the table above.

**An instrument defect of mine, found on the way.** My filter over the gate's output
excluded every line containing "ok", and hid invariant 10's report on
`17-sessions-and-t**ok**ens.md`. The gate was right; the filter now anchors on `^    ok`.

## 2026-09-25 — ROADMAP 66 step 3a: four concepts completed to 9/9 and pinned (the floor is now 29)

Operator-approved list (A). Each concept was 7/9 or 8/9 at checklist level; the missing cells
were written as a BUILD rule and an audit probe, each probe run against a bad and a good
fixture under ugrep and BSD grep before it shipped. Every API a rule names was read in its
primary source first.

| concept | cell written | source themes (OWASP ids) | verified against |
|---|---|---|---|
| deserialization / unsafe parsing | `sota-c-cpp` rules/04 §2: no wire-buffer-to-struct casts; libxml2 without `XML_PARSE_NOENT`/`XML_PARSE_DTDLOAD`, with `XML_PARSE_NONET` | T527 (XML_External_Entity_Prevention cheat sheet) | libxml2 `parser.h` (macOS 15.4 SDK) |
| resource limits / DoS guards | `sota-c-cpp` rules/04 §2: depth, count, allocation and decompression caps; never `XML_PARSE_HUGE` on untrusted input | T488 (XML_Security cheat sheet) | same header: `XML_PARSE_HUGE` "relax any hardcoded limit" |
| TLS / transport verification | `sota-c-cpp` rules/04 §4 (OpenSSL: `SSL_set1_host`, verify result **and** a non-NULL peer certificate; libcurl verify options) and `sota-rust` rules/05 §7 (reqwest/native-tls `danger_*`, rustls `.dangerous()`) | T526 (Pinning cheat sheet), T031, T466 | OpenSSL 3.6.4 man pages (a missing certificate also returns `X509_V_OK`); reqwest 0.13.5, native-tls 0.2.18, rustls 0.23.45 sources |
| supply-chain provenance & publishing | `sota-php` rules/05 §1: canonical repositories, `secure-http`, forked packages published with pedigree | T552, T260 (SCVS 6.x) | Composer `doc/articles/repository-priorities.md` and `doc/06-config.md` |

**Batched as one PR, not four** — a choice inside the approved scope: each promotion needed
one or two cells, and the four share the floor edit. The remaining step-3 concepts touch
most or all nine languages and keep one PR each.

## 2026-09-25 — ROADMAP 66 step 3b: SSRF / outbound request validation, all nine languages, pinned

One agent per language skill, each told to check first whether the concept was already there.
**None was complete:** five languages (jvm, python, js/ts, php, ruby) had SSRF text, and all five
lacked the check at **connect time** on the dialled address (so DNS rebinding passes a check
done before the call) or the redirect policy; four (rust, go, c/c++, .NET) had nothing. Each
now names its own client's hook (Go `net.Dialer.ControlContext`, httpcore network backend,
undici/`http.Agent` `lookup` answering in the `all: true` array form, `SocketsHttpHandler.
ConnectCallback`, libcurl `CURLOPT_OPENSOCKETFUNCTION`, reqwest `dns_resolver`, OkHttp/Apache
socket hooks, `Net::HTTP#ipaddr=`), its redirect setting and its strict IP parser. The generic
policy stays in `sota-code-security` rules/01 §5.

**Verified independently of the agents' reports:** every probe re-run as written in the file
against its fixtures (9/9 match; Rust's report joined two commands with a literal "AND" that
is not in the file, and the file's two commands give 3/0); spot-checks run here — Go
`ControlContext` in `api/go1.20.txt`, Python `ipaddress` rejecting `0177.0.0.1`/`0x7f.0.0.1`/
`2130706433` while `inet_aton` accepts all three, Ruby `Net::HTTP#ipaddr=`, Node `net.BlockList`.
Two notable finds by the agents: an IP-literal URL never reaches Node's `lookup` hook (so it
needs a separate pre-dispatch check), and Go's `IsUnspecified` covers only `0.0.0.0`, not
`0.0.0.0/8`.

**A citation defect of mine, fixed before commit.** My brief passed "SSRF Prevention cheat
sheet items 6, 8-10 …" — those numbers are **our extraction ordinals**, not anything OWASP
publishes, and eight of nine agents wrote them into the skills. All nine now cite the cheat
sheets by name, and the workflow brief says to cite sources by name only.

## 2026-09-25 — ROADMAP 66 step 3b: regex escaping, anchoring & engine choice, all nine languages, pinned

Source theme: validation-regex hygiene (OWASP Input Validation cheat sheet, Proactive Controls
2024 C3, ASVS 5.0 V1.2.9, Go-SCP). Four added (go, rust, c/c++, php), five extended an existing
ReDoS rule without duplicating it. Each language now names its escape function, its full-match
API and **its own anchor trap** (Python `re.match` anchors only at the start and `$` matches
before a trailing newline; Go's `^a|b$` lets alternation escape the anchors; Java `find` vs
`matches`), bounds, and whether its engine is linear-time — with the mitigation where it is not
(`regex` module timeout, `RegexOptions.NonBacktracking`/match timeouts, regexp2 `MatchTimeout`,
a terminable `worker_threads` Worker).

**Verified here, not only in the agents' reports:** all nine probes re-run as written (9/9
match); the one behaviour an agent wrote without running — a Node worker `terminate()`d on a
deadline stopping a catastrophic regex — was run: terminated at 303 ms.

**An existing error corrected on the way:** `sota-python` rules/05 §8 said "Rust-backed RE2
bindings" since the library's first commit. RE2 is C++; `google-re2` (installed and run by the
agent) binds it. Now says so.

## 2026-09-25 — ROADMAP 66 step 3b: install/build-time code execution, all nine languages, pinned

Source theme: code-owner review of build-executing files (OWASP CI/CD Security, Software
Supply Chain Security and NPM Security cheat sheets), generalised to every ecosystem's own
execution points. Five added (go, c/c++, jvm, .NET, ruby), four extended partial text (python's
one-line `setup.py` bullet, rust, js/ts, php's plugin/script rule). Each names where a
dependency's code runs (sdist builds and `.pth` files; `go:generate`/`go run pkg@v`, cgo flag
allowlists, `-toolexec`, `GOTOOLCHAIN`; `build.rs` and proc-macros; CMake `FetchContent`/
`ExternalProject`; Gradle/Maven plugins and init scripts; MSBuild `.props`/`.targets` from
packages; npm lifecycle scripts; Composer plugins; gem native extensions), the switch that
turns it off, code-owner review of the repo's own build files including agent-authored changes,
and a CI job without secrets for those steps.

Several claims were measured, not recalled: the Python agent built a malicious sdist under uv
0.12 and pip 26.1 and watched `setup.py` run with the installer's environment; `--only-binary
:all:` still builds a **local-directory** requirement; `[tool.uv] no-build` refuses it. Go's
position that fetching and building a module never executes it is from go.dev's own supply-chain
post and `go help` on 1.27.1. All nine probes re-run here against their fixtures (9/9; Rust's
`cargo metadata` query lists the three build-executing packages in the bad fixture and none in
the good; .NET's second command prints positive evidence, not findings, on the good fixture).

**Cap watch:** `sota-golang` rules/05 is now **499/500** — step 4's Go themes need a split first.

## 2026-09-25 — ROADMAP 66 step 3b: dependency adoption (selection & insecure defaults), all nine, pinned

Source themes: the pre-adoption checklist, suspicion signals for new (including AI-suggested)
packages, and auditing security-sensitive options passed to libraries (OWASP Vulnerable
Dependency Management, Software Supply Chain Security and Secure Coding with AI cheat sheets;
SCVS V1/V6). Two added (jvm, php), seven extended existing supply-chain text. Each names its
registry's identity checks (a name that 404s, first-upload date, owners), deps.dev and the
Scorecard API, and **insecure defaults measured in the library's current source** — e.g.
`requests` has no timeout by default while `httpx` defaults to 5 s; `flask_cors.CORS(app)`
reflects any Origin (run); Jinja2's `Environment` does not autoescape; rs/cors `Default()`
allows every origin; gin trusts every proxy by default; golang-jwt checks the algorithm only
with `WithValidMethods`; SnakeYAML 1.x `new Yaml()`. The Python agent also checked lxml and
deliberately did **not** name it: its default refused an external entity, so it is not an
insecure default — a claim withheld because the measurement did not support it.

Probes re-run here: seven reproduce on the fixtures; jvm and .NET each fall short by exactly
the hits of their `git diff` half, which needs a git base the fixture is not; php's fixtures
live in `probe/` with a `vendor/` decoy and reproduce 7/0.

**Cap consequence, recorded for step 4:** the language security files are now full —
`sota-golang` rules/05 **500**, `sota-rust` rules/05 **499**, `sota-javascript-typescript`
rules/05 **492**, `sota-python` rules/05 **489**. Step 4 cannot add a line to them without a split.

## 2026-09-25 — ROADMAP 66 step 3b: arithmetic edge cases folded into "numeric precision & money"

Operator-approved fold, not a new concept (the floor stays at 33; the concept's matcher widens
to see the new text). Source theme: arithmetic edge cases (OWASP Go-SCP general coding
practices; SCSVS arithmetic). All nine extended, next to their existing numeric text, and none
into a full security file — the brief forbade files at ≥485 lines, so Python and Go placed it in
their idioms/design files. Each covers: a float parser that accepts `nan`/`inf` from input
(Python `float()`, Go `strconv.ParseFloat`, Python `json.loads`, Go's `,string` JSON tag) and the
range check `x < min || x > max` that **passes** a NaN; integer divide-by-zero behaviour and its
guard; `MIN / -1`, negating `MIN`, intermediate overflow and duration conversions (Go's
`time.Duration(1e10) * time.Second` is negative — run on 1.27.1); and each language's checked or
saturating APIs, with unchecked regions (C# `unchecked`, Rust wrapping ops) needing a proven bound.

Probes re-run here: all nine reproduce; .NET's bad fixture adds one advisory line by design and
its good fixture lists a csproj *because* it enables overflow checking — positive evidence, not
a finding. **Step 3b is complete**: four new universal concepts pinned (floor 29 → 33) and the fold.

## 2026-09-25 — four language security files split (ROADMAP 66, before step 3c)

Step 3b filled them: `sota-golang` rules/05 at 500, `sota-rust` rules/05 at 499,
`sota-javascript-typescript` rules/05 at 492, `sota-python` rules/05 at 489. Step 3c and step 4
both need room there, so each lost one coherent topic to a new `rules/08` — Go's supply chain
(§8 → §1), Rust's `std::process::Command` (§9 → §1), JS/TS's child processes and SSRF (section
names kept), Python's supply chain and static-analysis gates (§9–§10 → §1–§2). Sizes after:
444, 395, 399, 396. No rule text changed: every removed line reappears in its new file except
renumbered headings and the `§` numbers inside moved checklist bullets (a scripted check).

Invariant 18 flagged nine references; the rest were found by an explicit sweep — including
`sota-sandboxing` rules/04 pointing at JS/TS rules/05 for `child_process` (no `§`, so no gate
sees it) and the four `rules/05` index rows still advertising the moved topics, which would
have sent the model to the wrong file. Moving onto `main` after #452 conflicted only on the
generated skill map, resolved by regenerating it.

## 2026-09-25 — ROADMAP 66 step 3c: four concepts briefed as conditional; three proved universal

One agent per language handled all four (so no two agents touched one file), and each first
decided whether its ecosystem has the mechanism. The briefing assumed eval, cookies and debug
modes would not apply to C/C++ or Rust; **the agents found them, measured, in all nine**:
Lua's `load` accepting binary chunks unless mode `"t"` (checked across Lua 5.4.9, 5.5.0, 5.5.1),
mlua's `Lua::new()` exposing `os.execute`/`io.open` (run), Drogon's cookie defaults
(`secure_{false}`, no SameSite, from its source), an empty `CMAKE_BUILD_TYPE` shipping without
`-O`/`-DNDEBUG` (measured), the `cookie` crate serialising a bare cookie (run). Under the
operator's rule — universal goes into the template — those three are pinned (floor 33 → 36).
**Request-scoped context cleanup stays conditional:** present in eight; Go is a principled
absence (goroutines have no local storage by design), recorded in `LANGUAGE-TIER.md` so no
one "fixes" it.

Also measured along the way: Python `ThreadPoolExecutor(max_workers=1)` carries both a
`threading.local` and a `ContextVar` into the next job unless the token is reset in `finally`;
Werkzeug, Django and Starlette `set_cookie` default to no Secure/HttpOnly (Starlette adds
`SameSite=lax`); Werkzeug emits a `__Host-` cookie without `Secure`, so the prefix is not
enforced server-side. All probes re-run against their fixtures here: no mismatch.

**Cap watch:** `sota-jvm` rules/04 reached 484.
