# 05 — Reliability & Scale

## Backups & PITR

### Rule: A backup is restorable, point-in-time, off-box, and rehearsed — or it isn't a backup.
- **PITR** (base backup + continuous WAL archiving — pgBackRest, WAL-G, or
  managed equivalent) is the baseline. Nightly `pg_dump` alone means losing up
  to 24h (RPO=24h) and restoring slowly at scale; it's a supplement (logical,
  per-table recovery), not the strategy.
- State **RPO** (max data loss) and **RTO** (max downtime) explicitly; verify
  the setup achieves them. WAL archiving interval bounds RPO.
- **Restore rehearsal on a schedule**, automated: spin up from backup, run
  integrity checks (row counts on key tables, app smoke test), record time
  (that's your real RTO). Restoring into staging monthly does double duty.
  Untested backups: CRITICAL, no discussion.
- Off-instance and off-account/region storage; retention covers both ops
  recovery (days–weeks of PITR) and compliance (longer, possibly logical).
- **Replication is not backup** — a replica replays your `DROP TABLE`
  instantly. Delayed replicas are a complement, not a substitute.
- Protect backups from the database's own credentials (a compromised DB host
  must not be able to delete its backups — object lock / separate creds).

## Replication & read replicas

### Rule: Async by default; sync only for the durability you'll pay latency for.
- **Async** streaming: primary doesn't wait; replica crash-lag = lost recent
  commits on failover. Fine for read scaling and most HA.
- **Sync** (`synchronous_commit = on` + `synchronous_standby_names`): zero
  data loss on failover, every commit pays a network round trip, and a dead
  sync standby **blocks all commits** unless you have quorum
  (`ANY 1 (a, b)`) — never a single sync standby without quorum.
- Failover: use a battle-tested orchestrator (Patroni, managed-cloud HA);
  hand-rolled failover scripts cause split-brain. Test failover like you test
  restores.

### Rule: Read replicas are eventually consistent — route reads by staleness tolerance, not by load alone.
Read-your-own-writes breaks when a user's next request hits a lagging replica.
- Route to primary: anything read-after-write in the same user flow
  (post-then-show, payment status), auth/session checks.
- Route to replicas: search, browse, analytics, anything tolerating seconds
  of lag.
- Patterns when you must scale read-your-writes: sticky-to-primary for N
  seconds after a write; or track LSN (`pg_current_wal_lsn()` after write,
  wait for `pg_last_wal_replay_lsn() >= lsn` on replica).
- Monitor lag in **bytes and seconds** (`pg_stat_replication.replay_lsn`
  delta, `pg_last_xact_replay_timestamp`); alert before the lag exceeds what
  your routing assumes.
- Long queries on hot-standby replicas conflict with replay
  (`max_standby_streaming_delay` trade-off: cancel queries vs grow lag).
  Run heavy analytics on a dedicated replica with replay delay allowed, or on
  a logical-replica/warehouse.

### Rule: Logical replication is the tool for major-version upgrades, selective sync, and CDC — know its limits.
- Near-zero-downtime **major version upgrades**: logical replica on the new
  version → cutover. (`pg_upgrade --link` is the fast in-place alternative
  with brief downtime; dump/restore is for small DBs only.) Don't camp on an
  EOL major version — that's an audit finding on its own. Minor updates
  matter too: apply the quarterly minor releases within a defined SLA —
  they carry security fixes up to RCE class (the Feb 2026 minors fixed
  arbitrary-code-execution bugs in pgcrypto, CVE-2026-2005, and intarray,
  CVE-2026-2004).
- **CDC** (Debezium-style) for feeding warehouses/search/caches: monitor slot
  lag religiously — an abandoned logical slot pins WAL until the disk fills
  (see vacuum section); set `max_slot_wal_keep_size` as the safety valve.
- Limits: DDL is not replicated (coordinate schema changes manually);
  sequences aren't replicated (resync at cutover); large transactions can
  stall apply.

## Partitioning

### Rule: Partition when lifecycle or scale demands it — not before, and plan it early enough.
Triggers for partitioning: table > ~100GB and growing; time-based retention
("delete data older than X" — partition drop is instant, mass DELETE is a
bloat catastrophe); pruning matches the dominant query predicate; vacuum on
the monolith can't keep up.
- **RANGE on time** for events/logs/audit (with `pg_partman` or equivalent for
  auto-creation — running out of future partitions is a classic outage).
  **LIST/HASH** for tenant or shard-key splits.
- The partition key must appear in hot queries (else every query scans all
  partitions) and must be part of PK/unique constraints (design constraint —
  decide before, not after).
- Default partition: have one as a safety net, monitor it staying empty.
- Retention = `DROP TABLE partition` (instant, no bloat). This alone justifies
  partitioning audit/event tables (file 01).
- Converting a live monolith table is a project (file 02: dual-write + swap);
  partition *at creation* any table you know will be append-heavy.

## Vacuum & bloat

### Rule: Autovacuum is correctly tuned, never disabled, and bloat is measured.
MVCC means every UPDATE/DELETE leaves a dead tuple; vacuum reclaims them.
Failure modes: table/index bloat (queries slow, cache wasted), stale
visibility maps (index-only scans degrade), and at the extreme **wraparound**
forced shutdown.
- Defaults are too lazy for hot tables: lower per-table
  `autovacuum_vacuum_scale_factor` (e.g. 0.01–0.02) on high-churn tables;
  raise `autovacuum_vacuum_cost_limit` / workers globally if vacuum can't
  keep up. Monitor `pg_stat_user_tables.n_dead_tup` vs live, and
  `last_autovacuum` age.
- Things that block vacuum (audit these first when bloat appears): long
  transactions (file 04), abandoned replication slots
  (`pg_replication_slots` where inactive — they pin WAL **and** xmin),
  hot_standby_feedback from long replica queries, prepared transactions
  (`pg_prepared_xacts` should be empty unless you really run 2PC).
- Wraparound: alert on `age(datfrozenxid)` > ~200M before autovacuum's
  emergency mode does it for you.
- Existing bloat: `pg_repack` (online) — not VACUUM FULL (exclusive lock)
  outside a maintenance window. PG19 (beta as of mid-2026) adds a built-in
  `REPACK ... CONCURRENTLY` that replaces pg_repack for this.
- Mass deletes: batch them (file 02) or partition; an unbatched
  multi-million-row DELETE is self-inflicted bloat + replication lag.

## Monitoring — the metric set that matters

### Rule: If these aren't graphed and alerted, the database is unmonitored.
- **Saturation:** connections vs max (+ pooler `cl_waiting`), CPU, disk space
  (% AND days-until-full from growth rate), IOPS vs provisioned.
- **Workload:** p95/p99 query latency via `pg_stat_statements` (top by
  total_exec_time), TPS, cache hit ratio (`blks_hit/(hit+read)` < ~0.99 on
  OLTP = memory pressure), temp file bytes (work_mem pressure).
- **Health:** replication lag (bytes + seconds), oldest transaction age,
  `idle in transaction` count, dead tuple ratios, autovacuum recency,
  `age(datfrozenxid)`, inactive replication slots, deadlock rate, WAL
  generation rate, invalid indexes.
- **Locks:** sessions waiting on locks (`pg_locks` not granted) > N seconds.
- Alert on trends (days-to-disk-full, lag growth), not just thresholds.

Queries worth wiring into dashboards directly:
```sql
-- replication lag per replica (run on primary)
SELECT application_name, state,
       pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes
FROM pg_stat_replication;
-- slots pinning WAL (abandoned slot = disk-full incident in progress)
SELECT slot_name, active,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained
FROM pg_replication_slots;
-- bloat candidates
SELECT relname, n_dead_tup, n_live_tup, last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000 AND n_dead_tup > n_live_tup * 0.1
ORDER BY n_dead_tup DESC;
-- top queries by total time
SELECT left(query, 80), calls, total_exec_time, mean_exec_time, rows
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 20;
```

## Scaling order of operations

### Rule: Exhaust these, in order, before saying "shard": measure → index/query
(file 03) → pooling (file 04) → caching (below) → read replicas → vertical
scaling (a single 2026 box runs Postgres to many TB and 100k+ TPS) →
partitioning → only then sharding (Citus, Vitess-for-MySQL, app-level by
tenant). Sharding costs cross-shard transactions, joins, unique constraints,
and rebalancing forever. Genuine signals you're approaching it: write volume
beyond one primary's I/O after tuning; working set far beyond max RAM;
vacuum/replication permanently behind despite tuning; single-tenant whales
(extract them first — file 01 hybrid tenancy).

## Redis & the caching layer

Everything here applies equally to **Valkey** (BSD-3, Linux Foundation fork;
the default open alternative since Redis moved to AGPLv3 tri-licensing — AWS
ElastiCache and GCP Memorystore ship it). Module gap has mostly closed:
valkey-json and valkey-search are GA (1.0+) and ship in the official
valkey-bundle — only a TimeSeries-equivalent module is still missing.

### Rule: Cache-aside with TTLs is the default pattern; invalidation is designed, not hoped.
```
read:  GET key → hit? return : load from DB → SET key val EX ttl → return
write: write DB (txn commits) → DEL key      -- delete, don't update-in-place
```
- **Always a TTL**, even with explicit invalidation — TTL is the bound on how
  wrong you can be. Jitter TTLs (±10–20%) to avoid synchronized expiry.
- Invalidate by **delete after commit** (update-in-place races with
  concurrent writers; delete is idempotent and converges). Accept the brief
  stale window of read-modify race, or use versioned keys when you can't.
- **Stampede protection** on hot keys: per-key mutex (`SET key 1 NX EX 10`
  around the DB load), probabilistic early refresh, or serve-stale-while-
  revalidate. A hot key expiring under load = thundering herd on the DB.
- Cache **misses** of existence checks too (negative caching, short TTL) when
  lookups of absent keys are common — else absent-key floods bypass the cache.
- Redis is ephemeral here: the app must be correct (just slower) with Redis
  flushed. If a Redis flush corrupts behavior, you've built a database in a
  cache (CRITICAL).
- Set `maxmemory` + `allkeys-lru`/`lfu` for pure caches; `noeviction` only
  for Redis-as-queue/state with explicit capacity planning.

### Rule: The moment Redis holds state you can't lose, it needs the full ops treatment.
Rate-limit counters, sessions you promised to keep, queue/stream contents,
distributed lock state — once any of these matter, configure Redis like a
database, not a cache:
- Persistence: AOF `appendfsync everysec` (RDB snapshots alone lose minutes);
  understand that even AOF loses ~1s on crash — if that's unacceptable, the
  data belongs in Postgres.
- HA: Sentinel or Cluster with tested failover. Failover loses recent
  async-replicated writes — locks and counters may rewind (another reason
  fencing tokens exist, below).
- Memory: `noeviction` for state (an evicting "queue" silently drops jobs);
  capacity alerts; separate the cache instance (LRU, flushable) from the
  state instance (noeviction, persisted) — mixed instances inherit the worst
  constraints of both.
- Big-O discipline: no `KEYS`, no unbounded `SMEMBERS`/`LRANGE 0 -1`, `SCAN`
  for iteration; single-threaded Redis means one O(N) command stalls everyone
  (watch `slowlog`).

### Rule: Distributed locks in Redis — single-instance SET NX with token + fencing; treat Redlock claims skeptically.
```
SET lock:resource <random_token> NX PX 30000
-- release: Lua script — compare token, then DEL (never blind DEL: you'd
--          release someone else's lock after your own expiry)
```
- The TTL-vs-pause problem is fundamental: a GC pause/network blip past the
  TTL means **two holders**. For efficiency locks (avoid duplicate work),
  that's acceptable. For **correctness**, the protected resource must enforce
  **fencing tokens** (monotonic number checked by the resource — e.g. a
  version/`WHERE token >= $n` in the DB) — Kleppmann's critique of Redlock
  stands; Redlock across N nodes still cannot guarantee safety under pauses
  and clock skew without fencing.
- If the source of truth is Postgres anyway, prefer `pg_advisory_xact_lock`
  or SKIP LOCKED (file 04) — locks colocated with the data they protect.

### Rule: Redis Streams (consumer groups) for lightweight queues — with the full loop.
`XADD` → `XREADGROUP` → process → `XACK`, plus: `XAUTOCLAIM` for messages
stuck in another consumer's PEL (crashed worker), `MAXLEN ~` to bound stream
memory, dead-letter after N delivery attempts, idempotent consumers (at-least-
once delivery is the contract; file 04). Pub/Sub is fire-and-forget (drops on
disconnect) — never for anything that must be processed. Postgres SKIP LOCKED
remains the right queue when jobs must commit atomically with data.

## Audit checklist

- [ ] PITR-class backups, off-box/off-account, restore rehearsed on a
      schedule with recorded RTO; RPO/RTO stated; backups protected from DB
      credentials; replication not counted as backup.
- [ ] Sync replication only with quorum; failover orchestrated and tested;
      replica routing respects read-your-own-writes; lag monitored in bytes
      and seconds with alerts below routing assumptions.
- [ ] Retention-bearing big tables partitioned (or a plan exists before
      100GB); future partitions auto-created; partition key in hot predicates
      and unique constraints; retention via partition drop, not mass DELETE.
- [ ] Autovacuum tuned per hot table; dead-tuple ratio, last_autovacuum,
      wraparound age monitored; no inactive replication slots, stale prepared
      xacts, or chronic long transactions pinning xmin; pg_repack (not VACUUM
      FULL) for live de-bloat.
- [ ] The monitoring metric set above graphed + alerted, including
      days-until-disk-full and pooler saturation.
- [ ] Scaling proposals follow the order of operations; no sharding while
      indexes/caching/replicas/vertical headroom remain unexploited.
- [ ] Cache: TTLs with jitter everywhere, delete-after-commit invalidation,
      stampede protection on hot keys, correct-when-flushed property holds,
      maxmemory+eviction policy explicit.
- [ ] Redis locks: NX + token + Lua release + TTL; fencing tokens wherever
      the lock guards correctness; no blind DEL releases; no unfenced Redlock
      protecting correctness-critical resources.
- [ ] Streams consumers: XACK + XAUTOCLAIM + MAXLEN + dead-letter +
      idempotency; no Pub/Sub for must-process messages.
- [ ] Redis holding non-cache state has AOF persistence, tested failover,
      noeviction, and is separated from the LRU cache instance; no
      KEYS/unbounded-range commands in code.
- [ ] Postgres major version supported (not EOL) and quarterly minor updates
      applied within a defined SLA (minors fix RCE-class bugs — e.g. pgcrypto
      CVE-2026-2005); logical/CDC slots monitored with max_slot_wal_keep_size
      set.
