# 06 — Observability Audit Playbook

How to assess a codebase/deployment's observability posture. The verdict
hinges on two questions, answered with evidence, not vibes:

1. **"Why is this request slow?"** — for an arbitrary single production
   request, can an engineer reconstruct where time went, today, with
   existing signals?
2. **"What broke at 3am?"** — would the team be paged for real user pain,
   and could a non-author on-call localize the cause in minutes?

## 1. Method: trace real paths, distrust claims

Do not grade by which tools are installed; OTel-in-requirements.txt proves
nothing. Pick 2–3 **critical user journeys** (the money paths) and follow
each through the code:

1. Entry point: is there middleware emitting a wide event / server span /
   RED metrics? Read the actual middleware config, not the framework docs.
2. Each outbound hop (DB, cache, HTTP, queue): spans? context injected?
   latency recorded per dependency?
3. Async continuation (consumer, job): context restored? its own wide
   event? lag metric?
4. Failure path: throw an exception mentally at each layer — where is it
   logged (once?), is the span marked, does the wide event still fire, does
   the error tracker see it, which alert (if any) fires, and at what user
   impact threshold?
5. The 3am simulation: pick last quarter's worst incident (or invent
   "dependency X p99 ×10"); walk the on-call path: which alert fires →
   which runbook → which dashboard → which trace/log query. Every missing
   link is a finding.

If you have live access, prefer empirical checks: pull one trace and count
services in it; grep an hour of logs for trace_id coverage; list firing and
recently-fired alerts; open the on-call dashboard cold and try to answer
"is checkout healthy right now".

## 2. Evidence-gathering greps and probes

Adapt to language/stack; these locate the load-bearing code fast.

```bash
# Logging reality: structured vs printf
grep -rEn 'print\(|console\.log|System\.out|fmt\.Print' --include='*.py' --include='*.js' --include='*.ts' --include='*.go' --include='*.java' src/ | head
grep -rEn 'logger\.|log\.|slog\.|zap\.|structlog|pino|winston' src/ | head

# Level abuse: expected events at error level
grep -rEn 'log(ger)?\.(error|Error)' src/ | grep -iE 'not found|retry|invalid input|missing param'

# Secrets/PII risk at call sites
grep -rEn 'log.*\b(password|token|secret|authorization|api_key|ssn|card)' -i src/
grep -rEn 'log.*(req\.(headers|body)|request\.(headers|json)|to_dict\(\)|JSON\.stringify\(req)' src/

# Correlation: who binds trace/request IDs, and is it middleware or hand-passed
grep -rEn 'trace_id|traceId|correlation|request_id|traceparent' src/ | head -30

# OTel posture: API vs SDK, where configured, propagators
grep -rn 'opentelemetry' --include='*' -l | head
grep -rEn 'TracerProvider|set_tracer_provider|NodeSDK|sdktrace' src/   # should hit ~1 file/service
grep -rEn 'inject|extract' src/ | grep -i propagat                      # queue propagation exists?

# Metrics cardinality: label values from variables = suspect
grep -rEn '\.labels\(|With\(prometheus\.Labels|attributes=' src/ | grep -vE '"(GET|POST|2xx|4xx|5xx)"'

# Health endpoints: what do they actually check
grep -rEn '(livez|healthz|readyz|/health|/ready|liveness|readiness)' src/ k8s/ deploy/ charts/

# Debug surface exposure
grep -rEn --exclude-dir=node_modules --exclude-dir=.git 'pprof|actuator|debug|heapdump|/metrics' . | grep -ivE 'test|_test'

# Alerting/dashboards as code present at all?
find . -path ./node_modules -prune -o -name '*.y*ml' -print | xargs grep -lE 'alert:|groups:|burn|slo' 2>/dev/null
find . -name '*.json' | xargs grep -l '"panels"' 2>/dev/null | head

# Error tracking
grep -rEn 'sentry|rollbar|bugsnag|crashlytics|captureException' src/ | head
```

Then read the hits in full context — a grep match is a lead, not a finding.

## 3. Common gaps catalog

Pattern-match against these; each maps to the rules file that specifies the
fix. Severity per SKILL.md conventions.

**Logging (rules/01):**
- G1. printf/console logging on prod paths; unparseable. [MEDIUM]
- G2. No correlation/trace ID in logs; async/queue work logs orphaned. [HIGH]
- G3. Secrets/PII reachable in logs (headers, bodies, user objects dumped);
  no logger-level redaction. [CRITICAL]
- G4. ERROR noise: 4xx/no-rows/successful-retry at ERROR; log-and-rethrow
  duplicates. [MEDIUM, HIGH if error-rate alerts feed off it]
- G5. No wide event; debugging = joining 15 breadcrumbs by timestamp. [HIGH]
- G6. Per-item loop logging, health checks logged, no sampling/retention
  policy; cost unowned. [MEDIUM]
- G29. No logging inventory: nobody can say, per stack layer, which events are
  logged, in what format, to which sink, read by whom, under what access
  control and for how long; or it exists but is not shipped with release
  documentation to the system owner, and code review and security testing
  never check that the specified events fire with consistent names and
  severities. [MEDIUM, HIGH where an audit trail is a compliance claim]
  OWASP: ASVS 5.0 V16.1.1, Logging cheat sheet.

**Metrics (rules/02):**
- G7. No RED per route; or "error" undefined (4xx counted, timeouts not). [HIGH]
- G8. No saturation metrics on pools/queues — the "slow but CPU idle"
  blindspot. [HIGH]
- G9. Unbounded labels (IDs, raw paths, error strings). [HIGH; CRITICAL if
  user-mintable]
- G10. Latency as gauge/average; p99s averaged across instances; buckets
  never tuned to SLO thresholds. [MEDIUM–HIGH]
- G11. No exemplars / no metric→trace path. [MEDIUM]

**Tracing (rules/03):**
- G12. No tracing at all on a multi-service system. [HIGH]
- G13. Broken propagation: traces shatter at queue/job boundaries; one user
  action = N disconnected traces. [HIGH]
- G14. Vendor SDK calls scattered through business code; SDK config
  duplicated per module. [MEDIUM]
- G15. Naive 1% head sampling: zero traces of any error. [MEDIUM–HIGH]
- G16. PII in span attributes or baggage; baggage leaking to third parties. [CRITICAL]

**SLOs & alerting (rules/04):**
- G17. No SLOs; alerting is ad-hoc thresholds someone set in 2022. [HIGH]
- G18. Cause-based paging (CPU, restarts, disk%) with no symptom coverage;
  or every ERROR log pages. [HIGH]
- G19. Alerts without runbooks/owners; permanent silences; > a few pages
  per shift; on-call confirms they ignore some alerts. [HIGH]
- G20. SLO exists but no error budget policy; never influenced a decision. [MEDIUM]
- G21. No dead-man's-switch: monitoring outage = silence = "all good". [HIGH]

**Cross-cutting:**
- GX1. Signals exist but don't link: no trace_id in logs, no exemplars, no
  release tags — three databases that can't be joined. [HIGH]
- GX2. Observability only on HTTP: cron jobs, consumers, and batch
  pipelines emit nothing (check: does the nightly job's failure surface
  anywhere within 24h?). [HIGH]
- GX3. Staging-only telemetry config drift: sampling/exporters differ from
  prod so nothing is rehearsed where it matters. [MEDIUM]
- GX4. Tribal-knowledge debugging: the one engineer who knows the magic
  log query is the real observability system. Runbooks/dashboards absent
  or stale. [MEDIUM]

**Operational readiness (rules/05):**
- G22. Liveness probe checks dependencies (restart-storm primitive); or
  readiness == liveness == "return 200". [CRITICAL/HIGH]
- G23. Debug/profiling/metrics endpoints reachable without auth from
  outside the internal network. [CRITICAL]
- G24. Silent fallbacks: degradation with no metric/log/alert. [HIGH]
- G25. No error tracker, or tracker is a landfill (thousands untriaged, no
  release tags, no sourcemaps). [HIGH/MEDIUM]
- G26. No profiling story; perf incidents debugged by redeploy-and-pray. [MEDIUM]
- G27. Dashboard sprawl: vanity walls, no deploy annotations, no
  symptom→cause structure, hand-edited. [MEDIUM]
- G28. Telemetry pipeline unmonitored (export drops invisible); single
  collector SPOF. [HIGH]

## 4. Time-boxed audit plans

Match depth to the time available; always deliver the two verdicts.

**90 minutes (smoke audit):** run §2 greps; read the request middleware,
one queue consumer, the probe manifests, and the alert rules file; check
for trace_id in a sample log line; deliver verdicts + top-5 findings.

**1 day (standard):** full §1 journey trace for two paths incl. failure
path; label-cardinality review of every custom metric; alert inventory
against the rules/04 quality bar; debug-surface enumeration; scored rubric
+ full findings report.

**1 week (deep):** everything above, plus: live verification (break a
sandbox dependency and watch the signals), page-history analysis for a
quarter (actionability rate, pages/shift), telemetry cost review (top log/
metric/trace producers vs value), pipeline failure-mode testing (kill the
collector — does anyone notice?), and on-call interviews (the single
highest-signal source: ask "which alerts do you ignore?" and "what do you
wish you could see?").

Sequencing rule: hunt CRITICALs first (secrets in telemetry, liveness
dep-checks, exposed debug endpoints) — they are cheap to find with greps
and unacceptable to miss regardless of time box.

## 5. Scoring rubric

Score each pillar 0–3; report the profile, not just a total.

| Pillar | 0 — Blind | 1 — Basic | 2 — Solid | 3 — SOTA |
|--------|-----------|-----------|-----------|----------|
| Logging | printf, no IDs | structured, partial IDs | JSON + trace_id + redaction | + wide events, sampling, cost-managed |
| Metrics | none/host-only | some app metrics | RED+USE, bounded labels, real histograms | + exemplars, SLO-tuned buckets, cardinality guards |
| Tracing | none | edge-only spans | E2E propagation incl. queues, semconv | + tail sampling, profile/log/metric linkage |
| SLOs/alerts | ad-hoc thresholds | SLIs defined | SLOs + burn-rate paging + runbooks | + budget policy in use, alert reviews, DMS |
| Op readiness | none | health endpoint exists | correct probes, error tracker, secured debug | + continuous profiling, degradation visibility, dashboards-as-code |

Verdicts for the two questions:
- **"Why is this request slow?"** YES = trace_id from any log/event → full
  trace with per-dependency timing → profile if CPU-bound. PARTIAL = some
  hops visible. NO = timestamp archaeology.
- **"What broke at 3am?"** YES = symptom page fires at real impact, runbook
  + dashboard localize within minutes. PARTIAL = paged but must improvise.
  NO = customers are the alerting system.

## 6. Report structure

```
# Observability Audit — <system> — <date>

## Verdict
"Why is this request slow?"  — YES/PARTIAL/NO + one-line evidence
"What broke at 3am?"         — YES/PARTIAL/NO + one-line evidence
Pillar scores: Logging 2/3, Metrics 1/3, Tracing 0/3, SLOs 1/3, OpReady 2/3

## Critical & High findings
[findings in SKILL.md format, sorted by severity, with file:line evidence]

## Medium & Low findings
[...]

## Shortest path to YES
1–5 ordered moves with highest MTTR-reduction per effort, e.g.:
1. Add trace_id injection middleware + wide event (S) — unlocks correlation
2. Replace CPU pagers with 2-tier burn-rate alerts on checkout SLI (M)
3. Move liveness dep-checks to readiness (S) — removes restart-storm risk
```

Rules for findings:
- Every finding carries verbatim evidence (file:line snippet, alert YAML,
  probe config). No evidence → no finding.
- Distinguish "absent" from "present but broken" — broken telemetry that
  the team trusts is worse than a known gap.
- Note what is GOOD too: the team must know what not to break, and audits
  that only criticize get ignored.
- Prioritize by incident impact, not by purity: a missing wide event on the
  checkout path outranks printf logging in an internal cron.

## Audit checklist (meta — did the audit itself cover everything)

- [ ] 2–3 critical user journeys traced through actual code, entry to
      async tail, including the failure path.
- [ ] The two verdict questions answered with named evidence.
- [ ] All five pillars scored; gaps mapped to catalog IDs and rules files.
- [ ] Secrets/PII telemetry scan performed (logs, span attributes, baggage,
      error tracker payloads).
- [ ] Probe configs (liveness/readiness) read from deploy manifests, not
      assumed; debug surface enumerated from route/port truth.
- [ ] Alert inventory reviewed against actionability/runbook/owner bar;
      on-call interviewed or page history sampled if accessible.
- [ ] Telemetry pipeline itself assessed (sampling config, export loss,
      collector SPOF, dead-man's-switch).
- [ ] Findings carry file:line evidence, severity, concrete fix, effort;
      "shortest path to YES" list delivered.
- [ ] Logging inventory requested and compared with the code (G29): pick
      three events it lists (e.g. a failed login, an authorization denial, an
      admin change), trigger each in a test or sandbox, and confirm the record
      arrives in the named sink with the documented name, fields and severity.
