# Performance: Bundles, React, Memory, Event Loop

Measure before optimizing: bundle analyzer for size, React Profiler/DevTools for renders, Chrome Performance + heap snapshots for memory, `monitorEventLoopDelay` for Node. Optimizations without a measurement are style choices.

## Bundle discipline

Every shipped KB is parse/compile/execute time on the median phone, not just transfer.

- **Budget and analyze in CI**: `rollup-plugin-visualizer` / `webpack-bundle-analyzer` / `vite-bundle-visualizer`; budget per route (e.g. ≤200KB gz initial JS) enforced with `size-limit` so regressions fail PRs.
- **Tree-shaking-friendly code**: ESM only; no module-level side effects (top-level mutations, auto-registration); `"sideEffects": false` in package.json (list CSS/polyfill exceptions). Barrel files (`index.ts` re-exporting everything) defeat dev-server perf and often shaking — import from the specific module, or use `optimizePackageImports`/eslint `no-barrel-files` policy.

```ts
// BAD — pulls whole lib if package isn't shakeable; barrels chain-load the world
import _ from 'lodash';
import { Button } from '@/components';          // barrel of 200 components

// GOOD
import debounce from 'lodash-es/debounce';      // or write the 10-liner yourself
import { Button } from '@/components/button';
```

- **Dynamic import for conditional weight**: routes, modals, charts, editors, anything below the fold or behind interaction.

```tsx
const ChartPanel = lazy(() => import('./ChartPanel'));   // + <Suspense fallback>
// Non-React: const { parse } = await import('heavy-parser');
```

- **Dependency weight check before adding**: bundlephobia/pkg-size; prefer date-fns over moment, valibot/zod-mini where bundle-critical. Duplicate-version check: `pnpm dedupe`, analyzer's duplicates view.
- Ship modern JS (`target: 'es2022'`-ish browserslist) — transpiling classes/async down for dead browsers costs 20-30% size.
- Fonts/images dwarf JS in LCP terms — but that's outside this file's scope; don't let JS micro-opts distract from a 2MB hero image.

## Startup: loading and hydration

- `<script type="module">` defers by default; never blocking scripts in `<head>` without `defer`/`async`. `modulepreload` the critical graph; `rel=preconnect` to API/CDN origins.
- Hydration cost scales with shipped component tree: RSC/islands architectures (Next App Router, Astro) exist to ship less of it — interactivity leaves only (`'use client'` discipline below).
- Lazy-hydrate below-the-fold islands (visible-trigger) where the framework supports it; don't lazy-load anything needed for first interaction (you trade LCP for INP).
- Third-party scripts are the usual LCP/INP killers: load analytics/chat after interactive (`next/script strategy="lazyOnload"` or equivalent), or move to a worker via Partytown when compatible.
- Prefetch on intent: route prefetch on link hover/viewport (framework default — verify it's not disabled), data prefetch for the predictable next step. Cheap wins that beat any memoization.

### Profiling toolbox

| Question | Tool |
|---|---|
| What's in the bundle? | vite-bundle-visualizer / webpack-bundle-analyzer, `size-limit` in CI |
| Why is this interaction slow? | Chrome Performance panel (look for long tasks), React Profiler |
| What re-rendered and why? | React DevTools Profiler, "record why" enabled |
| Where's the memory going? | DevTools Memory: snapshot diff, allocation timeline |
| Is the Node loop blocked? | `monitorEventLoopDelay`, `node --cpu-prof` / `0x` flamegraphs under load (clinic.js: README says not actively maintained) |
| Real-user numbers? | web-vitals → RUM (LCP, INP, CLS) — lab numbers lie about phones |

## React rendering

A render is a function call, not a DOM write — cheap-ish, but O(subtree) and they cascade. Hunt structural causes before memoizing.

Ordered playbook:
1. **State down**: state used by one subtree must live there, not in a page-level component re-rendering everything per keystroke.
2. **Children as props / composition**: a component taking `children` doesn't re-render them when its own state changes — lift expensive subtrees out of frequently-updating wrappers.

```tsx
// BAD — every tick re-renders <ExpensiveTree>
function Page() { const t = useTick(); return <div><Clock t={t} /><ExpensiveTree /></div>; }
// GOOD — move ticking state into Clock; ExpensiveTree untouched
function Page() { return <div><Clock /><ExpensiveTree /></div>; }
```

3. **Subscribe narrowly**: context splits (state vs dispatch), or selector-based stores (zustand/jotai) so components re-render on their slice only. A single fat context is the classic whole-app re-render.
4. **Then memoize, judiciously**: `React.memo` on expensive leaf/list components; `useMemo` for expensive computations; `useCallback` only to stabilize props of memoized children or effect deps. Memoizing everything adds comparison cost + complexity for nothing — and one unstable prop (inline object/array) silently voids `memo`. React Compiler 1.0 (stable since Oct 2025) auto-memoizes — when it's enabled, delete manual memo noise rather than adding more.
5. **Verify with the Profiler** (record → interact → check "why did this render") before and after.

Other React essentials:
- **Keys**: stable identity (`item.id`), never array index for reorderable/insertable lists (state and DOM get misattached), never `Math.random()` (full remount per render).
- **Transitions**: wrap non-urgent updates (`startTransition`, `useDeferredValue` for derived expensive renders) so typing stays responsive while results lag gracefully.
- **Server Components mental model** (Next.js App Router etc.): RSC run on the server only and ship zero JS — default everything server; add `'use client'` only at interactivity leaves. Don't pass non-serializable props across the boundary; push `'use client'` boundaries as deep as possible. Data-fetch in server components (no client waterfall, no useEffect-fetch).
- **Effects**: `useEffect` is for synchronizing with external systems, not for derived state (compute during render) or event logic (put in handler). Effect-chains (`setState` in effect triggering next effect) cause render cascades — derive instead. `useEffectEvent` (React 19.2+) reads latest props/state inside an effect without adding them to deps — use it instead of dep-list gymnastics or stale-closure refs.
- Avoid layout thrash: batch DOM reads then writes; in raw-DOM code interleaved `offsetHeight`/style writes force sync reflow per iteration.

### Re-render hunting workflow

1. React DevTools Profiler → enable "Record why each component rendered" → record the slow interaction.
2. Sort commits by duration; in the flamegraph find wide bars that shouldn't have rendered (props visually unchanged).
3. Common causes, in observed frequency order:
   - New object/array/function identity per render passed as prop: `<List style={{ margin: 8 }} onSelect={() => ...} />` — hoist constants, memoize handlers only when the child is memoized.
   - Context value rebuilt each render: `<Ctx.Provider value={{ user, setUser }}>` — memoize the value object, or split into two contexts.
   - Store subscription too broad: `const state = useStore()` instead of `useStore(s => s.cartCount)`.
   - Parent state that belongs in a child (form input state at page level).
4. Fix the structural cause; re-profile; only then add `memo` to remaining hot leaves.

```tsx
// BAD — context identity changes every render; every consumer re-renders
function App() {
  const [user, setUser] = useState<User | null>(null);
  return <UserCtx.Provider value={{ user, setUser }}>{children}</UserCtx.Provider>;
}
// GOOD — stable value; even better: separate state and dispatch contexts
const value = useMemo(() => ({ user, setUser }), [user]);
```

Measure interaction health with INP (Interaction to Next Paint): long tasks >50ms between input and paint are the budget violations. `PerformanceObserver` with `{ type: 'event', durationThreshold: 40 }` or web-vitals library in RUM; break up long handlers with `await scheduler.yield()` between logical phases.

## Long lists: virtualization

DOM nodes are the cost: 10k rows × 20 nodes kills layout/paint regardless of framework.

- > ~200-500 rendered items (or heavy rows) → virtualize: `@tanstack/virtual`, `react-window`. Renders only the viewport ± overscan.
- CSS `content-visibility: auto` + `contain-intrinsic-size` is a zero-JS alternative for long static pages.
- Paginate/infinite-scroll at the data layer too — don't ship 50k records to the client to virtualize their DOM.
- Virtualization breaks Ctrl-F and screen-reader sequence; for short lists just render them.

## Debounce and throttle

- **Debounce** (trailing): act after input settles — search-as-you-type (200-300ms), autosave, resize-end.
- **Throttle**: act at most every N ms during continuous events — scroll position, drag, mousemove.
- Prefer platform primitives when they fit: `IntersectionObserver` over scroll handlers, `ResizeObserver` over resize handlers — they're off-main-thread scheduled and don't need throttling.

```tsx
// React: keep the timer in a ref; cancel on unmount; or use TanStack Pacer/use-debounce
const debouncedSearch = useMemo(() => debounce((q: string) => run(q), 250), []);
useEffect(() => () => debouncedSearch.cancel(), [debouncedSearch]);
```

Recreating the debounced fn every render (inline `debounce(...)` in the component body without memo) resets the timer each keystroke — the #1 debounce bug. For data fetching, debounce + abort previous request (rules/03) together.

## Caching and memoization (non-React)

- Memoize pure-expensive functions with bounded caches; an unbounded memo on user-keyed input is a leak (below).

```ts
import { LRUCache } from 'lru-cache';
const cache = new LRUCache<string, Report>({ max: 500, ttl: 60_000 });
async function getReport(id: string): Promise<Report> {
  const hit = cache.get(id);
  if (hit) return hit;
  const r = await buildReport(id);
  cache.set(id, r);
  return r;
}
```

- Cache the promise, not just the value, to collapse concurrent misses (stampede pattern, rules/03).
- Invalidate explicitly on write paths or accept TTL staleness deliberately — "cache + forgot invalidation" bugs masquerade as data corruption.
- HTTP layer first: `Cache-Control`/`ETag` on API responses and CDN caching beat in-process caches for read-heavy public data.

## Memory leaks

Long-lived references are the leak; SPAs and Node servers never get the page-refresh absolution.

Usual suspects:
- **Listeners/observers on long-lived targets** (`window`, `document`, sockets, emitters) added per component/request and never removed → remove in cleanup, or `addEventListener(..., { signal })` + one `abort()` (rules/03). Disconnect `IntersectionObserver`/`MutationObserver`/`ResizeObserver`.
- **Timers**: `setInterval` without `clearInterval` keeps its closure (and everything it captures) alive forever.
- **Closures over large scopes**: a small callback capturing a huge parsed payload pins it; extract what you need into locals before creating the long-lived closure.
- **Module-level caches without bounds**: `const cache = new Map()` growing per-key forever in a server = slow OOM. Bound it (LRU — `lru-cache`), or key by object with `WeakMap` so entries die with their keys.
- **Detached DOM**: keeping element refs (in arrays, maps, closures) after removal from the document retains whole subtrees. Heap snapshot → search "Detached".
- **Node-specific**: per-request data stuffed into module/global scope; `EventEmitter` listeners accumulating (MaxListenersExceededWarning is a leak smell, not a limit to raise blindly); unbounded in-flight maps without `finally` cleanup.

```ts
// BAD — closure pins the whole 50MB parsed report for the life of the listener
const report = await parseHugeReport(file);
emitter.on('tick', () => updateBadge(report.summary.count));

// GOOD — capture only the scalar
const count = (await parseHugeReport(file)).summary.count;
emitter.on('tick', () => updateBadge(count));
```

Detection workflow (browser and Node `--inspect` alike):
1. Heap snapshot → perform the suspected-leaking action 3-5× → snapshot again.
2. Comparison view, sort by retained-size delta; look for arrays/maps/closures growing linearly with actions, and "Detached" DOM entries.
3. Follow the retainer chain upward to the root holding the reference — that's the fix site, not the leaked object's class.
4. Node services: export `process.memoryUsage().heapUsed`/RSS to metrics; alert on monotonic growth across hours; capture snapshots on signal (`v8.writeHeapSnapshot()` behind an admin endpoint) when it fires.

## Node event-loop blocking

One blocked loop = every request stalled (full treatment in rules/04). Performance-audit angle:
- Instrument: `perf_hooks.monitorEventLoopDelay()` histogram exported to metrics; alert p99 > 100ms.
- Identify: `node --cpu-prof` (open the `.cpuprofile` in DevTools) or `0x` flamegraphs under load, `--heap-prof` for allocation; continuous profiling via your OpenTelemetry/pprof-compatible backend in production. clinic.js's README says it is not actively maintained and may give inaccurate results, and `blocked-at` has had no commit since 2022: treat both as legacy.
- Fix order: cap input sizes → move CPU work to `piscina` workers → chunk unavoidable loops with `setImmediate` yields → cache the computation.
- `JSON.stringify` of huge objects in logging/serialization is a stealth blocker — log IDs and summaries, not payload dumps.

```ts
// Minimal loop-lag detector — cheap enough for production
import { monitorEventLoopDelay } from 'node:perf_hooks';
const h = monitorEventLoopDelay({ resolution: 20 });
h.enable();
setInterval(() => {
  metrics.gauge('event_loop_p99_ms', h.percentile(99) / 1e6);
  h.reset();
}, 10_000).unref();
```

## Offloading and scheduling on the main thread

- CPU work >50ms in the browser (parsing, diffing, search indexing, image manipulation): Web Worker (rules/03) — the main thread is for UI. Comlink removes the postMessage ceremony.
- Truly-idle work (analytics aggregation, prefetch warmup): `requestIdleCallback` (with a timeout fallback) — never for anything user-visible.
- Animation reads/writes: `requestAnimationFrame`; CSS transforms/opacity (compositor-only) over layout-triggering properties; `will-change` sparingly.
- Chunked processing keeps input responsive: process N items → `await scheduler.yield()` → continue; combine with `AbortSignal` so navigation cancels the rest.

## Micro-level idioms that matter at scale only

In hot paths (per-row in 100k iterations, per-frame): avoid spread-accumulator `reduce` (O(n²), rules/02), reuse compiled regexes, prefer `for...of` over chained array methods, avoid `try/catch`-free claims (modern engines made try cheap — don't contort code for it), and don't `delete obj.prop` in hot objects (deopts shapes; set to `undefined` or use Maps). Outside hot paths, write the readable version.

## Audit checklist

- [ ] Bundle analyzer wired and a size budget enforced in CI (`size-limit`/bundlesize)? Absent on a frontend app = MEDIUM.
- [ ] `grep -rn "from 'lodash'\|from \"lodash\"" src/` (non-`lodash-es`) and `from 'moment'` — heavy/cjs imports (MEDIUM). `grep -rn "import \* as" src/` — namespace imports of large libs.
- [ ] `grep -rln "export \* from" src/` — barrel files on hot paths (LOW/MEDIUM).
- [ ] `grep -rn "key={index}\|key={i}\|key={idx}" src/ --include="*.tsx"` — index keys on mutable lists (MEDIUM); `key={Math.random()` (HIGH — remount storm).
- [ ] `grep -rn "useEffect" src/ --include="*.tsx" | wc -l` high relative to components → review for derived-state effects and fetch waterfalls (MEDIUM).
- [ ] `grep -rn "useMemo\|useCallback\|React.memo" src/` — blanket memoization with unstable deps (inline objects in props of memoized components) = dead weight (LOW); missing memo on expensive list rows that profile hot (MEDIUM).
- [ ] `grep -rn "'use client'" app/ src/` — at layout/page top level wholesale = RSC benefits discarded (MEDIUM in App Router projects).
- [ ] Long lists: components mapping >hundreds of rows without virtualization (`grep -rn "\.map(" src/ --include="*.tsx"` + check data sizes) — MEDIUM.
- [ ] `grep -rn "addEventListener" src/` without matching remove/`{ signal }`; `grep -rn "setInterval" src/` without `clearInterval` — leaks (MEDIUM).
- [ ] `grep -rn "new Map()\|new Map<" src/` at module scope in server code — unbounded cache check (MEDIUM if grows per-request/per-user key).
- [ ] `grep -rn "onScroll\|onMouseMove\|onResize\|addEventListener('scroll'" src/` — unthrottled continuous handlers doing layout reads (MEDIUM); could be Intersection/ResizeObserver.
- [ ] Node: event-loop delay metric exported? `grep -rn "monitorEventLoopDelay" src/` — absent in a latency-sensitive service (LOW/MEDIUM).
- [ ] `grep -rn "JSON.stringify" src/` in logging/hot request paths over large objects (MEDIUM).
