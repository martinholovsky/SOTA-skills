# 04 — Async Rust & Tokio

Async Rust's failure modes are quiet: a blocked worker thread, a future dropped
mid-write, a lock held across `.await`. These rules cover tokio idioms,
cancellation safety, structured concurrency, channels, and shutdown.

## 1. Never block the runtime

A tokio worker thread running blocking code stalls **every task scheduled on
it**. Blocking = sync I/O, heavy CPU (>~100µs per poll), `std::thread::sleep`,
sync DB drivers, `reqwest::blocking`, sync `zip`/compression, big serde on huge
payloads, `std::sync::Mutex` under contention.

```rust
// BAD: stalls the worker thread
async fn load(path: PathBuf) -> Result<Config> {
    let raw = std::fs::read_to_string(&path)?;          // sync I/O in async
    let parsed = heavy_parse(&raw);                     // 50ms CPU in async
    Ok(parsed)
}

// GOOD
async fn load(path: PathBuf) -> Result<Config> {
    let raw = tokio::fs::read_to_string(&path).await?;  // async I/O
    let parsed = tokio::task::spawn_blocking(move || heavy_parse(&raw))
        .await?;                                         // CPU off-runtime
    Ok(parsed)
}
```

- `spawn` for async work; `spawn_blocking` for blocking-but-bounded work
  (file ops via std, sync clients, password hashing); a dedicated **rayon pool
  or separate runtime** for sustained CPU-parallel work — `spawn_blocking`'s
  pool (default cap 512 threads) is sized for blocking I/O, not compute.
- `tokio::time::sleep`, never `std::thread::sleep`, in async fns.
- Detection: `tokio-console` (task poll times), `RUSTFLAGS` +
  `tokio_unstable` task dumps; in review, grep for sync APIs inside `async fn`
  (checklist below). A p99 latency cliff under load with idle CPU is the
  classic blocked-worker signature.
- `block_on` inside an async context panics or deadlocks
  (`Handle::block_on` on the current runtime, nested `Runtime::block_on`).
  Bridging sync→async from a blocking thread: `Handle::current().block_on`
  from `spawn_blocking` is legal; document why.

## 2. Decoding Send/Sync bounds errors

"future cannot be sent between threads safely" means a non-`Send` value is
**held across an `.await`** in a future passed to `tokio::spawn`
(multi-threaded runtime requires `Send + 'static`).

Fix in priority order:

1. **Shrink the hold**: drop/scope the non-Send value before the await.

```rust
// BAD: MutexGuard (often non-Send) and Rc held across await
let guard = state.lock().unwrap();
let data = guard.compute();
remote.push(data).await?;        // guard still alive here

// GOOD: scope ends before await
let data = { state.lock().unwrap().compute() };
remote.push(data).await?;
```

2. Replace the type: `Rc`→`Arc`, `RefCell`→`Mutex`/atomics, thread-local /
   `dyn Trait` without `+ Send` → bounded version.
3. For genuinely thread-bound libs (e.g. some FFI/GUI handles), as a last
   resort: `tokio::runtime::LocalRuntime` (stabilized in tokio 1.51, 2026 —
   a whole runtime whose tasks may be `!Send`) or the older
   `tokio::task::LocalSet` + `spawn_local`.

- The compiler note "this value is used across an await" points at the exact
  hold — read it before refactoring.
- `'static` errors on `spawn`: the future can't borrow from the caller. Move
  owned/`Arc` data in (`async move`), or restructure so the parent awaits the
  child directly (no spawn = borrows fine), or use `JoinSet`/scoped patterns.
- Library code: add `Send` bounds tests (`fn assert_send<T: Send>(t: T)`) so
  you don't break downstream spawnability silently.

## 3. Cancellation safety

**Every `.await` is a possible end of your function.** Futures are cancelled by
being dropped — by `select!`, timeouts, dropped `JoinHandle`s being aborted,
or a client disconnect dropping the request future (hyper/axum do this).

- `select!` pitfall: the non-winning branches' futures are **dropped** each
  iteration. Recreating a future in a loop loses partial progress:

```rust
// BAD: on every tick, read_line future is dropped — buffered partial line lost
loop {
    tokio::select! {
        line = read_line(&mut reader) => handle(line?),
        _ = interval.tick() => flush().await,
    }
}

// GOOD: keep the future alive across iterations (pin it once)
let read_fut = read_line(&mut reader);
tokio::pin!(read_fut);
loop {
    tokio::select! {
        line = &mut read_fut => { handle(line?); read_fut.set(read_line(&mut reader)); }
        _ = interval.tick() => flush().await,
    }
}
```

- Know your cancel-safe primitives (safe to drop and retry: `recv()` on tokio
  mpsc/broadcast/watch, `Notified`, `accept()`, `read()`/`read_buf`) vs
  cancel-unsafe (`write_all` — partial write, `Mutex::lock` is safe but work
  after acquiring may not be, anything that buffers internally, multi-await
  sequences with intermediate state). Tokio docs label each — check before
  putting it in `select!`.
- State mutations spanning an await are torn by cancellation. Either make the
  critical section await-free, or use a **drop guard** to restore/complete
  invariants:

```rust
struct InFlightGuard<'a>(&'a Counter);
impl Drop for InFlightGuard<'_> { fn drop(&mut self) { self.0.dec(); } }
// guard decrements even if the request future is dropped mid-await
```

- Cooperative cancellation: `CancellationToken` (tokio-util) +
  `token.cancelled()` in `select!`, or `JoinHandle::abort()` (abort only stops
  at await points; CPU loops need explicit checks).
- Spawned tasks are **not** cancelled when their `JoinHandle` drops — they
  leak unless tracked (see §4) or aborted. Dropping a `JoinSet` *does* abort
  its tasks.

**Cancelling a `timeout` around a child process does not kill the process.** The
future is dropped, the OS process is not — rules/05 §9 (R9.5) has the measured
behaviour and `.kill_on_drop(true)`. A spawned process is owned state exactly like a
spawned task, and cancellation is where that ownership is usually dropped.

## 4. Structured concurrency

Unsupervised `tokio::spawn` is a goto: errors vanish, panics vanish, shutdown
can't find it.

- **`JoinSet`** for dynamic groups of homogeneous tasks: collects results,
  propagates panics as `JoinError`, aborts all on drop.

```rust
let mut set = tokio::task::JoinSet::new();
for url in urls { set.spawn(fetch(url)); }
while let Some(res) = set.join_next().await {
    let body = res??;             // JoinError (panic/abort) then app error
    process(body);
}
```

- **`TaskTracker` + `CancellationToken`** (tokio-util) for service-lifetime
  tasks: `tracker.spawn(...)`, then `tracker.close(); tracker.wait().await`
  on shutdown.
- Concurrency without spawning (no `'static` needed, same task):
  `join!`/`try_join!` for fixed sets;
  `futures::stream::iter(items).map(work).buffer_unordered(N)` for bounded
  fan-out — **always bound N**; unbounded fan-out over request-derived
  collections is a self-DoS.
- Every `tokio::spawn` must have an owner that observes its `JoinHandle` (or a
  comment justifying fire-and-forget + its own error logging). Panics in
  spawned tasks are silent until joined.

## 5. Locks across `.await`

- `std::sync::MutexGuard` is non-Send (compile error on spawn) — but on
  single-future paths it *can* compile and then **deadlock**: task A holds the
  lock, awaits; task B on the same thread polls and blocks on the lock.
- Decision rule: **short, await-free critical sections → `std::sync::Mutex`
  (or `parking_lot`)**, scoped to drop before any await. Need to hold a lock
  across an await (e.g. exclusive access to a connection through a protocol
  exchange) → `tokio::sync::Mutex` — accept that it's slower and serializes
  tasks.
- Often the real fix is neither: move owned state into a dedicated task and
  communicate via channels (actor pattern), or use `RwLock`/`arc-swap` for
  read-mostly config.
- Clippy: `await_holding_lock`, `await_holding_refcell_ref` — deny in CI.

## 6. Channel selection

| Channel | Shape | Use |
|---|---|---|
| `mpsc` | many→one, bounded | work queues, actor inboxes — **default choice** |
| `oneshot` | one value | request/response, completion signal |
| `broadcast` | many→many, each gets all | events, pub/sub; lagging receivers get `RecvError::Lagged` — handle it |
| `watch` | latest-value only | config updates, status, shutdown flag |
| `mpsc::unbounded` | many→one, unbounded | almost never — unbounded = memory DoS under backpressure |

- **Bounded `mpsc` everywhere by default**; choose capacity deliberately —
  `send().await` backpressure is the feature. `try_send` + explicit
  drop/shed policy on latency-critical producers.
- Request/response over an actor: send `(payload, oneshot::Sender<Reply>)`.
- `watch` for shutdown signals predates `CancellationToken`; prefer the token
  in new code.
- Crossing sync→async: tokio `mpsc::Sender::blocking_send` from sync threads;
  never `block_on(tx.send(...))` inside the runtime.

## 7. Async traits & API design

- Native `async fn` in traits (stable 1.75): fine for internal/sealed traits;
  **not dyn-compatible** and leaves `Send` of the returned future
  unnameable for generic callers. Public traits used as `dyn` or spawned
  generically: use `#[async_trait]` (boxes, adds `Send` bound by default) or
  return `impl Future + Send` explicitly / `BoxFuture`. The 2026-era
  alternative: `trait-variant` to generate `Send` variants.
- Don't make functions `async` that never await — sync fn returning a value
  is simpler and callable anywhere (`clippy::unused_async`).
- Don't expose tokio types in library public APIs unless the crate is
  tokio-specific by design; abstract over `AsyncRead`/`AsyncWrite`
  (tokio or futures versions) where feasible.
- Tokio remains 1.x (1.52 as of mid-2026; no 2.0) and designates LTS minors
  with ≥1 year of backported fixes (1.47.x until Sep 2026, 1.51.x until Mar
  2027). Stability-critical services can pin an LTS line with tilde syntax:
  `tokio = { version = "~1.51", features = [...] }`.

## 8. Graceful shutdown

The canonical service shape:

```rust
let token = CancellationToken::new();
let tracker = TaskTracker::new();

// signal handling
let t = token.clone();
tokio::spawn(async move {
    tokio::signal::ctrl_c().await.expect("ctrl_c handler installed");
    t.cancel();
});

// accept loop
loop {
    tokio::select! {
        _ = token.cancelled() => break,
        conn = listener.accept() => {
            let (stream, _) = conn?;
            tracker.spawn(handle(stream, token.clone()));
        }
    }
}

// drain: stop accepting, let in-flight finish (with deadline), then exit
tracker.close();
tokio::select! {
    _ = tracker.wait() => {}
    _ = tokio::time::sleep(DRAIN_TIMEOUT) => warn!("shutdown deadline hit"),
}
```

- Order: stop intake → signal cancellation → drain with deadline → flush
  (logs, metrics, WAL) → exit. Dropping the `Runtime` mid-flight cancels
  everything abruptly — drain first.
- Handlers must observe the token at long awaits (`select!` with
  `token.cancelled()`) or be cancel-safe end-to-end.
- Test shutdown: a service that can't exit cleanly under load hides task leaks.

## Audit checklist

- [ ] Blocking in async: `rg -t rust 'async fn' -A30 | rg 'std::fs::|std::thread::sleep|reqwest::blocking|\.lock\(\)\s*$'`
      — more reliably, grep each: `rg 'thread::sleep|std::fs::(read|write|File)|blocking::' -t rust`
      and check enclosing fn for `async`. High severity in request paths.
- [ ] `rg 'block_on' -t rust` — any call reachable from async context =
      Critical (deadlock/panic).
- [ ] `rg 'unbounded_channel|UnboundedSender' -t rust` — each needs a written
      backpressure argument; attacker-fed unbounded channel = High (DoS).
- [ ] `rg 'tokio::spawn' -t rust` — orphaned handles (result never joined, no
      JoinSet/TaskTracker, no error logging in task) = Medium; panic
      observability gap.
- [ ] `select!` loops: any branch future recreated per-iteration that buffers
      internally (reads, `write_all`, custom combinators) → cancellation data
      loss = High. Check each `select!` arm against cancel-safety docs.
- [ ] Locks: clippy `await_holding_lock`, `await_holding_refcell_ref`;
      `rg 'tokio::sync::Mutex' -t rust` — verify each actually needs
      hold-across-await, else downgrade to std/parking_lot.
- [ ] `rg '\.abort\(\)' -t rust` — aborted tasks: is every shared invariant
      abort-safe (drop guards present)?
- [ ] Fan-out: `rg 'buffer_unordered|buffered\(' -t rust` — bound derived from
      config, not unbounded or request-controlled; loops spawning per item of
      untrusted-size collections.
- [ ] Shutdown path exists: signal handler, drain deadline, `tracker.close()`
      before `wait()` (close-after-wait hangs forever).
- [ ] `rg 'async fn' -t rust` + `clippy::unused_async`; public async traits:
      dyn-compat and Send bounds checked for downstream spawnability.
- [ ] CI lints: `clippy::await_holding_lock`, `clippy::unused_async`,
      `clippy::large_futures` (oversized futures → stack/box them).
