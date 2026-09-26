# 03 — Memory: Allocation, Layout, Leaks, GC

Memory problems present as CPU problems (GC burn, cache misses), latency
problems (pauses, page faults), and reliability problems (OOM). This file
covers allocation discipline, data layout, leak patterns per runtime, and GC
tuning principles.

## 1. Allocation pressure

Every allocation costs: the allocation itself (~10–50 ns fast path), future GC
work proportional to allocation *rate*, and cache pollution. In managed
runtimes, **allocation rate is the GC tax base** — halving allocations/sec
roughly halves GC CPU.

Hot-path rules (a "hot path" runs ≥ ~10⁴ times/sec or inside a per-request loop):

- **Don't allocate per iteration what can be allocated per batch/request.**

```go
// BAD — allocates a new buffer per call; 50k req/s × 64 KB = 3 GB/s churn
func handle(w io.Writer, r *Req) {
    buf := make([]byte, 64*1024)
    process(buf, r, w)
}

// GOOD — reuse via sync.Pool (Go), ThreadLocal/ringbuffer (JVM), or
// preallocated per-worker buffers. Pool a *pointer*: Put([]byte) boxes the
// slice header and allocates every call (staticcheck SA6002); measured
// 2026-09-26: 1 vs 0 allocs/op. Pool criteria in sota-golang rules/06.
var bufPool = sync.Pool{New: func() any { b := make([]byte, 64*1024); return &b }}
func handle(w io.Writer, r *Req) {
    bp := bufPool.Get().(*[]byte)
    defer bufPool.Put(bp)
    process(*bp, r, w)
}
```

- **Pre-size growable containers** when the size is known or estimable:
  geometric regrowth is O(n) amortised, but every doubling still copies the
  whole buffer, spikes peak memory and fragments.
- **Avoid hidden allocators**: boxing (Java `Integer` in hot loops, Go
  `interface{}` conversions), closure capture creating heap escapes, string
  formatting/concat, iterator/lambda allocation per call in some runtimes,
  substring/slice APIs that copy, `JSON.parse`/reflect-based serialization of
  large objects per message.
- **Escape analysis is your friend** (Go `-gcflags=-m`, JVM does it silently):
  keep values stack-allocatable — don't return pointers to locals needlessly,
  don't store short-lived values into longer-lived structures.
- Measure, don't guess: Go `testing.AllocsPerOp` / pprof alloc profile; JVM
  async-profiler `-e alloc`; .NET `dotnet-counters` alloc rate; Python
  `memray`/`tracemalloc`. Allocation profiles are usually more actionable
  than CPU profiles in managed services.

## 2. Object pooling — when it helps and when it hurts

Pooling pays when the object is **expensive to create** (connections, TLS
sessions, big buffers, compiled regexes, ML sessions) or when allocation rate
is a measured GC bottleneck.

Pooling **hurts** when:
- Objects are cheap: modern allocators/GCs make small short-lived objects
  nearly free (bump-pointer alloc + die-young = generational hypothesis).
  Pooling them adds synchronization, retention, and bugs for nothing.
- Pooled objects hold stale state → correctness bugs (the classic "user A sees
  user B's data" is often a dirty pooled buffer). Reset on return, always.
- The pool is unbounded → it's a leak; or sized wrong → contention point.
- In GC'd runtimes, long-lived pools promote objects to old-gen, making major
  GCs scan more — pooling can *increase* GC cost if the objects are small.

Rules: bound the pool, reset state on return/acquire, measure before and
after, prefer per-worker (sharded) pools over one global locked pool.

## 3. Arena allocation (concept)

Arena/region allocation: allocate many objects from one contiguous block with
a bump pointer; free them **all at once** by resetting the arena. Fits
phase-structured work: per-request, per-frame, per-compilation-unit.

- Wins: allocation ≈ pointer increment (~1–2 ns); zero per-object free cost;
  perfect locality (objects allocated together sit together); no fragmentation.
- Native: explicit arenas (Rust `bumpalo`, C `talloc`/APR pools, jemalloc
  arenas). Managed analogs: reusing one large buffer + indices, .NET
  `ArrayPool`+spans, flatbuffers-style serialization into one slab, Go arena
  experiment (frozen — use pooled slabs instead).
- Constraint: nothing allocated in the arena may outlive it. Escaping pointers
  are use-after-free (native) or force copies (managed). Design the lifetime
  boundary first (request scope is the natural one).

## 4. Cache locality — layout is performance

DRAM access is ~100 ns; L1 is ~1 ns. The CPU fetches 64-byte cache lines and
prefetches sequential patterns. Hot-loop throughput is usually bounded by
memory layout, not instruction count.

- **Sequential beats random**: iterating a contiguous array can be 10–100×
  faster than chasing pointers (linked lists, object graphs) over the same
  elements. Prefer arrays/vectors of values over collections of heap pointers
  in hot loops.
- **Smaller is faster**: shrinking a hot struct from 80 to 48 bytes puts more
  elements per cache line; use compact field types, reorder fields to kill
  padding (largest first), use indices (u32) instead of 8-byte pointers.
- **Row-major vs column-major**: iterate 2D data in memory order; wrong order
  multiplies cache misses (classic `a[j][i]` vs `a[i][j]` — up to 10× on big
  matrices).
- **False sharing**: two threads writing different variables on the same
  64-byte line ping-pong the line between cores (~100× slowdown on counters).
  Pad/align per-thread hot data (`#[repr(align(64))]`, `@Contended`,
  cache-line padding in counter arrays).

### Struct-of-Arrays vs Array-of-Structs

```text
AoS: [ {x,y,z,vx,vy,vz,hp,name…}, … ]   — natural OO layout
SoA: { x:[…], y:[…], z:[…], hp:[…], … } — column layout
```

- Loop touches *few fields of many records* (analytics, physics, filtering by
  one column) → **SoA**: only needed bytes enter cache, SIMD vectorizes
  naturally. This is why columnar formats (Arrow, Parquet, DuckDB) win for
  scans.
- Loop touches *all fields of one record* (per-entity logic, OLTP row access)
  → **AoS**: one cache line per record.
- Hybrid (AoSoA) for SIMD kernels. In managed languages, SoA = parallel
  primitive arrays instead of object lists — also removes per-object headers
  (12–16 bytes/object on JVM) and pointer chasing.

## 5. Memory leak patterns per runtime

A leak in GC'd runtimes = unintended *reachability*. Hunt the references.

**JavaScript / Node / browser**
- Closures capturing large scopes: a small callback retaining a parsed 50 MB
  document because it references one field. Extract the field before closing.
- `addEventListener` / `on(...)` without removal — especially on long-lived
  emitters (sockets, window, global stores) from short-lived components.
  Symptom: `MaxListenersExceededWarning`; fix: `removeEventListener`,
  `AbortSignal`-based listeners, framework cleanup hooks.
- Timers: `setInterval` never cleared retains its closure forever.
- Module-level caches (`const cache = new Map()`) without eviction.
  Use bounded LRU (`lru-cache`) or `WeakMap` keyed by the owning object.
- Detached DOM nodes retained by JS references (browser).
- Tooling: heap snapshot diff in DevTools, `--inspect`, look at "Retainers".

**Python**
- Module-level dict/list accumulators; `functools.lru_cache` on methods
  (retains `self` for every instance — use `cached_property` or bounded
  per-instance caches); default mutable args accumulating.
- Reference cycles with `__del__` (delays collection), C-extension leaks.
- Large object retained by an exception traceback held in a variable.
- Tooling: `tracemalloc` snapshots diff, `memray`, `objgraph` for retainers.

**JVM**
- `static` collections/caches without eviction (the canonical Java leak).
- `ThreadLocal` not removed on thread-pool threads (threads live forever →
  values live forever).
- Listener/observer registration without deregistration; inner-class instances
  retaining outer `this`.
- ClassLoader leaks on redeploy (web containers).
- Unclosed resources (use try-with-resources): direct ByteBuffers and native
  handles leak off-heap.
- Tooling: heap dump + Eclipse MAT "dominator tree"; JFR allocation/leak views.

**Go**
- Goroutine leaks: a goroutine blocked forever on a channel nobody closes or a
  context never cancelled — each retains its whole stack and referenced heap.
  Audit every `go func` for a guaranteed exit path; `pprof/goroutine` count
  must plateau.
- Subslices retaining huge backing arrays (`small := big[:3]` keeps all of
  `big`) — copy when keeping a sliver. Same for substrings pre-1.21 patterns.
- `time.Ticker` not stopped; maps that only grow (maps never shrink — replace
  the map to reclaim).

**General (all runtimes)**: any cache/map/registry with `put` but no
`remove/TTL/LRU` is a leak by construction — flag without running anything.
Symptom signature in metrics: sawtooth baseline that ratchets upward after
each GC; old-gen/heap floor climbing across days.

## 6. Serialization and copies — the silent memory tax

Serialization sits on nearly every hot path and is routinely the top
allocator in service profiles.

```javascript
// BAD — three full materializations of a 20 MB payload per request:
// object graph → JSON string → Buffer
const data = await loadBigReport(id);          // 20 MB of objects
const json = JSON.stringify(data);             // +20 MB string
res.end(Buffer.from(json));                    // +20 MB buffer

// GOOD — stream rows; peak memory = one chunk
res.setHeader("content-type", "application/json");
await pipeline(reportRowStream(id), jsonArrayStringify(), res);
```

- Prefer encoders that write to the output stream (`json.NewEncoder(w)` in
  Go, Jackson streaming, `serde` to writer) over encode-to-string-then-write.
- Don't round-trip for deep copy (`JSON.parse(JSON.stringify(x))` →
  `structuredClone` or targeted copies).
- Parse selectively for huge documents: streaming/SAX parsers, or formats
  with lazy/zero-copy access (flatbuffers, Cap'n Proto, Arrow for columnar).
- Intermediate collection chains (`filter().map().map()` materializing each
  stage on big inputs) → fuse into one pass or use lazy iterators
  (generators, Rust iterators, Java streams are already lazy until collect).

## 7. GC tuning principles

Tune in this order — most GC problems are application problems:

1. **Reduce allocation rate first** (§1). No GC flag beats allocating less.
2. **Right-size the heap.** Too small → constant collection; absurdly large →
   long full collections and wasted RAM. Aim for live-set × 2–4 as a starting
   point. Set container limits and GC heap % consistently
   (`-XX:MaxRAMPercentage`, `GOMEMLIMIT`, `--max-old-space-size`) — a JVM/Go
   process that doesn't know its cgroup limit OOMs instead of collecting.
3. **Pick the collector for the goal**: throughput batch jobs → throughput
   collector (Parallel); latency-sensitive services → low-pause concurrent
   collectors (G1 default, ZGC/Shenandoah for < 1 ms pauses on big heaps;
   modern ZGC is generational). Go: one GC, tune `GOGC` (collection frequency
   vs heap growth) and `GOMEMLIMIT` (hard cap).
4. **Watch promotion, not just pauses**: short-lived objects surviving into
   old gen (because of pools, caches, or batch lifetimes) make major GCs
   expensive. Generational hypothesis: die young or live forever — avoid the
   middle.
5. **Measure GC like latency**: pause time distribution (p99), GC CPU %, and
   allocation rate. GC CPU > ~10% or pauses inside your latency budget →
   act. Enable GC logs/JFR in prod; they're nearly free.
6. Don't cargo-cult flags. Every GC flag pasted from a blog without a
   before/after measurement is a liability — audit finding if you see a wall
   of unexplained `-XX:` flags.

## Audit checklist

- [ ] Grep for caches/maps/registries with insertion but no eviction, TTL, or
      removal path → leak by construction (High if keyed by user/request data).
- [ ] Event listeners, subscriptions, timers: every registration paired with a
      cleanup on the owner's lifecycle?
- [ ] Go: every spawned goroutine has a guaranteed exit (context cancel,
      channel close)? Tickers stopped?
- [ ] JVM: `static` collections, `ThreadLocal` on pooled threads without
      `remove()`, unclosed resources?
- [ ] JS: `setInterval` cleared? Listeners on global/long-lived objects
      removed? Module-level Maps bounded?
- [ ] Python: `lru_cache` on methods? Module-level accumulators?
- [ ] Hot paths: per-iteration allocation of buffers/objects that could be
      pooled or hoisted? Containers pre-sized?
- [ ] Any pooling of cheap objects (adds complexity, no win) or pools without
      bounds/reset (bug factory)?
- [ ] Hot data structures: pointer-chasing collections where contiguous arrays
      would do? Hot loops touching few fields of fat structs (SoA candidate)?
- [ ] Shared mutable counters/flags written by multiple threads without
      cache-line padding (false sharing)?
- [ ] Heap/RSS trend over days: does the floor after GC ratchet upward?
- [ ] Runtime knows its memory limit (`GOMEMLIMIT`, `MaxRAMPercentage`,
      `--max-old-space-size` aligned with container limit)?
- [ ] GC metrics exported (pause p99, GC CPU %, alloc rate)? Unexplained GC
      flag soup in deploy configs?
