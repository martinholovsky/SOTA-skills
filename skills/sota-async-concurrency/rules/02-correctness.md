# 02 — Correctness: Races, Atomicity, Memory Ordering, Deadlock

## Data race vs race condition — different bugs, different fixes

- **Data race:** two threads access the same memory location concurrently,
  at least one writes, with no synchronization. In C/C++/Rust(unsafe)/Go this
  is undefined or corrupting behavior — torn reads, impossible values. Fix
  with synchronization (atomics, locks) or by removing sharing.
- **Race condition:** a correctness bug from *ordering*, even with perfectly
  synchronized individual accesses. A program can be 100% data-race-free and
  still race. Fix by making the whole multi-step operation atomic, not by
  adding more locks around the individual steps.

Single-threaded event loops eliminate data races but **not** race conditions:
every `await` is a yield point where other tasks run and mutate shared state.

```python
# RACE CONDITION, zero threads — classic async check-then-act.
# Task A and Task B both see cache miss, both fetch, B overwrites A.
# Worse with non-idempotent actions (double-charge, double-send).
async def get_user(uid):
    if uid not in cache:               # check
        cache[uid] = await fetch(uid)  # await = interleave point; act
    return cache[uid]

# GOOD — collapse to single-flight: first caller stores a future,
# concurrent callers await the same future. Check+act with no await between.
async def get_user(uid):
    fut = cache.get(uid)
    if fut is None:
        fut = asyncio.ensure_future(fetch(uid))
        cache[uid] = fut               # no await between check and act
    try:
        return await fut
    except Exception:
        cache.pop(uid, None)           # don't cache failures
        raise
```

## Atomicity: find the invariant, protect the whole transition

`count += 1` is read-modify-write: three steps, racy everywhere (yes, also in
CPython — the GIL serializes bytecodes, not statements; and `+=` on an
attribute is multiple bytecodes). The unit of protection is the **invariant**,
not the variable.

```go
// BAD — both fields individually atomic, invariant (sum constant) still
// violated: a reader between the two Stores sees money created/destroyed.
a.balance.Store(a.balance.Load() - amt)   // also a lost-update race itself
b.balance.Store(b.balance.Load() + amt)

// GOOD — one lock spans the whole invariant-preserving transition.
mu.Lock()
a.balance -= amt
b.balance += amt
mu.Unlock()
```

Heuristics:
- If two fields must change together, one lock (or one owner task) covers both.
- Atomics are for single-word counters/flags/pointers. The moment logic reads
  an atomic and then writes based on it, you need CAS-loop or a lock.
- Compound map ops (`check-then-insert`, `get-then-update`) need the map's
  lock across the compound, or a primitive that is compound-atomic
  (`dict.setdefault`, `sync.Map.LoadOrStore`, `compute_if_absent`, UPSERT).

## Check-then-act / TOCTOU

Any `if <state> then <act-on-state>` where state is shared (memory, file
system, DB, remote API) is suspect. The gap between check and act is the race
window — and on the filesystem it's also a security hole (symlink swap between
`access()` and `open()`).

| Bad pattern | Atomic replacement |
|---|---|
| `if not exists(path): create(path)` | `open(path, O_CREAT|O_EXCL)` / `mkdir` and handle EEXIST |
| `if key not in map: map[key] = v` | `setdefault` / `LoadOrStore` / `putIfAbsent` |
| `SELECT` then `INSERT` | `INSERT ... ON CONFLICT` / unique constraint + handle violation |
| `if balance >= amt: balance -= amt` | `UPDATE ... SET balance = balance - amt WHERE balance >= amt` and check rows-affected |
| `if not lock_file_exists: write lock_file` | `O_EXCL` create, or flock, or a real lease with expiry |

**Rule:** push atomicity to the system that owns the state (DB constraint,
atomic syscall, compound-atomic API). Checking first and acting second is only
valid as an optimization *before* an atomic operation, never as the guard.

## Memory visibility & ordering (the 20% you need)

On multicore hardware, writes by one thread are not visible to others in
program order unless synchronization establishes **happens-before**. Without
it: stale reads forever (compiler hoists the load), reordered writes
(initialization seen after the published pointer).

- Every lock release **happens-before** the next acquire of the same lock;
  channel send happens-before the corresponding receive; thread/task join
  happens-before the joiner's next read. Use these — they're why properly
  locked code "just works".
- A plain boolean `done` flag set by one thread and polled by another with no
  sync is broken in C/C++/Rust/Go/Java. Use an atomic with acquire/release
  (or the language default: Java `volatile`, Rust `AtomicBool` with
  `Release`/`Acquire`, Go — use `sync/atomic` or a channel; Go has no benign
  data races, the race detector is the law).
- `Relaxed`/`memory_order_relaxed` is for statistics counters only. If any
  control flow or other memory depends on the value, you need acq/rel. When
  in doubt, use the default sequentially-consistent ordering — correctness
  first, then profile.
- Double-checked locking is broken without an acquire-load/release-store on
  the pointer. Don't hand-roll it: use `Once`/`OnceLock`/`lazy_static`,
  `sync.Once`, Java holder idiom, `functools.cache` (rule 03).
- Python/JS note: the GIL / single thread gives you sequential consistency for
  free *within* the interpreter; this whole section applies to Python threads
  with free-threaded builds, to native extensions, and to shared
  ArrayBuffers (`Atomics.*` in JS).

```go
// BAD — data race AND visibility bug: `done` may never be observed as true
// by the reader (load hoisted out of the loop), and even when it is, the
// write to `result` is not guaranteed visible (no happens-before).
var result *Report
var done bool
go func() { result = compute(); done = true }()
for !done { runtime.Gosched() }   // may spin forever; result may be nil
use(result)

// GOOD — channel send happens-before receive: result is fully visible.
ch := make(chan *Report, 1)
go func() { ch <- compute() }()
use(<-ch)
```

The pattern generalizes: **publish via a synchronizing edge** (channel, lock,
atomic release-store, task join), never via a plain flag. The same bug in
Java is a non-volatile `done`; in C++ a non-atomic bool (UB); in Rust the
compiler simply refuses — which is the correct default to internalize.

## Deadlock

Requires all four Coffman conditions: mutual exclusion, hold-and-wait, no
preemption, circular wait. Break any one — in practice you break **circular
wait** (ordering) or **hold-and-wait** (timeouts/trylock).

```text
T1: lock(A); lock(B)        T2: lock(B); lock(A)     → cycle → deadlock
```

Prevention rules, in order of preference:
1. **One lock.** Two locks whose regions ever overlap are a design question
   before they are an ordering question.
2. **Global lock order.** Document it (e.g., "always account-lock before
   ledger-lock; for two accounts, lock lower ID first"). Enforce in debug
   builds if possible (lock-rank assertions, `tokio-console`, TSan).
3. **Never call unknown code while holding a lock** — callbacks, virtual
   methods, user-supplied closures, logging frameworks that might lock, and
   above all `await` (rule 07: lock-across-await).
4. **Hierarchies with timeouts at the boundary.** `try_lock` with backoff
   only as a last resort — it converts deadlock into livelock if everyone
   retries in lockstep (add jitter).
5. **Encapsulate the lock.** The lock that guards a resource is a private
   object owned by the code that manages the resource — never something a
   caller can also reach. Locking on a reachable object lets unrelated code
   join your lock order (deadlock), hold it indefinitely (denial of service),
   or mutate the state without it. Unsafe: `lock(this)` / `synchronized(this)`
   and Java `synchronized` methods on a type untrusted code can hold (they lock
   `this`; `static synchronized` locks the class object, reachable via
   `getClass()`); `lock(typeof(T))` / `synchronized(T.class)`; string literals
   or interned strings, and in Java boxed primitives/`Boolean` (shared
   instances); in Go, a `sync.Mutex` **embedded** in a struct promotes `Lock`/
   `Unlock` to every holder of the value — use a named unexported field
   (`mu sync.Mutex`). Safe: `private final Object lock = new Object()` (Java),
   `private readonly Lock _lock = new()` (C# 13/.NET 9+, else a private
   `object`), and in Python a `_lock` attribute never returned or documented.
   OWASP: ASVS 5.0 V15.4.3.

```python
# GOOD — canonical two-resource ordering by stable key.
first, second = sorted((acct_a, acct_b), key=lambda a: a.id)
with first.lock, second.lock:
    transfer(acct_a, acct_b, amt)
```

Async deadlocks need no locks at all: two tasks awaiting each other's results;
a task awaiting a queue item that only it would produce; `gather` inside a
handler waiting on a pool slot held by its own parent; a bounded channel
where the consumer awaits the producer's reply on the same full channel.
Audit the **wait-for graph**, not just the mutexes.

## Livelock & starvation

- **Livelock:** everyone busy, nobody progresses (mutual try-lock-retry,
  retry storms in lockstep). Fix: randomized backoff (jitter), or impose
  asymmetry (one side wins ties).
- **Starvation:** some waiter never gets the resource. Sources: RwLock
  readers starving writers (rule 03), unfair locks under high contention,
  priority tasks monopolizing the loop, a `select` with a always-ready branch
  shadowing others. Fix: fair/queued primitives, bounded work per turn, or
  explicit rotation.

## Idempotency under retries

Every retry (and every at-least-once queue) means your operation can execute
**twice**. Concurrency-correct code is idempotent or deduplicated:

- Give mutations an **idempotency key**; store processed keys transactionally
  with the effect (same DB transaction — a separate "did I do this" check is
  TOCTOU again).
- Make handlers natural no-ops on repeat: `SET state = 'shipped'` not
  `count = count + 1`; `INSERT ... ON CONFLICT DO NOTHING`.
- A timeout does **not** mean the operation failed — it means you don't know.
  Retrying a timed-out non-idempotent call without a dedupe key is a
  double-charge bug (HIGH in audits).

## Async-signal-safety (pointer)

Signal handlers (POSIX) may only call async-signal-safe functions — no
malloc, no printf, no locks (the interrupted thread may hold them → instant
self-deadlock). Correct pattern: handler sets a `volatile sig_atomic_t` flag
or writes one byte to a self-pipe/eventfd; the main loop reacts. In
Python/Go/Rust runtimes, use the runtime's signal facilities
(`asyncio.loop.add_signal_handler`, `signal.Notify`, `tokio::signal`) — never
do real work in a raw handler.

## Audit checklist

- [ ] Every shared mutable variable: what synchronizes it? "It's just a flag"
      is not an answer in threaded code (visibility).
- [ ] Grep for read-modify-write on shared state: `+=`, `count++`,
      `x = x + `, `append` to shared slices/lists from multiple tasks.
- [ ] Check-then-act sweep: `if ... in` / `exists(` / `has(` followed by a
      mutation of the same state — is the pair atomic? Includes
      filesystem (TOCTOU) and SELECT-then-INSERT.
- [ ] In async code: any await between a check and its act? Any shared-state
      invariant temporarily broken across an await?
- [ ] Multi-lock code: is there a documented order? Build the lock graph from
      the call sites; any cycle is CRITICAL.
- [ ] Callbacks/virtual calls/logging/awaits inside lock regions?
- [ ] Lock reachable by outside code (rule 5; HIGH where untrusted or
      plugin code can reach the object, else MEDIUM):
      `grep -rnE '(^|[^A-Za-z0-9_])(lock|synchronized) *\( *((this|getClass\(\)|[A-Za-z_][A-Za-z0-9_]*\.class) *\)|"|typeof *\()|(public|protected)( [a-z]+)* synchronized |synchronized( [a-z]+)* (public|protected) |^[[:space:]]+\*?sync\.(RW)?Mutex[[:space:]]*(//.*)?$' --include='*.cs' --include='*.java' --include='*.kt' --include='*.go' .`
      — a Go hit is an embedded mutex; confirm the enclosing type escapes.
- [ ] Wait-for cycles without locks: tasks awaiting each other, self-feeding
      queues, pool-within-pool acquisition.
- [ ] RwLocks under write-heavy or reader-storm load: starvation analysis.
- [ ] Every retried or queued mutation: idempotency key or natural
      idempotence? Timeout treated as "unknown", not "failed"?
- [ ] Atomics: any load-then-write-based-on-it that isn't a CAS loop? Any
      `Relaxed` ordering guarding non-counter data?
- [ ] Signal handlers doing more than set-flag/write-byte?
