# 06 — Performance & runtime: OPcache, FPM, JIT, profiling

PHP performance is mostly *runtime configuration and I/O shape*, not
micro-optimization: OPcache on, FPM sized to memory, queries not multiplied by
loops. Measure before optimizing; a profile is the entry ticket for any
optimization PR.

## 1. OPcache: non-negotiable in production

Without OPcache every request re-lexes and re-compiles every file. Verified
against php.net OPcache configuration docs (2026-07):

```ini
opcache.enable = 1
opcache.memory_consumption = 256      ; default 128 MB — size to the codebase,
                                      ; interned strings come out of this total
opcache.max_accelerated_files = 20000 ; > count of .php files (vendor included)
opcache.validate_timestamps = 0       ; immutable deploys: never stat files
opcache.interned_strings_buffer = 16
```

- `validate_timestamps=0` requires an OPcache reset on deploy — restart FPM or
  atomic-symlink switch with new realpaths. If deploys overwrite files in
  place, keep timestamps on (`revalidate_freq` low) or serve stale code.
- Monitor `opcache_get_status()`: cache full, `oom_restarts`, low hit rate are
  silent performance cliffs; alert on them.
- CLI workers: `opcache.enable_cli=1` only pays off for long-running processes.

## 2. Preloading (7.4+)

`opcache.preload=/srv/app/preload.php` compiles chosen files once at FPM
startup, linked into every worker — removing per-request autoload/compile for
the hot core (php.net opcache.preload).

- Preload the stable hot path (framework kernel, core domain classes), not all
  of `vendor/` — preloaded code is held **until server restart**; changing it
  requires an FPM restart, and it's shared across all pools of the process
  (php.net warns against preloading in shared/multi-tenant setups).
- Not supported on Windows (php.net).
- Measure: preloading typically buys a few percent on framework-heavy stacks —
  worth it at scale, not worth operational complexity for small apps.

## 3. JIT: reality check

Verified against php.net OPcache configuration docs (2026-07): as of PHP 8.4
the defaults are `opcache.jit=disable` with `opcache.jit_buffer_size=64M`
reserved — i.e. JIT ships **off**; enabling is a deliberate act
(`opcache.jit=tracing`, the recommended mode).

- **Typical web workloads are I/O-bound** (DB, cache, HTTP): JIT cannot
  optimize waiting, and published benchmarks of framework request paths show
  small single-digit gains at best. Don't expect throughput wins from flipping
  it on.
- JIT shines on CPU-bound PHP: numeric loops, image/data processing,
  long-running CLI workers with typed hot functions.
- If enabled: benchmark your actual workload before/after, watch memory
  (buffer is shared memory), and re-test after PHP upgrades — JIT bugs
  historically surface as heisencrashes. Debuggers/profilers may need JIT off.
- AUDIT: `opcache.jit` enabled with no benchmark justification is INFO;
  claiming "JIT will fix it" for an I/O-bound app is a wrong-tool finding.

## 4. PHP-FPM sizing and hygiene

FPM concurrency is the worker count — the classic failure is `pm.max_children`
set by folklore, either OOM-killing the box or queueing requests while RAM
sits idle.

```ini
pm = static                       ; dedicated app servers; dynamic/ondemand for
                                  ; shared or spiky/low-traffic hosts
pm.max_children = 40              ; = (RAM budget for PHP) / (avg worker RSS)
pm.max_requests = 1000            ; recycle workers to cap leak accumulation
pm.status_path = /fpm-status      ; scrape it: active/idle, listen queue
request_slowlog_timeout = 5s      ; slowlog with stack traces of slow requests
slowlog = /var/log/php-fpm/slow.log
```

- Measure average worker RSS under real traffic (`ps` on pool workers), leave
  headroom for OPcache shared memory + everything else on the host.
- `listen.backlog` and the status page's `listen queue` reveal saturation
  before users do; alert on queue > 0 sustained.
- One pool per app, distinct user per pool (also a security boundary,
  `rules/04` §5).
- **Session locking:** file-backed sessions serialize concurrent requests per
  user; call `session_write_close()` as soon as writes are done, or use a
  store with proper locking semantics.
- Long-running CLI/queue workers: recycle on a request/memory budget
  (`--max-jobs`-style flags or supervisor restarts), reconnect DB on failure,
  and remember: no OPcache revalidation surprise, but also no automatic code
  reload after deploys — restart workers on every deploy.

## 5. Application-level: N+1, caching, autoloading

- **N+1 queries** dominate real PHP slowness. One query per loop iteration =
  finding. Fix with eager loading / joins (e.g. Eloquent `with()`, Doctrine
  `JOIN` fetch or `EXTRA_LAZY` deliberately). Detect: query logging in dev,
  a query-count assertion in tests for hot endpoints, APM span counts in prod.
  Index/schema depth → sota-databases.
- **Cache layers, by scope:** OPcache (bytecode) → APCu (per-host, in-memory,
  no network — great for config/feature flags) → Redis/Memcached (shared,
  neutral examples). Every cache entry gets a TTL and a stampede story
  (lock-or-stale) on hot keys.
- **Autoloader:** production runs `composer install --optimize-autoloader`
  (classmap generation); `--classmap-authoritative` when the deploy is truly
  immutable — skips filesystem checks for unknown classes
  (getcomposer.org autoloader optimization docs).
- `realpath_cache_size` (default 4M since 7.x) matters for large vendor trees
  on stat-heavy configs; with `validate_timestamps=0` it's mostly moot.
- Streams and generators (`yield`) for large datasets — `fetchAll()` on
  unbounded result sets and building giant arrays in memory are HIGH on
  memory-constrained workers; `->fetch()` loops / cursors / chunked processing
  instead.
- `usleep`/HTTP calls inside request loops, un-batched external API calls:
  same N+1 pathology, worse latency multiplier.

## 6. Profiling: measure, don't guess

- **Xdebug is a development tool**: step debugging and coverage. Its overhead
  (even in `develop`/profile modes) disqualifies it for production — never
  enabled there (also an information-exposure risk).
- **Production:** sampling profilers/APM designed for prod — e.g. Excimer
  (low-overhead sampling), Blackfire, Tideways, or OpenTelemetry
  auto-instrumentation as neutral examples. Continuous sampling beats one-off
  local benchmarks because it sees real data shapes.
- Workflow: profile → find the top exclusive-time frames → fix the biggest →
  re-profile. Optimizations without before/after numbers don't merge.
- Micro-benchmarks: PHP's timers (`hrtime(true)`) with warmup and OPcache on,
  or phpbench (neutral example); beware measuring the JIT/opcache cold path.

## Audit checklist

Run from repo root / against the runtime; verify each hit manually.

```bash
# OPcache posture — the single highest-leverage check
php -r 'var_export(function_exists("opcache_get_status") ? (opcache_get_status(false)["opcache_statistics"] ?? opcache_get_status(false)) : "OPCACHE MISSING");'
php -r 'foreach (["enable","memory_consumption","max_accelerated_files","validate_timestamps","preload","jit","jit_buffer_size"] as $k) echo "opcache.$k=", ini_get("opcache.$k"), PHP_EOL;'
# validate_timestamps=1 on immutable deploys = LOW perf debt; cache-full/oom_restarts>0 = MEDIUM

# FPM sizing
grep -rnE '^(pm|pm\.max_children|pm\.max_requests|request_slowlog_timeout)' /etc/php*/fpm/pool.d/ 2>/dev/null
# max_children default-ish (5) on a production box, or no slowlog = MEDIUM

# N+1 / query-in-loop heuristics — confirm by reading the loop
grep -rnE '(foreach|while)[^{]*\{[^}]*->(query|prepare|find|get)\(' --include='*.php' src/ | head
grep -rn 'fetchAll' --include='*.php' src/        # unbounded result sets?
grep -rnE '(curl_exec|file_get_contents\s*\(\s*.http)' --include='*.php' src/  # HTTP in loops?

# Autoloader optimization in the deploy path
grep -rn 'optimize-autoloader\|classmap-authoritative\|-o ' Dockerfile* deploy* .github/workflows/ 2>/dev/null

# Xdebug in production (HIGH if confirmed on prod hosts)
php -m | grep -i xdebug

# Session lock hygiene on slow endpoints
grep -rn 'session_write_close' --include='*.php' src/

# Performance claims without measurements — check PR/commit rationale
git log --oneline --grep='perf\|optimi' -10
```

Severity guide: OPcache off in production HIGH (perf); Xdebug on production
HIGH; FPM sized by default/folklore causing OOM or queueing MEDIUM–HIGH;
confirmed N+1 on hot path MEDIUM; missing autoloader optimization LOW;
unmeasured optimization PRs INFO (process).
