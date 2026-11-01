# 06 — Workloads, Scheduling Availability & Multi-Tenancy

Scope: the platform-level properties of workloads that affect **availability and tenant
isolation** — resource requests/limits as QoS (not isolation), PodDisruptionBudgets,
topology spread / anti-affinity, priority/preemption, the namespace-as-soft-boundary
reality and when you need hard multi-tenancy, and where Secrets live. **Pod isolation
mechanics (securityContext, seccomp, runtime classes) are [`sota-sandboxing`](../../sota-sandboxing/SKILL.md) ([rules/03](../../sota-sandboxing/rules/03-containers-microvms.md));**
this file references the *isolation decision* but does not re-spec the pod fields. Secret
*backends* are [`sota-secrets-management`](../../sota-secrets-management/SKILL.md); this file states the etcd-encryption requirement
and points there.

---

## 1. Resource requests/limits — availability + QoS, NOT isolation

Requests/limits govern scheduling and the cgroup budget; they are an **availability and
fairness** control, not a security boundary (a shared kernel means a noisy/hostile neighbor
can still affect others — real isolation is [`sota-sandboxing`](../../sota-sandboxing/SKILL.md)'s node/runtime story).

- **Set both `requests` and `limits`** for CPU and memory on every container.
  - `requests` drive scheduling (the scheduler packs to requested capacity).
  - **Memory `limit` is a hard kill**: exceed it → OOMKill. Set it from real usage +
    headroom; too low = crashloop, too high = node memory overcommit and node-level OOM
    that evicts *other* pods.
  - **CPU `limit` throttles** (CFS), it doesn't kill — and aggressive CPU limits cause
    latency cliffs. Many shops set CPU *requests* and omit CPU *limits* (or set generous
    ones) to avoid throttling while keeping scheduling fairness; decide deliberately.
- **QoS classes** follow from this: **Guaranteed** (requests == limits for all
  containers) is evicted last; **Burstable** (requests < limits) next; **BestEffort** (none
  set) is evicted first under node pressure. Critical workloads should be Guaranteed.
- **A pod with no requests is a scheduling and eviction hazard** — it can be packed onto a
  full node and is first to be evicted. Enforce limits/requests at admission ([`rules/03`](03-admission-policy.md))
  and set namespace **`LimitRange`** (defaults) + **`ResourceQuota`** (caps) so a tenant
  can't starve the cluster or schedule unbounded pods.

## 2. Disruption, spread & priority — staying up

- **PodDisruptionBudget (PDB)** on every multi-replica workload (a missing one on a *critical* workload is the Medium finding): caps how many
  pods *voluntary* disruptions (node drain/upgrade) may take down at once
  (`minAvailable`/`maxUnavailable`). Without a PDB, a node drain during an upgrade can take
  all replicas at once → outage. (PDBs don't protect against involuntary disruptions like
  node crashes — that's replicas + spread.)

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 2                      # or maxUnavailable: 1
  selector: { matchLabels: { app: api } }
```

- **Topology spread constraints** spread replicas across zones/nodes so one failure domain
  loss doesn't kill the service:

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector: { matchLabels: { app: api } }
```

- **Pod anti-affinity** (`podAntiAffinity`) keeps replicas off the same node — use
  `requiredDuringScheduling` for hard, `preferred` for soft. Topology spread is usually the
  cleaner modern tool; don't double-specify conflicting rules.
- **PriorityClass & preemption**: assign higher `priorityClassName` to platform-critical
  pods so they preempt lower-priority workloads under contention. Beware: a too-high
  default priority on tenant workloads lets a tenant preempt platform pods — reserve top
  priorities for the platform, and consider `preemptionPolicy: Never` for non-urgent batch.

## 3. Multi-tenancy — namespace is a SOFT boundary

The most common dangerous assumption: **a Namespace is not a security boundary.** It scopes
names and RBAC, but tenants in different namespaces still share **the same nodes, kernel,
control plane, CNI, and CRDs**. A container escape, a kernel CVE, a node-level secret read,
or a cluster-scoped resource crosses namespaces. So:

- **Soft multi-tenancy (namespace-per-tenant)** is appropriate only for **mutually trusted
  or low-sensitivity** tenants (teams in one org). Even then, enforce per-namespace: RBAC
  isolation ([`rules/02`](02-rbac-serviceaccounts.md)), `ResourceQuota`/`LimitRange`, PSA `restricted` ([`rules/03`](03-admission-policy.md)), and
  **default-deny NetworkPolicy** — note the requirement here, but NetworkPolicy/CNI depth
  is [`sota-network-security`](../../sota-network-security/SKILL.md).

- **When you need HARD multi-tenancy** (untrusted tenants, strong compliance/regulatory
  separation, hostile-neighbor model), namespaces are insufficient. Escalate the boundary:
  - **Separate clusters per tenant** — the strongest, simplest-to-reason-about boundary;
    no shared control plane/etcd. Default for genuinely untrusted tenants.
  - **vCluster** (virtual clusters) — each tenant gets its own API server/control plane
    syncing into a host namespace; far stronger control-plane isolation than a namespace,
    cheaper than separate clusters. Good middle ground; the *data plane* still shares host
    nodes unless combined with node isolation.
  - **Node isolation** — dedicate node pools per tenant (taints/tolerations + node
    affinity) so workloads don't co-reside; combine with a **stronger runtime boundary
    (gVisor/Kata)** for untrusted code — this is [`sota-sandboxing`](../../sota-sandboxing/SKILL.md) ([rules/01](../../sota-sandboxing/rules/01-isolation-boundaries.md) boundary
    choice, [rules/03](../../sota-sandboxing/rules/03-containers-microvms.md) runtime classes). Co-residency of untrusted tenants on a shared kernel
    is the thing node isolation + microVM/gVisor exists to fix.

  State the tenancy model and its boundary explicitly in design; "we use namespaces for
  isolation" against an untrusted tenant is a **High** finding.

## 4. Secrets in Kubernetes (platform view)

- **etcd encryption-at-rest with KMS v2 is mandatory** — K8s Secrets are base64, not
  encrypted, by default (full treatment in [`rules/01`](01-control-plane-etcd.md) §4).
- **Don't inject secrets as plain env vars** where avoidable — env is readable via
  `/proc`, crash dumps, `kubectl describe`, and child processes; prefer **mounted files**
  (projected/volume) and tools that support file-based secrets. (App-level secret handling
  is [`sota-secrets-management`](../../sota-secrets-management/SKILL.md).)
- **Use a real secrets workflow**: **ExternalSecrets Operator** (sync from Vault/cloud
  secret managers — [`sota-secrets-management` rules/02](../../sota-secrets-management/rules/02-storage-backends.md), and scope it per [`rules/05`](05-operators-crds-webhooks.md)),
  **sealed-secrets** (encrypt secrets safe to commit to git for GitOps), or the **Secrets
  Store CSI driver** (mount from an external store, optionally never landing in etcd). Pick
  per your GitOps model; the goal is that the source of truth is an encrypted store, not a
  plaintext manifest in git.
- **Restrict who can read Secrets** ([`rules/02`](02-rbac-serviceaccounts.md) §2.5) — `get`/`list secrets` is
  near-credential-equivalent. Audit it.

## Audit checklist

- [ ] Every container sets memory requests+limits and CPU requests (CPU limits a deliberate decision)? Critical workloads Guaranteed QoS? (`kubectl get pods -A -o json | jq '..|.resources? // empty'`) (§1)
- [ ] Namespaces have `ResourceQuota` + `LimitRange` (§1) so a tenant can't starve the cluster or schedule unbounded pods? (`kubectl get resourcequota,limitrange -A`)
- [ ] Multi-replica critical workloads have a PDB; PDB values won't block legitimate drains or allow full takedown? (`kubectl get pdb -A`) (§2)
- [ ] Topology spread / anti-affinity spreads replicas across zones/nodes (§2) (no single-node single-zone critical service)?
- [ ] PriorityClasses reserve top priorities for the platform (§2); tenants can't preempt platform pods?
- [ ] Tenancy model stated explicitly (§3): is "namespace" being relied on as a security boundary against untrusted tenants? (that's a High finding — escalate to vCluster / separate clusters / node isolation + gVisor/Kata per [sota-sandboxing](../../sota-sandboxing/SKILL.md))
- [ ] Soft-tenant namespaces enforce RBAC isolation (§3), quota, PSA restricted, and default-deny NetworkPolicy (depth → [sota-network-security](../../sota-network-security/SKILL.md))?
- [ ] Platform secrets (§4): etcd Secrets encrypted with KMS v2 ([rules/01](01-control-plane-etcd.md)); secrets mounted as files not env where possible; ESO/sealed-secrets/CSI used over plaintext-in-git ([sota-secrets-management](../../sota-secrets-management/SKILL.md))? Env-delivered Secrets: the `secretKeyRef` probe in [`sota-secrets-management` rules/02](../../sota-secrets-management/rules/02-storage-backends.md) §6.
- [ ] Secret read RBAC scoped and audited (§4) ([rules/02](02-rbac-serviceaccounts.md))?
