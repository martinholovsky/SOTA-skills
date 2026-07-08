# 04 — Service Mesh & mTLS / Internal Encryption

Scope: the plaintext-internal-traffic problem and how mesh/mTLS solves it structurally; choosing and
auditing a mesh (Istio sidecar vs ambient/ztunnel, Linkerd, Cilium service mesh); mTLS everywhere
(STRICT, not permissive-forever); mesh authorization policy; SPIFFE/SPIRE workload identity; and when
a mesh is overkill vs just using TLS.

Where this sits: **sota-identity-access** owns SPIFFE/SPIRE *issuance* and the workload-identity
trust domain; this skill consumes those identities for network authorization. rules/03 owns L3/4 CNI
policy; this file owns the L7/identity/encryption layer that complements it. sota-secrets-management
owns TLS private-key handling.

Verified (2026-07): **Istio ambient mode (ztunnel + waypoints)** reached **GA in Istio 1.24 (Nov
2024)** — sidecar and ambient are both production data planes today. **Linkerd** (CNCF Graduated)
added **SPIFFE identities and mesh expansion in 2.15** (Feb 2024). **SPIFFE/SPIRE** are CNCF
Graduated, production-ready. **Cilium** mTLS is now the **ztunnel integration** (per-node proxy
adopted from Istio ambient) — **Beta in 1.19, TCP-only** (UDP/other protocols aren't redirected),
enrolled per-namespace; the older out-of-band Mutual Authentication beta is disabled by default in
1.19. Pin exact versions against the projects' docs before committing.

---

## 1. The plaintext-internal-traffic problem

**R1 — Credentials and tokens on an unencrypted internal hop are a Critical finding.** The real
case: DB root credentials and JWTs flowing over `ws://` (and unencrypted DB protocol) across the pod
network. Anyone with a foothold on the network — a sniffing sidecar, a compromised node, a misrouted
pod — reads them. "It's internal" does not make plaintext safe (rules/01: location is not trust).

Symptoms to hunt: `http://`/`ws://` between services, DB connections without TLS, gRPC without TLS,
`mode: PERMISSIVE` in a mesh that's been "temporary" for months, app config trusting that the
network is private.

**R2 — Solve it structurally with mTLS, not per-app TLS plumbing.** You *can* terminate TLS in every
service, but that means every team correctly configures certs, validates peers, and rotates — which
fails in practice. A mesh (or Cilium mTLS) makes mutual TLS the *default transport* for all
service-to-service traffic, transparently, with automatic short-lived certs. The structural property:
plaintext becomes impossible, not merely discouraged.

## 2. mTLS everywhere — STRICT, not permissive-forever

**R3 — Drive mesh mTLS to STRICT; PERMISSIVE is a migration state, not a destination.** PERMISSIVE
accepts both mТLS and plaintext — useful while onboarding, but it means plaintext *still flows* and
an attacker can simply speak plaintext. Auditing a mesh that's been PERMISSIVE for a long time = the
plaintext problem is unsolved.

```yaml
# GOOD: Istio — STRICT mTLS mesh-wide (then per-workload exceptions if truly needed)
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata: { name: default, namespace: istio-system }
spec:
  mtls: { mode: STRICT }
```

Verify it's actually STRICT and enforced: send plaintext to a meshed workload and confirm it's
rejected (`kubectl exec ... curl http://svc` from an unmeshed pod must fail).

## 3. Workload identity (SPIFFE) is the foundation

**R4 — Authorization binds to cryptographic workload identity, not IP.** Mesh mTLS issues each
workload a short-lived identity — a **SPIFFE SVID** (`spiffe://trust-domain/ns/<ns>/sa/<sa>`) or
mesh-native cert. Authz policy then references *that identity*, so "only the api service may call
billing" survives pod churn and can't be spoofed by landing on the right IP. sota-identity-access
owns SPIFFE/SPIRE setup and the trust domain; here, ensure policies reference identities, not CIDRs.

## 4. Mesh authorization policy (the L7 PEP)

**R5 — mTLS proves *who*; authorization decides *what they may do*. You need both.** mTLS alone
authenticates peers but, by default, any authenticated workload can call any other. Add
deny-by-default authorization keyed on identity + L7 attributes:

```yaml
# GOOD: Istio — only the api SA may POST /charge on billing; default-deny otherwise
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata: { name: billing-allow-api, namespace: payments }
spec:
  selector: { matchLabels: { app: billing } }
  action: ALLOW
  rules:
  - from: [{ source: { principals: ["cluster.local/ns/payments/sa/api"] } }]
    to: [{ operation: { methods: ["POST"], paths: ["/charge"] } }]
# Pair with a default-deny (empty ALLOW selector or explicit DENY) so unlisted callers are refused.
```

Linkerd uses `Server` + `AuthorizationPolicy`/`MeshTLSAuthentication`; Cilium uses CNP L7 rules
(rules/03 §4) keyed on identity. Same principle: default-deny, identity-scoped, L7 where it tightens.

## 5. Choosing a mesh (or not)

**R6 — Don't deploy a mesh you don't need; don't hand-roll mTLS you can't maintain.** Decision:

| Situation | Choice |
|---|---|
| 1–3 services, simple topology | **Plain TLS** between them (or Cilium WireGuard node-to-node encryption) — a full mesh is overkill |
| Many services, need mTLS + L7 authz + telemetry, want it transparent | A mesh |
| Already on Cilium, want mTLS without a full mesh | **Cilium ztunnel mTLS** — per-node proxy, **Beta in 1.19, TCP-only, per-namespace enrollment**; pin-and-evaluate, and prefer Istio ambient or Linkerd where production mTLS is required today. Cilium **WireGuard** gives stable node-to-node encryption (no per-workload identity) |
| Want the lightest dedicated mesh, Kubernetes-only | **Linkerd** (simple, fast, Graduated, SPIFFE in 2.15) |
| Need the richest L7/traffic-management, multi-cluster, VM mesh | **Istio** — prefer **ambient mode** (ztunnel + waypoints, GA since 1.24) to avoid per-pod sidecar cost; sidecar mode still valid |

**R7 — Ambient vs sidecar (Istio).** Ambient splits the data plane: a per-node **ztunnel** handles
L4 mTLS for all pods (no sidecar injection, lower overhead), and **waypoint** proxies add L7
(authz, routing) only where needed. GA since 1.24. Prefer ambient for new rollouts to cut the
sidecar tax; the security properties (STRICT mTLS, identity-based authz) are the same — audit them
the same way.

**R8 — A mesh is not a substitute for L3/4 CNI policy.** Mesh mTLS+authz covers meshed,
TCP/HTTP traffic. CNI NetworkPolicy (rules/03) still default-denies for non-meshed pods, non-TCP
traffic, egress, and anything that bypasses the mesh (e.g. a pod talking straight to a DB outside
the mesh). Run both: CNI for the L3/4 floor, mesh for L7/identity. A mesh-only posture with
allow-all NetworkPolicy still has a flat L3 underneath.

## 6. Operational pitfalls

- **PERMISSIVE drift** (R3) — the top one. Track which namespaces are still permissive; treat
  long-lived PERMISSIVE as a High finding.
- **Authz default-allow** — mTLS on but no AuthorizationPolicy means any workload calls any other.
  Default-deny then allow.
- **mTLS bypass paths** — traffic that skips the mesh (hostNetwork pods, direct IP, ports the mesh
  doesn't capture, the DB outside the mesh). Hunt for unmeshed sensitive endpoints; cover them with
  CNI policy (rules/03).
- **Cert rotation = the mesh's job** — short-lived SVIDs auto-rotate; if you're manually managing
  mesh certs, something is wrong. Internal root/intermediate (your step-ca) feeds the mesh CA;
  rotate per rules/06.
- **Don't double-encrypt blindly** — if Cilium already encrypts transparently at L4 (WireGuard or
  ztunnel) and you add a full mesh on top, justify it; usually pick one transport-security layer.

## Audit checklist

- [ ] Hunt plaintext on internal hops: `grep -rEn 'ws://|http://[a-z].*\.svc|sslmode=disable|tls: *false'`
      across manifests/config. Any credential/token/DB traffic in plaintext → Critical.
- [ ] If a mesh exists, is mTLS **STRICT** (not PERMISSIVE)? Prove by sending plaintext to a meshed
      workload — it must be rejected.
- [ ] Is there a default-deny **AuthorizationPolicy**, with allows keyed on workload identity
      (SPIFFE principal / SA), not IP?
- [ ] Are there mesh-bypass paths (hostNetwork, direct-IP, out-of-mesh DB) reaching sensitive
      services? Are those covered by CNI NetworkPolicy (rules/03)?
- [ ] Is CNI L3/4 default-deny still in place *underneath* the mesh (mesh is not a CNI replacement)?
- [ ] Are mesh/workload certs short-lived and auto-rotated (not hand-managed)?
- [ ] Is the mesh choice justified for the service count (not a mesh for 2 services; not hand-rolled
      mTLS at scale)? For Istio, is ambient considered to cut sidecar overhead?
- [ ] Are mesh/CNI/SPIFFE versions pinned and verified against current project docs?
