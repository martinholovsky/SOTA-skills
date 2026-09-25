# Rules 06 — Data & Lifecycle

The durable assets of an LLM application are not the prompts — they are the
eval sets, the curated data, the feedback loops, and the indexes. This file
covers the decisions and hygiene around them: when to fine-tune, how to
curate, how to close the feedback loop, how to migrate embeddings, and how to
keep user data out of places it must not live.

## 1. Fine-tuning vs prompting: the decision

**The verified mid-2026 consensus sequence: Prompt → RAG → Fine-tune →
Distill.** Most teams reaching for fine-tuning should fix prompts, build real
retrieval, and write evals first — in that order. Fine-tuning is the last
resort because it carries a permanent operational tax (data pipeline,
training runs, adapter versioning, re-validation on every base-model change)
that prompts and retrieval don't.

**Fine-tuning is for form, not facts.** It reliably shapes *behavior* —
style, tone, output structure, domain dialect, classification on fuzzy
boundaries, tool-use conventions — and unreliably injects *knowledge*, which
goes stale the day training ends and can't be access-controlled or cited.
Volatile knowledge → retrieval (rules/03 §1); stable behavior → first
prompting, then weights.

Fine-tune only when ALL hold:

1. A strong eval suite exists (rules/01) — otherwise you cannot even measure
   whether tuning helped; this is the hard prerequisite.
2. Frontier-model + tuned-prompt + few-shot has been tried against that eval
   and demonstrably plateaus below the requirement.
3. The gap is behavioral (format/style/latency at a smaller size), not
   missing knowledge.
4. You have (or can curate, §2) hundreds–thousands of high-quality examples.
5. Someone owns the lifecycle: retraining cadence, adapter rollback,
   re-validation when the base model shifts.

**The economically dominant 2026 case is distillation/right-sizing:** tune a
small, cheap model (typically a LoRA/QLoRA-style adapter on an open-weight
model, or a provider fine-tune where offered) on a frontier model's traced
outputs for one narrow, high-volume task — buying the big model's quality at
the small model's price and latency. Pair with retrieval; don't replace it.

Provider note (verify before committing — availability shifts): fine-tuning
offerings differ sharply by provider and platform (some expose
SFT/preference-tuning APIs, some only via cloud platforms, some not at all).
If your product strategy requires tuning, confirm the current offering for
your provider first; open-weight + self-hosted is the fallback.

**Beware silent base drift:** a hosted adapter sits on a base the provider
may update or deprecate; behavior can degrade without any change on your
side. Pin base versions where possible and schedule re-validation
(quarterly, and on every announced base change) against the eval suite.

## 2. Dataset curation hygiene

For eval sets, fine-tuning sets, and few-shot pools alike — quality beats
quantity at every scale that matters:

- **Provenance per example:** source (production/synthetic/incident/SME),
  timestamp, license/consent status, annotator. Unknown-provenance data is
  unusable for tuning (legal + quality) — discard or re-source.
- **Deduplicate** (exact + near-dup via embedding similarity) — dup-heavy
  sets overweight one pattern and leak between train/eval splits.
- **Split discipline:** train/dev/held-out split by *source entity* (user,
  document, ticket), not by row, or near-duplicates straddle the split and
  inflate scores. Eval contamination rules apply (rules/01 §8).
- **Label quality:** double-annotate a sample, measure inter-annotator
  agreement; where humans disagree, the rubric is broken — fix the rubric
  before "fixing" the labels. Adjudicate disagreements, don't average them.
- **Negative and refusal examples:** include "no answer", "refuse", and
  "escalate" cases — sets containing only happy-path completions teach
  overconfidence (same rule as eval sets, rules/01 §1).
- **PII scrubbing before storage** (§5): datasets outlive their context and
  get copied to laptops, CI, and vendors. Scrub at ingestion, not at use.
- **Version datasets like code:** content-hashed releases (DVC/LakeFS/object
  store + manifest), changelog per release, eval results pinned to dataset
  version. "Which data trained the model in prod?" must have an exact answer.

## 3. Feedback loops: signals into eval sets

Production feedback is the cheapest continuous source of truth — if wired.

- **Capture more than thumbs.** Explicit signals (👍/👎 + optional reason,
  ratings) are sparse and skew negative; implicit signals are denser and
  often more honest: user edited the draft (the diff is a correction label),
  regenerated, abandoned mid-stream, copied the output (success), escalated
  to a human, accepted/rejected a suggestion. Log all of these as
  structured events tied to the trace ID (rules/05 §5).
- **Route signals to destinations:**
  - 👎 + escalations + edit-diffs → review queue → labeled eval cases
    (rules/01 §7), tagged with failure taxonomy.
  - 👍/copied/accepted at volume → candidate pool for few-shot examples and
    fine-tuning data (§2 hygiene applies; positive signal ≠ correct — still
    sample-review).
  - Aggregates → online quality dashboards per route/prompt-version
    (rules/05 §5).
- **Close the loop measurably:** every incident/complaint becomes a
  permanent eval case; track "time from bad production output → case in the
  gating suite". If feedback lands in a dashboard nobody mines, you have
  telemetry, not a loop (Medium finding).
- Feedback data is user data: consent/notice for using it to improve the
  product, PII scrubbing before it enters eval/training sets (§5).

## 4. Embedding & index migration

Embedding models deprecate, improve, and change dimensions; you WILL migrate.
Design for it on day one (rules/03 §3 owns selection; this is the lifecycle):

- **Stamp every vector** with `embedding_model`, `embedding_version`,
  `chunker_version`, `indexed_at`. Without stamps, migration means "re-embed
  everything and pray".
- **Blue/green reindex:** build the new index (or a named parallel vector
  set on the same collection — native support exists in mainstream vector
  DBs) → backfill-embed the corpus → dual-write new content to both during
  the window → run the golden retrieval eval (rules/03 §6) against both →
  flip reads via config → keep the old index until the error budget clears,
  then delete.
- **Never query mixed vector spaces.** Two models' vectors in one searched
  set return confident nonsense with no error raised (Critical).
- **Quantify before you flip:** recall@k delta on the golden set, latency,
  storage/cost delta. A "better" embedding model that loses 5 points of
  recall on *your* corpus is worse.
- Chunker changes are migrations too — re-chunking shifts IDs and
  boundaries; plan citation/ID stability (stable source-doc IDs + offsets,
  not chunk-row IDs, in anything user-facing).
- Budget for re-embedding cost/time at corpus scale (batch APIs, rules/05
  §4) and rate limits — a 100M-chunk reindex is a project, not a script.

## 5. PII in prompts, logs, and provider settings

Prompts and completions are user data flowing to a third party and into your
logs. Deep regulatory treatment: **sota-privacy-compliance**; security of the
stores: sota-code-security rules/07. The LLM-engineering obligations:

- **Minimize at the boundary:** send the model only the fields the task
  needs — schema-projected records, not whole user objects; pseudonymize
  stable identifiers (user_123 → token) where the task allows, re-hydrate
  after.
- **Outbound AI traffic crosses a DLP boundary.** Calls to external model
  services go through one egress gateway (the rules/05 §1 gateway, or a
  network-level one) that inspects prompts and attachments for secrets and
  personal data, blocks or redacts what it finds, and keeps an audit trail
  of who sent what to which provider. Developer coding assistants are the
  same data flow with a wider aperture — they upload whatever files they
  read: record what they send (the tool's request logging, or an outbound
  proxy you control) and scope what they can read (sota-sandboxing rules/05
  §4). Code or data under a regulatory or classification regime goes only to
  self-hosted or air-gapped models, behind an explicit approval to use AI on
  it at all. OWASP: OWASP DSOMM; OWASP Secure Coding with AI cheat sheet.
- **Redact before persistence:** prompt/completion logging (rules/05 §5),
  eval-set promotion (rules/01 §7), and dataset curation (§2) all pass
  through a redaction layer (NER/pattern-based PII detection + allowlists).
  Raw-prompt logging with PII into a general log platform with broad access
  is a High finding; wholesale, unredacted, unbounded-retention → Critical.
  **The embedding path is persistence too:** detect sensitive fields before
  text is chunked and embedded, and mask, tokenise or drop them — a vector
  store is a durable copy that approximately preserves its input
  (sota-code-security rules/08 §4), and a chunk's payload text is stored
  verbatim. An embedding model fine-tuned on one tenant's data is that
  tenant's data: serve it to that tenant only. OWASP: AISVS 8.2.1; OWASP RAG
  Security cheat sheet.
- **Retention & access:** LLM traces get their own retention clock (shortest
  that supports debugging/evals) and access control distinct from app logs;
  deletion requests must reach traces, eval sets, memory stores (rules/04
  §5), and vector indexes — RAG chunks of a deleted user document are still
  that user's data (rules/03 §7 deletes propagate).
- **Provider data-retention settings are configuration you must set, not
  defaults you inherit.** Verify per provider and per platform: API data
  used (or not) for training, retention window options (standard vs
  zero-data-retention agreements), regional processing. Note ZDR interacts
  with features — some models/features require minimum retention (verified:
  at least one frontier model requires 30-day retention and is unavailable
  under ZDR, June 2026) and some platforms differ from first-party APIs.
  Record the chosen settings in the repo (compliance docs) so they're
  auditable; re-verify on provider/platform change.
- Memory stores and semantic caches hold user data too: scope per user/
  tenant, make them erasable, and exclude them from cross-tenant retrieval.

## Audit checklist

- [ ] Any fine-tuning proposal/document shows: eval suite first, prompt+RAG
      plateau evidence, behavioral (not knowledge) gap, data volume, named
      lifecycle owner. Tuning used for facts/knowledge injection → finding.
- [ ] Tuned models: base version pinned where possible; scheduled
      re-validation against evals; adapter rollback path; provider offering
      verified current, not assumed.
- [ ] Datasets: provenance + license per example; deduped; entity-level
      splits; inter-annotator agreement measured; refusal/negative cases
      present; versioned releases with pinned eval results.
- [ ] Feedback: implicit signals (edits, regenerations, copies, escalations)
      captured and trace-linked, not just thumbs; 👎/escalation → eval-case
      pipeline exists and is exercised; positive pool sample-reviewed before
      reuse as examples/training data.
- [ ] Vectors stamped with model/version/chunker; migrations are blue/green
      with dual-write and retrieval-eval gates; no mixed vector spaces
      queryable; re-embedding cost planned via batch.
- [ ] PII minimized at the model boundary (projection, pseudonymization);
      redaction layer in front of trace logging, eval promotion, and dataset
      storage; traces have distinct retention + access control.
- [ ] Sensitive fields masked, tokenised or dropped before embedding and
      indexing; tenant-trained embedding models never shared across tenants
      (§5). **High**. Probe — embedding calls with no redaction step on the
      line: `grep -rnE 'embed(_documents|_query|dings\.create)?\(' . | grep -vE 'redact|mask|scrub'`
- [ ] Calls to external AI services leave through one scanning egress
      gateway with an audit trail; coding-assistant uploads logged or
      proxied; regulated code only on self-hosted/air-gapped models with an
      approval gate (§5). **High**. Probe — provider hosts hard-coded outside
      the gateway module: `grep -rnE 'api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com' .`
- [ ] Deletion requests propagate to traces, eval sets, memory, semantic
      caches, and vector indexes.
- [ ] Provider data-retention/training-use settings explicitly configured,
      documented in-repo, and re-verified on provider/platform/model change
      (including ZDR-vs-feature constraints).
