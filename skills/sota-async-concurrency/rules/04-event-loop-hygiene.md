# 04 — Event-Loop Hygiene: Never Block the Loop

## The contract

An event loop multiplexes thousands of tasks onto one thread. Any task that
holds the thread for more than ~10–50ms steals latency from **every** other
task: timers fire late, heartbeats miss, health checks fail, sockets back up.
One blocking call in one handler degrades the whole process. There is no
"just this once".

Latency math: a 200ms sync call on a loop serving 500 req/s queues ~100
requests behind it. Blocking is a tail-latency multiplier, not a local cost.

## The blocklist — what must never run on the loop thread

1. **Sync I/O:** file reads/writes (`open`/`read`, `fs.readFileSync`),
   sync HTTP clients (`requests`, `urllib`, `http.client`), sync DB drivers
   (psycopg2 without async wrapper, `sqlite3`, blocking JDBC), `subprocess.run`,
   `socket` without non-blocking mode. Note: on Linux, regular-file I/O is
   *always* potentially blocking — there is no readiness API for files; even
   "fast" reads stall on cold page cache or NFS.
2. **Sync sleeps:** `time.sleep` (use `asyncio.sleep`), `std::thread::sleep`
   in async fns (use `tokio::time::sleep`), busy-wait loops.
3. **CPU-bound work:** parsing/serializing multi-MB JSON, compression,
   image/video processing, template rendering of huge documents, regex
   catastrophic backtracking, crypto: `bcrypt.hashSync`, `pbkdf2Sync`,
   `scrypt` sync variants, RSA keygen. Password hashing is *designed* to take
   ~100ms — it is the canonical loop-killer.
4. **Blocking lock acquisition** on a contended threading mutex
   (`threading.Lock.acquire` in a coroutine, `Mutex::lock` of `std::sync` in
   async Rust when contended), and `queue.Queue.get()`/`.join()` from a
   coroutine.
5. **Sync DNS:** Node's `dns.lookup` uses a tiny libuv threadpool (default 4)
   — slow DNS exhausts it and stalls *fs and crypto too*; size
   `UV_THREADPOOL_SIZE` or use `dns.resolve`.

```python
# BAD — three loop-blockers in one handler.
async def register(req):
    data = requests.post(KYC_URL, json=req.json).json()   # sync HTTP
    pw = bcrypt.hashpw(req.password, bcrypt.gensalt())     # CPU ~100ms
    time.sleep(0.1)                                        # sync sleep
    ...

# GOOD
async def register(req):
    async with httpx.AsyncClient() as c:
        data = (await c.post(KYC_URL, json=req.json)).json()
    pw = await asyncio.to_thread(bcrypt.hashpw, req.password, bcrypt.gensalt())
    await asyncio.sleep(0.1)
```

## Offloading correctly

| Runtime | I/O-blocking call | CPU-bound work |
|---|---|---|
| Python asyncio | `asyncio.to_thread` / `loop.run_in_executor(None, f)` | `run_in_executor(ProcessPoolExecutor)` (GIL); thread pool OK on free-threaded 3.13+ |
| Node | rewrite to async API (almost always exists) | `worker_threads` / `piscina` pool |
| Rust tokio | `tokio::task::spawn_blocking` | `spawn_blocking` for occasional; `rayon` pool + channel back for heavy |
| Go | nothing — runtime parks blocked goroutines | nothing special; cap with semaphore if it floods cores |
| JVM virtual threads | fine, *unless* pinned: native calls pin the carrier; `synchronized` pins only on JDK ≤23 (JEP 491 fixed it in 24+) — on JDK 21 LTS use `ReentrantLock` | platform-thread pool sized to cores |

Offloading rules:
- **Bound the offload pool and its queue.** `spawn_blocking` has a large
  default cap (512) — that's 512 concurrent blocking calls before
  backpressure; put a semaphore in front for expensive operations.
  Python's default executor: similar story (`min(32, cpu+4)` threads, unbounded queue).
- **Data crossing to a process pool is serialized** — don't ship 1GB to save
  50ms of compute. Sometimes the sync path is the right call: measure.
- **Don't offload trivially small work**; thread-hop overhead (~µs–ms) can
  exceed the work. The threshold that matters is the p99 of the call, not the
  mean — offload anything that *can* take >10ms.
- **Values returned from workers are snapshots.** Don't mutate shared loop
  state from worker threads; return data and apply it on the loop
  (`call_soon_threadsafe` / channel back / `postMessage`).

## Long-task chunking

When CPU work must run on the loop (small, frequent, not worth a pool),
chunk it so other tasks interleave:

```js
// BAD — 5M-row aggregation freezes the loop for seconds.
for (const row of rows) total += score(row);

// GOOD — yield to the macrotask queue every N items.
let i = 0;
for (const row of rows) {
  total += score(row);
  if (++i % 10_000 === 0) await new Promise(r => setImmediate(r));
}
```

```python
# Python equivalent: await asyncio.sleep(0) every N iterations.
```

Caveats: `await asyncio.sleep(0)` / `setImmediate` yields a *turn*, it doesn't
bound the chunk's own cost — size N so each chunk stays under ~10ms. Chunking
mutable shared state reintroduces interleaving races (rule 02): your data
structure is now visible mid-aggregation.

## Microtask vs macrotask (JS — and the asyncio analogue)

- **Microtasks** (promise callbacks, `queueMicrotask`, `await` resumption)
  run to exhaustion after the current task, *before* rendering, I/O events,
  or timers. A microtask that schedules microtasks in a loop **starves the
  event loop completely** — worse than a sync loop, and `await` won't save
  you because resolved-promise `await` only hops the microtask queue:

```js
// BAD — this never yields to I/O; `await` of an already-resolved promise
// stays inside the microtask queue.
while (!done) { await Promise.resolve(); doSmallStep(); }

// GOOD — setImmediate/setTimeout(0) reaches the macrotask queue,
// letting I/O and timers run.
while (!done) { await new Promise(r => setImmediate(r)); doSmallStep(); }
```

- **Macrotasks** (`setTimeout`, `setImmediate`, I/O callbacks) interleave with
  the loop phases. Use them to yield; use microtasks only for ordering within
  a tick.
- `process.nextTick` runs even before microtasks — recursive `nextTick`
  starves everything; treat it as internals-only.
- **asyncio analogue:** `call_soon` callbacks run in FIFO per iteration —
  closer to macrotask behavior, so `await asyncio.sleep(0)` does yield to I/O.
  But a coroutine that awaits only immediately-ready awaitables can still hog;
  the loop runs ready callbacks in batches.

## Sync-over-async: the self-deadlock

Blocking the loop on a result *the loop itself must produce* doesn't just
degrade — it deadlocks instantly. The loop thread waits on a future; the
future needs the loop thread to advance; nothing ever runs again.

```python
# BAD — called from a coroutine (so the loop thread):
fut = asyncio.run_coroutine_threadsafe(work(), loop)
data = fut.result()          # loop thread blocks waiting on itself → hang

# BAD — RuntimeError at best, deadlock pattern at heart:
loop.run_until_complete(work())   # inside a running loop
```

```rust
// BAD — panics on tokio ("Cannot block_on inside a runtime") or
// deadlocks a current-thread runtime.
let data = futures::executor::block_on(fetch(url));
```

The C# classic is `.Result`/`.Wait()` on a task needing the captured context;
the JS analogue is `Atomics.wait` on the main thread. Variants to flag:

- Sync facade over async internals: `def get(self): return
  asyncio.get_event_loop().run_until_complete(self._aget())` — works in
  scripts, deadlocks when called from inside a server's loop.
- Worker thread calling back into the loop **synchronously** and the loop
  meanwhile blocking on the worker pool (pool ↔ loop cycle). Offloaded
  functions must be pure sync: no `fut.result()` back into the loop with the
  loop's own thread saturated waiting for the pool.
- Library code that "detects" a running loop and silently spins a nested one
  (`nest_asyncio`) — a workaround that hides the architecture bug; flag it.

**Rule:** the boundary between sync and async worlds belongs at the top of
the program (one `asyncio.run` / `#[tokio::main]` / single runtime), not
sprinkled through the call graph. Crossings mid-stack are findings.

## Detecting a blocked loop (build it in; check for it in audits)

- **Python:** run with `loop.set_debug(True)` + `loop.slow_callback_duration =
  0.05` in staging — logs any callback >50ms with its name. `aiodebug` /
  `aiomonitor` for production. On 3.14+, `python -m asyncio ps|pstree PID`
  inspects a live process's task tree (`pstree` also reports await-graph
  cycles, i.e. async deadlocks); `asyncio.print_call_graph()` in-process.
- **Node:** monitor event-loop lag/utilization (`perf_hooks.monitorEventLoopDelay`,
  `performance.eventLoopUtilization()`); alert at p99 lag >100ms.
  `blocked-at` pinpoints offenders in dev.
- **Rust:** `tokio-console` shows tasks with long poll times; a single poll
  >100ms is a blocking bug.
- An audit of an async service that has **no loop-lag metric** should flag
  that as a MEDIUM observability finding by itself.

## Sneaky blockers (audit-grade list)

- Logging handlers doing sync file/network writes on the loop (Python
  `logging` to a slow disk; use `QueueHandler`).
- `os.getaddrinfo` via sync resolution inside "async" libs; certificate
  loading; `random.SystemRandom`/`/dev/random` stalls.
- Lazy module imports inside handlers (Python import lock + disk I/O on
  first request).
- ORMs: "async" facades over sync drivers offload to a hidden, small,
  unbounded-queue threadpool — know your driver (asyncpg ✓; psycopg2 ✗).
- `JSON.parse`/`json.loads` of multi-MB payloads; `JSON.stringify` of huge
  responses — these are CPU items 3, not I/O.
- Accidental sync fallback: `await maybe_async()` where a code path returns a
  plain value computed synchronously for 300ms.
- Prometheus/metrics endpoints rendering huge text on the loop.

## Audit checklist

- [ ] Grep async modules for: `time.sleep`, `requests.`, `urllib`,
      `subprocess.run`, `open(`, `.read()`/`.write()` on files, `sqlite3`,
      `psycopg2`, `boto3` (sync), `Sync(` suffixed Node APIs, `hashSync`,
      `pbkdf2Sync`, `execSync`, `std::thread::sleep`, `std::sync::Mutex` in
      hot async paths, `reqwest::blocking`.
- [ ] Sync-over-async crossings mid-stack: `run_until_complete`/`block_on`/
      `.result()`/`.Result` reachable from loop threads (deadlock-capable:
      CRITICAL); `nest_asyncio` anywhere.
- [ ] Password hashing / crypto in request handlers: offloaded? (HIGH if not.)
- [ ] Large JSON/template/compression work on the loop thread?
- [ ] Offload pools: bounded? Sized deliberately? Semaphore in front of
      `spawn_blocking`/executor for expensive ops?
- [ ] Worker results applied to shared state via loop-safe mechanism
      (`call_soon_threadsafe`, channels, `postMessage`) — not direct mutation
      from the worker thread?
- [ ] Long loops over unbounded input without a yield point (and is the
      chunked state safe to observe mid-flight)?
- [ ] JS: recursive microtask/`nextTick` patterns; `await Promise.resolve()`
      used as a "yield" (it isn't).
- [ ] Node `dns.lookup` on hot paths / `UV_THREADPOOL_SIZE` left at 4 with
      heavy fs+crypto+dns use?
- [ ] Loop-lag metric exported and alerted on? Debug slow-callback logging
      available in staging?
