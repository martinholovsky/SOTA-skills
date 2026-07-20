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
