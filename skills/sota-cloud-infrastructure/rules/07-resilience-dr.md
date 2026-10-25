# 07 — Resilience & Disaster Recovery

Scope: RTO/RPO-driven design, DR strategy tiers, multi-AZ vs multi-region decisions,
dependency mapping, quota management, graceful degradation, DR testing. Backup
mechanics: [rules/05](05-data-storage.md). Alerting/SLO machinery: [sota-observability](../../sota-observability/SKILL.md).

## 1. Start from RTO/RPO, not from architecture

- Every system gets two numbers assigned by the business owner, recorded next to
  the system inventory:
  - **RTO** — max tolerable time to restore service.
  - **RPO** — max tolerable data loss window.
- Without declared numbers, engineers silently assume either "whatever
  backup-restore gives" (and the business assumes zero-downtime) or gold-plate
  everything multi-region. Both are failures. "Undeclared RTO/RPO for a
  production system" is itself an audit finding (Medium).
- Tier the portfolio — typically 3–4 tiers — and map each tier to a DR strategy
  and a test cadence. Most systems belong in lower tiers; the conversation that
  puts them there is the deliverable.

## 2. DR strategy tiers

| Strategy | Typical RTO | Typical RPO | Cost shape | Mechanics |
|---|---|---|---|---|
| **Backup & restore** | hours–day+ | hours (last backup) | Storage only | Cross-region/account backups ([rules/05](05-data-storage.md)) + IaC to rebuild; restore runbook |
| **Pilot light** | tens of min–hours | minutes | Data replication + dormant minimal core | Data continuously replicated; core infra (DB replica, AMIs/images, network) exists but scaled to ~0; scale up on declare |
| **Warm standby** | minutes | seconds–minutes | Scaled-down full copy running | Full stack live at reduced capacity in second region; scale + cut traffic over |
| **Active-active** | ~seconds–minutes | ~0 | ≥ 2x + engineering complexity | Both regions serve; data layer is the hard part (conflict resolution or partitioned writes); failover = weight shift |

- RTO/RPO of the **data layer dominates**: stateless compute redeploys in minutes
  from IaC + registries; the database replica lag, promotion time, and backup
  granularity set your real numbers. Design data first.
- **Failover must be tested-automatic or runbook-manual — decide.** Auto-failover
  that's never been exercised will surprise you (split-brain, flapping); manual
  failover needs a decision tree (who declares, on what evidence) or you'll lose
  your RTO to meetings. Record the declare-authority by name/role.
- DR region requirements: IaC fully region-parameterized; images/artifacts
  replicated; secrets/KMS available in target region (multi-region keys or
  per-region keys provisioned — a backup you can't decrypt in-region is
  decoration); DNS/traffic-management plan (low TTLs, health-checked routing or
  global LB); quotas pre-raised in the standby region (cold quotas are the classic
  pilot-light failure — everyone's DR plan targets the same region).

```hcl
# GOOD: DNS failover wired before the incident (Route 53 sketch)
resource "aws_route53_health_check" "primary" {
  fqdn              = "api-primary.example.com"
  type              = "HTTPS"
  resource_path     = "/healthz" # meaningful readiness, see rules/03 §8
  failure_threshold = 3
}
resource "aws_route53_record" "api_primary" {
  zone_id         = aws_route53_zone.main.zone_id
  name            = "api.example.com"
  type            = "CNAME"
  ttl             = 60 # low TTL: failover applies in ~minutes, not cache-lifetime
  set_identifier  = "primary"
  records         = ["api-primary.example.com"]
  health_check_id = aws_route53_health_check.primary.id
  failover_routing_policy { type = "PRIMARY" }
}
# BAD: TTL 86400 on the record you plan to repoint during a disaster
```

## 3. Multi-AZ is the default; multi-region is a justified exception

- **Multi-AZ, always, for prod:** LBs spanning zones, ASGs/MIGs across ≥ 2 (prefer
  3) AZs, multi-AZ managed databases, K8s topology spread ([rules/04](04-compute-selection.md)). AZ failure
  is common enough to design for by default and cheap enough to absorb (the main
  cost is cross-AZ traffic — accept it for prod).
- **Multi-region active-active is justified by:** regulatory mandate, genuinely
  global latency requirements, or revenue-per-minute that dwarfs the 2x+ cost and
  the permanent complexity tax (data consistency, double the deploy surface,
  config drift between regions). For most systems, the honest answer is multi-AZ +
  pilot-light/warm-standby DR.
- The most common resilience lie: "multi-region" where region B has never served
  production traffic. Untested standby = backup-restore with extra steps and extra
  cost. If you pay for warm standby, route a trickle of real traffic or fail over
  on schedule.
- Account for **control-plane vs data-plane** behavior in regional incidents:
  during a region's bad day, creating new resources (control plane) often fails
  while existing ones (data plane) keep running — DR designs that require
  mass-creating resources mid-incident are betting on the part most likely to be
  degraded. Pilot light pre-creates the skeleton for exactly this reason. Prefer
  static stability: pre-provisioned capacity over launch-on-failure.

## 4. Dependency mapping

- You cannot state an RTO without knowing the dependency graph. For each tier-1
  system, maintain the list of: cloud services used (per region), internal
  upstreams, third-party SaaS (auth provider! payment! email!), and DNS/CDN/cert
  chain — each annotated with "what happens here if it's down" and "does our DR
  region remove this dependency or duplicate it".
- **Your availability ceiling is the weakest hard dependency.** A multi-region app
  with single-region auth, a single payment provider, or one CDN has that
  provider's availability, not yours. Decide per dependency: accept (document),
  degrade (see §6), or dual-source (rarely worth it; auth and DNS are the usual
  candidates).
- Hidden circulars to hunt in audits: deploy pipeline hosted on the infrastructure
  it deploys; secrets manager needed to boot the secrets manager's dependencies;
  SSO required to reach the console during an SSO outage (break-glass, [rules/02](02-iam-design.md)
  §7); runbooks stored on the wiki that's down.

## 5. Quotas, limits, and capacity

- Cloud quotas are soft until they're not — at 2am during failover. For every prod
  account: know the top 10 quotas you actually consume (instances per family,
  vCPUs, EIPs, LB count, API rates, function concurrency), monitor utilization
  against limits (provider quota dashboards + alerts at ~70%), and pre-request
  headroom in DR regions for tier-1 capacity.
- Quota increases take hours–days and need a support tier that can answer —
  factor both into RTO. Anything that "requests quota on failover" has already
  failed.
- Also bound the other direction: autoscale maxes and concurrency caps ([rules/06](06-cost-finops.md))
  so one system's incident can't exhaust shared account limits and become
  everyone's incident — or isolate noisy systems into their own accounts
  ([rules/01](01-org-accounts-governance.md)).

## 6. Graceful degradation architecture

Total failure should be the last stop, not the first. Build the intermediate
states:

- **Classify features critical vs sheddable** per service; expose kill switches /
  feature flags ops can flip without a deploy (flag system itself must fail open
  to defaults).
- **Standard patterns:** timeouts on every remote call (no default-infinite
  clients); retries with backoff + jitter and a budget (retry storms turn brownout
  into blackout); circuit breakers around flaky dependencies; load shedding /
  admission control when saturated (fast 429/503 beats slow death); queues as
  buffers between tiers (accept writes, defer processing); serve stale
  cache/read-only mode when the write path is down.
- Degraded modes are product decisions — "checkout works, recommendations blank"
  needs a product sign-off before the incident, not during.
- Implementation detail of these patterns in code: see [sota-async-concurrency](../../sota-async-concurrency/SKILL.md) and
  [sota-api-design](../../sota-api-design/SKILL.md); this file owns the requirement that the modes exist.

## 7. Test it: game days and DR exercises

An untested DR plan is a document, not a capability. Cadence by tier:

- **Tier-1:** full DR exercise (actual regional failover or full restore-and-serve)
  at least annually; component-level chaos (AZ evacuation, instance/pod kill, DB
  failover, dependency blackhole) quarterly; backup restore test quarterly
  ([rules/05](05-data-storage.md)).
- **Game day discipline:** written scenario + hypothesis; defined blast radius and
  abort criteria; run in prod-like (or prod, with leadership sign-off and
  controlled scope — start in staging, graduate); measure actual RTO/RPO vs
  declared; file and fix the gaps. The measured numbers replace the aspirational
  ones in the inventory.
- Use fault-injection tooling where available (AWS FIS, chaos engineering tools,
  Azure Chaos Studio) instead of hand-run destruction; tooling gives repeatability
  and stop conditions.
- Also exercise the humans: paging works, runbooks current, declare-authority
  known, status comms templates exist. Half of blown RTOs are coordination, not
  technology.

## Audit checklist

- [ ] System inventory exists with declared RTO/RPO per system, business-owner
      signed; tiers mapped to DR strategies (§1, §2).
- [ ] Prod workloads multi-AZ end to end: LB, compute groups/topology spread, DB
      multi-AZ; no tier-1 singleton in one zone (§3).
- [ ] Multi-region claims verified: standby actually serves traffic in tests;
      IaC region-parameterized; images, secrets, and KMS keys available in DR
      region; DNS/traffic failover defined with low TTLs; multi-region active-active
      has a recorded justification; DR does not rely on creating resources
      mid-incident (pre-provisioned, statically stable) (§2, §3).
- [ ] Data layer numbers known: replica lag, promotion time, backup cadence —
      consistent with declared RPO/RTO (do the math; flag fantasy numbers) (§2).
- [ ] Failover mode decided (auto vs manual) and exercised; declare-authority
      named; runbook accessible during an outage of the primary (not on the
      affected wiki) (§2, §4).
- [ ] Backups cross-account/cross-region per tier with tested restores ([rules/05](05-data-storage.md));
      restore time measured against RTO.
- [ ] Dependency map for tier-1 systems incl. third parties; each hard dependency
      has accept/degrade/dual-source decision; no hidden circulars (deploy, auth,
      secrets, DNS) (§4).
- [ ] Top consumed quotas monitored against limits with alerts (~70%); DR-region
      quotas pre-raised for tier-1 capacity; support plan adequate for incident-time
      escalation (§2, §5).
- [ ] Degradation built: timeouts/retry budgets/circuit breakers/load shedding on
      critical paths; kill switches exist and were flipped in a test; degraded
      modes product-approved; the flag system fails open to defaults (§6).
- [ ] Last DR exercise within cadence for each tier; measured RTO/RPO recorded;
      gap actions closed; the exercise also covered the humans — paging, runbooks,
      declare-authority, comms templates (§7). Ask for evidence, not assurances.
