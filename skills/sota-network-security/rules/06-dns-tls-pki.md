# 06 — DNS, TLS & PKI

Scope: DNS security (DNSSEC, DNS firewall / RPZ, DoH/DoT, split-horizon, registrar/CAA hygiene,
DNS-tunneling/exfil), TLS posture (1.3, cipher/version policy, HSTS, OCSP/CRL), certificate
lifecycle automation (ACME) and the shrinking max cert lifetimes that force it, and internal PKI
(e.g. step-ca — short-lived certs, private CA trust distribution, cert-pinning
tradeoffs).

Where this sits: sota-cloud-infrastructure rules/03 owns DNS zone/registrar *setup* and
provider-managed cert provisioning; this skill owns the *security posture* (DNS firewalling,
tunneling defense, TLS policy, internal PKI). sota-secrets-management owns TLS private-key storage/
rotation mechanics. sota-detection-engineering owns DNS-exfil *detection* content; this file owns the
*controls* that reduce its surface.

Verified (2026-06-14): **CA/Browser Forum SC-081v3** (approved Apr 2025) phases public TLS cert max
lifetime down: **200 days from 2026-03-15 → ~100 days from 2027-03-15 → 47 days from 2029-03-15**
(DCV reuse → 10 days by 2029). **NIST SP 800-207** frames identity over location. **IMDSv2** for the
metadata cross-reference (rules/05). Pin the CA/B schedule against cabforum.org.

---

## 1. The cert-lifetime collapse forces automation

**R1 — Every certificate is auto-issued and auto-renewed. Manual renewal is now an outage
generator.** Public cert max lifetime drops to 200 days (2026-03), then ~100, then 47 (2029). A
human cannot reliably re-issue every ~6 weeks across a fleet. Therefore:
- **ACME everywhere** — Let's Encrypt / your CA's ACME endpoint for public certs; **cert-manager** on
  Kubernetes (Issuer/ClusterIssuer + Certificate) for both public and internal.
- **Provider-managed certs** on managed LB/CDN/Cloudflare where applicable (no private key you can
  leak).
- **Expiry monitoring as a backstop** (alert at 30/14/7 days) *even with* automation — automation
  fails silently. (Alert wiring: sota-observability.)
- Any cert renewed by hand, or living past the current CA/B cap, is a finding (High on a public
  endpoint — guaranteed future outage).

## 2. TLS posture

**R2 — TLS 1.3 preferred, 1.2 minimum; everything below is disabled.** No TLS 1.0/1.1, no SSLv3.
Cipher policy: AEAD suites only (1.3 enforces this; for 1.2 allow only ECDHE + AES-GCM/ChaCha20).
Audit edges, ingress, mesh, and internal services alike.

```bash
# Hunt weak TLS quickly
nmap --script ssl-enum-ciphers -p 443 host        # flags TLS<1.2, weak ciphers, no PFS
grep -rEn 'TLSv1\.0|TLSv1\.1|SSLv3|min_version.*1\.0' ./config
```

**R3 — HSTS on web origins, OCSP stapling, modern key types.** `Strict-Transport-Security` with a
sensible max-age (and `includeSubDomains` once you're sure) so browsers refuse plaintext. Enable
**OCSP stapling** at the edge (CRL/OCSP checks owned by the server, not punted to the client);
short-lived certs (R1) reduce reliance on revocation anyway — a 47-day cert that's compromised
expires fast. Prefer ECDSA (P-256) certs for performance; RSA-2048+ acceptable.

**R3.1 — Enable hybrid post-quantum key exchange where the stack supports it.** Offer the
`X25519MLKEM768` hybrid group on TLS 1.3 (already default-on in modern stacks, e.g. Go 1.24+;
configurable in current OpenSSL/BoringSSL and major CDNs). It defends *confidentiality* against
harvest-now-decrypt-later — relevant for EU/long-lived-sensitive traffic — at negligible cost,
and being hybrid it's no weaker than X25519 if the PQ part is ever broken. (Signatures/PKI stay
classical for now.) See sota-code-security rules/04 §1.

## 3. DNS security

**R4 — Registrar & issuance hygiene.** (Setup is cloud-infra rules/03; the *security* controls:)
- **CAA records on every public zone** restricting issuance to your CA(s) — limits who can mint a
  cert for your domains.
- Registrar in a corporate account with MFA + transfer/registry lock for crown-jewel domains.
- **Dangling records** (CNAME/A pointing at deprovisioned resources) = subdomain-takeover vector;
  lifecycle-couple DNS to resources in IaC and scan zones for danglers.

**R5 — Split-horizon: internal names stay in private zones.** Internal hostnames in public DNS leak
topology and aid recon. Public zones hold only public entry points; internal records live in private
zones served to internal resolvers only.

**R6 — DNSSEC where the registrar+provider support is solid and rotation is automated.** Sign zones
used as identity anchors (email/SPF/DKIM-bearing); use *managed* DNSSEC (avoid hand-rolled key
rollover). DNSSEC protects integrity (anti-spoofing), not confidentiality.

**R7 — DNS firewall / RPZ + DoH/DoT for confidentiality and policy.**
- **Resolver-level DNS firewall (RPZ)** blocks resolution of known-malicious / newly-registered /
  C2 / DGA domains — a cheap, high-value control that kills many malware and exfil paths at the
  *name* layer before any packet leaves. Pair with FQDN egress allowlisting (rules/05 §6) and a
  blocklist feed.
- **DoH/DoT** encrypts client↔resolver DNS so on-path observers can't see/modify queries. Decide a
  stance: force internal clients to your resolver (which does logging + RPZ), and consider blocking
  *unauthorized* external DoH (rogue DoH bypasses your DNS firewall and exfil monitoring — a known
  evasion). The control is "all DNS goes through *our* policy-applying, logging resolver."

**R8 — DNS tunneling / exfil: reduce surface here, detect in detection-engineering.** DNS is a
classic covert channel (data encoded in subdomains/TXT to an attacker NS). Controls this skill owns:
funnel all resolution through your resolver (R7), RPZ-block/limit lookups to attacker-controlled
zones, rate-limit/length-limit queries, and FQDN-allowlist egress so workloads can't reach arbitrary
authoritative servers. **Detection** of the exfil pattern (entropy, query volume, long labels) is
sota-detection-engineering — feed it your resolver logs.

## 4. Internal PKI (step-ca)

**R9 — Run a private CA with short-lived certs; distribute trust deliberately.** A common self-hosted choice is
**step-ca**. SOTA internal PKI:
- **Short lifetimes + ACME automation:** step-ca speaks ACME — issue internal certs (services, mTLS,
  bastion sessions) with hours-to-days lifetimes and auto-renew. Short-lived internal certs make
  revocation largely moot (the window is tiny) — this is *why* you prefer them over long-lived certs
  with CRL/OCSP plumbing.
- **Trust distribution:** push the internal root/intermediate to the trust stores of clients/
  workloads that must validate it (node trust bundle, container base image, mesh CA config). The
  recurring bug: a service can't validate internal certs because the root isn't distributed →
  someone "fixes" it with `InsecureSkipVerify`/`--insecure` (R11). Distribute the root, never skip
  verification.
- **Control what gets *into* the trust store** (OWASP Key Management): adding a root to a
  workload's trust bundle is a privileged, audited change — a rogue/extra CA is silent MITM for
  everything that workload talks to. Ship trust bundles as immutable, version-controlled artifacts
  (baked into the image / GitOps-managed), not mutated at runtime; alert on drift in the bundle.
- **Protect the CA key** (sota-secrets-management): the private CA's signing key is a crown jewel —
  HSM/KMS-backed or tightly access-controlled; its compromise mints trusted certs for everything.
- **Separate intermediates** per purpose/environment so one can be rotated/revoked without
  re-trusting the root.

**R10 — Feed the mesh from the internal CA.** The service mesh / Cilium mTLS CA (rules/04) chains to
step-ca (or its own intermediate). Short-lived SVIDs auto-rotate; don't copy a long-lived wildcard
between services.

**R11 — Cert pinning: deliberate, with a rotation story, or not at all.** Pinning a peer's cert/CA
adds MITM resistance but turns rotation into an outage if the pin isn't updated in lockstep — and
short-lived certs (R1/R9) rotate constantly. Pin to the *CA/intermediate* (stable) rather than the
*leaf* (rotates), keep backup pins, and only pin where the threat justifies the operational cost
(mobile apps, high-value B2B). For internal mesh traffic, identity-validated mTLS already gives the
property; extra leaf-pinning is usually net-negative. `InsecureSkipVerify` / `--insecure` /
`verify=false` is never the answer — distribute trust (R9).

```bash
# Hunt disabled verification — each hit is a finding
grep -rEn 'InsecureSkipVerify|verify=false|--insecure|NODE_TLS_REJECT_UNAUTHORIZED *= *0|sslmode=disable' .
```

## Audit checklist

- [ ] Are all public certs ACME/managed and auto-renewed, with expiry alerts as backstop? Any
      manual renewal or cert older than the current CA/B cap (200d in 2026) → finding.
- [ ] TLS 1.2 minimum (1.3 preferred), weak ciphers/protocols disabled across edge, ingress, mesh,
      internal? (`nmap --script ssl-enum-ciphers`.)
- [ ] HSTS on web origins; OCSP stapling enabled?
- [ ] CAA records on public zones restrict issuance to your CA(s)?
- [ ] Split-horizon: no internal hostnames in public DNS; zones scanned for dangling records?
- [ ] DNSSEC stance decided (managed, on identity-anchor zones)?
- [ ] All DNS funneled through a policy-applying, logging resolver with RPZ/DNS-firewall blocking
      malicious/newly-registered domains? Unauthorized external DoH blocked?
- [ ] DNS-tunneling surface reduced (FQDN egress allowlist, resolver funnel) and resolver logs fed
      to detection?
- [ ] Internal PKI (step-ca): short-lived certs + ACME automation; root distributed to trust stores
      (not worked around with `--insecure`); CA key HSM/KMS-protected; per-purpose intermediates?
- [ ] Cert pinning (if used) pins CA/intermediate with backup pins and a rotation story — not leaf,
      not skipped verification? Hunt `InsecureSkipVerify|--insecure|sslmode=disable`.
