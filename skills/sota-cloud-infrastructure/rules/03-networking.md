# 03 — Networking, DNS, TLS & Edge

Scope: VPC/VNet design, CIDR planning, egress control, private connectivity,
hub-spoke topology, DNS architecture, TLS/certificate automation, load balancing,
CDN, DDoS posture, IPv6.

## 1. VPC design: three tiers, multi-AZ, deny-by-default

- **Standard tier model per VPC/VNet:**
  - **Public subnets** — only internet-facing entry/exit points: load balancers, NAT
    gateways, bastion-replacement endpoints. No application instances. No databases,
    ever.
  - **Private subnets** — application compute. Outbound internet only via controlled
    egress (NAT/proxy); inbound only from LB tier.
  - **Isolated subnets** — data stores and internal-only services. No route to the
    internet in either direction; reach cloud APIs via private endpoints.
- **Span ≥ 2 (prefer 3) availability zones** with one subnet per tier per AZ. A
  single-AZ subnet layout silently forces single-AZ workloads later.
- Security groups / firewall rules: deny-by-default, reference **security groups (or
  tags/service accounts in GCP), not CIDRs**, for internal flows — `sg-app → sg-db:5432`
  survives re-IPs; CIDR rules rot. No `0.0.0.0/0` ingress anywhere except 80/443 on
  the edge LB tier. SSH/RDP from the internet is a finding even "temporarily" — use
  SSM Session Manager / IAP / Azure Bastion instead, and you usually don't need a
  bastion subnet at all.
- Keep NACLs/subnet-level rules coarse (subnet-tier intent) and do fine-grained
  control in SGs; duplicating every rule in both layers guarantees drift.
- Flow logs on (sampled where cost-sensitive), delivered to central logging (rules/01).

```hcl
# BAD: CIDR-based, internet-wide "temporary" access
resource "aws_security_group_rule" "db_in" {
  type        = "ingress"
  from_port   = 5432
  to_port     = 5432
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"] # finding: Critical
}

# GOOD: SG-to-SG, intent readable, survives re-IP
resource "aws_security_group_rule" "db_in" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db.id
  source_security_group_id = aws_security_group.app.id # only the app tier
}
```

## 2. CIDR planning: allocate like you'll have 50 VPCs

- Reserve a **non-overlapping supernet plan up front** (e.g., carve 10.0.0.0/8 into
  per-region /12s, per-VPC /16–/20s), tracked in IPAM (provider IPAM service or a
  versioned registry). Overlapping CIDRs are nearly unfixable once peered/VPN'd —
  they block peering, hybrid connectivity, and mergers.
- Avoid 192.168.0.0/16 and the most common 10.0.0.0/24-style defaults for anything
  that might ever connect to a partner/VPN — collisions are guaranteed.
- Size for the orchestrator: Kubernetes eats IPs (pod-per-IP models). Give cluster
  VPCs/subnets generous space or use secondary ranges (GKE alias IPs, EKS custom
  networking) from day one.
- Don't bridge overlap with NAT hacks; renumber the smaller side or use IPv6.

## 3. Egress control

- **Egress is a control point, not a default-open pipe.** Data exfiltration and
  C2 traffic leave through egress; treat `0.0.0.0/0` outbound from data tiers as a
  finding.
- Tiered approach:
  1. Isolated tier: no egress at all; private endpoints for needed cloud services.
  2. Private tier: egress via NAT gateway; restrict with L7 egress filtering
     (AWS Network Firewall / GCP Secure Web Proxy / Azure Firewall FQDN rules, or a
     self-managed proxy) allowing named domains for high-sensitivity environments.
  3. Public tier: only LBs/NAT; they originate nothing themselves.
- NAT gateways: one per AZ for prod (cross-AZ NAT = paid cross-AZ hop + AZ
  coupling); they bill per-hour AND per-GB processed — high-volume flows to cloud
  services should bypass NAT via private/gateway endpoints (see rules/06).

## 4. Private connectivity to managed services

- Reach provider services privately: **gateway endpoints** (AWS S3/DynamoDB — free,
  use always), **interface endpoints / PrivateLink**, **GCP Private Google Access /
  Private Service Connect**, **Azure Private Endpoints / service endpoints**.
- Default for prod: data stores, secret managers, container registries, and logging
  endpoints reachable without traversing the internet or NAT. This is both a
  security control (no public exposure, org-ID conditions on endpoint policies) and
  a cost control (NAT per-GB).
- PrivateLink/PSC is also the SOTA pattern for **service-to-service across
  accounts/VPCs without merging networks** — expose one service, not your whole CIDR.

## 5. Topology: flat → peered → hub-spoke

- < ~3 VPCs: peering is fine. Peering is non-transitive — beyond a handful, the mesh
  (n²) becomes unauditable.
- At scale: **hub-spoke** via AWS Transit Gateway / GCP Network Connectivity Center /
  Azure vWAN-Virtual-hub. Centralize in the hub: hybrid links (VPN/Direct
  Connect/Interconnect/ExpressRoute), inspection/egress firewalls, shared endpoints.
  Spokes (workload VPCs) cannot reach each other unless route tables say so —
  segment prod from non-prod at the routing layer, not just SGs.
- Don't share one VPC across unrelated teams as a topology shortcut (GCP Shared VPC
  is the deliberate, IAM-governed exception when used with per-team subnets).

## 6. DNS architecture

- **Registrar hygiene:** domains in a corporate registrar account (not an
  employee's), registrar MFA + transfer lock + registry lock for crown-jewel
  domains, auto-renew with monitored payment, contact = team alias. Expired domains
  and dangling delegations are takeover vectors.
- **Split-horizon:** public zones contain only public entry points; internal records
  live in private zones (Route 53 private hosted zones / Cloud DNS private zones /
  Azure Private DNS) attached to VPCs. Internal hostnames in public DNS leak
  topology. Private endpoints (above) require matching private DNS zones —
  the most common "why is it still going over the internet" bug.
- **Dangling records are the top DNS finding:** CNAMEs/A records pointing at
  released cloud resources (deleted buckets, old LB names, deprovisioned PaaS apps)
  enable subdomain takeover. Make DNS records lifecycle-coupled to the resources in
  IaC; scan zones for danglers regularly.
- **Decommission in DNS-first order.** Releasing the resource while a record still
  names it is the takeover window, so the sequence is: (1) repoint or park the name
  on a host you control (redirect or maintenance page) if it must keep answering;
  (2) delete every record that targets the service — CNAME, A/AAAA, alias, MX, NS
  delegations; (3) wait at least the old TTL; (4) only then delete the bucket, LB,
  app or zone; (5) confirm the name no longer resolves to it, re-run the takeover
  scan, update the DNS inventory. Keep ownership-verification TXT records that bind
  the name to *your* tenant (e.g. App Service `asuid.<name>`) — they are what stops
  another tenant validating it. A dangling record found later is fixed twice: the
  record, and the teardown procedure that left it. Pipeline gate: sota-devsecops
  rules/06 §6.7. (OWASP: Subdomain Takeover Prevention cheat sheet)
- **DNSSEC stance:** sign zones where the registrar+provider support is solid and
  you have rotation automation (managed DNSSEC on Route 53/Cloud DNS/Azure DNS);
  skip hand-rolled key management. Always enable it for domains used as identity
  anchors (email/SPF/DKIM-bearing zones). CAA records on all public zones limiting
  issuance to your CAs.
- Low TTLs (60–300s) on records you'll need to move in an incident; long TTLs on
  stable apex/MX.

## 7. TLS and certificate automation

- **Certificate lifetimes are collapsing by CA/Browser Forum schedule: max 200 days
  from 2026-03-15, 100 days from 2027-03-15, 47 days from 2029-03-15.** Manual
  renewal is now an outage generator, period. Every cert must be issued and renewed
  automatically.
- Prefer **provider-managed certs** terminated on managed LBs/CDN (ACM, Google-managed
  certs, Azure-managed) — auto-renewed, no private key you can leak. Where you must
  hold certs (self-managed ingress, on-prem), use **ACME** (Let's Encrypt or your
  CA's ACME endpoint) with DNS-01 for wildcards/internal, cert-manager on Kubernetes.
- Expiry monitoring as a backstop (alert at 30/14/7 days) even with automation —
  automation fails silently; see sota-observability for alert wiring.
- Internal/mTLS: use a private CA service (AWS Private CA, GCP CA Service, or
  service-mesh-issued identities) with short lifetimes; never a long-lived wildcard
  cert copied between services.
- TLS policy on LBs/CDN: modern policy (TLS 1.2 minimum, 1.3 preferred), HSTS on
  web origins.

## 8. Load balancing

- **L7 (ALB / GCP HTTP(S) LB / Azure App Gateway or Front Door)** for HTTP: routing,
  WAF attachment, OIDC auth offload, gRPC. **L4 (NLB / GCP passthrough / Azure LB)**
  for raw TCP/UDP, extreme connection rates, static IPs, PrivateLink targets.
- Health checks must hit a **meaningful endpoint** (checks downstream dependency
  readiness, not just "200 on /"), with sane thresholds; a health check on `/` that
  always 200s converts partial outages into full ones by keeping dead nodes in
  rotation. Distinguish liveness (process up) from readiness (can serve).
- Enable cross-zone/multi-AZ distribution deliberately (know the cross-AZ data cost),
  connection draining/deregistration delay ≥ app's longest request, and LB access
  logs to central storage.
- LBs are the only public compute-adjacent surface: attach WAF for L7 apps exposed
  to the internet; origins behind a CDN must not be directly reachable (see §9).

## 9. CDN and edge

- Put a CDN (CloudFront / Cloud CDN or Media CDN / Azure Front Door) in front of any
  public static or cacheable content, and in front of dynamic apps when you want
  edge TLS, DDoS absorption, and WAF at the edge.
- **Lock the origin:** origin accepts traffic only from the CDN — S3 via Origin
  Access Control (no public bucket behind CloudFront, ever), custom origins via
  origin-auth headers/managed prefix lists/private connectivity. An origin reachable
  directly bypasses your WAF, cache, and DDoS layer.
- **Origin shielding / tiered caching on** for origin-cost-sensitive backends.
- **Cache keys minimal:** include only headers/cookies/query params that change the
  response. Default-everything cache keys = near-0% hit ratio; forgetting a varying
  header = serving user A's response to user B (cache poisoning class).
- Private content: **signed URLs/cookies** (CloudFront signed URLs, GCS/S3 presigned,
  Front Door + token auth) with short expiry; never security-by-obscure-URL.
- Cache invalidation is a deploy step (versioned asset filenames preferred over
  purges).

## 10. DDoS posture

- Baseline (free/default): provider always-on L3/4 mitigation (AWS Shield Standard,
  Google/Azure network defenses), CDN absorbing edge traffic, autoscaling with hard
  caps so an attack can't scale your bill infinitely.
- Internet-facing L7 apps: WAF with rate-limiting rules + managed rule sets.
- Paid tiers (Shield Advanced / Cloud Armor Adaptive / Azure DDoS Protection) when
  you have revenue-critical public endpoints — they add response teams and cost
  protection. Decide explicitly and record the stance; "we never considered DDoS"
  is the finding.
- Don't expose what doesn't need exposure: the best DDoS surface is none (private
  endpoints, CDN-only origins).

## 11. IPv6 stance

- Decide explicitly; default for new builds: **dual-stack at the edge** (LB/CDN
  accept IPv6), IPv4 or dual-stack internally as provider support allows.
- IPv6 relieves IPv4 exhaustion (large pod networks, many VPCs) and avoids growing
  per-IPv4-address charges; egress-only internet gateways give outbound-only IPv6
  semantics like NAT-without-NAT-cost.
- IPv6 has **no NAT safety blanket**: every IPv6 address is globally routable, so
  SG/firewall discipline must be airtight before enabling on private tiers; audit
  for `::/0` rules exactly like `0.0.0.0/0`.

## Audit checklist

- [ ] Subnet tiers exist (public/private/isolated); no compute or data stores in
      public subnets; databases have no internet route.
- [ ] ≥ 2 AZs per tier; NAT per AZ in prod.
- [ ] No `0.0.0.0/0` or `::/0` ingress except 80/443 on edge LBs; no SSH/RDP from
      internet; internal rules reference SGs/tags, not broad CIDRs.
- [ ] CIDR plan documented/IPAM-tracked; no overlaps among connected networks.
- [ ] Egress controlled: isolated tier has none; sensitive envs have domain-level
      egress filtering; flow logs centralized.
- [ ] Private/gateway endpoints for storage, secrets, registries, logging in prod;
      matching private DNS zones attached.
- [ ] Topology: peering count sane or hub-spoke; prod/non-prod not mutually routable.
- [ ] Registrar: corporate account, MFA, transfer locks, auto-renew, team contacts.
- [ ] Split-horizon: no internal records in public zones; zones scanned for dangling
      records (sample-check CNAME targets exist and are yours).
- [ ] **Medium** — DNS records coupled to resource lifecycle (§6): a record whose
      target is a hard-coded provider hostname outlives the resource on teardown.
      Probe: `grep -rn -E 'records *= *\[ *"[^"]*\.(cloudfront\.net|azurewebsites\.net|herokuapp\.com|elasticbeanstalk\.com|amazonaws\.com|azureedge\.net|trafficmanager\.net|github\.io)"' --include='*.tf' .`
      — each hit should reference the resource attribute instead; the decommission
      runbook deletes records before the resource and waits out the TTL.
- [ ] CAA records present; DNSSEC stance decided and recorded.
- [ ] All public certs auto-issued/renewed (ACM/ACME/managed); expiry alerts as
      backstop; nothing renewed by hand or living past current CA/B lifetime caps.
- [ ] LB health checks meaningful; draining configured; access logs on; WAF on
      internet-facing L7.
- [ ] CDN origins not directly reachable (OAC/origin auth verified by hitting origin
      directly); cache keys reviewed for poisoning/varying headers; private content
      uses signed URLs.
- [ ] DDoS stance recorded; rate limiting on public APIs; autoscale caps set.
- [ ] IPv6: stance recorded; if enabled, `::/0` rules audited.
