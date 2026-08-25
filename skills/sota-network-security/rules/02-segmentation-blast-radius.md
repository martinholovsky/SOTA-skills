# 02 — Segmentation & Blast-Radius Containment

Scope: network zones/tiers, north-south vs east-west, the flat-network anti-pattern, the over-broad
`any`/`0.0.0.0/0`/`world` rule trap, microsegmentation, lateral-movement containment, choke points,
stateful firewall/SG default-deny, and remote-access methods (WireGuard vs ZTNA, bastion vs
identity-aware proxy, the SSH-open-everywhere anti-pattern). Kubernetes-specific policy depth is
rules/03; this file is the topology/strategy and the host/edge firewall layer.

---

## 1. North-south vs east-west; segment both

- **North-south** = traffic crossing the trust boundary (internet ↔ your network, client ↔ cluster).
  Historically the only thing firewalled.
- **East-west** = traffic *inside* — service↔service, pod↔pod, host↔host. Where attackers move after
  the first foothold, and historically wide open.

**R1 — Containment is an east-west property.** A hardened edge with a flat interior means one popped
front-end pod can reach the database, the secrets store, and the registry. The whole point of
segmentation is to make east-west reachability *declared*, so a foothold reaches only its
dependencies. North-south hardening (rules/05) without east-west segmentation (rules/03) is half a
control.

## 2. The flat-network anti-pattern

**R2 — A flat network is a single blast radius.** Symptoms: every host/pod can reach every other on
any port; "internal" = "trusted"; one VLAN/subnet/namespace for everything; security groups that
allow the whole VPC CIDR to itself. Impact: lateral movement is free; one CVE, one stolen
credential, one SSRF, and the incident is cluster-wide.

Fix direction: carve **zones/tiers** with deny-by-default between them, then microsegment *within*
zones (rules/03 for K8s, mesh authz for service-level).

**R3 — Standard zone model (map your real topology onto it):**

| Zone | Holds | Reachable from |
|---|---|---|
| Edge/DMZ | Reverse proxy, WAF, ingress, LB | Internet (north-south, 80/443 only) |
| App / service tier | Stateless workloads | Edge + declared peers only |
| Data / stateful tier | DBs, queues, secrets store, registry, PKI | *Only* the specific services that use them — never `any` |
| Management | CI runners, bastion/IAP, observability | Tightly scoped admin paths |

The data tier is the crown jewels. Reachability into it is the audit's first target.

## 3. The over-broad-rule trap (`any` / `0.0.0.0/0` / `world`)

**R4 — A broad source/destination on a sensitive service is a Critical finding.** This is the most
common real exposure. Examples seen in audits:
- A Cilium/firewall rule letting the `world` entity (everything, including off-cluster/internet)
  reach OpenBao (secrets), Grafana, and the container registry.
- A security group whose ingress is `0.0.0.0/0` on a DB port "for debugging."
- An ingress allow of `any → any` that someone added to "make it work."

**R5 — Prove reachability before downgrading severity, and prove the fix.** A rule *named* `restrict`
that effectively allows the world is still Critical. Render the *effective* policy and probe:

```bash
# Cilium: what can actually reach this endpoint?
cilium policy get
hubble observe --to-pod openbao/ -f          # are unexpected sources getting through?
# Generic: from an unrelated pod, can you reach the sensitive service?
kubectl -n scratch exec deploy/test -- sh -c 'curl -sm3 https://openbao.vault:8200/v1/sys/health && echo REACHABLE'
# Firewall: hunt the broad rules
grep -rEn '0\.0\.0\.0/0|::/0|\bany\b|\bworld\b' ./policies ./firewall
```

A reachable secrets store / DB / registry / admin UI from a broad entity → Critical, fix is usually
*small* (tighten the source to the one identity that needs it) but the exposure is severe.

## 4. Microsegmentation & choke points

**R6 — Segment to the workload, then funnel cross-zone traffic through choke points.**
- *Microsegmentation*: the unit of isolation is the workload/identity, not the subnet. Within the
  app tier, service A reaches service B only if declared. Enforced by CNI policy (rules/03) and/or
  mesh authz (rules/04).
- *Choke points*: cross-zone traffic (app→data, internal→internet) passes through a small number of
  inspectable, enforceable points — an egress gateway/proxy (rules/05), a mesh waypoint, a firewall.
  Choke points are where you log, allowlist, and rate-limit. A topology with no choke points cannot
  be inspected or contained.

**R7 — Right-size the segmentation effort.** Macro-segmentation (zones, deny between tiers) is the
high-value baseline — do it everywhere. Full per-workload microsegmentation is *Advanced* (CISA
ZTMM) — apply it first to the data tier and crown-jewel paths, then broaden. Don't let "perfect
microsegmentation everywhere" block shipping the deny-between-tiers baseline.

## 5. Stateful firewall / security-group policy

**R8 — Default-deny, identity/tag-referenced, audited for breadth.** (Host nftables for a single box
is sota-sandboxing rules/02; cloud SG/VPC *setup* is sota-cloud-infrastructure rules/03 — this skill
owns the *posture*.)
- Deny inbound and outbound by default; allow specific flows.
- Reference **security groups / tags / service accounts, not CIDRs**, for internal flows so rules
  survive re-IP (`sg-app → sg-db:5432`, not `10.2.0.0/16 → :5432`).
- No `0.0.0.0/0`/`::/0` ingress except 80/443 on the edge tier. Audit IPv6 `::/0` exactly like
  IPv4 — every IPv6 address is globally routable, no NAT safety blanket.
- eBPF-based enforcement (Cilium host firewall, Tetragon for L7/syscall visibility) scales better
  than iptables rule sprawl on busy nodes; where Cilium is the CNI it can enforce host-level policy
  too — verify the current stable line at the project's releases page rather than pinning one here.

## 6. Remote access: WireGuard vs ZTNA, bastion vs identity-aware proxy

**R9 — SSH/RDP open to the internet is a finding, even "temporarily."** It is the perennial
brute-force and 0-day target. There is always a better option.

**R10 — Choose the access method by what's being accessed:**

| Need | SOTA choice | Avoid |
|---|---|---|
| Human → internal *web* app | Identity-aware proxy / ZTNA (rules/01 §6) | Exposing the app; flat VPN |
| Human → *shell* on a host | Identity-aware bastion (Teleport/IAP/SSM-style: per-session identity, recording, short-lived certs) | Static SSH keys; `0.0.0.0/0:22` |
| Site-to-site / machine-to-machine | **WireGuard** (per-peer keys, modern crypto, in-kernel since Linux 5.6) | Legacy IPsec sprawl; bespoke tunnels |
| Per-user "get on the network" | ZTNA (scoped to apps) | Flat VPN onto the LAN (rules/01 §5) |

- **WireGuard discipline:** one keypair per peer (never shared), `AllowedIPs` scoped to exactly the
  destinations that peer needs (it is also the routing/ACL — a wide `AllowedIPs = 0.0.0.0/0` makes
  it a flat VPN again), rotate keys on offboarding, keys handled as secrets (sota-secrets-management).
- **Bastion vs IAP:** a plain jump-host with shared SSH keys is barely better than direct SSH.
  Prefer an identity-aware bastion that issues short-lived per-session certs (your step-ca can back
  this), records sessions, and is itself fronted by the IdP. The bastion must be the *only* SSH
  path — hosts deny SSH from everywhere except the bastion's identity/SG.

## 7. Containment in depth

**R11 — Assume one layer fails; have the next.** A defense-in-depth network has: edge filtering →
zone deny-by-default → workload microsegmentation → mTLS authz → egress control. An attacker who
clears the WAF still hits zone deny; who lands in the app tier still can't reach data; who reaches a
service still needs a valid mTLS identity; who wants to exfil still hits egress allowlisting. Audit
asks: *if this layer were bypassed, what's the next thing stopping lateral movement?* If the answer
is "nothing," that's the finding.

## Audit checklist

- [ ] Are zones/tiers defined with deny-by-default *between* them, or is the network flat? Probe
      cross-tier reachability (app pod → data tier on a non-declared port must fail).
- [ ] Hunt over-broad rules: `grep -rEn '0\.0\.0\.0/0|::/0|\bany\b|\bworld\b' policies firewall`.
      For each hit touching a sensitive service (secrets/DB/registry/admin/PKI), prove reachability
      and rate Critical until fixed.
- [ ] Do internal firewall/SG rules reference identities/tags/SGs, not bare CIDRs?
- [ ] Is the data tier reachable only by the specific services that use it (not `any`, not the
      whole VPC/cluster CIDR)?
- [ ] Are cross-zone flows funneled through inspectable choke points (egress gateway, firewall,
      mesh waypoint)?
- [ ] Is SSH/RDP exposed to `0.0.0.0/0`? (`nmap`/SG scan for 22/3389 from outside → finding.)
- [ ] Remote access: ZTNA/IAP for web, identity-aware bastion for shells, WireGuard (scoped
      `AllowedIPs`, per-peer keys) for site/machine links — not flat VPN, not shared keys?
- [ ] For each control layer, is there a next layer if it's bypassed (defense in depth)?
