# 01 — Baseline: versions, support windows, render modes

Fast-moving facts. Every version and EOL date below was primary-sourced 2026-07;
**re-verify at use time** before pinning — these stacks ship majors yearly and
security releases weekly.

## 1. Supported versions and EOL (verify before pinning)

| Runtime | Current stable (2026-07) | Floor for new code | EOL / support note |
|---|---|---|---|
| React | 19.2.x | 19.x | 18.x maintained but no new features; React Compiler needs 19 idioms |
| Next.js | 16.2.x | 15.x (16.x preferred) | **Active LTS 16.x**, **Maintenance LTS 15.x** (critical + security ~2y from 2024-10-21). Everything **< 15 is unsupported** — treat as a finding |
| Vue | 3.5.x | 3.5+ | Vue 2 **EOL 2023-12-31** (paid extended support only). 3.6 (Vapor mode) in beta — not stable |
| Nuxt | 4.4.x | 4.x | Nuxt 3 **security-patches-only until 2026-07-31** (then EOL); Nuxt 2 EOL 2024-06-30; Nuxt 5 (unreleased) brings Nitro v3 + h3 v2 |
| Nitro | 2.13.x | 2.x | v3 in beta; ships with Nuxt 5 |
| Pinia | 3.x | 3.x | Pinia 3 dropped Vue 2; default Nuxt/Vue store |

Sources: react.dev/versions, nextjs.org/support-policy, github.com/vuejs/core
releases, nuxt.com/docs/4.x/community/roadmap. Running an EOL major (Vue 2, Nuxt 2,
Next < 15) means no security patches — HIGH at minimum for an internet-facing app.

- **React Compiler 1.0 is stable** (2025-10-07): a build-time plugin that
  auto-memoizes, removing most manual `useMemo`/`useCallback`/`memo`. It requires
  Rules-of-Hooks-clean code (see `rules/02`). Opt-in for Next/Vite today; verify
  current adoption status for your toolchain. Prefer it over hand-memoization for
  new code, but it is not a substitute for fixing render-model mistakes.

## 2. Choosing a stack (framework selection)

Both stacks are mature and SSR-first; the choice is usually ecosystem/team, not
capability. Neutral guidance, not prescription:

- **React + Next.js** — largest ecosystem; React Server Components + Server Actions
  are the reference implementation of the RSC model; the deepest hosting integration
  (Vercel and others). Cost: the RSC/client mental model is genuinely hard, and the
  security surface is large and fast-moving (see the 2025-12 RSC RCE).
- **Vue + Nuxt** — gentler learning curve, batteries-included conventions (file-based
  routing, auto-imports, `runtimeConfig`), Nitro gives a portable server runtime.
  Smaller but healthy ecosystem.
- **Not every app needs a meta-framework.** A purely client-side app (internal
  dashboard behind auth, no SEO need) can be a plain Vite SPA — you shed the entire
  SSR/hydration/RSC attack surface. Reach for Next/Nuxt when you need SSR/SSG for SEO,
  fast first paint, or server-side data access. Don't adopt SSR for its own sake.

Record the decision as an ADR (`sota-docs-workflow`); it drives everything downstream.

## 3. Render modes — pick per route, not per app

The single most consequential design choice. Modern frameworks let you mix modes
per route, so match each route to its data:

| Mode | What it is | Use for | Watch out for |
|---|---|---|---|
| **CSR** (client only) | JS renders in the browser; empty initial HTML | Highly interactive, auth-gated, no-SEO views (`ssr: false` route in Nuxt) | Blank first paint; not indexable |
| **SSR** (per request) | HTML rendered on each request | Personalized/authenticated pages, fresh data | Server cost; **must not be cached at a shared CDN if personalized** (`rules/06`) |
| **SSG / prerender** | HTML rendered at build | Marketing, docs, anything static | Rebuild to update; no per-user content |
| **ISR / SWR** | Static + periodic/on-demand revalidation | Semi-static content (catalogs, blogs) | Stale windows; cache-invalidation correctness |
| **PPR** (Next, Cache Components) | Static shell + streamed dynamic holes via Suspense | Pages mixing static chrome + dynamic data | Uncached data outside `<Suspense>` is a build error; incompatible with CSP nonces |

- **Next.js**: route-segment config + `"use cache"`; PPR is the default when
  `cacheComponents: true`. Fetch is **not cached by default since v15** — opt in
  explicitly (`rules/03`).
- **Nuxt**: `routeRules` in `nuxt.config` sets per-route mode (`ssr: false`,
  `prerender: true`, `swr: <ttl>`, `isr: <ttl>`) — hybrid rendering (`rules/05`).
- **Security corollary:** the more a route is cached and shared, the more a caching
  bug leaks one user's data to another. Personalized ⇒ SSR + `private` cache. Static
  ⇒ safe to cache widely. Decide this consciously per route.

## 4. Project setup baseline

- **TypeScript strict** — non-negotiable; details in `sota-javascript-typescript`
  rules/01. Frameworks generate a `tsconfig`; extend, don't loosen it.
- **Lockfile committed**, exact framework versions pinned, Dependabot/Renovate on —
  framework CVEs are frequent and the fix is almost always "upgrade" (`rules/07`,
  `sota-devsecops`).
- **Lint the framework rules**: `eslint-plugin-react-hooks` (Rules of Hooks — also
  what the React Compiler needs) / `eslint-plugin-vue`; Next's and Nuxt's own ESLint
  configs. A hooks-rule violation is a real bug, not style.
- **Env discipline from day one**: server secrets in unprefixed env vars; only
  deliberately-public config in `NEXT_PUBLIC_*` / `runtimeConfig.public` / `VITE_*`
  (`rules/07`). Never commit `.env`.
- **CI gates**: typecheck, lint, tests, `npm audit`/`osv-scanner`, and a build. Add a
  bundle-size check if shipping to the browser (`sota-performance` rules/06).

## Audit checklist

```bash
# Framework majors in use — compare against the support table above
grep -E '"(react|react-dom|next|vue|nuxt|nitropack|pinia)"' package.json
cat package.json | grep -A2 '"dependencies"'   # then read lockfile for exact patch

# EOL / unsupported runtimes (findings)
node -e "const p=require('./package.json');const d={...p.dependencies,...p.devDependencies};for(const k of ['vue','nuxt','next'])if(d[k])console.log(k,d[k])"
# vue ^2 -> EOL; nuxt ^2 -> EOL; next <15 -> unsupported

# Render-mode inventory
grep -rn 'ssr:\s*false\|routeRules\|prerender\|export const dynamic\|cacheComponents' nuxt.config.* next.config.* app/ pages/ 2>/dev/null

# Hooks/vue lint present?
grep -rn 'react-hooks\|eslint-plugin-vue\|next/core-web-vitals\|@nuxt/eslint' .eslintrc* eslint.config.* package.json 2>/dev/null
```

- [ ] Every framework major is supported and receiving security patches (no Vue 2, Nuxt 2, Next < 15)?
- [ ] Exact versions pinned + lockfile committed + automated dependency updates on?
- [ ] Render mode chosen per route to match its data (personalized ⇒ SSR + private cache)?
- [ ] TypeScript strict; hooks/vue lint rules enforced in CI?
- [ ] Public-env boundary understood: no secrets in `NEXT_PUBLIC_`/`public`/`VITE_`?
- [ ] For a no-SEO auth-gated app: is a meta-framework actually needed, or would a plain SPA shed the SSR attack surface?
