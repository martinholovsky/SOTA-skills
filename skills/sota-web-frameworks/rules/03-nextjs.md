# 03 — Next.js: App Router, Server Actions, caching, CVEs

Written for Next.js 16 (App Router); verify the latest at nextjs.org/blog. Pages Router still ships but is not the
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
- **Most** functions and class instances can't cross the boundary; React throws. That's a
  feature — it stops you leaking server closures to the client. Know the exceptions before
  you report one as a violation: React's serializable list **does** include `Date`, `Map`,
  `Set`, `TypedArray`, `ArrayBuffer`, promises, JSX elements, and **functions that are
  Server Functions** (`'use server'`). What is not serializable is a function *not* exported
  from a client-marked module or marked `'use server'`, a class, an instance of any
  non-built-in class, a null-prototype object, and a non-global symbol
  ([React: serializable types](https://react.dev/reference/rsc/use-client), verified
  2026-09-16). The minimal-DTO advice below stands on its own security merits.

## 2. Server Actions — public endpoints with ergonomic syntax

A `"use server"` function is compiled into a **public HTTP POST endpoint**. This is
the highest-value Next security topic.

```tsx
'use server';
export async function deletePost(id: string) {
  const user = await requireUser();           // 1. authenticate — every time
  const postId = z.string().uuid().parse(id); // 2. validate input before any query
  const post = await db.post.find(postId);
  if (!post || post.authorId !== user.id) throw new Error('forbidden'); // 3. authorize (ownership)
  await db.post.delete(postId);
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
- **CSRF:** Next checks Origin vs Host (or `x-forwarded-host`) for actions; extra hosts go in
  `experimental.serverActions.allowedOrigins`. That list *is* the action CSRF check, so
  keep it to the hosts users actually load the app from: the public host, and a front
  door that forwards its own host instead of `x-forwarded-host` (when it forwards the
  public host, no entry is needed). Entries match the Origin's host[:port]; `*` covers
  one label and `**` one or more, so `*.example.com` trusts every subdomain. A wildcard
  over a suffix where others can get a subdomain (a hosting platform's shared preview
  domain, a user-content zone) lets any page there post to your actions — HIGH; list
  exact hosts. The check lets an Origin-less request through with a warning, so it
  sits beside `SameSite` cookies, not in place of them ([Next.js: serverActions](https://nextjs.org/docs/app/api-reference/config/next-config-js/serverActions),
  read 2026-09-25, v16.3.6). OWASP: Nextjs Security cheat sheet. Closure-captured variables are
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
- **Fewer endpoints, fewer checks to forget.** A Server Component can call the DAL
  directly, so a `route.ts` whose only consumer is your own server code (a page doing
  `` fetch(`${BASE_URL}/api/...`) ``) adds an internet-reachable endpoint and buys nothing.
  Delete it and call the DAL function; keep Route Handlers for real external callers
  (browsers, webhooks, third parties), each with its own authn/authz. OWASP: Nextjs
  Security cheat sheet.
- **Draft Mode's enable handler is a public GET** (`draftMode().enable()` sets the
  `__prerender_bypass` cookie, which skips every cache layer for that browser). Before
  enabling: compare the CMS's shared secret (high-entropy, from env) in constant time
  (`crypto.timingSafeEqual` on equal-length buffers or digests — it throws on a length
  mismatch), look the requested id/slug up in the CMS and refuse unknown ones, then
  redirect to the path taken **from that record**, never from the query string (an open
  redirect otherwise; the docs' sample redirects from the record but compares with `!==`)
  ([Next.js: Draft Mode](https://nextjs.org/docs/app/guides/draft-mode), read
  2026-09-25, v16.3.6). OWASP: Nextjs Security cheat sheet.

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
- **What a per-user cache key is made of.** `cookies()`/`headers()` cannot be called
  inside a `"use cache"` scope (it fails with `next-request-in-use-cache`); the documented
  pattern is to read them outside and pass *values* in as arguments — and every
  argument becomes key material. So pass **dimensions the server has already verified**
  (user or tenant id, a role/permission version that changes on revocation, locale),
  never the raw session cookie, bearer token or JWT: a credential as a key is written
  into the cache handler's storage (in memory, or Redis/KV with `use cache: remote`),
  and a key that stays the same after a role is revoked keeps serving the
  pre-revocation result until it expires (HIGH when the cached output is authorized
  data). Verify the session first, then call the cached function with the derived ids
  ([Next.js: use cache](https://nextjs.org/docs/app/api-reference/directives/use-cache),
  read 2026-09-25, v16.3.6). OWASP: Nextjs Security cheat sheet.
- **Invalidation, and the allowed context differs per API:** `revalidateTag` and
  `revalidatePath` work from a Server Action **or** a Route Handler. **`updateTag` is
  Server-Actions-only** — calling it from a Route Handler *throws*
  (`updateTag can only be called from within a Server Action`), so reach for
  `revalidateTag` there. This is an invocation-context rule, not a caching-style
  preference ([Next.js: updateTag](https://nextjs.org/docs/app/api-reference/functions/updateTag),
  verified 2026-09-16). **ISR** (route `revalidate`) still works.
- **Invalidation is a privileged mutation.** Each call forces origin work (the next
  visit to every page using the tag re-renders), so whoever can trigger it can drive
  load at your origin and CMS. The docs' Route Handler sample revalidates whatever
  `?tag=` a caller sends, with no check. Authenticate and authorize the caller; map a
  known name to a fixed tag/path from an allowlist instead of passing a request value
  through; verify a CMS webhook's signature (`sota-api-design` rules/06) and rate-limit
  the endpoint ([Next.js: revalidateTag](https://nextjs.org/docs/app/api-reference/functions/revalidateTag),
  read 2026-09-25). OWASP: Nextjs Security cheat sheet.
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
| **GHSA-9qr9-h5gf-34mp** (Next surface of CVE-2025-55182; CVE-2025-66478 was REJECTED as its duplicate) | Next.js surface of React2Shell | 15.0.5/15.1.9/15.2.6/15.3.6/15.4.8/15.5.7/16.0.7 | Next 15.x/16.x/14.3-canary.77+ affected; **rotate secrets if it ran unpatched** |
| CVE-2025-55184 / -55183 / -67779, CVE-2026-23864 / -23869 / -23870 / -44907 | RSC DoS + Server-Function source exposure (React2Shell follow-ups) | react-server-dom-* 19.0.8 / 19.1.9 / 19.2.8 (CVE-2026-44907, 2026-07-24) | Next declares no react-server-dom dependency — it ships a compiled copy under `next/dist/compiled/` — so a Next app follows the Next floor, not this one |
| **CVE-2025-29927** (GHSA-f82v-jwr5-mffw) | **Middleware auth bypass** via `x-middleware-subrequest`, CVSS 9.1 | 12.3.5/13.5.9/14.2.25/15.2.3 | Self-hosted; strip the header at the proxy; don't rely on middleware for authz |
| CVE-2024-46982 (GHSA-gp8f-8m3g-qvj9) | Cache poisoning (Pages Router) | 13.5.7 / 14.2.10 | + CVE-2025-32421 low-sev bypass (<15.1.6) |
| CVE-2025-49005 (GHSA-r2fc-ccr8-96c4) | RSC cache poisoning via missing `Vary` | 15.3.3 | App Router |
| CVE-2024-34351 (GHSA-fr5h-rqp8-mj6g) | SSRF in Server Actions via Host header | 14.1.1 | Self-hosted redirect handling |
| CVE-2025-57822 (GHSA-4342-x723-ch2f) | Middleware redirect → SSRF | 14.2.32 / 15.4.7 | Unsanitized headers into `NextResponse.next()` |
| CVE-2024-56332 (GHSA-7m27-7ghc-44w9) | Server Actions DoS | 13.5.8/14.2.21/15.1.2 | |
| CVE-2026-44581 (GHSA-ffhc-5mcf-pf4q) | XSS in CSP-nonce apps | 15.5.16 / 16.2.5 | Malformed nonce reflected; cache-poisonable |
| CVE-2025-55173 (GHSA-xv57-4mr9-wg8v) / CVE-2025-57752 | next/image content injection / cross-user image cache confusion | 14.2.31 / 15.4.5 | Precondition: permissive `remotePatterns`/`domains` |
| CVE-2026-44578 (GHSA-c4j6-fc7j-m34r) + 2026-05-11 batch | WebSocket-upgrade SSRF; proxy/segment-prefetch bypasses (CVE-2026-44574/-44575/-44573); Cache-Components DoS | 15.5.16 / 16.2.5 (incomplete-fix follow-up CVE-2026-45109: 15.5.18 / 16.2.6) | |
| 2026-07-22 batch: CVE-2026-64645 (GHSA-p9j2-gv94-2wf4), CVE-2026-64649 (GHSA-89xv-2m56-2m9x), CVE-2026-64641, CVE-2026-64642 (16.x only), CVE-2026-64643/-64644/-64646/-64647/-64648 | SSRF via rewrite destination host; Server Actions SSRF on custom servers; Server Actions DoS; Turbopack proxy bypass; cache confusion; endpoint disclosure | 15.5.21 / 16.2.11 | Nine advisories (published 2026-07-21), four High |
| **GHSA-2xp9-vwfh-vxw4** (2026-09-08) / **CVE-2026-75604** (GHSA-p293-qw3h-jr36) | **Unauthenticated RCE**: Image Optimization API with AVIF; Windows-hosted servers | **15.5.24 / 16.3.3** | Both critical. As of 2026-09-26 this is the floor: **Next ≥ 15.5.24 / ≥ 16.3.3**; newer advisories: the [vercel/next.js advisory feed](https://github.com/vercel/next.js/security/advisories) |

**next/image SSRF:** `remotePatterns` with a `**` wildcard host turns the
`/_next/image` optimizer into a blind-SSRF proxy (reachable internal URLs / metadata
endpoint), and it follows redirects from an allowed host without re-validating — an
open redirect on an allowlisted domain becomes SSRF. Allowlist explicit hosts,
protocols, and paths (`rules/07`).

## Audit checklist

- [ ] **Exact version — compare to the CVE table** —
      `node -e "console.log(require('./node_modules/next/package.json').version)"` ;
      `grep -E '"(react|react-dom|react-server-dom-webpack|next)"' package.json`
- [ ] **Server Actions / Route Handlers — each must authn+authz+validate** —
      `grep -rn "'use server'" --include='*.ts' --include='*.tsx' app lib` ;
      `grep -rlnE 'export async function (GET|POST|PUT|DELETE|PATCH)' app` (-E: without it the
      parens are LITERAL in BRE and this silently finds 0)
- [ ] **Authz only in middleware/layout? (finding)** —
      `find . -maxdepth 2 -path ./node_modules -prune -o \( -name 'middleware.*' -o -name 'proxy.*' \) -type f -print; grep -rnE 'getServerSession|auth\(\)|requireUser' app | head`
- [ ] **Server->client data exposure: whole objects as props, env on client** —
      `grep -rnE 'process\.env\.[A-Z0-9_]+' --include='*.tsx' app components | grep -v 'NEXT_PUBLIC_'`
      (no negative lookahead: POSIX ERE has none, so `(?!...)` is a syntax error or a literal —
      list the env reads, then exclude the public prefix with a second pass). **NB this is a
      CANDIDATE list, not an absence proof**: it greps text, not the Client Component module
      graph; a server module imported by a client one is invisible to it —
      `grep -rn "import 'server-only'\|import \"server-only\"" app lib` (want: present in data
      layer)
- [ ] **next/image SSRF precondition** —
      `find . -maxdepth 2 -path ./node_modules -prune -o -name 'next.config.*' -type f -exec grep -HnE "hostname:[[:space:]]*['\"][*]{1,2}['\"]|domains:" {} +`
      (matches a multi-line `remotePatterns` entry; a subdomain wildcard such as `'*.example.com'` is read by eye)
- [ ] **Caching of personalized routes** —
      `grep -rnE "use cache|cacheComponents|force-cache|revalidate|Cache-Control" app; find . -maxdepth 2 -path ./node_modules -prune -o -name 'next.config.*' -type f -exec grep -HnE "use cache|cacheComponents|force-cache|revalidate|Cache-Control" {} +`
- [ ] **Credential used as a `use cache` key (HIGH)** — list files with the directive, then
      cached-function signatures that take a credential:
      `grep -rlE "[\"']use cache" app lib src | xargs grep -HniE 'async[^(]*\([^)]*(token|session|cookie|authorization|bearer|jwt)'`
      (single-line signatures only; a hit is a candidate — confirm the argument is the raw
      credential, not an id derived from it)
- [ ] **Draft Mode enable handler: plain `!=` secret check or redirect to a request value
      (MEDIUM; HIGH if the secret check is missing)** — find it with
      `grep -rln 'draftMode' app src`, then
      `grep -rnE "secret[[:space:]]*!=|!=[=]?[[:space:]]*secret|redirect\((slug|path|target|url|searchParams|request|req)[.)!]|redirect\(new URL\((slug|path|target|url|searchParams)" --include='*.ts' --include='*.js' --exclude-dir=node_modules .`
      (want: constant-time compare, an unknown slug refused, `redirect(record.slug)`)
- [ ] **Cache invalidation from a request value (MEDIUM)** — calls whose first argument
      is not a literal:
      `` grep -rnE "(revalidateTag|revalidatePath|updateTag)\([^'\"\`)]" --include='*.ts' --include='*.tsx' --include='*.js' --exclude-dir=node_modules . ``
      — a hit is a candidate; confirm the value comes from an allowlist and the caller is
      authenticated (a webhook: signature-verified) and rate-limited
- [ ] **Wildcard `allowedOrigins` (HIGH over a shared suffix)** —
      `find . -maxdepth 2 -path ./node_modules -prune -o -name 'next.config.*' -type f -exec grep -HnE "allowedOrigins.*['\"][*]" {} +` (single-line arrays; read a
      multi-line one by eye) — each `*`/`**` entry must be a zone only you can create hosts in
- [ ] **Route Handlers that only feed your own Server Components (LOW, surface)** — server
      files fetching the app's own `/api/`:
      `grep -rLE "^.use client" --include='*.tsx' --include='*.ts' --include='*.jsx' --include='*.js' app src 2>/dev/null | xargs grep -HnE 'fetch\(.(https?://(localhost|127\.0\.0\.1)[^/]*|\$\{[^}]*\})/api/'`
      — if no browser or third party calls that handler, replace it with a DAL call

- [ ] Exact Next + react-server-dom versions patched against CVE-2025-55182 (Next: GHSA-9qr9-h5gf-34mp), CVE-2025-29927 and the 2026-09-08 RCEs (Next ≥ 15.5.24 / ≥ 16.3.3)?
- [ ] Every Server Action and Route Handler authenticates, authorizes (ownership/IDOR), and schema-validates input — not relying on middleware?
- [ ] No secrets or whole DB rows crossing server→client; data layer marked `server-only`; DTOs minimal?
- [ ] Authorization enforced at the data layer, not only in `proxy.ts`/middleware or a layout?
- [ ] Caching understood per route; no personalized page cached at a shared cache; `use cache` keyed per-user where needed, on verified ids + a permission version, never a raw cookie/token?
- [ ] `next/image` `remotePatterns` limited to explicit trusted hosts (no `**`)?
- [ ] `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` set for multi-replica deploys; `allowedOrigins` limited to the exact public/front-door hosts, no wildcard over a suffix others can host on?
- [ ] Draft Mode enable handler: constant-time secret check, unknown ids refused, redirect built from the CMS record?
- [ ] Every `revalidateTag`/`revalidatePath`/`updateTag` caller authenticated and authorized, targets from an allowlist, external triggers signature-verified and rate-limited?
- [ ] No Route Handler that exists only for your own Server Components?
