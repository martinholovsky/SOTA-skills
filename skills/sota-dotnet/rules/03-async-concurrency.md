# 03 — Async/await and concurrency

`async`/`await` is the .NET concurrency model, and misusing it causes the two
classic production failures: **deadlocks** (blocking on async under a sync
context) and **thread-pool starvation** (sync-over-async at scale). The rules
are mechanical — follow them. Reference:
[async guidance](https://learn.microsoft.com/en-us/dotnet/csharp/asynchronous-programming/).

## 1. Async all the way; never block on async

- Once a call chain is async, keep it async to the entry point. **Never** block:
  `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` on a Task in request/UI/hot
  paths deadlocks under a sync context (classic ASP.NET/UI) and starves the
  thread pool under load. CRITICAL/HIGH depending on reachability.
- Expose async APIs (`...Async`) for I/O; don't wrap sync I/O in `Task.Run` to
  "make it async" on the server (it just burns a thread).

## 2. ConfigureAwait

- In **library** code (no dependence on a sync context), `await ... .ConfigureAwait(false)`
  so continuations don't capture/marshal back to a context — avoids deadlocks
  and overhead. In app code (ASP.NET Core has no sync context; modern UI differs)
  it matters less, but libraries should always do it.

## 3. async void and exceptions

- **`async void`** only for event handlers. Elsewhere it's fire-and-forget with
  unobservable exceptions that can crash the process — use `async Task`. A
  non-handler `async void` is a MEDIUM–HIGH finding.
- Don't fire-and-forget Tasks without observing them (lost exceptions, no
  back-pressure). If intentional, document and handle faults.

## 4. CancellationToken everywhere

- Flow a `CancellationToken` through every async method and pass it to inner
  calls (I/O, EF Core, HttpClient); honor it (`ThrowIfCancellationRequested`,
  or the token-aware API). Endpoints should bind the request-aborted token.
  Ignoring cancellation wastes work and delays shutdown.

## 5. Concurrency primitives

- Shared mutable state needs synchronization: `lock` (don't `await` inside a
  `lock` — use `SemaphoreSlim` for async mutual exclusion), `Interlocked` for
  counters, `Concurrent*` collections (`ConcurrentDictionary`) over manual
  locking. Immutability avoids the problem.
- `System.Threading.Channels` (`Channel<T>`) for producer/consumer with
  back-pressure; `IAsyncEnumerable<T>` + `await foreach` for async streams.
- `Task.WhenAll` for parallel awaits (observe all exceptions — `WhenAll`
  aggregates); `Parallel.ForEachAsync` for bounded data parallelism. Don't
  spin unbounded concurrent work — bound it (`SemaphoreSlim`, channel,
  `Parallel` options).
- `ValueTask` for very hot, often-synchronous paths — but don't await a
  `ValueTask` twice or store it (`rules/05`).
- **Request-scoped ambient state (tenant, user, culture, log scope).** Pool threads carry
  thread-local state into whichever request runs on them next. Measured on .NET 10 Kestrel: after
  a request set a `[ThreadStatic]` field and did not clear it, 9 of 20 later requests read
  `leaked`. The same applies to `ThreadLocal<T>` and to static fields in a singleton, so never
  keep per-request data in any of them. **`AsyncLocal<T>`** follows the async flow instead
  (`IHttpContextAccessor` is built on it). A value set in middleware did not reach the next
  request on the same keep-alive connection (measured). It has three traps, all measured:
  - A value set inside an `async` method is gone when the caller resumes, but a value set in a
    **synchronous** helper stays set for the caller.
  - `Task.Run` and a `new Timer` started during a request **capture** the value. Background work
    started from a request keeps running as that tenant until you start it inside
    `using (ExecutionContext.SuppressFlow())`, which it then saw as `null`.
  - Nothing clears a value you set. Restore the previous value in a `finally`.

  Prefer a scoped DI service (`AddScoped<TenantContext>()`), which the container disposes with
  the request. `ILogger.BeginScope` returns an `IDisposable`, so open it only in a `using`. *(OWASP: Multi-Tenant Security and Session Management cheat sheets.)*

## 6. Testable time and the `Lock` type

- **Inject `TimeProvider` (in the BCL since .NET 8) instead of reading the clock.** Code that
  calls `DateTime.UtcNow`/`DateTimeOffset.UtcNow`, or waits with `Task.Delay(TimeSpan)`, can only
  be tested by waiting in real time. Take a `TimeProvider`, register `TimeProvider.System` as a
  singleton, and use `GetUtcNow()`, `GetTimestamp()`/`GetElapsedTime()`, `CreateTimer`, and the
  overloads that accept one: `Task.Delay(TimeSpan, TimeProvider[, CancellationToken])`,
  `Task.WaitAsync(TimeSpan, TimeProvider)`, and `new CancellationTokenSource(TimeSpan,
  TimeProvider)`. In tests, `FakeTimeProvider` from `Microsoft.Extensions.TimeProvider.Testing`
  moves time forward with `Advance`. Measured on .NET 10: a one-hour
  `Task.Delay(TimeSpan.FromHours(1), fake)` was still pending before `fake.Advance(1h)` and
  complete after it, with no wall-clock wait. Targets older than .NET 8 (including .NET Framework
  4.6.2+ and .NET Standard 2.0) get it from the `Microsoft.Bcl.TimeProvider` package (Microsoft
  Learn, "What is the TimeProvider class").
- **On .NET 9+ / C# 13, lock a dedicated `System.Threading.Lock`.** Declare
  `private readonly Lock _gate = new();`. A `lock (_gate)` statement then compiles to
  `_gate.EnterScope()` rather than `Monitor`, and Microsoft recommends it for best performance.
  Convert the `Lock` to `object` or any other type and `lock` silently falls back to `Monitor`.
  The compiler flags that as **CS9216** (reproduced on SDK 10.0.401), and
  `TreatWarningsAsErrors` turns it into a build break. On older targets, lock a dedicated private
  `object`. On every target, never lock `this`, a `Type` (`typeof`), or a string, because other
  code can take the same lock. You still cannot `await` inside `lock`; use `SemaphoreSlim` (§5).
  (Microsoft Learn, "The lock statement".)

## Audit checklist

- [ ] **Blocking on async — CRITICAL/HIGH (deadlock / thread-pool starvation)** —
      `grep -rnE '\.(Result|Wait\(\))|GetAwaiter\(\)\.GetResult\(\)' --include='*.cs' . | head`
      ; `grep -rnE 'Task\.Run\(' --include='*.cs' . | head` (sync wrapped as async on server?)
- [ ] **async void (non-handler) — MEDIUM/HIGH** —
      `grep -rnE 'async void ' --include='*.cs' . | grep -vE 'EventHandler|_Click|[[:space:]]On[A-Z][[:alnum:]_]*\('`
      (case-sensitive on purpose: `-i` would also drop `ContinueProcessing(`; confirm each
      remaining hit is not a handler whose name misses the convention)
- [ ] **Missing ConfigureAwait(false) in libraries — MEDIUM** —
      `grep -rnE 'await ' --include='*.cs' . | grep -v 'ConfigureAwait' | head` (in library
      projects)
- [ ] **Cancellation not flowed — MEDIUM** —
      `grep -rnE 'async Task[<A-Za-z, >]* [A-Za-z]+\([^)]*\)' --include='*.cs' . | grep -v 'CancellationToken' | head`
- [ ] **await inside lock — HIGH (won't compile for lock, but SemaphoreSlim misuse /
      sync-over-async)** — `grep -rnE 'lock\s*\(' --include='*.cs' . | head` ;
      `grep -rnE 'new (Dictionary|List)<' --include='*.cs' . | grep -i 'static\|shared'`
      (non-concurrent shared)
- [ ] **Unbounded parallelism — MEDIUM (verify bounding)** —
      `grep -rnE 'Task\.WhenAll|Parallel\.(For|ForEach)' --include='*.cs' . | head`
- [ ] **Request-scoped state in thread-local or `AsyncLocal` storage — HIGH in a multi-tenant
      service (cross-tenant leak)** (§5) —
      `grep -rnE '\[ThreadStatic\]|ThreadLocal<|AsyncLocal<|ExecutionContext\.SuppressFlow|CallContext\.' --include='*.cs' .`
      (a thread-local holding tenant/user data is the finding. An `AsyncLocal` must be set in
      async code and restored in `finally`, and background work started from a request needs
      `SuppressFlow`; prefer a scoped DI service)
- [ ] **Clock read directly in production code — LOW (untestable time logic; MEDIUM where
      expiry or lockout decisions depend on it)** (§6) —
      `grep -rnE 'DateTime(Offset)?\.(Utc)?Now' --include='*.cs' . | grep -viE 'test'`
      (each hit in expiry, retry, rate or scheduling logic should take a `TimeProvider`; the
      filter drops every line containing "test", in its path or its code)
- [ ] **Lock target shared or not a `Lock` — MEDIUM for `this`/`typeof`/string, INFO for a
      plain `object` on .NET 9+** (§6) —
      `grep -rnE 'object[[:space:]]+_?[A-Za-z0-9_]+[[:space:]]*=[[:space:]]*new([[:space:]]*object)?\(\)|lock[[:space:]]*\((this|typeof\(|"|nameof\()' --include='*.cs' .`
      (a CS9216 warning in the build log is the Lock-converted-to-object case)
