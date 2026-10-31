# 05 — Cancellation, Timeouts & Shutdown Sequencing

## 1. Every await needs a timeout policy

An await with no deadline is a promise to wait forever. Networks drop ACKs,
peers hang half-open, pools exhaust, locks queue — and your task waits
eternally, holding its own resources (this is how one hung dependency
cascades into total exhaustion).

**Policy, not reflex:** each await either (a) has an explicit timeout, or
(b) demonstrably inherits a deadline from an enclosing scope (request
deadline, task-group timeout, ctx with deadline), or (c) has a comment
defending "forever" (e.g., the main accept loop). In audits, (a|b|c) must
hold for every external call: HTTP, DB, queue ops, lock/semaphore acquires,
`channel.recv`, `process.wait`.

```python
# BAD — fetch can hang forever; so does everyone awaiting this handler.
data = await client.get(url)

# GOOD — scoped deadline covering the whole operation tree (Python 3.11+).
async with asyncio.timeout(2.0):
    data = await client.get(url)
```

```go
// GOOD — deadline rides the context through every layer.
ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
defer cancel()
data, err := client.Get(ctx, url)
```

Deadline design rules:
- **Deadlines propagate; timeouts don't compose.** Prefer one deadline at the
  boundary (request entry) that flows down, over N stacked per-call timeouts
  that can sum to more than the caller will wait. Inner calls take
  `min(own_limit, remaining_budget)`.
- **Connect timeout ≠ read timeout ≠ total timeout.** A "30s timeout" that is
  only a connect timeout still hangs forever on a stalled body. Set total
  operation deadlines.
- Timeout firing means **outcome unknown**, not failure — pair with
  idempotency before retrying (rule 02).
- A timeout that fires must also **cancel the underlying work** —
  `Promise.race` against a timer abandons the loser, it doesn't stop it
  (rule 03). Use `AbortSignal.timeout(ms)` and pass the signal into fetch;
  use `asyncio.timeout` (which cancels the task); use ctx (the callee must
  honor it — verify it does).

## 2. Cancellation propagation — the mechanisms

| Runtime | Mechanism | Semantics |
|---|---|---|
| Python asyncio | `task.cancel()` → `CancelledError` raised at the next await point | Preemptive-at-awaits; catchable; MUST re-raise |
| Go | `context.Context` cancelled → `ctx.Done()` closes | Fully cooperative; only code that checks ctx stops |
| JS | `AbortSignal` → abort event / `signal.aborted` | Cooperative; only APIs accepting the signal stop |
| Rust async | dropping a future cancels it; nothing polls = nothing runs | Implicit at every await; sync code inside is unstoppable |
| .NET/Java | `CancellationToken` / `Thread.interrupt` | Cooperative; interrupt sets flag + wakes blocking ops |

Consequences:
- **Go/JS:** a call chain is only cancellable if **every** layer threads the
  ctx/signal through. A single `context.Background()` or signal-less fetch in
  the middle breaks the chain — grep for these in audits.
- **Python:** every `await` is a potential `CancelledError` raise site. Code
  must be exception-safe at each await (use `try/finally`, async context
  managers).
- **Rust:** every `.await` is a potential drop site. State held across awaits
  must be drop-safe; side effects "after the await" may never run. This is
  cancellation-safety (rule 03's `select!` discussion).

```python
# BAD — swallows cancellation; the task becomes unkillable and
# shutdown hangs on it.
while True:
    try:
        await poll()
    except BaseException:       # or bare `except:` — CancelledError is a
        continue                # BaseException since 3.8, so `except
                                # Exception` does NOT catch it; these do
# Also BAD:
    except BaseException:
        log(...)                # caught CancelledError, didn't re-raise

# GOOD — clean up, then re-raise; cancellation is not an error.
try:
    await poll()
except asyncio.CancelledError:
    await release_lease()       # bounded cleanup only
    raise
```

## 3. Cleanup on cancel

Cancellation arrives at the worst time by definition. Guarantees you must
preserve:

- **Resource release:** `finally` / `defer` / RAII / async context managers
  around every acquire. In Python, the `finally` block of a cancelled
  coroutine runs — but if it awaits, it can be cancelled *again*; keep
  cleanup short or shield it.
- **Shielding:** for must-complete sections (commit after the money moved),
  `asyncio.shield(commit())` — and still await it with an outer bound;
  shield-everything is just uncancellable code. Go: pass a *detached* context
  with its own short timeout (`context.WithoutCancel(ctx)` + WithTimeout) for
  cleanup RPCs — cleanup using the already-cancelled ctx instantly fails,
  a classic bug:

```go
// BAD — ctx is already cancelled; the rollback never happens.
defer store.Rollback(ctx, tx)

// GOOD — cleanup gets its own small budget, detached from the dead ctx.
defer func() {
    cctx, cancel := context.WithTimeout(context.WithoutCancel(ctx), 2*time.Second)
    defer cancel()
    store.Rollback(cctx, tx)
}()
```

- **Invariant restoration:** if a task mutates shared state in steps,
  cancellation between steps leaves it broken. Make mutations transactional,
  or apply them at a single commit point after all awaits.
- **Don't start what you can't stop:** spawning subprocesses / remote jobs
  requires a kill path wired to cancellation (`process.kill` on abort,
  `ctx`-aware job API).

## 4. Shutdown sequencing

Graceful shutdown is a protocol, not a `kill`. Canonical order:

```
1. Trap signal (SIGTERM)            — flip "shutting down" flag
2. Stop accepting new work          — close listener / unsubscribe / fail
                                      readiness probe FIRST, then wait one
                                      probe interval so LBs stop routing
3. Drain in-flight work             — with a deadline (e.g., 0.8 × the
                                      orchestrator's grace period)
4. Cancel stragglers                — propagate cancellation, await briefly
5. Flush & release                  — buffers, queues, DB pools, files
6. Exit                             — nonzero if drain was forced
```

```python
# GOOD — asyncio skeleton.
async def main():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    server = await start_server()
    await stop.wait()

    server.close()                      # 2: stop accepting
    await server.wait_closed()
    try:
        async with asyncio.timeout(25): # 3: drain (k8s grace 30s)
            await inflight.join()
    except TimeoutError:
        pass
    for t in background_tasks:          # 4: cancel daemons/stragglers
        t.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)
    await pool.aclose()                 # 5: flush/release
```

Ordering pitfalls:
- **Closing the queue before draining it** drops accepted work; **draining
  without a deadline** hangs shutdown forever (then SIGKILL corrupts state
  anyway — your deadline must undercut the orchestrator's).
- **Producer/consumer order:** stop producers first, drain consumers, then
  stop consumers. Stopping consumers first deadlocks producers blocked on a
  full bounded queue.
- **Dependency order on release:** cancel tasks *before* closing the pools
  they use, or cancellation cleanup hits closed connections.
- Workers blocked on `queue.get()` need a wakeup: sentinel values (one per
  consumer), closing the channel (Go: `for range` exits), or cancelling the
  getter task.

**The same sequence, per runtime.** Step 1 and steps 2–3 are what differ. Each entry below
was checked against the runtime's own documentation on 2026-10-31 (the Ruby trap behaviour
by running it), and nothing in this table sets a timeout for you: steps 3 and 4 still need
your deadline.

| Runtime | Step 1: trap the signal | Steps 2–3: stop accepting, drain | Detail |
|---|---|---|---|
| Go | `signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)` | `srv.Shutdown(ctx)` with a deadline context | [`sota-golang` rules/04](../../sota-golang/rules/04-http-services.md) §3 |
| Node | `process.on('SIGTERM', …)` | `server.close()`, then `server.closeIdleConnections()` | [`sota-javascript-typescript` rules/04](../../sota-javascript-typescript/rules/04-node-backend.md) §5 |
| Python asyncio | `loop.add_signal_handler(signal.SIGTERM, …)` | the skeleton above | — |
| Rust (tokio) | `tokio::signal::unix::signal(SignalKind::terminate())?`, then `.recv().await`; `tokio::signal::ctrl_c()` is Ctrl-C only, **not** SIGTERM | axum: `axum::serve(listener, app).with_graceful_shutdown(fut)`; your own tasks: `tokio_util`'s `CancellationToken` to tell them, then `TaskTracker::close()` and `wait()`, which returns once the tracker is closed and empty. Wrap the wait in a deadline | [`sota-rust` rules/04](../../sota-rust/rules/04-async-tokio.md) §8 |
| JVM | `Runtime.getRuntime().addShutdownHook(thread)`: hooks start when the shutdown sequence begins, which includes a signal from the operating system; `Runtime.halt` skips them | Spring Boot: graceful shutdown is on by default for embedded Jetty, Reactor Netty and Tomcat (`server.shutdown=immediate` turns it off); bound each phase with `spring.lifecycle.timeout-per-shutdown-phase` | — |
| .NET | the generic host's default `ConsoleLifetime` handles SIGINT, SIGQUIT and SIGTERM (since .NET 6; before it, SIGTERM could not be handled gracefully) | `IHostApplicationLifetime.ApplicationStopping` fires while requests may still be in flight; every `BackgroundService.ExecuteAsync(stoppingToken)` must observe its token; `HostOptions.ShutdownTimeout` bounds `StopAsync` | — |
| PHP (CLI workers) | `pcntl_async_signals(true)` (PHP 7.1+), then `pcntl_signal(SIGTERM, $handler)` | the handler only sets a flag; the worker loop checks it between jobs, finishes the current one and exits | — |
| Ruby | `Signal.trap("TERM") { … }`. **Inside a trap, `Mutex#synchronize` raises `ThreadError: can't be called from trap context`** (measured, Ruby 4.0.6), so a logger or connection pool that locks fails there: push to a `Queue` and act on a normal thread | Sidekiq: TERM shuts down within the `-t` timeout (default 25 s) and pushes unfinished jobs back to Redis; Puma: on TERM a worker "will attempt to finish then exit" | — |
| Swift | swift-service-lifecycle: `ServiceGroup(services:gracefulShutdownSignals: [.sigterm], logger:)`, then `try await serviceGroup.run()` | the group triggers a graceful shutdown on each service | — |
| C/C++ | block the signal with `pthread_sigmask` in the main thread before starting any other (new threads inherit the mask), then read it synchronously with `sigwaitinfo` or, on Linux, `signalfd`. A classic handler may touch only `volatile sig_atomic_t` or lock-free atomics (SEI CERT SIG31-C) and call only async-safe functions (SIG30-C) | run steps 2–6 on an ordinary thread once the signal is read | [rules/02](02-correctness.md) §8 |

**In a container the signal must reach your process at all.** A package-manager launcher as
PID 1 does not forward it: [`sota-devsecops` rules/04](../../sota-devsecops/rules/04-build-containers.md) §4.2.1.

## 5. Retry interplay

Cancellation and timeout must beat retry logic: a retry loop that ignores
ctx turns one cancelled request into N background attempts.

```go
// GOOD — every retry checks the context; backoff sleep is cancellable.
for attempt := 0; attempt < max; attempt++ {
    if err := op(ctx); err == nil || !retryable(err) || ctx.Err() != nil {
        return err
    }
    select {
    case <-time.After(backoff(attempt)):   // jittered; a bounded loop, not a hot one (sota-golang rules/03 §2)
    case <-ctx.Done():
        return ctx.Err()
    }
}
```

Full retry-storm analysis is in rules 06/07; the rule here: **the deadline is
the retry budget** — retries fit inside the caller's remaining time, never
extend it.

## Audit checklist

- [ ] Sweep external awaits (HTTP, DB, queue, lock acquire, recv, wait):
      timeout, inherited deadline, or justifying comment? Unbounded await on
      a network peer is HIGH (§1).
- [ ] Timeouts (§1): total-operation or just connect? Stacked timeouts that exceed
      the caller's deadline?
- [ ] Timeout firing actually cancels the work (§1) (AbortSignal wired, asyncio
      timeout context, ctx honored by callee) — or does the loser keep running?
- [ ] Grep Go for `context.Background()`/`context.TODO()` outside main/tests —
      each one severs the cancellation chain; in JS, a signal-accepting call
      in a cancellable chain made without the caller's `signal` (§2).
- [ ] Grep Python for `except BaseException`, bare `except:`, or
      `except Exception` in retry/cleanup loops around awaits — does
      CancelledError survive and re-raise (§2)?
- [ ] Cleanup paths using the already-cancelled context/signal (rollback that
      can never run)? Shared state mutated in steps across awaits instead of
      at one commit point (cancel leaves it half-applied)? (§3)
- [ ] `finally` blocks with unbounded awaits (§3) (cancellable cleanup hanging
      shutdown)? `shield` usage bounded?
- [ ] Shutdown: readiness flipped before listener close? Drain deadline <
      orchestrator grace? Producers stopped before consumers? Sentinels/
      closure to wake blocked getters? Background daemons cancelled and
      awaited? Queue drained before it is closed? Tasks cancelled before the
      pools they use close? Nonzero exit when the drain was forced? (§4)
      Is SIGTERM trapped with the runtime's own primitive from §4's table (not Ctrl-C
      alone, not a lock taken inside a Ruby trap or a C handler), and does it reach
      the process in its container?
- [ ] Retry loops: ctx/signal checked per attempt? Backoff sleep cancellable?
      Retries within the deadline budget? (§5)
- [ ] Subprocesses/remote jobs killed on cancellation (§3)?
