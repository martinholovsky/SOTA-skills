# 01 — Methodology: Measure, Budget, Decide, Protect

Performance work without measurement is guessing; measurement without a budget
is trivia. This file defines how to measure, what numbers mean, and how to
decide what is worth fixing.

## 1. Measure first — with the right instrument

Pick the instrument for the question. Using a CPU profiler to debug an I/O-bound
service tells you nothing.

| Question | Instrument |
|---|---|
| Where does CPU time go? | Sampling CPU profiler → flamegraph |
| Why is wall time >> CPU time? | Off-CPU / wall-clock profiler, async-aware tracing |
| Where does latency go across services? | Distributed tracing (OpenTelemetry spans) |
| Is it the kernel/syscalls? | `strace -c`, eBPF (bpftrace), `perf trace` |
| Memory growth? | Heap profiler, allocation profiler, heap snapshots diff |
| Is this function faster now? | Micro-benchmark harness with statistics |
| Is the system faster? | Load test + latency distribution comparison |

Per-runtime profilers (sampling, production-safe unless noted):

- **Linux native / mixed**: `perf record -g -F 99`, eBPF tools, flamegraphs via
  `perf script | flamegraph.pl` or `samply`.
- **Go**: built-in `pprof` (CPU, heap, mutex, block, goroutine), continuous
  profiling via Pyroscope/Parca. Always enable `net/http/pprof` in services.
- **JVM**: async-profiler (CPU + alloc + locks, no safepoint bias), JFR
  (always-on flight recorder, < 2% overhead).
- **Node.js**: `node --prof`, `--cpu-prof`, Chrome DevTools, `0x` for
  flamegraphs; `perf_hooks.monitorEventLoopDelay` for event-loop lag
  (rules/04 §9). Clinic.js is unmaintained (per its own README) — flag it
  where found; don't adopt.
- **Python**: `py-spy` (attach to live process, no code change), `cProfile`
  (deterministic, high overhead — dev only), `memray` for allocations.
- **Rust/C++**: `perf` + flamegraph, `heaptrack`/`valgrind --tool=massif` (dev).
- **Browser**: Chrome DevTools Performance panel, Lighthouse (lab), RUM (field).

**Rule: profile in production or production-like conditions.** Dev machines
have empty caches, tiny datasets, no contention, and different CPUs. Sampling
profilers at 49–99 Hz are safe in production; prefer continuous profiling so
the data already exists when an incident starts.

## 2. Reading flamegraphs

- **Width = time** (samples). The x-axis is alphabetical, NOT chronological.
- Look for **wide plateaus**: a single wide frame is your hottest code.
- Look for **wide-but-thin towers repeated** under many parents: a hot utility
  (serialization, logging, regex) called from everywhere — fix once, win
  everywhere.
- **CPU flamegraph flat/idle but requests slow?** The time is off-CPU: I/O,
  locks, GC, scheduler. Switch to off-CPU analysis or tracing.
- Inverted (icicle) view answers "which leaf functions burn the most total CPU".

## 3. Benchmarks that don't lie

Micro-benchmarks are adversarial: the compiler, CPU, and OS all conspire to
give you fiction.

```text
BAD                                  GOOD
start = now()                        Use a harness: JMH (JVM), criterion
f()                                  (Rust), go test -bench + benchstat,
print(now() - start)   # one run,    pytest-benchmark, mitata/tinybench (JS).
                       # cold cache, They handle warmup, multiple samples,
                       # no variance # outlier rejection, and statistics.
```

Non-negotiables for any benchmark:

1. **Warm up** until JIT/branch predictors/caches stabilize (harnesses do this).
2. **Many samples, report variance.** A result is `median ± MAD` or a
   confidence interval, never a single number. Two results differ only if the
   intervals don't overlap (Go: `benchstat`, p < 0.05).
3. **Prevent dead-code elimination**: consume results (blackhole/`black_box`).
4. **Realistic data**: production-shaped sizes and distributions. Sorting
   already-sorted arrays or hashing tiny strings benchmarks nothing.
5. **Pin the environment**: fixed CPU governor (`performance`), no turbo
   variance for comparisons, no laptop on battery, no noisy CI neighbors —
   or use dedicated runners / ratio-based comparisons.
6. **Benchmark the distribution, not the mean** of latency-sensitive code.
7. **Avoid coordinated omission** in load tests: closed-loop testers that wait
   for each response before sending the next silently pause during slow
   periods, deleting the worst samples from your data. Use open-loop /
   constant-arrival-rate load (wrk2, vegeta, k6 `constant-arrival-rate`) when
   measuring latency under a target throughput.

## 4. Percentiles, not averages

Averages are arithmetic fiction for latency. Latency distributions are
long-tailed; the mean sits between p50 and p99 and describes no real request.

- **p50**: typical experience. **p95/p99**: the experience of your heaviest
  users (who are often your biggest customers — bigger carts, more data).
- **Tail amplification**: if one page fans out to 50 backend calls, the page
  hits a backend's p99 on `1 - 0.99⁵⁰ ≈ 39%` of loads. Per-service p99 IS the
  user's median when fan-out is high. Budget backends at p999 when fan-out > 10.
- p99/p50 ratio > ~10× signals queueing, GC pauses, lock contention, or cache
  misses — not uniformly slow code.
- Never average percentiles across hosts; aggregate histograms (HDRHistogram,
  Prometheus native histograms / t-digest), then compute percentiles.

## 5. Orders of magnitude — internalize this table

Approximate 2020s hardware; exact values vary, ratios don't.

| Operation | Latency |
|---|---|
| L1 cache hit | ~1 ns |
| L2 cache hit | ~4 ns |
| L3 cache hit | ~10–40 ns |
| Main memory (DRAM) | ~60–100 ns |
| Mutex lock/unlock, uncontended | ~20 ns |
| Syscall (getpid, round trip) | ~100–300 ns |
| NVMe SSD random read | ~20–100 µs |
| Same-DC network round trip | ~100–500 µs |
| Memory read of 1 MB sequential | ~10–50 µs |
| Disk read of 1 MB sequential (NVMe) | ~50–200 µs |
| Cross-AZ round trip | ~1–2 ms |
| Same-region DB query (indexed, warm) | ~0.5–2 ms |
| HDD seek | ~5–10 ms |
| Cross-continent round trip (US↔EU) | ~70–90 ms |
| TLS 1.3 full handshake (cross-continent) | ~1 RTT + crypto ≈ 80–100 ms |

Consequences:

- One avoidable network round trip (~0.5 ms in-DC) costs the same as ~5,000
  DRAM accesses or ~500k L1 hits. **Round trips dominate; count them first.**
- RAM is the new disk: a cache-missing pointer chase (100 ns) is 100× an L1
  hit. Data layout (rules/03) matters for hot loops.
- Anything touching cross-region links is 100,000× slower than memory — cache
  it, move it, or batch it.

## 6. USE and RED

**USE** (Brendan Gregg) — for every hardware/software *resource*:
- **U**tilization: % busy (CPU %, disk busy %, pool in-use/size).
- **S**aturation: queued work (run-queue length, pool wait time, queue depth).
- **E**rrors: error counts (TCP retransmits, pool timeouts, OOM kills).

Saturation, not utilization, predicts latency: 80% CPU with an empty run queue
is fine; 60% CPU with a growing run queue is an incident. Check USE on: CPU,
memory, network, disk, connection pools, thread pools, worker queues, locks.

**RED** — for every *service/endpoint*:
- **R**ate (req/s), **E**rrors (failed/s), **D**uration (latency histogram).

Audit rule: a service without RED metrics per endpoint and USE on its pools is
unauditable at runtime — flag that as a finding itself (Medium).

## 7. Latency budgets

Work backwards from the user:

1. Pick the user-facing SLO: e.g. "search responds in ≤ 300 ms p99".
2. Subtract fixed costs you don't control: client RTT (~50 ms), TLS (resumed,
   ~0), CDN/proxy hops (~5 ms). Remainder = server budget (~245 ms).
3. Decompose across the critical path: auth 10 ms + query 100 ms + ranking
   80 ms + serialization 10 ms = 200 ms, leaving 45 ms slack (keep ≥ 20% slack
   for variance).
4. Assign each component's budget to its owning team/module; enforce in CI
   and alerting per component, not just end-to-end.

A new feature that adds a sequential dependency must fit the remaining slack
or buy budget by optimizing something else. "We'll just add one more call" is
how 300 ms endpoints become 900 ms over two years.

## 8. Amdahl's law — what's worth optimizing

Speedup from optimizing a fraction *p* of total time by factor *s*:
`Speedup = 1 / ((1 − p) + p/s)`.

- Optimizing 10% of runtime **infinitely** yields at most 1.11×. Don't touch
  anything under ~20% of the profile unless it's a one-line fix.
- Corollary for parallelism: 5% serial fraction caps speedup at 20× regardless
  of core count. Find and shrink the serial section (locks, single-threaded
  stages) before adding cores.
- Inverse use: a component that is 60% of latency is where 2× effort yields
  1.43× end-to-end — start there. The flamegraph tells you *p*.

## 9. Premature optimization vs known pathology

The Knuth quote has a second half: "...yet we should not pass up our
opportunities in that critical 3%". Operationalize it:

**Fix on sight, no profiler needed (known pathologies):**
- O(n²)+ on input that can grow (user data, DB rows, list endpoints).
- N+1 queries / RPC-in-a-loop.
- Unbounded memory: caches without eviction, accumulating listeners, reading
  unbounded result sets into memory.
- Blocking calls on async event loops.
- Per-request creation of poolable resources (connections, clients, regexes).
- Missing timeouts/limits.
- Sequential awaits on independent I/O.

These are correctness-adjacent: they work in dev and fail at scale.

**Profile first (speculative optimization):**
- Rewriting idiomatic code into "fast" contorted code.
- Caching something not yet shown to be hot or expensive.
- Micro-tuning (manual loop unrolling, bit tricks, custom allocators).
- Adding concurrency/complexity for an unmeasured win.

Decision test: *"Does this code's cost grow with production scale in a way dev
testing won't reveal?"* Yes → pathology, fix now. No → demand a profile.

One more invariant: optimizations must not erode security — identity-keyed
caching, constant-time comparisons, and validation/size limits are not
overhead to shave (rules/05 §9, sota-code-security).

## 10. Performance regression testing in CI

Performance regressions ship silently; functional tests pass at any speed.

1. **Micro-benchmarks in CI** for hot library code. Compare against the base
   branch with statistical tooling (`benchstat`, JMH + jmh-compare,
   criterion's built-in comparisons). Gate on regressions beyond noise
   (e.g. > 10% with p < 0.05), don't gate on raw thresholds that rot.
2. **Macro load tests** (k6, Locust, Gatling, vegeta) on a fixed-size staging
   environment, nightly or per-release: assert p95/p99 and throughput against
   the budget, with the same dataset every run.
3. **Counting tests beat timing tests in noisy CI.** Assert *invariants* that
   don't depend on machine speed: number of DB queries per request (tools:
   `assertNumQueries` in Django, n+1 detectors like Prosopite/Bullet in Rails,
   query counters in tests), allocation counts per op (Go `testing.AllocsPerOp`,
   JMH GC profiler), bytes over the wire, bundle size (size-limit). These are
   deterministic and catch the most common regressions (a new N+1).
4. **Frontend budgets in CI**: Lighthouse CI with budgets.json (LCP, TBT,
   bundle bytes); fail PRs that exceed them.
5. **Continuous profiling in prod** + alerting on RED p99 per endpoint catches
   what CI misses; keep before/after flamegraphs for every major release.

CI timing noise mitigation: dedicated runners, multiple iterations with
median-of-runs, compare ratios vs base commit on the same machine in the same
job, never compare absolute times across runner generations.

## Audit checklist

- [ ] Is there any profiling/tracing data, or is all perf discussion folklore?
      No data on a "slow" system → first finding: add RED metrics + profiler.
- [ ] Are SLOs/budgets defined in percentiles? Any dashboards showing averages
      only → flag (Medium): averages hide the tail.
- [ ] Compute p99/p50 per hot endpoint; ratio > 10× → investigate queueing,
      GC, locks, cache misses.
- [ ] High fan-out call graphs: is the per-dependency percentile budget set
      accordingly (p999 for fan-out > 10)?
- [ ] Do benchmarks exist? Do they use a statistical harness, warmup,
      realistic data, and report variance? Single-run timing → flag.
- [ ] Does CI gate on any perf signal (query counts, alloc counts, bundle
      size, benchmark deltas)? None → flag (Medium): regressions ship blind.
- [ ] For each proposed/past optimization: what fraction of total time was it?
      (< 20% of profile and non-trivial → likely wasted effort — Amdahl.)
- [ ] Are USE metrics available for pools/queues (saturation especially)?
      Pool wait time unmeasured → flag.
- [ ] Were any "optimizations" added without before/after measurements?
      Treat them as suspect complexity; consider recommending removal.
- [ ] Count network round trips on the critical user journey; verify each is
      necessary, parallelized where independent, and inside the budget.
