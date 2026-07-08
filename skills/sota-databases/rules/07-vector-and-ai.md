# 07 — Vector Search & AI-Era Data

## Engine choice

### Rule: pgvector in your existing Postgres until a measured limit says otherwise.
The Postgres-as-default heuristic (file 01) applies doubly here, because
vector data is almost never standalone — it joins to documents, tenants,
permissions, and metadata you already store. pgvector gives you: transactional
consistency between source rows and embeddings (no sync pipeline), SQL
metadata filtering, RLS-based tenant isolation (file 01/06), one backup story.

Move to a dedicated vector DB (Qdrant, Milvus, Weaviate, Turbopuffer, managed
equivalents) only on concrete triggers:
- **Scale:** beyond ~10–50M vectors per node-class instance, HNSW memory
  (index must fit RAM for good latency) and index build times start to hurt;
  dedicated engines bring quantization tiers, disk-based indexes (DiskANN-
  style), and horizontal sharding as first-class features.
- **Recall/latency SLOs under heavy filtering:** measured pgvector recall@k
  insufficient despite tuning (see filtering below).
- **Operational isolation:** vector index builds/queries are CPU+RAM-heavy;
  if they degrade your OLTP primary and a replica doesn't solve it, isolate.
- Many-tenant vector workloads with per-tenant index isolation requirements.

Document the trigger you hit. "We might need scale later" is not a trigger.
A dedicated vector DB adds: a sync pipeline (and its lag/failure modes),
duplicate authz logic, a second backup/monitoring/security surface.

### Rule: pgvector operational basics — get these right or it "doesn't work".
```sql
CREATE EXTENSION vector;
ALTER TABLE chunks ADD COLUMN embedding vector(1536);  -- dimension fixed per column
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
-- query (operator must match opclass: <=> cosine, <-> L2, <#> inner product):
SELECT id FROM chunks ORDER BY embedding <=> $1 LIMIT 10;
```
- **HNSW** default (better recall/latency, more RAM, slower build); IVFFlat
  only for cheap builds on mostly-static data — and it needs training data
  present before CREATE INDEX, plus periodic re-cluster as data drifts.
- ANN indexes return **approximate** results: tune `hnsw.ef_search` (query-
  time) against a measured recall@k baseline (exact scan on a sample =
  ground truth). Shipping ANN without a recall measurement is shipping an
  unknown correctness budget.
- `ORDER BY embedding <=> $1 LIMIT k` is the index-eligible shape — wrapping
  the distance in a function or adding it to WHERE can silently fall back to
  a seq scan (or error-prone exactness); EXPLAIN it like any query (file 03).
- **Filtered search** is the classic trap: `WHERE tenant_id = $1 ORDER BY
  embedding <=> $2 LIMIT 10` post-filters HNSW candidates — selective filters
  can return < k rows or crater recall. Options: pgvector 0.8+ iterative
  scans (`SET hnsw.iterative_scan = relaxed_order`), partial indexes per
  high-traffic filter value, or partition by tenant. Measure recall under the
  real filters, not unfiltered.
- Embeddings are big (1536 floats ≈ 6KB → TOAST): use `halfvec` (fp16, halves
  storage/RAM, negligible recall loss for most models) and consider
  `SET hnsw.ef_search` per route rather than globally. Vacuum matters —
  dead embedding tuples bloat fast under re-embedding churn (file 05).
- **Patch floor:** run pgvector ≥ 0.8.2 — CVE-2026-3172 (buffer overflow in
  parallel HNSW index builds; memory disclosure from other relations, or a
  server crash) — and prefer ≥ 0.8.4 for the June 2026 HNSW
  vacuum-corruption and distance-calculation fixes. Parallel builds
  (`max_parallel_maintenance_workers`) on an older version hit the CVE path.

### Rule: Quantize before you shard: halfvec → binary-quantized + rescore.
The capacity ladder inside pgvector, each step ~2–10× headroom:
1. `vector` → `halfvec` (fp16): half the storage and index RAM, recall loss
   usually <1%.
2. Binary quantization with rescore: index `bit`-quantized vectors (32×
   smaller), over-fetch candidates, rescore with full-precision distance:
```sql
CREATE INDEX ON chunks USING hnsw ((binary_quantize(embedding)::bit(1536)) bit_hamming_ops);
SELECT id FROM (
  SELECT id, embedding FROM chunks
  ORDER BY binary_quantize(embedding)::bit(1536) <~> binary_quantize($1)
  LIMIT 100                                   -- over-fetch ~5-10× k
) c ORDER BY c.embedding <=> $1 LIMIT 10;     -- exact rescore
```
Binary quantization works well on high-dimensional modern embeddings
(≥1024d); validate recall@k on your golden set before and after, like any
retrieval change.

### Rule: If you do adopt a dedicated vector DB, hold it to database standards.
The vector DB is now a datastore in scope for every other file of this skill:
- Sync: outbox/CDC-driven upserts and deletes (below), reconciliation sweep,
  alerting on sync lag — not best-effort dual writes from request handlers.
- Tenancy: per-tenant filtering enforced server-side (payload filter +
  enforced tenant key, or per-tenant collections); test cross-tenant leakage
  like RLS (file 01).
- Ops: snapshots/backups actually restored in rehearsal; capacity and memory
  monitoring; version upgrade path. Auth enabled — vector DBs ship with auth
  off more often than you'd think; an unauthenticated vector DB with document
  payloads is a data breach, not a search index (CRITICAL).
- Keep the authoritative copy of documents/metadata in Postgres; the vector
  DB stores vectors + the minimal payload needed for filtering. Rebuilding
  the collection from Postgres must always be possible (it's your recovery
  path and your migration path).

## Vector store exposure hardening

### Rule: A dedicated vector DB is locked down like the database it is — auth, network, TLS, tenancy, quotas.
Self-hosted vector DBs ship insecure: Qdrant's own docs state self-deployed
instances "are not secure by default" — no auth, listening on all interfaces.
Researchers keep finding the result in the wild (Legit Security, 2024: ~30
unauthenticated vector DBs leaking PII and private conversations; Orca, 2026:
exposed instances with credentials, medical and biometric data). Treat an
unauthenticated reachable vector DB as an active breach, not a hardening gap.
- **Auth on, always.** Qdrant: set `service.api_key`
  (`QDRANT__SERVICE__API_KEY`); use `read_only_api_key` (v1.7+) for
  query-only consumers; granular per-collection RBAC via JWT
  (`service.jwt_rbac: true`, v1.9+, HS256 signed with the api_key — rotate
  via `alt_api_key`, v1.17+, and note JWTs die with the key they were signed
  by). The admin key is a root credential: secret manager, never in client
  code.
- **Network:** internal-only binding, private subnets/security groups, TLS on
  (an api-key over cleartext is a leaked api-key — Qdrant's docs say exactly
  this). In distributed mode the internal gRPC port (6335) has **no** auth at
  all — it must never be reachable beyond cluster peers.
- **Payload hygiene:** payloads are documents — they carry PII, and people
  paste secrets into them. Classify payload fields in the PII inventory
  (file 06), run them through the same DLP/log-scrubbing rules as any store,
  and never put credentials/API keys in payloads; store the minimal filter
  fields plus an ID back to Postgres.
- **Tenant isolation is server-enforced.** A tenant filter added client-side
  is BOLA for vectors — any caller who omits it reads every tenant. Enforce
  with collection-per-tenant, or a mandatory tenant key the server applies
  (Qdrant: JWT RBAC per-collection `access` claims / payload-bound tokens).
  Cross-tenant leak test it like RLS (file 01).
- **Bound client-supplied search params.** `limit`, `hnsw_ef`/exploration
  factors, `with_payload`/`with_vectors` passed through from user input are a
  resource-exhaustion DoS (and `with_vectors` is exfiltration of your
  embedding space). Cap them server-side in your API layer; never proxy raw
  search bodies to the vector DB.

## Hybrid search

### Rule: Hybrid (lexical + vector) beats either alone; fuse with RRF.
Pure vector search misses exact identifiers, names, codes, and rare terms;
pure lexical misses paraphrase. Default architecture for retrieval quality:

```sql
WITH lexical AS (
  SELECT id, row_number() OVER (ORDER BY ts_rank_cd(tsv, q) DESC) AS r
  FROM chunks, plainto_tsquery('english', $1) q
  WHERE tsv @@ q LIMIT 50
), semantic AS (
  SELECT id, row_number() OVER (ORDER BY embedding <=> $2) AS r
  FROM chunks ORDER BY embedding <=> $2 LIMIT 50
)
SELECT id, sum(1.0 / (60 + r)) AS rrf_score      -- Reciprocal Rank Fusion, k=60
FROM (SELECT * FROM lexical UNION ALL SELECT * FROM semantic) t
GROUP BY id ORDER BY rrf_score DESC LIMIT 10;
```
- RRF over score blending: lexical and cosine scores live on incomparable
  scales; rank fusion needs no normalization or tuning.
- Maintain `tsv tsvector GENERATED ALWAYS AS (to_tsvector(...)) STORED` + GIN
  index; or BM25-class extensions (e.g. pg_search/ParadeDB) when ts_rank
  quality is insufficient.
- Retrieve generously (50–100 per arm), fuse, then optionally **rerank** the
  top ~50 with a cross-encoder for quality-critical paths — reranking is an
  app-tier concern but the DB must return enough candidates to make it work.
- Evaluate with a golden set (queries → known-relevant docs; recall@k, MRR)
  before and after every retrieval change. Retrieval changes without an eval
  harness are vibes.

## Embedding versioning & lifecycle

### Rule: An embedding is derived data, versioned by (model, dimensions, chunking, preprocessing).
Embeddings from different models — or the same model after a provider
"upgrade" — are **not comparable**. Mixing them in one searchable space is
silent corruption of results.
```sql
CREATE TABLE chunk_embeddings (
  chunk_id    bigint NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
  model       text   NOT NULL,            -- 'text-embedding-4-large@2026-01'
  embedding   halfvec(1536) NOT NULL,
  source_hash text   NOT NULL,            -- hash of embedded text → staleness detection
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (chunk_id, model)
);
CREATE INDEX ON chunk_embeddings USING hnsw (embedding halfvec_cosine_ops)
  WHERE model = 'text-embedding-4-large@2026-01';  -- partial index per active model
```
- Tag every vector with its model identifier **including version**; pin model
  versions in config — never "latest".
- Query embeddings must come from the same model as stored ones; assert this
  in code (config couples the query-encoder and the index/partial-index it
  searches).
- `source_hash` lets a reconciliation job find chunks whose text changed
  after embedding (staleness) and rows missing embeddings — embeddings
  generated asynchronously WILL drift without this.

### Rule: Model migration is dual-write/dual-index, then cutover — never in-place.
1. Backfill new-model embeddings alongside old (batched, rate-limited — this
   is an expensive external-API backfill; file 02 rules apply).
2. Build the new (partial) index; evaluate on the golden set vs old.
3. Cut queries over (config flag, instant rollback available).
4. Drop old rows/index after soak.
In-place overwrite leaves a window where the index mixes models, and no
rollback. Same pattern applies in dedicated vector DBs (new collection →
alias swap).

### Rule: Embedding pipelines follow the outbox/queue rules, not ad hoc syncs.
Source-row write → outbox/queue event (file 04) → embed worker (idempotent:
keyed on (chunk_id, model, source_hash)) → upsert embedding. Failures retry;
a periodic reconciliation sweep catches anything missed. Deleting the source
must delete embeddings everywhere — including a dedicated vector DB if used
(this is also a GDPR surface: file 06; vectors and their payload metadata can
reconstruct PII).

## Cost & capacity notes

- RAG chunk stores grow ~10–100× the source text (chunk overlap + per-chunk
  vectors + index) — capacity-plan the vector table like a real table
  (file 05), not an afterthought.
- HNSW build is parallel (`max_parallel_maintenance_workers`) but still
  hours at 10M+ rows — schedule rebuilds, don't improvise them.
- Quantization (halfvec/binary + rescore) before sharding; it's an order of
  magnitude of headroom for most workloads.

## Audit checklist

- [ ] Vector store choice justified: pgvector default; any dedicated vector
      DB tied to a measured trigger (scale/recall/isolation), with its sync
      pipeline, authz duplication, and backup story accounted for.
- [ ] HNSW (or justified IVFFlat) present — no exact-scan vector queries on
      large tables; operator matches opclass; query shape is index-eligible
      (EXPLAIN-verified); ef_search tuned against measured recall@k.
- [ ] pgvector at or above the CVE-2026-3172 fix (0.8.2; prefer 0.8.4+ for
      HNSW vacuum fixes).
- [ ] Filtered vector queries tested for recall under real filter selectivity;
      iterative scan / partial index / partition mitigation where needed;
      tenant isolation applies to vector queries (RLS or per-tenant index).
- [ ] Hybrid search (lexical + vector, RRF-fused) on user-facing retrieval;
      candidate counts sized for reranking; golden-set eval harness exists
      and gates retrieval changes.
- [ ] Every embedding tagged with pinned model+version; no mixed-model
      search space; query encoder coupled to stored model by config.
- [ ] source_hash (or equivalent) staleness detection + reconciliation job;
      embedding pipeline idempotent, outbox/queue-driven, with retries.
- [ ] Model migrations are dual-index with eval-gated cutover and rollback;
      old vectors dropped only after soak.
- [ ] Quantization ladder (halfvec → binary+rescore) exploited before
      sharding or engine migration; each step recall-validated.
- [ ] Dedicated vector DB (if present): auth on, server-side tenant
      enforcement tested, snapshot/restore rehearsed, sync lag alerted,
      collection rebuildable from Postgres source of truth.
- [ ] Vector DB not publicly reachable; TLS on; admin key in secret manager;
      read-only/scoped keys (or JWT RBAC) for query-only consumers; internal
      cluster ports (e.g. Qdrant 6335) unreachable from outside the cluster.
- [ ] Payload fields classified in the PII inventory; no secrets in payloads;
      tenant isolation enforced server-side (mandatory filter/scoped token or
      collection-per-tenant) with a cross-tenant leak test.
- [ ] Client-supplied search params (limit, ef/hnsw_ef, with_payload,
      with_vectors) capped server-side; no raw search bodies proxied to the
      vector DB.
- [ ] Source deletion cascades to all vector stores; vector data included in
      PII inventory and RTBF flow; capacity plan covers vector growth and
      index RAM.
