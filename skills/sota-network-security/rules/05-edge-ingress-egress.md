# 05 — Edge, Ingress & Egress

Scope: WAF (OWASP CRS, Coraza/ModSecurity) incl. virtual patching and WAF telemetry, ingress/API-gateway hardening, DDoS posture (edge
scrubbing + self-hosted L3/4 kernel hardening), TLS
termination + re-encryption to backends, reverse-proxy trusted-IP / allowlist handling (behind
Cloudflare), Cloudflare-tunnel / identity-aware-proxy patterns, and **egress as a first-class
control**: default-deny egress, egress gateways/proxies, FQDN allowlisting, preventing C2/exfil, and
blocking the cloud metadata endpoint (the SSRF-meets-egress chain). A worked example used below: a reverse proxy
(e.g. Caddy) with a CRS WAF, behind a CDN (e.g. Cloudflare).

Where this sits: sota-cloud-infrastructure rules/03 owns LB/CDN *provisioning* and registrar/DNS
*setup*; this skill owns the *security posture*. rules/03 here owns the K8s-internal egress
mechanics (CNP/FQDN); this file owns the edge and the egress *discipline*. sota-api-design rules/07
owns API rate-limiting design; sota-code-security rules/01 (SSRF) and rules/05 (CORS/CSP) own the
app side.

Verified (2026-07-09): **OWASP CRS** current line **4.x** (4.25 is the first CRS-4 LTS, patched
through Q3 2027; verify latest at coreruleset.org). **CRS 3.3.x support ends Q3 2026** — a WAF still
on 3.3 is a finding. CRS runs on **OWASP ModSecurity** *and* **OWASP Coraza** (Go,
SecLang-compatible, the modern engine; both are now OWASP projects). **IMDSv2** is token-required
and account-enforceable; metadata IP `169.254.169.254` / `fd00:ec2::254`. Pin CRS version.

---

## 1. Ingress / edge proxy hardening

**R1 — One hardened, inspectable edge; backends not directly reachable.** All north-south HTTP
enters through the edge proxy (e.g. Caddy, nginx, Envoy) / ingress controller, which terminates TLS, applies the WAF,
sets security headers, and forwards. Backends accept traffic *only* from the edge/ingress (mesh authz
to the gateway identity, or NetworkPolicy allowing only the ingress namespace — rules/03/04). A
backend reachable directly bypasses the WAF, rate limits, and auth — verify by hitting a backend pod
IP directly; it must be refused.

**R2 — Minimal exposure and version hygiene at the edge.** Expose only 443 (and 80→443 redirect);
disable unused methods/modules; keep the proxy and WAF engine patched (a WAF with a known bypass CVE
is theater). Don't leak backend topology in headers (`Server`, `X-Powered-By`, internal hostnames).

**R2.0 — Scrub trace-propagation and gateway diagnostics from client responses, too.** Internal
trace and span IDs, retry counts and upstream timings hand an attacker a map of the call graph and
a timing oracle. On responses leaving the edge, strip: B3 (`X-B3-*`, single-header `b3`),
Datadog (`x-datadog-*`), W3C `traceparent`/`tracestate` wherever a service echoes them; Envoy's
`x-envoy-upstream-service-time` (the router sets it on every response) and `x-envoy-attempt-count`
(only when `include_attempt_count_in_response` is on); Kong's `X-Kong-*-Latency` and
`X-Kong-Upstream-Status` (Kong's `headers` setting controls them; `off` drops all of Kong's own,
though plugins may still add theirs). Envoy's `x-envoy-internal` and `x-envoy-external-address`
are *request* headers set for upstreams — they reach a client only if a service reflects request
headers back, so test for the echo. Mechanisms: Envoy router `suppress_envoy_headers: true` (the
router's own `x-envoy-*`; other filters may still set some) plus `response_headers_to_remove`.
Keep exactly one opaque correlation ID on the response (sota-api-design rules/07 §6 returns one
on every response): a random request ID support can look up server-side, never the trace ID
itself. OWASP: Secure Headers Project.

**R2.1 — No EOL controllers in the L7 data path.** `kubernetes/ingress-nginx` — long the most common
Kubernetes ingress controller — was retired in **March 2026** (repo read-only, **no further security
fixes**); the Kubernetes Steering/Security Response Committees state that remaining on it leaves you
vulnerable to attack. Finding it running is a High finding: migrate to a maintained **Gateway API**
implementation (`ingress2gateway` automates much of the conversion) or another maintained ingress
controller.

**R2.2 — Every hop in the chain agrees on where a request ends (no desync / request smuggling).**
When the edge and the backend disagree about message length, bytes the edge thought were one body
become the start of the backend's *next* request — which skipped the WAF, auth and routing rules
(CL.TE, TE.CL, and HTTP/2-to-1.1 downgrade variants). Require, on every tier:
- **Strict parsers, never lenient modes on a reachable hop.** RFC 9112 Sec. 6.1 and 6.3: a message with
  both `Content-Length` and `Transfer-Encoding` "ought to be handled as an error", a server that
  processes one anyway MUST close the connection afterwards, and an invalid or conflicting
  `Content-Length` list is unrecoverable (400). Prefer rejecting outright. Leniency switches that
  relax this are findings: Apache `HttpProtocolOptions Unsafe` (default `Strict`), HAProxy
  `option accept-unsafe-violations-in-http-request` (formerly `accept-invalid-http-request`), Node
  `--insecure-http-parser` / `insecureHTTPParser: true`. Measured 2026-09-25 on Node 22.22.1: a
  CL+TE request got `400` + `Connection: close` from the default parser and `200` + keep-alive with
  `insecureHTTPParser: true`.
- **HTTP/2 front, HTTP/1.1 back:** RFC 9113 Sec. 8.2.2 and 8.1.1 make an h2 message carrying
  `Transfer-Encoding` (or another connection-specific field), or a `content-length` that differs
  from the DATA it arrived with, malformed — an intermediary MUST NOT forward it. The edge must
  rebuild the 1.1 framing itself from the h2 frames, never copy a client-supplied length header.
- **No h2c upgrade through the edge.** RFC 9113 deprecated the `h2c` Upgrade token; a proxy that
  forwards the client's `Upgrade` header lets the backend switch protocols and turns the connection
  into a tunnel the proxy no longer inspects. Forward `Upgrade` only on WebSocket routes, and only
  the value `websocket`.
- **Same HTTP version handling on every tier** — one tier speaking 1.0 (no chunked) or reusing
  back-end connections differently from its peer is where the parses diverge. Keep the proxy and the
  app server patched: smuggling fixes ship as parser CVEs (e.g. sota-dotnet rules/06 §3, Kestrel).
OWASP: Secure Coding Practices QRG, WSTG-INJT-16.

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

**R4.1 — A virtual patch is an interim fix with an owner, a ticket and an end date.** When a
known vulnerability cannot be fixed in code today (sota-devsecops rules/03 "no upstream patch
available"), an edge rule can block the exploit path while the fix is built. Run it as a
repeatable flow, not an ad-hoc edit:
- **Prepare before you need it:** a pre-approved fast change path for WAF rules (who may deploy,
  what review, how to roll back), so an emergency patch does not wait on the normal release train.
- **Identify → analyse → write → test → deploy → recover.** Analyse the actual injection point
  and preconditions; write the narrowest rule that covers them — prefer an allowlist of the
  expected parameter shape over a blocklist of one payload.
- **Deliberate rule IDs.** Custom rules live in the locally reserved range (CRS documents
  1–99,999 for local use; 900,000–999,999 belongs to CRS) and each ID is recorded against the
  vulnerability ticket, e.g. in a `tag:` or `msg:` carrying the ticket key, so a log line leads
  straight to the tracked code fix.
- **Test both directions:** replay legitimate traffic (false positives) *and* evasion variants
  of the exploit — encodings, case, parameter pollution, alternate content types (false
  negatives). The person who found the vuln retests through the rule; a bypass sends the rule
  back to analysis, not to "done".
- **Recover:** the rule is removed once the code fix ships and is verified, and time-to-fix
  (ticket open → code fix live → rule removed) is tracked, so virtual patches do not become
  permanent. Generating candidate rules from DAST findings is an optional accelerator; review
  each generated rule as above.
- **Session handling at the edge is a stopgap too.** Rewriting `Set-Cookie` attributes
  (`Secure`, `HttpOnly`, `SameSite`) or session behaviour in the proxy is acceptable only while
  the application cannot change; the durable fix is in the app (sota-code-security rules/17).
OWASP: Virtual Patching cheat sheet, Session Management cheat sheet.

**R4.2 — Report every firing; review every rule that never fires.** Each virtual patch and custom
rule gets a match counter and an alert: a firing means someone is probing that known
vulnerability now, which is worth knowing even when the block succeeded. The inverse is a signal
as well: a rule with zero matches over a period in which the exploit path saw traffic may not be
in force at all (wrong phase, wrong variable, detection-only, a route that bypasses the WAF) —
prove it with a harmless test request that should match (a control not in force:
sota-code-security rules/14). OWASP: Virtual Patching cheat sheet.

**R4.3 — WAF events are security telemetry, shipped and alerted on.** Match and block events go
to the central logging/SIEM pipeline (sota-detection-engineering), not only to a local file: in
Coraza and ModSecurity that means an audit engine set to `RelevantOnly` (or `On`), never `Off`
(Coraza documents `Off` as its default). Alert on spikes of blocked payloads per rule or client,
and on anomalies against the baseline. Known scanner and attack-tool fingerprints (CRS
`REQUEST-913-SCANNER-DETECTION`, e.g. rule 913100 on scanner user agents at `CRITICAL` severity)
are recorded as high-severity security events for correlation, not silently dropped. OWASP:
Logging Vocabulary cheat sheet, Secure Cloud Architecture cheat sheet.

**R4.4 — Know the WAF's coverage limits; use a positive model where it matters.** A negative
(signature) model only catches payload shapes it knows. For sensitive endpoints — auth,
payments, admin, key APIs — add a positive model: only known routes and methods pass, and only
the expected parameters with expected types and lengths (an OpenAPI schema is a good source);
add custom rules for the specific stack in front of it. Many WAFs inspect only the WebSocket
upgrade handshake, not the frames that follow — confirm what yours inspects; if frames are not
inspected, message validation, authorisation and logging stay in the server (sota-api-design
rules/05). OWASP: DSOMM, Secure Cloud Architecture cheat sheet, WebSocket Security cheat sheet.

## 3. TLS termination + re-encryption

**R5 — Terminate TLS at the edge; re-encrypt to backends crossing a trust boundary.** Edge
terminates the public cert (auto-managed — rules/06), inspects, then originates a *new* TLS/mTLS
connection to the backend. Plaintext from edge→backend across the cluster network is the
plaintext-internal-traffic problem (rules/04) at the ingress hop. Inside a mesh, the edge gateway
hands off to mTLS automatically; otherwise configure backend TLS explicitly.

## 4. Reverse-proxy trusted-IP handling (behind a CDN)

**R6 — Trust `X-Forwarded-For` / `CF-Connecting-IP` ONLY from your proxy's real IPs, or attackers
spoof client identity.** Behind a CDN → edge proxy → app (e.g. Cloudflare → Caddy), two recurring bugs:
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

**R8 — Absorb at the edge, rate-limit per-identity, cap autoscaling.** A scrubbing edge (e.g.
Cloudflare, a cloud provider's DDoS tier, or an Anycast scrubbing provider) absorbs L3/4 and much
L7; add WAF rate-limiting rules and per-route/per-identity limits (design owned by
sota-api-design rules/07). Cap autoscaling so a flood can't scale your bill or cluster infinitely
(economic/"yo-yo" DoS). "We never considered DDoS" is the finding; record the stance. Best DDoS
surface is none — keep non-public surfaces non-public (tunnels, IAP). Cloud L3/4 mitigation posture
(Shield/Cloud Armor/Azure DDoS tiers) is sota-cloud-infrastructure rules/03 §10; this rule owns the
edge you operate.

**R8.1 — Self-hosted / bare-metal edge: harden the kernel, you are the scrubber.** When there is no
Anycast provider in front (e.g. a bare-metal edge exposed directly), L3/4 defense is yours.
Baseline, matched to the exposed protocols:
- **SYN floods:** enable TCP **SYN cookies** (`net.ipv4.tcp_syncookies=1`) — the kernel answers with
  a cryptographic cookie instead of holding half-open state when the SYN backlog overflows. For a
  high-rate edge, add a **synproxy** (nftables) in front of the listener so flood SYNs never create
  conntrack entries: it needs `tcp_syncookies` **and** `tcp_timestamps` on, `notrack` on SYNs in the
  raw table, `nf_conntrack_tcp_loose=0`, and a rule matching `ct state invalid,untracked`
  (per the nftables synproxy wiki). Note syncookies disable some TCP options — expected trade-off
  under attack, not a steady-state default concern.
- **Conntrack exhaustion** is its own DoS: a stateful firewall drops new flows once
  `nf_conntrack_max` fills. Size it (and the hashsize) to expected concurrency, alert on
  `nf_conntrack_count` / "table full" drops, and `notrack` high-volume stateless traffic so it never
  consumes a slot.
- **Anti-spoofing:** enable **reverse-path filtering** (`rp_filter`, strict where routing allows;
  RFC 3704) so spoofed-source packets are dropped at ingress.
- **Don't be an amplifier (BCP 38 / RFC 2827):** never expose an **open** UDP reflector — recursive
  DNS resolver, NTP `monlist`, memcached, SSDP, chargen — to the internet; bind them internally or
  require auth. An exposed open resolver makes you a weapon in someone else's reflection attack and a
  target for the return traffic. Prefer TCP or authenticated protocols on the public edge; rate-limit
  or drop unsolicited UDP you don't serve.

**R8.2 — Cap bytes, not only requests; know your pipe before the flood.** Request-rate limits do
nothing against a few clients pulling large responses or pushing large bodies. At the edge:
- **Per-client data caps:** a request-body ceiling (nginx `client_max_body_size`; `0` disables the
  check), a response-rate limit (nginx `limit_rate`, bytes per second — per *request*, so pair it
  with `limit_conn` on the client address, or two connections double it), and a connection cap
  per client. The inverse — a *minimum* rate that drops slow senders — is sota-code-security
  rules/06 §5.
- **An overall bandwidth ceiling** per service or tenant, so one hot path cannot starve the rest
  of the uplink.
- **Self-hosted / on-prem uplink: ask the provider before you need it.** What volume can the ISP or
  transit provider absorb, is there upstream scrubbing or blackholing on request, and is there
  more than one ingress path? A volumetric flood larger than your uplink is lost before your
  kernel sees it; R8.1 cannot help there.
OWASP: Denial of Service cheat sheet.

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
"connection refused." An on-prem cluster has no IMDS, but keep the egress default-deny so a future
cloud burst is safe by default.

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
      not detection-only-forever, not unpatched? A ruleset still on CRS 3.3.x (end of support
      Q3 2026) is a finding.
- [ ] **Medium — trace IDs and gateway diagnostics leak to clients (R2.0).** Per public host:
      `curl -sI https://<host>/ | grep -iE '^(x-b3-|b3:|x-datadog-|x-envoy-|x-kong-(upstream|proxy|response|admin)-latency|x-kong-upstream-status|traceparent:|tracestate:)'`
      — every hit is a finding; an opaque request-ID header is the one allowed. Repeat on an
      error path (4xx/5xx) and an echo endpoint, where reflected request headers show up.
- [ ] **Medium — virtual patches without lifecycle (R4.1).** List local-range custom rule IDs:
      `grep -rnE "id:[1-9][0-9]{0,4}[,\"']" --include='*.conf' .` — each needs a linked ticket,
      an owner, false-negative (evasion) test evidence, and a removal date tied to the code fix.
- [ ] **Medium — virtual patches nobody watches (R4.2).** Firings per rule over the window:
      `grep -oE '\[id "[0-9]+"\]' <waf-error-log> | sort | uniq -c | sort -n` — every virtual patch
      has an alert on match; a patch with zero matches while its route saw traffic gets a
      test request that should match.
- [ ] **High — WAF events not shipped (R4.3).** `grep -rnE '^[[:space:]]*SecAuditEngine[[:space:]]+Off' .`
      (or the directive absent — Coraza defaults to `Off`). Are block/match events in the SIEM with
      spike alerts, and scanner fingerprints (CRS 913xxx) raised as high-severity events?
- [ ] **Medium — WAF coverage (R4.4).** Sensitive routes on a positive model (known routes,
      methods, parameters)? WebSocket routes: does the WAF inspect frames, and if not, is message
      validation and logging server-side?
- [ ] Is the ingress controller maintained? `kubernetes/ingress-nginx` is EOL (March 2026, no
      security fixes) → High; migrate to a maintained Gateway API implementation.
- [ ] **High — request smuggling / desync (R2.2).** Any lenient HTTP parser on a reachable hop:
      `grep -rnE 'HttpProtocolOptions +Unsafe|accept-(invalid-http-request|unsafe-violations-in-http-request)|insecure-http-parser|insecureHTTPParser *: *true' .`
      Upgrade forwarded outside WebSocket routes (review each hit; h2c smuggling):
      `grep -rnE 'proxy_set_header +Upgrade +\$http_upgrade' .`
      Live check per tier — CL+TE must yield `400` or a closed connection, never keep-alive:
      `printf 'POST / HTTP/1.1\r\nHost: h\r\nContent-Length: 4\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n' | nc -w 2 <host> <port>`
      (TLS: `openssl s_client -quiet -connect <host>:443`). Also test h2 front-ends with a
      `transfer-encoding` header and a mismatched `content-length`: both must be refused.
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
- [ ] **Medium — byte caps disabled (R8.2).** `grep -rnE '(client_max_body_size|limit_rate)[[:space:]]+0[[:space:]]*;' .`
      — each hit removes a cap. Per-client connection cap and an overall bandwidth ceiling set?
      Self-hosted uplink: ISP/transit absorption capacity, scrubbing and ingress diversity on
      record?
- [ ] Self-hosted/bare-metal edge with no scrubbing provider in front: `tcp_syncookies` on,
      `rp_filter` enabled, `nf_conntrack_max` sized + drops alerted, synproxy on high-rate TCP
      listeners? (`sysctl net.ipv4.tcp_syncookies net.ipv4.conf.all.rp_filter`)
- [ ] No open UDP reflector (recursive DNS, NTP monlist, memcached, SSDP, chargen) exposed to the
      internet — you are not an amplification source (BCP 38)?
