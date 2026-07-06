<!-- last-verified: 2026-07 -->

# 03 — Next.js: App Router, Server Actions, caching, CVEs

Baseline: Next.js 16.x (App Router). Pages Router still ships but is not the
recommended model for new code. Hydration is in `rules/06`; the consolidated
security boundary and CVE reference in `rules/07`. **Re-verify every CVE range at
use time** — the version numbers below were primary-sourced 2026-07.

## 1. Server vs Client Components — the boundary is everything

App Router components are **Server Components by default**. They run only on the
server, can be `async`, and can touch the database, filesystem, and secrets directly.

- **`"use client"` marks the boundary**, not a single component — everything imported
  into a `"use client"` module becomes client code. Push the directive to the leaves
  that actually need interactivity (state, effects, event handlers, browser APIs).
- **Everything a Server Component passes as a prop to a Client Component is serialized
  into the RSC payload and shipped to the browser** — it is public. The canonical
  anti-pattern is passing a whole DB row (with password hashes, internal flags) when
  the client needs two fields. Pass minimal DTOs.
- **Keep secrets and data access server-side.** Mark server-only modules with
  `import 'server-only'` so importing them from a Client Component is a *build error*.
  Only server code should read `process.env` secrets.
- Functions and class instances can't cross the boundary; React throws. That's a
  feature — it stops you leaking server closures to the client.

## 2. Server Actions — public endpoints with ergonomic syntax

A `"use server"` function is compiled into a **public HTTP POST endpoint**. This is
the highest-value Next security topic.

```tsx
'use server';
export async function deletePost(id: string) {
  const user = await requireUser();           // 1. authenticate — every time
  const post = await db.post.find(id);
  if (post.authorId !== user.id) throw new Error('forbidden'); // 2. authorize (ownership)
  const parsed = z.string().uuid().parse(id); // 3. validate input
  await db.post.delete(parsed);
}
```

- **Every action re-checks authn + authz + input**, even if it's never imported into
  a page and even if it "looks internal." Next's dead-code elimination and encrypted,
  per-build action IDs raise the bar but the docs are explicit: treat every action as
  externally reachable. Missing authz here is IDOR (HIGH).
- **Validate all input with a schema** (Zod/Valibot). `formData`, arguments, and any
  reflected header are attacker-controlled. Never trust a hidden field like
  `isAdmin`.
- **Return values are serialized to the client** — filter them the same as a prop
  (don't return the raw row).
- **CSRF:** Next checks Origin vs Host for actions; behind a proxy set
  `experimental.serverActions.allowedOrigins`. Closure-captured variables are
  encrypted per build (key `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` — set it explicitly
  for multi-replica deploys so restarts don't invalidate in-flight forms);
  `.bind()` arguments are **not** encrypted. Don't rely on encryption for authz.
- **Route Handlers** (`route.ts`) are the same story — treat every one as a public
  API endpoint (`sota-api-design`, `sota-code-security`).

## 3. Authorization placement — the Data Access Layer

Post-CVE-2025-29927 (middleware bypass, below), the official guidance is unambiguous:
**do not put your only authorization check in middleware or a layout.**

- **`proxy.ts`/middleware** (renamed from `middleware.ts` in Next 16; `proxy.ts`
  defaults to the Node runtime) is for coarse, optimistic checks (redirect if no
  session cookie) — an optimization, not the security boundary. It can be bypassed
  (CVE-2025-29927) and its matcher can silently stop covering a route.
- **Layouts don't re-render on client navigation**, so a layout-level auth check is
  not re-evaluated as the user navigates — insufficient on its own.
- **Data Access Layer (DAL):** a `server-only` module that every read/write goes
  through, which authenticates, authorizes, and returns minimal DTOs. Authorization
  lives *next to the data*. This is the pattern the Next docs recommend for new apps.
- **Taint APIs** (`experimental_taintObjectReference`/`taintUniqueValue`) are still
  experimental (`experimental.taint`) — a backstop that throws if a tainted object
  reaches the client, not a primary control (cloning/deriving escapes the taint).

## 4. The caching model (know what's cached, and when)

The caching model changed materially; stale mental models cause both bugs and leaks.

- **`fetch` is not cached by default since v15.** Opt in per call
  (`fetch(url, { cache: 'force-cache' })` or `next: { revalidate: N }`) or via route
  config. Don't assume memoized fetches.
- **Cache Components** (`cacheComponents: true` in `next.config`, formerly the
  experimental `dynamicIO`) turns on the `"use cache"` directive and makes **PPR the
  default**: a static shell plus dynamic holes streamed through `<Suspense>`. Any
  uncached dynamic data *outside* a Suspense boundary is a build error.
- **`"use cache"`** caches a function/component's output; defaults are ~5 min client
  stale / ~15 min server revalidate; tune with `cacheLife()` and tag with
  `cacheTag()`. Cache keys include the build ID, the function ID, and serialized
  arguments/closed-over values — **so a user-specific value in the closure becomes
  part of the key** (correct) but caching a *component that renders per-user data
  without keying on the user* leaks across users (MEDIUM–HIGH). Variants:
  `use cache: private` for per-user.
- **Invalidation:** `revalidateTag`/`revalidatePath` (and `updateTag` with Cache
  Components) from a Server Action or Route Handler. **ISR** (route `revalidate`) still
  works.
- **Security rule:** never cache a personalized page at a shared cache. If a route
  reads the session/cookies, it must be dynamic or explicitly `private`. Cache
  poisoning has been a repeated Next CVE class (below) — CDNs also drop `Vary`, so
  don't rely on it (`rules/06`).

## 5. Next.js CVE reference (verify ranges at use time)

Unpatched, several of these are CRITICAL on their own. Fingerprint the exact version
from the lockfile and compare.

| CVE / advisory | Class | Fixed in | Note |
|---|---|---|---|
| **CVE-2025-55182** ("React2Shell") | **RSC deserialization RCE, CVSS 10.0** | react-server-dom-* 19.0.1 / 19.1.2 / 19.2.1 | The React-level flaw; exploited in the wild within hours of 2025-12-03 disclosure |
| **CVE-2025-66478** (GHSA-9qr9-h5gf-34mp) | Next.js surface of React2Shell | 15.0.5/15.1.9/15.2.6/15.3.6/15.4.8/15.5.7/16.0.7 | Next 15.x/16.x/14.3-canary.77+ affected; **rotate secrets if it ran unpatched** |
| CVE-2025-55184 / -55183 / -67779 / CVE-2026-23864 | RSC DoS + Server-Function source exposure (React2Shell follow-ups) | see 2025-12-11 + later advisories | Upgrade to the latest patch on your line |
| **CVE-2025-29927** (GHSA-f82v-jwr5-mffw) | **Middleware auth bypass** via `x-middleware-subrequest`, CVSS 9.1 | 12.3.5/13.5.9/14.2.25/15.2.3 | Self-hosted; strip the header at the proxy; don't rely on middleware for authz |
| CVE-2024-46982 (GHSA-gp8f-8m3g-qvj9) | Cache poisoning (Pages Router) | 13.5.7 / 14.2.10 | + CVE-2025-32421 low-sev bypass (<15.1.6) |
| CVE-2025-49005 (GHSA-r2fc-ccr8-96c4) | RSC cache poisoning via missing `Vary` | 15.3.3 | App Router |
| CVE-2024-34351 (GHSA-fr5h-rqp8-mj6g) | SSRF in Server Actions via Host header | 14.1.1 | Self-hosted redirect handling |
| CVE-2025-57822 (GHSA-4342-x723-ch2f) | Middleware redirect → SSRF | 14.2.32 / 15.4.7 | Unsanitized headers into `NextResponse.next()` |
| CVE-2024-56332 (GHSA-7m27-7ghc-44w9) | Server Actions DoS | 13.5.8/14.2.21/15.1.2 | |
| CVE-2026-44581 (GHSA-ffhc-5mcf-pf4q) | XSS in CSP-nonce apps | 15.5.16 / 16.2.5 | Malformed nonce reflected; cache-poisonable |
| CVE-2025-55173 (GHSA-xv57-4mr9-wg8v) / CVE-2025-57752 | next/image content injection / cross-user image cache confusion | 14.2.31 / 15.4.5 | Precondition: permissive `remotePatterns`/`domains` |
| GHSA-c4j6-fc7j-m34r + 2026-05 batch | WebSocket-upgrade SSRF; proxy/segment-prefetch bypasses; Cache-Components DoS | latest 15.5.x / 16.2.x | No confirmed CVE on the WS-SSRF advisory; upgrade to current patch |

**next/image SSRF:** `remotePatterns` with a `**` wildcard host turns the
`/_next/image` optimizer into a blind-SSRF proxy (reachable internal URLs / metadata
endpoint), and it follows redirects from an allowed host without re-validating — an
open redirect on an allowlisted domain becomes SSRF. Allowlist explicit hosts,
protocols, and paths (`rules/07`).

## Audit checklist

```bash
# Exact version — compare to the CVE table
node -e "console.log(require('./node_modules/next/package.json').version)"
grep -E '"(react|react-dom|react-server-dom-webpack|next)"' package.json

# Server Actions / Route Handlers — each must authn+authz+validate
grep -rn "'use server'" --include='*.ts' --include='*.tsx' app lib
grep -rln 'export async function (GET|POST|PUT|DELETE|PATCH)' app  # route.ts handlers

# Authz only in middleware/layout? (finding)
ls middleware.* proxy.* 2>/dev/null; grep -rn 'getServerSession\|auth()\|requireUser' app | head

# Server->client data exposure: whole objects as props, env on client
grep -rnE 'process\.env\.(?!NEXT_PUBLIC_)' --include='*.tsx' app components | grep -i client
grep -rn "import 'server-only'\|import \"server-only\"" app lib   # want: present in data layer

# next/image SSRF precondition
grep -rn "remotePatterns\|images:\s*{" next.config.* | grep -n '\*\*\|domains'

# Caching of personalized routes
grep -rn "use cache\|cacheComponents\|force-cache\|revalidate\|Cache-Control" app next.config.*
```

- [ ] Exact Next + react-server-dom versions patched against CVE-2025-55182/-66478 and CVE-2025-29927?
- [ ] Every Server Action and Route Handler authenticates, authorizes (ownership/IDOR), and schema-validates input — not relying on middleware?
- [ ] No secrets or whole DB rows crossing server→client; data layer marked `server-only`; DTOs minimal?
- [ ] Authorization enforced at the data layer, not only in `proxy.ts`/middleware or a layout?
- [ ] Caching understood per route; no personalized page cached at a shared cache; `use cache` keyed per-user where needed?
- [ ] `next/image` `remotePatterns` limited to explicit trusted hosts (no `**`)?
- [ ] `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` set for multi-replica deploys; `allowedOrigins` configured behind a proxy?
