# 03 — Streaming & CDC

Streaming is the most expensive way to move data. It buys latency and pays
in operational complexity, harder testing, and harder reprocessing. Make it
earn its place.

## When streaming is justified

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

## Kafka-style log fundamentals

(Kafka 4.x is current — ZooKeeper is gone, KRaft-only; the KIP-848 consumer
rebalance protocol is GA in 4.0+ and consumers opt in via
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

## Exactly-once reality

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

## Schema registry & evolution

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

## CDC patterns

- **Log-based CDC (Debezium-class, 3.x current) is the default** for
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
  inconsistency) is owned by `sota-architecture` — use it; don't tail
  business tables to fake events.
- Schema changes on source tables flow through CDC: test ADD COLUMN and
  type-widening paths; alert on incompatible DDL rather than silently
  dropping fields.

## Watermarks, windowing, late data

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

## DLQ & poison messages

- **Every streaming consumer has a poison-message policy.** Default: retry
  N times (with backoff), then route the message + error metadata +
  original topic/partition/offset to a DLQ topic, and continue. A consumer
  that crash-loops on one bad message takes the whole partition hostage =
  HIGH.
- DLQs are monitored (alert on arrival rate) and have a replay path back to
  the source topic after fix. An unmonitored DLQ is a data black hole —
  MEDIUM.
- Never DLQ-and-forget messages whose absence corrupts aggregates; for
  those, halt and page instead (block-tier, by analogy with rules/04).

## Backpressure

Consumers must degrade by slowing intake (pause/resume, bounded buffers),
not by buffering unboundedly in memory. Mechanics and patterns are owned by
`sota-async-concurrency`; in Kafka terms: bound in-flight work, watch lag as
the system-level backpressure signal, scale consumers before lag approaches
retention.

## Audit checklist

- [ ] Each streaming component has a named consumer/latency requirement, or
      is justified as transport?
- [ ] Partition keys match the entity whose ordering matters; skew checked?
- [ ] Offsets committed only after effects are durable; auto-commit
      semantics understood?
- [ ] Sinks idempotent (merge key / transactional offsets) — exactly-once
      claims verified at the sink?
- [ ] Consumer lag monitored with alerts on all prod groups; retention >
      max tolerable downtime?
- [ ] Schemas registered with enforced compatibility mode; breaking changes
      via new topic/version?
- [ ] CDC: log-based for sources with deletes; deletes/tombstones applied
      downstream; ordering by LSN not wall-clock; re-snapshot path exists?
- [ ] Aggregations on event time with explicit watermark/lateness policy;
      late-drop counted and alerted?
- [ ] DLQ per consumer, monitored, with replay procedure; no crash-looping
      on poison messages?
- [ ] Keyed state has TTLs; consumer memory bounded under lag?