# 04 — Compute Selection: Serverless, Containers, Kubernetes, VMs

Scope: choosing the compute layer, serverless patterns, Kubernetes architecture
essentials. Container image hardening: see sota-sandboxing. Deploy pipelines and
GitOps: see sota-devsecops.

## 1. The decision tree — simplest thing that meets requirements

Work down; stop at the first fit. Each step down adds operational surface you must
staff.

1. **Fully managed / no compute at all.** Static site → object storage + CDN. API
   that's pure CRUD → consider managed API + database integrations before writing
   glue compute.
2. **Serverless functions** (Lambda / Cloud Functions / Azure Functions) when:
   event-driven or spiky traffic, short tasks (AWS Lambda caps at 15 min/invocation,
   10 GB memory — verify other providers' current limits), team wants zero
   infrastructure ops, per-request pricing beats idle provisioning. Wrong when:
   long-lived connections (websockets at scale), sustained high constant load
   (always-on container is cheaper), heavy local state, > a few GB memory/GPU needs,
   or latency budgets that can't absorb cold starts. Two AWS options shift these
   break-evens: Lambda Managed Instances (GA since re:Invent 2025) runs functions on
   EC2-backed capacity with multi-request execution environments and Savings
   Plans/RI pricing — steady-load functions may now beat migrating to containers
   (decide with measured cost numbers); Lambda MicroVMs (2026) add suspendable
   isolated sandboxes up to 8 h for code-execution/agent workloads past the 15-min
   cap.
3. **Containers on managed runners** (Cloud Run / Fargate-on-ECS / Azure Container
   Apps) — **the default for standard web services and workers in 2026.** You bring
   an image; provider runs, scales, patches hosts. Choose when: HTTP services,
   background workers, anything that fits "stateless container + autoscale" without
   needing the K8s API.
4. **Kubernetes (managed: EKS/GKE/AKS)** only with a written justification, e.g.:
   you need the ecosystem (operators, service mesh, custom controllers, ML platforms
   like Ray/Kubeflow), multi-team platform with namespace tenancy, portability is a
   real requirement (not a vibe), or workload shapes managed runners can't express
   (DaemonSets, stateful sets with custom topology, GPU bin-packing). **And** you have
   ≥ 1 FTE-equivalent of platform capacity for upgrades (3 minor releases/year,
   ~14-month support window — being > 2 versions behind is an audit finding).
5. **VMs** for: lift-and-shift, licensed/legacy software, kernel/hardware control,
   stateful systems not yet on managed equivalents. VMs demand the patching, AMI
   pipeline, and autoscaling-group discipline everything above gives you for free.

Anti-pattern: **resume-driven Kubernetes** — a 5-service startup on a 3-node cluster
spends platform time it doesn't have; Cloud Run/Fargate would carry it to millions of
requests/day. Reverse anti-pattern: 40 microservices duct-taped across function
sprawl when the team actually needs an orchestrator.

Mixed estates are normal: functions for event glue, managed containers for services,
one K8s cluster for the platform workloads that justify it. Pick per workload, not
per company.

## 2. Serverless patterns

- **Idempotent handlers, always.** Every major trigger (queues, streams, schedulers)
  delivers at-least-once. Key side effects on an idempotency key (request/message
  ID) stored conditionally (DynamoDB conditional put / Firestore txn) — dedupe at
  the effect, not the entry point.
- **DLQs/failure destinations on every async consumer** (queue redrive policies,
  Lambda failure destinations, Pub/Sub dead-letter topics) with alerting on DLQ
  depth, and a documented redrive procedure. An async function without a DLQ deletes
  failures silently.

```hcl
# GOOD: queue with bounded retries into an alarmed DLQ
resource "aws_sqs_queue" "orders" {
  name                       = "orders"
  visibility_timeout_seconds = 90 # > 6x consumer timeout, per AWS guidance
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.orders_dlq.arn
    maxReceiveCount     = 5 # then it parks, visibly, instead of looping forever
  })
}
# BAD: no redrive_policy — poison messages retry until expiry, then vanish
```
- **Cold starts:** keep packages small, init outside the handler reused across
  invocations, avoid VPC-attach unless needed (it's cheap now but still adds
  config/ENI considerations), use provisioned concurrency / min instances only for
  measured latency-critical paths (it converts serverless pricing into
  always-on pricing — decide with numbers).
- **Concurrency is a real limit and a real weapon.** Account/regional concurrency is
  shared: one runaway function can starve the rest — set per-function reserved
  concurrency caps for anything triggered by unbounded sources. Also use concurrency
  caps to protect downstreams (DB connection limits — or use RDS Proxy/serverless
  drivers).
- **Orchestration: state machines for state, code for logic.** Multi-step workflows
  with retries/waits/human-approval/sagas → Step Functions / GCP Workflows / Azure
  Durable Functions, or AWS Lambda durable functions (GA Dec 2025: checkpointed
  steps/waits inside Lambda code, suspensions up to a year) — not hand-rolled
  retry loops sleeping inside a 15-minute invocation. If you're paying a function to
  `sleep()`, you chose the wrong orchestrator.
- Timeouts tuned to p99 + margin, not max — a 15-minute timeout on a 2-second
  function turns retries of a hung dependency into a cost and concurrency incident.
- Event contracts versioned; consumers tolerant readers (see sota-api-design).

## 3. Kubernetes architecture essentials

(Current upstream: v1.36, supported window v1.34–v1.36 as of mid-2026 — the latest
three minors; v1.33 reached EOL ~2026-06; verify your managed-provider version
offerings at design time.)

- **Managed control plane only** (EKS/GKE/AKS). Self-hosted control planes need a
  dedicated platform team and a reason.
- **Cluster topology:** separate prod and non-prod clusters (cheaper than perfect
  multi-tenancy isolation); within a cluster, namespace-per-team/service with
  ResourceQuotas + LimitRanges. Regional/multi-AZ control plane and node placement
  for prod.
- **Node pools by workload shape:** general on-demand pool for baseline,
  spot/preemptible pools for interruption-tolerant work (taint them; workloads
  opt in via tolerations), dedicated pools for GPU/memory-heavy. Prefer
  provider-managed provisioning (Karpenter on EKS, GKE NAP/Autopilot, AKS node
  autoprovisioning) over hand-tuned static ASGs.

### Autoscaling — three layers, configure all deliberately

| Layer | Tool | Rule |
|---|---|---|
| Pod count | HPA (or KEDA for event/queue-driven scaling to zero) | Scale on a metric that tracks load (RPS, queue depth, CPU as fallback); set sane min/max; behavior stabilization to stop flapping |
| Pod size | VPA / in-place resize | In-place pod resize is GA since v1.35 (resize CPU/mem without restart); use VPA in recommendation mode at minimum to ground requests in reality |
| Nodes | Cluster autoscaler / Karpenter / Autopilot | Must be on — HPA without node scaling = Pending pods at the worst time; set max nodes (cost cap) |

Don't point HPA and VPA at the same metric (CPU) in active mode simultaneously —
they fight; HPA on a throughput metric + VPA for sizing is the stable combo.

### Workload discipline — every production manifest

```yaml
# GOOD: the minimum acceptable production Deployment fragment
resources:
  requests: { cpu: 250m, memory: 512Mi }   # measured, not guessed; scheduler currency
  limits:   { memory: 512Mi }              # memory limit = request (predictable OOM);
                                           # CPU limit often omitted to avoid throttling — decide per workload
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector: { matchLabels: { app: checkout } }
---
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 2          # or maxUnavailable — but NEVER minAvailable == replicas
  selector: { matchLabels: { app: checkout } }
```

- **No requests = no capacity math.** Missing requests is an audit finding: the
  scheduler bin-packs blind, evictions hit randomly, autoscaling lies.
- **PDB on everything with > 1 replica** — node upgrades and spot reclaim drain
  nodes; without PDBs, voluntary disruption takes out all replicas at once. A PDB
  requiring all replicas (`minAvailable` = replica count) blocks node upgrades
  forever — equally a finding.
- **Topology spread across zones** (and hosts) for anything claiming HA; replicas
  on one node are one failure domain.
- Probes: readiness ≠ liveness; liveness must not check dependencies (dependency
  blip → restart storm).
- Graceful shutdown: handle SIGTERM, `terminationGracePeriodSeconds` ≥ drain time,
  preStop hook to de-register before exit.

### Cluster operations

- **Upgrade cadence is a standing commitment:** upstream ships 3 minors/year with a
  ~14-month support window; managed providers add extended-support fees for
  laggards. Track ≤ 1 version behind your provider's default; test upgrades in
  non-prod with the same add-ons.
- Add-on sprawl is the hidden K8s cost: every controller (mesh, ingress, cert
  manager, secrets operator) is software you now operate. Adopt the minimal set;
  prefer provider-managed add-on variants.
- Cluster API endpoint: private (or IP-restricted) for prod; authn via cloud IAM
  (no static kubeconfig certs in CI — see sota-devsecops); RBAC mapped to IdP groups.

## 4. VMs (when you must)

- VMs live in autoscaling groups / MIGs / VMSS even at count=1 (self-healing,
  recreate-from-image), built from pipeline-produced images (Packer or provider
  image builder), no SSH mutation in place — access via SSM/IAP for debugging only.
- Patch via image rebake + rolling replace, not in-place fleet patching.
- Stateful VM workloads: pin per-AZ, snapshot schedules (rules/05), and a written
  failover story — an ASG won't save your database.

## Audit checklist

- [ ] Compute choice per workload has a justification; K8s clusters have a written
      reason + named platform owner; no orchestrator running 3 trivial services.
- [ ] Serverless: every async consumer has DLQ + alert + redrive runbook; handlers
      idempotent (check for idempotency keys on at-least-once triggers).
- [ ] Function timeouts/memory tuned vs p99; reserved concurrency caps on
      unbounded-trigger functions; provisioned concurrency justified by latency data.
- [ ] Multi-step workflows in a workflow engine (or durable functions), not
      sleep/retry loops in handler code.
- [ ] K8s version within provider standard support, ≤ 1 behind default; upgrade
      runbook exists and was exercised.
- [ ] All prod pods have resource requests; memory limits set; no
      requests-vs-usage gap > 2x sustained (check VPA recs / metrics).
- [ ] PDBs present on multi-replica workloads and none block drains
      (minAvailable < replicas).
- [ ] Topology spread or anti-affinity across zones on HA-claimed services.
- [ ] All three autoscaling layers configured; cluster/node autoscaler max set;
      spot pools tainted with tolerating workloads only.
- [ ] Probes sane (liveness dependency-free); SIGTERM handled; grace period ≥ drain.
- [ ] Cluster API endpoint private/IP-restricted; RBAC via IdP groups; quotas per
      namespace.
- [ ] VMs in ASGs/MIGs from pipeline-built images; no snowflakes (check instance
      age + provenance); no inbound SSH from internet.
