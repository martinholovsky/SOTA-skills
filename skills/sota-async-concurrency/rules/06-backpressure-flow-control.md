# 06 — Backpressure & Flow Control

## The law of rate mismatch

Whenever a producer can outpace a consumer — and under load, some producer
always can — the difference goes somewhere: memory (unbounded queue → OOM),
latency (bounded queue → growing wait), or rejection (shedding). **You don't
choose whether to have backpressure; you choose whether it's controlled.**
Uncontrolled backpressure looks like: heap growth, GC death spirals, queue
latencies in minutes, then a crash that loses everything buffered.

Design question for every queue/channel/buffer: *what happens when it's
full?* If the answer is "it can't fill up", the design is wrong.

## Bounded queues everywhere

Every queue gets a capacity and a full-policy:

| Full-policy | Behavior | Use when |
|---|---|---|
| **Block (backpressure)** | Producer waits; pressure propagates upstream to the true source | Producer can tolerate waiting; source is throttleable (TCP does this for you) |
| **Drop-new (shed)** | Reject the incoming item, tell the caller | Request/response systems — fail fast beats slow death |
| **Drop-old (slide)** | Evict oldest, keep newest | Telemetry, frames, tickers — freshness beats completeness |
| **Coalesce/conflate** | Merge into pending item (keep-latest, sum deltas) | State updates where only the latest matters |

```python
# BAD — unbounded; a slow consumer turns this into an OOM timer.
q = asyncio.Queue()

# GOOD — bounded, and the enqueue point makes the full-policy explicit.
q = asyncio.Queue(maxsize=256)
try:
    q.put_nowait(item)              # shed:
except asyncio.QueueFull:
    metrics.dropped.inc()
    raise ServiceOverloaded()       # ...or `await q.put(item)` to block
```

Sizing: capacity ≈ `consumer_rate × tolerable_queue_delay` (Little's law),
plus burst headroom. A queue of 10,000 in front of a 100/s consumer is a
100-second latency reservoir — big buffers don't add throughput, they hide
overload and delay the inevitable. Default small (dozens–hundreds); grow only
with a measured reason.

**Blocking-policy deadlock warning:** block-on-full inside a cycle (consumer
also produces into the same queue, or A→B and B→A both bounded-blocking)
deadlocks when both fill. Cycles need shed/coalesce somewhere, or strictly
acyclic flow.

## End-to-end propagation

Backpressure only works if the pressure reaches the **source**. Audit the
chain: socket → parser → queue → workers → DB. One unbounded link (or one
fire-and-forget spawn per item — rule 07) breaks the chain, absorbing
pressure invisibly until OOM.

```go
// BAD — "absorb with goroutines": unbounded queue in disguise.
for msg := range kafkaMessages {
    go handle(msg)              // 50k msgs/s × 2s handling = 100k goroutines
}

// GOOD — worker pool: consumption rate is explicitly capped; the Kafka
// consumer naturally pauses (stops polling) when workers are busy.
sem := make(chan struct{}, 64)
for msg := range kafkaMessages {
    sem <- struct{}{}           // blocks when 64 in flight
    go func(m Msg) { defer func() { <-sem }(); handle(m) }(msg)
}
```

Natural backpressure carriers — don't defeat them:
- **TCP flow control:** not reading from a socket slows the sender. Reading
  eagerly into an unbounded buffer ("to free the socket") destroys this.
- **Pull-based consumption:** polling (Kafka, SQS) is inherently
  backpressured — poll only when capacity exists. Push-based (raw WebSocket,
  gRPC stream w/o flow control config) needs explicit bounding.
- **AMQP prefetch (`basic.qos`):** RabbitMQ *pushes*; the prefetch count (cap
  on unacked deliveries) is the demand signal. Unset/0 = unlimited prefetch =
  an unbounded buffer in the consumer. Always set it explicitly (broker-side
  semantics: [sota-architecture rules/03](../../sota-architecture/rules/03-distributed-systems-and-events.md) §7b).
- **HTTP server concurrency limits:** cap in-flight requests at the listener
  (semaphore/middleware); past the cap, 503 immediately.

## Load shedding

When demand exceeds capacity, serving fewer requests *well* beats serving all
requests *too late to matter*. A response delivered after the client's
timeout is pure waste — you paid the cost and got zero utility ("goodput").

- **Shed early, shed cheap:** reject at admission (queue full, semaphore
  unavailable, deadline already insufficient) before parsing/auth/DB work.
- **Deadline-aware:** if `remaining_budget < expected_cost`, drop now —
  the caller has already given up by the time you'd answer.
- **Signal correctly:** 503/429 + `Retry-After`; gRPC `RESOURCE_EXHAUSTED`.
  Distinguishable from real failures so clients back off rather than retry
  hot (rule 07: retry storms).
- **Prioritize:** shed batch/analytics before interactive; health checks
  never shed (or the orchestrator kills an overloaded-but-alive pod —
  conversely, *readiness* should fail under overload to divert traffic).

## Rate limiting: token bucket as the workhorse

Token bucket = sustained rate `r` + burst capacity `b`. Use it for: outbound
calls to dependencies (protect *them*), per-tenant fairness (protect *you*),
and retry/error-path throttling.

```go
// GOOD — golang.org/x/time/rate; Wait blocks (backpressure),
// Allow sheds. Pick per the full-policy table above.
lim := rate.NewLimiter(rate.Limit(100), 200) // 100/s, burst 200
if err := lim.Wait(ctx); err != nil { return err }  // cancellable!
```

Notes:
- Rate limiters **smooth**, they don't bound concurrency — a 100/s limit with
  10s handlers is 1000 in flight. Pair limiter (rate) with semaphore
  (concurrency); you usually need both.
- Per-tenant buckets need an eviction story (LRU of buckets) or they're an
  unbounded map — the leak you built to prevent leaks.
- Distributed limiting (Redis token bucket) is approximate; design for slight
  overshoot rather than coordinating exactly.
- **Adaptive concurrency** (AIMD / gradient — Netflix concurrency-limits
  style) outperforms static limits when downstream capacity varies; SOTA for
  service meshes, overkill for a single worker pool.

## Streaming with pull-based demand

The streaming SOTA is **demand-driven (pull) flow**: the consumer signals
capacity; the producer sends at most that much. Push-with-buffering is the
legacy failure mode.

- **Reactive Streams / RxJava / Reactor:** `request(n)` is the demand signal;
  an operator chain without bounded demand (`onBackpressureBuffer()`
  unbounded) is a leak.
- **Node streams:** respect `write()`'s return value — `false` means stop and
  wait for `'drain'`. Ignoring it buffers unboundedly in the writable's
  internal queue. Prefer `pipeline()`/`pipe()`, which wire this up (and
  propagate errors/teardown), over hand-rolled `on('data', ...)` +
  `write(...)` pairs. `for await (const chunk of readable)` pauses the source
  between iterations: pull semantics for free.
- **Async iterators/generators (Python & JS)** are naturally pull-based —
  the producer runs only when the consumer awaits the next item. Converting a
  callback/push source into an async iterator requires an internal queue:
  bound it and choose a full-policy (this is where "adapter" libraries leak).
- **gRPC/HTTP2:** per-stream flow-control windows give transport-level
  backpressure — but only if your handler awaits sends and reads lazily
  rather than spooling the whole stream into memory.

```js
// BAD — push: data events keep firing regardless of write capacity.
src.on("data", chunk => dst.write(transform(chunk)));

// GOOD — pull with drain handling, teardown and error propagation.
await pipeline(src, transformStream, dst);
```

```python
# GOOD — pull-based pipeline: each stage runs only on demand.
async def transformed(source):
    async for item in source:        # awaits = demand signal upstream
        yield transform(item)
```

**Slow-consumer policy for fan-out (pub/sub, WebSockets):** one slow
subscriber must not buffer the world or stall the broadcast. Per-subscriber
bounded queue + drop-old/disconnect-on-lag (this is why Go's `rxgo`-style
broadcast and NATS use lag-based eviction). Decide per endpoint: kill the
laggard, or degrade its stream.

## Circuit breakers: backpressure for failure

Retry budgets slow the bleeding; a circuit breaker stops calling a dependency
that is down, failing fast locally and giving it room to recover.

States: **closed** (normal; count failures over a rolling window) →
**open** (error rate over threshold, e.g., >50% of ≥20 calls in 10s: reject
immediately for a cooldown) → **half-open** (after cooldown, admit a few
probe calls; success closes, failure re-opens).

Implementation rules:
- Trip on **error rate over a minimum volume**, not consecutive-failure
  counts (one slow burst trips a count-based breaker spuriously).
- Treat timeouts as failures — a dependency answering slowly at 100%
  occupancy is *down* for capacity purposes.
- Half-open probes must be **bounded** (1–N concurrent), or the reopen is a
  thundering herd onto a convalescent service.
- Scope per dependency *endpoint/shard*, not globally — one bad shard
  shouldn't open the breaker for nine healthy ones.
- The breaker-open error must be distinguishable (and non-retryable at this
  layer) so callers shed or degrade rather than hammer.
- Breaker state is shared mutable state read on every call: use atomics or a
  lock-free snapshot, not a mutex on the hot path (rule 03).

```python
# GOOD — shape of the call site: breaker wraps the timeout, which wraps the op.
if not breaker.allow():
    raise DependencyUnavailable(retry_after=breaker.cooldown_remaining())
try:
    async with asyncio.timeout(0.5):
        result = await dep.call(req)
except (TimeoutError, DependencyError) as e:
    breaker.record_failure()
    raise
breaker.record_success()
```

## Batching & coalescing

Batching raises throughput (amortized syscalls/commits) at the cost of
latency. Correct batcher shape: flush on **size OR time, whichever first**
(`max_batch=100, max_delay=10ms`), bounded pending buffer, flush on shutdown
(rule 05). Size-only batchers strand the tail; time-only batchers under-fill
at high rates. Coalescing (keep-latest per key) is the strongest defense for
state-update streams: the queue can't exceed the keyspace.

## Audit checklist

- [ ] Inventory every queue/channel/buffer (incl. implicit ones: goroutine
      spawns per item, promise arrays, stream internal buffers, per-subscriber
      send queues). Each has: a bound? a full-policy? a stated size rationale?
- [ ] Unbounded queue reachable from network input = HIGH (CRITICAL if
      multiplied per-connection/per-tenant).
- [ ] Trace pressure source→sink: where does it stop propagating? Any
      fire-and-forget or eager-read-into-buffer that defeats TCP/pull
      semantics?
- [ ] Bounded-blocking queues inside cycles (deadlock) — wait-for graph check.
- [ ] Admission control on servers: in-flight cap, early shedding before
      expensive work, deadline-aware drops, correct 429/503 + Retry-After?
- [ ] Health/readiness behavior under overload: liveness must pass, readiness
      should shed.
- [ ] Rate limiters paired with concurrency limits? Per-tenant limiter maps
      evicted? Limiter waits cancellable (ctx in `Wait`)?
- [ ] Critical dependencies behind breakers? Rate-based tripping, timeouts
      counted as failures, bounded half-open probes, per-endpoint scope?
- [ ] Node: `write()` return value honored or `pipeline()` used? Custom
      `on('data')` handlers without pause/resume?
- [ ] Push→pull adapters (callback to async-iterator bridges): internal queue
      bounded?
- [ ] AMQP consumers: prefetch count set explicitly (no unlimited prefetch),
      sized to handler speed?
- [ ] Fan-out endpoints: slow-consumer policy defined (drop, lag-kick), or
      can one dead-slow WebSocket OOM the broadcaster?
- [ ] Batchers: size+time flush, bounded pending, shutdown flush?
