# 05 — Nuxt 4: data fetching, state, server routes, CVEs

Written for Nuxt 4 on Nitro 2 / h3 1; verify the latest at nuxt.com/blog. Vue fundamentals are in `rules/04`;
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
  richer state management, **Pinia** (v3+; v4 is ESM-only) is the recommended store and is
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
  rule — the class behind CVE-2026-53721 and its incomplete-fix follow-up CVE-2026-71315 below.
- **Server components / islands are experimental** in Nuxt 4 (enable component
  islands; `.server.vue` rendered via `<NuxtIsland>`): single root element, props
  travel as URL query params (keep them small), no route middleware inside an island.
  Given the island advisories below, treat as experimental and don't put authz
  decisions inside island rendering.

## 6. Nuxt / Nitro / h3 / IPX / devalue CVE reference (verify at use time)

| CVE / advisory | Class | Fixed in |
|---|---|---|
| **CVE-2025-27415** (GHSA-jvhm-gjrh-3h93) | Nuxt CDN **cache poisoning DoS** via a `?…_payload.json`-style query rendering the route as JSON, High 7.5 | Nuxt **3.16.0** |
| **CVE-2026-53721** (GHSA-mm7m-92g8-7m47) | `routeRules` **middleware bypass** via case-sensitivity mismatch, High | Nuxt 4.4.7 / 3.21.7 — **incomplete**, see next row |
| **CVE-2026-71315** (GHSA-hxvh-4h3w-prp9) | Incomplete fix for CVE-2026-53721: route rules dropped for mixed-case paths, bypassing `appMiddleware` auth gates, High | Nuxt **4.5.1** (3.21.10, but 3.x is EOL) |
| **2026-08-05 batch**: **CVE-2026-71320** (GHSA-9473-5f9j-94wq), CVE-2026-71314, CVE-2026-71321, CVE-2026-71318 | **Server-island props RCE** (runtime template injection); unauthenticated island OOM / CPU-exhaustion DoS; unauthorized component instantiation — High except -71318 | Nuxt **4.5.1** (3.21.10) |
| **CVE-2026-71316** (GHSA-wm8w-6qjm-cv43) | Runtime **payload cache serves another user's SSR data** across users and to unauthenticated clients, High; affects 4.4.0–4.5.0 only | Nuxt **4.5.1** |
| CVE-2026-53722 (GHSA-934w-87qh-qr26) | Reflected **XSS in `<NuxtLink>`** via `javascript:`/`data:` URLs | Nuxt 4.4.7 / 3.21.7 |
| CVE-2026-47200 (GHSA-hg3f-28rg-4jxj) | Route middleware **not enforced** rendering `.server.vue` via `/__nuxt_island/…` | Nuxt 4.4.6 / 3.21.6 |
| CVE-2026-45669 (GHSA-fx6j-w5w5-h468), CVE-2026-56326 (GHSA-c9cv-mq2m-ppp3) | `navigateTo()` reflected XSS / open redirect, Medium | Nuxt 4.4.6 / 4.4.7 (below the 4.5.1 floor) |
| CVE-2025-54387 (GHSA-mm3p-j368-7jcr) | **IPX path traversal** (prefix-match bypass) — the `@nuxt/image` optimizer | IPX **1.3.2 / 2.1.1 / 3.1.1** |
| CVE-2026-33128 (GHSA-22cc-p3c6-wpvm) + follow-ups | **h3 SSE injection** via unsanitized newlines (High); serveStatic path traversal; middleware bypass | h3 1.15.6 / 2.0.1-rc.15 |
| GHSA-4hxc-9384-m385, GHSA-72gr-qfp7-vwhw (v1); GHSA-fp4x-ggrf-wmc6, GHSA-q5pr-72pq-83v3, CVE-2026-33490 (v2) | SSE `\r` injection (bypass of the CVE-2026-33128 fix); `serveStatic` double-decode traversal; v2 `redirectBack()` open redirect, session-cookie DoS, `mount()` prefix bypass | h3 **1.15.9 / 2.0.1-rc.18** (TE.TE smuggling CVE-2026-23527, fixed 1.15.5, sits below this floor) |
| CVE-2026-44373 (GHSA-5w89-w975-hf9q), CVE-2026-44372 (GHSA-9phm-9p8f-hw5m) | Nitro `routeRules` **proxy scope bypass** via percent-encoded traversal; open redirect via protocol-relative URL in wildcard route rules | nitropack **2.13.4** |
| CVE-2025-57820 (GHSA-vj54-72f3-p5jv) | **devalue prototype pollution** on `parse` (the Nuxt payload deserializer), High | devalue **5.3.2** |
| CVE-2026-30226 (GHSA-cfw5-2vxh-hr84) + DoS advisories | devalue prototype pollution / parse DoS | devalue 5.6.4 |
| CVE-2026-42570 (GHSA-77vg-94rm-hx3p), CVE-2026-81176 (GHSA-9rgm-9g3h-6x36) | devalue sparse-array DoS (High); DoS via malformed input | devalue **5.9.2** |

Floors as of 2026-09-26 ("fixed in", not "current"): **Nuxt ≥ 4.5.1**, **h3 ≥ 1.15.9**, **nitropack ≥ 2.13.4**, **devalue ≥ 5.9.2**. Newer advisories: the [nuxt](https://github.com/nuxt/nuxt/security/advisories), [h3](https://github.com/h3js/h3/security/advisories) and [nitro](https://github.com/nitrojs/nitro/security/advisories) feeds.

- **`nuxt-security` module** is the maintained hardening layer: OWASP-pattern security
  headers, CSP (with nonce support for SSR — verify the CSP docs for your mode), rate
  limiting, request-size limits, CORS, allowed-methods, XSS input validation, CSRF.
  Strongly consider it for any Nuxt app exposed to the internet.

## Audit checklist

- [ ] **Exact versions vs the CVE table** —
      `node -e "const p=require('./package.json');console.log(p.dependencies?.nuxt||p.devDependencies?.nuxt)"`
      ; `grep -E '"(nuxt|nitropack|h3|ipx|@nuxt/image|devalue|pinia)"' package.json`
- [ ] **Secret under public runtimeConfig (CRITICAL)** —
      `find . -maxdepth 2 -path ./node_modules -prune -o -name 'nuxt.config.*' -type f -exec grep -HnA8 'runtimeConfig' {} + | grep -iE 'public' -A6 | grep -iE 'secret|key|token|password'`
- [ ] **Module-level refs / state outside setup (cross-request leak)** —
      `grep -rnE '^(export )?const \w+\s*=\s*(ref|reactive)\(' --include='*.ts' composables server utils 2>/dev/null`
- [ ] **$fetch in setup (double fetch), server routes without validation** —
      `grep -rn '\$fetch(' --include='*.vue' pages components | grep -v useFetch` ;
      `grep -rLn 'getValidated\|readValidatedBody\|requireUserSession\|\.parse(' server/api server/routes 2>/dev/null`
- [ ] **routeRules that cache — must not be personalized** —
      `find . -maxdepth 2 -path ./node_modules -prune -o -name 'nuxt.config.*' -type f -exec grep -HnE 'swr|isr|prerender|ssr:[[:space:]]*false' {} +`
- [ ] **NuxtLink / URL sinks** —
      `grep -rn ':to=\|:href=' --include='*.vue' pages components | grep -iv 'sanitiz'`

- [ ] Nuxt/Nitro/h3/IPX/devalue versions patched against the table (Nuxt ≥ 4.5.1 for CVE-2026-71315/-71320/-71316; h3 ≥ 1.15.9; nitropack ≥ 2.13.4; devalue ≥ 5.9.2) and not on EOL Nuxt 3?
- [ ] No secret under `runtimeConfig.public`; server secrets at the root only?
- [ ] No module-level `ref`/`reactive` state outside `setup` (cross-request leak); `useState`/Pinia used instead?
- [ ] Every `server/api` handler authenticates, authorizes (ownership), and schema-validates input; responses filtered?
- [ ] `useFetch`/`useAsyncData` (not bare `$fetch`) for SSR data; payload shrunk via `pick`/`transform`?
- [ ] No `swr`/`isr`/`prerender` route serving personalized content; `routeRules` matchers actually match?
- [ ] `nuxt-security` (or equivalent headers/CSP/rate-limit) in place for internet-facing apps?
