# Async JavaScript

## Promise combinators: pick deliberately

| Combinator | Resolves when | Rejects when | Use for |
|---|---|---|---|
| `Promise.all` | all fulfill | **first rejection** (others keep running, results dropped) | interdependent work — if one fails, the batch is useless |
| `Promise.allSettled` | always (array of `{status, value/reason}`) | never | independent work — you want every outcome (batch sends, multi-source fetch) |
| `Promise.race` | first settle (fulfil OR reject) | first rejection | timeouts (prefer `AbortSignal.timeout`), first-response-wins |
| `Promise.any` | first fulfillment | all reject (`AggregateError`) | redundant sources/mirrors — first success wins |

```ts
// BAD — one failed notification aborts reporting on all the rest
const results = await Promise.all(users.map(notify));

// GOOD — independent ops: collect all outcomes, then handle failures
const results = await Promise.allSettled(users.map(notify));
const failed = results.filter((r): r is PromiseRejectedResult => r.status === 'rejected');
if (failed.length) logger.warn({ count: failed.length }, 'notifications failed');
```

- `Promise.all` losers are NOT cancelled — pass a shared `AbortSignal` and abort it in a catch if the others' work matters.
- Sequential-vs-parallel: `await` in a loop is sequential (sometimes correct — rate limits, ordering); `Promise.all(arr.map(f))` is parallel. Choose explicitly; accidental sequential awaits are a top latency bug. For bounded parallelism over large sets use a pool (`p-limit`, or `Array.fromAsync` over a semaphore-wrapped generator) — unbounded `Promise.all` over 10k fetches is a self-DoS.

```ts
// BAD — sequential, 10× slower than needed
for (const id of ids) results.push(await fetchUser(id));
// GOOD — parallel with a concurrency cap
const limit = pLimit(8);
const results = await Promise.all(ids.map(id => limit(() => fetchUser(id))));
```

## Floating promises and unhandled rejections

A promise nobody awaits or `.catch`es crashes Node (default since v15) and silently drops errors in browsers.

```ts
// BAD — floating; rejection is an unhandled crash, completion unordered
saveAudit(event);
return response;

// GOOD — await it, or explicitly detach with a handler
await saveAudit(event);
// or, genuinely fire-and-forget:
void saveAudit(event).catch(e => logger.error({ err: e }, 'audit failed'));
```

- Enable `@typescript-eslint/no-floating-promises` and `no-misused-promises` (catches `async` callbacks passed where `void` is expected — `setTimeout`, event handlers, `array.forEach`).
- `async` executor in `new Promise(async ...)` is a smell — throws inside it are lost; you almost never need `new Promise` at all when the API already returns promises. Promisify callbacks with `util.promisify` or `new Promise` at the lowest layer only.
- Don't mix `.then` chains and `await` in one function; pick `await` + try/catch.
- `return await fn()` inside try/catch is required for the catch to see the rejection; bare `return fn()` skips it (`@typescript-eslint/return-await` rule, `in-try-catch` option).

## AbortController everywhere

Every cancellable operation takes an `AbortSignal`. fetch, event listeners, streams, and your own long-running functions.

```ts
// fetch with timeout + caller cancellation
async function getUser(id: UserId, signal?: AbortSignal): Promise<User> {
  const res = await fetch(`/api/users/${id}`, {
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(5000)]) : AbortSignal.timeout(5000),
  });
  if (!res.ok) throw new HttpError(res.status);
  return UserSchema.parse(await res.json());
}

// event listeners: one signal removes them all — the leak-proof pattern
const ac = new AbortController();
window.addEventListener('resize', onResize, { signal: ac.signal });
el.addEventListener('click', onClick, { signal: ac.signal });
// teardown (React useEffect cleanup, component unmount, route change):
ac.abort();

// custom operations: check + propagate
async function processAll(items: Item[], signal: AbortSignal) {
  for (const item of items) {
    signal.throwIfAborted();
    await process(item, signal);   // propagate downward
  }
}
```

- `AbortSignal.timeout(ms)` replaces hand-rolled `Promise.race` timeout patterns; `AbortSignal.any([...])` composes caller-cancel + timeout.
- Abort rejections are `DOMException` named `'AbortError'` (or `'TimeoutError'` from `.timeout`) — treat as flow control, not failure: `if (e instanceof DOMException && e.name === 'AbortError') return;`
- React: abort in-flight fetches in effect cleanup to kill setState-after-unmount and stale-response races. Stale-response guarding via abort beats `let cancelled = true` flags.
- Public async APIs in your codebase should accept `signal` as part of an options object. Functions doing network/FS/timers without a signal path are unkillable — that's a finding for long-running ops.

## Event loop: microtasks vs macrotasks

Ordering model: run-to-completion of current task → drain ALL microtasks (promise reactions, `queueMicrotask`, MutationObserver) → render (browser) → next macrotask (`setTimeout`, I/O, UI events).

- `await` yields to the microtask queue, not the event loop. Since ALL queued microtasks drain before the next macrotask, a tight loop of `await Promise.resolve()` still starves rendering, timers, and I/O. To genuinely yield to the loop use `scheduler.yield()` (browsers), `setTimeout(0)`, or `setImmediate` (Node).
- Node ordering: `process.nextTick` runs before promise microtasks (avoid nextTick in app code — it can starve everything); `setImmediate` runs after I/O, before timers of the next loop iteration.
- Long synchronous work blocks everything (see workers below). Chunk big loops: process N items, then `await scheduler.yield()` / `setImmediate`.
- Zalgo: never make an API sometimes-sync, sometimes-async. If a function may return cached-sync or fetched-async, always go async (`return cached !== undefined ? Promise.resolve(cached)…` — just declare it `async`).

## Top-level await

Allowed in ESM only. Implications:
- It blocks every importer until resolution — a slow TLA in a shared module delays the whole graph. Fine for app entrypoints (config load, DB connect); avoid in library code and widely-imported modules.
- Circular imports + TLA can deadlock or yield partially-initialized modules.
- A rejected TLA fails module evaluation permanently — every subsequent import of that module rethrows. Wrap in try/catch with a fallback if the module must stay importable.
- Prefer lazy init (exported `async function init()` or a memoized `getClient()`) over TLA for connections, so tests and tooling can import the module without side effects.

## Workers for CPU-bound work

The event loop handles I/O concurrency; it cannot parallelize CPU. Anything >~50ms of synchronous compute (parsing huge JSON, image processing, crypto, compression, large sorts) belongs off-thread.

```ts
// Node worker_threads pool — use piscina rather than hand-rolling
import Piscina from 'piscina';
const pool = new Piscina({ filename: new URL('./worker.js', import.meta.url).href });
const hash = await pool.run({ file }, { signal });

// Browser
const worker = new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' });
worker.postMessage(data);             // structured clone; use Transferable for big buffers
worker.postMessage(buf, [buf]);       // transfer ArrayBuffer — zero copy, source neutered
```

- postMessage structured-clones by default — copying a 100MB buffer per call erases the win; transfer `ArrayBuffer`s or use `SharedArrayBuffer` (requires COOP/COEP headers in browsers).
- Workers have startup cost (~ms) — pool them, don't spawn per task.
- Comlink (browser) wraps workers in async proxies and removes postMessage boilerplate.
- Don't use workers for I/O-bound work — that's what async already does, workers just add overhead.

## Async iteration and web streams

`for await...of` consumes async iterables — paginated APIs, streams, message queues — with backpressure for free (you don't pull the next chunk until you're done with this one).

```ts
// Web Streams (standard in Node ≥18, browsers, Deno, Bun, edge runtimes)
const res = await fetch(url, { signal });
for await (const chunk of res.body!.pipeThrough(new TextDecoderStream())) {
  feed(chunk);   // process as it arrives — no full buffering
}

// Transform pipeline
await readable
  .pipeThrough(new TextDecoderStream())
  .pipeThrough(toLines())          // TransformStream
  .pipeTo(destination, { signal });
```

- Prefer Web Streams (`ReadableStream`/`WritableStream`/`TransformStream`) over Node streams in new cross-platform code; bridge legacy with `Readable.toWeb()`/`fromWeb()`.
- Node-side pipelines: `stream/promises` `pipeline(src, transform, dst, { signal })` — handles error propagation and cleanup; never `.pipe()` chains without error handling (each `.pipe` swallows downstream errors).
- Don't buffer whole files/bodies when output is also a stream — `await res.json()` on a 2GB body is an OOM; stream it.
- `Array.fromAsync(asyncIterable)` (ES2024) materializes when you genuinely need the full array.
- `ReadableStream` is async-iterable; respect cancellation: a `break` out of `for await` cancels the stream (releases the lock) — that's correct behavior, rely on it.

## Retries with backoff, abort-aware

Retry only transient failures (network errors, 429/503), only idempotent operations, bounded attempts, exponential backoff with full jitter, and propagate the caller's signal so cancellation stops the retry loop too.

```ts
async function withRetry<T>(fn: (signal: AbortSignal) => Promise<T>, opts: { attempts?: number; signal?: AbortSignal } = {}): Promise<T> {
  const { attempts = 3, signal } = opts;
  for (let i = 0; ; i++) {
    signal?.throwIfAborted();
    try {
      return await fn(signal ?? new AbortController().signal);
    } catch (e) {
      if (i >= attempts - 1 || !isTransient(e)) throw e;
      const delay = Math.random() * Math.min(1000 * 2 ** i, 10_000);   // full jitter, capped
      await scheduler.wait(delay, { signal });   // or setTimeout-promise with signal
    }
  }
}
```

Retrying on every error (including 400s and bugs) hammers dependencies and hides defects — classify first. Libraries: `p-retry` does this correctly; don't hand-roll in more than one place.

## Race conditions in async code

`await` is a suspension point — shared state may change across it.

```ts
// BAD — check-then-act across await; two concurrent calls both insert
if (!(await db.userExists(email))) await db.insertUser(email);   // TOCTOU
// GOOD — atomic at the source of truth: UNIQUE constraint + upsert/conflict handling

// BAD — stale write: slower older request overwrites newer result
onChange: async (q) => setResults(await search(q));
// GOOD — abort the previous request
onChange: (q) => { ac.abort(); ac = new AbortController(); search(q, ac.signal).then(setResults).catch(ignoreAbort); }
```

- In-memory mutexes (`async-mutex`) only serialize within one process — cross-instance invariants belong in the DB/queue.
- Cache stampede: memoize the promise, not the value, so concurrent callers share one in-flight request:

```ts
const inflight = new Map<string, Promise<User>>();
function getUser(id: string) {
  let p = inflight.get(id);
  if (!p) { p = fetchUser(id).finally(() => inflight.delete(id)); inflight.set(id, p); }
  return p;
}
```

## Async generator cleanup and resource safety

Generators suspended at `yield` still hold resources. A consumer that `break`s or throws triggers the generator's `return()` — put cleanup in `finally`:

```ts
async function* readBatches(db: Db, signal: AbortSignal) {
  const cursor = await db.openCursor();
  try {
    while (!signal.aborted) {
      const batch = await cursor.next();
      if (!batch) return;
      yield batch;
    }
  } finally {
    await cursor.close();    // runs on break/throw/return — guaranteed
  }
}
```

- ES2026 explicit resource management generalizes this: `await using cursor = await db.openCursor();` with `[Symbol.asyncDispose]` on the resource — adopt for locks, files, connections as the runtimes/tsconfig (`lib: esnext.disposable`) allow.
- Browser-side last-resort rejection telemetry: `window.addEventListener('unhandledrejection', e => { report(e.reason); e.preventDefault(); })` — report, don't suppress silently; this is monitoring, not error handling.

## Deferred patterns worth knowing

- `Promise.withResolvers()` (ES2024) replaces the deferred anti-boilerplate when bridging callback/event worlds:

```ts
const { promise, resolve, reject } = Promise.withResolvers<Payload>();
socket.once('reply', resolve);
socket.once('error', reject);
return promise;
```

- Event-to-promise: `once(emitter, 'event', { signal })` from `node:events`; in browsers, wrap `addEventListener(..., { once: true, signal })`.
- Queue/serialize without a library: chain onto a stored promise — `queue = queue.then(() => task())` — each task starts after the previous settles; add a `.catch` so one failure doesn't poison the chain.
- Async cleanup that must not be cancelled (audit flush, lock release): run it in `finally`, and if it's itself async inside an aborted context, detach it deliberately with its own timeout — don't pass the already-aborted signal.

## Audit checklist

- [ ] `@typescript-eslint/no-floating-promises` + `no-misused-promises` enabled and passing — if not, HIGH; floating promises are silent data loss.
- [ ] `grep -rn "Promise.all(" src/` — for each: are the ops independent? Should be `allSettled`? Is parallelism unbounded over user-controlled set sizes (HIGH — self-DoS)?
- [ ] `grep -rn "await" src/ | grep -n "for (\|for(" -B0` → review loops: `grep -rn -A3 "for (const .* of" src/ | grep "await"` — sequential awaits that should be parallel (MEDIUM perf).
- [ ] `grep -rn "fetch(" src/ | grep -v "signal"` — fetches without abort/timeout (MEDIUM; HIGH server-side where a hung upstream pins resources).
- [ ] `grep -rn "addEventListener" src/` — paired removal or `{ signal }`? Unremoved listeners on long-lived targets = memory leak (MEDIUM).
- [ ] `grep -rn "new Promise(async" src/` — lost rejections (HIGH).
- [ ] **Resources released on every exit path** (§"Async generator cleanup and resource
      safety"): `grep -rnE '(const|let|var)[[:space:]]+[A-Za-z_$][A-Za-z0-9_$]*[[:space:]]*=[[:space:]]*await[[:space:]]+[A-Za-z_$.]*(\.open|openCursor|\.connect|\.acquire|getConnection)\(' src/`
      — each hit binds a file handle, cursor, pooled client or lock to a plain variable; confirm a
      `finally` releases it (`close()`/`release()`), or that it is `await using`. A release on
      the happy path only leaks on the first throw (MEDIUM; a pooled client never released is
      lost to the pool, so repeated throws drain it). `await using` needs runtime or compiler support: Node 22.22.1 rejected
      it with a SyntaxError.
- [ ] `grep -rn "setInterval\|setTimeout" src/` — cleared on teardown? Async callbacks with try/catch?
- [ ] `grep -rn "forEach(async\|map(async" src/` — `map(async` without surrounding `Promise.all` = floating (HIGH); `forEach(async` always wrong.
- [ ] `grep -rn "process.nextTick" src/` — app-code use is a smell (LOW).
- [ ] `grep -rn "\.pipe(" src/` — Node pipes without `pipeline()` error handling (MEDIUM).
- [ ] Check-then-act across `await` on shared resources (manual review around `await` + `if` patterns) — TOCTOU (HIGH where it guards uniqueness/money).
- [ ] Top-level `await` in shared/library modules (`grep -rn "^await \|^const .* = await" src/` at module scope) — startup coupling (LOW/MEDIUM).
