# 03 — Distributed Systems, Messaging & Eventing

Rules for any system where two components are separated by a network. The
network will partition, messages will duplicate and reorder, clocks will lie.
Design for that on day one; it cannot be patched in later.

## 1. CAP/PACELC: pick trade-offs per operation, not per system

**Rule:** During a partition you choose consistency or availability; even
without a partition you choose latency or consistency (PACELC). Make the choice
*per operation*, write it down (ADR), and verify the datastore's defaults match.
"We use a CP database" is not a design; "balance reads are linearizable,
product-view reads are eventually consistent with ≤5 s staleness" is.

**Rule:** Never assume read-your-writes across replicas or caches. If a flow
needs it (user saves, next page shows the save), engineer it explicitly: sticky
session to primary, version-pinned reads, or write-through cache.

**Rule:** Distrust distributed transactions (2PC/XA) across heterogeneous
systems. Coordinators block on failure and availability collapses to the worst
participant. Prefer sagas (§5) and the outbox (§4).

## 2. Idempotency is mandatory, everywhere

**Rule:** Every message handler, every retried API call, and every job must be
safe to execute at least twice. Delivery guarantees are at-least-once in
practice (§3), so non-idempotent consumers corrupt data — it's a when, not an if.

**Mechanisms, in order of preference:**
1. Naturally idempotent operations (`set status = 'shipped'`, upsert by key).
2. Idempotency key: caller supplies a key; handler records `(key → result)` and
   replays the stored result on duplicates. Store key + result *in the same
   transaction* as the state change.
3. Version/sequence checks: reject events older than current aggregate version.

```text
GOOD (dedupe inside the TX):
  BEGIN
    INSERT INTO processed(msg_id) VALUES ($id)   -- unique constraint
      ON CONFLICT DO NOTHING; IF no row inserted: ROLLBACK, ACK, return
    ...apply state change...
  COMMIT; ACK

BAD: if redis.exists(msg_id): skip      -- check and write not atomic;
     apply(); redis.set(msg_id)         -- crash between = duplicate apply
```

**Rule:** Public write APIs accept an `Idempotency-Key` header (or equivalent)
and document retention. Payment-ish operations without idempotency keys are a
Critical finding.

## 3. Exactly-once delivery is a myth; exactly-once *processing* is yours to build

**Rule:** No broker gives you end-to-end exactly-once across your database and
side effects. "Exactly-once" broker features (Kafka transactions) cover
broker-internal read-process-write only. Your contract is: at-least-once
delivery + idempotent processing = effectively-once outcomes. Any design doc
that depends on exactly-once delivery is wrong; fix the design, not the broker.
On NATS JetStream (dedup window, ack semantics, stream limits): [rules/08](08-nats-jetstream.md).

**Rule:** Acknowledge messages only after the state change is durably committed.
Ack-then-process loses messages on crash; process-then-ack duplicates them —
which is fine, because §2.

## 4. Outbox pattern: never dual-write

**Rule:** Never write to your database and publish to a broker as two separate
operations — a crash between them either loses the event or emits a phantom.
Write the event into an `outbox` table in the same transaction as the state
change; a relay (poller or CDC e.g. Debezium) publishes from the outbox.

```text
BEGIN
  UPDATE orders SET status='placed' WHERE id=$1;
  INSERT INTO outbox(event_id, type, payload, created_at) VALUES (...);
COMMIT
-- relay: SELECT unpublished → publish → mark published (at-least-once; consumers dedupe)
```

**Rule:** The same applies inbound: to atomically consume and act, use an inbox
table (record msg_id + effects in one TX), then ack.

## 5. Sagas for cross-service workflows

**Rule:** A business transaction spanning services is a saga: a sequence of
local transactions, each with a **compensating action** for rollback. Define
compensations at design time; a saga step without a compensation (or an explicit
"pivot — no return past this point" marker) is undesigned failure handling.

**Orchestration vs choreography:**
- **Orchestrate** (explicit coordinator / workflow engine: Temporal, Step
  Functions, or a state-machine table) when steps ≥ 3, ordering matters, or you
  need to answer "where is order 123 stuck?". Default choice.
- **Choreograph** (each service reacts to events) only for short, stable, 2–3
  step flows. Beyond that, the workflow exists only in engineers' heads —
  unauditable and undebuggable.

**Rule:** Compensations are not undo. `cancelReservation` after `reserveStock`
must handle "stock already shipped". Compensations are themselves idempotent,
retried, and may need their own compensations escalated to humans (incident
queue), which must be designed, not improvised.

**Rule:** Every saga has a timeout and a terminal failure state visible in
monitoring. Sagas stuck "in progress" for hours are a High finding.

**Rule:** Order the steps so a partial completion leaves the *conservative*
state — take value out of the source first, put it into the destination last.
Debit then credit; consume the coupon then grant the discount; decrement stock
then confirm the order; revoke the old grant then issue the new one. A crash
between legs then leaves value **missing**, which compensation or retry can
recover, instead of value **duplicated**, which nothing recovers once the
destination has spent it. Credit-first is defensible only when the credited
resource provably cannot be consumed before the saga reaches its terminal state
— and that must be *enforced* (a pending/held balance excluded from the
spendable one), never assumed. The cost is real: debit-first strands the payer's
value while the saga is in flight, which is why the timeout-to-terminal-state
above and a user-visible pending status are part of this rule, not extras.

## 5b. Reconciliation: the completeness check on an external integration

**Rule:** Where an external system holds authoritative state that you also
record — payment processor, exchange, carrier, billing vendor, another team's
service — the two records *will* diverge: a webhook is dropped, a call times out
after the far side committed, a retry posts twice. Idempotency and retries bound
the damage; neither tells you a divergence happened. A periodic reconciliation
does. On a money-, inventory-, or entitlement-bearing integration, its absence
is a High finding. Note what this is: §2–§4 give you *integrity* — each record
you wrote is correct. Reconciliation is the only thing that gives you
**completeness** — that no record is missing.

**Rule:** Reconcile against the counterparty's own extract, not against your own
records. Their settlement file, statement, or list endpoint is an independent
observation; recomputing your database from your own event log proves internal
consistency and says nothing about the seam. Where they publish no extract, the
paginated read API over the period is the substitute — the same call the webhook
was meant to save you (webhook senders owe consumers exactly this, see
[`sota-api-design` rules/06](../../sota-api-design/rules/06-webhooks.md)).

**Rule:** Classify breaks; a count alone is not a result. Three buckets with
three different actions: **(a)** known shape, safe to adjust by a written rule —
automate it, and log every adjustment; **(b)** known shape, needs a human —
queue it; **(c)** unclassified — page someone, because an unclassified break is
indistinguishable from a bug still producing them. An automated (a) adjustment
on a money path posts as a reversing ledger entry, never an in-place correction
([`sota-databases` rules/01](../../sota-databases/rules/01-choosing-and-modeling.md)). Breaks also **age**: alert on the oldest unresolved
break, not only on the count, or one permanently stuck break becomes background
noise that hides the next twenty.

**Rule:** A reconciliation that has never reported a break is not evidence of
correctness — it is the inert-control signature. Print the denominator (rows
compared on *each* side, and the period covered), fail closed when either side
reads zero, and prove it can fire by seeding a known break. Diagnostics:
[`sota-code-security` rules/11](../../sota-code-security/rules/11-dead-path-diagnostics.md) §2.2 and [rules/15](../../sota-code-security/rules/15-instruments-and-guards.md).

## 6. Event-driven architecture: events are facts

**Rule:** An event states a fact that happened (`PaymentCaptured`), in past
tense, owned by the producer. A command requests work (`CapturePayment`), owned
by the consumer. Don't disguise commands as events ("EmailShouldBeSent") — that
inverts ownership and creates hidden coupling.

**Rule:** Producers don't know consumers. If producer code must change when a
consumer is added, you have RPC over a message bus, not eventing.

**Rule:** Consumers must tolerate: duplicates (§2), reordering (use aggregate
version numbers or partition-key ordering, never wall-clock timestamps), and
unknown fields (forward-compatible deserialization).

**Rule:** Use CQRS only where read and write shapes genuinely diverge (complex
domains, heavy read fan-out, projections per consumer). CQRS does not require
event sourcing; start with "write model + projected read tables". Event sourcing
is a Type 1 decision — adopt only with replay/audit requirements and ops
capacity for snapshotting, upcasting, and GDPR-compliant deletion (crypto-
shredding), each of which must be designed before adoption.

**Rule (the precondition replay quietly assumes):** rebuilding state means re-running the
**apply** step over old events, so that step must be a **pure function of (state, event)**.
Every non-deterministic input it touches — the wall clock, a random or UUID generator, a
config lookup, a call to another service — makes the rebuilt state differ from the
original, silently and without an error. The classic case is an external query: *"if I ask
for an exchange rate on December 5th and replay that event on December 20th, I will need
the exchange rate on Dec 5"* (Fowler, *Event Sourcing*). Two remedies, and you need both:
**capture the answer in the event** (the rate, the generated id, the timestamp — resolved
once, at command time), and **gate outbound effects during replay** so a rebuild does not
re-send emails or re-charge cards. A gateway that cannot be switched into replay mode is a
replay you can only run in a scratch environment, which is the same as not having one.

**Rule:** the **event log is the durable record; commands are not.** A command is a
*request* that may be rejected, deduplicated, or rewritten; the event is what actually
happened. So the durability, retention and backup budget belongs to the event store, and a
lost command is a retry while a lost event is unrecoverable state. If your design gives
commands the stronger guarantee, the roles have been swapped.

## 7. Queues: DLQs, ordering, backpressure

**Rule:** Every queue/subscription has: a max-retry policy with backoff, a
dead-letter queue, an alert on DLQ depth > 0, and a documented + tested
redrive procedure. A DLQ nobody drains is a data-loss buffer with extra steps.

**Rule:** Distinguish poison messages (malformed/bug — will never succeed; DLQ
immediately after schema validation fails) from transient failures (dependency
down; retry with backoff). Retrying poison messages 10 times just delays the DLQ
and burns ordering.

**Rule:** Ordering is per-partition-key only. Pick the partition key = the
entity whose events must be ordered (order_id, account_id). Global ordering
doesn't scale; don't design flows that require it.

**Rule:** Backpressure is designed, not discovered:
- Bounded queues everywhere (unbounded queues turn overload into OOM + huge latency).
- Consumers pull at their own rate; producers get pushback (block, shed, or buffer-with-bound).
- Define the overload policy per queue: shed lowest-priority work first (see [rules/04](04-resilience-and-failure-design.md) §6).
- Monitor consumer lag with alerts; lag growing monotonically = under-provisioned consumer or poison loop.

**Rule:** In a multi-tenant system a shared queue or topic is **not** an isolation
boundary — the application has to carry the boundary through it. Classify every job
type as *global*, *tenant-scoped* or *explicitly cross-tenant*, and write the class
down beside the handler. For tenant-scoped work:
- Bind the tenant to the message from the authenticated producer (trusted routing or
  signed metadata), and at the consumer re-establish that context and re-authorize —
  a `tenant_id` field in the body is a claim, not proof ([`sota-code-security` rules/03](../../sota-code-security/rules/03-authorization.md) §8).
- Put the tenant into every per-message key: the dedup/idempotency key (§2), retry
  state, the partition key where order matters per tenant, and who may read or redrive
  the DLQ. Unscoped, tenant B's message is dropped as a duplicate of tenant A's, and a
  DLQ viewer sees every tenant's payloads.
- Global and cross-tenant jobs run under an explicit **system identity** with its own
  grants, never under a made-up tenant (`tenant_id = "system"`), which every
  tenant-scoped check then either rejects or, worse, accepts.
Per-tenant quotas on the shared fleet: [rules/05](05-scalability-state-and-data.md) §7. OWASP: Multi Tenant Security
cheat sheet.

## 7b. Broker queues (AMQP/RabbitMQ): semantics the log model misses

AMQP-style brokers delete on ack and *push* to consumers — different failure
modes than Kafka-style logs:

**Rule:** Manual ack only after the state change is durably committed (§3
applied to AMQP) — never auto-ack: messages count as delivered once written to
the TCP socket, so a consumer crash under auto-ack loses them silently. With
manual acks, unacked deliveries requeue on channel/connection close — which is
why §2 idempotency is mandatory here too.

**Rule:** Nack/requeue is a decision, not a reflex. Requeue only transient
failures; every consumer requeueing the same delivery is a redelivery storm
(CPU + bandwidth burn). Poison messages are rejected with `requeue=false` to a
dead-letter exchange after validation fails (§7), with redelivery count bounded.

**Rule:** Consumer prefetch (`basic.qos`) is the backpressure knob. AMQP pushes,
so the cap on unacked deliveries is your only bound; unset/0 = unlimited
prefetch = an unbounded buffer in the consumer (and memory growth on the node).
Set it explicitly: ~100–300 for fast handlers, low single digits for heavy
ones ([sota-async-concurrency rules/06](../../sota-async-concurrency/rules/06-backpressure-flow-control.md)).

**Rule:** Claim-check pattern: messages carry references (entity IDs,
object-store URLs), never large blobs and never secrets — the broker is a
shared failure domain, not storage. Payloads stay small, schema'd (§8), with
correlation IDs (§9).

**Rule:** Quorum queues are the default for anything that must survive node
loss. Classic queue mirroring was removed in RabbitMQ 4.0; classic queues are
single-replica now. Quorum queues default to delivery-limit 20 — messages
exceeding it are dead-lettered or *dropped*, so configure the DLX target; and
default dead-lettering is at-most-once — where DLQ loss is unacceptable, set
`dead-letter-strategy: at-least-once` + `overflow: reject-publish`.

**Rule:** Broker hardening in one line: per-service users, vhost isolation,
least-privilege configure/write/read permissions, TLS, and no default `guest`
account beyond localhost dev — details in [sota-cloud-infrastructure](../../sota-cloud-infrastructure/SKILL.md) and
[sota-secrets-management](../../sota-secrets-management/SKILL.md).

## 8. Contracts and schema evolution

**Rule:** Every cross-service message and API has an explicit, versioned schema
(OpenAPI, protobuf, Avro/JSON Schema in a registry) with compatibility checks in
CI. Changes are additive by default (expand/contract): add optional field →
migrate consumers → remove old field. Breaking changes require a new version
published alongside the old, with a deprecation window.

**Rule:** Use consumer-driven contract tests (Pact or equivalent) or a schema
registry with compatibility mode — one of the two, enforced in CI. "We'll
coordinate releases in Slack" is the distributed monolith ([rules/07](07-anti-patterns-catalog.md)).

**Rule:** Tolerant reader: consumers ignore unknown fields and validate only
what they use. Strict full-payload validation on consume turns every producer
addition into your outage.

## 9. Time, IDs, and causality

**Rule:** Never use wall-clock timestamps for ordering or uniqueness across
machines. Use per-aggregate version numbers for ordering, UUIDv7/ULID/KSUID
for IDs (sortable, collision-resistant), and the database for authoritative time
where one exists.

**Rule:** Propagate correlation/trace context (W3C traceparent) through every
hop — HTTP, queue message headers, scheduled jobs. A distributed flow you can't
trace end-to-end is undebuggable; this is an audit-blocking gap, not polish.

## 10. Async request/response done right

**Rule:** When a caller needs an answer but the work is async, use correlation
explicitly: caller sends command with `correlation_id` + reply channel (reply
queue, callback URL, or polling endpoint with job status), worker replies with
the same `correlation_id`. Define the no-reply timeout and its user-facing
behavior up front.

**Rule:** Job-status resources beat held connections: `POST /exports → 202 +
/jobs/123`, then poll or push notification. States exposed: `queued → running →
succeeded(result_url) | failed(error, retryable?)`. Every async API the system
offers should converge on one such job pattern, not five bespoke ones.

## 11. Competing consumers and partition assignment

**Rule:** Scale consumers via the competing-consumers pattern, but know your
broker's unit of parallelism (Kafka: partitions; SQS: messages; AMQP: prefetch).
Max useful consumers = partition count for a classic Kafka consumer group
(Kafka 4.2+ share groups, KIP-932, lift that ceiling for true queue workloads
at the cost of per-key ordering — [sota-data-engineering rules/03](../../sota-data-engineering/rules/03-streaming-and-cdc.md)); provision
partitions for target parallelism *at topic creation* — repartitioning later
breaks key→partition ordering during the transition.

**Rule:** Keep per-message work small and uniform. One 10-minute message behind
500 fast ones on the same partition is head-of-line blocking; split heavy work
into a separate queue/topic with its own consumers (bulkheads, [rules/04](04-resilience-and-failure-design.md) §4).

**Rule:** Handle rebalances: consumers must expect partition reassignment
mid-stream (commit offsets only after processing; idempotency §2 covers the
overlap window).

## 12. Distributed coordination: avoid it, then do it right

**Rule:** The best lock is no lock: partition the work (each worker owns a key
range), or let the database arbitrate via constraints and conditional updates
(`UPDATE ... WHERE version = $expected`). Reach for distributed locks only when
neither applies.

**Rule:** If you must lock distributed-ly: use a lease (lock with TTL +
fencing token), never an unbounded lock — holders crash. Verify the fencing
token at the resource, not just at acquisition; a paused process can wake up
believing it still holds an expired lock.

```text
GOOD: token = lock.acquire(ttl=30s)        # token = monotonically increasing
      storage.write(data, fence=token)      # storage rejects stale tokens
BAD:  if redis.setnx(key): do_work()        # GC pause > TTL → two holders, no fence
```

**Rule:** Singleton jobs (schedulers, relays) use leader election (lease in
etcd/DB/k8s Lease) with the same fencing discipline, and must be idempotent
anyway because elections overlap.

## 12a. Check the design before you build it (model checking)

**When.** Write and check a small model when an in-house design's correctness depends on
interleavings or partial failure that a reviewer can only simulate in their head: a replication,
consensus or membership protocol; your own lease, lock or leader-handover scheme (§12); a workflow
split into asynchronous steps whose orderings are not obviously safe (§5); cache or index
invalidation; a lock removed or a message-ordering constraint weakened for performance. A stock
leader-election library or a platform Lease used as documented does not need one. AWS found bugs
this way that "passed unnoticed through extensive design reviews, code reviews, and testing", one
needing a trace of 35 high-level steps, because "testing the code is inadequate as a method for
finding subtle errors in design" (CACM 2015). Model one protocol, not the system: MongoDB's
engineers warn that one huge spec is doomed by state-space explosion. Model checking shows a
performance optimisation stays correct; it does not predict emergent latency or metastable
collapse, for which AWS runs discrete-event simulation, often driven by the same TLA+ or P models
(CACM 2025).

**With which tool** (checked against each project, 2026-10-25):

- **TLA+ with TLC** (MIT): explicit-state, safety and liveness; the most used.
- **Apalache** (Apache-2.0): checks a typed, finite fragment of TLA+ symbolically, with bounded
  runs and inductive invariants.
- **P** (MIT): the model is communicating state machines close to the code. Its checker samples
  **one** random schedule by default, so CI passes `-s <N>` (or `-t <seconds>`) and records the count;
  exhaustive search is a separate mode.
- **Quint** (Apache-2.0): TLA-based with programming-language syntax. `quint run` simulates and
  defaults to `--invariant 'true'`, so name the invariant; with `--seed` it runs one sample unless
  `--max-samples` is given. `quint verify` is bounded on Apalache (10 steps by default) or
  exhaustive with `--backend tlc`.
- **Alloy 6**: bounded signature scopes; the time horizon defaults to 10 steps unless an unbounded
  engine is configured.
- Where no model is justified, test the running system instead: deterministic simulation
  (FoundationDB's simulator, TigerBeetle's VOPR, `turmoil` or `shuttle` in Rust), or Jepsen with
  the Elle checker, whose README asks you to confirm reported anomalies by hand.

**A check that explores nothing passes.** Measured on TLC (v1.7.4 and the 1.8.0 pre-release,
2026-10-25): an `Init` that admits no state printed "No error has been found", exit 0, **0
distinct states**. So the job asserts what was explored:

- **A floor on distinct states**, not exit 0 alone.
- **Never `-deadlock`.** It disables deadlock detection in every state, not only the final one:
  two processes taking two locks in opposite order deadlocked, and `-deadlock -coverage 1` passed
  it, exit 0, with every action firing. If the protocol is meant to stop, add an explicit
  `Terminating == <done> /\ UNCHANGED vars` disjunct to `Next` (PlusCal generates one); the same
  spec then reported the deadlock, exit 11.
- **`-coverage 1`**, failing on any action whose final count is `0:0` (never enabled). Read the
  last coverage block: TLC reprints it during a long run. `0:N` is normal (it fired, but found
  only states already seen).
- **A reach check per state that matters** (committed, leader elected, lease expired): the main
  config with only the INVARIANT swapped for one saying the state is never reached, for example
  `~(\E n \in Node : role[n] = "Leader")`, which must be **violated**. Measured: exit 12 on the real
  spec, exit 0 on the empty-`Init` one. Keep the same CONSTANTS and CONSTRAINT, since a reach config
  without the main run's constraint was violated for a state the main run never explored. Drop
  SYMMETRY, under which a reachable state read as unreachable. Require the named invariant in the
  output and a trace longer than one state: an `Init` that already satisfies the predicate also
  exits 12. It is the counterpart of Kani's `cover!` ([`sota-rust` rules/09](../../sota-rust/rules/09-formal-verification.md)).
- **Liveness for a protocol meant to run forever.** Deadlock checking does not find livelock or
  starvation. Check at least one `PROPERTY` (a leader is eventually elected, a lease is eventually
  released) under explicit fairness; TLC exits 13 on a violation. AWS's own results table records a
  lock manager where it "Failed to find a liveness bug as we did not check liveness".

**Exit status is not a verdict on every tool** (measured 2026-10-25): TLC exits 12 on a violated
invariant, 11 on a deadlock and 13 on a liveness violation. Alloy 6.2.0 exits 0 whether a `check`
finds a counterexample or not, and a contradictory fact reads `UNSAT` like a real pass. FizzBee
0.5.4 exits 0 on `FAILED`, and Quint exits 1 for a violation and for its own tool errors alike.
Parse the result line, and give Alloy a `run` that must be satisfiable.

**The model is not the code.** A checked design says nothing about whether the implementation
follows it; AWS wrote in 2015 "we do not know". Where the gap matters, derive tests from the model
(MongoDB's generated tests reached full branch coverage on one component) or check test and
production traces against it (AWS's PObserve). Trace-checking a large existing server against an
abstract spec is the expensive end: MongoDB stopped after ten weeks because the traces never matched.

## 13. The fallacies, applied

Design reviews must not contain these assumptions; each appears in real designs
weekly:
- "The call will succeed" — every remote call needs a failure branch with a decision (retry? degrade? surface?), not just a log line.
- "Latency is negligible" — N sequential cross-service calls = N × RTT floor; budget it ([rules/04](04-resilience-and-failure-design.md) §1).
- "Bandwidth is infinite" — fat events/payloads (full entity snapshots on every change) saturate brokers; send deltas + version, or IDs + hot fields.
- "Topology doesn't change" — pin nothing to instance identity; discovery via the platform (DNS/service registry), connections re-resolve on failure.
- "The clock is right" — clock skew between machines is unbounded for ordering purposes (§9); never compare timestamps from two machines to decide order or expiry of anything critical.

## Audit checklist

- [ ] **Event sourcing: is replay actually runnable, or only theoretically?** Does the
      `apply` step read a wall clock, a random/UUID generator, config, or another service?
      Each one makes a rebuild differ from the original **silently** (§6). The values must
      be resolved at command time and **captured in the event**.
- [ ] Can outbound effects be **gated during replay** — a gateway with a replay mode? If
      not, replay only runs in a scratch environment, which is not a rebuild capability
      (§6).
- [ ] Do **events** get the durability/retention/backup budget rather than commands? A
      lost command is a retry; a lost event is unrecoverable state (§6).

- Is the consistency model (linearizable vs eventual, staleness bound) written down per critical operation? Does any flow assume read-your-writes across replicas or caches without sticky-primary, version-pinned reads or write-through, and is 2PC/XA used across heterogeneous systems? (§1)
- Is every message handler and retried endpoint provably idempotent? Is dedupe state committed atomically with the state change? (§2)
- Do public write APIs accept idempotency keys? Is retention documented? A payment-ish operation without one is Critical (§2)
- Does anything depend on exactly-once *delivery*? Any naked dual-writes (DB write + publish without outbox/CDC)? Is every message acked only after the state change is durably committed, and is inbound consume-and-act atomic (inbox table)? (§3, §4)
- Does every multi-service workflow have defined, idempotent compensations and a timeout-to-terminal-failure path? Can you answer "where is workflow X stuck" from a dashboard? Is any flow of 3+ steps choreographed rather than orchestrated? (§5)
- Do multi-leg money/inventory/entitlement workflows take value from the source *before* granting it at the destination? Where a credit lands first, is that balance provably held out of the spendable one — enforced, not assumed? (§5)
- Does every integration where an external party holds authoritative state have a periodic reconciliation against **their** extract (not your own event log), with breaks classified into auto-adjustable / manual / unclassified, aged, and alerted? Has that reconciliation ever been observed reporting a break, and does it print how many rows it compared on each side? Does it fail closed when either side reads zero? (§5b)
- Are events past-tense facts with producer ownership, or commands in disguise?
- Does every queue have bounded size, retry-with-backoff, DLQ, DLQ alerting, and a tested redrive runbook?
- Are poison messages separated from transient failures, or retried identically?
- [ ] Multi-tenant async work (§7): is every job type classified global / tenant-scoped / cross-tenant, are dedup and idempotency keys, retry state, per-tenant ordering and DLQ access scoped by tenant, and do global jobs run as an explicit system identity? HIGH (cross-tenant dedup drops or DLQ exposure). Probe for dedup/idempotency keys built without a tenant: `grep -rniE '(idempot|dedup)[a-z_]*_?key[[:space:]]*[:=]' . | grep -vi tenant`; for a fabricated tenant: `grep -rniE "tenant(_?id)?[\"']?[[:space:]]*(:=|[:=])[[:space:]]*[\"'](system|global|default|all|none|0)[\"']" .`
- AMQP consumers: manual ack after durable commit (no auto-ack)? Requeue limited to transient failures, with poison messages rejected (`requeue=false`) to a DLX? (§7b)
- Is prefetch (`basic.qos`) set explicitly on every AMQP consumer, or is any consumer running with unlimited prefetch? (§7b)
- Durable RabbitMQ queues: quorum (not classic), delivery-limit dead-lettering configured (not silently dropping)? Messages carry references rather than blobs/secrets? Broker locked down (per-service users, vhosts, least privilege, TLS)? (§7b)
- Is ordering guaranteed only where a partition key provides it? Any logic assuming global order or wall-clock ordering? Are wall-clock timestamps used for uniqueness across machines instead of version numbers and UUIDv7/ULID/KSUID ids? (§9)
- Are message/API schemas versioned with CI compatibility checks or consumer-driven contract tests? Do breaking changes ship as a new version alongside the old with a deprecation window? (§8)
- Are consumers tolerant readers (ignore unknown fields)? (§8)
- Is trace/correlation context propagated across every async hop? (§9)
- If event sourcing is used: are snapshotting, upcasting, and deletion (crypto-shredding) designed and tested?
- Do async request/response flows use correlation IDs and a standard job-status pattern with defined no-reply timeouts? (§10)
- Is consumer parallelism aligned with broker partitioning? Any head-of-line blocking from mixed-weight messages on one queue? Do consumers commit offsets only after processing, so a rebalance mid-stream is covered by idempotency? (§11)
- Are distributed locks lease-based with fencing tokens verified at the resource? Any bare `setnx`-style locks guarding critical sections? (§12)
- Are singleton/scheduled jobs leader-elected and idempotent under overlapping elections? (§12)
- [ ] An in-house replication, consensus, lease or lock scheme, or an async workflow whose step orderings are not obviously safe, built with no checked model and no deterministic-simulation test (§12a) → Medium (High where it guards money or data durability). Where a model exists: does CI run it with a distinct-state floor, without `-deadlock`, with reach checks that must be violated under the main config, and with a liveness `PROPERTY` for a forever-running protocol, parsing the result line rather than trusting exit 0 (Alloy, FizzBee, Quint)? Each missing → Medium. Locate the jobs: `grep -rnE 'tla2tools|tlc2\.TLC|(^|[[:space:]])tlc[[:space:]]|apalache|quint[[:space:]]+(run|verify|test)|(^|[[:space:]/])p[[:space:]]+check|(^|/)fizz[[:space:]]|org\.alloytools' --include='*.yml' --include='*.yaml' --include='*.sh' --include='*.mk' --include=Makefile --include=justfile --include=Dockerfile --include='*.toml' --include='*.json' .` (calibrated: 9 of 9 invocations, 0 of 2 decoys; standalone `ugrep` skips `.github/` unless given `--hidden`), and print a denominator beside it: `find . -name '*.tla' -o -name '*.qnt' -o -name '*.p' -o -name '*.als' | wc -l` (models with no job are the finding).
- Do any designs assume reliable network, ordered clocks, or stable topology (check failure branches on every remote call)? Any unbudgeted sequential cross-service calls, or full entity snapshots sent on every change? (§13)
