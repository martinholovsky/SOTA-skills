# 05 — Operational Readiness

The surfaces operators and orchestrators use: health endpoints, degradation
visibility, debug/profiling access, crash reporting, dashboards. These ship
WITH the feature, not after the first incident.

## 1. Health endpoints: liveness ≠ readiness ≠ startup

Three probes, three different questions, three different consequences:

| Probe | Question | On failure | Checks |
|-------|----------|-----------|--------|
| Liveness | Is the process irrecoverably wedged? | RESTART | Process-internal only: event loop responsive, no deadlock. Usually just "return 200". |
| Readiness | Can this instance serve traffic NOW? | Remove from LB (no restart) | Required dependencies, warm caches, not draining, not overloaded |
| Startup | Has init finished? | Keep waiting (gates liveness) | Migrations applied, config loaded, connections established |

**The cardinal sin — dependency checks in liveness:**

```yaml
# Bad: database hiccup → every pod fails liveness → cluster-wide restart
# storm → thundering-herd reconnects → outage amplified
livenessProbe:
  httpGet: {path: /health, port: 8080}   # /health pings Postgres + Redis
```

```yaml
# Good
livenessProbe:
  httpGet: {path: /livez, port: 8080}    # process self-check only
  periodSeconds: 10
  failureThreshold: 3
readinessProbe:
  httpGet: {path: /readyz, port: 8080}   # checks required deps, cheap/cached
  periodSeconds: 5
startupProbe:
  httpGet: {path: /startupz, port: 8080}
  failureThreshold: 30                    # allows slow boot without lying livez
```

Rules:
- Restarting a process does not fix its database. Liveness restarts must
  only fire for conditions a restart actually fixes.
- Readiness checks only **required** dependencies (without which serving is
  impossible). Optional dependencies (cache, recommendations) degrade
  gracefully (§2) and must NOT fail readiness — or a Redis blip removes
  your whole fleet from the load balancer.
- Health checks are cheap and bounded: cached dependency status (TTL a few
  seconds), strict timeouts, no real queries against production tables, no
  writes. The probe must not be the load.
- Whole-fleet readiness failure on a shared dependency takes everything out
  of rotation simultaneously — for shared deps, prefer serving degraded
  (§2) over failing ready. Decide per dependency, on purpose.
- Expose a verbose authenticated variant (`/readyz?verbose`) listing each
  check's status for humans; the orchestrator gets the cheap boolean.
- Health endpoints: no auth for the orchestrator path, but not internet-
  exposed; excluded from access logs and request metrics (or labeled out).

## 2. Graceful degradation must be visible

Silent fallbacks rot: the cache that's been bypassed for a week, the
secondary provider quietly serving 100%. Degradation without telemetry is a
latent outage.

Rules:
- Every fallback/circuit-breaker/feature-kill-switch emits, when active:
  a WARN log (rate-limited), a metric
  (`degradation_active{feature="recs",reason="redis_down"}` gauge and a
  fallback counter), and a span attribute (`fallback: true`).
- Circuit breaker state is a metric (`circuit_breaker_state{dep="stripe"}`
  0=closed/1=half/2=open) with state-transition events logged.
- Wide events carry `degraded: true` + which features, so you can quantify
  user impact of running degraded ("12% of requests served without
  personalization").
- Long-running degradation alerts as TICKET (not page, if SLI holds):
  fallbacks are for surviving the night, not for permanent operation.
- Test degradation paths in CI or chaos drills; an unexercised fallback is
  assumed broken.
- **One shared helper, deduped per cause.** Route every degradation through a
  single `degraded(component, reason)` call rather than ad-hoc warnings, and
  dedupe per (component, reason) — not per request. Per-request warnings get
  filtered by operators and stop being read, which returns the system to silent
  failure. This matters most for **security controls**: a scanner or policy
  engine running inert must be a distinct health state, not a quiet default
  (`sota-code-security` rules/10).

## 3. Debug endpoints: powerful and dangerous

`/debug/pprof`, `/actuator`, `/metrics`, heap dumps, env dumps, GraphQL
introspection, `phpinfo` — chronic real-world breach and DoS vectors.

Rules:
- **Never on the public listener.** Bind debug/admin surfaces to a separate
  port/interface reachable only via internal network + authn (mTLS, SSO
  proxy). `kubectl port-forward` beats an exposed route.
- Spring Boot Actuator: explicit include-list only (`health,info,
  prometheus`); `env`, `heapdump`, `threaddump`, `mappings`, `shutdown`
  stay disabled or hard-authed — heapdump and env leak secrets outright.
- Go `net/http/pprof`: importing it registers on `DefaultServeMux` — if
  your app serves DefaultServeMux publicly, you just published profiling
  (info leak + trivial CPU DoS). Register pprof on a dedicated internal-only
  mux/port.
- `/metrics` is internal: scraped by the collector, not world-readable
  (metric names and label values leak topology, tenants, versions).
- Dynamic debug togglers (log level change endpoints, feature inspection)
  are admin APIs: authenticated, audited, rate-limited.
- Audit move: enumerate every listening port and route table; diff against
  "intended public surface". Anything debug-shaped reachable without auth is
  a CRITICAL finding.

## 4. Profiling in production

Metrics say the service is slow; profiles say which function. As of 2026,
**continuous profiling** is a standard fourth signal, not an exotic one.

Rules:
- Run an always-on low-overhead profiler (eBPF agents — Parca, Pyroscope,
  Elastic Universal Profiling; or language-native continuous profilers:
  Go pprof-based, JFR for JVM, py-spy-based). Overhead at ~1–2% CPU buys
  you "what was on-CPU at 3:14am" forever.
- OTel's profiles signal entered public **alpha** in early 2026 (OTLP
  profiles format, Collector pprof receiver, official eBPF-profiler
  distribution) — watch it as the future standard transport, but don't bet
  production profiling on it yet; the established agents above remain the
  stable path until profiles reach GA.
- Profile types: CPU + allocation at minimum; add lock-contention and
  off-CPU/wall where supported (most "slow but idle CPU" mysteries are
  off-CPU: locks, I/O waits, pool waits).
- Tag profiles with `service.version` so a regression diff is "compare
  profile of v2.14 vs v2.13" — flamegraph diffing is the fastest perf-
  regression root-cause tool that exists.
- Keep on-demand deep capture available (pprof endpoint on the internal
  port, JFR trigger) for incidents needing higher resolution.
- Memory-leak workflow: alleged leak → allocation profile + heap diff over
  time, not guess-and-redeploy.

## 5. Crash reporting & error tracking (Sentry-style)

Error trackers answer "what exceptions exist, are they new, who do they
hit" — a different job from logs (search) and alerts (interrupts).

Rules:
- Every unhandled exception in every runtime is captured: backend services,
  workers, frontend JS (with sourcemaps uploaded per release — minified
  stacks are useless), mobile (with dSYM/mapping files). Crash without a
  report = invisible user pain.
- **Release tagging is mandatory**: every event carries `release` and
  `environment`. The killer queries — "new in this release", "regressed
  after being resolved" — depend on it. Wire deploy notifications so the
  tracker knows release boundaries.
- Attach context: trace_id (link back to the trace!), user-impact key
  (opaque user/tenant id per privacy policy), feature flags. Scrub PII via
  the SDK's server-side + client-side scrubbing — same redaction bar as
  logs.
- **Grouping hygiene is the difference between signal and landfill:**
  - Fix groups that lump distinct bugs (over-grouping) or shatter one bug
    into hundreds of issues (under-grouping — usually dynamic strings in
    exception messages; move variables to structured context, keep messages
    static).
  - Every issue gets triaged: assign, resolve-in-release, or ignore-with-
    reason. "5,000 open unassigned issues" means the tracker is dead;
    institute a weekly triage rota and resolve-by-default policies for
    stale noise.
  - Resolved-then-reoccurred ("regression") notifications ON — that's the
    highest-signal notification type the tool has.
- Notification policy: new issue / regression / spike → TICKET (or chat),
  not page. Pages come from SLOs (rules/04); the tracker tells you WHICH
  exception is burning the budget.

## 6. Shutdown, crashes, and the last 10 seconds

The least-observed moments of a process are its first and last seconds —
and that's where deploy regressions and OOM mysteries live.

Rules:
- **Graceful shutdown is observable**: on SIGTERM log `shutdown_started`
  (with reason if known), flip readiness to failing, drain in-flight work
  with a deadline, flush telemetry exporters (spans, metrics, logs, error
  tracker), then log `shutdown_completed{drained=n, aborted=m}`. A deploy
  that loses its final telemetry batch hides exactly the requests it broke.
- **Crash forensics**: panics/fatal errors write a structured last-gasp
  line (and error-tracker event where the SDK supports fatal handling)
  before exit; container stdout is the channel of record — never only a
  file inside the dying container.
- **OOM kills are invisible to the app** — detect them from the outside:
  kube_state_metrics `OOMKilled` reason, exit code 137 tracking, and a
  memory-usage-vs-limit panel per workload. Recurring OOM = TICKET with the
  allocation profile attached (§4), not a silent restart loop.
- **CrashLoopBackOff has a budget**: restarts are a metric; > N restarts/h
  on one workload tickets the owner even if replicas mask user impact.
- Startup is logged once, structured: version, config hash (not values),
  migrations applied, listening ports. "What exactly is running right now"
  must be answerable from logs alone.

## 7. Dashboards that answer questions

A dashboard is a pre-computed answer to a question you expect to ask under
stress. A wall of 40 unlabeled graphs is a vanity wall, not a tool.

Rules:
- Name the question. Each dashboard (and ideally each row) answers
  something specific: "Is checkout healthy?" "Why is checkout slow right
  now?" "Are we keeping up with the queue?"
- Standard per-service layout, top to bottom = symptom to cause:
  1. SLO status + burn rate (is it broken? how badly?)
  2. RED per route (where is it broken?)
  3. Dependency latency/errors (is it them?)
  4. USE/saturation: pools, queues, CPU/mem (is it us, resource-wise?)
  5. Deploy/config-change annotations overlaid on everything (was it a
     change? — it usually was).
- Every paging alert's runbook links a dashboard whose top row confirms the
  symptom and whose rows below bisect causes.
- Link down the stack: dashboard panel → exemplar trace → logs by trace_id.
  A panel that can't lead anywhere deeper is a dead end at 3am.
- Dashboards as code (Grafana provisioning/Jsonnet/Terraform), reviewed,
  versioned. Hand-edited live dashboards drift and die.
- Delete dashboards nobody opened in 90 days (usage stats exist). Curation
  is a feature: the on-call landing page lists THE five dashboards that
  matter.
- No averaged percentiles, no per-instance p99 walls (rules/02 §4); prefer
  route/tenant breakdowns over instance breakdowns for symptom dashboards.

## 7a. The question with no instrument, and the substitute that answers a different one

§7 assumes the data exists. The harder failure is a question with **no** instrument
behind it — and it never presents as a gap, because somebody always finds a proxy
and the proxy returns a number.

The canonical case is a removal decision. *"Is this feature still used?"* is a
question about **requests**, and it is answerable only from request-level telemetry
at the edge: gateway/ingress/load-balancer access logs, or per-route and per-field
usage metrics (`sota-api-design` rules/02 §5 step 4, rules/03 §11 — *without
per-field usage data you can never delete anything*). With those absent, the
reachable substitute is the **stored data**: query the corpus, count what carries
the feature's shape, conclude.

That answers *"does data shaped like this exist"* — a different question, with a
different answer and a **known direction of error**. Stored data outlives its last
reader, so the corpus systematically over-reports use and the substitute is biased
toward keep-it. The shape recurs: commit count standing in for maintenance, a
dependency's presence in a manifest standing in for it being reached (`sota-devsecops`
rules/03 §3.9), a dashboard existing standing in for someone opening it.

Rules:
- **Edge access logs are a required telemetry stream**, not an optional one, wherever
  a gateway/ingress/LB fronts a versioned or deprecable surface. Sample if volume
  demands, but **retain across one deprecation runway** — rules/02 §5 publishes a
  ≥ 6-month runway, so 30-day retention cannot support the decision it exists for.
  Log the route *template* and the principal *id*, not the raw path and identity
  (cardinality and PII: rules/01).
- **Instrument the question you will be asked, not only the ones you are asked
  today.** "Which surfaces can we retire?" is asked of every system that lives long
  enough; it needs a per-route/per-field usage counter from the day the surface
  ships (rules/02 §5's "usage metric the day its successor ships").
- **When you substitute, say so in the same sentence as the number.** Name the
  question you could answer, the question you were asked, and the direction the
  substitution errs. *"Zero rows carry this field"* is evidence; *"nobody uses this
  feature"* is a claim that measurement does not support.
- **Prefer instrumenting forward over inferring backward.** If the signal is absent
  and the decision is reversible, adding the counter and waiting one runway is
  usually cheaper and always sounder than building a more elaborate proxy. Record
  the gap as a finding in its own right — *a decision was made on a substitute
  measure* is a durable observability defect, and it recurs on the next removal.

## 8. Synthetic monitoring

Real-user telemetry goes silent exactly when traffic does — overnight
low-traffic windows, broken signup flows (no users get far enough to emit
errors), pre-launch features.

Rules:
- Probe every critical journey end-to-end (not just `/health`): scripted
  login → action → assert on response content, from outside your network,
  from the regions users are in.
- Tag synthetic traffic (`synthetic: true` header → wide-event field) so it
  is excludable from SLIs/business metrics while feeding its own
  availability SLI for low-traffic journeys (rules/04 §1).
- Probe failures page only on consecutive failures from multiple locations
  (single-location flaps are network noise).
- Certificates, DNS, and domain expiry are synthetic checks too — classic
  "no symptom until total outage" causes with perfect lead time.

## 8a. Test writes and production writes must not share a sink

§8 tags synthetic *probe* traffic so it is excludable from SLIs. The same requirement
holds one layer down and is met far less often: **telemetry a test run can write must be
distinguishable from telemetry production writes, at the point of collection.**

- Either a **separate sink** — a distinct directory, table, index, bucket prefix or
  dataset chosen by config — or a **stamped marker on every record** (`env: test`, the
  provider identity, the run id). Prefer the separate sink; a marker only helps a reader
  who already knows to filter on it.
- **Never a naming convention.** One filename pattern for both, told apart by "test runs
  happen to have a round row count", is not a filter — it is post-hoc archaeology,
  available only to someone who already suspects the problem. The same goes for filtering
  on a *value*: excluding rows by duration or size infers the population from the data
  instead of recording it.
- The stamp goes on at **write** time, in the emitting code. A field the reader adds can
  only classify what the reader already understands, which is the case that was never in
  doubt.
- **Check the ordering, not just the presence, of the stamp.** In this library's own eval
  harness the runner recorded its denominator *before* branching into `--selftest`, so a
  self-test row and a measurement row were byte-identical apart from the elapsed time —
  the marker existed and was written on the wrong side of the branch (2026-09-02).
- Git-ignoring or gitignoring a local sink is not isolation: it keeps the file out of the
  repo, not the test rows out of the aggregate.
- The reader-side obligation — every aggregate over a shared sink states its exclusion
  filter, and an unexplained jump in n is contamination rather than power — is
  `sota-code-security` rules/11 §2.7.

## Audit checklist

- [ ] Liveness, readiness, startup probes distinct; liveness contains NO
      dependency checks; readiness fails only on required deps; probes are
      cheap, cached, and bounded.
- [ ] Optional-dependency failure degrades service without failing
      readiness; shared-dependency behavior (fail vs degrade) is a
      documented decision.
- [ ] All degradation paths (fallbacks, breakers, kill switches) emit
      metric + log + span attribute when active; long-running degradation
      tickets someone.
- [ ] Port/route inventory done: no pprof/actuator/metrics/heapdump/env/
      introspection endpoints reachable without auth from outside the
      internal network; Go DefaultServeMux not publicly served with pprof
      imported.
- [ ] Continuous profiling running with version tags; on-demand capture
      path documented; off-CPU/lock profiling available where supported.
- [ ] No sink receives both test-suite and production telemetry without a write-time
      marker or a separate destination; any analysis over a shared sink states its
      exclusion filter (§8a).
- [ ] Error tracker captures all runtimes incl. frontend with sourcemaps;
      release+environment on every event; trace_id linked; PII scrubbed.
- [ ] Issue grouping healthy (no message-interpolation shatter); triage
      rota exists; regression notifications enabled; open-untriaged count
      is bounded.
- [ ] Per-service dashboard follows symptom→cause layout with deploy
      annotations; paging alerts link runbook + dashboard; panels
      click-through to traces/logs.
- [ ] Dashboards and alerts are code-reviewed and provisioned, not
      hand-edited; stale dashboards pruned.
- [ ] Edge access logs (gateway/ingress/LB) exist for every deprecable surface,
      with per-route/per-field usage counters and retention covering a full
      deprecation runway — and where a usage question was answered from stored
      data instead, the substitution and its direction of error are stated
      beside the number, not left implied (§7a).
