<!-- last-verified: 2026-07 -->
# 05 — Concurrency & performance: GVL, jobs, JIT, GC, N+1

Ruby's concurrency story is shaped by the GVL; its performance story by the
GC, the allocator, and (increasingly) the JITs. Rules of engagement: know
which resource you're bound on, design jobs for at-least-once delivery, and
profile before optimizing.

## 1. The GVL and the concurrency decision table

CRuby's Global VM Lock lets **one thread execute Ruby code at a time per
process**; the GVL is released during blocking I/O and by many C extensions.
Consequences:

| Workload | Right tool |
|---|---|
| I/O-bound, moderate concurrency (HTTP calls, DB waits) | Threads (or a threaded server/job runner) |
| I/O-bound, very high concurrency | Fiber scheduler / event-driven (async gem as a neutral example) |
| CPU-bound | **Multiple processes** (forking server/job workers); Ractors only experimentally |
| Mixed web serving | Processes × threads (e.g. a forking+threaded server), sized per §6 |

- Threads still buy real parallelism for I/O — a GVL-bound app is *not* a
  reason to avoid threads for network-heavy work.
- CPU-heavy request paths don't get faster with more threads — they get
  slower (GVL contention + context switching). Move the work to more
  processes or out of band.

## 2. Thread correctness

- **Any mutable state reachable from two threads needs a lock** (`Mutex`) or
  a concurrency-safe structure (`Queue`/`SizedQueue`; the
  concurrent-ruby gem's `Concurrent::Map`/atomics as neutral examples).
  Core `Hash`/`Array` are not thread-safe for concurrent mutation; "it's
  fine because of the GVL" is not a guarantee — context switches happen
  between bytecodes.
- Lazy memoization (`@x ||= build`) is a benign-looking race under threads:
  compute may run twice and, worse, a *partially built* object may be
  visible. Initialize eagerly at boot, or guard with a `Mutex`.
- **`Timeout.timeout` is dangerous around anything with state** — it kills
  the block via an async exception raised at an arbitrary bytecode
  (mid-transaction, mid-cleanup). Prefer native timeouts: DB statement
  timeouts, HTTP client `open_timeout`/`read_timeout`, `IO.select`. Audit
  every `Timeout.timeout` wrapping DB/file/network state as MEDIUM+.
- Pools for shared clients: DB/Redis/HTTP connections come from a pool
  (`connection_pool` gem as a neutral example) sized ≥ thread count — a
  shared bare client across threads corrupts protocol state.
- **`Thread#[]`/`Thread#[]=` are fiber-local, not thread-local** — under a
  fiber scheduler or streaming server this "thread-local" silently resets;
  true thread-locals are `Thread#thread_variable_get/set`.
- Spawned threads: handle exceptions (a dead worker thread fails silently
  unless `abort_on_exception`/`report_on_exception` or a join checks it) and
  join on shutdown.

## 3. Fibers and Ractors

- **Fiber scheduler** (Ruby 3.0+): with a scheduler installed (async gem as
  the common neutral example), blocking I/O in fibers yields automatically —
  thousands of concurrent I/O waits per thread. Constraints: everything on
  the loop must actually be non-blocking (a C extension that holds the GVL
  blocks the whole loop); fiber-per-request servers (e.g. Falcon as a
  neutral example) need fiber-safe, not just thread-safe, libraries.
- **Ractors are still experimental as of Ruby 4.0** — the
  [4.0 release notes](https://www.ruby-lang.org/en/news/2025/12/25/ruby-4-0-0-released/)
  say the team "aim[s] to remove its experimental status next year". 4.0
  reworked communication: `Ractor::Port` replaces the **removed**
  `Ractor.yield`/`Ractor#take`. Rules: fine for isolated CPU-bound
  experiments (only shareable — deep-frozen — objects cross boundaries);
  don't build production hot paths on Ractors yet; audit any Ractor use on
  pre-4.0 code for the removed APIs before an upgrade.

## 4. Background jobs: at-least-once means idempotent

Queue backends (Sidekiq, SolidQueue, GoodJob, Resque as neutral examples)
deliver **at least once**: crashes and retries re-run jobs. Design contract:

- **Jobs are idempotent.** Techniques: natural idempotency (set-to-state,
  not increment), a uniqueness key checked/recorded in the DB
  (`INSERT ... ON CONFLICT DO NOTHING` on a dedup table), or state-machine
  guards (`return if order.shipped?`).
- **Arguments are IDs and primitives, never objects.** Serialized objects go
  stale, bloat the queue, and break on deploys that change the class. The
  job refetches; a missing record is usually a *discard*, not a retry.
- **Enqueue after commit.** Enqueuing inside a DB transaction races the
  worker against the commit (job runs, record not visible) and enqueues for
  rolled-back work. Use the framework's after-commit enqueueing or a
  transactional-outbox pattern; a DB-backed queue in the *same* database
  (SolidQueue/GoodJob style) makes enqueue naturally transactional.
- Retries: bounded with exponential backoff (the runner's default is fine);
  a dead-letter/discard queue that someone actually monitors; alert on queue
  depth and oldest-job age, not just failures.
- Timeouts: jobs get an execution budget enforced by the runner or by
  native timeouts inside the job — not `Timeout.timeout` (§2).
- Don't do slow work in the request cycle: anything > ~100ms and not needed
  for the response body belongs in a job.

## 5. YJIT and ZJIT

- **YJIT is the production JIT.** Mature since the 3.2/3.3 era; enable with
  `--yjit` / `RUBY_YJIT_ENABLE=1` / `RubyVM::YJIT.enable` (4.0 adds
  `mem_size:` and `call_threshold:` options to `enable` — see the
  [4.0 release notes](https://www.ruby-lang.org/en/news/2025/12/25/ruby-4-0-0-released/)).
  It speeds up CPU-bound *Ruby* execution (typical real-app gains are
  double-digit percent); it does not help I/O waits or C-extension time.
  Verify it's actually on in production (`RubyVM::YJIT.enabled?`) and give
  it headroom — JIT code costs extra memory per process.
- **ZJIT (new in 4.0) is experimental**: per the release notes it is "faster
  than the interpreter, but not yet as fast as YJIT" and the guidance is to
  "hold off on deploying it in production for now". Benchmark it in staging
  if curious; ship YJIT.
- Measure with the app's own workload (`benchmark-ips` for micro, production
  latency percentiles for real) — never adopt or tune a JIT on faith.

## 6. Memory, GC, allocator

- **Measure first**: `GC.stat` (heap pages, `major_gc_count`,
  `old_objects`), RSS per process over time, and an allocation profile
  (memory_profiler gem) before touching knobs.
- Most "Ruby memory leaks" are **glibc-malloc retention/fragmentation** in
  long-lived multithreaded processes, not Ruby-object leaks. First,
  cheap mitigation: **`MALLOC_ARENA_MAX=2`** (a platform default on some
  PaaSes — [Heroku changelog](https://devcenter.heroku.com/changelog-items/1683)).
- **jemalloc caveat (status changed):** the classic "just use jemalloc"
  advice needs re-checking — the upstream
  [jemalloc repo](https://github.com/jemalloc/jemalloc) was archived in
  June 2025 and its future maintenance path is unclear as of 2026-07 (needs
  verification at adoption time). Existing jemalloc deployments keep
  working; for *new* setups, start with `MALLOC_ARENA_MAX=2` and adopt an
  alternative allocator only with your own RSS benchmarks and a maintained
  package source.
- GC tuning (`RUBY_GC_HEAP_*`) is a last resort with before/after
  measurements committed next to the config; out-of-band GC between requests
  and periodic worker recycling (e.g. a worker-killer middleware as a
  neutral example) are legitimate operational tools for slow RSS growth.
- Sizing threaded/forking servers and workers: threads per process stay
  small for CPU-heavy apps (GVL, §1); total memory = workers × (base +
  JIT + heap growth) — leave allocator headroom before the container limit.
- Avoid allocation churn on hot paths: frozen literals (`rules/01` §2),
  `String#<<` over `+=`, precomputed constants over per-call construction.

## 7. N+1 queries and data-access performance

- **Detection beats vigilance**: run a detector in development/CI —
  bullet or prosopite (neutral examples) — and fail tests on new N+1s
  (`Prosopite.raise = true` style) rather than reviewing by eye.
- Fix with the ORM's eager loading: ActiveRecord
  `includes`/`preload`/`eager_load` (Sequel: `eager`); verify the fix by
  counting queries in a test, not by reading code.
- ActiveRecord `strict_loading` (6.1+) makes lazy loading raise — enable per
  model/association for hot paths so N+1s can't creep back.
- Select what you use on wide tables (`select(:id, :email)`/`pluck`);
  `find_each`/`in_batches` for large scans, never `Model.all.each`.
- Cache derived values with explicit invalidation rules; "cache it" without
  an invalidation story is a future correctness bug (see `sota-databases`
  for the deeper rules).

## 8. Profiling workflow

1. Reproduce with a realistic workload (production-like data volume).
2. Profile CPU with a sampling profiler — stackprof or vernier (neutral
   examples; vernier understands GVL/GC pauses) — or rack-mini-profiler
   per-request in development.
3. Allocation hotspots: memory_profiler / `GC.stat` deltas around the
   suspect region.
4. Fix the top item, re-measure, repeat. No optimization PR without
   before/after numbers in the description.

## Audit checklist

Run from repo root; verify each hit manually.

```bash
# Timeout.timeout around stateful work — MEDIUM+ (HIGH around transactions)
grep -rn "Timeout.timeout\|Timeout::timeout" --include='*.rb' .

# Unsynchronized shared mutable state (class-level accumulators) — manual review
grep -rnE "@@\w+|class << self" --include='*.rb' app/ lib/ 2>/dev/null | head
grep -rnE "\|\|=" --include='*.rb' . | grep -viE "spec|test" | head   # memoization under threads?

# Fiber-local mistaken for thread-local
grep -rnE "Thread\.current\[" --include='*.rb' . | head

# Threads without exception handling / join (manual review)
grep -rn "Thread.new" --include='*.rb' . | grep -v join | head

# Ractor use — verify experimental caveats & removed APIs (Ractor.yield/#take gone in 4.0)
grep -rnE "Ractor\.(new|yield)|\.take\b" --include='*.rb' . | head

# Jobs: object args (GlobalID mitigates for AR models; raw objects = MEDIUM)
grep -rnE "perform_(async|later)\(" --include='*.rb' . | grep -vE "\(\s*[a-z_]*id|\(\s*\d|\(\s*\)" | head
# Enqueue inside transactions — race, MEDIUM+
grep -rn -B3 "perform_later\|perform_async" --include='*.rb' app/ lib/ 2>/dev/null | grep "transaction do" | head
# Idempotency signals absent (manual: look for guards/upserts in job bodies)
grep -rln "def perform" app/jobs/ 2>/dev/null | head

# JIT posture — INFO
grep -rn "yjit\|YJIT" Dockerfile* config/ Procfile* .github/ 2>/dev/null | head -3
grep -rn "zjit" Dockerfile* config/ 2>/dev/null | head -1   # experimental in prod = MEDIUM

# Allocator / memory posture — INFO
grep -rn "MALLOC_ARENA_MAX\|jemalloc" Dockerfile* config/ Procfile* 2>/dev/null | head -3

# N+1 guards present? absent detector = note it
grep -rn "bullet\|prosopite" Gemfile 2>/dev/null | head -2
grep -rn "strict_loading" --include='*.rb' app/ config/ 2>/dev/null | head -2
grep -rnE "\.all\.each\b" --include='*.rb' . | head

# Unbounded scans
grep -rnE "\.(map|each)\b" --include='*.rb' app/ 2>/dev/null | grep -vE "find_each|in_batches" | grep -E "\.(all|where\([^)]*\))\." | head
```

Severity guide: non-idempotent retried job with side effects (payments,
emails) HIGH; enqueue-in-transaction, `Timeout.timeout` around transactions,
shared client without a pool MEDIUM–HIGH; Ractors or ZJIT on a production hot
path MEDIUM; YJIT off, no N+1 detector INFO/LOW.
