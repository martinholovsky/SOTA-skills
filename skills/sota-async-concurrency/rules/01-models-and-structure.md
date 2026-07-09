# 01 — Concurrency Models & Structured Concurrency

## Choosing a model

There are four models. Pick by workload shape, not by familiarity.

| Model | Parallelism | Memory | Best for | Worst for |
|---|---|---|---|---|
| Event loop (async/await) | None (single thread) | Shared, but single-threaded — no data races, still race conditions | Many concurrent I/O waits (10k sockets) | CPU work, blocking libraries |
| Threads | Yes (runtime permitting) | Shared — full data-race exposure | Parallel CPU work, blocking-API integration | Massive fan-out (stack cost), correctness at scale |
| Processes | Yes, full | Isolated — share via IPC/serialization | CPU-bound in GIL-locked runtimes; fault isolation | Chatty workloads (serialization tax) |
| Actors (message passing) | Yes | Isolated per actor; communicate via mailboxes | Stateful entities at scale, distribution, supervision trees | Simple request/response pipelines (overkill) |

### Decision tree

```
What dominates the workload?
├── Waiting on I/O (network, disk, DB)
│   ├── Concurrency level high (100s+)  → event loop / async
│   └── Low, and libraries are blocking → small thread pool is fine
├── Computing (CPU-bound)
│   ├── Runtime has parallel threads (Go, Rust, Java, C#,
│   │   Python 3.13+ free-threaded)    → thread pool, size ≈ cores
│   └── GIL-constrained (CPython w/ GIL, Node JS-land)
│       → process pool / worker_threads (V8 isolates count as this);
│         subinterpreter pool on CPython 3.14+ (see Python note)
├── Both (typical server: I/O front, CPU spikes)
│   → async front-end + bounded worker pool for CPU (rule 04)
└── Long-lived stateful entities, supervision, distribution
    → actor model (Erlang/Elixir, Akka/Pekko, Actix, or hand-rolled
      single-owner task + mailbox channel — see below)
```

**Rationale:** the event loop wins I/O fan-out because a parked coroutine costs
~KB versus ~MB-of-stack per thread; threads win CPU because an event loop has
exactly one core's worth of compute. Mixing them backwards produces the two
classic failures: blocked loops (rule 04) and 10,000 threads.

### Per-runtime notes

- **Python:** asyncio coroutines for I/O; `ProcessPoolExecutor` for CPU under
  the GIL. Python 3.13+ free-threaded builds make thread pools viable for CPU,
  but C extensions must declare support — verify before relying on it.
  Python 3.14+ adds subinterpreters (PEP 734: `concurrent.interpreters`,
  `concurrent.futures.InterpreterPoolExecutor`) — per-interpreter-GIL
  parallelism in one process, cheaper than a process pool, but objects cross
  the boundary by pickling, not by reference.
- **Node:** one JS thread per isolate. CPU work goes to `worker_threads`
  (or `piscina`); never compute on the main loop.
- **Go:** goroutines are M:N scheduled — blocking syscalls don't block the
  scheduler, so "async vs threads" mostly disappears. Your problems shift to
  unbounded goroutine spawns and channel misuse (rules 03, 06).
- **Rust:** `tokio` (or `smol`) for I/O; `rayon` or `spawn_blocking` for CPU.
  Don't run rayon work on the tokio runtime threads — it starves the reactor.
- **JVM:** virtual threads (Loom) give event-loop economics with thread
  programming model; pinning on `synchronized` blocks around blocking calls is
  the main hazard on JDK ≤23 (use `ReentrantLock` instead in hot paths) —
  fixed in JDK 24+ (JEP 491), but JDK 21 LTS deployments still hit it.

## Structured concurrency is the default

A task whose lifetime exceeds the scope that created it is an **orphan**: its
exceptions vanish, its resources leak, and nothing cancels it on shutdown.
Structured concurrency makes task lifetime lexical: a scope (nursery, task
group, errgroup, JoinSet) owns its children, propagates their errors, and
cancels siblings on failure.

**Rule: every spawn is inside a scope that joins it.** Spawning into the void
(`asyncio.create_task` with a discarded handle, bare `go func()`,
un-awaited promise, dropped `JoinHandle`) requires: (a) an attached error
handler, (b) registration with a shutdown mechanism, (c) a comment saying why.

```python
# BAD — orphan: exception is swallowed, task outlives the request,
# nothing cancels it on shutdown. CPython may even GC the task mid-flight
# because create_task only holds a weak reference.
async def handle(req):
    asyncio.create_task(audit_log(req))     # fire-and-forget
    return await process(req)

# GOOD — scope owns both; if process() raises, audit_log is cancelled;
# neither can outlive handle().
async def handle(req):
    async with asyncio.TaskGroup() as tg:
        tg.create_task(audit_log(req))
        t = tg.create_task(process(req))
    return t.result()
```

```go
// BAD — goroutine leaks if ctx is cancelled before send; errors lost.
func fetchAll(urls []string) []Result {
    out := make(chan Result)
    for _, u := range urls {
        go func() { out <- fetch(u) }()     // who joins this? nobody.
    }
    ...
}

// GOOD — errgroup: bounded, joined, first error cancels the rest.
func fetchAll(ctx context.Context, urls []string) ([]Result, error) {
    g, ctx := errgroup.WithContext(ctx)
    g.SetLimit(16)
    results := make([]Result, len(urls))
    for i, u := range urls {
        g.Go(func() error {
            r, err := fetch(ctx, u)
            results[i] = r                  // disjoint index: no race
            return err
        })
    }
    return results, g.Wait()
}
```

```rust
// BAD — handle dropped: task detaches, panics are silently lost.
tokio::spawn(async move { sync_to_remote(item).await });

// GOOD — JoinSet ties tasks to the owning scope; aborts on drop.
let mut set = tokio::task::JoinSet::new();
for item in items {
    set.spawn(sync_to_remote(item));
}
while let Some(res) = set.join_next().await {
    res??; // surface panics and errors
}
```

```js
// BAD — floating promise: rejection becomes unhandledRejection,
// possibly crashing the process at a random later time.
function handle(req) {
  auditLog(req);            // async fn, not awaited, no .catch
  return process(req);
}

// GOOD — join both; Promise.allSettled if audit failure is non-fatal.
async function handle(req) {
  const [audit, result] = await Promise.allSettled([auditLog(req), process(req)]);
  if (result.status === "rejected") throw result.reason;
  return result.value;
}
```

### Scope semantics to know

- **Error propagation:** TaskGroup/errgroup cancel siblings on first error and
  re-raise. If you need "collect all results, even failures", use
  `Promise.allSettled` / gather with `return_exceptions=True` / collect from
  `JoinSet` — and then *actually inspect* the failures.
- **Nesting:** scopes nest; cancellation flows down, errors flow up. Deadlines
  attach naturally to scopes (rule 05).
- **Background services** (true daemons: metrics flusher, heartbeat) are the
  one legitimate long-lived spawn. Pattern: create them in `main`'s top-level
  scope, store handles, cancel them in shutdown. They are still owned — by the
  application scope, not by nobody.

### Hand-rolled actor (single-owner state)

When multiple tasks need the same mutable state, the cheapest correct design
is often: one owner task, one bounded mailbox, no locks.

```go
// GOOD — counter actor: state confined to one goroutine; callers
// communicate via channel. No mutex, no race, natural backpressure.
type op struct{ delta int; reply chan int }
func counter(ctx context.Context, ops <-chan op) {
    n := 0
    for {
        select {
        case <-ctx.Done():
            return
        case o := <-ops:
            n += o.delta
            o.reply <- n
        }
    }
}
```

Use this instead of a mutex when: state has invariants spanning multiple
fields; operations must serialize anyway; or you need to bound the request
rate to the state (mailbox = built-in backpressure).

## Sizing rules

- Thread/process pool for CPU: `n_cores` (maybe `n_cores ± 1`); more adds
  context-switch overhead, not throughput.
- Thread pool wrapping blocking I/O: size by `concurrency_target ×
  avg_wait_fraction`, cap it, and queue behind a semaphore — not "unbounded
  cached pool".
- Async fan-out: never `gather(*[f(x) for x in million_items])`. Bound with a
  semaphore or worker pool reading from a bounded queue (rule 06).

```python
# BAD — a million concurrent connections, file descriptors, and timers.
await asyncio.gather(*(fetch(u) for u in urls))

# GOOD — bounded fan-out inside a scope.
sem = asyncio.Semaphore(50)
async def bounded_fetch(u):
    async with sem:
        return await fetch(u)
async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(bounded_fetch(u)) for u in urls]
```

## Audit checklist

- [ ] Workload classified? CPU-bound code on an event loop or I/O fan-out on
      a thread-per-request model is an architecture-level finding.
- [ ] Grep for orphan spawns: `create_task(`/`ensure_future(` with unused
      result, bare `go func(`, `tokio::spawn` with dropped handle, async calls
      and `.then(` chains with no await/`.catch`.
- [ ] For every spawn: who joins it? Who sees its exception? Who cancels it on
      shutdown? Three answers or it's a finding (HIGH if it does I/O or holds
      resources).
- [ ] `asyncio.create_task` results stored in a strong reference (or
      TaskGroup)? Weak-ref GC of running tasks is a real CPython footgun.
- [ ] Fan-out loops bounded by semaphore/errgroup limit/pool size?
- [ ] `gather`/`Promise.all` failure mode considered — does first failure
      strand or leak the siblings? (Plain `asyncio.gather` does not cancel
      siblings on error unless they're in a TaskGroup.)
- [ ] Background daemons registered for shutdown cancellation?
- [ ] Pools sized with a stated rationale, not defaults-by-accident?
- [ ] Shared mutable state: could it be owned by one task + mailbox instead of
      a lock? (Not mandatory, but flag invariant-spanning state guarded by
      multiple separate locks.)
