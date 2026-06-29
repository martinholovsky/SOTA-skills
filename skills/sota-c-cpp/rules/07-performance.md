# 07 — Performance: profile, allocate less, respect the cache

C++ gives you control over memory layout and dispatch that few languages do —
which means the wins come from *data layout and allocation*, not micro-tweaks.
Measure first: optimize against a profiler and a benchmark, never a hunch.
Cross-reference `sota-performance` for the discipline (latency budgets,
regression gates); this file is the C/C++ specifics.

## 1. Measure before optimizing

- Profile a release build (`-O2`/`-O3 -g`) under realistic load: **perf**
  (Linux, `perf record`/`report`, flame graphs), **Callgrind/KCachegrind**
  (instruction-level), **VTune** (Intel, microarchitecture), or **Instruments**
  (macOS). Find the hot function/loop; don't guess.
- Benchmark with a real harness — **Google Benchmark** — not `chrono` around a
  loop. Beware the optimizer deleting your benchmark: use
  `benchmark::DoNotOptimize`/`ClobberMemory`. Pin frequency/affinity; report
  distribution, not a single number (see `sota-performance`).

## 2. Allocation is the usual bottleneck

- Heap allocation (`new`/`malloc`) is expensive and a contention point. Reduce
  allocations on hot paths:
  - `reserve()` containers to final size; avoid repeated `push_back`
    reallocation.
  - Reuse buffers across iterations instead of reallocating per call.
  - Prefer stack/`std::array` for small fixed sizes; small-buffer-optimized
    types (`std::string`) avoid heap for short data.
  - Custom allocators / memory pools / `std::pmr` (polymorphic memory
    resources, `monotonic_buffer_resource`) for allocation-heavy phases.
- Avoid hidden copies: pass big objects by `const&`; `std::move` into sinks;
  use `emplace_back` to construct in place; watch implicit copies in
  range-`for` (`for (auto x : v)` copies — use `const auto&`).

## 3. Copy elision and move

- Return by value and rely on (N)RVO — do **not** `return std::move(local)`,
  which disables NRVO (`rules/01`). Guaranteed copy elision (C++17) makes
  returning prvalues free.
- Make types cheaply movable (`noexcept` moves) so containers move instead of
  copy on growth.

## 4. Cache locality and data-oriented design

- Memory latency dominates. Favor contiguous storage (`vector`/`array`) over
  node-based containers (`list`, `map`, pointer-chasing trees) on hot paths;
  `std::flat_map`/`flat_set` (C++23) are cache-friendly alternatives.
- Structure-of-arrays (SoA) over array-of-structures (AoS) when you iterate one
  field across many elements — packs the hot field into cache lines.
- Avoid false sharing: align/pad per-thread hot data to
  `std::hardware_destructive_interference_size` (`rules/05`). Keep
  frequently-accessed fields together; cold fields elsewhere.
- Branch-predictable, vectorizable loops beat clever branchy code; `[[likely]]`/
  `[[unlikely]]` only with profile evidence.

## 5. Use the standard library and the compiler

- Prefer `<algorithm>`/ranges (C++20) over hand-rolled loops — they're
  optimized, vectorizable, and correct. `std::sort`, `std::ranges::*`.
- Let the compiler do the work: `-O2` (usually the sweet spot), `-march=native`
  only when you control the target CPU. **LTO** (`-flto`) for cross-TU
  inlining. **PGO** (profile-guided optimization,
  `-fprofile-generate`/`-fprofile-use`) for measurable wins on hot workloads.
- `constexpr`/`consteval` move work to compile time. `[[nodiscard]]` and
  `[[gnu::pure]]`/`const` attributes can enable optimization.

## 6. Common pitfalls

- Premature optimization that hurts readability for unmeasured gain (LOW
  finding — but so is shipping an obvious O(n²) on a hot path that a profiler
  would catch).
- `std::endl` in loops (flushes every call — use `'\n'`); `shared_ptr` where
  `unique_ptr` suffices (atomic refcount cost); virtual calls in tight inner
  loops; `std::function` where a template/`auto` lambda would inline.
- Debug-build performance numbers (sanitizers/`-O0` are 2–50x slower — never
  benchmark them).

## Audit checklist

```bash
# Copies that should be references/moves — LOW
grep -rnE 'for *\( *auto [A-Za-z_]+ *:' --include='*.cpp' .     # range-for by value → const auto&
grep -rn 'return std::move' --include='*.cpp' .                 # disables NRVO
grep -rnE '\.push_back\(' --include='*.cpp' .                   # reserve()? emplace_back?

# Allocation on hot paths / node containers — LOW/MEDIUM (verify with profiler)
grep -rnE 'std::(list|map|set|unordered_map|unordered_set)<' --include='*.cpp' .  # cache-unfriendly?
grep -rn 'shared_ptr' --include='*.cpp' .                       # needed, or unique_ptr?

# Flush-per-line — LOW
grep -rn 'std::endl' --include='*.cpp' .

# Benchmark hygiene — verify release build + DoNotOptimize
grep -rn 'chrono::' --include='*.cpp' . | grep -i bench         # prefer Google Benchmark
grep -rn 'DoNotOptimize\|ClobberMemory' --include='*.cpp' .

# Optimization flags for release?
grep -rnE '\-O[23]|-flto|fprofile-(generate|use)|march=' CMakeLists.txt cmake/ 2>/dev/null

# Profile first (no static grep): perf record -g ./bench && perf report
```
