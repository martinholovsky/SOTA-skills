# 03 — Streaming & CDC

Streaming is the most expensive way to move data. It buys latency and pays
in operational complexity, harder testing, and harder reprocessing. Make it
earn its place.

## 1. When streaming is justified

- **Require a named consumer with a sub-minute (or low-minutes) latency
  need:** fraud/abuse decisions, operational dashboards driving immediate
  action, ML features that decay in minutes, user-facing freshness.
- "The business wants real-time" usually means "the daily batch is too
  slow." Try 15-minute or hourly micro-batch first — same orchestration,
  same idempotent batch semantics, ~10x less operational surface.
- **Streaming is also legitimate as transport regardless of latency:** CDC
  replication (below) and high-volume event ingestion where a durable log
  beats files. Transport-streaming + batch-transform is a sound and common
  shape.
- **AUDIT:** A Flink/Kafka Streams job whose only consumer is an hourly
  dashboard = MEDIUM (cost/complexity without benefit). No documented
  latency requirement for a streaming component = ask; absence of any
  consumer needing it = finding.

## 2. Kafka-style log fundamentals

(Kafka 4.0 removed ZooKeeper — KRaft-only; the KIP-848 consumer
rebalance protocol is GA since 4.0 and consumers opt in via
`group.protocol=consumer`. Same fundamentals apply to Pulsar/Kinesis/Redpanda.)

- **Ordering exists only within a partition.** Choose the partition key as
  the entity whose event order matters (`order_id`, `user_id`,
  `aggregate_id`). Random/round-robin keys on a topic where consumers assume
  per-entity order is a CRITICAL correctness finding.
- **Key skew:** one hot key = one hot partition = one maxed consumer no
  matter how many instances you add. Check partition-level lag/throughput
  for skew before scaling out.
- **Partition count is concurrency ceiling** for a classic consumer group
  (one consumer per partition max). Size with headroom (you can add
  partitions but that **reshuffles key→partition mapping**, breaking
  per-key ordering across the boundary — plan it, don't improvise it).
  KIP-932 "share groups" (queue semantics, more consumers than partitions,
  per-record acks) are production-ready since Kafka 4.2 but sacrifice
  per-key ordering — only for true queue workloads.
- **Consumer groups & offsets:** commit offsets only after the message's
  effects are durably stored. Auto-commit-on-poll means a crash between
  commit and processing **loses data**; commit-after-process means
  duplicates on crash — which is why sinks must be idempotent (below).
- **Rebalancing pitfalls:** long processing between polls (`max.poll.interval.ms`
  exceeded) gets consumers evicted, causing rebalance storms; slow
  startup + eager rebalance causes stop-the-world pauses. Use cooperative/
  KIP-848 protocols, keep per-poll work bounded, and process slow items
  async with pause/resume rather than blocking poll.
- **Retention is a contract:** consumers must be able to be down for less
  than retention and recover. Lag monitoring with alerts on every production
  group is mandatory; lag approaching retention = imminent data loss.

## 3. Exactly-once reality

"Exactly-once" end-to-end is achieved as **effectively-once: at-least-once
delivery + idempotent application of effects.** Audit the sink, not the
producer flag.

- **Idempotent producer** (`enable.idempotence=true`, default in modern
  clients): prevents broker-side duplicates from producer retries. Necessary,
  nowhere near sufficient.
- **Kafka transactions / EOS:** give atomic consume-transform-produce
  *within Kafka* (Kafka→Kafka pipelines, Streams `processing.guarantee=
  exactly_once_v2`). The moment data leaves Kafka for a warehouse, lake, or
  API, transactions stop covering it.
- **At the sink, make redelivery harmless:**
  - MERGE/upsert on a natural or deterministic key (event ID,
    `topic-partition-offset`).
  - Or atomic write+offset: store consumed offsets in the same transaction
    as the data (e.g. in the target DB), resume from stored offsets.
  - Or rely on the connector's documented mechanism (e.g. table-format sinks
    committing offsets inside the table commit) — verify, don't assume.

```python
# BAD: duplicates on every crash between write and commit
for msg in consumer:
    warehouse.insert("events", msg.value)      # append
    consumer.commit()                          # separate failure domain

# GOOD: redelivery-proof — offset stored atomically with the data
for batch in consumer.batches():
    with target_db.transaction() as tx:
        tx.merge("events", batch.rows, key="event_id")     # idempotent
        tx.upsert("kafka_offsets", batch.tp, batch.last_offset)
# on startup: seek(stored_offset + 1); Kafka's committed offset is advisory
```
- **AUDIT:** Consumer writes appends to a warehouse table and commits Kafka
  offsets separately = duplicates on every crash/rebalance = CRITICAL if the
  table feeds metrics. "We have exactly-once because idempotent producer is
  on" = misunderstanding; check the sink.

## 4. Schema registry & evolution

- **Every production topic has a registered schema** (Avro/Protobuf/JSON
  Schema). Schemaless JSON topics shared across teams = HIGH; every consumer
  is one producer refactor away from breaking.
- **Pick and enforce a compatibility mode.** `BACKWARD` (new schema reads
  old data: add optional fields, delete fields) lets consumers upgrade
  after producers — the common default. `FORWARD` = consumers first.
  `FULL` for long-lived shared topics. Never `NONE` in prod.
- Breaking changes (rename, retype, semantic change) = **new topic** (or
  contract-versioned subject) + migration window, not an in-place break.
- Defaults on new fields; never reuse field IDs/positions (Protobuf/Avro).

## 5. CDC patterns

- **Log-based CDC holds a replication slot on the source**, and an abandoned or lagging slot makes
  the source retain WAL until its disk fills: alert on slot lag, set `max_slot_wal_keep_size` (its
  default, `-1`, is unlimited), and drop slots no connector owns ([`sota-databases` rules/05](../../sota-databases/rules/05-reliability-and-scale.md)).
- **Log-based CDC (Debezium-class) is the default** for
  replicating OLTP into the analytical platform: reads the WAL/binlog,
  emits ordered change events, near-zero source impact. Query-based
  ("`SELECT WHERE updated_at >`") misses deletes and intermediate states —
  acceptable only for append-only sources.
- **Snapshot + stream:** initial consistent snapshot, then stream from the
  log position captured at snapshot start. Re-snapshot procedure must exist
  (incremental snapshots) for adding tables or recovering from gaps.
- **Deletes & tombstones:** CDC delete events must be **applied** downstream
  (merge-delete or soft-delete flag), and Kafka tombstones (null payloads on
  compacted topics) must be handled by every consumer. A lake table fed by
  CDC where deletes are dropped silently diverges from source = CRITICAL.
- **Apply layer:** CDC streams are change *logs*; downstream either stores
  the log (append, then dedupe/window to current state in SQL) or maintains
  a mirror via MERGE keyed on PK ordered by LSN/commit timestamp. Out-of-order
  application (e.g. merging on wall-clock `updated_at` with ties) silently
  resurrects deleted/stale rows.

```sql
-- GOOD: latest-state mirror from a CDC change log, deletes applied,
-- ordered by log position (LSN), not wall-clock
MERGE INTO mirror.customers t
USING (
  SELECT * FROM cdc.customers_changes
  QUALIFY row_number() OVER (PARTITION BY id ORDER BY source_lsn DESC) = 1
) s ON t.id = s.id
WHEN MATCHED AND s.op = 'd' THEN DELETE
WHEN MATCHED THEN UPDATE SET ...
WHEN NOT MATCHED AND s.op != 'd' THEN INSERT ...;
```
- **Outbox pattern** for application-emitted events (avoiding dual-write
  inconsistency) is owned by [`sota-architecture`](../../sota-architecture/SKILL.md) — use it; don't tail
  business tables to fake events.
- Schema changes on source tables flow through CDC: test ADD COLUMN and
  type-widening paths; alert on incompatible DDL rather than silently
  dropping fields.

## 6. Watermarks, windowing, late data

- **Event time, not processing time,** for any business aggregation.
  Processing-time windows shift numbers whenever the pipeline lags.
- A **watermark** declares "events older than T are no longer expected" and
  triggers window emission. Set allowed lateness from measured event-delay
  distributions (p99/p999), not guesses.
- Decide explicitly what happens to later-than-watermark events: drop +
  count (alert on the count), side-output to a corrections path, or
  re-emit updated window results (consumers must then handle retractions/
  upserts). Silent drop with no metric = HIGH.
- Window types: tumbling for periodic aggregates, sliding for rolling
  metrics, session for activity grouping. State for long/huge windows needs
  TTLs — unbounded keyed state is a slow OOM.

## 7. DLQ & poison messages

- **Every streaming consumer has a poison-message policy.** Default: retry
  N times (with backoff), then route the message + error metadata +
  original topic/partition/offset to a DLQ topic, and continue. A consumer
  that crash-loops on one bad message takes the whole partition hostage =
  HIGH.
- DLQs are monitored (alert on arrival rate) and have a replay path back to
  the source topic after fix. An unmonitored DLQ is a data black hole —
  MEDIUM.
- Never DLQ-and-forget messages whose absence corrupts aggregates; for
  those, halt and page instead (block-tier, by analogy with [rules/04](04-data-quality-and-contracts.md)).

## 8. Backpressure

Consumers must degrade by slowing intake (pause/resume, bounded buffers),
not by buffering unboundedly in memory. Mechanics and patterns are owned by
[`sota-async-concurrency`](../../sota-async-concurrency/SKILL.md); in Kafka terms: bound in-flight work, watch lag as
the system-level backpressure signal, scale consumers before lag approaches
retention.

## Audit checklist

- [ ] Each streaming component has a named consumer/latency requirement, or
      is justified as transport? A streaming job whose only consumer is an
      hourly dashboard = MEDIUM (§1)
- [ ] Partition keys match the entity whose ordering matters (random keys
      where consumers assume per-entity order = CRITICAL); skew checked on
      partition-level lag; partition count sized with headroom and any increase
      planned (it reshuffles key→partition); share groups only on true queue
      workloads (§2)?
- [ ] Offsets committed only after effects are durable; auto-commit
      semantics understood; per-poll work bounded under `max.poll.interval.ms`
      with a cooperative/KIP-848 rebalance protocol (§2)?
- [ ] Sinks idempotent (merge key / transactional offsets) — exactly-once
      claims verified at the sink? Warehouse appends with separately committed
      offsets = CRITICAL if the table feeds metrics (§3)
- [ ] Consumer lag monitored with alerts on all prod groups; retention >
      max tolerable downtime (§2)?
- [ ] Schemas registered with enforced compatibility mode (never `NONE` in
      prod; schemaless JSON topics shared across teams = HIGH); breaking changes
      via new topic/version; new fields carry defaults; no reused Protobuf/Avro
      field IDs or positions (§4)?
- [ ] CDC: log-based for sources with deletes; deletes/tombstones applied
      downstream (dropped deletes = CRITICAL); ordering by LSN not wall-clock;
      re-snapshot path exists; incompatible source DDL alerts rather than
      silently dropping fields; no business tables tailed to fake events (§5)?
- [ ] CDC replication slots ("CDC patterns" above) — on the source, `SELECT slot_name, active, wal_status,
      pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) FROM pg_replication_slots;`
      — an inactive slot no connector owns, or `max_slot_wal_keep_size = -1` with no slot-lag
      alert = HIGH (the source disk fills) (§5)
- [ ] Aggregations on event time with explicit watermark/lateness policy,
      allowed lateness set from measured event-delay p99/p999; late-drop
      counted and alerted (silent drop = HIGH) (§6)?
- [ ] DLQ per consumer, monitored (alert on arrival rate), with replay
      procedure; no crash-looping on poison messages (HIGH); messages whose
      absence corrupts aggregates halt and page instead of being DLQ'd (§7)?
- [ ] Keyed state has TTLs (§6); consumer memory bounded under lag:
      in-flight work bounded (pause/resume, bounded buffers), consumers scaled
      before lag approaches retention (§8)?
