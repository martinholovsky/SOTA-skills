# 08 — NATS JetStream

Scope: building on or auditing NATS JetStream as a primary message bus (Go
services). The general distributed-messaging doctrine of **rules/03** —
exactly-once is a myth, ack after durable commit, outbox/never-dual-write, DLQs,
ordering, schema evolution, claim-check, idempotent consumers — applies in full
and is **not repeated here**. This file maps that doctrine onto JetStream's
concrete mechanisms and flags JetStream-specific failure modes. Consumer-loop
and backpressure mechanics live in **sota-async-concurrency**; TLS/mesh/leafnode
transport security in **sota-network-security**; NKEY/JWT/account auth in
**sota-identity-access** and **sota-secrets-management**.

Version: written against **NATS Server 2.11/2.12**; 2.14 has since superseded
2.12 (2.13 was skipped; 2.12.x continues as a maintenance line) — run the
latest stable release and verify the current line with a quick web search at
time of use. KV and Object stores are GA and JetStream-backed. The `jetstream`
Go package is the current API; the older `nc.JetStream()` JetStreamContext is
legacy. Pin and track your server line — per-message TTL, KV limit markers, and
the message scheduler are recent additions gated on server API level.

## Core NATS vs JetStream: choose per subject, not per cluster

### Rule: Use core NATS for fire-and-forget; reach for JetStream only when you need persistence, replay, or dedup.
- **Core NATS** (plain `nc.Publish`/`Subscribe`, request-reply, queue groups) is
  at-most-once: no subscriber online means the message is gone. Correct for RPC,
  health pings, cache invalidations, ephemeral fan-out — anything where loss is
  acceptable and latency is king.
- **JetStream** adds a persistent log with acks, replay, and publish-dedup. Use
  it when a missed message is a bug: orders, state changes, work queues, audit.
- Request-reply (`nc.Request`) and **queue groups** (load-balanced delivery to a
  named group of subscribers) are core-NATS primitives — you do not need
  JetStream for competing consumers on transient work. Putting RPC traffic
  through a stream is a common over-reach: it pays the storage/ack cost for
  no benefit.
- "Exactly-once" on JetStream is **dedup-on-publish + idempotent consumption**,
  not a delivery guarantee (rules/03 §3). Do not design as if it were one.

## Subject design: the schema of your whole bus

### Rule: Design the subject hierarchy deliberately; tokens are your routing and authz surface.
- Dot-separated tokens, hierarchy from general to specific:
  `orders.eu.created`, `orders.eu.shipped`. Tokens are the unit of wildcard
  matching and of account permissions — design them so a single subject pattern
  grants exactly the access a service needs.
- Wildcards: `*` matches one token, `>` matches one-or-more trailing tokens.
  `orders.*.created` = any region's created events; `orders.>` = everything
  under orders. A consumer filtering on `>` at the top of a busy stream is a
  firehose — filter as specifically as the work requires.
- One stream binds a set of subjects; a subject belongs to **one stream** (two
  streams capturing the same subject double-store and confuse consumers). Map
  subjects→streams on paper before creating either.
- **Subject transforms** (`SubjectTransform`, and per-source transforms) rewrite
  subjects on ingest or when sourcing — use for namespacing aggregated streams
  (`orders.>` → `agg.orders.>`), not as a substitute for getting the producer's
  subjects right.

## Streams: an unbounded stream is a latent outage

### Rule: Every stream has explicit limits. No max-bytes and no max-age = a disk-fill incident waiting to happen.
- Set `MaxBytes` and `MaxAge` on every stream, sized to retention need and disk.
  `MaxMsgs`, `MaxMsgsPerSubject`, and `MaxMsgSize` as the workload requires.
  A stream with all limits unset grows until the file store fills and the node —
  and its RAFT peers — degrade. This is the JetStream form of rules/03's
  "bounded queues everywhere"; treat unbounded as **High**.
- **Storage**: `FileStorage` (default, durable, survives restart) for anything
  that matters; `MemoryStorage` only for fast, loss-tolerant, regenerable data.
- **Retention policy** — pick by consumption shape:
  - `LimitsPolicy` (default): messages kept until a limit evicts them;
    many independent consumers replay the same log. Use for event streams.
  - `WorkQueuePolicy`: each message consumable exactly once, removed on ack;
    a true job queue. Requires non-overlapping consumer filter subjects.
  - `InterestPolicy`: message retained only while a bound consumer hasn't acked
    it; storage tracks consumer interest. Use when you want event semantics but
    automatic cleanup once all known consumers have processed.
- **Discard policy**: `DiscardOld` (default — evict oldest to make room) for
  logs where newest matters; `DiscardNew` (reject the publish) when losing old
  data is unacceptable and you want the producer to feel backpressure. Pair
  `DiscardNew` with `DiscardNewPerSubject` + `MaxMsgsPerSubject` to bound each
  subject independently.

```text
GOOD (bounded, durable, work queue):
  nats stream add ORDERS \
    --subjects 'orders.>' --storage file --retention work \
    --discard new --max-bytes 10GB --max-age 720h \
    --max-msgs-per-subject 1000 --replicas 3 --dupe-window 2m

BAD: nats stream add ORDERS --subjects 'orders.>' --storage file
     # no max-bytes, no max-age, no replicas, R1 → unbounded + no HA
```

### Rule: R3 for anything you can't afford to lose; R1 is dev-only. Mirrors/sources for aggregation, not HA.
- `Replicas: 3` (R3) gives a per-stream RAFT group that survives one node loss.
  R1 has no redundancy — a single disk failure loses the stream. Production
  durable streams are R3 (or R5 across failure zones); `--replicas 1` in prod is
  **High**. Use `Placement` (cluster + tags) to pin streams to the right
  hardware/zone.
- **Mirrors** (`Mirror`) are a read-only 1:1 copy of one origin stream — for
  fan-out reads, backup, or cross-region read replicas. **Sources** (`Sources`)
  aggregate many streams into one (fan-in, cross-region roll-up), with optional
  per-source subject transforms and filters. Neither is a substitute for R3:
  they copy asynchronously and lag; HA is replicas, aggregation is mirrors/sources.

## Publish & idempotent dedup: the duplicate window

### Rule: Publishers set `Nats-Msg-Id`; the stream's duplicate window dedups. This is the publish half of effectively-once.
- JetStream publish is at-least-once: a publish ack can be lost and the client
  retries, producing a duplicate. Set the **`Nats-Msg-Id`** header to a stable
  business id; the stream rejects a second message with the same id seen within
  its **duplicate window** (`Duplicates`/`--dupe-window`, default 2 minutes).
- Size the window to your **maximum publish-retry horizon**, not larger — the
  window is held in memory; large windows cost RAM. If a retry can arrive 10
  minutes later, a 2-minute window won't dedup it; if retries resolve in seconds,
  don't set hours.
- **Always check the publish ack.** Use `js.Publish` (sync — blocks for the ack)
  or `js.PublishAsync` with a **bounded** in-flight window (`PublishAsyncMaxPending`)
  and drain/await before considering messages durable. Ignoring the ack is silent
  message loss — the rules/03 "no dual-write / confirm the write" rule applied to
  the publish path; treat fire-and-forget JetStream publishing as **High**.
- This is only half of effectively-once. The other half is **idempotent /
  de-duplicated consumption** (rules/03 §2) — the duplicate window does nothing
  for duplicates a consumer sees from redelivery.

```go
js, _ := jetstream.New(nc)
ack, err := js.Publish(ctx, "orders.eu.created", payload,
    jetstream.WithMsgID(order.ID)) // dedup key; checked vs the stream's window
if err != nil { return err }       // NOT durable until ack returns without error
_ = ack.Sequence
```

## Consumers: pull is the modern default; explicit ack after processing

### Rule: Use durable pull consumers via the `jetstream` package. Push and JetStreamContext are legacy.
- The `github.com/nats-io/nats.go/jetstream` package is the current API. Create a
  consumer, then pull with `Consume` (callback, continuous), `Messages`
  (iterator), or `Fetch` (explicit batch). The older `nc.JetStream()`
  JetStreamContext + `Subscribe` is legacy — don't write new code against it.
- **Durable** (named, `Durable`/explicit name) for work that must resume where it
  left off after restart; **ephemeral** for throwaway tail-follows. An ephemeral
  consumer for durable work loses its position on disconnect — **High** for any
  at-least-once job (rules/03 anti-pattern).
- **`AckExplicit`** (default and correct): ack **after** the state change is
  durably committed (rules/03 §3). `AckNone` and `AckAll` discard the
  per-message safety net; ack-on-receipt before processing loses messages on
  crash — never do it.
- For stronger guarantees use **double-ack** (`msg.DoubleAck(ctx)`/`AckSync`):
  the client waits for the server to confirm the ack landed, closing the window
  where a lost ack causes redelivery of an already-processed message.

### Rule: `MaxAckPending` is your primary backpressure knob; `MaxDeliver` bounds poison redelivery.
- **`MaxAckPending`**: the cap on un-acked in-flight messages per consumer — the
  JetStream analogue of AMQP prefetch (rules/03 §7b). Unbounded (`-1`) lets a
  slow consumer pull more than it can process; set it explicitly, sized to
  handler throughput (sota-async-concurrency rules/06). Unbounded `MaxAckPending`
  on a real consumer is **High**.
- **`AckWait`**: how long the server waits for an ack before redelivering. Size
  it above your worst-case processing time, or in-flight work gets redelivered
  while still running. Send `msg.InProgress()` to extend it for long handlers.
- **`MaxDeliver`**: cap redelivery attempts. **Unset (infinite) means a poison
  message redelivers forever**, burning a consumer slot and CPU — rules/03's
  poison-vs-transient rule, and **High** here. Set `MaxDeliver` and a `BackOff`
  array (per-attempt delays) so transient failures retry with growing spacing.
- **`FilterSubjects`** (multi-filter supported) narrows a consumer to the
  subjects it handles — essential for `WorkQueuePolicy` streams, where consumer
  filters must not overlap.
- **`DeliverPolicy`**: `DeliverAll` (replay from start), `DeliverNew` (only new),
  `DeliverByStartSequence`/`DeliverByStartTime` (replay from a point),
  `DeliverLastPerSubject` (latest per subject — current-state bootstrap).
  **`ReplayPolicy`**: `ReplayInstant` (default) or `ReplayOriginal` (reproduce
  original inter-message timing).
- **Ordered consumers** (`OrderedConsumer`) give a single client an in-order,
  gap-detecting replay that auto-recreates on error — use for single-consumer
  projections/replay, not for scaled competing-consumer work.

```go
cons, _ := stream.CreateOrUpdateConsumer(ctx, jetstream.ConsumerConfig{
    Durable:       "orders-projector",
    AckPolicy:     jetstream.AckExplicitPolicy,
    AckWait:       30 * time.Second,
    MaxDeliver:    5,
    MaxAckPending: 256,                       // backpressure
    FilterSubjects: []string{"orders.eu.>"},
    BackOff:       []time.Duration{1*time.Second, 5*time.Second, 30*time.Second},
})
cc, _ := cons.Consume(func(msg jetstream.Msg) {
    if err := process(ctx, msg); err != nil { // do the work first
        _ = msg.NakWithDelay(5 * time.Second) // transient: retry later
        return
    }
    _ = msg.DoubleAck(ctx)                     // commit only after success
})
defer cc.Stop()
// BAD: msg.Ack() before process()  → crash = silent loss (rules/03 §3)
```

## Error handling: ack/nak/term/inprogress, and the DLQ you must build

### Rule: JetStream has no built-in DLQ. Route poison messages out yourself after `MaxDeliver`.
- The four dispositions:
  - **Ack** — processed successfully and committed; remove from redelivery.
  - **Nak** (`Nak`/`NakWithDelay`) — transient failure; redeliver (with delay).
  - **Term** (`Term`) — permanently unprocessable (poison); stop redelivery
    immediately, do **not** wait out `MaxDeliver`. Use it the moment you know a
    message will never succeed (schema-invalid, references a deleted entity).
  - **InProgress** — still working; reset the `AckWait` timer.
- Distinguish transient from poison (rules/03 §7): `Nak` transient, `Term`
  poison. Don't `Nak` a poison message `MaxDeliver` times — that's the redelivery
  storm rule.
- Because there's no native dead-letter, build one: subscribe to the advisory
  **`$JS.EVENT.ADVISORY.CONSUMER.MAX_DELIVERIES.>`** and republish the exhausted
  message to a dedicated **DLQ stream**, or have the handler republish on its
  final attempt. Then apply rules/03 §7 in full: alert on DLQ depth > 0, and have
  a tested redrive runbook. A DLQ nobody drains is a data-loss buffer.
- Consumers must be **idempotent** regardless (rules/03 §2): redelivery after a
  lost ack, double-ack timeout, or `AckWait` expiry will hand you the same
  message again.

## KV & Object stores: config, coordination, and the claim-check

### Rule: Use JetStream KV for config/locks/dedup-state; Object store for large blobs (claim-check).
- **KV** is a JetStream-backed bucket (GA). Each key is versioned with a
  monotonic **revision**; do optimistic concurrency with **compare-and-set**
  (`Update` against an expected revision — rejects if the key moved under you),
  the rules/03 §12 "let the store arbitrate" pattern without a separate lock
  service. **Watchers** stream changes (config hot-reload, coordination);
  **history** keeps N prior revisions (bucket `History`, default 1).
- NATS KV is a good fit for **token revocation** lists and similar hot lookups:
  fast reads, watch-driven propagation, CAS for safe updates.
- KV TTL: bucket-level TTL is long-standing; **per-key TTL** is newer (NATS 2.11+,
  via per-message TTL / `Nats-TTL` and KV limit markers) — verify your server
  supports it before relying on it, and note the stream's `MaxAge` still takes
  precedence over a per-key TTL. Don't assume per-key expiry on an older server.
- **Object store** holds large payloads. Apply rules/03's **claim-check**: keep
  big blobs and secrets out of messages; publish a reference (object id/bucket),
  let the consumer fetch from the object store. The bus is a shared failure
  domain, not a file server — fat messages saturate streams and replication.

## Clustering, HA & multi-tenancy: accounts are the isolation boundary

### Rule: Accounts isolate tenants; domains/leafnodes bridge edge↔hub; per-account quotas bound blast radius.
- JetStream runs a cluster-wide **meta RAFT** group plus a per-stream/per-consumer
  RAFT group; leaders are elected per group. R3 streams tolerate one node loss.
- **Accounts** are the hard multi-tenant boundary: separate subject space, separate
  JetStream assets, no cross-account visibility except via explicit subject
  exports/imports. Multi-tenant systems isolate tenants by **account**, not by
  subject-prefix convention within one account (rules/05 tenancy discipline) —
  subject-prefix-only "isolation" is a cross-tenant leak risk: **High**.
- Set **per-account JetStream limits/quotas** (max memory, max file store, max
  streams/consumers) so one tenant can't exhaust the cluster — the rules/04
  bulkhead applied to storage.
- **Leafnodes** extend a cluster to the edge; **gateways/superclusters** connect
  clusters across regions; **JetStream domains** name an isolated JetStream
  instance (e.g. an edge leafnode hub) so edge and hub streams don't collide and
  can be addressed/mirrored explicitly. Use domains for edge↔hub topologies.
- Auth and transport are out of scope here: NKEY/JWT and account design live in
  **sota-identity-access**/**sota-secrets-management**; TLS, leafnode/gateway
  transport security, and mesh in **sota-network-security**. JetStream over a
  cluster with no TLS and a shared account is not production-ready.

## Operations: monitor lag, snapshot, drain

### Rule: Watch consumer lag and ack-pending; back up streams; drain on shutdown.
- Monitor per consumer: **`num_pending`** (unprocessed backlog),
  **`num_ack_pending`** (in-flight un-acked), **`redelivered`** count, and stream
  bytes vs `MaxBytes`. `num_pending` climbing monotonically = under-provisioned
  consumer or a poison loop (rules/03 §7). Alert on it.
- `nats stream report` and `nats consumer report` are the first-line operability
  tools; advisories on `$JS.EVENT.ADVISORY.>` surface max-deliveries, terminated
  messages, and leader elections. Export metrics vendor-neutrally (the server's
  monitoring endpoints / `nats-surveyor`) into whatever scrapes them — keep the
  collection stack out of the design.
- **Snapshot/restore**: streams support snapshot/backup and restore — schedule
  them, store off-cluster, and rehearse restore (rules/03 / sota-databases
  backup discipline). Replicas are HA, not backup.
- **Graceful drain**: on shutdown call `Stop`/`Drain` on consume contexts and
  `nc.Drain()` so in-flight messages finish and acks flush rather than being cut
  mid-process and redelivered (sota-async-concurrency graceful-shutdown).
- Don't block the consume callback: offload slow work and let `MaxAckPending`
  bound concurrency (sota-async-concurrency rules/06). A blocking callback stalls
  delivery and inflates ack-pending.

## Anti-patterns (JetStream-specific)

- **Unbounded stream** — no `MaxBytes`/`MaxAge`: disk fills, RAFT peers degrade.
- **No `MaxDeliver`** — a poison message redelivers forever (rules/03 §7).
- **Ack before processing** / `AckNone` on durable work — silent loss on crash.
- **One giant catch-all stream** (`>` over everything) — couples unrelated
  workloads, breaks per-subject limits and per-consumer reasoning; the rules/07
  "god service" smell in stream form.
- **At-least-once publisher with no dedup** — no `Nats-Msg-Id`/duplicate window,
  so publish retries duplicate silently.
- **Ephemeral consumer for durable work** — loses position on disconnect.
- **Unbounded `MaxAckPending`** — no consumer backpressure; slow consumer OOMs.
- **Ignored publish acks** — fire-and-forget JetStream publish = silent loss.
- **Subject-prefix "tenancy"** in one account instead of per-account isolation.
- **Blocking the consume callback** — stalls delivery (sota-async-concurrency).

## Audit checklist

- [ ] Is core NATS used for fire-and-forget/RPC and JetStream reserved for
      persistence/replay/dedup, rather than RPC pushed through streams?
      (`nats stream ls`; look for streams capturing request-reply subjects.)
- [ ] Does **every** stream set `MaxBytes` and `MaxAge` (and per-subject limits
      where relevant)? (`nats stream info <s>` → Limits; grep IaC/config for
      stream definitions missing `max_bytes`/`max_age`.)
- [ ] Are durable production streams **R3+**? Any `--replicas 1` / `Replicas: 1`
      outside dev? (`nats stream report` shows replica counts.)
- [ ] Is retention policy correct for the access pattern (work queue vs limits vs
      interest), and `DiscardNew` used where old-data loss is unacceptable?
- [ ] Do publishers set **`Nats-Msg-Id`** and is the **duplicate window** sized to
      the retry horizon? (grep for `WithMsgID`/`Nats-Msg-Id`; `nats stream info`
      → Duplicate Window.)
- [ ] Are publish acks checked — `js.Publish` sync, or `PublishAsync` with bounded
      pending and a drain/await? Any fire-and-forget publishes? (grep `PublishAsync`
      without `PublishAsyncMaxPending`/await.)
- [ ] Are consumers **durable pull** via the `jetstream` package, not ephemeral
      and not legacy `JetStreamContext`/`Subscribe` for durable work? (grep
      `nc.JetStream(`, `.Subscribe(` in JS paths.)
- [ ] Is `AckPolicy` **explicit**, with ack/DoubleAck **after** the commit, never
      before processing and never `AckNone` on durable work? (read the consume
      callback; ack should be the last successful step.)
- [ ] Is `MaxAckPending` set (not `-1`) and sized to handler throughput?
      (`nats consumer info` → Max Ack Pending.)
- [ ] Is `MaxDeliver` bounded with a `BackOff`, and poison `Term`ed (not `Nak`ed
      to exhaustion)? (grep `MaxDeliver`; consumer config; advisory consumers.)
- [ ] Is there a **DLQ stream** fed by `MAX_DELIVERIES` advisories or a final-attempt
      republish, with depth alerting and a redrive runbook? (`nats stream ls` for a
      DLQ/dead-letter stream; subscriber on `$JS.EVENT.ADVISORY.CONSUMER.MAX_DELIVERIES.>`.)
- [ ] Are consumers idempotent under redelivery (rules/03 §2)?
- [ ] KV: optimistic concurrency via revision CAS (`Update`), not blind `Put`,
      for contended keys (token revocation, locks)? Per-key TTL only relied on if
      the server supports it? (`nats kv ls`; grep `kv.Update` vs `kv.Put`.)
- [ ] Large payloads via Object store claim-check, not inline in messages?
      (`nats object ls`; check message sizes / `MaxMsgSize`.)
- [ ] Multi-tenant isolation by **account** (with per-account JetStream quotas),
      not subject-prefix convention in a shared account? (server/account config.)
- [ ] Edge↔hub topologies use leafnodes + **JetStream domains**; TLS and
      NKEY/JWT auth in place (defer to network-security / identity-access)?
- [ ] Monitoring on `num_pending`/`num_ack_pending`/`redelivered` with lag
      alerts; stream snapshots scheduled and restore-rehearsed; graceful
      `Drain` on shutdown? (`nats consumer report`; check shutdown path.)
