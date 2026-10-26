# 03 — Primitives: Locks, Semaphores, Condvars, Channels, Select, Once

## 1. Picking the primitive

| Need | Use | Not |
|---|---|---|
| Protect invariant across fields | Mutex (one, spanning the invariant) | Two atomics |
| Single-word counter/flag | Atomic | Mutex |
| Bound concurrent access to N | Semaphore | Spin-checking a counter |
| Hand data between tasks | Bounded channel/queue | Shared list + lock + sleep-poll |
| Wait for a state change | Condvar (with predicate loop) or channel/event | Polling loop |
| Read-mostly shared data | RwLock — or better, immutable snapshot swap (arc-swap, copy-on-write) | RwLock by reflex |
| One-time init | Once/OnceLock/lazy | Hand-rolled double-checked locking |

Prefer the highest-level primitive that fits: channel > semaphore > mutex >
atomic > condvar (condvars are last because they're the easiest to misuse).

## 2. Mutex vs RwLock — RwLock is not "mutex but faster"

- RwLock pays for its bookkeeping; under short critical sections a plain mutex
  often outperforms it. Choose RwLock only for **read-heavy, long-ish reads,
  measurable contention**.
- **Writer starvation:** with reader-preferring RwLocks, a continuous stream
  of readers can block a writer indefinitely. Writer-preferring
  implementations (and most modern defaults: Rust `parking_lot`, Go
  `sync.RWMutex`) instead make *new readers* wait once a writer queues — which
  means **recursive read-lock acquisition deadlocks** (reader holds read lock,
  writer queues, reader re-acquires read → waits behind writer → cycle).
  Never re-acquire a read lock you might already hold.
- Read-mostly data is often better served lock-free: build a new immutable
  snapshot, atomically swap the pointer (`ArcSwap`, `AtomicReference`,
  Go `atomic.Pointer`). Readers never block; writers pay for copy.

```rust
// BAD — recursive read lock; deadlocks when a writer queues between them.
fn total(&self) -> u64 {
    let g = self.map.read();
    g.keys().map(|k| self.get(k)).sum()   // get() also takes map.read()
}
```

Upgradable locks (read→write upgrade) deadlock when two readers both try to
upgrade. If your design "needs" an upgrade, restructure: release, re-acquire
write, **re-validate** (state may have changed — TOCTOU otherwise).

## 3. Semaphores: the bounding primitive

A semaphore's job in modern code is **admission control**: cap in-flight
work, connections, memory-heavy operations.

```python
# GOOD — cap concurrent outbound calls without restructuring the caller.
sem = asyncio.Semaphore(20)
async def call(api):
    async with sem:                  # context manager: released on raise too
        return await api.get()
```

Rules:
- Release on every path — context manager / `defer` / RAII, never bare
  `acquire` ... `release` pairs separated by raisable code.
- Acquire with the request's timeout/cancellation, not unconditionally:
  a semaphore queue with no deadline converts overload into infinite latency
  (rule 06 — shed instead).
- Don't acquire a second semaphore (or pool) while holding one unless ordering
  is global (same deadlock rules as locks). Pool-within-pool (HTTP pool inside
  DB-transaction holder) is a classic production deadlock.
- Weighted semaphores (`golang.org/x/sync/semaphore`) for memory-proportional
  bounding: acquire `n = estimated_bytes`, not 1.

## 4. Condition variables: two famous bugs

**Bug 1 — spurious wakeups & stolen wakeups.** `wait()` can return without a
notify, and another thread may consume the state between notify and your
wakeup. Therefore: **always wait in a loop re-checking the predicate.**

```java
// BAD                                 // GOOD
synchronized (lock) {                  synchronized (lock) {
    if (queue.isEmpty())                   while (queue.isEmpty())
        lock.wait();                           lock.wait();
    item = queue.remove();                 item = queue.remove();
}                                      }
```

**Bug 2 — lost notify.** Notifying before the waiter waits (or mutating the
predicate outside the mutex) means the waiter sleeps forever. Therefore:
**mutate the predicate and notify while holding the same mutex the waiter
checks under.** The predicate-loop also defends against this — the waiter
checks state before sleeping.

`notify_one` vs `notify_all`: `notify_one` is an optimization that is only
correct when all waiters are interchangeable and one item satisfies exactly
one waiter. When waiters wait for different conditions on one condvar, or you
are not sure: `notify_all` (correctness first; thundering herd is rule 06's
problem).

In async code, prefer events/channels over condvars; if you use
`asyncio.Condition`, the same predicate-loop law applies (`await
cond.wait_for(pred)` encodes it).

## 5. Channels & queues: bounded or it's a bug

**An unbounded channel is a memory leak with extra steps.** If the producer
is ever faster than the consumer — and under load it will be — the queue
absorbs the difference until OOM. Bounding turns the failure into visible
backpressure at the source (rule 06).

```go
// BAD — unbounded buffering via goroutine-per-send, or huge buffer "to be safe"
ch := make(chan Event, 1_000_000)

// GOOD — small bound; the send blocks (or selects to drop) when behind.
ch := make(chan Event, 128)
select {
case ch <- ev:
case <-ctx.Done():
    return ctx.Err()
}
```

```rust
// BAD: tokio::sync::mpsc::unbounded_channel() in a request path.
// GOOD: mpsc::channel(cap) — and handle `send().await` taking time,
// or try_send + shed when latency matters more than completeness.
```

Channel discipline:
- **Capacity is a policy decision**: 0/1 = handoff/rendezvous (tightest
  coupling, best backpressure), small N = burst absorption, large N = latency
  hiding + delayed failure. Document the choice.
- **Close from the producer side only**; receivers detect closure
  (`for range ch`, `recv() -> None`). Go: send on closed channel panics;
  multiple producers need a `sync.WaitGroup` + closer goroutine, or don't
  close at all and signal via context.
- **Every blocking send/receive pairs with cancellation** (select on
  ctx.Done / `asyncio.wait_for` / AbortSignal), or it's a leak when the other
  side is gone. A goroutine blocked forever on a channel nobody reads is the
  canonical Go leak.
- Python `asyncio.Queue`: `Queue(maxsize=N)` — default is unbounded. Use
  `queue.join()` + `task_done()` for drain semantics; remember `get()` must be
  cancellable during shutdown.
- JS has no native channel; bounded behavior comes from async iterators with
  pull semantics or a library — `Array.push` into a shared array consumed by
  an interval is an unbounded queue in disguise.

## 6. Select / race patterns

`select` (Go), `tokio::select!`, `asyncio.wait(FIRST_COMPLETED)`,
`Promise.race` — wait on multiple sources, proceed with the first.

Hazards:
- **Loser leakage.** `Promise.race([op(), timeout()])` does not cancel the
  loser: `op()` keeps running, holding sockets. Pair race with cancellation —
  AbortSignal into `op`, cancel the losing asyncio task, drop the future in
  Rust (where drop *is* cancel — see below).
- **Partial-completion loss (tokio):** `select!` drops the non-winning
  futures. If a dropped future had buffered state (half-read message,
  half-sent write), it's gone. Loop-with-select must keep such futures
  outside the loop or use cancellation-safe operations only — check each
  awaited method's cancellation-safety documentation. This is the #1 subtle
  tokio bug class.
- **Starvation by ordering:** Go's `select` picks randomly among ready cases
  (good); `tokio::select!` is also randomized by default; hand-rolled
  "check A then B" loops starve B. If one branch must win ties (e.g.,
  shutdown), use `biased;` (tokio) or check it explicitly first.
- **asyncio:** `asyncio.wait(..., return_when=FIRST_COMPLETED)` returns
  pending tasks — you must cancel and await them. Forgetting is fire-and-forget.

```python
# GOOD — race with proper loser cleanup.
done, pending = await asyncio.wait(
    {asyncio.create_task(primary()), asyncio.create_task(fallback())},
    return_when=asyncio.FIRST_COMPLETED)
for t in pending:
    t.cancel()
await asyncio.gather(*pending, return_exceptions=True)  # reap, don't leak
result = done.pop().result()
```

## 7. Once / lazy init

One-time initialization under concurrency must be a primitive, not a flag:

- Rust: `OnceLock` / `LazyLock`. Go: `sync.Once` / `sync.OnceValue`.
  Java: holder class idiom or `volatile` + DCL (prefer the holder).
  Python threads: `threading.Lock` around init or module import-time init.
  JS single-threaded: a memoized promise.
- **Memoize the promise/future, not the value** in async code — otherwise N
  concurrent first-callers each run init (the cache-stampede micro version):

```js
// BAD — three concurrent callers → three connections, last one wins.
let conn;
async function getConn() {
  if (!conn) conn = await connect();   // await between check and act
  return conn;
}

// GOOD — store the promise synchronously; everyone awaits the same one.
let connPromise;
function getConn() {
  if (!connPromise) {
    connPromise = connect().catch(e => { connPromise = undefined; throw e; });
  }
  return connPromise;                  // note: failure resets for retry
}
```

- Beware **init that blocks inside Once** while other threads wait on it:
  if init can call back into something needing the same Once (or lock),
  that's a self-deadlock; `sync.Once` re-entry deadlocks.

## 8. Reentrancy & lock scope hygiene

- Recursive/reentrant mutexes paper over design problems and break invariant
  reasoning (the invariant may be broken when you re-enter). Avoid; refactor
  into `fooLocked()` internal methods called under the lock.
- Keep critical sections minimal: compute outside, lock, mutate, unlock. No
  I/O, no allocation-heavy work, no logging, no callbacks, no awaits inside.
- Guard data, not code: name the lock after the data it protects and keep
  them adjacent (`struct { mu sync.Mutex; cache map[...]... }`).

## Audit checklist

- [ ] Unbounded anything (§5): `Queue()` no maxsize, `unbounded_channel`,
      `make(chan T, huge)`, arrays used as queues, channels with
      goroutine-per-send. Each is MEDIUM minimum; HIGH on network-fed paths.
- [ ] Condvar waits: `if` instead of `while` around `wait()` (HIGH);
      predicate mutated outside the mutex; `notify_one` with heterogeneous
      waiters (§4).
- [ ] RwLock: recursive read acquisition; reader-storm writer starvation;
      upgrade patterns (state re-validated after release and re-acquire);
      would snapshot-swap be simpler? Chosen without read-heavy, measured
      contention, where a plain mutex is likely faster? (§2)
- [ ] Semaphores: released on all paths (RAII/finally)? Acquired with
      timeout/cancellation? Nested under another semaphore/pool without a
      global order? Memory-heavy work bounded by weight (bytes), not 1? (§3)
- [ ] Channel sends/receives without a cancellation branch; close() called
      from consumer side or from multiple producers (Go panic); capacity
      choice undocumented (§5).
- [ ] `Promise.race` / `select!` / `wait(FIRST_COMPLETED)`: are losers
      cancelled and reaped? Are tokio `select!` arms cancellation-safe?
      Hand-rolled "check A then B" loops starving B, or a shutdown branch that
      must win ties without `biased;` or an explicit first check? (§6)
- [ ] Lazy init: value memoized instead of future (stampede)? Failed init
      cached forever (permanent outage)? DCL without acquire/release? Init
      inside a Once that can call back into the same Once or lock
      (self-deadlock)? (§7)
- [ ] Primitive mismatches (§1), MEDIUM: read each hand-off and wait site for
      a shared list + lock + sleep-poll used as a queue, a polling loop
      waiting for a state change, a spin-checked counter bounding access, or
      two atomics guarding one invariant; replace with the table's "Use".
- [ ] Critical sections containing I/O, awaits, callbacks, or logging (§8).
- [ ] Reentrant locks or `fooLocked` conventions violated (double-acquire);
      critical sections doing more than lock, mutate, unlock (see the item
      above); lock not named after and declared next to the data it guards
      (§8).
