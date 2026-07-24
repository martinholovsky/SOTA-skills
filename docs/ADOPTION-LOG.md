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
  version + PR rather than a bare hash.
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
