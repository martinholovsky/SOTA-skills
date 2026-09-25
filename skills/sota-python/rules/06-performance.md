# 06 — Performance

Order of operations: **measure, fix the algorithm, fix the data structure, vectorize or move
to native, only then micro-optimize.** Every optimization PR cites a profile; "should be
faster" without numbers is rejected.

## 1. Profile first — tool selection

| Question | Tool |
|---|---|
| Where does CPU time go (dev, deterministic) | `cProfile` + `snakeviz` / `python -m cProfile -o out.prof` |
| What is prod doing *right now*, no restart, low overhead | `py-spy top --pid N`, `py-spy record -o flame.svg --pid N` |
| CPU vs memory vs copy time, line-level, GPU | `scalene mypkg/main.py` |
| Memory growth / leaks | `tracemalloc` snapshots, `memray` |
| Micro-benchmarks of one expression | `python -m timeit`, `pytest-benchmark`, `pyperf` (statistically sound) |

Rules:
- py-spy is safe on production (samples out-of-process; add `--native` for C extensions,
  `--gil` to see GIL contention). cProfile distorts hot loops — fine for *finding* hotspots,
  not for before/after numbers; use pyperf/pytest-benchmark for comparisons.
- Profile realistic data sizes. O(n²) is invisible at n=100.
- Keep a benchmark in the repo for any code with a perf SLA (`pytest-benchmark` with
  `--benchmark-autosave` to track regressions).

## 2. The usual suspects (hot-loop killers)

**String concat in loops — O(n²):**
```python
# Bad
out = ""
for part in parts:
    out += render(part)

# Good — O(n)
out = "".join(render(p) for p in parts)
# Many formatted pieces: io.StringIO or a list + join
```

**Membership tests against a list — O(n) each:**
```python
# Bad — O(len(allowed)) per check, O(n*m) total
if user.role in allowed_roles_list: ...

# Good — build once, O(1) per check
allowed = frozenset(allowed_roles_list)
if user.role in allowed: ...
```
Same for dedupe: `seen: set[str]` not a list. `list.pop(0)`/`insert(0, ...)` → `deque`.

**Repeated lookups in hot loops** — attribute/global/method resolution costs per iteration:
```python
# Good — hoist invariants out of the loop
append = results.append          # method lookup once
pattern = re.compile(r"...")     # NEVER re.compile inside the loop; module level
for line in lines:
    m = pattern.match(line)
    if m:
        append(m.group(1))
```
Also hoist `len()`, dotted constants (`self.config.threshold` → local), and dict `.get`
bound methods. Only do this in *measured* hot loops — it hurts readability.

**List vs generator:**
- Generator when you iterate once or might stop early (`any`, `next`, streaming) — O(1) memory.
- List when you iterate multiple times, need `len`/indexing, or the consumer is `str.join`
  (join materializes anyway — a list is marginally faster there).
- Never `list(...)` just to loop over it once.

**Other classics:** `sort(key=...)` not `functools.cmp_to_key`; `Counter` not manual dict
counting; `dict.setdefault`/`defaultdict` not check-then-insert; exception setup is cheap but
raising in a hot loop is not — restructure if a "miss" is the common case.

## 3. Vectorize: numpy / polars over Python loops

A Python-level loop over a million floats is ~100× slower than the vectorized equivalent.

```python
# Bad — interpreter-bound
total = 0.0
for row in rows:
    if row["qty"] > 0:
        total += row["qty"] * row["price"]

# Good — polars (multi-threaded, lazy, no GIL contention)
total = (
    df.lazy()
      .filter(pl.col("qty") > 0)
      .select((pl.col("qty") * pl.col("price")).sum())
      .collect()
      .item()
)

# numpy equivalent for array math
mask = qty > 0
total = float(np.dot(qty[mask], price[mask]))
```

- Tabular pipelines in 2026: **polars** by default (lazy frames, predicate pushdown, Arrow
  interop); pandas where ecosystem demands it — then prefer Arrow-backed dtypes and avoid
  `DataFrame.apply` with Python lambdas (it's a loop in disguise) and `iterrows` (worst case).
- The cardinal sin is *mixed* mode: a vectorized frame iterated row-by-row in Python.
  If you must apply a Python function elementwise, you've left the fast path — reconsider
  (expression API, `np.vectorize` is NOT faster, numba/cython for genuine custom kernels).
- Crossing the boundary costs: batch conversions (`tolist()` once, not `float(x)` per element).

## 4. Caching with functools — and the caveats

```python
@functools.cache                      # unbounded — only for small, finite domains
def parse_spec(spec: str) -> Spec: ...

@functools.lru_cache(maxsize=1024)    # bounded — default choice for hot pure functions
def resolve(name: str) -> Target: ...
```

Caveats that bite:
- **Unbounded `@cache` on user-influenced arguments = memory leak / DoS.** If callers control
  the argument space, use `lru_cache(maxsize=N)` or an external TTL cache (`cachetools.TTLCache`).
- **Methods:** `@cache` on an instance method keys on `self` → the cache keeps every instance
  alive forever. Use `@cached_property` for per-instance memoization, or cache a module-level
  function taking explicit args.
- **Invalidation:** functools caches never expire. Anything whose answer can change (config,
  DNS, feature flags, files) needs TTL or explicit `cache_clear()` wired to the change event —
  and `cache_clear()` in tests (autouse fixture) or tests pollute each other.
- Arguments must be hashable; `lru_cache` keys distinguish `f(1)` from `f(x=1)`.
- Caching wraps exceptions? No — exceptions are not cached; a failing call re-executes (can
  stampede). For expensive fallible calls add single-flight locking.

## 5. Concurrency model: threads vs processes vs asyncio

| Workload | Choice | Why |
|---|---|---|
| Many slow network calls, one service | **asyncio** | thousands of concurrent ops, single thread, no sync overhead |
| Blocking-library I/O, moderate fan-out | **ThreadPoolExecutor** | GIL released during I/O; simplest retrofit |
| CPU-bound pure Python | **ProcessPoolExecutor** / multiprocessing | GIL serializes threads; processes get real parallelism |
| CPU-bound numpy/polars | often **none needed** | native code releases the GIL / is internally parallel |
| CPU-bound on a free-threaded build (officially supported since 3.14, PEP 779) | threads become viable | measure first; see rules/01 §8 |

- GIL reality (default build): threads never speed up pure-Python CPU work; they *do* help
  I/O and GIL-releasing extensions. Don't "add threads" to a CPU loop and call it done.
- Process pools: pickling costs dominate small tasks — chunk work; pass paths/ids, not fat
  objects; prefer `concurrent.futures` API over raw `multiprocessing`. 3.14 changed the
  Unix default start method from `fork` to `forkserver` (Windows/macOS stay `spawn`) —
  module-global state is no longer inherited; guard with `if __name__ == "__main__"` and
  request `fork` explicitly via `get_context("fork")` only if you must.
- Subinterpreters shipped in 3.14 (PEP 734): `concurrent.interpreters` +
  `concurrent.futures.InterpreterPoolExecutor` — share a process, isolated GILs. A real
  middle ground now, but ecosystem support is young; benchmark before betting on it.
- Mixing: asyncio app with CPU spikes → `loop.run_in_executor(process_pool, ...)` (rules/04 §3).

## 6. Startup latency: lazy imports

CLI tools and serverless functions pay import cost on every invocation. `import pandas`
alone can be 500ms+.

```python
# Bad — every `mycli --help` pays for pandas
import pandas as pd

def report_cmd(path: str) -> None: ...

# Good — defer heavy imports into the command that needs them
def report_cmd(path: str) -> None:
    import pandas as pd            # local import: only this command pays
    ...
```

- Measure with `python -X importtime -c "import mypkg" 2>&1 | sort -t'|' -k2 -rn | head` or
  `tuna` for visualization.
- Combine with `TYPE_CHECKING` imports for annotation-only deps (rules/02 §10).
- PEP 810 explicit lazy imports (`lazy import x`, `-X lazy_imports`) are added in 3.15;
  until your floor is 3.15, function-local imports are the idiom.
  Don't lazy-import inside hot loops (lookup cost per call is small but real —
  module-level once the function is hot path).

## 7. Memory

- `slots=True` dataclasses (rules/03 §7) for objects allocated in volume.
- Generators/streaming over materializing: read files with iteration, not `.read()` of
  multi-GB files; `json` → `ijson`/msgspec streaming for huge payloads.
- `sys.intern()` for millions of repeated strings (parser tokens, column values).
- numpy/Arrow buffers instead of lists-of-floats: 24 bytes/float object vs 8 bytes flat.
- Watch accidental retention: caches on methods (§4), default mutable args, closures over
  large frames, `lru_cache` on functions taking DataFrames.

## 8. I/O and serialization throughput

CPU profiles often blame the interpreter when the real cost is chatty I/O or slow codecs:

- **Batch the round trips.** One query returning 1,000 rows beats 1,000 queries (rules/07
  N+1); one `executemany`/`COPY`/`bulk_create` beats row-at-a-time inserts; pipeline redis
  commands; batch S3/HTTP calls behind a concurrency-bounded TaskGroup (rules/04 §9).
- **JSON:** stdlib `json` is the slow path. For hot serialization use `msgspec` (fastest,
  typed decode in one step) or `orjson`. Typed `msgspec.Struct` decode replaces
  json.loads + pydantic validation at a fraction of the cost when the schema is fixed —
  keep pydantic where you need its coercion/error UX, not on the hot path of an internal
  service mesh.
- **File reading:** iterate (`for line in f`) instead of `.read().splitlines()` on big
  files; `Path.read_bytes()` once instead of many small reads; `mmap` for random access to
  large read-only files.
- **Compression trade:** zstd dominates gzip on both axes for service-to-service payloads
  and cache entries; gzip survives only for compatibility. On 3.14+ it's stdlib
  (`compression.zstd`, PEP 784); older floors use the `zstandard` package.
- Buffered writes: thousands of small `f.write()` calls are fine (buffered), but thousands
  of `open()/close()` cycles are not — hoist the file handle out of the loop.

## 9. Don'ts

- Don't micro-optimize cold code; don't trade clarity for unmeasured wins.
- Don't catch the "optimization" of removing logging — fix lazy formatting instead (rules/03 §11).
- Don't hand-roll C extensions before trying polars/numpy/numba/Rust-via-pyo3 — maintenance
  cost dwarfs the speedup.
- Don't benchmark with `time.time()` — `time.perf_counter()` or pyperf.

## Audit checklist

- [ ] **Ruff perf rules** — `uvx ruff check --select PERF,C4,SIM --statistics .`
- [ ] **String building & containers [hot-loop suspects]** —
      `grep -rn "+= .*str(\|+= f\"\|+= \"" --include="*.py" src/` (concat in loops? check
      context); `grep -rn "\.pop(0)\|insert(0," --include="*.py" src/` (O(n) deque ops);
      `grep -rn "in \[" --include="*.py" src/ | head` (list membership in conditions)
- [ ] **re.compile / invariant work inside loops [manual: confirm loop context]** —
      `grep -rn "re.compile\|re.match\|re.search" --include="*.py" src/ | head -30`
- [ ] **DataFrame antipatterns [MEDIUM in data code]** —
      `grep -rn "iterrows\|itertuples\|\.apply(lambda" --include="*.py" src/` ;
      `grep -rn "for .* in df\[" --include="*.py" src/`
- [ ] **Cache hygiene** — `grep -rn "@cache$\|@functools.cache" --include="*.py" src/`
      (unbounded — user-controlled args? on methods?);
      `grep -rn "@lru_cache" --include="*.py" src/ -A2 | grep "def .*(self"` (instance leak
      [MEDIUM]); `grep -rn "cache_clear" --include="*.py" tests/ src/` (invalidation/test
      isolation present?)
- [ ] **Concurrency model sanity** — `grep -rn "ThreadPoolExecutor" --include="*.py" src/` (used
      for CPU-bound work? [MEDIUM]);
      `grep -rn "multiprocessing\|ProcessPoolExecutor" --include="*.py" src/ | head` ;
      `grep -rln "if __name__" $(grep -rln ProcessPoolExecutor --include="*.py" src/ 2>/dev/null)`
- [ ] **Import-time cost (CLIs/lambdas)** —
      `python -X importtime -c "import mypkg" 2>&1 | sort -t'|' -k2 -rn | head -15` ;
      `grep -rn "^import pandas\|^import numpy\|^import torch" --include="*.py" src/*cli* src/*/cli* 2>/dev/null`
- [ ] **Benchmarks exist for perf-critical code?** —
      `grep -rln "pytest-benchmark\|pyperf" pyproject.toml tests/ 2>/dev/null`