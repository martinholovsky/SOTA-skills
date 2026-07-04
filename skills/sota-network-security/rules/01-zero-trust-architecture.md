<!-- last-verified: 2026-06 -->
# 01 — Zero-Trust Architecture

Scope: the model that frames every other rule — never trust, always verify; policy decision/
enforcement points; identity-aware access over network-location trust; microsegmentation as
strategy; ZTNA vs traditional VPN; de-perimeterization; the identity-aware (BeyondCorp-style) proxy.
This file is the *why*; rules/02–06 are the *how*.

Anchors (verified 2026-06-14): **NIST SP 800-207** "Zero Trust Architecture" (Aug 2020) is the
definitive reference; **CISA Zero Trust Maturity Model v2.0** (Apr 2023, current) gives the maturity
ladder across five pillars — Identity, Devices, Networks, Applications & Workloads, Data.

---

## 1. The core tenet: location is not a credential

**R1 — Trust is never granted by network position.** The classic perimeter model trusts anything
"inside" the firewall. Zero trust assumes the network is already hostile (the attacker may be on it)
and grants access per-request, per-resource, based on *authenticated identity + device/workload
posture + context*, re-evaluated continuously. Being on the corporate LAN, the VPN, or the pod
network confers nothing.

Practical consequences that recur as findings:
- A service that authenticates callers only by source IP/subnet (`allow 10.0.0.0/8`) is trusting
  location. Any workload that lands in that range inherits the trust — this is how one popped pod
  reaches a DB.
- "It's internal" is not a reason to skip TLS or authz. East-west traffic gets the same scrutiny as
  north-south (see rules/04 for the plaintext-internal-traffic failure).

## 2. PDP / PEP: the decision and enforcement split

NIST SP 800-207 splits the control plane into a **Policy Decision Point (PDP)** — Policy Engine
(decides allow/deny from identity, posture, threat signals) + Policy Administrator (issues the
session token/credential) — and **Policy Enforcement Points (PEP)** that sit in the data path and
let the connection through or not.

**R2 — Every protected resource sits behind a PEP; the PEP consults a PDP.** Map your stack onto
this so gaps are visible:

| Plane | PDP (decides) | PEP (enforces) |
|---|---|---|
| User → app | IdP + access proxy policy engine (identity-access owns the IdP) | Identity-aware proxy / ZTNA gateway / mesh ingress gateway |
| Workload → workload | Mesh control plane authz policy (SPIFFE identity) | Mesh sidecar / ztunnel; CNI (Cilium) policy enforcement |
| Pod → pod (L3/4) | NetworkPolicy/CNP objects | CNI datapath (eBPF in Cilium) |
| Host → host | Firewall/SG policy | nftables / cloud SG (sota-cloud-infrastructure setup) |

A resource with no PEP in front of it is implicitly "trust everyone who can route to it" — find it.

**R3 — Decisions are dynamic and context-aware where it matters.** The PDP should consume more than
static identity: device posture, request risk, time, geo, prior behavior. Don't over-engineer a
homelab, but for human access to crown-jewel systems, a static allow that never re-checks posture is
a weaker control than the model promises.

## 3. Identity-aware access over network-location access

**R4 — Authenticate the *who*, not the *where*.** For users: per-request identity from an IdP
(OIDC/SAML), ideally + device trust. For workloads: cryptographic workload identity (SPIFFE SVID,
mesh cert, cloud workload identity) — see sota-identity-access for issuance, rules/04 for mesh
consumption. The network policy then references *identity* (label/SA/SPIFFE ID), not a CIDR that any
new workload could land inside.

```yaml
# BAD: location trust — any pod that gets this IP range reaches the DB
- from: { ipBlock: { cidr: 10.0.0.0/8 } }   # "the internal network"

# GOOD: identity trust — only the api service account, in this namespace
- from:
  - podSelector: { matchLabels: { app: api } }
  # in Cilium, prefer endpointSelector / identity; in a mesh, the SPIFFE ID of the caller
```

## 4. De-perimeterization mindset

**R5 — There is no single hard shell; there are many small ones.** Stop investing in a thicker
perimeter and a soft interior. Push enforcement *to the workload*: every service is its own
perimeter (its PEP), every namespace its own segment. The firewall at the edge still matters (DDoS,
coarse filtering — rules/05), but it is one layer, not *the* control. This is why microsegmentation
(rules/02) and mesh mTLS (rules/04) are zero-trust load-bearing, not nice-to-haves.

## 5. ZTNA vs traditional VPN

**R6 — Prefer ZTNA / identity-aware proxy to flat VPN for human access.**

| | Traditional VPN | ZTNA / identity-aware proxy |
|---|---|---|
| Grants | Network access (a route onto the LAN) | Access to a *specific application*, per request |
| Trust after connect | Implicit — you're "inside" | None — every request re-authorized |
| Blast radius if creds stolen | Whole reachable network | One app, posture-gated |
| Model fit | Perimeter | Zero trust |

A VPN that drops a user onto a flat internal network is a perimeter pattern wearing a crypto
overcoat: one stolen credential = lateral movement. ZTNA (BeyondCorp-style) brokers each
application individually, checks identity + device posture per request, and never exposes the
network itself. **WireGuard still has a place** — for site-to-site links, machine-to-machine, or as
the transport *under* an app-level access decision — but per-user "VPN onto the LAN" is the
anti-pattern (see rules/02 §5 for the access-method decision).

## 6. Identity-aware proxy (BeyondCorp pattern)

**R7 — Front internal web apps with an identity-aware proxy, not a network ACL.** The proxy
(Cloudflare Access, Pomerium, oauth2-proxy + ingress, Teleport, cloud IAP) authenticates the user
via the IdP, evaluates device/context policy, and only then forwards to the backend — which is *not*
otherwise reachable. The user's identity-access skill owns the IdP and auth plane; this skill owns
making the backend unreachable except through the PEP.

The recurring failure: app reachable both via the IAP *and* directly on its cluster IP / a `world`
NetworkPolicy entity. The direct path bypasses every check. The backend must accept traffic *only*
from the proxy (mesh authz to the gateway identity, or a NetworkPolicy allowing only the
ingress/proxy namespace) — verify by hitting the backend directly and confirming it's refused.

## 7. Maturity, not perfection (CISA ZTMM v2.0)

**R8 — Place each pillar on the ladder and move it, deliberately.** ZTMM v2.0 grades each of the
five pillars Traditional → Initial → Advanced → Optimal, with cross-cutting Visibility & Analytics,
Automation & Orchestration, Governance. Use it to scope work: e.g. Networks pillar at "Initial"
(macro-segmentation, some default-deny) → target "Advanced" (microsegmentation + dynamic policy).
Don't claim "we did zero trust"; name the pillar and the level. The honest audit output is a
per-pillar maturity placement with the next concrete step, not a binary.

## Audit checklist

- [ ] Is any service authenticating callers by source IP/subnet alone (location trust)? Grep configs
      for broad `allow`/`trusted` CIDRs: `grep -rEn '10\.0\.0\.0/8|0\.0\.0\.0/0|allow .*internal'`.
- [ ] Does every protected resource sit behind an identifiable PEP, or can something route straight
      to it? List Services/Ingresses and ask "what enforces authz here?"
- [ ] Do network/mesh policies reference *identity* (label/SA/SPIFFE) rather than bare CIDRs for
      internal flows?
- [ ] For human access: is it ZTNA / identity-aware proxy, or flat VPN onto the LAN? If VPN, is it
      per-user-keyed and scoped (not whole-network)?
- [ ] Are identity-aware-proxied backends reachable *only* through the proxy? Probe the backend
      directly (`kubectl exec ... curl backend.svc`) — it must be refused.
- [ ] Is access dynamic (re-evaluated, posture-aware) for crown-jewel systems, or a one-time static
      allow?
- [ ] Can you state, per CISA ZTMM pillar, your current maturity level and the next step?
