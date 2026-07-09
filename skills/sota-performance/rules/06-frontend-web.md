# 06 — Frontend & Web Performance

Frontend performance is measured at the user's device — a $150 Android phone
on 4G, not your M-series laptop on fiber. Budget against **field data at p75**
(CrUX / your RUM), use lab tools (Lighthouse, WebPageTest) for diagnosis and
CI gating.

## 1. Core Web Vitals — current thresholds (p75, field)

| Metric | Good | Needs improvement | Poor | Measures |
|---|---|---|---|---|
| **LCP** (Largest Contentful Paint) | ≤ 2.5 s | 2.5–4.0 s | > 4.0 s | Loading: when the main content renders |
| **INP** (Interaction to Next Paint) | ≤ 200 ms | 200–500 ms | > 500 ms | Responsiveness: worst-case interaction latency (replaced FID in 2024) |
| **CLS** (Cumulative Layout Shift) | ≤ 0.1 | 0.1–0.25 | > 0.25 | Visual stability |

Supporting diagnostics: TTFB ≤ 800 ms (LCP can't be good on a 2 s TTFB),
FCP ≤ 1.8 s, Total Blocking Time (lab proxy for INP).

**LCP decomposition** — fix the dominant phase, not all of them:
TTFB → resource load delay → resource load time → render delay.
- LCP image must be discoverable in initial HTML (no CSS `background-image`
  for hero, no JS-inserted `<img>`, never `loading="lazy"` on the LCP image).
  Use `<img fetchpriority="high">` + `<link rel="preload">` if late-discovered.
- Lazy-load everything below the fold (`loading="lazy"`), never above it.

**INP** is caused by long main-thread tasks (> 50 ms):
- Break up long JS: `scheduler.yield()` / `await` chunking; show feedback
  within 100 ms even if work continues.

```javascript
// BAD — 5,000 items processed in one task: ~800 ms frozen main thread,
// every click during it counts against INP
items.forEach(render);

// GOOD — yield between chunks; first paint of feedback within one frame
for (const chunk of chunks(items, 200)) {
  chunk.forEach(render);
  await scheduler.yield();          // or: await new Promise(r => setTimeout(r))
}
```

- Avoid synchronous layout thrash (read layout → write style → read again in
  a loop forces reflow per iteration — batch reads, then writes).

```javascript
// BAD — read/write interleaved: forced synchronous reflow per element
for (const el of els) el.style.height = el.offsetHeight * 2 + "px";

// GOOD — phase 1 read all, phase 2 write all: one reflow total
const heights = els.map(el => el.offsetHeight);
els.forEach((el, i) => { el.style.height = heights[i] * 2 + "px"; });
```
- Heavy work off the main thread: Web Workers for parsing/crypto/diffing.
- Hydration and rerender storms are the top INP killers in SPAs (§6).
- Debounce input handlers; use CSS (`content-visibility`, transforms,
  animations on compositor) over JS where possible.

**CLS**: reserve space — explicit `width`/`height` (or `aspect-ratio`) on
images/embeds/ads; `font-display` strategy + size-matched fallback fonts (§5);
never insert banners above existing content; animate with `transform`, not
top/left/height.

## 2. Bundle size budgets

JS is the most expensive byte: 200 KB of JS costs download + parse + compile +
execute (~3–5× the cost of 200 KB of image on a mid-range phone's CPU).

Budgets (compressed, over-the-wire) — adjust to audience, enforce in CI:
- Initial critical-path JS: **≤ 150–200 KB** (≈ 450–600 KB uncompressed).
  An app shipping 1 MB+ initial JS will not hit INP/LCP targets on median
  mobile hardware.
- Initial CSS: ≤ 50 KB; inline critical CSS if render-blocking matters.
- Per-route async chunks: ≤ 100 KB each.
- Track *first-load JS per route* (Next.js build output does this natively).

Enforcement: `size-limit`, `bundlesize`, Lighthouse CI `budgets.json`, webpack
`performance.maxAssetSize` — fail the PR, don't dashboard it. Diagnose with
`webpack-bundle-analyzer` / `source-map-explorer` / `vite-bundle-visualizer`.

Top offenders to grep for: moment (→ date-fns/dayjs/Temporal), lodash
full-import (→ `lodash-es` named imports), big charting/editor libs loaded
eagerly, polyfills for evergreen browsers, duplicate dependency versions
(`npm dedupe`, lockfile audit), source-map/dev artifacts shipped to prod,
importing a server SDK into client code.

## 3. Code splitting

- **Route-based splitting is the floor**: every router-level view is its own
  chunk (framework defaults: Next/Nuxt/SvelteKit do this; verify it isn't
  defeated by a barrel file importing everything into a shared layout).
- **Interaction-based splitting**: heavy components behind user intent —
  modals, editors, charts, maps — `import()` on open/hover/viewport
  (`React.lazy`, `defineAsyncComponent`).

```tsx
// BAD — 280 KB editor in the initial bundle of every page that *might* edit
import { RichTextEditor } from "@acme/editor";

// GOOD — loads only when the user opens the editor; prefetch on hover
const RichTextEditor = lazy(() => import("@acme/editor"));
<Suspense fallback={<EditorSkeleton />}>{editing && <RichTextEditor />}</Suspense>
```
- Preload likely-next chunks on idle/hover (`rel="prefetch"`, router
  prefetching) so splitting doesn't add interaction latency.
- Don't over-split: hundreds of tiny chunks add request overhead and waterfall
  depth even on h2/h3; group by route/feature (~30–100 KB chunks).
- Barrel files (`index.ts` re-exporting a directory) defeat tree-shaking in
  many setups — import from concrete modules or configure
  `optimizePackageImports`/`sideEffects: false`.

## 4. Images

Usually the largest bytes on the page and the most common LCP element.

- **Formats**: AVIF first (≈ 30–50% smaller than JPEG at equivalent quality),
  WebP fallback (≈ 25–35% smaller than JPEG), JPEG/PNG last resort. SVG for
  icons/illustrations. Use `<picture>` + `type` negotiation or an image CDN
  that negotiates via `Accept`.
- **Responsive sizing**: `srcset` + `sizes` so a phone doesn't download the
  2400 px desktop hero. Serving a 2000 px image into a 400 px slot is a
  ~10–20× byte waste — the most common image finding.
- Compress: quality 60–75 covers most photographic content; use an image
  CDN/pipeline (resize, format, quality per request) instead of committed
  pre-baked assets.
- LCP image: `fetchpriority="high"`, preload, no lazy (§1). Everything below
  fold: `loading="lazy" decoding="async"`.
- Always `width`/`height`/`aspect-ratio` (CLS). Poster images for videos;
  `preload="none"` on below-fold video.

## 5. Fonts

Web fonts block or shift text rendering.

- **WOFF2 only** (≈ 30% smaller than WOFF; universal support).
- **Subset** to used scripts/characters (`pyftsubset`, `glyphhanger`):
  a full font with CJK + symbols can be 1 MB+; a Latin subset ~15–30 KB.
- **Self-host** with `Cache-Control: immutable`; third-party font CSS adds a
  connection + CSS round trip on the critical path (and cache partitioning
  killed the shared-cache benefit years ago).
- `<link rel="preload" as="font" type="font/woff2" crossorigin>` for the 1–2
  critical fonts only.
- `font-display: swap` (text visible immediately) or `optional` (no swap
  flash; best CLS). Tame swap-induced CLS with metric-compatible fallbacks:
  `size-adjust`/`ascent-override` on a fallback `@font-face` (tooling:
  fontaine, Next.js `next/font` does all of this automatically).
- Limit families/weights: every weight is a file; use variable fonts when you
  need > 2–3 weights.

## 6. Hydration cost

SSR HTML that then hydrates pays twice: server render + client re-execution
of the entire component tree (download → parse → execute → attach). On
mid-range mobile, hydrating a large tree costs 1–3 s of main-thread time —
the page *looks* ready but ignores taps (INP/TBT killer, "uncanny valley").

Mitigations, in order of leverage:
1. **Ship less component code**: server-only rendering for static parts —
   React Server Components / Astro-style zero-JS-by-default mean
   non-interactive components ship **no** client JS at all.
2. **Islands / partial hydration**: hydrate only interactive widgets (Astro,
   Fresh, eleventy-is-land); the static 90% of a content page stays HTML.
3. **Lazy/deferred hydration**: hydrate on visibility/interaction
   (`client:visible`, `astro:idle` equivalents; React `lazy` + Suspense
   boundaries) — below-fold widgets shouldn't hydrate during load.
4. **Streaming SSR + selective hydration** (React 18+): flush HTML early
   (TTFB/LCP win), hydrate islands as their code arrives, prioritize the one
   the user touches.
5. Resumability (Qwik) skips replay-style hydration entirely — niche but the
   conceptual benchmark.

Audit signals: framework runtime + app code re-executing everything on load;
`hydration mismatch` warnings (double render); interactive-but-dead period in
traces (long tasks right after LCP); TBT ≫ 300 ms in lab.

## 7. Edge rendering & delivery

- **Static-first**: anything renderable at build time (marketing, docs, blogs)
  ships as CDN-cached static HTML — TTFB ~20–50 ms globally, origin can be
  down. ISR/SWR regeneration keeps content fresh without rebuild-the-world.
- **Edge SSR** for personalized-but-light pages: render at the POP (~10–30 ms
  from user) vs origin (~100–300 ms cross-region). Constraints: limited
  runtime APIs, and **data locality** — an edge function calling a
  single-region DB pays the cross-region RTT anyway (worse than origin
  rendering). Edge SSR only wins when data is also at the edge (edge KV,
  regional replicas) or the page needs ≤ 1 origin fetch.
- Hybrid default: static shell from CDN + cached API + client/edge
  personalization; or streaming SSR from origin with early-flushed `<head>`.
- TTFB budget ≤ 800 ms is mostly an architecture decision: cache HTML where
  possible, stream when not, terminate TLS at edge always (rules/04 §8).

## 8. Delivery hygiene (fast wins)

- `<script defer/type=module>` — no sync scripts in `<head>`; third-party tags
  async or via a tag manager loaded post-LCP, or `web worker`-ized (Partytown)
  when feasible. Third-party JS is the most common externally-caused INP/TBT
  regression — audit the tag list quarterly.
- Resource hints: `preconnect` to critical third-party origins (≤ 2–3);
  `preload` only what's provably late-discovered (preload spam steals
  bandwidth from the LCP resource).
- `103 Early Hints` for preconnect/preload while origin thinks.
- Compression and caching per rules/04 §6/§8: brotli/zstd, immutable hashed
  assets, h2/h3 end-to-end.
- Measure RUM (web-vitals JS library → your analytics) segmented by device
  class and country — averages across devices hide the phones where you fail.
- Know the SPA blind spot: classic CWV attributes everything after the initial
  load to that first page — soft (in-app) navigations aren't measured. Chrome's
  Soft Navigations API (launching unflagged from Chrome 151; the final API
  differs from earlier origin-trial shapes) extends LCP/CLS/INP to SPA route
  changes — adopt via the web-vitals library once it ships.

Calibrate against real conditions — what a byte budget means on the wire:

| Condition | Bandwidth | RTT | 200 KB JS arrives in |
|---|---|---|---|
| Fast 4G / median mobile | ~9 Mbps | ~60–170 ms | ~0.3–0.5 s + parse/exec ~0.5–1.5 s on mid-range CPU |
| Slow 4G / crowded network | ~1.6 Mbps | ~150 ms | ~1.2 s + parse/exec |
| 3G (emerging markets, roaming) | ~0.4–0.7 Mbps | ~300–400 ms | ~3–4 s before a line of your code runs |

Lab-test with throttling (Lighthouse's default is throttled mobile for a
reason); a page that's "instant" unthrottled and 6 s on slow 4G is a 6 s page
for a real cohort of users.

## Audit checklist

- [ ] Field CWV (CrUX/RUM) at p75 per key page: LCP ≤ 2.5 s, INP ≤ 200 ms,
      CLS ≤ 0.1? Which metric/phase dominates the failure?
- [ ] LCP element: discoverable in initial HTML? `fetchpriority="high"`?
      Not lazy-loaded? TTFB ≤ 800 ms on that route?
- [ ] Initial compressed JS per route ≤ ~200 KB? CI budget enforcement
      (size-limit/Lighthouse CI) present and failing builds?
- [ ] Bundle analyzer output: moment/full-lodash/duplicate versions/eagerly
      loaded heavy libs/barrel-file tree-shaking defeats?
- [ ] Route-level code splitting working (check chunk map)? Heavy widgets
      (editor/chart/map/modal) behind dynamic `import()`? Likely-next routes
      prefetched?
- [ ] Images: AVIF/WebP negotiated? `srcset`/`sizes` present? Dimensions set
      (CLS)? Below-fold lazy, above-fold not? Any image > ~200 KB on the wire?
- [ ] Fonts: WOFF2, subset, self-hosted, ≤ 2 preloaded, `font-display` +
      metric-compatible fallback (or next/font/fontaine)?
- [ ] Long tasks > 50 ms during load and on interaction (trace)? Layout
      thrash loops? Heavy work that belongs in a Worker?
- [ ] Hydration: does static content ship client JS (RSC/islands candidate)?
      Below-fold components hydrating eagerly? TBT after LCP?
- [ ] Third-party scripts: inventoried, async/deferred, measured for
      main-thread cost? Any sync `<head>` script?
- [ ] HTML caching strategy: static/ISR where possible? Edge SSR only where
      data is edge-local? Early-flushed streaming where origin-rendered?
- [ ] RUM in place, segmented by device/geo — or is the team flying on
      laptop Lighthouse runs only?
