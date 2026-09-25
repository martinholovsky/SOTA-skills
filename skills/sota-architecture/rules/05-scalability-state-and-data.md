# 05 — Scalability, State & Data Architecture

Rules for scaling horizontally, placing state deliberately, caching without
lying, partitioning data, and isolating tenants. Scaling problems are state
problems; everything stateless is trivially scalable.

## 1. Stateless services by default

**Rule:** Service instances hold no request-scoped state between requests: no
sticky sessions, no local user files, no in-memory state another request depends
on. Session state goes to a shared store (Redis/DB) or signed tokens; files go
to object storage. Any instance can serve any request; any instance can die
mid-flight without data loss.

**Test:** Can you kill any instance at any moment and scale 1→N→1 with zero
correctness impact? If not, find the hidden state and evict it.

**Permissible local state:** caches (rebuildable, with bounded staleness) and
buffers already made durable elsewhere. Local state that is the *only* copy of
anything is a Critical finding.

**Rule:** If state must live in the service (stateful stream processing,
websocket hubs, game servers), be explicit: consistent-hash routing, replication,
and a rebalancing story. Accidental statefulness is the problem; deliberate
statefulness is a design.

## 2. Scale out, not up; know your bottleneck first

**Rule:** Design for horizontal scaling (more replicas behind a load balancer),
but **measure before scaling**: profile and load-test to find the actual
bottleneck. Scaling app replicas when the database is the bottleneck adds
connections and makes it worse.

**Rule:** Autoscale on the constraining signal (queue depth, p95 latency,
concurrent requests) — CPU only when CPU is genuinely the constraint. Set
sane min/max, and verify scale-*down* behaves (connection draining, no flapping).

**Rule:** Every shared resource downstream of a scalable tier needs a guard:
connection poolers (e.g., pgbouncer) in front of databases, concurrency limits
per instance, rate limits per client. N autoscaled replicas × M connections
each is the classic way to murder a database.

## 3. The database is the hard part

**Rule:** Scale reads first via replicas + caching; scale writes via partitioning
(§5) only when measured write throughput or data volume demands it. In between,
exhaust the boring options: indexes, query tuning, fewer round-trips, bigger box.
Vertical scaling is honest and cheap up to a surprisingly high ceiling.

**Rule:** Read replicas are eventually consistent. Audit every read-after-write
flow: route them to the primary, pin by session, or use version tokens
(read-your-writes, rules/03 §1). Random replica reads after writes produce
"my save disappeared" bugs.

**Rule:** Long-running queries, analytics, and reporting never run against the
OLTP primary. Use a replica, CDC into an analytical store, or scheduled
extracts. One BI query table-scanning production is a recurring outage pattern.

## 4. Caching: every cache is a consistency decision

**Rule:** For each cache, write down: key shape, TTL, max staleness tolerated,
invalidation trigger, stampede protection, and fallback when cold/down. A cache
without an invalidation story is a bug factory with good latency.

**Tiering (apply outside-in; each tier only if measured need):**
1. CDN/edge — static assets, anonymous pages.
2. Gateway/HTTP cache — cacheable GETs with correct `Cache-Control`/ETags.
3. Distributed cache (Redis/Memcached) — hot entities, computed views, sessions.
4. In-process cache — tiny, hottest keys, short TTL (it multiplies staleness by replica count).

**Patterns:**
- Default: **cache-aside** with TTL + explicit invalidation on write (delete, don't update, the key — update races produce stale-forever entries).
- Stampede protection on hot keys: single-flight/request coalescing + TTL jitter + optionally serve-stale-while-revalidate.
- Negative caching with short TTL for "not found" to stop miss-storms.

**Rule:** The system must be *correct* (if slow) with the cache completely cold
or down. If cache loss = outage or wrong answers, you've built an unmanaged
datastore; either make it a real datastore (durable, replicated) or fix the
dependency.

**Rule:** Never cache authorization decisions or feature-flag evaluations beyond
their tolerated staleness (seconds, not hours), and never share cached responses
across users/tenants without the user/tenant in the key. Missing tenant in cache
key = cross-tenant data leak = Critical.

## 5. Partitioning (sharding): defer, then commit properly

**Rule:** Partition when a single primary measurably can't hold the write load,
working set, or data volume — not before. Sharding multiplies every operational
task (migrations, backups, queries, rebalancing).

**Rule:** Choose the partition key by access pattern: the key that appears in
~all hot queries (tenant_id for B2B SaaS, user_id for consumer). Getting it
wrong means scatter-gather on every request; changing it later is a full data
migration. This is a Type 1 decision — ADR required.

**Rule:** Design for resharding from day one: use many logical partitions
mapped to few physical nodes (consistent hashing or a directory/lookup service),
so adding nodes moves logical partitions instead of rehashing the world.

**Rule:** Accept and design around the losses: no cross-shard transactions
(use sagas, rules/03 §5), no cross-shard joins (denormalize or query a
projection), hot-partition monitoring (one celebrity tenant can melt a shard —
have an isolation/relocation plan).

## 6. Data lifecycle and growth

**Rule:** Every table/collection/topic has a growth model and a lifecycle:
retention policy, archival path (object storage), and deletion (legal +
GDPR/erasure). "Keep everything forever in the OLTP store" is a slow-motion
incident: backups, migrations, and queries all degrade.

**Rule:** Time-series and append-mostly data (events, logs, audit) goes to
stores built for it (or native table partitioning by time with partition
dropping), not into the same tables as hot transactional rows.

## 7. Multi-tenancy: pick the model consciously

**Models (per tier of customer, not necessarily one global choice):**

| Model | Isolation | Cost/tenant | Use when |
|---|---|---|---|
| Pooled: shared schema, `tenant_id` column | Lowest (logical only) | Lowest | Long tail of small tenants |
| Schema-per-tenant / DB-per-tenant | Medium–high | Medium | Hundreds of tenants, compliance asks |
| Silo: dedicated stack per tenant | Highest | Highest | Regulated/enterprise tier, residency requirements |

**Rule:** Every shared layer follows the tenant's tier, and that includes the cache. A
silo or high-isolation tenant gets its own cache instance or cluster. Key prefixes in a
shared Redis are not enough, because a prefix keeps keys apart only while every code path
builds its keys correctly. One shared instance also shares memory, eviction, one
`FLUSHALL` and every credential that can reach it. Pooled tenants may share an instance
with tenant-scoped keys (§4). Either way the check comes first: authorize the request
before reading a cached value. (OWASP: Multi Tenant Security cheat sheet)

**Rule:** In pooled models, tenant isolation must be enforced *below* the
application's good intentions: row-level security in the DB, or a mandatory
tenant-scoped repository layer that makes it impossible to build a query without
`tenant_id` — verified by tests that attempt cross-tenant access. One forgotten
`WHERE tenant_id = ?` is a breach.

**Rule:** Tenant context flows from authenticated identity at the edge through
every hop (headers/context), is never accepted from request bodies or query
params, and appears in: every query, every cache key (§4), every queue message,
every log line, and every metric label (for noisy-neighbor attribution).

**Rule:** Apply fairness controls in pooled tiers: per-tenant rate limits,
per-tenant concurrency caps, per-tenant queue quotas (bulkheads, rules/04 §4).
Without them, your biggest tenant defines everyone's worst day.

**Rule:** Plan tenant mobility: onboarding, offboarding (export + verified
deletion), and *migration between models* (a pooled tenant grows into a silo).
If moving one tenant's data out is impossible, you've built a roach motel.

**Rule:** Provisioning and offboarding are security operations with an explicit
state machine (`provisioning → active → offboarding → deleted`), not a script.
- *Provision*: create the tenant's schema/DB, storage prefix, keys and first
  credential while it sits in `provisioning`, and flip it to `active` only as the
  last step. A single DB transaction rarely spans the schema, the object store and
  the KMS, so the failure path must be an idempotent cleanup that removes whatever
  was half-created — an orphaned schema or key is a later tenant's collision.
- *Offboard*: move to `offboarding` first, so new operations are refused, then
  revoke every session, API key, token and integration credential the tenant holds,
  and only then export (if owed) and schedule deletion. Deleting data while a key
  still works leaves an authenticated principal pointing at nothing, or at the next
  tenant who reuses the id.
- Write each step (started, completed, failed) to the audit trail; deletion then
  follows the retention policy across replicas, object versions and backups (§6).
OWASP: Multi Tenant Security cheat sheet.

## 8. Workload separation

**Rule:** Separate latency-sensitive request serving from throughput-oriented
batch/async work: different deployments, pools, and scaling policies (bulkheads,
rules/04 §4). Background jobs run on workers consuming queues — never as fire-
and-forget threads inside request-serving instances, where deploys and
autoscaling silently kill them.

**Rule:** All heavy work triggered by users (exports, imports, report
generation) is async: enqueue, return a job handle, notify on completion.
Holding an HTTP connection open for a 5-minute job fails at every proxy,
timeout, and deploy between you and the user.

## 9. Capacity: utilization math you can't ignore

**Rule:** Queueing theory is not optional: at high utilization, wait time
explodes nonlinearly (M/M/1: wait ∝ ρ/(1−ρ); 80%→90% utilization roughly
doubles queueing delay). Plan steady-state utilization of latency-sensitive
tiers at ~50–70%, not 90% — the "wasted" headroom is what absorbs bursts,
deploys, and AZ loss.

**Rule:** Capacity-plan against peak + failure: the fleet must serve peak
traffic with one AZ down and one deploy in flight. N+1 at the *peak*, not the
average.

**Rule:** Load-test with production-shaped traffic (real key skew, real
read/write mix, real payload sizes) before major launches. Uniform-random
synthetic load hides hot keys and lock contention — the two things that
actually fall over.

## 10. Hot keys and skew

**Rule:** Assume skew: some tenant, product, or celebrity will be 1000x median.
Detect it (top-K key metrics on caches, partitions, and rate limiters) and have
a playbook: replicate hot read keys (key suffixing: `item:42#1..N`), isolate
hot tenants to dedicated capacity, collapse duplicate in-flight work
(single-flight), precompute hot aggregations.

**Rule:** Counters and append-heavy rows (likes, view counts, "current balance"
rows updated by everything) serialize on row locks. Shard the counter
(N sub-rows summed on read) or buffer increments through a queue and apply in
batches.

## 11. Derived data and projections

**Rule:** Treat search indexes, materialized views, denormalized read tables,
and analytics copies as *derived data*: rebuildable from the source of truth by
a documented, tested backfill job. If you can't rebuild a projection, it's
secretly a primary store with no backup discipline.

**Rule:** Keep derivation pipelines idempotent and ordered-per-key (rules/03
§2, §7); track and alert on projection lag the same way as replica lag.
Consumers of a projection must know its staleness contract.

**Rule:** Push denormalization to the read side, never the write side: the
write model stays normalized around invariants (rules/02 §3); projections
denormalize per consumer. Denormalizing the write model "for performance"
trades correctness machinery for a cache you can't invalidate.

## 12. Large objects and blob handling

**Rule:** Binary/large content (images, exports, documents) lives in object
storage with the database holding metadata + key. Uploads and downloads go
direct-to-storage via presigned URLs — streaming gigabytes through your API
tier burns its memory and connection slots for zero value.

**Rule:** Lifecycle-manage blobs like rows (§6): retention classes, orphan
sweeps (DB row deleted but blob remains, or vice versa — reconcile on a
schedule), and per-tenant prefixes so tenant offboarding (§7) can actually
delete their data.

**Rule:** Classify every stored object as global, tenant-scoped or user-scoped,
and put intentionally shared assets under a separately named global namespace, so
nothing tenant-owned lands there by default. Partition tenant objects by a
tenant-aware bucket, account or prefix *and* have the storage policy enforce it
(a per-tenant role or policy condition), so a bug in application code is not the
only thing between tenants. **End every tenant prefix with the delimiter**: list
and delete by prefix match a raw string (S3 `ListObjectsV2` "limits the response
to keys that begin with the specified prefix"), so the prefix `acme` also matches
`acme-west/…` and an offboarding delete of `acme` erases a second tenant. Use
`acme/`. Authorize the exact object and verb before signing a URL for it.
OWASP: Multi Tenant Security cheat sheet.

## Audit checklist

- [ ] Can every service instance be killed at any moment without data loss? Any sticky sessions, local files, or solo in-memory state?
- [ ] Is session/user state in a shared store or token, not instance memory?
- [ ] Is autoscaling driven by the constraining metric, with verified scale-down/drain behavior?
- [ ] Are database connections guarded (pooler, per-instance caps) against replica multiplication?
- [ ] Are read-after-write flows protected against replica/cache staleness?
- [ ] Do analytics or long-running queries run against the OLTP primary?
- [ ] Does every cache have documented TTL, invalidation trigger, stampede protection, and a correct cold-cache fallback? Is anything cache-as-only-copy?
- [ ] Do cache keys include user/tenant scope everywhere responses differ by user/tenant?
- [ ] If sharded: was the partition key chosen from access patterns (ADR)? Are logical→physical partitions resharding-friendly? Any cross-shard transactions or joins?
- [ ] Does every large table/topic have retention, archival, and erasure paths?
- [ ] Is the multi-tenancy model explicit per tenant tier? Is tenant isolation enforced below application code (RLS or mandatory scoped layer) with cross-tenant access tests?
- [ ] **Isolated tiers have their own cache (§7), High:** for each silo or high-isolation tenant, its cache endpoint differs from the pooled one. List the endpoints with `grep -rnE -i '(redis|valkey|memcached?|cache)[_.-]?(url|uri|host|endpoint)' .`. A silo tenant that resolves to the shared endpoint is a finding.
- [ ] Is tenant context derived from identity (not request params) and present in queries, cache keys, messages, logs, metrics?
- [ ] Are per-tenant rate/concurrency/queue quotas in place in pooled tiers?
- [ ] Is all user-triggered heavy work async with job handles, and are background jobs on dedicated workers?
- [ ] Is steady-state utilization of latency-sensitive tiers planned with headroom (~50–70%), and does capacity cover peak with an AZ down?
- [ ] Are load tests production-shaped (key skew, payload sizes), and is hot-key detection (top-K metrics) with a mitigation playbook in place?
- [ ] Are high-contention counters sharded or queue-buffered rather than single-row hot spots?
- [ ] Is every projection/search index/denormalized table rebuildable via a tested backfill, with lag monitored and staleness contracts known to consumers?
- [ ] Are blobs in object storage with presigned direct transfer, orphan reconciliation, and tenant-scoped prefixes?
- [ ] Does tenant offboarding refuse new operations and revoke every session and API key **before** deletion is scheduled, and does a failed provision clean up what it half-created, with each step audited (§7)? HIGH where a deprovisioned tenant's key still authenticates. Probe for offboarding code that never revokes: `grep -rliE '(offboard|deprovision)[_a-z]*[[:space:]]*\(' . | while read -r f; do grep -qi revoke "$f" || echo "$f"; done` — a listed file is a lead, read its order of operations.
- [ ] Does every tenant storage prefix end in the delimiter, is the boundary enforced by storage policy and not only app code, and do shared assets live in a named global namespace (§12)? HIGH: prefix `acme` matches `acme-west`, so a list leaks and an offboarding delete erases another tenant. Probe for a prefix built from a tenant id with no `/` after it: `grep -rniE 'prefix[[:space:]]*[:=].*tenant[^/]*$' .`
