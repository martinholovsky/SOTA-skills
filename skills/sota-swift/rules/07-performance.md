# 07 — Performance: measure, then fix allocations and dispatch

The general method (latency budgets, regression gates) is `sota-performance`; this file is
Swift's cost model.

## 1. Profile before optimising

- Measure a **release** build — swift.org's build guide calls debug builds *"significantly
  slower"*; a debug profile optimises the wrong thing.
- Profilers by platform: Instruments (Time Profiler, Allocations, Leaks) on Apple platforms;
  `perf` on Linux, including user probes on `malloc` to count allocations (swift.org server
  guides: allocations, linux-perf, memory-leaks-and-usage); `heaptrack`/valgrind where available.
- Benchmarks: `package-benchmark` (ordo-one) tracks wall time, memory allocations, syscalls and
  ARC traffic per benchmark; its baseline format *"is not stable"*, so compare baselines produced
  by the same version in CI.

## 2. Allocation and ARC pressure

- The usual hot-path costs, in order of how often they matter: heap allocations (class
  instances, closures capturing context, existential boxes, string building), ARC retain/release
  traffic on shared references, and copy-on-write copies triggered by an extra reference.
- **Existentials cost**: SE-0413 on `any Error` — it *"incurs some necessary overhead, in code
  size, heap allocation overhead, and execution performance"*. On hot paths prefer generics or
  `some P` to `any P` parameters and `[any P]` arrays.
- **Copy-on-write**: mutate collections in place; an accidental second reference (a captured
  copy, a stored alias) turns every mutation into a full copy. `isKnownUniquelyReferenced`
  confirms uniqueness in custom COW types.
- `final` classes and `private`/`fileprivate` members allow static dispatch.
- Reserve capacity (`reserveCapacity`) when the size is known; avoid building `String`s in loops
  for logs that are filtered out (swift-log's autoclosure message parameters already defer this).

## 3. Concurrency costs

- Actor hops and task creation are not free: do not create a `Task` per tiny unit of work; batch.
- Contention on one actor serialises everything behind it; shard state or use value pipelines.
- `@concurrent` (Swift 6.2) is where parallelism is wanted; justify it with a profile.

## Audit checklist

- [ ] Profiling before optimizing: performance changes cite a release-build profile (Instruments, `perf`, or package-benchmark), not a debug build or intuition.
- [ ] Allocation / GC-style pressure: hot paths avoid `any P` existentials (grep `: *any +[A-Z]|\[any +[A-Z]`), per-iteration closure or class allocations, and string building in loops.
- [ ] No accidental copy-on-write copies on hot collections (extra references reviewed); capacity reserved where sizes are known.
- [ ] Benchmarks that gate CI compare baselines from the same package-benchmark version; no `Task` per tiny work item; hot actors are not a serialisation bottleneck.
