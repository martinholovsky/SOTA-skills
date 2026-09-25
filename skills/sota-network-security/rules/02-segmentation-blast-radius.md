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
# Cilium: what can actually reach this endpoint? (cilium-cli has no `policy` command;
# `cilium-dbg policy get` is deprecated). Endpoint IDs are per node: use the Cilium agent pod
# on the target pod's node, find the endpoint ID, then dump its policy map
kubectl -n kube-system exec <cilium-pod-on-that-node> -c cilium-agent -- cilium-dbg endpoint list
kubectl -n kube-system exec <cilium-pod-on-that-node> -c cilium-agent -- cilium-dbg bpf policy get <endpoint-id>
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

**R7.1 — Refine the zone model where the default table (R3) is too coarse.**
- **Split the DMZ by direction.** An *inbound* DMZ hosts internet-facing services behind the WAF;
  an *outbound-only* segment hosts things that must reach external networks (update fetchers,
  outbound mail relays, webhook senders) and accepts **no** connection initiated from outside —
  the firewall carries no inbound allow for it at all.
- **Give directory services and logging their own backend segments.** The directory (LDAP/AD,
  IdP backends) and the log store are what an intruder most wants to use or erase. Firewall each
  separately; for logging, split the paths — sources may only *write* to an ingest endpoint over
  an append-only protocol (e.g. syslog forwarding), while reading and searching is a separate,
  admin-only path — so a compromised host can add lines but not rewrite history (tamper evidence:
  sota-code-security rules/18). Another system's app tier never reaches your data tier directly;
  it goes through your service.
- **A shared network behind one L7 balancer is not segmentation.** When several applications sit
  on one network and a single load balancer fans traffic out, network rules no longer separate
  them; isolation now rests entirely on the balancer's L7 routing and authz rules — audit those
  as the control they are.
- **Write the policy for humans as well as for machines.** Keep a readable network security
  policy with diagrams (zones, permitted flows, how to request a new one) next to the
  policy-as-code; reviewers and incident responders need the intent, and a diff between the two
  is itself a finding.
OWASP: Network Segmentation cheat sheet, Logging cheat sheet.

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
  Prefer an identity-aware bastion that issues short-lived per-session certs (an internal CA such as
  step-ca can back this), records sessions, and is itself fronted by the IdP. The bastion must be the *only* SSH
  path — hosts deny SSH from everywhere except the bastion's identity/SG.

## 7. Containment in depth

**R11 — Assume one layer fails; have the next.** A defense-in-depth network has: edge filtering →
zone deny-by-default → workload microsegmentation → mTLS authz → egress control. An attacker who
clears the WAF still hits zone deny; who lands in the app tier still can't reach data; who reaches a
service still needs a valid mTLS identity; who wants to exfil still hits egress allowlisting. Audit
asks: *if this layer were bypassed, what's the next thing stopping lateral movement?* If the answer
is "nothing," that's the finding.

**R11.1 — Quarantine what cannot be modernised.** Systems that cannot be patched or re-platformed,
or that speak only plaintext protocols (telnet, FTP, TFTP, SNMPv1/v2c, plaintext POP/IMAP, legacy
industrial or mainframe protocols), live in a dedicated zone: deny-by-default in both directions,
reachable only through a modern authenticated front (an identity-aware proxy or bastion that
adds MFA and session recording, or a protocol gateway that terminates TLS), with full flow
logging and alerting on anything unexpected. Scale the isolation with the data at stake — up to
a physically separate or air-gapped network — and record the modernisation or retirement plan,
since the zone contains risk rather than removing it. OWASP: Legacy Application Management cheat
sheet, Zero Trust Architecture cheat sheet.

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
- [ ] **High — unintended external exposure.** Enumerate what you actually expose, then diff it
      against the intended list: every owned subdomain (DNS zone exports plus a Certificate
      Transparency search for the domain — CT shows names nobody put in the inventory) and every
      owned public IP range, scanned from outside, e.g.
      `nmap -Pn -sV -p- -iL targets.txt -oX exposure.xml` (only against ranges you own or are
      authorised to test). Any listening service not on the intended exposure list is a finding;
      repeat on a schedule, not once.
- [ ] **Medium — zone refinements (R7.1).** Outbound-only segment has no inbound allow; directory
      and log infrastructure in their own firewalled segments with ingest and read paths split;
      apps sharing a network behind one L7 balancer audited on the balancer's rules; a
      human-readable network policy with diagrams exists and matches the policy-as-code?
- [ ] **High — legacy / plaintext systems not quarantined (R11.1).** Triage allows for plaintext
      protocols: `grep -rnE '(dport|port|from_port|to_port)[^0-9]{1,6}(21|23|69|110|143|161|512|513)([^0-9]|$)' policies firewall`
      — each hit must sit in the quarantine zone, reachable only via an authenticated modern
      front, with flow logging.
