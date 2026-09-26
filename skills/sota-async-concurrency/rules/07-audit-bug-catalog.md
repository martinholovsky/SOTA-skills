# 07 — Audit Bug Catalog: Signatures, Severity, Fixes

How to use: grep for the signature, read each hit in context, prove the
interleaving (which two orders of execution diverge, and what breaks), then
report in the SKILL.md finding format. Severities below are baselines —
escalate for money/auth/durability state.

## 1. Fire-and-forget tasks swallowing exceptions — HIGH

**Signature greps:** `asyncio.create_task(` / `ensure_future(` with unused
return; bare `go func(` with no errgroup/WaitGroup/recover; `tokio::spawn(`
with dropped handle; `somethingAsync();` statement-position calls in JS;
`.then(` with no `.catch(`/second arg; C# `async void`, bare `Task.Run`.

**Failure mode:** the task fails, nobody observes it: silent data loss
(audit logs that never wrote, caches never invalidated), plus resource leak
if the dead task held connections. In Node, unhandled rejection kills the
process (default since v15) — a crash triggered at a *random later* tick, far
from the cause. In Go, a panic in a bare goroutine kills the process with no
request context. CPython extra: `create_task` holds only a weak ref — an
unreferenced running task can be GC'd mid-execution.

**Fix:** structured scope (TaskGroup/errgroup/JoinSet — rule 01); if truly
detached, attach an error handler + shutdown registration + comment.

```python
asyncio.create_task(send_webhook(evt))          # BAD
tg.create_task(send_webhook(evt))               # GOOD (inside TaskGroup)
```

## 2. Missing await — HIGH (often CRITICAL in tests)

**Signature:** calling an async function and using/discarding the result
without await: `result = fetch_user(id)` then `result.name` (you read a
coroutine/promise attribute → AttributeError or `[object Promise]`);
statement-position async calls; `return someAsync()` inside `try` (the
rejection escapes the catch — return-await matters in try blocks);
`if has_permission(user):` — **a coroutine/promise is always truthy**, so the
check always passes (CRITICAL: auth bypass); `forEach(async x => ...)` — JS
forEach ignores the returned promises, the loop "completes" with nothing done;
async test functions not awaited → test always passes.

**Detection:** TS `@typescript-eslint/no-floating-promises` +
`no-misused-promises`; Python `RuntimeWarning: coroutine ... was never
awaited` in logs, `asyncio` debug mode; Rust: `#[must_use]` on futures makes
this a compiler warning — heed it.

**Fix:** await it; for JS loops use `for...of` with await or
`Promise.all(arr.map(...))` (bounded — rule 01).

## 3. Shared mutable state across tasks — HIGH→CRITICAL

**Signature:** module/global-level dicts/lists/maps mutated in handlers;
`this.cache` / `self.sessions` mutated by concurrent requests; closure
variables captured by multiple spawned tasks; Go maps written from multiple
goroutines (fatal: `concurrent map writes` crash — run `-race`); loop
variables captured by reference in spawned closures (pre-Go-1.22 `for i`;
Python `lambda: f(i)` late binding; JS `var`).

**Failure mode:** lost updates, corrupted aggregates, cross-request data
bleed (one user sees another's data — CRITICAL/security), map-write crashes.
Remember: single-threaded async only protects *between* awaits; any structure
read before an await and written after is a race window (rule 02).

**Fix:** confine to one owner task + channel (rule 01); or immutable
snapshots; or a lock spanning the invariant; request-scoped state instead of
shared (contextvars / AsyncLocalStorage / explicit parameter).

**Request-scoped state must also be un-set.** Ambient per-request context
(tenant, user, locale) is only request-scoped if its scope closes: keep the
token from `ContextVar.set()` and `reset(token)` in `finally` (or
`with var.set(x):`, since Python 3.14); prefer `AsyncLocalStorage.run()` over
`enterWith()`; `ThreadLocal.remove()` in `finally`. Otherwise a *reused*
worker thread serves the next request with the previous tenant. Measured on
Python 3.14: a 1-worker `ThreadPoolExecutor` job that set a `ContextVar`
without reset left `"A"` visible to the next job; with `reset` it read
`None`. On Node 22, the store was still set after an `enterWith()` call had
returned, while after `run()` it was `undefined`. Language detail: sota-python
rules/04 §6, sota-jvm rules/03, sota-javascript-typescript rules/04.
OWASP: Multi-Tenant Security cheat sheet.

```python
# BAD — interleaved handlers corrupt the running aggregate.
stats["total"] += order.amount          # read-modify-write at await scale
# GOOD — single mutation point, owned by one consumer task.
await stats_queue.put(order.amount)
```

## 4. Lock held across await — HIGH (deadlock-capable: CRITICAL)

**Signature:** `async with lock:` body containing `await` of I/O; Rust
`std::sync::Mutex`/`parking_lot` guard alive across `.await` (Clippy lint
`await_holding_lock`); JS "lock" promises chained around fetches; any
`mutex.lock()` ... `await` ... `unlock()` sequence.

**Failure mode:** (a) throughput collapse — every contender parks for the
full I/O duration; (b) deadlock — the awaited operation (directly or via the
pool/queue it needs) requires the same lock or a resource held by a task
waiting on this lock; (c) in Rust, a `std` MutexGuard held across await can
block the *executor thread* when another task on the same thread contends —
freezing unrelated tasks.

**Fix:** narrow the critical section — copy what you need under the lock,
await outside, re-acquire to write (and **re-validate**: state may have
changed). If the await must be inside, use an async-aware lock and document
why; for Rust, `tokio::sync::Mutex` is the escape hatch but usually the
design wants a channel/owner-task instead.

```rust
// BAD
let g = STATE.lock().unwrap();
let val = fetch_remote(g.key).await;     // guard across await
// GOOD
let key = { STATE.lock().unwrap().key.clone() };
let val = fetch_remote(key).await;
{ let mut g = STATE.lock().unwrap(); if g.key == key { g.val = val; } }
```

## 5. Blocking call in async context — HIGH

Full treatment in rule 04. Grep list: `time.sleep`, `requests.`, `open(`,
`subprocess.run`, sync DB drivers, `readFileSync`, `execSync`, `hashSync`,
`pbkdf2Sync`, `std::thread::sleep`, `reqwest::blocking`, `block_on(` inside
async (`futures::executor::block_on` deadlocks a current-thread runtime and
parks a worker otherwise; tokio's `Handle::block_on` panics),
`.result()`/`.get()` on a future from loop thread, `loop.run_until_complete`
inside a running loop. Severity HIGH; CRITICAL when the blocked call awaits
something scheduled on the same loop (self-deadlock: e.g., sync-waiting a
future the loop must complete).

## 6. Retry storms — HIGH

**Signature:** retry loops with no backoff (`for attempt in range(5): try
... except: continue`); backoff without jitter; retries on every layer
(client retries × gateway retries × service retries = N³ amplification);
retrying non-retryable errors (400s, auth failures); no retry budget; retry
ignoring ctx/deadline (rule 05).

**Failure mode:** a downstream blip multiplies traffic exactly when capacity
is lowest, preventing recovery — the outage becomes self-sustaining
("metastable failure"). Synchronized retries (fixed backoff, cron alignment)
arrive in waves.

**Fix:** exponential backoff + **full jitter**
(`sleep(rand(0, min(cap, base·2^attempt)))`); retry budget (e.g., retries ≤
10% of requests — token bucket on the retry path); retry at **one** layer;
honor `Retry-After`; circuit breaker for persistent failure; classify errors
(retry 503/timeout, never 4xx except 429).

```python
# GOOD
for attempt in range(MAX):
    try:
        return await op()
    except RetryableError:
        if attempt == MAX - 1 or not retry_budget.try_acquire():
            raise
        await asyncio.sleep(random.uniform(0, min(CAP, BASE * 2**attempt)))
```

## 7. Thundering herd — MEDIUM→HIGH

**Variants & signatures:**
- **Cache stampede:** popular key expires → all requesters recompute
  simultaneously. Signature: `get → miss → compute → set` with TTL, no
  single-flight. Fix: request coalescing (`singleflight.Group`, memoized
  in-process future — rule 02's example), stale-while-revalidate, probabilistic
  early refresh (XFetch), lock-and-recompute-once.
- **Synchronized wakeups:** every instance polls/refreshes on the same cron
  second (`:00`), reconnects immediately after a broker restart. Fix: jitter
  every period and every reconnect delay.
- **notify_all/broadcast for one item:** N waiters wake, one wins, N−1
  re-sleep — at scale this is a CPU spike per event. Fix: `notify_one` when
  waiters are interchangeable (rule 03 caveats), or sharded queues.
- **Deploy/startup herd:** all pods warm caches/open connections at once.
  Fix: staggered rollout, jittered warmup.

## 8. Futures spawned in loops without bounding — HIGH

**Signature:** `gather(*[f(x) for x in items])` / `Promise.all(items.map(f))`
/ `for ...: tg.create_task(...)` / `for { go f() }` where `items` is
unbounded (DB rows, file lines, network input). Also: recursion that spawns
(crawlers), per-event spawn in subscription handlers.

**Failure mode:** memory (N stacks/promise chains), fd exhaustion (N
sockets), and a self-DoS of the downstream (N concurrent calls = you are the
thundering herd). Works in dev (N=10), dies in prod (N=10M).

**Fix:** semaphore-bounded fan-out, fixed worker pool over a bounded queue,
`errgroup.SetLimit`, chunked `Promise.all`, streaming instead of
collect-then-blast (rules 01, 06).

## 9. Leaked tasks & goroutines (blocked forever) — MEDIUM→HIGH

**Signature:** channel send/receive with no cancellation branch and a
receiver/sender that can exit early (rule 03); `queue.get()` workers with no
sentinel/cancel path; `Promise` executors whose resolve path can be skipped
(a promise that never settles parks every awaiter forever); event-listener
accumulation per request (`emitter.on` in handlers without `off` —
EventEmitter leak warnings); periodic timers never cleared.

**Detection in review:** for each blocking point ask "what guarantees the
other side shows up?" For each subscription/timer: "where is the matching
teardown?" Goroutine/task counts as a metric; `pprof` goroutine dumps;
`asyncio.all_tasks()` snapshots.

## 10. Double-execution & ordering assumptions — MEDIUM→HIGH

- **At-least-once handlers without idempotency** (rule 02): queue redelivery
  + side effects = duplicates. Look for consumer handlers doing
  `INSERT`/`send_email`/`charge` with no dedupe key.
- **Assumed FIFO across workers:** a queue is FIFO; N workers consuming it
  complete out of order. Look for "process events in order" logic running at
  concurrency > 1; per-key ordering needs partitioning (hash key → one
  worker/partition).
- **Ack-before-durable:** message acked, then process crashes before the
  side effect commits → silent loss. Ack must follow the commit (or use
  transactional outbox).
- **Time-of-check on task state:** `if not task.done(): task.cancel()` —
  fine; but `task.result()` after `done()` check without exception handling
  re-raises the task's exception where you didn't expect it.

## 11. Async iterator / generator cleanup — LOW→MEDIUM

`break`-ing out of an `async for` may leave the generator suspended;
finalization runs late (GC) or never — connections held open. Python: wrap
in `contextlib.aclosing(gen)`; JS: `for await` with `break` *does* call
`return()` — but a hand-rolled iterator must implement it. Rust streams:
dropping is fine (drop = cancel) but resources must be in Drop, not in
"after the loop" code.

## 12. Test-only / heisenbug smells — MEDIUM

`sleep(0.1)`-then-assert synchronization in tests or — worse — production
("wait a bit for the worker to pick it up"). Sleeps are a race with a
deadline: flaky in CI, broken under load. Replace with explicit
synchronization: events, joins, polling-with-timeout on the actual condition,
fake clocks (`tokio::time::pause`, `looptime`, Go's `testing/synctest`
bubbles — GA in 1.25, `synctest.Wait` replaces sleep-and-hope).
Production code that
"sleeps to let X finish" is finding-worthy as written — it encodes an
ordering assumption with no enforcement.

## Audit sweep order (efficient pass over a codebase)

1. **Topology first** (30 min): entry points, spawns, shared state, queues,
   locks. Write down the lock graph and channel graph.
2. **Greps, in descending hit-value:** blocking-in-async list (rule 04) →
   fire-and-forget signatures (#1) → unbounded queue/channel constructors
   (#8, rule 06) → lock-across-await (#4) → `context.Background`/missing
   AbortSignal (rule 05) → check-then-act on the shared state found in step 1
   (rule 02) → retry loops (#6).
3. **Read the shutdown path end-to-end** — it exercises cancellation,
   draining, and task ownership all at once; most codebases fail here.
4. **Read the hottest handler end-to-end** and prove its timeout chain.
5. Report with interleavings, not vibes.

## Audit checklist (meta — the whole catalog)

- [ ] #1 fire-and-forget: every spawn owned, errors observed
- [ ] #2 missing await: truthy-promise checks, forEach(async), return-in-try
- [ ] #3 shared mutable state: cross-request bleed, loop-var capture, Go maps
- [ ] #3 request-scoped context set but never reset — HIGH when it holds a
      tenant or user id: `grep -rnE '^[[:space:]]*[[:alnum:]_.]+\.set\([^)]|\.enterWith\(|ThreadLocal<' --include='*.py' --include='*.js' --include='*.ts' --include='*.java' --include='*.kt' .`
      (a bare `x.set(v)` statement discards the token and cannot be reset; each
      `ThreadLocal` needs a `remove()` in `finally`; a `token = x.set(v)` or
      `with x.set(v):` does not match; a JS/Java `map.set(k, v)` hit is noise —
      keep only the context variables)
- [ ] #4 locks across await; Rust std guards across `.await`
- [ ] #5 blocking calls in async (rule 04 grep list); `block_on` in async
- [ ] #6 retries: backoff+jitter+budget+classification+ctx
- [ ] #7 herd: cache stampede single-flight; jittered periodics/reconnects
- [ ] #8 unbounded fan-out: gather/Promise.all/go-in-loop over external input
- [ ] #9 leaks: unsettleable promises, sentinel-less workers, listener/timer
      teardown
- [ ] #10 duplicates & ordering: idempotency keys, per-key partitioning,
      ack-after-commit
- [ ] #11 generator/stream cleanup on early exit
- [ ] #12 sleep-based synchronization anywhere
- [ ] Shutdown path read end-to-end; hottest path timeout chain proven
