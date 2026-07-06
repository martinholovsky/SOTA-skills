<!-- last-verified: 2026-07 -->

# 07 — Framework security: boundary, authz, SSRF, CVEs

The security pass for both stacks. This consolidates the framework-specific angles;
generic web-appsec theory (injection classes, session/JWT mechanics, crypto) lives in
`sota-code-security`, secrets handling in `sota-secrets-management`, supply chain in
`sota-devsecops`. **Re-verify every CVE at use time.**

## 1. The server/client secret boundary

The one boundary unique to these frameworks, and the most common leak.

- **Build-time-inlined public env is public forever:** `NEXT_PUBLIC_*`, Nuxt
  `runtimeConfig.public.*`, and Vite `VITE_*` are substituted into the client bundle at
  build time. **A secret in any of them is a client-side secret leak (CRITICAL)** —
  and rotating it means a rebuild, not just a config change. Server secrets go in
  unprefixed env / root `runtimeConfig`, read only in server code.
- **Everything crossing server→client is public:** RSC props (Next), the serialized
  payload (`useState`/`useFetch` data in Nuxt), and anything in an inline `<script>`.
  Pass **minimal DTOs**, never raw DB rows, tokens, internal flags, or `process.env`.
- **Enforce the boundary mechanically:** `import 'server-only'` (Next/bundler) makes a
  server module a build error if imported by client code; keep data access and secrets
  behind it. In Nuxt, keep secrets in `server/` and root `runtimeConfig`.
- **Production source maps** can re-expose "server" logic and comments if uploaded
  publicly — ship them to your error tracker privately, not to the CDN.

## 2. Authorization placement (post-CVE-2025-29927)

The middleware-bypass CVE (CVE-2025-29927) made the lesson concrete: **a single authz
checkpoint at the edge is not enough.**

- **Middleware / `proxy.ts` (Next) and route middleware (Nuxt) are optimizations**, not
  the security boundary. They can be bypassed (a spoofed header; a matcher that stops
  covering a route; the Nuxt case-sensitivity bypass CVE-2026-53721) and don't re-run
  where you assume.
- **Authorize next to the data.** Every Server Action, Route Handler, RSC data read,
  and Nitro handler independently: (1) authenticates, (2) authorizes the *specific
  resource* (ownership/role), (3) validates input. A Data Access Layer (Next) or a
  shared `requireUserSession` + policy helper (Nuxt) is how you avoid forgetting.
- **IDOR is the dominant framework authz bug:** an action/route that takes an `id` and
  acts on it without checking the caller owns it. Test for it (`sota-testing` authz
  tests). Never trust a client-supplied role/flag (`?isAdmin=true`, a hidden field).
- **Layouts don't re-authorize on client navigation** (Next) — don't put the only
  check there.

## 3. SSRF surfaces specific to SSR apps

Server-side rendering means the server makes outbound requests — attacker-influenced
URLs become SSRF.

- **Image optimizers:** `next/image` `remotePatterns`/`domains` with a `**` wildcard,
  and IPX/`@nuxt/image` (path-traversal CVE-2025-54387), turn the optimizer into a
  proxy to internal URLs and the cloud metadata endpoint (169.254.169.254). Allowlist
  explicit hosts, protocols, ports, and path prefixes — and note the optimizer follows
  redirects from an allowed host *without re-validating*, so an open redirect on an
  allowlisted domain becomes SSRF.
- **User-URL fetchers:** og-image/link-preview/"import from URL" features fetch a
  user-supplied URL server-side. Validate the host against an allowlist, block private
  ranges and the metadata IP, disable/limit redirects, and set timeouts
  (`sota-code-security` rules/09, `sota-network-security` for egress control).
- **Header trust:** building absolute URLs or redirects from `Host`/`X-Forwarded-Host`
  (Next SSRF CVE-2024-34351, CVE-2025-57822; Nuxt navigate advisories) lets an attacker
  redirect server fetches. Pin a canonical base URL from config, don't reflect the Host
  header. Never pass unsanitized inbound headers into `NextResponse.next()`/redirects.
- **Open redirects:** validate `redirect`/`next`/`returnTo` targets against a
  same-origin/allowlist check before redirecting.

## 4. Consolidated framework CVE reference (verify ranges at use time)

Fingerprint exact versions from the lockfile; unpatched criticals are findings on
their own. Full detail in `rules/03` (Next/React) and `rules/05` (Nuxt/Nitro/h3).

**React / Next.js**

- **CVE-2025-55182 "React2Shell"** — RSC deserialization **RCE, CVSS 10.0**;
  react-server-dom-* fixed 19.0.1 / 19.1.2 / 19.2.1. Next surface **CVE-2025-66478**
  fixed on every 15.x/16.x line (e.g. 15.5.7 / 16.0.7); **rotate secrets if it ran
  unpatched.** Follow-up DoS/exposure: CVE-2025-55184/-55183/-67779, CVE-2026-23864.
- **CVE-2025-29927** — middleware auth bypass, CVSS 9.1; fixed
  12.3.5/13.5.9/14.2.25/15.2.3.
- Cache poisoning: CVE-2024-46982 (13.5.7/14.2.10), CVE-2025-49005 (15.3.3),
  CVE-2025-32421. SSRF: CVE-2024-34351 (14.1.1), CVE-2025-57822 (14.2.32/15.4.7),
  GHSA-c4j6-fc7j-m34r (WebSocket). CSP-nonce XSS: CVE-2026-44581 (15.5.16/16.2.5).
  next/image: CVE-2025-55173 / CVE-2025-57752 (14.2.31/15.4.5). DoS: CVE-2024-56332.

**Vue / Nuxt / Nitro / h3 / IPX / devalue**

- Nuxt cache-poisoning DoS **CVE-2025-27415** (3.16.0); `routeRules` bypass
  **CVE-2026-53721** (4.4.7/3.21.7); `<NuxtLink>` XSS CVE-2026-53722; island authz
  advisories (GHSA-hg3f-28rg-4jxj).
- IPX path traversal **CVE-2025-54387** (1.3.2/2.1.1/3.1.1).
- h3 SSE injection **CVE-2026-33128** + serveStatic traversal / middleware bypass
  (1.15.6 / 2.0.1-rc.15).
- devalue prototype pollution **CVE-2025-57820** (5.3.2), **CVE-2026-30226** (5.6.4) +
  DoS advisories. serialize-javascript CVE-2024-11831 (6.0.2).

The pattern across all of these: **the fix is almost always "upgrade."** Automated
dependency updates + a fast patch path is the actual control (`sota-devsecops`).

## 5. Framework security hygiene

- **CSP** nonce/hash-based, not `'unsafe-inline'` (`rules/06`); `nuxt-security` or a
  Next `proxy.ts` header layer. Plus the standard headers (HSTS, `nosniff`,
  `frame-ancestors`) — `sota-code-security` rules/05.
- **Supply chain:** these apps have deep dependency trees (a framework pulls hundreds of
  transitive packages). Lockfile committed, `npm audit`/`osv-scanner` in CI, provenance
  where available (`sota-devsecops`). Client-shipped dependencies are also an XSS
  surface (a compromised npm package runs in your users' browsers).
- **Error handling:** don't leak stack traces / internal paths to the client in
  production; don't render user-controlled error text as HTML (`rules/02`).
- **Rate limiting** on Server Actions / Route Handlers / Nitro routes — they're public
  endpoints (`sota-api-design` rules/07).

## Audit checklist

```bash
# Public-env secret leak (CRITICAL)
grep -rnE '(NEXT_PUBLIC_|VITE_)[A-Z_]*(SECRET|KEY|TOKEN|PASSWORD|PRIVATE)' --include='*.ts' --include='*.tsx' --include='*.vue' .
grep -rnA8 'runtimeConfig' nuxt.config.* | grep -iE 'public' -A6 | grep -iE 'secret|key|token'

# Server->client exposure & the server-only guard
grep -rn "import 'server-only'\|server/" app lib server | head
grep -rnE 'process\.env\.' --include='*.tsx' --include='*.vue' app components pages | grep -iv 'NEXT_PUBLIC\|NODE_ENV'

# Authz only at the edge? enumerate actions/handlers and check each
grep -rn "'use server'" app lib; ls -1 app/**/route.ts server/api/**/*.ts 2>/dev/null

# SSRF surfaces
grep -rn 'remotePatterns\|images:\s*{\|ipx\|@nuxt/image' next.config.* nuxt.config.* | grep -n '\*\*\|domains'
grep -rnE '\$?fetch\(|ofetch\(|axios\.|got\(' --include='*.ts' server app | grep -iE 'req\.|query|params|headers|host'
grep -rnE 'X-Forwarded-Host|req\.headers\.host|getRequestHost' --include='*.ts' server app proxy.* middleware.*

# CVE fingerprint
grep -E '"(react|react-dom|react-server-dom-webpack|next|nuxt|nitropack|h3|ipx|devalue|serialize-javascript)"' package.json
```

- [ ] No secret in `NEXT_PUBLIC_`/`VITE_`/`runtimeConfig.public`; server secrets behind `server-only`/`server/`?
- [ ] No raw rows/tokens/`process.env` crossing server→client; minimal DTOs only?
- [ ] Every Server Action / Route Handler / Nitro route authenticates, authorizes the specific resource (no IDOR), and validates input — not relying on edge middleware?
- [ ] `next/image`/IPX `remotePatterns` allowlisted to explicit hosts (no `**`); user-URL fetchers block private ranges + metadata IP + redirects?
- [ ] Absolute URLs/redirects built from config, not reflected `Host`/`X-Forwarded-Host`; redirect targets allowlisted?
- [ ] All framework + loader deps (react-server-dom, next, nuxt, h3, ipx, devalue, serialize-javascript) patched against §4; automated updates on?
- [ ] Nonce/hash CSP + standard security headers; rate limiting on public endpoints; production errors not leaked as HTML?
