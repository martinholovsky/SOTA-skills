# 05 — Performance & Quality

Mobile performance is policed by the OS and the stores, not just by users: ANRs and crashes above Android vitals "bad behavior" thresholds reduce Play Store visibility; the iOS watchdog kills apps that block at launch; janky lists drive uninstalls measurable in retention curves. Budgets live in CI and production telemetry — a performance "initiative" after launch is an admission the budgets didn't exist.

## Budgets

Set these in the repo (`docs/perf-budgets.md` or CI config). Adjust the numbers per product; never delete the rows.

| Metric | Budget | Enforcement |
|---|---|---|
| Cold start → first meaningful content | ≤ 2.0 s on a mid-tier device (target 1.5 s) | Macrobenchmark / XCTest launch metrics in CI; Android vitals flags cold start ≥ 5 s |
| Warm / hot start | ≤ 1.0 s / ≤ 0.5 s | same |
| Frame budget | 16.6 ms @ 60 Hz; 8.3 ms @ 120 Hz — budget for the worst supported device, not your ProMotion dev phone | JankStats / MetricKit hang rate |
| Slow / frozen frames | < 5% / < 0.1% (vitals: > 16 ms / > 700 ms) | Android vitals, APM |
| ANR rate | < 0.47% of daily active users (Play user-perceived bad-behavior threshold, 8% per device model; main thread blocked > 5 s) | Play vitals, release gate |
| Crash-free sessions | ≥ 99.9% (vitals user-perceived crash threshold: 1.09%) | Crash SDK, rollout gate (rules/06) |
| Download size | Tracked per release with a delta gate (e.g., +2 MB needs sign-off). Play: compressed download limits of 500 MB for the base module and for each feature module, 4 GB cumulative for all modules and install-time asset packs; above 200 MB, cellular users see a non-blocking size dialog; iOS: large apps prompt on cellular | CI size report |
| Memory | Flat across a 10-min core-loop soak; survives `onTrimMemory`/`didReceiveMemoryWarning` without data loss | soak test, LeakCanary |

## Rules

### 5.1 Main-thread discipline is rule zero

The main thread renders frames and dispatches input — nothing else. JSON parsing, DB queries, image decoding, crypto, disk I/O, and lock waits move off it. Every other rule in this file is downstream of this one.

```swift
// BAD: decode on main → dropped frames on every message batch
let msgs = try JSONDecoder().decode([Message].self, from: data)
self.messages = msgs

// GOOD: decode off-main, hop back for the state write
let msgs = try await Task.detached(priority: .userInitiated) {
    try JSONDecoder().decode([Message].self, from: data)
}.value
await MainActor.run { self.messages = msgs }
```

```kotlin
// BAD: hidden main-thread disk I/O — synchronous commit
prefs.edit().putString("draft", text).commit()   // commit() blocks; apply() doesn't

// GOOD: Room/DataStore are main-safe by construction; suspend functions on IO dispatcher
suspend fun saveDraft(text: String) = withContext(io) { dao.saveDraft(text) }
```

- Tooling, debug builds: Android `StrictMode` (`detectDiskReads/detectNetwork().penaltyDeath()` in CI-instrumented runs; never active in release, rules/04 §4.9), iOS Main Thread Checker + `os_signpost` spans. New StrictMode violations fail CI — that's the cheapest perf regression gate that exists.
- Hidden main-thread work to hunt in audits: synchronous `SharedPreferences.commit()`, eager DI graph construction at startup, `DateFormatter`/`NumberFormatter` *creation* in list rows (creation is expensive; cache them), oversized `Codable` decodes in `@MainActor` contexts, synchronous `UIImage(named:)` of huge assets, blocking `.get()`/`runBlocking` on futures.
- ANR specifics (Android): also caused by slow `BroadcastReceiver.onReceive` (delegate to WorkManager immediately) and input-dispatch timeouts. ANR rate above the vitals threshold suppresses your store ranking — treat the budget as a release gate, not a dashboard.

### 5.2 Cold start: defer everything that isn't first-frame

Instrument the segments — process start → `Application.onCreate` / `didFinishLaunching` → first frame → first *meaningful* content — and attack the largest one. Typical findings, in order of frequency:

1. **Third-party SDK pile-up in `onCreate`.** Eight SDKs initializing synchronously is the classic startup killer. Lazy-initialize via DI; use Jetpack `App Startup` / deferred initializers; analytics, attribution, and ads SDKs initialize *after* first frame (also required for consent gating, rules/04 §4.10).
2. **Synchronous I/O before first frame** — migrations, feature-flag fetches, "quick" prefs reads. First frame renders from local DB/cache (rules/03); flags use last-known values.
3. **Eager DI graphs** — constructing the entire object graph at launch. Scope construction to the first screen's needs.

Platform tooling:
- Android: **Baseline Profiles** are mandatory equipment — precompiled hot paths routinely cut cold start 20–30%. Generate with Macrobenchmark, verify in CI on a physical-device runner, regenerate per release train.
- iOS: minimize dylib count, avoid `+load` and heavy static initializers, profile with Instruments' App Launch template; watch the watchdog (apps blocking the main thread at launch get killed — visible in MetricKit as launch terminations).
- Show real content skeletons, never a blocking splash hiding three seconds of synchronous setup. A splash screen longer than ~500 ms is concealing a 5.2 violation.

### 5.3 Lists: virtualize, stabilize identity, zero work per row

- Use the virtualizing primitive: `LazyColumn` (stable `key` + `contentType`), SwiftUI `List`/`LazyVStack` with stable `Identifiable` IDs, RN **FlashList** (or `FlatList`; never `.map()` inside a `ScrollView`), Flutter `ListView.builder` with `itemExtent`/`prototypeItem` when rows are uniform.
- **Stable keys are correctness and performance:** unstable identity (index keys, regenerated UUIDs) forces full rebind/recompose on every change, breaks item animations, and corrupts scroll position on insert.

```kotlin
// BAD: index keys — insert at top rebinds every row
LazyColumn { itemsIndexed(orders) { i, o -> OrderRow(o) } }

// GOOD
LazyColumn {
    items(orders, key = { it.id }, contentType = { it.type }) { OrderRow(it) }
}
```

- Row bodies do **zero** work: no formatter creation, no date math, no image decode (5.4), no allocation-heavy mapping. Precompute display fields in the repository/mapper layer (`displayDate: String` on the UI model), off-main.
- Paginate at the data layer (Paging 3, cursor queries, TanStack Query infinite) — loading 10k rows and virtualizing only the rendering still pays full memory and query cost.

### 5.4 Images: dedicated loader, decode to display size, two cache levels

- Use the platform-standard loader: Coil (Compose/KMP), Nuke/Kingfisher (iOS; `AsyncImage` is fine for simple cases with URLCache tuned), `expo-image` (RN), `cached_network_image` (Flutter). Hand-rolled `URLSession`→`UIImage` pipelines lose decode-off-main, downsampling, request dedup, and caching in one stroke.
- **Downsample at decode time to display size.** Decoding a 4000-px photo into a 120-px avatar wastes ~100× the memory (decoded size = w×h×4 bytes, regardless of file size) and is the most common cause of list jank plus background OOM kills.
- Two cache levels, both bounded: memory LRU sized as a fraction of the heap, plus disk. Serve size-variant URLs and modern formats (WebP/AVIF/HEIC) from the CDN — client-side resizing of giant originals is paying twice.
- Placeholder + crossfade beats layout shift; cache keys must include the size variant or you'll serve thumbnails into full-screen viewers.

### 5.5 Memory: respond to pressure, find leaks before users do

- Implement `onTrimMemory` / `didReceiveMemoryWarning`: drop memory caches, release decoded bitmaps, close what can be reopened. Apps ignoring pressure are first in line for background kill → next open is a cold start → your startup and retention metrics pay for the laziness.
- Leak discipline: **LeakCanary** in Android debug builds with CI failure on detected leaks; Xcode Memory Graph + Instruments Leaks in the iOS release ritual. The usual suspects: closures strongly capturing `self`, Activity/Context captured by singletons, listeners/observers never unregistered, Flow/Rx collections outliving their scope, NotificationCenter tokens dropped.
- Soak test: 10 minutes of scripted core-loop usage (Macrobenchmark/XCUITest) asserting flat RSS. Catches the "leaks 200 KB per screen visit" class that no unit test sees.

### 5.6 Battery and radio: batch, coalesce, respect the schedulers

- **Radio wake-ups dominate network battery cost** — one request every 30 s keeps the radio in high-power state continuously. Batch small requests, coalesce via WorkManager/BGTaskScheduler (rules/03), prefer push-triggered sync over polling, and enable gzip/Brotli + HTTP/2 connection reuse.
- **Location is the top battery-complaint generator:** request the coarsest accuracy and longest interval the feature tolerates; stop updates the instant the feature ends (audit for dangling `startUpdatingLocation`/`requestLocationUpdates`); use geofencing and significant-change APIs instead of continuous GPS; background location triggers extra store review scrutiny on both platforms and must be product-essential.
- No wakelocks for convenience — Android vitals tracks excessive wakeups and partial wakelocks as bad behavior. No iOS background audio/location modes kept alive to fake background execution (App Review and the battery screen both catch it).
- Defer non-urgent work to charging+unmetered constraints; users notice the app that drained 8% overnight, and the OS battery screen names you.

### 5.7 App size is a conversion metric

Install conversion drops measurably with download size, and storage-pressure uninstalls target the biggest apps first.

- Android: AAB (mandatory for new Play apps) + R8 with resource shrinking; per-device compressed download tracked in Play Console (the limits in the budget table apply to compressed downloads, not the bundle; 200 MB is only the cellular-warning threshold); Play Asset Delivery / Feature Delivery for large content and rarely-used features; strip unused locales/ABIs (`resConfigs`, ABI splits come free with AAB).
- iOS: App Thinning handles per-device slicing; audit the App Store Connect app-size report per release; asset catalogs with on-demand resources for big media.
- Cross-platform runtimes add a real floor (Flutter/RN baseline MBs) — accepted at stack choice time (rules/01), but the *delta per release* is yours: CI prints the size diff per PR and the release gate requires sign-off on regressions. Lazy-download ML models, fonts, and media; never ship debug symbols or test fixtures in release artifacts.

### 5.8 Jank: measure on weak hardware, keep work off the render path

- Keep a **low-end test device** in rotation — a 4-year-old mid-tier Android and the oldest supported iPhone. Jank invisible on a flagship is the median user's daily experience; performance sign-off on a dev phone is not sign-off.
- Framework-specific hygiene:
  - **Compose:** read state at the lowest scope; `derivedStateOf` for derived values; defer reads with lambda modifiers (`Modifier.graphicsLayer { translationY = offset }` instead of recomposing on every scroll tick); check skippability with compiler reports for hot composables; hoist unstable lambdas.
  - **SwiftUI:** keep `body` cheap and value-typed; split observed state so unrelated changes don't invalidate large trees (`@Observable` fine-grained tracking helps but doesn't absolve giant views); profile with Instruments' SwiftUI template; avoid `AnyView` in hot paths.
  - **React Native:** animations on the UI thread via Reanimated worklets; no per-frame bridge/JSI chatter; `React.memo` + stable props for list rows; Hermes profiles for JS hot spots.
  - **Flutter:** `const` constructors everywhere applicable; `RepaintBoundary` around expensive repainting subtrees; DevTools rebuild stats; shader-compilation jank addressed (impeller default on both platforms — verify if targeting older Flutter).
- Animations: drive them from the compositor/render thread (platform animation APIs, Reanimated, Core Animation) — main-thread-tick animations jank under any load.

### 5.9 Production performance telemetry, not just lab numbers

Lab benchmarks regress quietly; production distributions are the truth.

- **iOS: MetricKit** — launch times, hang rate, memory peaks, disk writes, plus `MXSignpostMetric` custom spans — reviewed per release alongside Xcode Organizer's hangs/launch/termination reports.
- **Android: Android vitals** (ANR, crash, startup, slow/frozen frames, wakeups — with store-ranking consequences) + **Macrobenchmark** in CI + `JankStats` for in-field frame data tagged by screen.
- One APM (Sentry, Firebase Performance, Datadog, Embrace) for screen-load traces and network latency distributions, tagged with app version, OS, device class, and **active feature flags** — flag-tagged regressions are how you catch a bad rollout at 5% instead of 100% (rules/06 §6.5).
- Track **p90/p95, not means** — mobile distributions are long-tailed and the tail is where churn lives. Alert on per-release regression of p95 cold start, p95 screen load, ANR rate, and crash-free rate; these alerts are the staged-rollout gates.

## Audit checklist

- [ ] Budgets documented in-repo with CI/telemetry enforcement; numbers exist for startup, frames, ANR, crash-free, size, memory.
- [ ] StrictMode (debug/CI) and Main Thread Checker active; no disk/network/parse/decode on main in hot paths; formatters cached; no `runBlocking`/`.get()` on main.
- [ ] Startup segments instrumented; SDKs lazy-initialized post-first-frame; first frame renders from local data; Baseline Profiles generated and benchmarked (Android); no blocking splash hiding setup.
- [ ] Long lists virtualized with stable keys and `contentType`; row bodies free of formatting/decoding/allocation; pagination at the data layer; RN lists on FlashList/FlatList, never mapped ScrollViews.
- [ ] Standard image loader; decode-time downsampling verified (inspect memory cache entry sizes); bounded memory+disk caches; CDN size variants.
- [ ] Memory-pressure callbacks implemented and tested; LeakCanary in CI; soak test asserts flat memory; release ritual includes Instruments/Memory Graph pass.
- [ ] Network batched and coalesced; no polling where push suffices; location coarsest/shortest possible and provably stopped; no convenience wakelocks; vitals wakeup metrics clean.
- [ ] AAB + R8 + shrinking; per-device download size tracked; CI size-delta gate; no symbols/fixtures in release artifacts.
- [ ] Jank validated on low-end hardware; framework-specific recomposition/rebuild hygiene applied to hot screens; animations off the main thread.
- [ ] MetricKit + Android vitals reviewed per release; APM traces tagged by version/device/flags; p95 alerts wired to rollout gates; ANR < 0.47% and crash-free ≥ 99.9% or a dated remediation plan exists.
