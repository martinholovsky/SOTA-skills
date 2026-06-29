# 05 — Concurrency: the memory model, races, atomics, locks

A **data race** — two threads accessing the same non-atomic object, at least
one writing, with no happens-before ordering — is undefined behavior in both C
and C++ (`rules/03`), not merely a stale read. The optimizer assumes
race-freedom, so a race can corrupt unrelated state. Synchronize all shared
mutable state, or make it `atomic`. Build threaded code under ThreadSanitizer.
Reference: [cppreference memory model](https://en.cppreference.com/w/cpp/language/memory_model).

## 1. Default: don't share mutable state

- Prefer message passing, ownership transfer (move a `unique_ptr` to the
  worker), or immutable shared data over shared mutable state. The cheapest
  race to fix is the one you don't create.
- Confine mutable data to one thread; communicate via queues. If you must
  share, every access goes through one synchronization discipline documented at
  the type.

## 2. Mutexes and RAII locking

- Lock with RAII: `std::lock_guard` (simple scope), `std::scoped_lock` (one or
  more mutexes, deadlock-free acquisition), `std::unique_lock` (when you need
  to unlock early or move). Never bare `mutex.lock()`/`unlock()` — an exception
  or early return leaks the lock.
- **Lock ordering**: acquire multiple mutexes in a single global order, or use
  `std::scoped_lock(m1, m2)` which avoids the deadlock. Document the order.
- Keep critical sections small; never call user callbacks, allocate heavily, or
  block on I/O while holding a lock. Don't hold a lock across a `condition_
  variable` wait except via the `unique_lock` it manages.
- `std::condition_variable`: always wait with a predicate
  (`cv.wait(lk, [&]{ return ready; })`) to handle spurious wakeups and lost
  wakeups; signal after mutating the shared state under the lock.

```cpp
// GOOD — RAII lock, predicate wait
std::mutex m; std::condition_variable cv; bool ready=false;
void producer(){ { std::lock_guard lk(m); ready=true; } cv.notify_one(); }
void consumer(){ std::unique_lock lk(m); cv.wait(lk, []{return ready;}); use(); }
```

## 3. Atomics and memory order

- `std::atomic<T>` for lock-free flags/counters. Default operations use
  `memory_order_seq_cst` — correct and the right starting point. Only weaken
  (acquire/release, relaxed) with a written justification and a model in mind;
  relaxed atomics are an expert tool and a frequent source of subtle bugs.
- Use atomics for the *synchronization variable*; the data it publishes is made
  visible by the acquire/release pairing. A non-atomic flag checked across
  threads is a race even if "it's just a bool".
- `volatile` is **not** for threading — it does not provide atomicity or
  ordering (it's for memory-mapped I/O / signal handlers). Using `volatile` as
  a thread-sync mechanism is a bug.
- Prefer higher-level tools where they fit: `std::atomic_ref` (C++20) for
  atomic ops on non-atomic storage, `std::latch`/`std::barrier`/`std::
  counting_semaphore` (C++20) for coordination.

## 4. Threads, futures, and cancellation

- Prefer `std::jthread` (C++20) over `std::thread`: it joins in its destructor
  (no `std::terminate` from a forgotten join) and carries a `std::stop_token`
  for cooperative cancellation. A bare `std::thread` not joined/detached before
  destruction calls `std::terminate`.
- Pass data to threads by value or via owned handles; capturing references/
  `[&]` into a thread that outlives the scope is a dangling-reference race
  (`rules/02`).
- `std::async` with `std::launch::async` for simple fan-out + `future.get()`;
  beware the returned future's destructor blocks. For pools, use a vetted
  library (oneTBB, a thread-pool lib) rather than hand-rolling.
- Watch for false sharing: hot per-thread counters on the same cache line
  serialize; pad/align to `std::hardware_destructive_interference_size`
  (`rules/07`).

## 5. Tooling

- **TSan** (`-fsanitize=thread`) is the ground truth for races and lock-order
  inversions — run the concurrent tests under it in CI. It's mutually exclusive
  with ASan (separate job) and has memory/latency overhead.
- `-Wthread-safety` (Clang thread-safety annotations: `GUARDED_BY`,
  `REQUIRES`) gives compile-time race checking when you annotate. Helgrind
  (Valgrind) is a no-recompile alternative to TSan.

## Audit checklist

```bash
# Bare lock/unlock (no RAII) — MEDIUM/HIGH (lock leak on exception)
grep -rnE '\.(lock|unlock)\(\)' --include='*.cpp' .            # prefer lock_guard/scoped_lock
grep -rn 'pthread_mutex_lock' --include='*.c' --include='*.cpp' .

# volatile used for threading — HIGH (not a sync primitive)
grep -rn 'volatile' --include='*.cpp' --include='*.c' . | grep -iE 'flag|ready|done|count|shared'

# Unjoined std::thread / detached without lifetime reasoning — MEDIUM
grep -rn 'std::thread' --include='*.cpp' . | grep -v jthread     # verify join/detach + arg lifetimes
grep -rn '\.detach()' --include='*.cpp' .

# Relaxed/weak memory order without justification — MEDIUM
grep -rnE 'memory_order_(relaxed|acquire|release|consume)' --include='*.cpp' .

# condition_variable wait without predicate — MEDIUM (spurious/lost wakeup)
grep -rnE 'cv?\.wait\([^,)]*\)' --include='*.cpp' .              # one-arg wait == no predicate

# Ground truth: run concurrent tests under TSan
#   cmake -DCMAKE_CXX_FLAGS="-fsanitize=thread" && ctest   # any race report == CRITICAL
```
