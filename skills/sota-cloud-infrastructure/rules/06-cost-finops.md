# 06 — Cost Engineering (FinOps)

Scope: cost visibility, the big optimization levers, unit economics, anomaly
detection, and cost as a review gate. Cost is an architecture fitness function: a
design that meets every functional requirement at 4x the necessary spend is a wrong
design, the same way one that misses latency budgets is.

Pricing numbers change constantly — this file names the *mechanisms and traps*;
verify current rates against provider pricing pages before committing numbers to a
design.

## 1. Visibility before optimization

You cannot optimize what you cannot attribute. Sequence: allocate → show → set
targets → optimize. Optimizing an unattributed bill produces one heroic month and a
relapse.

- **Allocation foundation = account structure + tags.** Account/project-per-team
  ([rules/01](01-org-accounts-governance.md)) gives you coarse attribution for free; mandatory `owner`, `service`,
  `env`, `cost-center` tags (activated as cost-allocation tags / labels) give
  per-workload resolution. Shared costs (network hubs, clusters, support plans,
  data transfer) need an explicit, documented split rule — even a crude one beats
  "platform absorbs it".
- **Export raw billing data** to a queryable store (AWS CUR/Data Exports → Athena;
  GCP billing export → BigQuery; Azure cost exports) — console dashboards don't
  answer real questions; tooling (Cost Explorer / Looker dashboards / Cloud
  Intelligence dashboards / third-party FinOps platforms; FOCUS-format exports for
  multi-cloud normalization) sits on top of the export.
- **Showback per team monthly, visible to the team and its management.** Chargeback
  only when the org's accounting supports it; showback captures most of the
  behavioral effect.
- **Kubernetes needs its own allocation layer** (OpenCost or provider cost
  allocation for EKS/GKE/AKS): the cluster is one line on the bill but many
  tenants; per-namespace/label cost with idle-cost assignment, or your "platform"
  line hides everyone's waste.
- Budgets with alerts on every account — including (especially) sandboxes; a
  forgotten sandbox GPU instance is a classic four-figure surprise.

## 2. The big levers, in order of typical yield

1. **Delete idle.** Unattached volumes/IPs, stopped-but-billed instances, idle LBs
   and NAT gateways, empty clusters, dev environments running nights/weekends
   (schedule them off — ~65% off for 12x5 usage), stale snapshots, never-queried
   logs at premium retention. Run an idle-sweep report monthly; auto-reap in
   sandbox.
2. **Rightsize.** Use provider recommenders (Compute Optimizer / GCP recommender /
   Azure Advisor) and utilization data; act on the recs (the finding is usually not
   "no data" but "recommendations ignored for a year"). In K8s, requests are the
   cost driver — requests >> usage bills you for air ([rules/04](04-compute-selection.md)). Also rightsize
   storage: gp2→gp3-class migrations, overprovisioned IOPS, premium tiers on dev
   disks.
3. **Commitment discounts for the stable floor.** Measure a baseline over ≥ 1
   quarter, then cover ~60–80% of it with Savings Plans / Committed Use Discounts /
   Reservations (start with compute-flexible commitments; instance-pinned only for
   truly static fleets). Review coverage and utilization quarterly. Committing to
   an unoptimized baseline locks in waste — rightsize first, commit second.
4. **Spot/preemptible for interruption-tolerant work** (batch, CI, stateless
   horizontally-scaled services with headroom): steep discounts in exchange for
   reclaim. Requirements: graceful SIGTERM handling, checkpointing for long jobs,
   diversified instance types, and never for singleton stateful workloads.
5. **Storage lifecycle** ([rules/05](05-data-storage.md)): tiering + expiry + multipart abort. Logs and
   backups are the classic unbounded growers.
6. **Architecture-level moves** (the biggest but slowest lever): serverless for
   spiky loads, managed containers instead of an underutilized K8s cluster,
   batch aggregation instead of per-event processing, caching/CDN offload of
   origin traffic, ARM-based instances (Graviton/Axion/Cobalt-class) for
   compatible workloads.

## 3. The traps: egress and per-GB processing

Data transfer is the bill's dark matter — invisible in design diagrams, dominant in
some bills.

- **Egress to internet** bills per-GB; **cross-region** per-GB; **cross-AZ**
  typically per-GB in both directions (AWS); same-AZ private traffic free. Know
  which arrows in your architecture diagram cost money.
- **NAT gateway processing:** NAT bills per-hour AND per-GB processed. The classic
  incident: high-volume traffic to object storage routed through NAT — fix with
  free gateway endpoints (S3/DynamoDB) or private endpoints; an interface endpoint's
  per-hour+per-GB is usually far below NAT data processing for the same flow.
  "NAT data processing > NAT hourly cost" on a bill = misrouted traffic, go look.

```hcl
# GOOD: S3 gateway endpoint — removes S3 traffic from NAT, costs nothing
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.eu-west-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
}
# BAD: no endpoint — every GET/PUT from private subnets pays NAT per-GB processing
```
- **Cross-AZ chatter:** chatty service meshes, K8s services hopping zones
  (use topology-aware routing for high-volume internal traffic), DB replicas
  crossing AZs by design (fine — that one's purchased availability).
- **CDN as cost control:** CDN egress rates undercut origin egress and absorb
  origin compute; cache-hit ratio is a cost metric ([rules/03](03-networking.md) §9).
- Cross-cloud / to-on-prem flows: per-GB both directions adds up — co-locate
  chatty components; move compute to data, not data to compute.
- Watch per-request pricing at volume: KMS calls (use bucket keys/data-key
  caching), object-storage PUT/GET on tiny-object workloads (aggregate), LB LCU
  dimensions, log ingestion per-GB (see [sota-observability](../../sota-observability/SKILL.md) for telemetry cost
  discipline).

## 4. Unit economics

- Absolute spend is noise; **cost per unit of value** (per request, per active
  user, per tenant, per job, per GB processed) is signal. Rising spend with flat
  unit cost is growth; flat spend with rising unit cost is decay.
- Pick 1–3 unit metrics per service, compute monthly from the billing export +
  usage metrics, trend them on the team dashboard next to latency/error SLOs.
- Per-tenant cost matters for pricing and abuse: a tenant whose serving cost
  exceeds their revenue is a business bug; meter the expensive dimensions
  (storage, egress, compute-heavy API calls) per tenant where the architecture
  allows.

## 5. Anomaly detection and guardrails

- Enable provider anomaly detection (AWS Cost Anomaly Detection, GCP/Azure
  anomaly alerts) with alerts routed to the owning team, not a central inbox that
  rubber-stamps.
- Budgets: hard caps where the platform supports enforcement (sandbox), alert
  thresholds (50/80/100% forecast) elsewhere.
- Architectural cost-bombs need *technical* caps, not just alerts: autoscaling
  max sizes, function concurrency caps, log ingestion quotas, lifecycle rules.
  An alert fires after the money is gone; a cap prevents it. Recursive patterns
  (function writing to the bucket that triggers it; log-processing that logs)
  deserve explicit review.

## 6. Cost in PR review for infra changes

- Infra PRs state expected cost delta. Automate the estimate (Infracost or
  equivalent in CI — wiring belongs to [sota-devsecops](../../sota-devsecops/SKILL.md)) so the number appears in
  review; reviewer checks the number like they check a migration.
- Cost review prompts for any infra change: What's the monthly steady-state? What
  scales with traffic, and what's the cap? What data crosses AZ/region/internet
  boundaries? What's the lifecycle/teardown story? Spot/commitment applicable?
- New-resource definition of done includes: tags ([rules/01](01-org-accounts-governance.md)), lifecycle/expiry,
  autoscale caps, and an owner who will see its cost line.

## 7. Operating cadence

- Monthly: showback review per team; idle-sweep report; anomaly postmortems.
- Quarterly: commitment coverage/utilization review; rightsizing batch; unit-cost
  trend review; renegotiate/retier support plans as spend grows.
- Cost incidents get lightweight postmortems like outages: what spent, why no
  cap, which control was missing.

## Audit checklist

- [ ] Billing export to a queryable store exists and is used (ask for the last
      analysis it answered); dashboards per team; showback reviewed with each team
      monthly (§1, §7).
- [ ] Cost-allocation tags activated; >90% of spend attributable to a team/service;
      shared-cost split rule documented; K8s per-namespace allocation in place (§1).
- [ ] Budgets + anomaly alerts on every account, routed to owners; sandbox has
      hard caps/auto-reap; anomalies and cost incidents get lightweight postmortems
      (§1, §5, §7).
- [ ] Idle inventory near zero: unattached volumes/IPs, idle LBs/NAT, off-hours
      schedules for non-prod (check a Tuesday-2am snapshot of dev spend); idle-sweep
      report runs monthly (§2, §7).
- [ ] Rightsizing recommender findings reviewed within last quarter; K8s
      requests-vs-usage gap measured and bounded (§2, §7).
- [ ] Commitment coverage 60–80% of stable baseline; utilization > 90%; coverage
      reviewed quarterly; no commitments bought against un-rightsized baseline (§2, §7).
- [ ] Spot used for batch/CI/stateless where tolerable (with SIGTERM handling);
      justification where it is not (§2).
- [ ] No NAT-processing-dominated bills (gateway/private endpoints for high-volume
      service traffic); cross-AZ/region flows known and intentional; CDN hit
      ratio tracked; per-request lines at volume (KMS calls, tiny-object PUT/GET, LB
      LCUs, log ingestion) reviewed (§3).
- [ ] Storage lifecycle rules on logs/backups/buckets ([rules/05](05-data-storage.md)); log ingestion
      quotas/retention tiers set (§2).
- [ ] Unit-cost metrics defined and trended for the top services; expensive dimensions
      metered per tenant where the architecture allows (§4).
- [ ] Autoscale maxes, concurrency caps, and quota ceilings set on elastic
      resources (the bill cannot scale unbounded); recursive triggers (a function
      writing to the bucket that triggers it, log processing that logs) reviewed (§5).
- [ ] Infra PRs carry an automated cost-delta estimate (Infracost or equivalent) in
      review (sample recent PRs for evidence); new resources ship with tags,
      lifecycle/expiry, autoscale caps and an owner (§6).
