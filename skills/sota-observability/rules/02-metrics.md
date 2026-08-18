# 02 — Metrics

Metrics are cheap, aggregated, alertable numbers. They answer "is it broken
and how badly" — traces and wide events answer "why". Design them for
queries and alerts, not for completeness.

> **Backend-neutral.** Examples below use Prometheus/PromQL because it is the
> de-facto exposition format and query language. Everything here applies
> unchanged to any Prometheus-compatible backend — **VictoriaMetrics**
> (MetricsQL is a PromQL superset), Mimir, Thanos, Cortex — and OTLP-native
> pipelines. The rules are about metric *design* (RED/USE, cardinality,
> histograms, exemplars), not the vendor.

## 1. RED and USE: the two starting templates

**RED** — for every request-driven service/endpoint:
- **Rate**: requests/sec (`http_requests_total` counter)
- **Errors**: failed requests/sec (same counter, `status` label, or
  separate; define "error" = 5xx + timeouts, not 4xx)
- **Duration**: latency distribution (histogram, never a gauge or average)

**USE** — for every resource (CPU, memory, disk, connection pool, queue,
thread pool, semaphore):
- **Utilization**: fraction of capacity in use (pool connections busy / max)
- **Saturation**: queued/waiting work (waiters on the pool, queue depth/lag)
- **Errors**: resource-level failures (connection timeouts, OOM kills)

Rules:
- Every service exposes RED per route before any bespoke metric. Most
  platforms get this free from OTel/middleware instrumentation — verify it's
  on, don't reimplement.
- Every bounded resource you own (DB pool, worker pool, internal queue)
  exposes USE. The classic 3am mystery — "service slow, CPU idle" — is a
  saturated connection pool with no saturation metric.
- Queue consumers: RED becomes consume rate / failure rate / processing
  duration, plus **lag/age of oldest message** (the consumer's real SLI).
- Business metrics on top: `orders_completed_total`, `payments_failed_total`
  — these feed the SLOs users actually care about.

## 2. Instrument semantics: counter vs gauge vs histogram

| Instrument | Use for | Query pattern | Never |
|------------|---------|---------------|-------|
| Counter | Monotonic event counts (requests, errors, bytes, retries) | `rate()`, `increase()` | never decrement; never store a value that can go down |
| Gauge | Current level of something measurable now (queue depth, pool in-use, temperature, config value) | last value, `avg/max_over_time` | never for event counts (loses events between scrapes); never for latency |
| Histogram | Distributions (latency, payload size, batch size) | `histogram_quantile()` over summed buckets | — |
| Summary (client-side quantiles) | Almost never | — | cannot be aggregated across instances; prefer histograms |

**Bad:**

```python
LATENCY = Gauge("request_latency_seconds")     # last write wins; lies under load
LATENCY.set(elapsed)

ERRORS = Gauge("errors")                        # scrape misses bursts
ERRORS.set(error_count_this_minute)
```

**Good:**

```python
LATENCY = Histogram("http_request_duration_seconds",
    buckets=(.005,.01,.025,.05,.1,.25,.5,1,2.5,5,10))
LATENCY.observe(elapsed)

ERRORS = Counter("http_requests_errors_total")
ERRORS.inc()
```

Rules:
- Counters end in `_total`; include the unit in the name (`_seconds`,
  `_bytes`); base units (seconds not ms) per Prometheus convention.
- Gauges for derived "current state" should be callbacks/observable gauges
  (sample on scrape), not values you remember to set.
- Counter resets (restarts) are handled by `rate()` — never compute deltas
  by hand from raw counter values.
- Don't emit a metric and a log line as the same signal twice on hot paths
  by hand — derive metrics from spans/wide events where the pipeline
  supports it (spanmetrics), or instrument once in middleware.

## 3. Label cardinality discipline

Each unique label combination is a separate time series held in memory by
the TSDB. Cardinality explosions are the #1 way teams take down their own
monitoring — during the incident they need it.

**Forbidden as label values:** user IDs, emails, session/request/trace IDs,
raw URLs/paths (use the route template), free-text error messages, IPs,
container IDs you don't aggregate by, anything user-controlled.

**Bad:**

```python
REQS.labels(user_id=user.id, path=request.path, error=str(exc)).inc()
# /api/users/8231, /api/users/8232 ... × users × error strings = millions of series
```

**Good:**

```python
REQS.labels(
    route="/api/users/{id}",        # template, bounded by route table
    method="GET",
    status_class="5xx",             # or exact code: bounded set
    error_type=type(exc).__name__,  # bounded by exception classes
).inc()
```

Rules:
- Budget: know each label's value-set size; total series per metric =
  product of label cardinalities × instances. Keep per-metric series in the
  hundreds/low thousands, not millions.
- High-cardinality questions ("which user?", "which exact URL?") belong in
  traces and wide events — that's the division of labor. Metrics say *that*
  p99 spiked on route X; the exemplar-linked trace says *who and why*.
- Normalize at the edge: route templates from the router, error types from
  exception classes, status classes. Add a relabeling/drop rule in the
  pipeline as a backstop against accidental unbounded labels.
- Watch `prometheus_tsdb_head_series` (or vendor cardinality reports) and
  alert on sudden series growth — that alert is cheaper than the outage.
- Unbounded label sets are also a DoS vector when user input can mint
  series. Treat label values as untrusted input.

## 4. Percentiles done right

Averages hide everything that matters; percentiles computed wrong are worse
because they look authoritative.

Rules:
- **Never average percentiles.** `avg(p99 per instance)` is mathematically
  meaningless. Aggregate histogram buckets across instances FIRST, then
  compute the quantile:

```promql
# Bad: average of per-pod p99s
avg(histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])))

# Good: sum buckets across pods, then quantile
histogram_quantile(0.99,
  sum by (le, route) (rate(http_request_duration_seconds_bucket[5m])))
```

- Choose buckets around your SLO thresholds: quantile accuracy is bounded by
  bucket boundaries. If the SLO is 300ms, you need boundaries at/near 300ms
  (e.g. .25 and .3 and .4), or the reported p99 can be off by the whole
  bucket width. Default buckets are rarely right — set them per metric.
- Prefer **native/exponential histograms** (Prometheus native histograms,
  OTel exponential histograms) where the stack supports them: automatic
  bucketing, better accuracy, cheaper series. Note: Prometheus native
  histograms are **stable since v3.8.0 (Nov 2025)** — enable ingestion via the
  `scrape_native_histograms: true` config (the old
  `--enable-feature=native-histograms` flag is now a no-op). Still verify your
  whole pipeline (remote write 2.0 — itself still experimental — and dashboards)
  handles them before switching SLI queries.
- SLO arithmetic trick: a bucket boundary exactly at the SLO threshold lets
  you compute "fraction of requests under 300ms" exactly:
  `sum(rate(..._bucket{le="0.3"}[5m])) / sum(rate(..._count[5m]))` — this is
  your latency SLI, more robust than thresholding a quantile estimate.
- Report p50/p95/p99, not the average; keep max/p99.9 visible for tail
  debugging. Track tail latency per dependency, not just at the edge.

### 4a. `now` vs `offset X` is two samples, not a trend

And it convinces *more* than a single sample, which is exactly what makes it
dangerous: a before/after pair looks like a measurement. Neither point carries an
error bar, and a bursty series will hand you whatever ratio the two landing spots
imply.

Measured (2026-08-18). After a fix that bounded a set of unbounded aggregate
queries, a write-latency p99 read **0.40 s now** against **8.83 s at `offset
24h`** — a tidy 22x improvement, ready to report. Sampling the same metric at
hourly offsets across the same day:

```
-0h 0.40 | -2h 11.59 | -4h 10.49 | -6h 9.54 | -9h 0.11 | -12h 13.40 | -18h 4.38 | -24h 8.97
```

The series swings **0.11–13.40 s**. "Now" had landed in a trough and "24 h ago" on
a peak. Across that spread the same pair of reads could have shown anything from a
**122x improvement** to a **122x regression** (13.40 / 0.11), depending only on
where the two points landed. The load-invariant signal over the same windows — the **absolute
rate** of queries slower than the threshold, which a change in total query volume
cannot move — was flat, i.e. nothing had changed. The fix was real and useful; the
22x was an artefact of two points.

Rules:
- Before quoting any before/after from production telemetry, **sample the
  intervening window**. Two points cannot distinguish a step change from a
  diurnal swing, and the diurnal swing is the common case.
- When the question is "is this still happening", prefer a **load-invariant
  absolute count** to a percentile. A percentile is a **ratio**: a traffic-mix
  shift, a retry storm, or a batch job ending moves it without anything
  improving, because the denominator moved.
- This is not the "many samples, report variance" of a benchmark
  (`sota-performance` rules/01 §3). A production series **cannot be re-run**, so
  sampling more *offsets* of the same series is the only equivalent available —
  and a deploy marker on the chart is worth more than either number.

## 5. Exemplars: metrics → traces in one click

An exemplar attaches a sampled trace_id to a histogram bucket observation.
The on-call workflow becomes: see p99 spike on the dashboard → click the
exemplar dot → land in the exact slow trace. Without exemplars, the path
from "metric anomaly" to "specific request" is manual time-window
spelunking.

```yaml
# OTel SDK: exemplars on by default when a span is active (trace-based filter).
# Prometheus server: enable storage
#   --enable-feature=exemplar-storage
# Scrape with OpenMetrics so exemplars survive:
#   honor exemplars via application/openmetrics-text
```

```text
http_request_duration_seconds_bucket{le="0.5",route="/checkout"} 1027 \
  # {trace_id="4bf92f3577b34da6a3ce929d0e0e4736"} 0.43 1718160847.12
```

Rules:
- Record observations inside an active span so the SDK attaches the exemplar
  automatically; verify the whole chain (SDK → exposition format → scrape →
  Grafana datasource "exemplars: on") because any broken link silently drops
  them.
- Exemplars matter most on error counters and latency histograms — the two
  things you alert on.
- If the stack can't do exemplars, get the same effect by deriving metrics
  from traces (Collector `spanmetrics` connector) so trace search by
  route+duration substitutes for the click-through.

## 6. OTel metrics specifics

When instrumenting via the OpenTelemetry metrics API (preferred for new
code — one API, exporters decide Prometheus vs OTLP):

```go
meter := otel.Meter("checkout")
reqDur, _ := meter.Float64Histogram("http.server.request.duration",
    metric.WithUnit("s"),
    metric.WithExplicitBucketBoundaries(.005,.01,.025,.05,.1,.25,.3,.5,1,2.5))
poolInUse, _ := meter.Int64ObservableGauge("db.client.connections.usage",
    metric.WithInt64Callback(func(_ context.Context, o metric.Int64Observer) error {
        o.Observe(int64(pool.InUse()), metric.WithAttributes(attribute.String("state","used")))
        return nil
    }))
reqDur.Record(ctx, elapsed.Seconds(),
    metric.WithAttributes(semconv.HTTPRoute("/checkout"),
                          semconv.HTTPResponseStatusCode(code)))
```

Rules:
- Use semantic-convention instrument names (`http.server.request.duration`
  in seconds) — backends and dashboards key on them; don't reinvent
  `my_request_time_ms`. Prometheus 3.x ingests OTLP natively and accepts
  UTF-8 metric/label names, so dotted semconv names no longer have to be
  mangled to underscores — pick one naming scheme end-to-end and stop
  maintaining translation rules.
- **Aggregation temporality**: Prometheus needs cumulative; some vendors
  want delta. Set it in the exporter, never assume — delta counters scraped
  as cumulative silently report garbage rates.
- Prefer observable (callback) instruments for state you'd otherwise poll;
  prefer synchronous instruments inside request flow (they're what exemplars
  attach to).
- Views (SDK-level) are the escape hatch to fix cardinality/buckets of
  third-party instrumentation without forking it: drop attributes, re-bucket,
  rename — at the app edge or in the Collector.
- UpDownCounter vs Gauge: use UpDownCounter for additive quantities summed
  across instances (active requests fleet-wide); Gauge for non-additive
  readings (queue depth measured by each consumer — summing it double-counts).

## 7. Operational hygiene

- Pre-register metrics at startup (zero-valued where applicable) so
  `absent()`-style alerts and rate() have a baseline; a metric that appears
  only on first error breaks "no data" vs "no errors" disambiguation.
- Every metric a dashboard or alert references must exist in code review:
  delete metrics nothing queries (they cost memory and attention), and grep
  dashboards/alerts before renaming a metric — renames are breaking changes.
- Standard resource attributes on every series: `service.name`,
  `service.version`, `deployment.environment` — version is what turns "p99
  rose at 14:02" into "the 14:00 deploy did it".
- Instrument the telemetry itself: scrape failures, exporter queue drops,
  remote-write errors. Silent telemetry loss looks identical to "all good".

## Audit checklist

- [ ] RED metrics exist per service and per route (rate, errors with a
      defined error definition, duration as histogram).
- [ ] USE metrics exist for every owned bounded resource: DB/HTTP connection
      pools, worker pools, internal queues (utilization AND saturation).
- [ ] Queue consumers expose lag/oldest-message-age.
- [ ] No gauges used for latency or event counts; counters are `_total`,
      units in names, base units.
- [ ] Grep label usage: no user IDs, raw paths/URLs, error strings, or other
      unbounded values as labels; route templates used; series counts per
      metric known and bounded; cardinality-growth alert exists.
- [ ] No dashboard or alert averages percentiles; quantiles computed from
      bucket sums across instances; summaries not aggregated.
- [ ] Histogram buckets chosen around SLO thresholds (or native/exponential
      histograms in use); latency SLI computed from a bucket boundary.
- [ ] Exemplars flow end-to-end (SDK → exposition → TSDB → dashboard), or
      spanmetrics provides the metric↔trace bridge.
- [ ] `service.version` and environment present on all series; deploys are
      correlatable with metric shifts.
- [ ] Does any before/after claim from production telemetry rest on exactly two
      points (`now` vs `offset X`)? The intervening window must be sampled, and
      "is it still happening" answered with a load-invariant absolute count
      rather than a percentile, whose denominator moves on its own (§4a).
- [ ] Metrics pipeline self-monitored (scrape/export failures alerted);
      unused metrics pruned.
