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
| 2026-07-24 | [swarm-forge](https://github.com/unclebob/swarm-forge) `engineering.prompt` | Separate the testable core from the environment-bound shell; only the core participates in coverage/mutation/complexity tooling | **adopted** | `sota-architecture/rules/02` §14 · unreleased |
| 2026-07-24 | swarm-forge `hardender.prompt` | Differential mutation against a persisted manifest — gate on new survivors, not an absolute score | **adopted** | `sota-testing/rules/06` §6.3 · unreleased |
| 2026-07-24 | swarm-forge `crap4go`/`crap4clj` tools | Complexity × coverage composite to rank where the next test belongs | **adopted** | `sota-testing/rules/07` §7.2 · unreleased |
| 2026-07-24 | swarm-forge (convergent) | Scoped/diff mutation; mutation as a control probe; read survivors don't average; reviewer must not modify audited code; heartbeat on long runs; verify the other role ran the tool | **rejected: already ours** | — |
| 2026-07-24 | swarm-forge `engineering.prompt` Startup Tools | Resolve every tool at latest upstream each run; never reuse cached/vendored copies | **rejected: contrary** | — |

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
