# 01 — Platform & Stack Choice

Stack choice is a one-way door: migrating a shipped app between stacks is a rewrite, and a half-migrated hybrid is worse than either endpoint. Decide deliberately, record the rationale, and revisit only on major product inflection points.

## Current baselines (verified June 2026 — re-verify before relying on specifics)

| Item | State |
|---|---|
| iOS | iOS 26 current (26.5.x); iOS 27 announced at WWDC (June 8–12, 2026), developer betas out, public release expected Sept 2026. Apple uses year-based naming (jumped 18 → 26 in 2025). |
| iOS SDK requirement | Since **April 28, 2026**, App Store uploads must be built with Xcode 26 / iOS 26 SDK. Building with the 26 SDK applies the Liquid Glass appearance to system controls by default — re-test UI on SDK bump. |
| Android | Android 17 (API 37) stable since June 16, 2026 (Pixels first, OEM rollouts ongoing); Play target-API mandate remains API 36 (next row). |
| Play target API | New apps and updates must target **API 36 by Aug 31, 2026** (API 35 floor for Wear OS / Android TV). Stale targets make the app invisible to new users on newer devices. |
| Play 16 KB pages | Since **Nov 1, 2025**, new apps/updates targeting Android 15+ must support 16 KB page sizes on 64-bit devices. Pure-JVM/Kotlin apps comply automatically; anything with native `.so` libraries (including most RN/Flutter plugins) must use compatible builds. Verify in Play Console app bundle explorer. |
| Swift | Swift 6.x on current Xcode (verify the latest). Swift 6 strict concurrency is the norm for new code. |
| Kotlin | Kotlin 2.x with K2 compiler; coroutines/Flow standard. |
| SwiftUI / Compose | Default UI toolkits for new native code on both platforms. UIKit/Views are for interop, framework gaps, and legacy — not greenfield screens without a stated reason. |
| React Native | 0.86 (Jun 2026) — fixes the Android 15+ edge-to-edge issues (insets, `KeyboardAvoidingView`) that the mandatory API-36 edge-to-edge (1.4) exposes; repo moved to the `react` GitHub org under the React Foundation. 0.85 (Apr 2026) **removed** the Bridge from the codebase entirely (no fallback, no interop, no shim). New Architecture (JSI + Fabric + TurboModules) became non-disableable in 0.82 (Oct 2025); the Bridge interop layer stayed functional through 0.84. Hermes is the default engine on both platforms. |
| Flutter | recent stable (~4 releases/year, verify current); Material/Cupertino libraries being split into separately-versioned packages. |
| Kotlin Multiplatform | KMP stable since 2023 for shared logic. Compose Multiplatform for iOS **stable since 1.8.0 (May 2025)** — production-ready (Netflix, Cash App scale), but iOS fidelity still trails SwiftUI for platform-idiomatic feel; budget per-platform polish. |
| OWASP MASVS | v2.1 current (adds MASVS-PRIVACY); verification levels replaced by MAS profiles + MASWE weakness enumeration. MASTG v2.0.0 stable (June 2026) supplies the test procedures. |

## Rules

### 1.1 Choose the stack from team and product constraints, not fashion

Work through the factors in priority order and stop at the first decisive one:

1. **Team skills.** A Swift/Kotlin team forced onto Flutter (or a JS team forced onto native) ships worse software for at least a year. For teams under ~8 engineers, existing skills dominate every other factor.
2. **Platform fidelity required.** Heavy platform integration — widgets, watchOS/Wear OS companions, App Intents/Siri, CarPlay/Android Auto, camera pipelines, real-time audio, platform-design-language UX — favors native. Cross-platform frameworks *can* reach all of these, but every integration point is a bridge you write, test, and maintain on two platforms forever.
3. **Where is the expensive code?** If the hard part is business logic (sync engine, domain rules, pricing, crypto), KMP shares the logic and keeps fully native UI — the lowest-risk sharing model. If the hard part is hundreds of screens, RN/Flutter/CMP share UI too, at the cost of fidelity and bridge maintenance.
4. **One platform or two?** A single-platform product gains nothing from a cross-platform framework. Don't pay the abstraction tax for a hypothetical second platform that may never ship.
5. **Hiring market.** RN taps the largest pool (JS/TS); Flutter and KMP pools are smaller but strong; native pools are deep but bid up.

Defaults when nothing else dominates:

| Situation | Default |
|---|---|
| New native iOS | SwiftUI + Swift 6 concurrency; UIKit interop where SwiftUI gaps bite |
| New native Android | Jetpack Compose + Kotlin coroutines/Flow |
| Cross-platform, JS/TS team | React Native (New Architecture only) with Expo tooling |
| Cross-platform, pixel-identical brand UI | Flutter |
| Kotlin team wanting shared UI | Compose Multiplatform |
| Share logic, keep native UI | Kotlin Multiplatform (logic-only) |

Anti-patterns to flag in audits:
- A cross-platform app with > ~30% platform-specific native code per platform — the sharing premise has failed; the team maintains three codebases.
- Two stacks in one app (e.g., RN screens embedded in a native app "temporarily" for 3+ years) without a written convergence plan.
- Framework chosen by a since-departed engineer's preference, with no one remaining who can debug the native layer.

### 1.2 Ask whether a web app suffices before building an app at all

An installable app is justified by at least one of: offline operation, push notifications as a core loop, background processing, deep hardware access (BLE, NFC, sensors, camera pipelines), home-screen presence as a retention strategy, or store distribution as an acquisition channel.

If the product is "a website the user visits sometimes," a responsive web app or PWA avoids the entire cost structure of this skill: store review latency, binary permanence, two codebases, forced-update plumbing, annual SDK ratchets. PWAs on iOS remain second-class (constrained push and background capabilities relative to Android); treat current iOS PWA capability as something to verify against Safari/WebKit release notes, not assume in either direction.

The hybrid middle ground — a native shell around WebViews — buys store presence and push at the cost of web-feeling UX. It is legitimate for long-tail content screens inside a real app (see WebView hardening, rules/04 §4.7), and a smell as the app's primary architecture for interaction-heavy products.

### 1.3 Set the minimum OS floor by data, and write it down

- A policy that ages well: **latest major minus 2** (e.g., iOS 24-equivalent floor under iOS 26; Android floor around API 28–30 depending on market). But check *your* analytics, not global stats — emerging-market Android skews years older than US iOS; enterprise fleets pin old versions.
- Raising the floor later is cheap: existing users keep the last compatible binary; you stop shipping them new features. Lowering a floor is impossible. Still, don't start lower than your market demands — every supported major is test-matrix cost.
- Every `if #available` / `Build.VERSION.SDK_INT` branch is a permanent test obligation. A floor of N-2 keeps the matrix at three majors.

```swift
// BAD: floor set by a developer's personal device
// IPHONEOS_DEPLOYMENT_TARGET = 26.0
// → cuts a third of devices for zero product reason

// GOOD: floor recorded with rationale and a revisit date
// IPHONEOS_DEPLOYMENT_TARGET = 24.0
// Covers 96% of our MAU (analytics snapshot 2026-05).
// Lets us use Observation + NavigationStack unconditionally.
// Revisit every September after the new iOS ships.
```

```kotlin
// BAD: copy-pasted template value nobody owns
minSdk = 21   // Android 5.0, 2014 — forces multidex hacks and dead API branches

// GOOD
minSdk = 28   // 99.2% of our installs (Play Console, 2026-05); revisit annually
```

### 1.4 Distinguish minSdk/deployment target from targetSdk/build SDK

These are different knobs with different policies:

- **Build SDK / targetSdk** tracks *store mandates*: iOS 26 SDK since April 2026; Android target API 36 by Aug 31, 2026. Bump within weeks of each annual deadline. Bumping in the deadline week under pressure is how behavior-change regressions ship to 100% of users at once.
- **minSdk / deployment target** tracks *your users* (1.3) and changes rarely.

Each Android targetSdk bump activates behavior changes for your app. For API 36 specifically:
- **Edge-to-edge is mandatory** — the opt-out flag is ignored; audit every screen for window-inset handling (status/navigation bar overlap, IME insets).
- **Predictive back is on by default** — `onBackPressed()` is no longer called and `KEYCODE_BACK` is not dispatched; migrate to `OnBackInvokedCallback`/`BackHandler` or back navigation silently breaks.

Treat the annual targetSdk bump as a named project with an owner: read the behavior-changes page, grep for affected APIs, test on the new OS, then bump — not the reverse order.

### 1.5 React Native: New Architecture only, Hermes, no orphaned bridges

- The legacy architecture and Bridge interop layer are gone (interop functional through 0.84; deleted in RN 0.85). Reject any dependency that hasn't migrated to TurboModules/Fabric — it will not load. Audit `package.json` for unmaintained native modules (last publish > 18 months, open New-Architecture issues) during every stack review.
- Stay within ~2 versions of current RN. Upgrade debt compounds brutally because Gradle, AGP, Xcode, and CocoaPods/SPM drift underneath the framework; a 5-version jump is routinely a multi-week project.
- Every custom native module is a maintenance contract across two platforms. Prefer maintained community modules (check Expo Modules ecosystem first); isolate unavoidable custom native code behind a single typed TS interface so it can be replaced without touching product code.
- Use Expo tooling (prebuild, EAS) even for "bare" apps unless a hard constraint forbids it — hand-maintained native projects for RN apps are where upgrades go to die.

```ts
// BAD: native module accessed ad hoc from product code everywhere
import { NativeModules } from 'react-native';
NativeModules.PaymentsBridge.charge(amountString); // untyped, untestable, scattered

// GOOD: one typed boundary, mockable in tests
// payments/native.ts
export interface Payments { charge(cents: number, currency: string): Promise<Receipt>; }
export const payments: Payments = TurboModuleRegistry.getEnforcing<PaymentsSpec>('Payments');
```

### 1.6 Flutter and Compose Multiplatform: own the native edges

- Flutter renders its own pixels — brand-consistent by construction, but platform conventions (text selection behavior, scroll physics, context menus, accessibility traits) need deliberate effort; allocate design review on real devices of both platforms, not just goldens.
- Keep Flutter within one stable release of current (quarterly cadence) and watch the Material/Cupertino package split — pinning old design packages while upgrading the SDK is the new upgrade hazard.
- CMP on iOS is stable but young: profile scrolling and text-heavy screens on real iPhones (jank and memory regressions are the reported weak spots), and keep an escape hatch — CMP interops cleanly with SwiftUI screens, so the riskiest screens can go native without abandoning the shared core.
- For all three sharing models, the **plugin/native layer is your risk register**: list every plugin with native code, its maintenance status, and its 16 KB page-size compliance (Android, see baselines).

### 1.7 Cross-platform does not mean zero native engineers

Budget at least part-time iOS and Android native capability for any RN/Flutter/KMP team. Build systems, store submissions, native crash triage, permission flows, background-execution quirks, and annual platform behavior changes all land in native code. An RN team with nobody who can read a symbolicated native stack trace is blind to an entire class of production crashes — typically the worst ones (startup, OOM, native module misuse).

### 1.8 Record the decision

Create `docs/adr/0001-mobile-stack.md` (or equivalent) capturing: the chosen stack; the 1.1 factors as actually weighed; minimum OS floor with revisit cadence; explicit non-goals ("no iPad-optimized layout in v1", "no tablet Android"); and the trigger conditions that would reopen the decision. Auditors: absence of any recorded rationale on a multi-platform codebase is a MEDIUM finding — it reliably predicts incoherent platform divergence and relitigated arguments.

## Audit checklist

- [ ] Stack rationale recorded (ADR or equivalent); the actual codebase matches it; no second stack accreting without a convergence plan.
- [ ] iOS: built with the currently required SDK (iOS 26 SDK as of Apr 28, 2026); Apple "Upcoming Requirements" page reviewed and nothing unaddressed.
- [ ] Android: targetSdk meets the current Play deadline (API 36 by Aug 31, 2026); API-36 behavior changes (edge-to-edge insets, predictive back) handled, not suppressed with opt-out flags.
- [ ] Android: 16 KB page-size compliance verified in Play Console bundle explorer if any native libraries are present (includes RN/Flutter plugin `.so` files).
- [ ] minSdk / deployment target justified by user analytics, documented, with a revisit cadence; no dead `#available`/`SDK_INT` branches below the floor.
- [ ] React Native: within ~2 versions of current stable; New Architecture throughout; Hermes enabled; no dependencies stranded on the removed legacy architecture; custom native code behind one typed boundary.
- [ ] Flutter: within one stable release of current; design-package versions coherent with SDK; no abandoned plugins.
- [ ] KMP/CMP: the shared-code boundary is deliberate (logic-only vs shared UI); iOS-specific polish has a named owner; riskiest screens have a native escape hatch.
- [ ] Plugin/native-module inventory exists with maintenance status per entry.
- [ ] Team has native Swift + Kotlin capability for store, crash, and build-system work even if the app is cross-platform.
- [ ] If the product could be a website, someone has written down why it's an app.
