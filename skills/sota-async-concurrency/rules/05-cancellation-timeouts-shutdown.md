# 05 — Cancellation, Timeouts & Shutdown Sequencing

## Every await needs a timeout policy

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

## Cancellation propagation — the mechanisms

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

## Cleanup on cancel

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

## Shutdown sequencing

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

## Retry interplay

Cancellation and timeout must beat retry logic: a retry loop that ignores
ctx turns one cancelled request into N background attempts.

```go
// GOOD — every retry checks the context; backoff sleep is cancellable.
for attempt := 0; attempt < max; attempt++ {
    if err := op(ctx); err == nil || !retryable(err) || ctx.Err() != nil {
        return err
    }
    select {
    case <-time.After(backoff(attempt)):   // jittered
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
      a network peer is HIGH.
- [ ] Timeouts: total-operation or just connect? Stacked timeouts that exceed
      the caller's deadline?
- [ ] Timeout firing actually cancels the work (AbortSignal wired, asyncio
      timeout context, ctx honored by callee) — or does the loser keep running?
- [ ] Grep Go for `context.Background()`/`context.TODO()` outside main/tests —
      each one severs the cancellation chain.
- [ ] Grep Python for `except BaseException`, bare `except:`, or
      `except Exception` in retry/cleanup loops around awaits — does
      CancelledError survive and re-raise?
- [ ] Cleanup paths using the already-cancelled context/signal (rollback that
      can never run)?
- [ ] `finally` blocks with unbounded awaits (cancellable cleanup hanging
      shutdown)? `shield` usage bounded?
- [ ] Shutdown: readiness flipped before listener close? Drain deadline <
      orchestrator grace? Producers stopped before consumers? Sentinels/
      closure to wake blocked getters? Background daemons cancelled and
      awaited?
- [ ] Retry loops: ctx/signal checked per attempt? Backoff sleep cancellable?
      Retries within the deadline budget?
- [ ] Subprocesses/remote jobs killed on cancellation?
