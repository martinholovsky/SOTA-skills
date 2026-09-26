# 06 — DNS, TLS & PKI

Scope: DNS security (DNSSEC, DNS firewall / RPZ, DoH/DoT, split-horizon, registrar/CAA hygiene,
DNS-tunneling/exfil), TLS posture (1.3, cipher/version policy, HSTS, OCSP/CRL), certificate
lifecycle automation (ACME) and the shrinking max cert lifetimes that force it, internal PKI
(e.g. step-ca — short-lived certs, private CA trust distribution, cert-pinning
tradeoffs), and email authentication / anti-spoofing (SPF, DKIM, DMARC, MTA-STS/DANE).

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

**R1.1 — Issue certificates that say only what is public, and know who shares each one.**
- **Every served FQDN is in the SAN.** Modern clients (Chrome among them) match the name against
  `subjectAltName` and ignore the CN; a name missing from the SAN fails validation.
- **No internal names or private addresses in a public certificate.** Public CAs may not issue for
  unqualified names or reserved IPs at all (CA/B Baseline Requirements sections 4.2.2 and 7.1.2.7.12),
  but an internal host under a public domain (`db01.corp.example.com`)
  *is* issuable — and lands in Certificate Transparency logs for anyone to read. Keep internal
  names on certificates from the internal CA (§4); a server reachable by both internal and
  external names gets two certificates, and a public and an internal server never share one
  (wildcard included).
- **SHA-256 or stronger signatures.** SHA-1 and MD5-signed certificates are rejected by modern
  clients; the CA/B Forum sunset its last remaining SHA-1 use in certificates and CRLs (ballot
  SC097, effective 2026-09-15). Anything still carrying one is a finding.
- **Inventory every system that shares a certificate or key** (a SAN list or wildcard spread
  across a load balancer, a CDN and three origins). Renewal and compromise response must reach
  every holder, or the rotated certificate leaves an old copy serving — or an old key live.
- **OV/EV buys no extra transport security.** Browsers and TLS stacks treat DV, OV and EV the
  same; choose by process, not by protection, and prefer what ACME can automate (R1).
OWASP: Transport Layer Security cheat sheet, Code Review Guide v2.

## 2. TLS posture

**R2 — TLS 1.3 preferred, 1.2 minimum; everything below is disabled.** No TLS 1.0/1.1, no SSLv3.
Cipher policy: AEAD suites only (1.3 enforces this; for 1.2 allow only ECDHE + AES-GCM/ChaCha20).
Audit edges, ingress, mesh, and internal services alike.

**R2.1 — Serve the whole chain: leaf plus every intermediate.** The server must send the
intermediates up to (not including) a root the client already trusts. A desktop browser often
papers over a missing intermediate by fetching it from the certificate's AIA URL or using one it
cached, so the site "works" in the browser while any client that does not fetch AIA fails with
an unknown-issuer error — and whether a given app, API client or TLS library fetches depends on
its stack (even one `curl` build differs from another by TLS backend). Configure the full-chain
file the CA or ACME client produces, and test from a client that does no AIA fetching:
`openssl s_client` fetched nothing and failed with `unable to get local issuer certificate`
against a leaf-only server whose certificate carried a reachable AIA URL (measured 2026-09-25,
OpenSSL 3.6). OWASP: Code Review Guide v2, Go-SCP (HTTP/TLS), Secure
Coding Practices QRG.

```bash
# Hunt weak TLS quickly
nmap --script ssl-enum-ciphers -p 443 host        # flags TLS<1.2, weak ciphers, no PFS
grep -rEn 'TLSv1\.0|TLSv1\.1|SSLv3|min_version.*1\.0' ./config
```

**R3 — HSTS on web origins, short lifetimes as the revocation story, modern key types.**
`Strict-Transport-Security` with a sensible max-age (and `includeSubDomains` once you're sure) so
browsers refuse plaintext. Short-lived certs (R1) are now the primary revocation mechanism — a
47-day compromised cert expires fast. **Let's Encrypt ended OCSP** (URLs dropped from certs May
2025, responders off Aug 2025; revocation is CRL-only), so OCSP stapling is impossible on LE certs;
enable stapling only where the CA still operates OCSP. Prefer ECDSA (P-256) certs for performance;
RSA-2048+ acceptable.

**R3.1 — Enable hybrid post-quantum key exchange where the stack supports it.** Offer the
`X25519MLKEM768` hybrid group on TLS 1.3 (already default-on in modern stacks, e.g. Go 1.24+;
configurable in current OpenSSL/BoringSSL and major CDNs). It defends *confidentiality* against
harvest-now-decrypt-later — relevant for EU/long-lived-sensitive traffic — at negligible cost,
and being hybrid it's no weaker than X25519 if the PQ part is ever broken. (Signatures/PKI stay
classical for now.) See sota-code-security rules/04 §1.

**R3.2 — Set the server's TLS details explicitly; isolate legacy clients rather than weaken.**
- **Name the key-exchange group list** instead of inheriting a library default that differs by
  version: hybrid PQ first, then X25519, then NIST curves — e.g. OpenSSL `Groups =
  X25519MLKEM768:X25519:prime256v1:secp384r1`, nginx `ssl_ecdh_curve` with the same list, Apache
  `SSLOpenSSLConfCmd Groups`. (OpenSSL 3.5+ already puts `X25519MLKEM768` first in its default;
  an explicit list keeps an older or distro-patched build from silently differing.)
- **Encrypted Client Hello** (ECH, RFC 9849; keys published in DNS HTTPS/SVCB records, RFC 9848)
  encrypts the ClientHello, so on-path observers see only the client-facing server's public
  name, not the real SNI. ASVS 5.0 V12.1.5 asks for it at Level 3; elsewhere enable it where the
  CDN or stack supports it — treat support as a per-stack check, not an assumption.
- **Downgrade protection:** TLS 1.3 servers mark a downgraded ServerHello with a sentinel that
  1.3 clients must check (RFC 8446 section 4.1.3), so `TLS_FALLBACK_SCSV` (RFC 7507) matters only on
  endpoints that still serve TLS 1.2 or older — enable it there if the stack offers it.
- **Unavoidable legacy clients get their own endpoint** — separate hostname, own cipher/version
  policy, no access to sensitive data — so the main endpoint keeps its modern floor.
- **TLS 1.3-only** fits links where you control both ends: service-to-service mTLS, mesh, internal
  zero-trust paths, and APIs whose clients you ship. Public web endpoints usually keep 1.2 as the
  floor (R2).
OWASP: Transport Layer Security cheat sheet, Zero Trust Architecture cheat sheet, ASVS 5.0 V12.1.5.

## 3. DNS security

**R4 — Registrar & issuance hygiene.** (Setup is cloud-infra rules/03; the *security* controls:)
- **CAA records on every public zone** restricting issuance to your CA(s) — limits who can mint a
  cert for your domains.
- Registrar in a corporate account with MFA + transfer/registry lock for crown-jewel domains.
- **Dangling records** (pointing at deprovisioned resources) = subdomain-takeover vector;
  lifecycle-couple DNS to resources in IaC and scan zones for danglers. Not only CNAME/A:
  - **NS** delegating a subdomain to a provider zone that was deleted — whoever re-creates that
    zone owns every name beneath it.
  - **MX** to a retired mail service — the claimant receives mail for the name, including a CA's
    domain-validation mail: CA/B Baseline Requirements method 3.2.2.4.4 mails `admin@`,
    `postmaster@` etc. at the name *or any parent it prunes to*, and CAs may rely on it until
    2028-03-15 (BR 2.3.0). A stale MX can mint a publicly trusted cert.
  - **SPF** `include:`/`ip4:`/`a:` terms covering a released IP or a reclaimable host let the
    claimant send SPF-passing mail as you (R12) — prune them in the same change.
  - **Decommission order:** repoint or delete the record, wait out its TTL, *then* delete the
    resource; the reverse order opens the takeover window. Remove the name from OAuth redirect
    allowlists, CSP and CORS lists, and revoke (or let expire) its certificates.
  - **Continuous detection:** alert on every new CNAME/NS and on any target that answers
    NXDOMAIN, `404` or a provider default page; run a takeover scanner on a schedule against a
    catalogue of claimable services, checking how current it is (the widely used
    `can-i-take-over-xyz` list had its last commit in February 2025, as of 2026-09-26); monitor
    Certificate Transparency for issuance you did not request.

**R4.1 — No wildcard records unless a service needs one, and then behind a hostname allowlist.**
`*.example.com` answers for every name, including ones nobody inventoried, so it hides danglers
and widens what a claimed target can serve. If a wildcard is unavoidable, scope it to the smallest
subtree (`*.preview.example.com`), and point it at a proxy or load balancer that serves only an
explicit list of known hostnames and returns an error (not a default site) for everything else.

**R4.2 — Recognise and respond to a takeover.** Indicators: an owned hostname serving content you
did not deploy (parking page, another app); a CT-logged certificate for your name from an issuer or
account you do not use; the name resolving outside your known address ranges in proxy/WAF logs;
DMARC aggregate reports (RUA, R12) showing mail from the name that you never sent. Response:
(1) delete the record or repoint it at something you control — the fastest cut; (2) search CT for
every certificate issued for the name during the exposure window and revoke them; (3) assess
impact — cookies scoped to the parent domain, OAuth/SSO redirect URIs or CSP/CORS entries naming
the host, mail received via its MX, and how long phishing content was served; (4) notify affected
users where exposure is shown; (5) sweep every zone for the same gap. Detection content and IR
workflow are sota-detection-engineering rules/06. OWASP: Subdomain Takeover Prevention cheat sheet.

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

## 4. Internal PKI (e.g. step-ca)

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
- **mTLS client certificates come from here, not a public CA.** Public CAs are removing the TLS
  Client Authentication EKU to meet the Chrome root program's requirement for separate client and
  server PKIs (Let's Encrypt: default profile without it from 2026-02-11, no more client-auth
  issuance from 2026-07-08). A service or partner link authenticating clients with publicly
  issued certs breaks at renewal; issue them from a private CA scoped to client auth (rules/04 R4.1).

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

## 5. Email authentication & anti-spoofing (SPF / DKIM / DMARC)

Your domain is an identity anyone can forge until you publish these DNS records. An unprotected
domain gets spoofed for phishing/BEC (your brand, your users); it also lands legitimate mail in
spam. All three are DNS records this skill owns; the *content* law of marketing mail (CAN-SPAM,
consent) is sota-copywriting rules/04.

**R12 — Publish SPF, DKIM, and DMARC; DMARC is the one that actually stops spoofing.**
- **SPF** (RFC 7208): a TXT record listing IPs/includes allowed to send for the domain, ending in
  `-all` (hard fail). Watch the **10-DNS-lookup limit** — too many `include:` chains → `permerror`
  → SPF silently stops protecting. SPF alone breaks on forwarding (the relay's IP isn't yours), so
  it is necessary but not sufficient.
- **DKIM** (RFC 6376): sign outbound mail with a private key; publish the public key at
  `<selector>._domainkey`. Use a **>=2048-bit key**, rotate it (per-selector rotation lets you roll
  without downtime), and keep the private key in a secret store (sota-secrets-management), never in
  the repo.
- **DMARC** (RFC 9989, which obsoletes the original RFC 7489; aggregate/failure reporting are
  RFC 9990/9991): a `_dmarc` TXT policy that ties SPF/DKIM to the visible `From:` domain via
  **alignment** — a pass only counts if the SPF or DKIM domain *aligns* with the From domain, which
  is what blocks look-alike spoofing. **Roll the policy forward, monitoring aggregate (RUA) reports
  at each step:** `p=none` (observe only — collect reports, fix your legitimate senders) →
  `p=quarantine` → `p=reject` (the goal; forged mail is refused). Stopping at `p=none` gives
  visibility but **zero protection** — a common finding.

**R13 — Lock down transport and non-sending domains too.**
- **MTA-STS** (RFC 8461) + **TLS-RPT** (RFC 8460): MTA-STS publishes a policy requiring senders to
  use authenticated TLS to your inbound MX (defeating STARTTLS-stripping downgrade attacks);
  TLS-RPT emails you JSON reports of TLS/policy failures. Roll MTA-STS `testing` → `enforce` using
  the reports, same discipline as DMARC. **DANE for SMTP** (RFC 7672) is the DNSSEC-anchored
  alternative/complement (TLSA records) — only where the zone is DNSSEC-signed (R6).
- **Parked/non-sending domains and subdomains** are prime spoofing targets: publish
  `v=spf1 -all` + `p=reject` (and an empty DKIM) on every domain that never sends mail, so
  attackers can't send *as* them. Set the DMARC subdomain policy (`sp=`) explicitly.
- **ARC** (RFC 8617) preserves authentication results across legitimate forwarders/mailing lists
  that would otherwise break SPF/DKIM — enable it if you forward mail.

**R14 — Bulk-sender rules are now table stakes.** Since Feb 2024, Gmail and Yahoo require senders of
**5,000+ messages/day** to their users to authenticate with SPF *and* DKIM, publish DMARC (at least
`p=none`), keep the From domain aligned, offer **one-click unsubscribe** (List-Unsubscribe with
RFC 8058) on bulk mail, and hold the spam-complaint rate **below 0.3%** (aim <0.1%); Microsoft added
equivalent requirements (enforcement from 2025). Treat these as the minimum for any transactional or
marketing sender. Monitor DMARC RUA reports as a *spoofing-detection* feed as well — hand them to
sota-detection-engineering. (Logo display via **BIMI** is an IETF draft, not yet an RFC, and rewards
reaching DMARC enforcement; a Verified Mark Certificate is optional evidence, not required.)

## Audit checklist

- [ ] Are all public certs ACME/managed and auto-renewed, with expiry alerts as backstop? Any
      manual renewal or cert older than the current CA/B cap (200d in 2026) → finding.
- [ ] TLS 1.2 minimum (1.3 preferred), weak ciphers/protocols disabled across edge, ingress, mesh,
      internal? (`nmap --script ssl-enum-ciphers`.)
- [ ] **High — incomplete chain (R2.1).** Per endpoint, from a client with no AIA fetching:
      `openssl s_client -connect <host>:443 -servername <host> -verify_return_error -brief </dev/null`
      — a non-zero exit with `unable to get local issuer certificate` (error 20) while browsers
      load the site means an intermediate is missing; serve the full chain.
- [ ] **Medium — certificate content (R1.1).** Per served certificate:
      `openssl s_client -connect <host>:443 -servername <host> </dev/null 2>/dev/null | openssl x509 -noout -text | grep -E '(sha1|md5)With|DNS:[A-Za-z0-9-]+(,|$)|DNS:[^,]*\.(internal|local|lan|corp|home|localdomain)(,|$)|IP Address:(10\.|127\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)'`
      — any hit (weak signature, unqualified or internal name, private IP) is a finding; also
      read the SAN list for internal hosts under your public domain. Is there an inventory of
      every system sharing each certificate or key?
- [ ] **Medium — TLS details (R3.2).** Group list explicit and hybrid-first:
      `grep -rnE '(ssl_ecdh_curve|^[[:space:]]*Groups[[:space:]]*=|SSLOpenSSLConfCmd[[:space:]]+(Curves|Groups))' . | grep -v MLKEM`
      — each hit is a list without a hybrid PQ group. ECH stance recorded; legacy clients on a
      separate endpoint rather than a weakened main one; `TLS_FALLBACK_SCSV` wherever 1.2 or
      older is still served?
- [ ] HSTS on web origins? OCSP stapling only where the CA still runs OCSP (Let's Encrypt ended it
      Aug 2025 — don't flag its absence on LE certs)?
- [ ] CAA records on public zones restrict issuance to your CA(s)?
- [ ] Split-horizon: no internal hostnames in public DNS; zones scanned for dangling records?
- [ ] **High — dangling or claimable targets (R4).** Triage every record aimed at a
      reclaimable service; each hit needs a live target you own:
      `grep -rnE '(herokuapp\.com|azurewebsites\.net|trafficmanager\.net|azureedge\.net|elasticbeanstalk\.com|s3-website[.-][a-z0-9.-]*amazonaws\.com|github\.io|netlify\.app)' .`
      Also NS delegations and MX to retired services, SPF terms covering released hosts? New-CNAME
      and NXDOMAIN/404 alerts plus CT monitoring in place?
- [ ] **Medium — wildcard DNS (R4.1).** `grep -rnE '^\*(\.[A-Za-z0-9-]+)*\.?[[:space:]]|name *= *"\*' .`
      — each hit: required, narrowly scoped, fronted by a hostname allowlist that errors on unknown
      names?
- [ ] Takeover response (R4.2) written down: record cut, CT search + revocation, impact
      assessment (parent-domain cookies, OAuth/CSP/CORS references, MX mail, phishing duration)?
- [ ] DNSSEC stance decided (managed, on identity-anchor zones)?
- [ ] All DNS funneled through a policy-applying, logging resolver with RPZ/DNS-firewall blocking
      malicious/newly-registered domains? Unauthorized external DoH blocked?
- [ ] DNS-tunneling surface reduced (FQDN egress allowlist, resolver funnel) and resolver logs fed
      to detection?
- [ ] Internal PKI (step-ca): short-lived certs + ACME automation; root distributed to trust stores
      (not worked around with `--insecure`); CA key HSM/KMS-protected; per-purpose intermediates?
- [ ] Cert pinning (if used) pins CA/intermediate with backup pins and a rotation story — not leaf,
      not skipped verification? Hunt `InsecureSkipVerify|--insecure|sslmode=disable`.
- [ ] Email: SPF (`-all`, under the 10-lookup limit), DKIM (>=2048-bit, rotated), and DMARC
      published — and is DMARC actually enforcing (`p=quarantine`/`p=reject`), not stuck at
      `p=none`? (`dig TXT _dmarc.<domain>`.) RUA reports monitored?
- [ ] Parked/non-sending domains and subdomains publish `v=spf1 -all` + `p=reject` so they can't be
      spoofed? Inbound transport hardened (MTA-STS enforce + TLS-RPT, or DANE on DNSSEC zones)?
- [ ] Bulk senders (5,000+/day to Gmail/Yahoo): SPF+DKIM+aligned DMARC, RFC 8058 one-click
      unsubscribe, spam rate <0.3%?
