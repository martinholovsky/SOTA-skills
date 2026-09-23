# 04 — Resilience & Failure Design

Rules for surviving the failures that will happen: slow dependencies, dead
dependencies, overload, and your own retries. Resilience is configuration +
code + tests; any leg missing means it doesn't exist.

## 1. Timeouts: every remote call, no exceptions

**Rule:** Every network call (HTTP, DB, cache, DNS, queue publish) has an
explicit timeout. Library defaults are usually infinite or absurd (e.g., many
HTTP clients default to no timeout) — a missing timeout converts a slow
dependency into thread-pool exhaustion and a full outage. Missing timeout on a
critical path is a Critical finding.

**Rule:** Set timeouts from the callee's measured p99 plus margin (e.g., p99 ×
1.5), not folklore. A 30 s timeout on a 50 ms-p99 service doesn't protect
anything; it queues doomed work for 30 s.

**Rule:** Enforce a deadline budget across hops: the caller's total deadline is
distributed down the chain (propagate remaining-deadline in context/headers).
Inner calls whose timeouts sum to more than the outer deadline do useless work
after the client has already given up.

```text
Client deadline 1000ms
  → gateway (deadline left: 950) → svc A (timeout 400) → svc B (timeout 300)
BAD: A and B each configured 5000ms while the edge gives up at 1000ms.
```

## 2. Retries: bounded, jittered, idempotent-only

**Rule:** Retry only idempotent operations (rules/03 §2), only on retryable
errors (timeouts, 503, connection reset — never 400/401/422), with **bounded
attempts** (2–3), **exponential backoff + full jitter**, and a **retry budget**
(e.g., retries ≤ 10% of requests) so retries can't melt a struggling dependency.

```text
delay = random(0, min(cap, base * 2^attempt))   # full jitter
```

**Rationale:** Synchronized un-jittered retries create thundering herds; the
dependency recovers, gets hit by the synchronized wave, dies again.

**Rule:** Retry at ONE layer. Client retries × mesh retries × queue redelivery
multiply: 3 layers of 3 attempts = up to 27 calls per request — a self-inflicted
DDoS. Decide which layer owns retries per edge and disable the rest.

**Rule:** Never retry on the user's synchronous critical path more than once;
prefer failing fast and letting the user/job-queue retry. Latency added by
retries must fit the deadline budget (§1).

## 3. Circuit breakers: stop calling the dead

**Rule:** Wrap dependencies that can fail-slow with a circuit breaker: after a
failure-rate threshold, open the circuit (fail instantly), then half-open with
probe requests before closing. Failing fast preserves your threads and gives the
dependency air to recover.

**Rule:** Breakers are per-dependency (and ideally per-endpoint), never global.
One breaker shared across all dependencies means a dead recommendation service
opens the circuit to your payment provider.

**Rule:** Every breaker open/close event is logged and alerted; breaker state is
a dashboard metric. A breaker that silently opens turns "degraded" into
"mysteriously missing data".

**Rule:** Define what happens when the breaker is open *as part of the design*:
fallback value, cached last-known-good, degraded UX, or explicit error. An open
breaker with no defined fallback is just a faster outage.

## 4. Bulkheads: isolate the blast radius

**Rule:** Partition resources per dependency and per workload class: separate
connection pools, thread pools/semaphores, and queue consumers so one slow
dependency or one greedy tenant can't starve everything else.

```text
BAD:  one 100-conn pool shared by /checkout and /export-report
      → slow report queries consume all 100; checkout dies.
GOOD: checkout pool: 60, reports pool: 10, admin: 5 — reports saturate alone.
```

**Rule:** Apply bulkheads at infra level too: critical and batch workloads on
separate node pools / autoscaling groups; noisy-neighbor isolation for
multi-tenant systems (rules/05 §7).

## 5. Graceful degradation: rank your features

**Rule:** Classify every dependency of each user flow as *required* or
*optional*. Optional-dependency failure degrades (skip recommendations, show
cached prices with a staleness badge, queue the email) — it never 500s the flow.
This classification is a design artifact, reviewed like code.

**Rule:** Fallbacks must be tested under real failure (chaos, §8) and must be
cheap. A fallback that calls another remote service can fail too; a fallback
that recomputes expensively turns partial failure into overload.

**Rule:** Fail closed for security and money (authz unavailable → deny;
fraud-check down → hold the order or apply strict limits). Fail open only for
genuinely optional features — and record the decision per dependency.

## 6. Load shedding and admission control

**Rule:** Decide what you drop *before* you're overloaded. Under saturation,
reject early (HTTP 429/503 + `Retry-After`) at the edge, cheapest-first:
rejecting a request at admission costs microseconds; timing it out after queuing
costs seconds of capacity.

**Rule:** Shed by priority: health checks and payments last; analytics,
prefetch, and crawlers first. Requires a request-priority signal (header,
route class) plumbed to the shedder.

**Rule:** Bound every in-process queue and use deadline-aware queue draining:
if a request has already exceeded its deadline while queued, drop it without
processing. Serving dead requests is how overload becomes collapse (congestion
collapse / metastable failure).

**Rule:** Protect against retry storms after recovery: combine load shedding
with client retry budgets (§2) and slow-start (gradually re-admit traffic).

## 7. Health checks: liveness ≠ readiness ≠ dependency health

**Rule:** Implement both: **liveness** ("process is not wedged" — never checks
dependencies) and **readiness** ("can serve traffic now" — may check critical
local state, warm caches, config loaded). A liveness probe that pings the
database restarts every replica when the DB blips — converting a dependency
outage into a fleet restart. That's a Critical finding.

**Rule:** Readiness should reflect *this instance's* ability to serve, not
shared dependencies' health: if all replicas mark unready when the DB is down,
you remove all capacity and serve connection errors instead of useful 503s with
degradation. Prefer degrading (§5) over going unready for shared-dependency
failure.

**Rule:** Health endpoints are cheap (<10 ms, no fan-out), unauthenticated only
on internal interfaces, and excluded from load shedding last.

## 8. Test failure on purpose (chaos engineering)

**Rule:** Resilience claims require evidence. Regularly and deliberately inject:
dependency latency (+500 ms), dependency errors (10% 503s), instance kills, AZ
loss, and full dependency outage — in staging always, in production once SLOs
and rollback are in place. Verify SLOs hold and fallbacks fire. Untested
fallbacks fail when needed; this is the most reliable finding in chaos history.

**Rule:** Start with game days (hypothesis → inject → observe → fix), automate
the validated experiments into a recurring suite (fitness functions, rules/01
§5). Every incident's failure mode becomes a permanent chaos experiment.

**Rule:** Define SLOs (availability, latency) per critical user journey with
error budgets. Chaos results, degradation policies, and shedding priorities all
derive from SLOs; without SLOs, "resilient" is an opinion.

## 9. Recovery and operability

**Rule:** Design for fast rollback over fast fix: every deploy is reversible in
minutes (previous artifact kept warm), schema changes are expand/contract so
code rollback never requires schema rollback.

**Rule:** Make restarts safe and boring: graceful shutdown (stop accepting,
drain in-flight within deadline, then exit), startup that tolerates dependency
unavailability (retry with backoff, don't crash-loop the fleet), and idempotent
startup migrations guarded by locks.

**Rule:** Avoid synchronized fleet behavior: jitter cron jobs, cache TTLs, and
token refreshes. Thousands of instances doing anything at the same second is a
self-inflicted spike (cache stampede: use TTL jitter + request coalescing /
single-flight).

## 10. Rate limiting: protect yourself and your dependencies

**Rule:** Rate-limit at every trust boundary: per-client at the public edge
(token bucket, keyed by API key/user, with `429 + Retry-After` and documented
limits), per-tenant inside pooled systems (rules/05 §7), and *outbound* toward
third parties whose limits you must respect — a client-side limiter beats
discovering their limit via a ban.

**Rule:** Prefer adaptive concurrency limits (AIMD/gradient on observed latency)
over fixed RPS numbers for internal hops; fixed numbers go stale the week after
the next deploy changes the cost per request.

**Rule:** Burst handling is a policy decision: token bucket (allows bursts) for
user-facing APIs, leaky bucket / shaping for downstream protection. Pick per
edge and write it down.

## 11. Hedging and tail-latency control

**Rule:** For idempotent reads with bad tail latency, consider hedged requests:
send a second attempt after the p95 mark, take the first response, cancel the
loser. Cap hedging (≤5% extra load) and never hedge writes or non-idempotent
calls.

**Rule:** Attack tail latency at the source before hedging: eliminate
synchronized pauses (GC tuning, connection re-establishment storms), avoid
cross-AZ hops on hot paths, and precompute/coalesce instead of fanning out.
Hedging is a patch over variance, not a substitute for removing it.

## 12. Failure-mode analysis as a design step

**Rule:** For every critical flow, run a lightweight FMEA before launch: list
each dependency hop; for each, ask "what happens if it's slow / erroring /
returning garbage?"; record the designed response (timeout value, retry policy,
breaker, fallback, shed, alert). The output is a table in the design doc;
gaps in the table are gaps in the system.

```text
Checkout flow — failure table (excerpt)
dep          slow                 down                    garbage
payments     timeout 2s, 1 retry  breaker→ hold order,    schema-validate,
             then hold-order      notify user, alert      reject + alert
inventory    timeout 300ms        fallback: optimistic    treat as down
             no retry             reserve, reconcile async
recs         timeout 150ms        skip section            skip section
```

**Rule:** Classify dependencies into tiers (T0: flow fails without it; T1:
degrade; T2: invisible loss) and let the tier dictate the minimum machinery:
T0 = timeout + breaker + tested fallback-or-fail-closed + page; T2 = timeout +
silent skip + ticket-level alert.

## 13. Disaster recovery is resilience at the largest blast radius

**Rule:** Define RTO/RPO per datastore *with the business*, then verify the
architecture delivers it: backup restore is **tested by actually restoring**
on a schedule (an unrestored backup is a hope, not a backup), and cross-region
posture (backup-restore / pilot-light / active-passive / active-active) is an
ADR with cost attached.

**Rule:** Active-active across regions is a Type 1 decision that drags
consistency design with it (conflict resolution, data residency, ID generation).
Don't back into it via "we just added a second region for latency".

## Audit checklist

- [ ] Does every remote call (HTTP, DB, cache, queue) have an explicit timeout? Grep for client construction sites and verify.
- [ ] Are timeouts derived from measured callee latency, and do nested timeouts fit within the edge deadline?
- [ ] Are retries bounded, jittered, restricted to idempotent operations and retryable errors, and owned by exactly one layer per edge?
- [ ] Is there a retry budget or equivalent guard against retry storms?
- [ ] Are circuit breakers per-dependency, with alerting on state change and a defined fallback per open circuit?
- [ ] Are connection/thread pools bulkheaded per dependency and per workload class, or is there one shared pool?
- [ ] Is each dependency of each critical flow classified required/optional, with degradation behavior implemented and tested?
- [ ] Do security- and money-touching paths fail closed?
- [ ] Is there admission control / load shedding with priority ordering, bounded queues, and deadline-aware dropping?
- [ ] Do liveness probes avoid dependency checks? Does readiness avoid mass-unready on shared-dependency failure?
- [ ] Are SLOs defined per user journey, and are chaos experiments (latency, errors, instance/AZ kill) run on a schedule with results tracked?
- [ ] Can every service roll back in minutes, shut down gracefully, and start while its dependencies are down?
- [ ] Are cache TTLs/crons jittered, and is stampede protection (single-flight) in place for hot keys?
- [ ] Is rate limiting present at the public edge (per client), per tenant internally, and outbound toward third-party limits?
- [ ] Is hedging, if used, restricted to idempotent reads with a load cap?
- [ ] Does each critical flow have a failure-mode table (slow/down/garbage per dependency) with designed responses, and are dependencies tiered T0/T1/T2?
- [ ] Are RTO/RPO defined per datastore, backups restore-tested on a schedule, and the cross-region posture an explicit ADR?
