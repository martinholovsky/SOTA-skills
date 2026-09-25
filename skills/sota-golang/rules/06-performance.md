# 06 — Performance: profiling, allocations, GC, PGO

Rule zero: **measure before and after; optimize only what profiles indict.**
Clarity-destroying micro-optimizations without a benchmark are LOW findings
in audits, same as obvious waste on a measured hot path.

## 1. pprof workflow

Wire profiling into every service (auth-gated or bound to localhost/admin
port — exposing pprof publicly is a MEDIUM info-leak/DoS finding):

```go
import _ "net/http/pprof" // registers on http.DefaultServeMux

go func() { // separate internal-only listener, never the public mux
    slog.Error("pprof", "err", http.ListenAndServe("localhost:6060", nil))
}()
```

Capture and analyze:

```bash
go tool pprof -http=:8081 'http://localhost:6060/debug/pprof/profile?seconds=30'  # CPU
go tool pprof -http=:8081 'http://localhost:6060/debug/pprof/heap'                # live heap (inuse_space)
go tool pprof -sample_index=alloc_space -http=:8081 '.../debug/pprof/heap'        # cumulative allocs
curl -s 'localhost:6060/debug/pprof/goroutine?debug=2'                             # goroutine dump (leak hunt)
go tool pprof '.../debug/pprof/mutex'     # contention; needs runtime.SetMutexProfileFraction(>0)
go tool pprof '.../debug/pprof/block'     # blocking; needs runtime.SetBlockProfileRate(>0)
curl -s 'localhost:6060/debug/pprof/goroutineleak?debug=1'  # leak profile: GA in 1.27; 1.26 needs GOEXPERIMENT=goroutineleakprofile
```

Reading order for a perf complaint: CPU profile (flame graph) → if CPU is in
`runtime.mallocgc`/GC, switch to heap `alloc_space` to find allocation sites →
if CPU is idle but latency high, goroutine/block/mutex profiles. `runtime/trace`
(`go tool trace`) for scheduler-level mysteries: long GC pauses, goroutine
starvation, syscall stalls. Continuous profiling (Parca/Pyroscope/Cloud
Profiler) is SOTA for production — point-in-time pprof lies about spiky loads.
Go 1.25 adds `trace.FlightRecorder` for capturing the moments *before* an
anomaly.

## 2. Benchmarks with testing.B

```go
func BenchmarkParse(b *testing.B) {
    data := loadFixture(b)      // setup outside the loop
    b.ReportAllocs()
    for b.Loop() {              // Go 1.24+: replaces `for i := 0; i < b.N; i++`
        parse(data)             // b.Loop prevents the compiler optimizing the call away
    }
}
```

- `b.Loop()` (1.24+) auto-excludes setup/teardown from timing and keeps the
  loop body from being dead-code-eliminated — the old `b.N` + global-sink
  idiom is obsolete; on older Go, assign results to a package-level sink.
  Go 1.26 fixed `b.Loop` blocking inlining in the loop body (which skewed
  allocs/op on 1.24/1.25) — on 1.26+ migrate all `b.N` benchmarks with no
  caveats.
- Always `b.ReportAllocs()`; allocs/op regressions are the early warning.
- Run with `-count=10` and compare using **benchstat** (significance, not
  vibes): `go test -bench=. -count=10 | benchstat old.txt new.txt`.
  Single-run deltas under ~5% are noise.
- `-benchmem`, `-cpuprofile`/`-memprofile` on benchmarks feed pprof directly:
  `go test -bench=Parse -cpuprofile=cpu.out && go tool pprof cpu.out`.
- Benchmark with realistic data sizes/shapes; `b.Run` sub-benchmarks over a
  size table exposes O(n²) cliffs.

## 3. Allocation reduction

Allocations cost three times: malloc, GC mark, cache misses. The biggest wins:

**Preallocate when length is known:**

```go
// BAD — grows: repeated alloc+copy
var out []Item
for _, r := range rows { out = append(out, convert(r)) }

// GOOD
out := make([]Item, 0, len(rows))
for _, r := range rows { out = append(out, convert(r)) }

m := make(map[string]int, len(keys)) // maps too
```

**String building** — `+` in a loop is O(n²) allocs:

```go
var sb strings.Builder
sb.Grow(estimatedLen)          // one alloc if estimate holds
for _, p := range parts { sb.WriteString(p) }
s := sb.String()               // no copy: Builder transfers ownership
```

Also: `strconv.AppendInt(buf, n, 10)` family over `fmt.Sprintf` on hot paths
(fmt reflects and allocates); `fmt.Appendf` over Sprintf-then-copy.

**string ↔ []byte**: each conversion copies. Avoid round-trips; work in one
domain. Map lookups `m[string(bytes)]` and `switch string(b)` are
compiler-optimized (no alloc) — don't contort code to avoid those. For
zero-copy in extreme hot paths, 1.20+ `unsafe.String(ptr, len)` — only under
the `rules/05 §7` unsafe policy, with the immutability invariant proven.

**sync.Pool** — justified only when ALL hold: profile shows the allocation
hot (GC pressure), objects are large or expensive, lifetime is strictly
scoped (get → use → put, no retention), contents fully reset on put.
Pools of small objects or pooling "just in case" adds complexity and can be
slower. Classic correct use: per-request buffers in high-QPS encoders.

```go
var bufPool = sync.Pool{New: func() any { return new(bytes.Buffer) }}

buf := bufPool.Get().(*bytes.Buffer)
buf.Reset()                       // ALWAYS reset on get or put
defer bufPool.Put(buf)
```

Cap what you return to the pool (don't pool 64MB outliers — check
`buf.Cap()` before Put). Never put slices whose backing array is still
referenced elsewhere (aliasing corruption — HIGH).

**Misc**: reuse buffers across loop iterations (`buf = buf[:0]`); avoid
`[]byte(fmt.Sprintf(...))`; prefer streaming (`io.Copy`, `json.NewEncoder(w)`)
over materializing (`io.ReadAll`, `json.Marshal` then `w.Write`); value
receivers on small structs avoid pointer-chasing, but see escape analysis.

## 4. Escape analysis basics

`go build -gcflags='-m'` (or `-m -m` for detail) shows what escapes to heap.
You don't fight every escape — just know the triggers on hot paths:

- Returning a pointer to a local → escapes (fine; that's how constructors work).
- Storing into an interface (`fmt.Sprintf` args, `slog` `[]any`, `any` params)
  → escapes. This is why `LogAttrs`/`strconv.Append*` beat fmt on hot paths.
- Closures capturing by reference, sending pointers to channels, slices that
  outgrow their scope → escape.
- `make([]byte, n)` with variable `n` escapes; constant small `n` can stay on
  stack.
- Don't return `*T` "for performance" on small structs — value returns often
  stay stack-allocated and copy cheaper than the GC cost of the escape.

## 5. GC tuning: GOGC and GOMEMLIMIT

Defaults first; tune only with metrics (`runtime/metrics`, GC CPU fraction,
RSS). Go 1.26 ships the Green Tea GC by default (10–40% lower GC overhead,
more on AVX-512-class CPUs) — re-baseline GC metrics after upgrading before
re-tuning; `GOEXPERIMENT=nogreenteagc` is a temporary escape hatch announced
for removal — still accepted by go1.27.1 (measured), so verify per release
before relying on it.

- **`GOMEMLIMIT`** (1.19+) is the main knob in containers: set to ~90% of the
  container memory limit (`GOMEMLIMIT=900MiB` for a 1Gi pod). It's a soft
  limit — GC runs harder as you approach it instead of OOM-killing. Leave
  headroom for non-heap memory (stacks, cgo, mmap).
- **`GOGC`** trades memory for CPU: `GOGC=200` halves GC frequency
  (more heap), `GOGC=50` doubles it (less heap). With GOMEMLIMIT set,
  `GOGC=off` + memlimit is a valid "use all the RAM I'm given" strategy for
  batch jobs; risky for spiky services (death-spiral near the limit —
  watch `/gc/limiter/last-enabled:gc-cycle`).
- Symptoms → actions: high `runtime.mallocgc`/`gcBgMarkWorker` CPU → reduce
  allocations (§3) before touching knobs; OOMKilled pods → GOMEMLIMIT;
  RSS far below limit with GC CPU high → raise GOGC.
- Ballast hacks are obsolete post-GOMEMLIMIT — audit and remove (LOW).

## 6. PGO builds

Profile-guided optimization (default-on since 1.21 when a profile is present):
put a representative CPU profile at `default.pgo` in the main package
directory; `go build` picks it up automatically.

```bash
curl -so cpu.pprof 'http://prod-host:6060/debug/pprof/profile?seconds=60'  # peak traffic
mv cpu.pprof cmd/api/default.pgo
go build ./cmd/api          # check logs: PGO enables extra inlining/devirtualization
```

- Typical win 2–8% CPU; free once automated. SOTA setup: CI job refreshes
  `default.pgo` weekly from continuous-profiling data; stale profiles degrade
  gracefully (no correctness risk).
- Verify it's active: `go build -pgo=auto -x` or check
  `go version -m binary` for the `-pgo` setting.

## 7. Production performance signals

Profiles answer "where"; metrics answer "when/whether". Export from
`runtime/metrics` (or via the OTel/Prometheus runtime collectors):

- `/gc/heap/allocs:bytes` rate — allocation pressure trend; pair with
  `/cpu/classes/gc/total:cpu-seconds` (GC CPU share; >10–15% sustained means
  go to §3).
- `/sched/latencies:seconds` — scheduler delay histogram; rising tail with
  idle CPU points at goroutine floods or syscall stalls (`go tool trace`).
- `/memory/classes/heap/live:bytes` vs container limit — headroom for
  GOMEMLIMIT decisions; `/gc/limiter/last-enabled:gc-cycle` flags memlimit
  death-spiral mode.
- `runtime.NumGoroutine()` as a gauge — monotonic growth is a leak
  (`rules/03 §2`), not a perf tuning problem.

Alert on trends, not absolutes; baseline per service. Capture a CPU+heap
profile automatically when alerts fire (flight recorder / continuous
profiler) so the incident carries its own evidence.

## 8. Hot-path checklist (apply only where profiles point)

- Bounds-check elimination: iterate with `for i := range s` / `for _, v`;
  hoist `_ = s[n-1]` hints rarely needed post-1.21.
- Avoid defer in ultra-hot tiny functions pre-1.14 lore is obsolete — defer
  is ~1ns now; keep defers, drop the superstition (flag stale "defer is slow"
  comments as INFO).
- Map with `int` keys beats `string` keys; consider sharded maps under
  write contention before `sync.Map`.
- Sort with `slices.SortFunc` (no interface boxing) over `sort.Slice`.
- JSON dominating? `json.NewDecoder`/`Encoder` streaming, smaller structs,
  `encoding/json/v2` (1.26: behind `GOEXPERIMENT=jsonv2`; since 1.27 available by
  default, with `encoding/json` itself backed by v2 — opt out with
  `GOEXPERIMENT=nojsonv2`) or a faster codec — measure.

## Audit checklist

- [ ] **Profiling wired up? (absence in a latency-sensitive service = LOW gap)** —
      `grep -rn 'net/http/pprof' --include='*.go' .` ;
      `grep -rn 'pprof' --include='*.go' . | grep -i 'listen\|mux\|handle'` (exposed publicly? —
      MEDIUM)
- [ ] **Benchmarks exist for hot packages; b.Loop adoption** —
      `grep -rln 'func Benchmark' --include='*_test.go' .` ;
      `grep -rn 'b.N' --include='*_test.go' .` (candidates to migrate to b.Loop (1.24+));
      `grep -rn 'ReportAllocs' --include='*_test.go' .`
- [ ] **Growth-by-append without prealloc near loops (then check if size was knowable)** —
      `grep -rnE 'var \w+ \[\]' --include='*.go' . | head -50` ;
      `golangci-lint run --enable-only prealloc,perfsprint,makezero ./...`
- [ ] **String concat in loops — O(n²)** —
      `grep -rn -B3 '+= ' --include='*.go' . | grep -E 'for |range' | grep -i 'str\|msg\|out'`
- [ ] **fmt on hot paths (handler/loop proximity — manual confirm)** —
      `grep -rnE 'fmt\.Sprintf' --include='*.go' . | wc -l`
- [ ] **sync.Pool correctness: Reset on reuse? cap check? aliasing?** —
      `grep -rn -A5 'sync.Pool' --include='*.go' .`
- [ ] **io.ReadAll on large/unbounded inputs — MEDIUM** —
      `grep -rn 'io.ReadAll\|ioutil.ReadAll' --include='*.go' .`
- [ ] **GC knobs & ballast** —
      `grep -rn 'GOGC\|GOMEMLIMIT\|SetMemoryLimit\|SetGCPercent' -r . --include='*.go' --include='*.yaml' --include='Dockerfile*'`
      ; `grep -rn 'ballast' --include='*.go' .` (obsolete pattern — LOW)
- [ ] **PGO** —
      `ls cmd/*/default.pgo 2>/dev/null; grep -rn 'pgo' Makefile* .github/ 2>/dev/null`
- [ ] **Escape analysis spot-check on hot package** —
      `go build -gcflags='-m' ./internal/hotpkg 2>&1 | grep 'escapes to heap' | head -30`

Severity guide: pool aliasing/missing reset HIGH (corruption); unbounded
ReadAll MEDIUM; missing prealloc/Builder on measured hot path LOW–MEDIUM;
publicly exposed pprof MEDIUM; cargo-cult optimizations without benchmarks
LOW.