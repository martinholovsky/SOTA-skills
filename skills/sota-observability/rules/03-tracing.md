# 03 — Distributed Tracing (OpenTelemetry)

Tracing answers "where did this request spend its time, and which hop
failed" across service boundaries. OpenTelemetry is the standard; vendor
tracing SDKs in application code are technical debt as of 2026.

## 1. OTel architecture: API vs SDK separation

- **Libraries and shared code depend ONLY on the OTel API**
  (`opentelemetry-api`, `@opentelemetry/api`, `go.opentelemetry.io/otel`).
  The API is no-op without an SDK, so libraries instrument unconditionally
  with zero cost to non-adopters.
- **Applications configure the SDK once at the entry point**: tracer
  provider, resource attributes, sampler, exporter (OTLP). Nothing else in
  the codebase imports SDK packages.
- **Export OTLP to a Collector**, not directly to a vendor: the Collector
  owns batching, retries, tail sampling, redaction, fan-out, and vendor
  routing. Swapping backends becomes a Collector config change, not a code
  change.

```python
# Library code — API only:
from opentelemetry import trace
tracer = trace.get_tracer("payments-lib", "1.4.0")

# main.py — the ONLY place SDK appears:
provider = TracerProvider(
    resource=Resource.create({
        "service.name": "checkout", "service.version": VERSION,
        "deployment.environment": ENV}),
    sampler=ParentBased(TraceIdRatioBased(0.1)),
)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)
```

Rules:
- Start with auto-instrumentation (HTTP frameworks, DB drivers, HTTP/gRPC
  clients, queue clients) — it covers 80% with correct semantic conventions.
  Add manual spans only for business logic the auto layer can't see.
- **Follow OTel semantic conventions** for span names and attributes
  (`http.request.method`, `db.system`, `messaging.operation`,
  `error.type`). Invented names break backend UIs, spanmetrics, and every
  query anyone else writes. HTTP and database conventions are now stable
  (messaging is still in development); when upgrading instrumentation that
  predates stabilization, migrate via `OTEL_SEMCONV_STABILITY_OPT_IN`
  rather than breaking dashboards in one jump.
- `service.name`, `service.version`, `deployment.environment` set as
  resource attributes always — they are the join keys to metrics and logs.

## 2. Span design: what deserves a span

A span = a meaningful unit of work whose duration and failure you'd want to
see in a waterfall. Span-per-function is noise; span-per-service is blind.

**Gets a span:** inbound request handling (server span); every outbound
network call — HTTP, DB query, cache op, queue publish (client/producer
span); message consume + processing (consumer span); expensive internal
phases (render, batch chunk, ML inference); each retry attempt (so retries
are visible as siblings).

**Does NOT get a span:** trivial pure functions, getters, per-item work in
large loops (span the batch, count the items), logging itself.

**Attributes vs events vs status:**
- **Attributes** = dimensions you'd filter/group by: route, db.system,
  tenant_id, cache.hit, retry.count. Set on the span, bounded-ish values,
  no payloads, no PII (same redaction policy as logs — rules/01 §4).
- **Events** = point-in-time happenings inside the span: `retry_scheduled`,
  `lock_acquired`, and especially **exception events**
  (`span.record_exception(e)`). Note OTel deprecated the Span Event API
  (`AddEvent`/`RecordException`) in 2026: the end-state is events and
  exceptions emitted as span-correlated **logs** via the Logs API.
  `record_exception` stays the acceptable default during the transition;
  migrate instrumentation via `OTEL_SEMCONV_EXCEPTION_SIGNAL_OPT_IN=logs`
  (or `logs/dup` to emit both), and SDK-level routing can surface log-based
  events as span events for backends that need them. Exceptions-as-logs
  matches rules/01 §1 (`exception.stacktrace` as a structured field).
- **Status**: set `ERROR` only for genuine failures of that unit of work.
  A 404 on a lookup endpoint is not span-error; an unhandled exception is.
  Marking expected outcomes as errors poisons tail sampling and spanmetrics.

```python
# Good: one span per outbound call, rich attributes, honest status
with tracer.start_as_current_span(
    "charge_card", kind=SpanKind.CLIENT,
    attributes={"payment.provider": "stripe", "amount_usd": total,
                "retry.max": 3}) as span:
    try:
        resp = stripe.charge(...)
        span.set_attribute("payment.id", resp.id)
    except StripeTimeout as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, "provider timeout"))
        raise
```

```python
# Bad
with tracer.start_as_current_span("process"):          # name says nothing
    for item in items:                                   # 50k spans per request
        with tracer.start_as_current_span(f"item-{item.id}"):  # high-card name
            ...
```

Rules:
- Span names are low-cardinality templates: `GET /users/{id}`,
  `SELECT orders` — never interpolated IDs/URLs (breaks grouping and
  spanmetrics cardinality).
- Always end spans — `with`/`defer`/`try-finally`. A leaked span orphans its
  whole subtree.
- Record the queue/pool wait time as either a separate span or an attribute;
  "slow handler" that is really "waited 2s for a connection" is the classic
  misdiagnosis tracing exists to prevent.

## 3. Context propagation: W3C traceparent everywhere

One dropped hop splits the trace and you're back to timestamp archaeology.

- **HTTP/gRPC**: W3C Trace Context (`traceparent`, `tracestate`) is the
  standard. Auto-instrumented clients/servers handle it; verify any
  hand-rolled HTTP client injects it, and configure the B3↔W3C composite
  propagator only where legacy systems require it.
- **Queues/streams (the usual gap)**: inject context into message
  headers/attributes at publish; extract at consume and start the consumer
  span with the extracted context as **link or parent**:

```python
# Producer
carrier = {}
propagate.inject(carrier)
channel.basic_publish(..., properties=BasicProperties(headers=carrier))

# Consumer
ctx = propagate.extract(message.headers)
with tracer.start_as_current_span("orders process", context=ctx,
                                  kind=SpanKind.CONSUMER):
    ...
```

  For batch consumers, use **span links** to all source messages rather than
  picking one parent. For long-delay queues, prefer a new trace linked to
  the producer trace over a single week-long trace.
- **Background jobs / cron / fan-out**: thread pools and task queues
  (Celery, Sidekiq, asyncio tasks) must capture context at submit time and
  restore at execution (`contextvars` copy, `context.with_current()`,
  framework instrumentation). A scheduled job starts a fresh root span —
  give it a real name and the standard resource attributes.
- **Trust boundary**: at the public edge, decide policy — typically accept
  incoming `traceparent` for continuity but never trust sampling flags from
  the internet blindly; strip/regenerate at the edge proxy if traces could
  be forced-sampled by clients.
- Audit test: one user action that crosses HTTP → queue → worker → DB must
  appear as ONE trace (or explicitly linked traces). If you see N
  single-service traces for one action, propagation is broken at a hop.

## 4. Sampling: head vs tail

100% tracing at scale is unaffordable; naive sampling discards exactly the
traces you need (errors, tail latency). Decide deliberately.

| Strategy | How | Pros | Cons |
|----------|-----|------|------|
| Head (TraceIdRatioBased + ParentBased) | Decide at root, propagate decision | Cheap, simple, consistent per-trace | Blind: drops 99% of errors/slow traces at 1% rate |
| Tail (Collector `tailsamplingprocessor`) | Buffer whole trace, decide on completion | Keep 100% of errors + slow + rare routes, sample boring successes | Collector memory/state; needs all spans of a trace at one collector instance (load-balancing exporter by trace_id) |

Recommended composite policy (tail, in the Collector):

```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors        # keep all failed traces
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: slow          # keep all traces over SLO threshold
        type: latency
        latency: {threshold_ms: 300}
      - name: baseline      # 5% of everything else
        type: probabilistic
        probabilistic: {sampling_percentage: 5}
```

Rules:
- Always `ParentBased` in SDKs so a trace is kept or dropped whole; mixed
  decisions produce broken partial traces.
- Pair head sampling at a moderate rate with tail sampling downstream
  (head controls SDK/network cost, tail controls storage and preserves
  signal). Pure 1% head sampling on a low-error service means you will have
  zero traces of the incident.
- Log the effective sampling config; during incidents, support a runtime
  knob to raise sampling on a specific route/tenant.
- Remember sampled-out requests still need their wide event (rules/01 §5) —
  logs are the unsampled record; traces are the deep-dive.

## 5. Limits, overhead, and pipeline hardening

Tracing must never take down the service it observes.

- **Span/attribute limits**: configure SDK limits (max attributes, events,
  links per span; max attribute length). A bug that attaches a 2MB response
  body or 10k events to a span should be truncated by config, not crash the
  exporter. Default limits exist — verify they're sane, don't raise them
  casually.
- **BatchSpanProcessor always** in production (never SimpleSpanProcessor —
  it exports synchronously on the request path). Size queue and export
  batches for peak; monitor the SDK's dropped-span counter: silent drops
  during the incident are when you needed traces most.
- Exporter failures must be non-blocking and bounded (timeout + queue, drop
  on overflow). Telemetry backpressure must never propagate into request
  latency.
- Collector deployment: at least an agent (daemonset/sidecar) + gateway
  pair for tail sampling; the gateway tier needs trace-ID-routed load
  balancing (`loadbalancingexporter`) so tail decisions see whole traces.
  The Collector itself exports its own metrics — alert on
  `otelcol_processor_dropped_spans` and exporter queue saturation.
- Redaction in the pipeline: a Collector `attributes`/`redaction` processor
  deny-listing token/PII-shaped attributes is the backstop for instrument-
  ation mistakes — same philosophy as logger-level redaction (rules/01 §4).
- Shutdown: flush the provider on SIGTERM (`provider.shutdown()` /
  `ForceFlush`) or you lose the last batch of every deploy — which is
  exactly the window where regressions live.

## 6. Baggage: handle with caution

Baggage propagates key-values alongside the trace context to all downstream
services — and into every outbound header.

- Use only for small, low-sensitivity routing/context values needed across
  services: `tenant.tier`, synthetic-test flag, experiment bucket.
- **Never** put PII, tokens, or anything large in baggage: it is forwarded
  to EVERY downstream hop — including third-party APIs your HTTP client
  calls with propagation enabled. That's a data-leak primitive.
- Baggage is not span attributes: receivers must explicitly read baggage and
  stamp it onto spans (Collector/SDK baggage-to-attribute processors) for it
  to appear in trace data.
- Cap count/size; treat inbound baggage at trust boundaries as untrusted
  input and strip it at the edge.

## Audit checklist

- [ ] Application code depends on OTel API only; SDK configured in exactly
      one place per service; exporters point at a Collector, not hardcoded
      vendors.
- [ ] Auto-instrumentation enabled for frameworks, DB, HTTP clients, queue
      clients; semantic conventions used for names/attributes.
- [ ] Every outbound network call (HTTP, DB, cache, queue) produces a span;
      retries visible; span names are low-cardinality templates.
- [ ] Span status ERROR only on real failures; exceptions recorded as span
      events or span-correlated logs (Span Event API deprecated 2026); no
      payloads/PII in attributes.
- [ ] Trace continuity verified end-to-end across HTTP → queue → worker →
      cron paths (one trace or linked traces per user action).
- [ ] Sampling is deliberate: documented policy; errors and slow traces are
      retained (tail sampling or equivalent); ParentBased everywhere;
      sampling rate adjustable during incidents.
- [ ] trace_id present in logs (cross-link works both ways: log→trace,
      trace→logs, metric exemplar→trace).
- [ ] Baggage usage reviewed: no PII/secrets, stripped or validated at trust
      boundaries, not leaking to third-party APIs.
- [ ] Collector pipeline monitored (dropped spans, queue saturation, export
      failures); tail-sampling memory sized for peak.
