# 05 — Nuxt 4: data fetching, state, server routes, CVEs

Baseline: Nuxt 4.4.x on Nitro 2.x / h3 1.x. Vue fundamentals are in `rules/04`;
hydration and SSR state in `rules/06`; the cross-framework security boundary in
`rules/07`. **Re-verify CVE ranges at use time.**

## 1. Data fetching — pick the right primitive

Getting this wrong causes double-fetches, hydration mismatches, and waterfalls.

- **`$fetch` alone in `setup` fetches twice** — once on the server, once again during
  client hydration — because its result isn't transferred in the payload. Use it only
  for **client-only / event-driven** calls (a button handler, a `POST`).
- **`useFetch`** is the SSR-safe wrapper: fetches once on the server and transfers the
  result to the client via the payload. The default in components. Keys default to a
  hash of the URL/options; calls sharing a key share the `data`/`error`/`status` refs.
- **`useAsyncData`** wraps arbitrary async logic (a CMS SDK, multiple calls, custom
  transform) with the same once-and-transfer semantics; give it an explicit key.
- `lazy: true` (or `useLazyFetch`) doesn't block navigation; `server: false` makes it
  client-only. Use `pick`/`transform` to **shrink the payload** — whatever these
  return is serialized into the HTML (`rules/06`, `rules/07`).

## 2. SSR-safe shared state — never a module-level ref

- **`useState(key, init)`** is the SSR-friendly `ref`: its value is serialized into
  the payload and restored on the client, and it's shared by key across components.
- **A module-level `const state = ref()` (outside `setup`) is a cross-request leak**
  on the server — the Nitro process reuses it across all users' requests (one user's
  data served to another) and it grows unbounded (memory leak). Nuxt's docs call this
  out explicitly. This is the single most important Nuxt SSR footgun (`rules/06`).
- `useState` values must be **serializable** (no classes/functions/symbols). For
  richer state management, **Pinia** (v3) is the recommended store and is
  SSR-safe by design (a fresh store per request).

## 3. `runtimeConfig` — the server/client secret boundary

```ts
export default defineNuxtConfig({
  runtimeConfig: {
    apiSecret: '',                 // SERVER-ONLY — never sent to the client
    public: { apiBase: '/api' },   // PUBLIC — serialized into the payload, visible to all
  },
})
```

- **Only `runtimeConfig.public.*` reaches the client** (it's in the payload).
  Everything at the root is server-only. **A secret under `public` is a client-side
  secret leak (CRITICAL)** — same failure class as `NEXT_PUBLIC_`/`VITE_` (`rules/07`).
- **Runtime override via env:** a `NUXT_`-prefixed env var overrides the matching key
  (`NUXT_API_SECRET`, `NUXT_PUBLIC_API_BASE`) — but the key must already exist in
  `nuxt.config` to be overridable. `.env` is read at dev/build time but **not** by the
  built production server; provide real env vars in production.

## 4. Nitro server routes — public API endpoints

Files under `server/api/` and `server/routes/` are Nitro handlers — **public HTTP
endpoints**, same trust model as any API (`sota-api-design`, `sota-code-security`).

```ts
// server/api/posts/[id].delete.ts
export default defineEventHandler(async (event) => {
  const { user } = await requireUserSession(event)          // 1. authenticate
  const { id } = await getValidatedRouterParams(event, z.object({ id: z.string().uuid() }).parse) // 3. validate
  const post = await db.post.find(id)
  if (post.authorId !== user.id) throw createError({ statusCode: 403 }) // 2. authorize
  await db.post.delete(id)
})
```

- **Validate every input** with `getValidatedQuery` / `readValidatedBody` /
  `getValidatedRouterParams` + a schema (Zod). Unvalidated query/body/params are the
  usual injection and IDOR entry points. Use `createError({ statusCode })` for typed
  responses; an uncaught throw is a 500.
- **Authenticate + authorize in the handler.** `nuxt-auth-utils` (sealed, encrypted
  session cookies; `requireUserSession`/`setUserSession`; scrypt hashing; OAuth +
  passkeys) is a solid, maintained baseline — it needs a real server (`nuxt build`,
  not `nuxt generate`). Check ownership on every resource to prevent IDOR.
- **Server-route responses are `JSON.stringify`'d** (unlike the devalue-serialized
  page payload) — return primitives/plain objects and filter them (no raw rows).

## 5. Hybrid rendering (`routeRules`) and islands

- **`routeRules`** in `nuxt.config` set the render mode per route pattern:
  `ssr: false` (client-only), `prerender: true` (SSG), `swr: <ttl>` (server/proxy
  cache + stale-while-revalidate), `isr: <ttl>` (like swr but pushed to CDN on
  supporting platforms; `isr: true` persists until next deploy). Also `redirect`,
  `headers`, `cors`, `noScripts`. **Security:** an `swr`/`isr`/cached route must not
  serve personalized content — the cache is shared (`rules/06`). A `routeRules`
  matcher that doesn't match the actual (case-sensitive) route can bypass an intended
  rule — the class behind CVE-2026-53721 below.
- **Server components / islands are experimental** in Nuxt 4 (enable component
  islands; `.server.vue` rendered via `<NuxtIsland>`): single root element, props
  travel as URL query params (keep them small), no route middleware inside an island.
  Given the island advisories below, treat as experimental and don't put authz
  decisions inside island rendering.

## 6. Nuxt / Nitro / h3 / IPX / devalue CVE reference (verify at use time)

| CVE / advisory | Class | Fixed in |
|---|---|---|
| **CVE-2025-27415** (GHSA-jvhm-gjrh-3h93) | Nuxt CDN **cache poisoning DoS** via a `?…_payload.json`-style query rendering the route as JSON, High 7.5 | Nuxt **3.16.0** |
| **CVE-2026-53721** (GHSA-mm7m-92g8-7m47) | `routeRules` **middleware bypass** via case-sensitivity mismatch, High | Nuxt **4.4.7 / 3.21.7** |
| CVE-2026-53722 (GHSA-934w-87qh-qr26) | Reflected **XSS in `<NuxtLink>`** via `javascript:`/`data:` URLs | Nuxt 4.4.7 / 3.21.7 |
| GHSA-hg3f-28rg-4jxj | Route middleware **not enforced** rendering `.server.vue` via `/__nuxt_island/…` | see advisory (2026-05) |
| CVE-2025-54387 (GHSA-mm3p-j368-7jcr) | **IPX path traversal** (prefix-match bypass) — the `@nuxt/image` optimizer | IPX **1.3.2 / 2.1.1 / 3.1.1** |
| CVE-2026-33128 (GHSA-22cc-p3c6-wpvm) + follow-ups | **h3 SSE injection** via unsanitized newlines (High); serveStatic path traversal; middleware bypass | h3 **1.15.6 / 2.0.1-rc.15** |
| CVE-2025-57820 (GHSA-vj54-72f3-p5jv) | **devalue prototype pollution** on `parse` (the Nuxt payload deserializer), High | devalue **5.3.2** |
| CVE-2026-30226 (GHSA-cfw5-2vxh-hr84) + DoS advisories | devalue prototype pollution / parse DoS | devalue **5.6.4** (+ later) |

- **`nuxt-security` module** is the maintained hardening layer: OWASP-pattern security
  headers, CSP (with nonce support for SSR — verify the CSP docs for your mode), rate
  limiting, request-size limits, CORS, allowed-methods, XSS input validation, CSRF.
  Strongly consider it for any Nuxt app exposed to the internet.

## Audit checklist

```bash
# Exact versions vs the CVE table
node -e "const p=require('./package.json');console.log(p.dependencies?.nuxt||p.devDependencies?.nuxt)"
grep -E '"(nuxt|nitropack|h3|ipx|@nuxt/image|devalue|pinia)"' package.json

# Secret under public runtimeConfig (CRITICAL)
grep -rnA8 'runtimeConfig' nuxt.config.* | grep -iE 'public' -A6 | grep -iE 'secret|key|token|password'

# Module-level refs / state outside setup (cross-request leak)
grep -rnE '^(export )?const \w+\s*=\s*(ref|reactive)\(' --include='*.ts' composables server utils 2>/dev/null

# $fetch in setup (double fetch), server routes without validation
grep -rn '\$fetch(' --include='*.vue' pages components | grep -v useFetch
grep -rLn 'getValidated\|readValidatedBody\|requireUserSession\|\.parse(' server/api server/routes 2>/dev/null

# routeRules that cache — must not be personalized
grep -rnE 'swr|isr|prerender|ssr:\s*false' nuxt.config.*

# NuxtLink / URL sinks
grep -rn ':to=\|:href=' --include='*.vue' pages components | grep -iv 'sanitiz'
```

- [ ] Nuxt/Nitro/h3/IPX/devalue versions patched against the table (esp. CVE-2025-27415, CVE-2026-53721, devalue pollution)?
- [ ] No secret under `runtimeConfig.public`; server secrets at the root only?
- [ ] No module-level `ref`/`reactive` state outside `setup` (cross-request leak); `useState`/Pinia used instead?
- [ ] Every `server/api` handler authenticates, authorizes (ownership), and schema-validates input; responses filtered?
- [ ] `useFetch`/`useAsyncData` (not bare `$fetch`) for SSR data; payload shrunk via `pick`/`transform`?
- [ ] No `swr`/`isr`/`prerender` route serving personalized content; `routeRules` matchers actually match?
- [ ] `nuxt-security` (or equivalent headers/CSP/rate-limit) in place for internet-facing apps?
