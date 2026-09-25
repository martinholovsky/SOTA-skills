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
- **The `Executors` shortcuts are unbounded.** The JDK Javadoc says `newFixedThreadPool`
  runs "off a shared unbounded queue" and `newSingleThreadExecutor` "off an unbounded
  queue". `newCachedThreadPool` "creates new threads as needed". A `LinkedBlockingQueue`
  constructed with no capacity is bounded only by `Integer.MAX_VALUE`. Under load these
  turn a slow dependency into heap exhaustion or thread exhaustion instead of a rejection
  the caller can see. For work arriving from outside, build a `ThreadPoolExecutor` with a
  bounded `ArrayBlockingQueue` (or a sized `LinkedBlockingQueue`) and an explicit
  `RejectedExecutionHandler`. A virtual-thread-per-task executor has no pool to bound, so
  cap concurrency with a `Semaphore` around the scarce resource. The general rule is
  `sota-async-concurrency` (backpressure).

## 3. Virtual threads (Java 21+, finalized JEP 444)

- Virtual threads make thread-per-request with blocking I/O scale — millions of
  cheap threads scheduled by the JVM. Use them for I/O-bound concurrency:
  `Executors.newVirtualThreadPerTaskExecutor()`.
- **Don't pool virtual threads** (they're cheap; pooling defeats the point).
- **Pinning is version-conditional**: on JDK 21–23 a `synchronized` block/
  method around a *blocking* call pins the carrier thread — HIGH under load;
  use `ReentrantLock`. Since JDK 24 (JEP 491) monitors no longer pin. The cases JEP 491
  leaves pinned are a native frame on the stack (a JNI/FFM callback), blocking while
  resolving and loading a class, blocking inside a class initializer, and waiting for a class
  that another thread is still initializing. So slow I/O in a `static {}` block or a Kotlin
  `companion object` initializer still pins. Keep the `ReentrantLock` advice only for code
  that must support 21 LTS. Avoid heavy `ThreadLocal` use.
- **Request-scoped ambient state is reset in `finally`, or it leaks to the next tenant.** A
  tenant id, user or locale in a `ThreadLocal`, or a logging `MDC` entry, rides the pooled
  platform thread into the next request. Measured on Temurin 25.0.4: a 1-thread pool task set
  `tenant-A` without `remove()` and the next task read `tenant-A`, while `remove()` in `finally`
  read `null`. A virtual-thread-per-task executor read `null`, but servlet worker pools and any
  `ExecutorService` reuse threads. `InheritableThreadLocal` copies once, at thread creation: a
  pool thread kept `tenant-D` after the parent switched to `tenant-E`. Use
  `try { set } finally { remove() }`, `MDC.putCloseable` in try-with-resources or `MDC.clear()`
  in a filter's `finally` (slf4j-api 2.0.20), or `ScopedValue.where(K, v).run(...)` (final in
  25), which unbinds on exit. Spring's `RequestContextFilter` already resets its holder in
  `finally`; your own holders need the same. OWASP: Multi-Tenant Security cheat sheet.
- **In a coroutine, `ThreadLocal` and `MDC` belong to whichever thread resumes it.** A coroutine
  can suspend on one thread and resume on another. A value set with `ThreadLocal.set` or
  `MDC.put` is missing after the suspension point, and it stays behind on the old thread for
  the next coroutine to read: the same cross-tenant leak as above. Carry the value in the
  coroutine context instead. Use `withContext(MDCContext()) { ... }` (kotlinx-coroutines-slf4j)
  for MDC and `withContext(tl.asContextElement(value)) { ... }` for your own `ThreadLocal`.
  Both restore the thread's previous value when the coroutine leaves the thread. Never
  `MDC.put` or `ThreadLocal.set` inside suspending code and expect the value to survive. The
  `MDCContext` docs say an `MDC.put` inside the coroutine "will be lost on the next suspension".
  The `asContextElement` docs say the element "does not track modifications of the
  thread-local". To change a value mid-coroutine, open a nested `withContext(MDCContext())` or
  `withContext(tl.asContextElement(newValue))` right after the change
  ([MDCContext](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-slf4j/kotlinx.coroutines.slf4j/-m-d-c-context/),
  [asContextElement](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/as-context-element.html)).
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
- **A catch-all in suspending code swallows cancellation too.** `CancellationException` is
  an `IllegalStateException`, so `catch (e: Exception)` catches it. So do
  `catch (e: Throwable)` and `runCatching`, which the stdlib documents as "catching any
  `Throwable`". The handler then turns a cancellation into an ordinary result (a fallback
  value, a logged "error"), and the code keeps running until its next suspension point. In a
  `suspend fun`, either rethrow first
  (`catch (e: CancellationException) { throw e }` ahead of the broad catch) or call
  `currentCoroutineContext().ensureActive()` inside the handler. Otherwise catch the specific
  exception types. Suspending cleanup in `finally` runs inside `withContext(NonCancellable)`;
  never pass `NonCancellable` to `launch`/`async`, because that detaches the child from its
  parent ([cancellation and timeouts](https://kotlinlang.org/docs/cancellation-and-timeouts.html)).
- **Know where each builder's exception goes**
  ([exception handling](https://kotlinlang.org/docs/exception-handling.html)).
  - `async` stores its failure in the `Deferred` until `await()`. A root `async` that nobody
    awaits loses the exception. Inside a scope, a failing child still cancels its parent, and
    `await()` rethrows the failure too.
  - Every child hands its exception up to the root. A `CoroutineExceptionHandler` placed on a
    child's context "is never used", so install it on the root `launch` or on the scope.
  - Under `SupervisorJob`/`supervisorScope` a child's failure does not reach the parent.
    Each child has to handle its own exceptions, with try/catch or a handler in the
    supervisor's scope. If it doesn't, the failure is silent apart from the default
    uncaught-exception log line.
- Don't block a coroutine thread (`Thread.sleep`, blocking JDBC) without
  `Dispatchers.IO`; prefer suspending APIs. `Flow` for async streams with
  backpressure.

## 5. Tooling

- Run concurrent tests deterministically where possible; use jcstress for
  low-level memory-model tests, and stress/load tests for races. SpotBugs flags
  some concurrency bugs (e.g. inconsistent synchronization); Error Prone has
  `@GuardedBy` checking.

## Audit checklist

- [ ] **Data-race smells — MEDIUM/HIGH (verify happens-before)** —
      `grep -rnE '^[[:space:]]*((public|private|protected)[[:space:]]+)?static[[:space:]]+[A-Za-z_][A-Za-z0-9_<>,?. ]*(\[\])?[[:space:]]+[a-z][A-Za-z0-9_]*[[:space:]]*(=|;)' --include='*.java' . | grep -vwE 'final|class|interface|enum|record'` (mutable shared
      static; the old `(?!final)` form exited 2, POSIX ERE has no lookahead); `grep -rnE 'volatile |@Volatile' --include='*.java' --include='*.kt' . | grep -E '\+\+|--|\+='` (compound op
      on volatile = race);
      `grep -rnE 'HashMap|ArrayList|mutable(Map|List|Set)Of' --include='*.java' --include='*.kt' . | grep -iE 'static|shared|object|companion'`
      (non-concurrent shared coll) ;
      `grep -rnE '^(private |internal |public )?(@Volatile )?var[[:space:]]' --include='*.kt' .`
      (Kotlin has no `static`: a top-level `var` is the same process-wide mutable state; also
      read `var`s inside `object`/`companion object` bodies)
- [ ] **Virtual-thread pitfalls** —
      `grep -rn 'newVirtualThreadPerTaskExecutor\|Thread.ofVirtual' --include='*.java' --include='*.kt' .` ;
      `grep -rnE 'synchronized|@Synchronized' --include='*.java' --include='*.kt' . | grep -iE 'block|java\.io|InputStream|OutputStream|Socket|http|jdbc'`
      (Kotlin spells it `@Synchronized` or `synchronized(lock) { }`. Pinning is HIGH on JDK
      21–23 and a non-issue on 24+ (JEP 491), except the native, class-loading and class-init
      cases in §3);
      `grep -rnE 'enable-preview|StructuredTaskScope' --include='*.java' --include='*.kt' --include='pom.xml' --include='*.gradle*' .`
      (structured concurrency is preview in 25)
- [ ] **CompletableFuture without executor/exception handling — MEDIUM** —
      `grep -rnE 'CompletableFuture\.(supplyAsync|runAsync)\([^,)]*\)' --include='*.java' --include='*.kt' .` (no
      explicit executor)
- [ ] **Kotlin coroutine hazards — MEDIUM/HIGH** — `grep -rn 'GlobalScope' --include='*.kt' .`
      (unstructured leak); `grep -rnE 'catch *\([^)]*CancellationException' --include='*.kt' .`
      (must rethrow); `grep -rnE 'runBlocking|Thread.sleep' --include='*.kt' .` (blocking in
      coroutine context)
- [ ] **Catch-all swallowing cancellation in suspending code — HIGH (the coroutine outlives its
      cancel and timeout)** (§4) —
      `grep -rlE 'suspend fun' --include='*.kt' . | while IFS= read -r f; do grep -nHE 'catch[[:space:]]*\([^)]*:[[:space:]]*(java\.lang\.|kotlin\.)?(Exception|Throwable)[[:space:]]*\)|runCatching' "$f"; done`
      (a hit passes only when the handler rethrows `CancellationException` or calls
      `ensureActive()`; a non-suspending function in the same file is a false positive to read
      past)
- [ ] **Coroutine exceptions with nowhere to go — MEDIUM, HIGH when the lost failure is a
      write** (§4) —
      `grep -rlE '(^|[^[:alnum:]_])async[[:space:]]*[({]' --include='*.kt' . | while IFS= read -r f; do grep -qE 'await(All)?\(' "$f" || echo "$f"; done`
      (an `async` whose `Deferred` is never awaited in the file) ;
      `grep -rnE 'CoroutineExceptionHandler|SupervisorJob\(|supervisorScope' --include='*.kt' .`
      (a handler must sit on the root coroutine or scope; every supervised child needs its own
      try/catch or a handler)
- [ ] **ThreadLocal / MDC set inside coroutines without a context element — HIGH when it holds a
      tenant or user** (§3) —
      `grep -rlE 'suspend fun|launch[[:space:]]*[({]|async[[:space:]]*[({]' --include='*.kt' . | while IFS= read -r f; do grep -nHE 'MDC\.(put|setContextMap)\(|ThreadLocal<' "$f" | grep -vE 'MDCContext|asContextElement'; done`
      (each `MDC.put` must be followed by a `withContext(MDCContext())` that carries it; each
      `ThreadLocal` declared here: find its `.set(` calls and confirm the value travels as
      `asContextElement(...)`)
- [ ] **Unbounded executors and queues (no backpressure) — MEDIUM, HIGH on a request
      path** (§2) —
      `grep -rnE 'Executors\.new(Fixed|Cached)ThreadPool\(|Executors\.newSingleThreadExecutor\(|new LinkedBlockingQueue(<[^>]*>)?\(\)|newVirtualThreadPerTaskExecutor\(' --include='*.java' --include='*.kt' .`
      (each needs a stated bound: a capacity plus a rejection policy, or a `Semaphore`
      around what the tasks consume; a sized `new LinkedBlockingQueue<>(1000)` does not
      match)
- [ ] **ThreadLocal / MDC request state never removed — HIGH when it holds a tenant or user
      (cross-tenant leak on a pooled thread)** (§3) —
      `grep -rlE 'ThreadLocal<|MDC\.put\(' --include='*.java' --include='*.kt' . | while IFS= read -r f; do grep -qE '\.remove\(\)|MDC\.(clear|remove)\(' "$f" || echo "$f"; done`
      (each printed file sets ambient state with no reset in it; a reset elsewhere must be in a
      `finally` on every request path)
- [ ] **Bare lock without finally — MEDIUM** —
      `grep -rnE '\.lock\(\)' --include='*.java' --include='*.kt' .` (verify unlock in finally)