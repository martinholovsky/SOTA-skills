# 04 — Async: Structured Concurrency Done Right

asyncio's failure modes are silent: lost exceptions, garbage-collected tasks, a blocked loop
that "works" until production load. The cure is structured concurrency plus a hard ban on
synchronous work inside coroutines.

## 1. TaskGroup is the default; gather is legacy

```python
# Good — structured: scope owns the tasks; one failure cancels siblings;
# all exceptions surface as ExceptionGroup; nothing leaks past the `async with`
async def fetch_all(urls: list[str]) -> list[Response]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(u)) for u in urls]
    return [t.result() for t in tasks]

# Legacy — gather without return_exceptions: first error propagates but siblings
# keep running detached; with return_exceptions=True: errors silently mixed into results
results = await asyncio.gather(*coros)
```

- New code uses `asyncio.TaskGroup` (3.11+). `gather` survives only for "collect results
  including failures" reporting — and then every element MUST be isinstance-checked.
- Handle TaskGroup failures with `except*` (exception groups, see rules/03 §10).
- A coroutine should not outlive the scope that created it. If you can't say which `async with`
  owns a task, the design is wrong.

## 2. Fire-and-forget: the GC eats your tasks

The event loop holds only **weak** references to tasks:

```python
# Bad — task may be garbage-collected mid-flight; exceptions vanish
asyncio.create_task(send_email(user))

# Acceptable when truly detached work is required — keep a strong ref + done callback
_background: set[asyncio.Task[None]] = set()

def _reap(t: asyncio.Task[None]) -> None:
    _background.discard(t)
    if t.cancelled():
        return
    if (exc := t.exception()) is not None:        # NEVER just discard: an unobserved
        log.exception("detached task failed", exc_info=exc)   # exception is a silent failure

def spawn(coro: Coroutine[None, None, None]) -> None:
    t = asyncio.create_task(coro)
    _background.add(t)
    t.add_done_callback(_reap)   # strong ref fixes LIFETIME; this fixes ERROR VISIBILITY
```

Better: don't fire-and-forget. Put background work in a long-lived TaskGroup owned by the app
lifespan (FastAPI lifespan, service main), or a queue + worker. Every unawaited
`create_task(...)` whose return value is discarded is an audit finding.

## 3. Never block the loop

One blocked coroutine freezes **every** request on that loop. Banned inside `async def`:

| Blocking call | Replacement |
|---|---|
| `time.sleep(n)` | `await asyncio.sleep(n)` |
| `requests.get(...)` / `urllib` | `httpx.AsyncClient` / `aiohttp` |
| `subprocess.run` | `await asyncio.create_subprocess_exec(...)` |
| blocking DB driver / ORM call | async driver (asyncpg, SQLAlchemy async) or `to_thread` |
| file I/O on slow media, `Path.read_text` of big files | `await asyncio.to_thread(p.read_text)` |
| CPU-bound work (parsing, crypto, image ops) | `to_thread` (releases GIL?) else ProcessPoolExecutor |

```python
# Sync library you can't replace — push to a thread
data = await asyncio.to_thread(legacy_client.fetch, key)

# CPU-bound — process pool (threads don't help under the GIL)
loop = asyncio.get_running_loop()
result = await loop.run_in_executor(process_pool, crunch, payload)
```

Detection: ruff `ASYNC` rules catch the obvious ones; `loop.slow_callback_duration` + dev mode
(`PYTHONASYNCIODEBUG=1` or `-X dev`) logs callbacks that hog the loop at runtime.

## 4. Timeouts on every external await

Unbounded awaits are how services hang. Use `asyncio.timeout` (3.11+) — composable, cancels
the whole block:

```python
async with asyncio.timeout(5.0):
    conn = await pool.acquire()
    rows = await conn.fetch(query)
```

- Prefer one `asyncio.timeout` around a logical operation over per-call `wait_for` wrappers.
- Library calls with native timeout params (httpx, asyncpg) should set them too — defense in
  depth, and httpx's default timeout exists but DB drivers' often don't.
- **Never swallow `CancelledError`.** Catch it only to clean up, then re-raise:
  ```python
  except asyncio.CancelledError:
      await release_partial()
      raise
  ```
  Swallowing it breaks timeouts, TaskGroup cancellation, and graceful shutdown. `except
  Exception` does NOT catch it (it's `BaseException`) — which is correct; don't "fix" that.
- 3.12 `wait_for` semantics changed; treat `asyncio.timeout` as the only spelling worth
  remembering.

## 5. Async generators & cleanup

Async generators finalize **non-deterministically** unless closed:

```python
# Risky — break exits the loop; generator's finally runs whenever GC gets to it,
# possibly on a dead loop
async for row in stream_rows():
    if found(row):
        break

# Good — deterministic cleanup
from contextlib import aclosing
async with aclosing(stream_rows()) as rows:
    async for row in rows:
        if found(row):
            break
```

- Wrap any async generator that holds resources (cursors, connections, files) in `aclosing`
  when the consumer might exit early.
- Inside the generator, `finally:` must be cancellation-safe — it may run during cancellation
  where further awaits can themselves be cancelled; use `asyncio.shield` only with care.
- Prefer returning an async context manager over a resource-holding async generator in
  public APIs.

## 6. Sharing clients, connections, loops

- One `httpx.AsyncClient` / connection pool per application, created at startup (lifespan),
  closed at shutdown — never per request (`async with AsyncClient()` inside a handler
  costs you connection reuse, TLS session caching, and adds latency).
- Never create objects bound to a loop (`Queue`, `Lock`, clients) at **import time** — they
  bind to whichever loop exists then, or none; instantiate inside async context / lifespan.
- `asyncio.run(main())` exactly once at the program edge. Nested `asyncio.run` or
  `get_event_loop().run_until_complete` inside libraries is a design error.
- asyncio primitives (`asyncio.Lock`, `Queue`) are not thread-safe; crossing threads uses
  `loop.call_soon_threadsafe` / `asyncio.run_coroutine_threadsafe`.

## 7. Common bugs checklist

- **Forgotten `await`:** `client.get(url)` returns an un-awaited coroutine that never runs;
  the only symptom may be a `RuntimeWarning: coroutine ... was never awaited` on stderr.
  Strict type checking flags this (`Coroutine` where `Response` expected) — another reason
  rules/01 mandates a checker. Enable `-W error::RuntimeWarning` in tests.
- **`async def` that never awaits** — either it shouldn't be async (caller pays scheduling
  cost, pretends concurrency) or it's missing the await.
- **Blocking ORM in async views — and the two frameworks fail *differently*:**
  **Django raises**, it does not silently serialize. A sync ORM call from a thread with a
  running event loop gets `SynchronousOnlyOperation`; it only blocks instead if someone set
  `DJANGO_ALLOW_ASYNC_UNSAFE`, which the docs warn risks data loss
  ([Django async safety](https://docs.djangoproject.com/en/5.2/topics/async/), verified
  2026-09-16). So "works in dev, dies in prod" is the wrong symptom to hunt for in Django —
  hunt for the exception, or for the env var that disabled the guard. A sync SQLAlchemy
  `Session` on a FastAPI async path **does** block silently, because nothing is watching.
  Django: `await Model.objects.aget(...)` / `sync_to_async`; FastAPI: see rules/07.
- **Lock-free check-then-act across awaits:** state can change at every `await`. Guard
  multi-step invariants with `asyncio.Lock`, or design single-writer.
- **`time.monotonic` vs loop time** for timing inside coroutines; never `time.time()` deltas.

## 8. anyio — when to consider

anyio runs on asyncio (and trio) with stricter structured-concurrency semantics and level
cancellation. Use it when: writing a **library** that shouldn't dictate the backend, you want
trio-style cancel scopes, or you're already in Starlette/FastAPI internals (they're anyio-
based — `anyio.to_thread.run_sync` is what `def` endpoints use). For applications committed
to asyncio, 3.11+ stdlib (TaskGroup + timeout) covers most of anyio's historical advantage;
don't mix both APIs ad hoc in one codebase — pick one idiom.

## 9. Bounded fan-out and producer/consumer

Unbounded concurrency is a self-inflicted DoS — against your own connection pool, the
remote API's rate limit, or memory.

```python
# Bad — 50_000 simultaneous requests; pool exhaustion, remote 429s, memory spike
async with asyncio.TaskGroup() as tg:
    for url in urls:                      # len(urls) == 50_000
        tg.create_task(fetch(url))

# Good — Semaphore caps in-flight work; TaskGroup still owns lifetimes
sem = asyncio.Semaphore(20)

async def fetch_bounded(url: str) -> Response:
    async with sem:
        return await fetch(url)

async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(fetch_bounded(u)) for u in urls]
```

For pipelines, prefer an explicit bounded queue — backpressure for free:

```python
async def pipeline(items: AsyncIterator[Item]) -> None:
    q: asyncio.Queue[Item | None] = asyncio.Queue(maxsize=100)   # maxsize = backpressure

    async def producer() -> None:
        async for item in items:
            await q.put(item)            # blocks when consumers lag — by design
        for _ in range(N_WORKERS):
            await q.put(None)            # sentinel per worker

    async def worker() -> None:
        while (item := await q.get()) is not None:
            await process(item)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(producer())
        for _ in range(N_WORKERS):
            tg.create_task(worker())
```

- `Queue(maxsize=0)` (unbounded) in a pipeline is a memory leak waiting for a slow consumer.
- Rate limiting (req/s) is not the same as concurrency limiting (in-flight); for hard API
  quotas use a token-bucket (`aiolimiter`) in addition to the semaphore.

## 10. Testing async code

- `pytest-asyncio` (or anyio's pytest plugin) with `asyncio_mode = "auto"` in pyproject;
  async tests just work, no decorator noise.
- Fake time with explicit clock injection or `looptime`-style plugins; never `await
  asyncio.sleep(real_seconds)` in tests.
- Test cancellation paths: `task.cancel()` then assert cleanup ran — uncancelled-safe cleanup
  is the most common untested async path.

## Audit checklist

```bash
# Ruff async rules first — blocking calls, sync sleep, etc.
uvx ruff check --select ASYNC --statistics .

# Blocking calls inside async defs [HIGH in servers]
grep -rn "time\.sleep" --include="*.py" src/                 # cross-check: inside async def?
grep -rn "requests\.\(get\|post\|put\|delete\|Session\)" --include="*.py" src/
grep -rn "subprocess\.\(run\|check_output\|call\)" --include="*.py" src/   # in async modules?

# Fire-and-forget tasks [MEDIUM-HIGH]
grep -rn "asyncio.create_task" --include="*.py" src/         # is the return value kept + callback added?
grep -rn "ensure_future" --include="*.py" src/               # legacy spelling, same issue

# gather usage [review each]
grep -rn "asyncio.gather" --include="*.py" src/
grep -rn "return_exceptions=True" --include="*.py" src/      # are results isinstance-checked after?

# Swallowed cancellation [HIGH]
grep -rn -A3 "except asyncio.CancelledError" --include="*.py" src/ | grep -L raise
grep -rn "except BaseException" --include="*.py" src/

# Timeouts
grep -rn "asyncio.timeout\|wait_for" --include="*.py" src/ | wc -l    # zero in a network service = finding
grep -rn "AsyncClient()" --include="*.py" src/               # per-request client construction? [MEDIUM]

# Loop-bound objects at import time [MEDIUM]
grep -rn "^[a-zA-Z_]* = asyncio.\(Queue\|Lock\|Event\)" --include="*.py" src/
grep -rn "get_event_loop" --include="*.py" src/              # legacy API [LOW-MEDIUM]

# Async generators holding resources without aclosing
grep -rln "async def.*->.*AsyncIterator\|AsyncGenerator" --include="*.py" src/
grep -rn "aclosing" --include="*.py" src/                    # compare counts

# Forgotten awaits — runtime + type checker
grep -rn "asyncio_mode" pyproject.toml setup.cfg 2>/dev/null
python -W error::RuntimeWarning -m pytest -x 2>&1 | grep "never awaited"
```
