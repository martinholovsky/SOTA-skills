# 01 — Structured Logging

Logs exist to answer questions during incidents. Every rule here optimizes
for one reader: an on-call engineer with a trace ID and 5 minutes.

## 1. Emit JSON, one event per line

Machine-parseable structure is non-negotiable. String interpolation destroys
queryability; you cannot `WHERE user_plan = 'enterprise'` on prose.

**Bad:**

```python
logger.info(f"User {user.id} checked out cart {cart.id} for ${total} in {ms}ms")
```

**Good:**

```python
logger.info("checkout_completed",
    user_id=user.id, cart_id=cart.id,
    amount_usd=total, duration_ms=ms)
```

Rules:
- Static, snake_case event name as the message; everything variable goes in
  fields. The message is a grep key, not a sentence.
- Consistent field names across the codebase: `duration_ms` everywhere, never
  a mix of `elapsed`, `time_taken`, `latency`. Maintain a field dictionary;
  prefer OTel semantic convention names (`http.response.status_code`,
  `db.system`) where they exist.
- Typed values: `duration_ms: 142` (number), not `"142ms"` (string). Units in
  the field name, not the value.
- Timestamps in UTC ISO-8601 or epoch nanos, emitted by the logger, never
  hand-formatted.
- Multi-line payloads (stack traces) belong in a single JSON field
  (`exception.stacktrace`), never as raw multi-line output that shreds into
  N orphan lines in the aggregator.

## 2. Levels: ERROR means a human must act

Level discipline is the upstream of alert discipline. If ERROR is noisy,
error-rate alerts are noise, and on-call learns to ignore both.

| Level | Contract | Examples |
|-------|----------|----------|
| FATAL | Process cannot continue; exits after logging | Config invalid at boot, can't bind port |
| ERROR | Unexpected failure; a human should investigate; counts toward error-rate SLIs | Unhandled exception, dependency hard-down after retries, data corruption detected |
| WARN | Degraded but self-handled; investigate if it trends | Retry succeeded, fallback used, deprecated API called, near a limit |
| INFO | Business-significant state change; the wide event lives here | Request completed, job finished, config reloaded |
| DEBUG | Developer detail; off or heavily sampled in prod | Cache decision, intermediate values |

**Bad** (expected events at ERROR — trains everyone to ignore ERROR):

```go
if errors.Is(err, sql.ErrNoRows) {
    log.Error("user not found", "user_id", id) // expected outcome, not an error
}
log.Error("retrying request, attempt 2/5")     // handled; WARN at most
log.Error("invalid input from client")          // client's bug → 4xx, INFO/WARN
```

**Good:** client errors (4xx) are INFO/WARN with the status in the wide
event; retries are WARN only on final failure being near; ERROR is reserved
for "this should never happen and someone must look."

Never log-and-rethrow at every layer — one exception must produce one ERROR
line (at the boundary that handles it), not five duplicates that quintuple
your error rate.

## 3. Correlation: trace_id in every line

A log line that cannot be joined to a request is gossip. Inject IDs from
context automatically — never pass them by hand.

```python
# Python: contextvars-based injection (structlog)
structlog.configure(processors=[
    structlog.contextvars.merge_contextvars,  # trace_id, request_id auto-attached
    ...,
    structlog.processors.JSONRenderer(),
])

# Middleware, once:
ctx = trace.get_current_span().get_span_context()
structlog.contextvars.bind_contextvars(
    trace_id=format(ctx.trace_id, "032x"),
    span_id=format(ctx.span_id, "016x"),
)
```

Rules:
- Use the active OpenTelemetry trace_id as the correlation ID. Do not invent
  a parallel `request_id` scheme if tracing exists; if you must keep a legacy
  request_id, log both.
- Propagate into async work: thread pools, queue consumers, cron-spawned
  tasks must restore context before logging (see rules/03 §4).
- Also bind stable dimensions once per request: `user_id` (if policy allows),
  `tenant_id`, `service.version`, `deployment.environment` — via logger
  context, not repeated at every call site.
- Audit test: pick any prod log line; you must be able to retrieve the full
  request trace and all sibling logs from it. If not, correlation is broken.

## 4. Redaction at the logger — secrets and PII never reach the sink

Call-site vigilance fails; the 200th engineer will log the request object.
Enforce centrally, fail closed.

**Bad:**

```js
logger.info('login attempt', { headers: req.headers });   // Authorization, cookies
logger.debug('user object', user);                        // email, address, hash
catch (e) { logger.error('payment failed', { request: e.config }); } // card data in axios config
```

**Good** (pino):

```js
const logger = pino({
  redact: {
    paths: ['*.password', '*.token', '*.authorization', '*.cookie',
            '*.ssn', '*.card_number', 'req.headers["x-api-key"]'],
    censor: '[REDACTED]',
  },
});
```

Rules:
- Layered defense: (1) typed serializers per domain object that emit an
  explicit allowlist of fields (`user → {id, plan}` only); (2) logger-level
  denylist for known key patterns (`password|token|secret|authorization|
  cookie|ssn|card`); (3) pipeline-level scanner (OTel Collector
  `transform`/`redaction` processor, or vendor DLP) as the last net.
- Never log: credentials, session tokens, API keys, full request/response
  bodies by default, `Authorization`/`Cookie` headers, PII beyond opaque IDs
  (email, name, address, IP where regulated), card/bank data (PCI scope
  contamination), encryption keys, signed URLs.
- Exceptions are caught objects too: exception messages and locals can embed
  connection strings and tokens. Scrub exception serializers as well.
- A secret found in logs is an incident: rotate the secret AND purge the log
  history; retention means the leak persists for the retention window.

## 5. Wide events: one canonical log line per unit of work

The single highest-leverage logging practice. Instead of 15 scattered
breadcrumb lines per request, emit ONE rich event at completion carrying
everything needed to characterize that request.

**"At completion" is doing real work in that sentence.** A line emitted mid-function
attests only that *that line ran* — not that its result survived the filter, early
return, exception path or reassignment that follows it. A count computed from a
collection the function later discards is still a computed count, and still false: one
real case logged `1 adjudicated` for weeks after the `return` beneath it stopped
including that collection. So **site a claim where the value is consumed**, derived from
what was actually returned or written: a producer may log its *intent*, only the
consumer can report the *effect*. Verify it by changing what the function returns and
reading the emitted line — for anything running unattended (cron, pipeline stage, agent
loop) the log is the **only witness**, so a log unchanged by that mutation is the
finding. Full class: `sota-code-security` rules/14 §1. Scattered lines force
join-by-timestamp archaeology; the wide event makes "show me slow checkouts
for enterprise tenants on v2.14" a single query.

```json
{
  "event": "http_request",
  "timestamp": "2026-06-12T03:14:07.121Z",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "http.request.method": "POST",
  "http.route": "/api/v2/checkout",
  "http.response.status_code": 502,
  "duration_ms": 4312,
  "outcome": "error",
  "error.type": "UpstreamTimeout",
  "user_id": "u_8a2f",
  "tenant_id": "t_acme",
  "tenant_plan": "enterprise",
  "cart_items": 7,
  "amount_usd": 1249.00,
  "payment_provider": "stripe",
  "retries.payment": 2,
  "cache.hit": false,
  "db.queries": 11,
  "db.total_ms": 220,
  "upstream.payment_ms": 4002,
  "feature_flags": ["checkout_v3"],
  "service.version": "2.14.1",
  "region": "eu-west-1"
}
```

Rules:
- Build the event incrementally: middleware creates a per-request accumulator
  at start; handlers and clients attach fields (`evt.set("cache.hit", true)`);
  middleware emits once in a `finally` — including on exceptions, where it
  must still fire with `outcome=error` and error fields.
- Include: identity (trace_id, route, method), outcome (status, error.type),
  timing breakdown (total + per-dependency ms), business context (tenant,
  plan, amounts, flags), infrastructure (version, region, instance).
- High dimensionality is the point — many fields per event is good. (High
  *cardinality* is fine in logs/events; it is only forbidden in metric
  labels — see rules/02 §3.)
- Same pattern for non-HTTP work: one event per consumed message, per job
  run, per batch — with queue lag, attempt number, batch size.
- Wide events at INFO are never sampled away independently of their request;
  breadcrumb DEBUG logs are the sampling target.

## 6. Sampling and cost discipline

Log spend is real money and real signal-to-noise. Defaults that are safe at
10 rps bankrupt you at 10k rps.

Rules:
- Never sample: ERROR/FATAL, wide events for failed or slow requests, audit/
  security logs (separate stream, longer retention, stricter access).
- Sample aggressively: DEBUG breadcrumbs on hot paths, wide events for
  boring successes (e.g. keep 1–10% of fast 2xx health-adjacent traffic),
  repeated identical WARNs (log-once-per-N or token bucket per event key).
- Sample per-trace, not per-line: keep or drop ALL logs of a request
  together (key the decision on trace_id, or follow the trace sampling
  decision), otherwise you get unjoinable fragments.
- Loops: never log per-item at INFO. Log batch start/end with counts, and
  per-item only at sampled DEBUG or on failure.

```python
# Bad: 1M lines per batch run
for row in rows:
    logger.info("processing row", row_id=row.id)

# Good: 2 lines + failures
logger.info("batch_started", batch_id=b, total=len(rows))
... # per-row only on failure, at WARN, with row_id
logger.info("batch_completed", batch_id=b, ok=ok, failed=failed, duration_ms=ms)
```

- Tier storage: hot/searchable 7–30 days; archive to object storage for
  compliance; route DEBUG to a cheap or ephemeral sink. Set retention per
  stream deliberately, not platform-default.
- Review the top-10 log producers (by volume and by cost) monthly; the top
  emitter is usually a forgotten DEBUG line or a health check being logged.
  Don't log load-balancer health-check requests at INFO at all.

## 7. What NOT to log

- Secrets/PII (§4) — ever.
- Per-iteration loop spam, poll ticks, "entering function X" tracing — that's
  what spans and profilers are for.
- Full request/response bodies by default. If a payload is needed for
  debugging, log it size-capped, sampled, redacted, behind a flag.
- Health-check and readiness probe traffic at INFO.
- Duplicate error reports up the call stack (§2).
- Anything you wouldn't show a contractor with log access: logs are your
  widest-read datastore with your weakest access control.

## Audit checklist

- [ ] All services emit JSON (or otherwise structured) logs; no printf prose
      on production paths.
- [ ] Field names consistent across services; a field dictionary or OTel
      semantic conventions are followed.
- [ ] Sample 20 ERROR lines from production: every one represents something
      a human should act on. No expected 4xx/no-rows/retry noise at ERROR.
- [ ] Every production log line carries trace_id (or correlation ID); IDs
      flow into async/queue/cron work.
- [ ] Redaction enforced at logger/pipeline level, not call sites; grep logs
      for `Authorization`, `password=`, `eyJ` (JWT), card-number patterns —
      zero hits.
- [ ] One wide event per request/job exists with outcome, duration breakdown,
      and business context; it fires on exceptions too.
- [ ] No per-item INFO logging in loops/batch jobs; hot-path DEBUG is sampled
      or disabled in prod.
- [ ] Sampling never drops errors or splits a request's logs; audit/security
      logs are unsampled on a separate stream.
- [ ] Log volume/cost reviewed; top producers known; retention set per
      stream; health-check traffic not logged.
- [ ] Exception serialization scrubbed (no connection strings/tokens in
      messages or stack locals).
