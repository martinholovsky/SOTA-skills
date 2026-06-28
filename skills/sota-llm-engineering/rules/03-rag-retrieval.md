# Rules 03 — RAG & Retrieval Architecture

RAG is a search problem wearing an LLM costume. Most "the model hallucinates"
complaints about RAG systems are retrieval failures: the right passage never
reached the context. Engineer and evaluate retrieval as its own system, then
make generation provably grounded in what was retrieved.

## 1. When RAG vs long context vs fine-tuning

Decide with this table, not by fashion. (1M-token context windows are
standard on frontier models as of mid-2026, which moved the boundary — small
stable corpora often no longer need a vector pipeline.)

| Situation | Choice |
|---|---|
| Corpus fits comfortably in context (≲ a few hundred K tokens), is stable across requests | **Long context + prompt caching.** Whole corpus in the cached prefix (rules/02 §5); reads at ~0.1× price. Simpler, no retrieval-miss class of bugs. Eval still required. |
| Corpus is large, changing, per-tenant, or ACL-filtered | **RAG.** Retrieval is the only way to scale, stay fresh, and enforce per-user access. |
| Need is *behavior/format/style*, not knowledge | **Prompting, then fine-tuning** (rules/06 §1). Fine-tuning is for form, not facts — it does not reliably inject or update knowledge. |
| Need citations / auditability of sources | **RAG** (or long context with inline source markers). Weights can't cite. |
| Latency-critical + small hot corpus | Long context + caching beats a retrieval round-trip. |

These compose: RAG over a moving corpus on a fine-tuned-for-format model with
a cached static preamble is a normal architecture. Also escalate honestly in
the other direction: if users' questions span documents ("summarize all
complaints this quarter"), top-k snippet retrieval is structurally wrong —
you need aggregation pipelines or agentic retrieval (§8), not a bigger k.

## 2. Chunking strategies

Chunking decides what *can* be retrieved; no reranker resurrects information
split across a chunk boundary.

- **Structure-first:** split on document structure (headings, sections,
  paragraphs; functions/classes for code; rows-with-header for tables) —
  never blind fixed-char windows across semantic boundaries. Markdown/HTML/
  AST-aware splitters are the default; fixed-size is the fallback for
  unstructured blobs.
- **Size tradeoff:** small chunks (~100–300 tokens) → precise embeddings,
  starved generation context; large chunks (~1–2K) → richer context, blurrier
  embeddings, fewer distinct results per budget. Common SOTA pattern:
  **retrieve small, expand big** — embed/match fine-grained units, hand the
  generator the parent section ("small-to-big" / parent-document retrieval).
- **Overlap** (~10–20%) mitigates boundary cuts for fixed-size chunking;
  structural chunking needs little.
- **Contextualize chunks at index time:** prepend document title / section
  path / date ("ACME 2026 10-K › Risk Factors › …") to the embedded text, or
  LLM-generate a 1–2 sentence situating blurb per chunk (contextual
  retrieval). Bare paragraphs lose their referents ("the company", "this
  method").
- **Semantic chunking** (split on embedding-similarity valleys) helps on
  unstructured prose; it's an optimization, not a default — measure it
  against structural chunking on your retrieval eval (§6) before paying its
  indexing cost.
- Store rich metadata per chunk: source ID/URI, section path, timestamps,
  ACL tags, embedding model+version (§3), chunker version. You will need
  every one of these for filtering, citation, invalidation, and migration.

## 3. Embedding model selection and versioning

- **Select on your own retrieval eval (§6), not leaderboard rank.** Public
  MTEB-style scores don't transfer reliably to your domain/language; shortlist
  2–3 current candidates (provider-hosted and open-weight), run recall@k on
  your golden retrieval set, weigh cost/latency/dimension/hosting.
- **Pin the exact model + version everywhere.** Query-time and index-time
  embeddings must come from the identical model; mixing vector spaces returns
  geometric noise that *looks* like results — no error is raised. Stamp
  `embedding_model` + `embedding_version` on every stored vector and assert
  at query time that the query encoder matches (Critical if mixed).
- **Migration is reindex + cutover, never in-place:** new index (or named
  vector set) → re-embed corpus → run the retrieval eval against both → flip
  reads atomically → retire the old index. Dual-write during the window.
  (rules/06 §4.)
- Use task-specific encoding modes where the model has them (query vs
  document/passage prefixes); skipping the prefix silently degrades recall.
- Match the index's distance metric to the model's training metric (usually
  cosine on normalized vectors); quantization (int8/binary) is fine when the
  retrieval eval confirms acceptable recall loss — measure, don't assume.

## 4. Hybrid retrieval: dense + lexical + rerank

Dense-only retrieval is no longer SOTA. The default production stack:

1. **Dense** (vector kNN) — semantic paraphrase matching;
2. **Lexical** (BM25/full-text) — exact terms, IDs, SKUs, error codes, names,
   rare jargon that embeddings smear;
3. **Fusion** — combine ranked lists (RRF is the robust default; tuned
   weighted fusion if the eval justifies it);
4. **Rerank** — cross-encoder/rerank model scores the fused top ~50–100
   query↔passage pairs; keep top 3–10 for the prompt;
5. **Metadata filtering** — tenant/ACL/date/type filters applied *in the
   retrieval engine* (pre- or during-search), never client-side after
   over-fetching. ACL filtering after retrieval is a security bug
   (sota-code-security rules/08 — RAG ACLs).

Each stage exists to fix the previous stage's failure mode; each costs
latency. Add stages bottom-up only when the retrieval eval shows the failure
they fix. A reranker on top of broken chunking is lipstick.

## 5. Query transformation

User queries are not good search queries. In rough order of payoff:

- **Rewriting/condensation (conversational RAG — mandatory):** resolve
  pronouns and ellipsis from chat history into a standalone query ("what
  about the Pro tier?" → "What is the refund policy for the Pro tier?").
  Skipping this is the #1 cause of bad multi-turn RAG.
- **Decomposition:** split multi-part/comparative questions into sub-queries;
  retrieve per sub-query; fuse.
- **Expansion:** generate term/synonym variants for the lexical leg;
  multi-query (N paraphrases → union → rerank) buys recall for N× retrieval
  cost.
- **HyDE — use with caution:** embedding a hypothetical generated answer can
  help on knowledge-sparse queries, but it injects the generator's
  hallucinations into retrieval, adds a full LLM call of latency, and on
  domain corpora often *underperforms* plain hybrid + rerank. Adopt only if
  it beats your stack on the retrieval eval; never as the default.

Every transformation is an LLM call: cheap/fast model tier, traced, and
evaluated — a bad rewriter silently caps the whole pipeline.

## 6. Retrieval evaluation

Evaluate retrieval separately from generation; end-to-end-only evals can't
tell you which stage failed (rules/01 §6).

- **Golden retrieval set:** ≥50 real queries mapped to the chunk/document IDs
  that *should* be retrieved. Build from production queries, support
  escalations, and SME annotation; include queries whose correct answer is
  "nothing in corpus".
- **Metrics:** recall@k at your actual prompt k (the metric that bounds
  everything downstream), MRR/nDCG for ranking quality, precision@k for
  context-pollution pressure. Track per stage: recall@50 after fusion vs
  recall@5 after rerank localizes the broken stage.
- **Generation-side metrics on top:** faithfulness/groundedness (every claim
  supported by retrieved context — LLM-judge with quoted evidence, rules/01
  §2) and answer relevance. RAG-specific harnesses (e.g. RAGAS-style) or
  your general eval harness both work; the metrics matter, not the brand.
- Re-run the retrieval eval on every change to chunking, embedding model,
  fusion weights, reranker, or k — these are config changes with silent
  global blast radius; gate them in CI like prompt changes.

## 7. Grounding, citation, and freshness

- **Grounded or refused.** Instruct + verify: answer only from provided
  context; if the context doesn't contain the answer, say so. "Not in the
  corpus" is a first-class outcome with its own eval cases — a RAG system
  that never refuses is hallucinating on the gaps.
- **Citations are structural:** assign stable IDs to context blocks, require
  the model to attach source IDs per claim (structured output, rules/02 §6),
  and **resolve them in code** — every cited ID must exist in the supplied
  context (reject/repair if not). Render as links to the actual source. Use
  provider-native citation features where available.
- **Freshness pipeline:** index updates are event-driven from the source of
  truth (webhook/CDC → re-chunk → re-embed → upsert) with a periodic
  reconciliation sweep; deletes propagate as hard index deletes (a deleted/
  ACL-revoked document still retrievable is a Critical data-exposure bug).
  Track and alert on index lag (source `updated_at` vs index `indexed_at`);
  surface document dates to the model so it can prefer current sources and
  caveat stale ones.
- **Corpus integrity (OWASP RAG Security):** the vector store is attacker-
  reachable if anyone can write to it. Restrict writes to the ingestion
  identity, store a content hash (SHA-256) per chunk and verify it before
  serving (exclude + alert on mismatch — poisoning/tamper detection), and
  **don't return raw similarity/distance scores to end users or sub-agents** —
  they let an attacker probe and reconstruct corpus contents. Rate-limit
  retrieval per identity. Vector-DB auth/network hardening is in
  sota-code-security rules/08 §4.

## 8. Agentic retrieval vs one-shot

One-shot (query → retrieve → generate) is the right default for FAQ-style
loads: cheapest, fastest, easiest to evaluate. Escalate to **agentic
retrieval** — model issues searches as tool calls, inspects results,
reformulates, iterates (rules/04) — when the eval shows one-shot failing on:
multi-hop questions, exploratory research, corpus-spanning aggregation, or
queries needing tool choice (search vs SQL vs API).

- Costs: multiple LLM round-trips of latency/spend, and an eval that must
  judge trajectories, not just answers. Apply rules/04 budgets and stopping
  conditions; an agent that loops reformulating a hopeless query burns money
  on a question it should refuse.
- Middle ground worth trying first: one-shot hybrid + a single
  verify-and-retry pass ("did the context answer the question? if not, one
  reformulated retrieval"), capped at one iteration.

## Audit checklist

- [ ] Architecture choice (RAG / long context + caching / fine-tune) is
      justified against §1 — no vector pipeline for a small stable corpus,
      no weights-as-knowledge-store.
- [ ] Chunking is structure-aware; tables/code not split mid-unit; chunks
      carry title/section context and full metadata (source, ACL, dates,
      model+chunker versions).
- [ ] Embedding model chosen via own-domain retrieval eval; exact
      model+version pinned and stamped per vector; query/document encoders
      provably identical; task prefixes used where required.
- [ ] Embedding migrations are reindex-and-cutover with eval-gated flips —
      never mixed vector spaces in one queried index.
- [ ] Hybrid retrieval in place (dense + lexical + fusion) or its absence
      justified by eval; reranker before the prompt where k-precision
      matters; stage-by-stage recall measured.
- [ ] Tenant/ACL/date filters enforced inside the retrieval engine, never
      post-hoc client-side.
- [ ] Conversational queries rewritten to standalone before retrieval;
      query-transform LLM calls traced and evaluated; HyDE/multi-query only
      with eval evidence.
- [ ] Golden retrieval set exists (≥50 queries, includes "nothing in
      corpus"); recall@k at prompt-k tracked; retrieval eval gates chunking/
      embedding/reranker/k changes in CI.
- [ ] Faithfulness judged with quoted evidence; refusal-on-missing-context
      behavior present and eval-covered.
- [ ] Citations structurally validated in code against supplied context IDs.
- [ ] Freshness: event-driven (or scheduled) reindex with reconciliation;
      deletes/ACL revocations propagate to the index; index lag monitored.
- [ ] Agentic retrieval only where one-shot demonstrably fails; bounded per
      rules/04.
