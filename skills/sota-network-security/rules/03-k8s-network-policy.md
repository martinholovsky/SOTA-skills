# 03 — Kubernetes Network Policy Depth

Scope: Kubernetes `NetworkPolicy`, `CiliumNetworkPolicy` (CNP/CCNP), the namespaced default-deny
pattern (ingress AND egress), the "default-deny that isn't" trap, the cluster-scoped
AdminNetworkPolicy / BaselineAdminNetworkPolicy (ANP/BANP) API, L7 + identity-based policy,
DNS-aware egress, egress gateways, and Hubble flow visibility. Examples here assume a **Cilium**-based cluster (e.g. Talos K8s + Cilium).

Where this sits: **sota-kubernetes** owns admission/RBAC and *that NetworkPolicy is admitted and the
CNI is wired*; this skill owns the policy *content and depth*. sota-cloud-infrastructure rules/03
owns the cluster's VPC/subnet/IPAM. sota-detection-engineering consumes Hubble flows.

Verified (2026-07): Cilium fully implements the upstream `networking.k8s.io/v1` NetworkPolicy and
adds L7 via Envoy — run the latest stable patch and verify the current release with a quick search
at time of use (the 2026 patch train fixed policy-bypass CVEs; see §4). The sig-network working
group merged ANP+BANP into a single **`ClusterNetworkPolicy` CRD at
`policy.networking.k8s.io/v1alpha2`** (Oct 2025; a `tier` field selects Admin vs Baseline) — still
ALPHA, out-of-tree; ANP/BANP `v1alpha1` remain usable at v0.1.7. Pin behavior; don't assume GA
semantics.

---

## 1. The two failure modes this file exists to kill

1. **No policy at all** — Kubernetes is allow-all by default. A namespace with zero NetworkPolicies
   lets every pod talk to every other pod, cluster-wide. Each such namespace is a flat segment.
2. **The "default-deny that isn't"** — a baseline policy that *looks* restrictive but effectively
   allows all intra-cluster traffic (e.g. an allow-from `namespaceSelector: {}` matching every
   namespace, or an egress allow to `0.0.0.0/0`, or a "deny" policy that only covers ingress while
   egress stays open). This is more dangerous than no policy because it reads as "we're covered."

**R1 — Always verify default-deny empirically.** Don't trust the policy's name or that one exists.
Probe:

```bash
# From an unrelated namespace, traffic to a target must be REFUSED if default-deny works.
kubectl -n scratch run probe --rm -it --image=nicolaka/netshoot --restart=Never -- \
  sh -c 'curl -sm3 http://target.othernamespace:8080 && echo LEAKED || echo denied'
# Egress test: can a pod reach the internet when it shouldn't?
kubectl -n payments exec deploy/api -- sh -c 'curl -sm3 https://example.com && echo EGRESS_OPEN'
```

## 2. The namespaced default-deny pattern (ingress AND egress)

**R2 — Every namespace gets a default-deny for BOTH directions, then explicit allows.** An
ingress-only default-deny leaves egress wide open (free C2/exfil — see §5 and rules/05).

```yaml
# GOOD: per-namespace default-deny, both directions
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny, namespace: payments }
spec:
  podSelector: {}            # all pods in the namespace
  policyTypes: [Ingress, Egress]   # BOTH — the common mistake is omitting Egress
  # no ingress/egress rules => deny all in both directions
```

Then add narrow allows. Note the subtle trap below — it is the "default-deny that isn't":

```yaml
# BAD: reads as a policy, but allows the whole cluster in.
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress:
  - from: [{ namespaceSelector: {} }]   # {} matches EVERY namespace = allow-all ingress
```

**R3 — Allow DNS explicitly, or default-deny egress breaks everything.** Once egress is denied,
pods can't resolve names. Allow egress to kube-dns/CoreDNS on 53 (and prefer the L7 DNS-aware form
in §5 so you also constrain *which* names resolve):

```yaml
egress:
- to: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } } }]
  ports: [{ protocol: UDP, port: 53 }, { protocol: TCP, port: 53 }]
```

## 3. Standard NetworkPolicy: powers and limits

`networking.k8s.io/v1` NetworkPolicy is namespaced, additive (allows union; deny is the absence of
allow), and selects by pod labels, namespace labels, or `ipBlock`. Limits to know:
- **No L7** (no HTTP path/method), **no FQDN** (only IPs/CIDRs in `ipBlock`), **no explicit deny**
  (no priority/deny — you express deny by *not* allowing), **no cluster-scoped** baseline.
- `ipBlock` matches pod IPs too — be careful that a broad `ipBlock` doesn't unintentionally re-open
  intra-cluster paths.

For the user's Cilium cluster, prefer **CiliumNetworkPolicy** for anything needing identity-based,
L7, FQDN, or cluster-wide policy; keep plain NetworkPolicy for portable baselines.

## 4. CiliumNetworkPolicy: identity, L7, FQDN

**R4 — Use identity-based selectors and L7 where they tighten the rule.** Cilium enforces by
*identity* (derived from labels) in eBPF, not by IP, so policy survives churn.

```yaml
# GOOD: identity + L7 — api may call billing ONLY on POST /charge
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata: { name: api-to-billing, namespace: payments }
spec:
  endpointSelector: { matchLabels: { app: billing } }
  ingress:
  - fromEndpoints: [{ matchLabels: { app: api } }]
    toPorts:
    - ports: [{ port: "8080", protocol: TCP }]
      rules:
        http: [{ method: "POST", path: "/charge" }]
```

Beware the **`world` / `reserved:world` entity** and `toCIDR: 0.0.0.0/0` — allowing them on a
sensitive endpoint is the Critical over-broad finding from rules/02 (the real OpenBao/Grafana/
registry-from-`world` case). Audit every CNP for `world`, `all`, `0.0.0.0/0`.

**Patch floor (2026 CVEs):** Cilium below **1.19.4 / 1.18.10 / 1.17.16** has known
policy-bypass/hijack CVEs that undermine this file's guarantees — CVE-2026-33726 (L7 proxy could
bypass NetworkPolicy for same-node traffic; fixed 1.19.2/1.18.8/1.17.14), CVE-2026-49445 (Envoy
admin socket exposure with L7 enabled — info disclosure/cluster disruption; fixed 1.19.2), and
CVE-2026-53935 (`CiliumLocalRedirectPolicy` `addressMatcher` cross-namespace service-traffic
hijack; fixed 1.19.4). Check the running version against Cilium's security advisories.

## 5. Egress control & DNS-aware egress

**R5 — Egress is first-class; allowlist by FQDN, not open `0.0.0.0/0`.** Cilium's DNS-aware policy
snoops DNS to map allowed names to IPs, so you can allowlist destinations by domain:

```yaml
# GOOD: pod may resolve+reach only api.stripe.com; everything else denied
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata: { name: egress-stripe-only, namespace: payments }
spec:
  endpointSelector: { matchLabels: { app: billing } }
  egress:
  - toEndpoints: [{ matchLabels: { k8s:io.kubernetes.pod.namespace: kube-system, k8s-app: kube-dns } }]
    toPorts:
    - ports: [{ port: "53", protocol: UDP }]
      rules: { dns: [{ matchPattern: "*.stripe.com" }] }   # constrain WHICH names resolve
  - toFQDNs: [{ matchName: "api.stripe.com" }]
    toPorts: [{ ports: [{ port: "443", protocol: TCP }] }]
```

**R6 — Block the cloud metadata endpoint from pods.** `169.254.169.254` (and `fd00:ec2::254`) is
the SSRF pivot to cloud credentials. Default egress should not include `169.254.0.0/16`; if a
broad egress exists, explicitly deny the link-local range. This is the egress side of the SSRF chain
(sota-code-security rules/01 owns the app-side SSRF; rules/05 here covers the edge/egress side).
On the user's on-prem Talos cluster there's no IMDS, but the habit prevents the finding if they
ever burst to cloud — and IMDSv2 (token-required, account-enforceable, default on new EC2 types)
is the cloud-side mitigation (sota-cloud-infrastructure).

**R7 — Egress gateways for stable, inspectable egress.** When external partners allowlist your
source IP, or you want all egress through one inspected choke point, use a **Cilium egress gateway**
(SNAT cluster egress to fixed node IPs). This pairs with FQDN policy: gateway = where you route and
log, FQDN policy = what's allowed.

## 6. Cluster-scoped baselines: ANP / BANP (alpha — handle with care)

**R8 — Use ANP/BANP for cluster-wide guardrails the way RBAC uses ClusterRoles — but pin the alpha.**
- **AdminNetworkPolicy (ANP)**: cluster-scoped, *priority-ordered*, supports explicit **Deny/Allow/
  Pass** (unlike namespaced NetworkPolicy). Use for non-overridable org rules: "no namespace may
  egress to the metadata IP," "deny all cross-tenant traffic." Evaluated *before* NetworkPolicy.
- **BaselineAdminNetworkPolicy (BANP)**: a single cluster-scoped default (e.g. cluster-wide
  default-deny) that namespaced NetworkPolicy can *override*. Use it to make default-deny the
  cluster baseline so a new namespace isn't accidentally allow-all.

Status: the `policy.networking.k8s.io` CRDs are **alpha**, out-of-tree. Since Oct 2025 ANP+BANP
are consolidated into **`ClusterNetworkPolicy` (v1alpha2)** — `tier: Admin` replaces ANP,
`tier: Baseline` replaces BANP — and the working group will base the beta on ClusterNetworkPolicy,
so plan migration toward it. Cilium and others implement subsets; **verify your CNI's support
matrix and pin versions** — don't build a control you can't test. Until it's solid in your
cluster, a Cilium *clusterwide* policy (CCNP) achieves the cluster-scoped default-deny today.

```yaml
# Cilium clusterwide default-deny baseline (works today on the user's stack)
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata: { name: default-deny-all }
spec:
  endpointSelector: {}
  ingress: [{ }]   # empty rule list under enableDefaultDeny => deny; pair with explicit allows
  egress: [{ }]
```

## 7. Hubble flow visibility

**R9 — Turn on Hubble; you cannot secure flows you can't see.** Hubble gives L3/4 and L7 flow
visibility and is how you (a) verify a policy actually denies, (b) author tight policies from
observed traffic, (c) feed network telemetry to detection (sota-detection-engineering owns the
detection content — DNS-exfil, anomalous flows). Export flows; don't leave Hubble UI-only.

```bash
hubble observe --namespace payments --verdict DROPPED   # what's being denied (tighten or fix)
hubble observe --to-fqdn '*.metadata*'                  # anyone reaching metadata-ish names?
hubble observe --from-pod payments/api --protocol http  # author L7 policy from real traffic
```

## 8. Cluster mesh (multi-cluster)

**R10 — Cluster mesh extends *identity and policy*, not a flat L3.** With Cilium Cluster Mesh,
identities and CNP selectors span clusters — but that means a too-broad cross-cluster allow now has
multi-cluster blast radius. Apply the same default-deny + identity-scoped allows across the mesh;
audit cross-cluster policies for `world`/wildcard exactly as single-cluster.

## Audit checklist

- [ ] Does *every* namespace have a default-deny for **both** Ingress and Egress? List namespaces
      with no NetworkPolicy/CNP: those are flat segments.
- [ ] Is any "default-deny" actually allow-all? Hunt `namespaceSelector: {}`, `podSelector: {}` on
      the *from* side, missing `Egress` in `policyTypes`, `0.0.0.0/0`/`world`/`reserved:world` in
      CNPs. Then **probe** cross-namespace and egress reachability to confirm.
- [ ] Is DNS allowed explicitly under default-deny egress (else everything breaks), and is the DNS
      policy constraining *which* names resolve?
- [ ] Is egress FQDN-allowlisted for sensitive namespaces, not open to `0.0.0.0/0`?
- [ ] Is `169.254.0.0/16` (metadata) blocked from pod egress?
- [ ] Are sensitive services (secrets/DB/registry/admin) selected by identity and reachable only
      from declared callers? Prove with Hubble + a probe.
- [ ] Is there a cluster-scoped default-deny baseline (BANP/ANP if stable, else
      CiliumClusterwideNetworkPolicy) so new namespaces aren't allow-all?
- [ ] Is Hubble enabled and flows exported to detection?
- [ ] ANP/BANP/ClusterNetworkPolicy usage: is the alpha API status pinned, CNI support verified,
      and migration to `ClusterNetworkPolicy` (v1alpha2, tiered) planned?
- [ ] Is Cilium at/above the 2026 CVE-fix floor (1.19.4 / 1.18.10 / 1.17.16) and checked against
      current security advisories?
