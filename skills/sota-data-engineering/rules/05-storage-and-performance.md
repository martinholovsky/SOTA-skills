# 05 — Storage & Performance

Analytical performance is mostly **scan avoidance**: read fewer files, fewer
row groups, fewer columns, fewer bytes. Every rule here is a variation on
that theme, and every one is also a cost lever.

## Parquet internals that matter

- **Row groups are the pruning unit.** Each carries min/max stats per
  column; engines skip row groups whose stats exclude the predicate
  (predicate pushdown). This only works if data is **sorted/clustered** on
  the filtered column — random layout makes every min/max range span
  everything, and pruning dies. Target row groups ~128 MB-ish (engine
  defaults are sane; pathological cases are tiny row groups from trickle
  writes).
- **Columnar projection:** only referenced columns are read. `SELECT *` in
  pipelines defeats the format's core advantage (and rules/01 bans it across
  layers anyway).
- **Dictionary encoding + page stats** make low-cardinality string filters
  cheap; sorted data compresses dramatically better (run-length/delta).
  Sorting is simultaneously a performance and a storage-cost move.
- **File sizing: target ~128 MB–1 GB per file.** Two failure modes:
  - *Small files* (the classic killer): thousands of KB-sized files from
    streaming/micro-batch/per-key writes turn metadata listing and open
    overhead into the dominant cost. Symptom: query time flat as data
    shrinks. Fix: compaction (below) and buffered/batched writes.
  - Giant single files limit read parallelism.
- **AUDIT:** `ls` a few partitions. Median file size under ~10 MB on a
  frequently-queried table = MEDIUM, HIGH at scale. CSV/JSON as the *query*
  layer (not just landing) = MEDIUM — convert to Parquet at staging.

## Partitioning vs clustering/sorting

- **Partitioning** (directory/metadata-level split, one value-set per
  partition): for the **coarse, always-filtered** dimension — almost always
  event date. Rules:
  - Partition count sanity: aim for partitions ≥ ~1 GB. Don't partition
    small tables at all.
  - **Never partition on high-cardinality columns** (`user_id`,
    `order_id`) — that's the small-files problem by construction =
    HIGH finding.
  - Iceberg uses *hidden* partitioning via transforms (`days(ts)`,
    `bucket(N, id)`) — queries on the raw column prune automatically, and
    partition schemes can evolve without rewriting old data.
- **Clustering/sorting within partitions:** for the second-tier filter
  columns (`customer_id`, `country`). Sort on write (`ORDER BY` in CTAS,
  Iceberg sort orders) or use the platform's clustering (Delta liquid
  clustering, warehouse cluster keys) so min/max pruning works inside
  partitions.
- Rule of thumb: **partition on one time column; sort/cluster on 1–3 query
  columns; stop.** Multi-level partitioning (`date/country/category`) is
  usually a small-files generator.

```sql
-- BAD: high-cardinality partitioning → millions of tiny files
CREATE TABLE events PARTITIONED BY (user_id) ...;

-- GOOD (Iceberg): coarse hidden time partition + bucket + sort
CREATE TABLE events (event_ts timestamp, user_id bigint, ...)
PARTITIONED BY (days(event_ts), bucket(32, user_id));
ALTER TABLE events WRITE ORDERED BY (user_id);
```

## Table formats: Iceberg / Delta

Open table formats add ACID commits, snapshots, and schema evolution on
object storage. Status (verified mid-2026): **Iceberg format v3** is ratified
and GA across major engines (deletion vectors, row lineage; engine support
for v3 features still varies — confirm your engines before enabling v3
features). **Delta Lake 4.x** brings the variant type and collations (deletion
vectors and liquid clustering matured in 3.x).

- **Snapshots & time travel:** every commit is a snapshot; you can query
  `AS OF` for debugging, incident forensics (rules/04), and WAP (rules/06).
  Time travel is bounded by snapshot retention — it is **not a backup
  strategy**.
- **Schema evolution:** safe in-place: add columns, widen types, rename
  (Iceberg tracks by field ID; renames are metadata-only). Still forbidden
  by *your* contracts without coordination (rules/04): downstream code keys
  on names.
- **Row-level changes:** merge-on-read (delete files/deletion vectors) makes
  MERGE/DELETE cheap at write time but accumulates read-time debt;
  copy-on-write is the reverse. CDC-heavy tables on merge-on-read **require**
  regular compaction of delete files or reads degrade steadily.
- **Maintenance is mandatory, scheduled, from day one:**
  - *Data compaction* (Iceberg `rewrite_data_files`, Delta `OPTIMIZE`):
    fixes small files and applies sort orders.
  - *Snapshot expiry* (`expire_snapshots` / `VACUUM`): unexpired snapshots
    = unbounded storage growth; retention window = your time-travel and
    concurrent-reader safety window (don't vacuum to zero).
  - *Manifest/metadata cleanup + orphan file removal* on a slower cadence.
  - **AUDIT:** An Iceberg/Delta table with no scheduled maintenance job =
    MEDIUM, HIGH for streaming/CDC-fed tables (they degrade fastest).

```sql
-- GOOD: scheduled weekly maintenance (Iceberg/Spark procedures)
CALL catalog.system.rewrite_data_files(
  table => 'db.events', strategy => 'sort',
  options => map('target-file-size-bytes', '536870912'));
CALL catalog.system.expire_snapshots(
  table => 'db.events', older_than => now() - INTERVAL 7 DAYS,
  retain_last => 20);
CALL catalog.system.remove_orphan_files(table => 'db.events');

-- Delta equivalents: OPTIMIZE events; VACUUM events RETAIN 168 HOURS;
```
- Concurrent writers: optimistic concurrency means conflicting commits
  retry; partition-overlapping concurrent writes (e.g. backfill + scheduled
  run on the same partitions) need coordination, not hope.

## Compression

- **zstd is the modern default** for Parquet (better ratio than snappy at
  similar read speed; level ~3 is the sweet spot — high levels buy little
  for analytics and cost write CPU). snappy remains fine; gzip is
  legacy-compat only; uncompressed is never right.
- Biggest compression lever is **sorting**, not codec choice (see above).
- Don't double-compress (gzip-ing Parquet files) and don't ship
  `.csv.gz` as a query layer — gzip CSV isn't splittable.

## Cost levers (warehouse credit burn & lake scan cost)

Cost in modern platforms ≈ bytes scanned × frequency + compute time ×
concurrency. Attack in this order:

1. **Prune more:** verify top queries actually hit partition/cluster
   pruning (`EXPLAIN` / query profile: partitions scanned vs total). A
   dashboard filter that wraps the partition column in a function can
   disable pruning — keep predicates sargable (see `sota-databases`).

   ```sql
   -- BAD: function over the partition column — full scan on many engines
   WHERE date(event_ts) = '2026-06-01'
   -- GOOD: range predicate on the raw column — prunes
   WHERE event_ts >= '2026-06-01' AND event_ts < '2026-06-02'
   ```
2. **Scan less per query:** incremental models instead of full rebuilds
   (rules/02); pre-aggregate hot dashboard queries into small marts;
   column pruning.
3. **Run less often:** match schedule to consumer need. An hourly rebuild
   feeding a daily-reviewed dashboard burns 24x the spend for zero value =
   classic MEDIUM finding.
4. **Materialization tradeoffs:** table for hot/expensive paths, view for
   cheap glue, incremental for large facts. A view chain 6 deep recomputed
   by every dashboard query is a hidden multiplier; conversely,
   materializing everything pays storage + build time for unread tables.
5. **Right-size and auto-suspend compute:** warehouses sized for the p99
   job running 24/7 for p50 work; aggressive auto-suspend; separate
   ETL/BI/ad-hoc compute pools so one team's scan storm doesn't queue
   everyone (and so cost is attributable per team).
6. **Watch the spend:** per-pipeline/per-team cost attribution and alerts
   on week-over-week jumps. Unattributed warehouse spend grows until
   someone panics.
- **AUDIT (quick wins, in order):** full-refresh models on large sources;
  queries scanning all partitions; small-files tables; oversized always-on
  compute; orphaned pipelines feeding dashboards nobody opens (check BI
  view counts — deleting a pipeline is the best optimization).

## Audit checklist

- [ ] Query layer is columnar (Parquet/native), not CSV/JSON?
- [ ] File sizes healthy (~128 MB–1 GB median); no small-files
      accumulation on hot tables?
- [ ] Partitioned on a coarse time column only; no high-cardinality or
      deep multi-level partitioning?
- [ ] Sort/cluster order defined matching top query predicates; pruning
      verified via query profiles?
- [ ] Iceberg/Delta: compaction + snapshot expiry + orphan cleanup
      scheduled on every table; CDC-fed merge-on-read tables compacted
      aggressively?
- [ ] Snapshot retention consciously chosen (forensics window vs storage)?
- [ ] Concurrent-writer conflicts (backfill vs scheduled) coordinated?
- [ ] zstd (or justified alternative) everywhere; no double compression?
- [ ] Hot dashboards served from pre-aggregated marts, not view chains over
      raw facts?
- [ ] Schedules match consumer freshness needs; no hourly builds of
      daily-read data?
- [ ] Compute auto-suspends, pools separated by workload, cost attributed
      per pipeline/team with trend alerts?