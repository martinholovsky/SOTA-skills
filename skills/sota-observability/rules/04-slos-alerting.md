# 04 — SLOs & Alerting

Alerts are interrupts on humans; SLOs are the contract that decides which
interrupts are justified. The failure mode to design against is alert
fatigue: a page that is ignorable trains on-call to ignore pages.

## 1. SLI selection: measure user journeys, not infrastructure

An SLI is a ratio: good events / valid events, defined from the user's
perspective.

Rules:
- Derive SLIs from **critical user journeys** (login, search, checkout,
  API call succeeds fast), not from components (CPU, pod count, replication
  lag). Users don't experience CPU; they experience "checkout failed".
- Standard SLI shapes:
  - **Availability**: non-5xx (and non-timeout) responses / valid requests.
  - **Latency**: requests faster than threshold / valid requests — computed
    from a histogram bucket boundary at the threshold (rules/02 §4), not
    from a p99 estimate.
  - **Freshness/lag** (pipelines): events processed within X / all events;
    or age of oldest unprocessed message under threshold.
  - **Correctness/durability** where it matters (e.g., job produced valid
    output).
- Measure as close to the user as possible (load balancer / edge), because
  server-side-only SLIs miss connection failures; complement with synthetic
  probes for low-traffic journeys.
- Define "valid events" explicitly: exclude health checks, exclude 4xx
  caused by clients (but COUNT 429s you caused by under-provisioning),
  document the exclusions in the SLO spec.
- Per-journey SLOs, few of them: 2–5 SLOs per service. Twenty SLOs means
  none of them governs decisions.

**Bad SLIs:** "CPU < 80%", "p99 of an internal function", "pod restart
count", "cache hit rate" (these are diagnostics, fine on dashboards, wrong
as SLOs).

## 2. SLOs and error budgets

- SLO = SLI target over a window: "99.9% of checkout requests succeed,
  rolling 30 days." Rolling windows beat calendar windows for alerting
  (no end-of-month amnesty).
- **Error budget** = 1 − target. At 99.9%/30d: 0.1% ≈ 43.2 minutes of full
  outage, or proportionally longer partial degradation.
- The budget is a spending account that makes reliability negotiable with
  engineering velocity:
  - Budget healthy → ship faster, run chaos experiments, take risks.
  - Budget exhausted → feature freeze / reliability-only work per a
    **documented error budget policy** agreed with product BEFORE the first
    breach. An SLO without consequences is decoration.
- Choose targets from user need and current reality, not vanity: don't
  promise 99.99% when your single-region dependency offers 99.9%; don't set
  an SLO you've never historically met (start at achievable, ratchet).
- Review SLOs quarterly: targets, exclusions, whether the SLI still matches
  the journey, and whether anyone used the budget to make a decision.

## 3. Burn-rate alerts: the multi-window pattern

Threshold alerts ("error rate > 1% for 5m") are either too twitchy or too
slow. Burn-rate alerting fixes both by alerting on the **rate of budget
consumption**.

Burn rate = (observed error ratio) / (1 − SLO). Burn rate 1 = budget exactly
exhausted at window end; 14.4 = monthly budget gone in ~2 days.

Multi-window multi-burn config for a 30d SLO. The Google SRE Workbook's canonical
recommendation is the three bold tiers (14.4/1h, 6/6h, 1/72h); the 3x/24h ticket tier
is a widely-used community extension (Sloth's default; Pyrra's equivalent tier is 2x/1d)
that fills the gap between fast page and slow burn — keep or drop it per taste:

| Severity | Burn rate | Long window | Short window | Budget consumed |
|----------|-----------|-------------|--------------|-----------------|
| **PAGE** | 14.4 | 1h | 5m | 2% of 30d budget in 1h |
| **PAGE** | 6 | 6h | 30m | 5% in 6h |
| TICKET | 3 | 24h | 2h | 10% in 24h (community extension) |
| **TICKET** | 1 | 72h | 6h | slow steady burn |

```yaml
# Prometheus: fast-burn page (99.9% SLO ⇒ 1-SLO = 0.001)
- alert: CheckoutSLOFastBurn
  expr: |
    ( sum(rate(http_requests_total{route="/checkout",code=~"5.."}[1h]))
      / sum(rate(http_requests_total{route="/checkout"}[1h])) ) > (14.4 * 0.001)
    and
    ( sum(rate(http_requests_total{route="/checkout",code=~"5.."}[5m]))
      / sum(rate(http_requests_total{route="/checkout"}[5m])) ) > (14.4 * 0.001)
  labels: {severity: page, slo: checkout-availability}
  annotations:
    summary: "Checkout burning 30d error budget at 14.4x"
    runbook: "https://runbooks.internal/checkout-availability"
    dashboard: "https://grafana.internal/d/checkout-slo"
```

Rules:
- The **short window** is the key fatigue fix: the alert auto-resolves when
  the burn stops, instead of paging for an hour about a blip that ended.
- Both PAGE tiers and both TICKET tiers; nothing else pages on this SLI.
- Use recording rules for the SLI ratios; alert expressions stay readable.
- Sparse-traffic services: burn rates go wild on 3 requests/min. Add a
  minimum-traffic guard or use synthetic probes as the SLI source.

## 4. Alert quality rules

Every alert must pass ALL of these or be deleted/demoted:

1. **Actionable**: there is a specific action a human takes on receipt. "FYI"
   alerts go to dashboards or logs, not notification channels.
2. **Symptom-based, not cause-based**: page on user pain (SLO burn, journey
   failure), not on causes (CPU high, pod restarted, disk 80%, node down).
   Causes belong on the diagnostic dashboard the symptom alert links to.
   Exception: page on causes only for *imminent, irreversible* user pain
   with lead time to act — e.g. "disk full in 4h at current rate", cert
   expiring, backup job failed (durability has no symptom until too late).
3. **Runbook-linked**: every alert carries a runbook URL with: meaning,
   verification step, dashboard link, mitigation steps, escalation. An
   alert nobody can act on at 3am without tribal knowledge is unfinished.
4. **Severity-routed**:
   - **PAGE** (wake a human): user-visible harm now or imminently, and
     human action can help. Fast/medium burn rates, journey down, security
     incident.
   - **TICKET** (next business day): slow burn, capacity trends, flaky
     dependency, single-instance failures the platform self-healed.
   - **NONE** (dashboard/log only): everything else. Most "warning"
     channels should not exist.
5. **Owned**: an alert routes to the team that can fix it. Unowned alerts
   are deleted, not muted.

**Bad:**

```yaml
- alert: HighCPU
  expr: cpu_usage > 0.85          # cause-based; autoscaler's job; no user impact
- alert: PodRestarted
  expr: increase(kube_pod_container_status_restarts_total[5m]) > 0  # self-healed
- alert: ErrorsInLogs
  expr: rate(log_errors_total[5m]) > 0   # any single error pages someone
```

## 5. Fighting alert fatigue (operational practice)

- **Track interrupts as a metric**: pages per on-call shift (target: < 2 per
  shift, each genuinely actionable), ack times, % of pages that led to
  action. Review in a monthly alert review; every page from the last period
  gets a verdict: keep / tune / demote / delete.
- Every incident retro asks two alert questions: did we get paged for the
  symptom (if not, add SLO coverage)? did we get paged for noise during it
  (if so, delete it)?
- Auto-resolve correctness: alerts must clear when the condition clears
  (multi-window helps); stale firing alerts get silenced and then fixed.
- Use inhibition/grouping: when the edge SLO pages, suppress downstream
  cause alerts; group per service per incident, don't send 40 notifications
  for one outage.
- Silences are temporary and expiring with an owner and a reason. A
  permanent silence is a deletion in denial.
- Never alert on every ERROR log line; alert on the SLI. Error logs are for
  diagnosis after the symptom alert fires. (Crash/error-tracker spike
  notifications are tickets, not pages — rules/05 §5.)
- Protect the alerting path itself: dead-man's-switch (an always-firing
  alert whose absence pages via an independent channel) so a broken
  Prometheus/Alertmanager doesn't equal silence-as-success.
- A scheduled job that **never ran** raises no failure alert. Every cron/batch
  job exports a last-success timestamp gauge (pushed, for short jobs) and
  alerts on its age, not its errors:
  `time() - job_last_success_timestamp_seconds > <interval × k>`, plus
  `absent(job_last_success_timestamp_seconds{job="…"})` for a job that never
  reported. Data-pipeline freshness SLAs: `sota-data-engineering` rules/02
  (Orchestration discipline).

## 6. SLO spec template and recording rules

Every SLO is a versioned document next to the alert code:

```yaml
# slo/checkout-availability.yaml
slo: checkout-availability
owner: payments-team
journey: "User completes checkout"
sli:
  kind: availability
  good:  sum(rate(http_requests_total{route="/checkout",code!~"5.."}[$window]))
  valid: sum(rate(http_requests_total{route="/checkout"}[$window]))
  exclusions: "health checks (excluded at scrape), synthetic logged-out probes"
target: 99.9
window: 30d rolling
budget_policy: https://wiki.internal/payments/error-budget-policy
dashboard: https://grafana.internal/d/checkout-slo
runbook: https://runbooks.internal/checkout-availability
```

Precompute the ratios as recording rules so alerts and dashboards share one
definition (no drift between "the alert's error rate" and "the dashboard's"):

```yaml
groups:
- name: slo-checkout
  rules:
  - record: slo:checkout_error_ratio:rate5m
    expr: sum(rate(http_requests_total{route="/checkout",code=~"5.."}[5m]))
        / sum(rate(http_requests_total{route="/checkout"}[5m]))
  - record: slo:checkout_error_ratio:rate1h
    expr: ...   # same, 1h window; repeat for 30m, 6h, 24h, 72h
```

Latency SLOs use the same machinery with the SLI flipped to a bucket ratio:
`1 - (rate(..._bucket{le="0.3"}) / rate(..._count))` is the "too slow" ratio
and burns budget identically to errors. One pair of burn-rate alerts per SLI
— availability and latency page independently because they fail
independently.

## 7. Page vs ticket decision table

| Situation | Route |
|-----------|-------|
| SLO fast burn (14.4x/1h or 6x/6h) | PAGE |
| SLO slow burn (3x/24h, 1x/72h) | TICKET |
| Critical journey down per synthetic probe | PAGE |
| Disk/quota/cert exhaustion with hours of lead time | PAGE if action needed before next business day, else TICKET |
| Single pod OOM, replaced automatically | NONE (dashboard); TICKET if recurring trend |
| Dependency degraded, fallback holding, SLI fine | TICKET |
| Backup/DR job failed | TICKET same-day; PAGE if RPO about to be violated |
| New error type spike in tracker, SLI fine | TICKET |
| Telemetry pipeline down (flying blind) | PAGE — blindness during a real incident is unbounded risk |

## 8. Burn-rate math reference

For SLO target T over window W, with budget B = 1 − T:

- Burn rate b means the W-budget is exhausted in W/b.
- Alert threshold for "consume fraction f of budget in time t":
  b = f × (W/t); error-ratio threshold = b × B.
- Sanity examples for 99.9%/30d (B = 0.001):
  - 2% in 1h → b = 0.02 × 720 = 14.4 → ratio > 1.44%
  - 5% in 6h → b = 0.05 × 120 = 6 → ratio > 0.6%
  - 10% in 24h → b = 0.10 × 30 = 3 → ratio > 0.3%
- Detection time at full outage (ratio = 1): t_detect ≈ threshold × window;
  the 14.4×/1h pager detects total outage in ~52 seconds (0.0144 × 3600 s)
  — verify yours.

## Audit checklist

- [ ] SLOs exist, are user-journey-based, and are written down (target,
      window, SLI query, exclusions, owner); 2–5 per service, not 0, not 20.
- [ ] Latency SLI computed from histogram bucket boundary at the threshold,
      not from averaged quantiles.
- [ ] Error budget policy documented and signed off by product; evidence it
      has actually gated a decision at least once.
- [ ] Paging alerts are multi-window burn-rate (or equivalently
      symptom-based with auto-resolve); no raw "error rate > X for 5m"
      pagers; no cause-based pagers (CPU/restarts/disk%) except
      lead-time-to-irreversible cases.
- [ ] Sample 10 recent pages: every one was actionable, runbook-linked, and
      led to action; pages per shift within budget; monthly alert review
      happens.
- [ ] Every alert has: severity label, owner/route, runbook URL (resolving,
      current), dashboard link.
- [ ] Inhibition/grouping configured; silences expire and carry reasons.
- [ ] Dead-man's-switch on the alerting pipeline; monitoring-down pages via
      an independent channel.
- [ ] Every scheduled job alerts on the age of its last success (and on
      the gauge's absence), so a job that never ran pages (§5).
- [ ] Low-traffic journeys covered by synthetic probes feeding SLIs.
- [ ] Alert definitions in version control, code-reviewed, deployed like
      code (no hand-edited live alerts).
