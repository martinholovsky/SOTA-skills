# 03 — Concurrency: virtual threads, the JMM, j.u.c, coroutines

The JVM is memory-safe but not race-free: the Java Memory Model (JMM) defines
when one thread's writes are visible to another, and code that ignores it has
real, nondeterministic bugs. Java 21+ adds virtual threads; Kotlin has
coroutines. References:
[Java 25 core docs](https://docs.oracle.com/en/java/javase/25/core/),
[Kotlin coroutines](https://kotlinlang.org/docs/coroutines-overview.html).

## 1. The Java Memory Model essentials

- A **data race** (two threads access the same field, ≥1 writes, no
  happens-before) yields undefined visibility — a thread may see a stale value
  forever. Fix by establishing happens-before, not by hoping.
- Establish ordering via: `synchronized`/`ReentrantLock`, `volatile` (visibility
  + ordering for a single field, no compound atomicity), `final` fields (safe
  publication after construction), or `java.util.concurrent` types (which carry
  the guarantees).
- `volatile` gives visibility but **not** atomic compound actions
  (`count++` on a volatile is still a race) — use `AtomicInteger`/`LongAdder`.
- Prefer immutability (`rules/01`) and confinement; the cheapest safe sharing is
  no shared mutable state.

## 2. Prefer high-level concurrency utilities

- Use `java.util.concurrent`: `ExecutorService`/`ThreadPoolExecutor`,
  `ConcurrentHashMap`, `BlockingQueue`, `CompletableFuture`, `CountDownLatch`,
  `Semaphore`, atomics. Don't hand-roll wait/notify or lock protocols.
- `CompletableFuture` for async composition (`thenCompose`/`thenCombine`);
  always supply an explicit executor and handle `exceptionally`/`handle` —
  default common-pool + swallowed exceptions is a trap.
- Lock with try/finally or prefer `ReentrantLock` with `lock()`/`unlock()` in
  finally; keep critical sections small; acquire multiple locks in a global
  order to avoid deadlock.

## 3. Virtual threads (Java 21+, finalized JEP 444)

- Virtual threads make thread-per-request with blocking I/O scale — millions of
  cheap threads scheduled by the JVM. Use them for I/O-bound concurrency:
  `Executors.newVirtualThreadPerTaskExecutor()`.
- **Don't pool virtual threads** (they're cheap; pooling defeats the point) and
  **don't pin the carrier**: a `synchronized` block/method around a *blocking*
  call pins the carrier thread (improved in 24+, but still prefer
  `ReentrantLock` around blocking sections). Avoid heavy `ThreadLocal` use.
- CPU-bound work still wants a bounded platform-thread pool sized to cores.
- **Scoped values** (`ScopedValue`) are **final in Java 25** (JEP 506) — safe
  to recommend as GA. **Structured concurrency** (`StructuredTaskScope`) is
  still *preview* (JEP 505 in 25; previews continue in later JDKs) — use
  behind a preview flag, note it's not yet stable, and don't recommend it as
  GA.

## 4. Kotlin coroutines

- Coroutines are structured by default: launch in a `CoroutineScope` tied to a
  lifecycle; child coroutines are cancelled with the parent. Never use
  `GlobalScope` (unstructured leak).
- Pick the right dispatcher: `Dispatchers.IO` for blocking I/O,
  `Dispatchers.Default` for CPU work, `Main` for UI. `withContext` to switch.
- **Cooperative cancellation**: check `isActive`/`ensureActive()` or use
  cancellable suspend funcs; never catch-and-swallow `CancellationException`
  (rethrow it). Use `withTimeout` for deadlines.
- Don't block a coroutine thread (`Thread.sleep`, blocking JDBC) without
  `Dispatchers.IO`; prefer suspending APIs. `Flow` for async streams with
  backpressure.

## 5. Tooling

- Run concurrent tests deterministically where possible; use jcstress for
  low-level memory-model tests, and stress/load tests for races. SpotBugs flags
  some concurrency bugs (e.g. inconsistent synchronization); Error Prone has
  `@GuardedBy` checking.

## Audit checklist

```bash
# Data-race smells — MEDIUM/HIGH (verify happens-before)
grep -rnE '\bstatic (?!final)[A-Za-z<>\[\]]+ [a-z]' --include='*.java' .   # mutable shared static
grep -rnE 'volatile ' --include='*.java' . | grep -E '\+\+|--|\+='          # compound op on volatile = race
grep -rn 'HashMap\|ArrayList' --include='*.java' . | grep -i 'static\|shared'  # non-concurrent shared coll

# Virtual-thread pitfalls — HIGH under load
grep -rn 'newVirtualThreadPerTaskExecutor\|Thread.ofVirtual' --include='*.java' .
grep -rnE 'synchronized' --include='*.java' . | grep -i 'block\|io\|http\|jdbc'  # pinning risk → ReentrantLock
grep -rn 'preview' --include='*.java' .   # structured concurrency is preview in 25

# CompletableFuture without executor/exception handling — MEDIUM
grep -rnE 'CompletableFuture\.(supplyAsync|runAsync)\([^,)]*\)' --include='*.java' .   # no explicit executor

# Kotlin coroutine hazards — MEDIUM/HIGH
grep -rn 'GlobalScope' --include='*.kt' .                       # unstructured leak
grep -rnE 'catch *\([^)]*CancellationException' --include='*.kt' .  # must rethrow
grep -rnE 'runBlocking|Thread.sleep' --include='*.kt' .         # blocking in coroutine context

# Bare lock without finally — MEDIUM
grep -rnE '\.lock\(\)' --include='*.java' --include='*.kt' .    # verify unlock in finally
```
