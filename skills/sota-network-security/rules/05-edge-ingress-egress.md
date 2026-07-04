<!-- last-verified: 2026-06 -->
# 05 — Edge, Ingress & Egress

Scope: WAF (OWASP CRS, Coraza/ModSecurity), ingress/API-gateway hardening, DDoS posture, TLS
termination + re-encryption to backends, reverse-proxy trusted-IP / allowlist handling (behind
Cloudflare), Cloudflare-tunnel / identity-aware-proxy patterns, and **egress as a first-class
control**: default-deny egress, egress gateways/proxies, FQDN allowlisting, preventing C2/exfil, and
blocking the cloud metadata endpoint (the SSRF-meets-egress chain). A representative edge stack: **Caddy with a
CRS WAF, Cloudflare in front**.

Where this sits: sota-cloud-infrastructure rules/03 owns LB/CDN *provisioning* and registrar/DNS
*setup*; this skill owns the *security posture*. rules/03 here owns the K8s-internal egress
mechanics (CNP/FQDN); this file owns the edge and the egress *discipline*. sota-api-design rules/07
owns API rate-limiting design; sota-code-security rules/01 (SSRF) and rules/05 (CORS/CSP) own the
app side.

Verified (2026-06-14): **OWASP CRS** current line **4.x** (4.25 is the first CRS-4 LTS; 4.27.x
released 2026) — runs on **OWASP ModSecurity** *and* **OWASP Coraza** (Go, SecLang-compatible, the
modern engine; both are now OWASP projects). **IMDSv2** is token-required and account-enforceable;
metadata IP `169.254.169.254` / `fd00:ec2::254`. Pin CRS version.

---

## 1. Ingress / edge proxy hardening

**R1 — One hardened, inspectable edge; backends not directly reachable.** All north-south HTTP
enters through the edge proxy (Caddy) / ingress controller, which terminates TLS, applies the WAF,
sets security headers, and forwards. Backends accept traffic *only* from the edge/ingress (mesh authz
to the gateway identity, or NetworkPolicy allowing only the ingress namespace — rules/03/04). A
backend reachable directly bypasses the WAF, rate limits, and auth — verify by hitting a backend pod
IP directly; it must be refused.

**R2 — Minimal exposure and version hygiene at the edge.** Expose only 443 (and 80→443 redirect);
disable unused methods/modules; keep the proxy and WAF engine patched (a WAF with a known bypass CVE
is theater). Don't leak backend topology in headers (`Server`, `X-Powered-By`, internal hostnames).

## 2. WAF (OWASP CRS on Coraza / ModSecurity)

**R3 — Run CRS in blocking mode at a tuned paranoia level — not detection-only forever.** CRS in
"DetectionOnly" logs but blocks nothing; a WAF that never blocks is monitoring, not a control. The
rollout is: deploy in detection → tune out false positives → flip to blocking. A long-lived
detection-only WAF is a Medium finding (it's not enforcing).

- **Paranoia Level (PL):** PL1 default; raise to PL2+ for sensitive apps, accepting more tuning.
- **Anomaly scoring:** CRS scores requests and blocks past a threshold; tune the threshold and add
  per-rule exclusions rather than disabling whole rule files.
- **Engine:** **Coraza** (Go, embeddable — pairs well with Caddy/Envoy/modern proxies) or
  **ModSecurity v3**; both run the same CRS. Caddy + a Coraza module is the SOTA self-hosted combo.
- CRS is **not** input validation or authz — it's a generic-attack net (SQLi/XSS/RCE patterns,
  scanner signatures). Defense in depth: app-layer validation (sota-code-security) still required.

**R4 — Don't let the WAF lull you on SSRF/business logic.** CRS catches generic payloads, not
app-specific SSRF or IDOR. Pair the edge WAF with app-side SSRF defenses (sota-code-security
rules/01) and the egress controls below (§6) — the WAF is the north-south net; egress is the
south-bound net.

## 3. TLS termination + re-encryption

**R5 — Terminate TLS at the edge; re-encrypt to backends crossing a trust boundary.** Edge
terminates the public cert (auto-managed — rules/06), inspects, then originates a *new* TLS/mTLS
connection to the backend. Plaintext from edge→backend across the cluster network is the
plaintext-internal-traffic problem (rules/04) at the ingress hop. Inside a mesh, the edge gateway
hands off to mTLS automatically; otherwise configure backend TLS explicitly.

## 4. Reverse-proxy trusted-IP handling (behind Cloudflare)

**R6 — Trust `X-Forwarded-For` / `CF-Connecting-IP` ONLY from your proxy's real IPs, or attackers
spoof client identity.** Behind Cloudflare → Caddy → app, two recurring bugs:
- **Spoofable client IP:** if the app reads `X-Forwarded-For` from *any* source, a request that
  reaches the app directly (bypassing Cloudflare) can forge any client IP — breaking IP allowlists,
  rate limits, and logs. Configure the proxy to trust XFF only from the upstream's known ranges, and
  prefer Cloudflare's `CF-Connecting-IP` validated against current Cloudflare IP ranges.
- **Origin exposure (the bypass):** if the origin is reachable on its public IP, an attacker skips
  Cloudflare and the WAF entirely. **Lock the origin to Cloudflare:** firewall/SG allow only
  Cloudflare IP ranges (or use **Cloudflare Tunnel** so the origin has *no* inbound public IP at
  all — strongly preferred). Verify by resolving and hitting the origin directly from outside.

```caddyfile
# Caddy: trust forwarded headers only from Cloudflare; everything else is untrusted
{
  servers {
    trusted_proxies static <cloudflare-ipv4-ranges...> <cloudflare-ipv6-ranges...>
    client_ip_headers Cf-Connecting-Ip X-Forwarded-For
  }
}
```

**R7 — Cloudflare Tunnel / identity-aware proxy for non-public or admin surfaces.** Internal/admin
apps go behind Cloudflare Access (identity-aware proxy, rules/01 §6) or a tunnel — never a public
origin guarded only by a path or a guessed-URL. The origin stays unreachable except through the
authenticated proxy.

## 5. DDoS posture

**R8 — Absorb at the edge, rate-limit per-identity, cap autoscaling.** Cloudflare absorbs L3/4 and
much L7; add WAF rate-limiting rules and per-route/per-identity limits (design owned by
sota-api-design rules/07). Cap autoscaling so a flood can't scale your bill or cluster infinitely.
"We never considered DDoS" is the finding; record the stance. Best DDoS surface is none — keep
non-public surfaces non-public (tunnels, IAP).

## 6. Egress as a first-class control

**R9 — Default-deny egress; allow named destinations only.** Exfiltration and C2 leave through
egress. Treat broad outbound (`0.0.0.0/0` from app/data tiers) as a finding. Tiers:
1. **Data/isolated tier:** no egress; reach internal deps via private paths only.
2. **App tier:** egress only to an **allowlist** — FQDN-based where possible (Cilium FQDN policy,
   rules/03 §5; or an egress proxy like a forward-Squid/Envoy with a domain allowlist).
3. **Egress gateway/proxy:** funnel all egress through one inspectable, loggable choke point (Cilium
   egress gateway for stable source IPs; a forward proxy for L7 domain allowlisting + logging).

**R10 — Block the cloud metadata endpoint — the SSRF-meets-egress chain.** An SSRF in an app
(sota-code-security rules/01 owns finding/fixing it) becomes credential theft only if the workload
can actually *reach* `169.254.169.254`. Close the egress side: deny `169.254.0.0/16` (and
`fd00:ec2::254`) from workload egress at the CNI/firewall, and on cloud use **IMDSv2** (token
required, hop-limit 1, account-level enforcement so v1 can't be used). Defense in depth: the app
should also not be SSRF-able, but egress denial is the backstop that turns "credential theft" into
"connection refused." On the user's on-prem Talos there's no IMDS, but keep the egress default-deny
so a future cloud burst is safe by default.

```
# Egress allowlisting, layered:
#  - CNI FQDN policy (rules/03 §5) for in-cluster app egress
#  - forward proxy w/ domain allowlist for L7 inspection + logging (the choke point)
#  - DENY 169.254.0.0/16 and ::ffff:169.254.0.0/112 everywhere
#  - egress flow logs -> detection (sota-detection-engineering: C2/DNS-exfil detection)
```

**R11 — Egress visibility feeds detection.** Export egress flow logs / proxy logs to
sota-detection-engineering (C2 beaconing, DNS exfil, anomalous destinations). An allowlist plus
logging beats either alone: the allowlist blocks the easy path, the logs catch the clever one.

## Audit checklist

- [ ] Are backends reachable only via the edge/ingress? Hit a backend pod IP / origin public IP
      directly from outside — must be refused.
- [ ] Is the WAF (CRS on Coraza/ModSecurity) in **blocking** mode at a tuned PL, current version —
      not detection-only-forever, not unpatched?
- [ ] Is the public cert terminated at the edge and traffic re-encrypted (not plaintext) to
      backends across the cluster network?
- [ ] Does the app trust `X-Forwarded-For`/`CF-Connecting-IP` **only** from known proxy ranges
      (not spoofable)? Is the origin locked to Cloudflare (IP allowlist or Tunnel — verify the
      origin isn't directly reachable)?
- [ ] Internal/admin surfaces behind an identity-aware proxy / tunnel, not a public origin?
- [ ] Is egress **default-deny** with an FQDN/IP allowlist for app tiers and none for data tiers?
      Probe: a pod reaching an arbitrary internet host must fail.
- [ ] Is `169.254.0.0/16` (metadata) blocked from workload egress? On cloud, is **IMDSv2**
      enforced (hop limit, account-level)?
- [ ] Is egress funneled through an inspectable choke point and are egress/proxy logs exported to
      detection?
- [ ] DDoS stance recorded; per-identity rate limits and autoscale caps set?
