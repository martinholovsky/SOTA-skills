# 05 — Performance: GC, allocations, spans, AOT

.NET performance is mostly about **allocation pressure and the GC**, plus using
the modern low-allocation primitives. Measure with BenchmarkDotNet and a
profiler before optimizing. Cross-reference `sota-performance` for methodology.

## 1. The GC and allocation pressure

- The .NET GC is generational (gen0/1/2) with a separate **Large Object Heap**
  (objects ≥ 85,000 bytes). High allocation rate → frequent gen0 collections;
  large/pinned objects fragment the LOH. The win is usually **allocate less**,
  not tune the GC.
- **Server GC** (`<ServerGarbageCollection>true`) for throughput on multi-core
  servers; workstation GC for client/low-latency-single-core. Know which you're
  running. Don't tune GC knobs before profiling shows GC is the bottleneck.

## 2. Reduce allocations

- Avoid needless allocations on hot paths: reuse buffers (`ArrayPool<T>`),
  avoid LINQ allocations in tight loops (closures, iterators, intermediate
  collections), avoid boxing (value type → `object`/non-generic API), and avoid
  `params object[]` / string concatenation in loops (`StringBuilder`, or
  `string.Create`/interpolated handlers).
- Prefer `struct`/`record struct` for small short-lived values to keep them off
  the heap — but beware large structs being copied (pass by `in`/`ref`).

## 3. Span and friends

- `Span<T>`/`ReadOnlySpan<T>`/`Memory<T>` for slicing arrays/strings/stack
  buffers **without copying** — parsing, formatting, buffer processing.
  `stackalloc` for small fixed buffers. C# 14 broadens span conversions
  (`rules/01`).
- `Utf8` APIs, `System.Text.Json` source-gen, and `IBufferWriter<T>` for
  low-allocation I/O. Pool large/reused buffers with `ArrayPool`/`MemoryPool`.

## 4. Async & throughput

- Async done right scales I/O (`rules/03`); done wrong (blocking, sync-over-async)
  it starves the thread pool. `ValueTask`/`ValueTask<T>` for very hot,
  frequently-synchronous paths to avoid a `Task` allocation — but never await a
  `ValueTask` twice, store it, or block on it.

## 5. Measuring

- **BenchmarkDotNet** for microbenchmarks — it handles warmup/JIT, isolates
  runs, and reports allocations (`[MemoryDiagnoser]`). Never `Stopwatch` around a
  loop. Profile with `dotnet-trace`/`dotnet-counters`/Visual Studio profiler /
  PerfView for allocation and GC analysis. Report distributions
  (`sota-performance`).

## 6. Native AOT & trimming

- **Native AOT** (`<PublishAot>true`) ahead-of-time compiles to a native binary:
  fast startup, low memory, small footprint — ideal for CLIs, serverless, and
  containerized microservices. .NET 10 improves AOT (broader support, smaller/
  faster). Costs: no JIT/runtime codegen, so **reflection/dynamic loading must be
  trim-safe** (use source generators; annotate with `IsAotCompatible`); not all
  libraries are AOT/trim-compatible. Test the published binary.
- Choose AOT for startup/footprint-bound workloads; stay on the JIT for
  long-running throughput-bound compute where peak JIT throughput wins.

## Audit checklist

```bash
# Allocation/boxing on hot paths — LOW/MEDIUM (verify with profiler)
grep -rnE '\+ ?"' --include='*.cs' . | grep -iE 'for ?\(|foreach|while'      # string concat in loops
grep -rnE 'string\.Format|\$"' --include='*.cs' . | head                      # hot-path formatting
grep -rnE '\.ToList\(\)|\.ToArray\(\)' --include='*.cs' . | head              # needless materialization in loops

# Server GC configured for a server app?
grep -rnE 'ServerGarbageCollection|ConcurrentGarbageCollection' *.csproj runtimeconfig* 2>/dev/null

# Span/pooling opportunities (hot path) — LOW
grep -rnE 'new byte\[|Substring\(|Split\(' --include='*.cs' . | head           # Span/ArrayPool candidates

# Benchmark hygiene — verify BenchmarkDotNet, not Stopwatch loops
grep -rnE 'Stopwatch' --include='*.cs' . | grep -i bench | head
grep -rnE '\[Benchmark\]|MemoryDiagnoser' --include='*.cs' . || echo "no BenchmarkDotNet benchmarks"

# Native AOT / trimming used? verify trim-safety
grep -rnE 'PublishAot|PublishTrimmed|IsAotCompatible' *.csproj 2>/dev/null
```
