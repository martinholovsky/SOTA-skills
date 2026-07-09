# 06 — Release & Operations

The defining constraint of mobile: **you cannot roll back a shipped binary.** Store review takes hours to days, users update on their own schedule, and a meaningful cohort runs every version you ever shipped — for years. All mobile release engineering is the discipline of designing around that single fact. The toolkit: kill switches instead of rollbacks, staged exposure instead of big bangs, forced updates as the last resort, and a server that never assumes clients are current.

## Store requirements (verified June 2026 — these ratchet annually; re-check Apple's "Upcoming Requirements" page and Play policy updates quarterly, with a named owner)

### 6.1 iOS / App Store

- **Privacy manifest (`PrivacyInfo.xcprivacy`)** — mandatory since May 2024. Declares: collected data types (feeds the Privacy Nutrition Label), tracking domains, and **required-reason APIs** (UserDefaults, file timestamps, system boot time, disk space, active keyboard APIs) with approved reason codes. App Store Connect **rejects uploads** with undeclared required-reason API use — including use inside third-party SDKs. Commonly-used SDKs must ship their own manifest and signature; prefer dependencies that do.
- **SDK floor:** uploads must be built with **Xcode 26 / the iOS 26 SDK since April 28, 2026**. The annual SDK bump is a real project, not a version-number edit — the 26 SDK applies the Liquid Glass appearance to system controls by default, so the bump includes a UI regression pass.
- Review logistics: working demo account, export-compliance/crypto declaration, sign-in-with-Apple obligation if you offer other third-party logins, in-app account deletion if you have account creation, updated age-rating questionnaire answered (mandatory since Jan 31, 2026 — submissions are interrupted without it; existing ratings were auto-migrated to the new tiers, so review them for accuracy), App Review notes for anything non-obvious (hardware requirements, geo-gated content).
- Distribution lanes: TestFlight internal (instant, 100 testers) → TestFlight external (review-gated, 10k) → App Store **phased release**: automatic 7-day ramp (1→2→5→10→20→50→100%) — pausable, but it only paces *automatic* updates; users updating manually get the new version immediately, so phased release is a damper, not a gate.

### 6.2 Android / Google Play

- **Data safety form** must accurately cover app + every SDK's collection and sharing; Google compares declarations against observed behavior and enforcement actions follow mismatches.
- **Target API ratchet:** API 36 required for new apps and updates by **Aug 31, 2026** (API 35 floor for Wear OS/TV). **16 KB page-size support** required since **Nov 1, 2025** for apps targeting Android 15+ with native code (rules/01 has the behavior-change details for each bump).
- **Play App Signing** (Google holds the app signing key) is standard: protect the *upload key*, document the upload-key reset process before you need it, and keep signing entirely in CI.
- AAB is the required upload format. The free **pre-launch report** runs your build on a device farm per track upload — read it; it catches crashes, accessibility, and security warnings at zero cost.
- Tracks: internal → closed → open → production with **staged rollout** at a percentage you control. Critical mechanic: a *halted* staged rollout leaves the affected users on the bad build — your fix path is always a new, higher version rolled out fast (see 6.5).

## Rules

### 6.3 Forced-update mechanism ships in v1.0

Some day a shipped version will have a security hole, a data-corrupting bug, or a dependency on an API you must kill. The mechanism must already be in the oldest binary that matters — which means it ships in the first one:

- On launch and periodically, the app calls a version-policy endpoint **you control**:

```json
{
  "minSupportedBuild": 2024,
  "recommendedBuild": 2107,
  "message": { "en": "This version is no longer supported." },
  "storeUrl": "https://apps.apple.com/app/id..."
}
```

- Below `minSupportedBuild` → blocking, non-dismissible screen with a store link. Below `recommendedBuild` → dismissible nudge with snooze. Everything localized and server-controlled.
- **Fail open:** the policy endpoint being down must never brick the app (cache last verdict, default to allow). The blocking screen itself must be the most-tested screen in the app — a forced-update screen that crashes is an unrecoverable brick for that cohort.
- Platform helpers layer on top: Play **In-App Updates API** (immediate flow for forced, flexible for recommended) gives a better Android UX; iOS has no system API — your endpoint + store link is the mechanism.
- Exercise the blocking path in every release candidate (point staging at a policy that blocks the RC).

### 6.4 Feature flags and kill switches: the only rollback you have

- **Every feature with server interaction, and every risky change, ships behind a remote flag whose hardcoded default is the safe state** (usually OFF). Flags fetch at launch, cache last-known values, and degrade to defaults when the flag service is unreachable — flag-service downtime must not take the app down with it.
- Maintain the distinction:
  - **Experiment flags** — A/B tests, temporary by definition; a removal ticket is created with the flag; stale experiment flags create 2^n untested configuration combinations.
  - **Ops kill switches** — permanent, deliberate, documented: certificate-pinning enforcement (rules/04 §4.3), sync engine, each third-party SDK's initialization, chatty/expensive subsystems, any feature that can hammer your backend. Auditors: a server-dependent feature with no kill switch is HIGH — when it misbehaves in a shipped binary, there is no other off button.
- Kill switches are **exercised, not just installed**: flip each one in staging (ideally periodically in production canaries) and verify the app degrades as designed. An untested kill path is a hope, not a control.
- Flag state is attached to crash reports and APM traces (rules/05 §5.9) — otherwise you can't attribute a regression to a rollout.

### 6.5 Staged rollouts with explicit promotion gates

- Never 0→100%. Standard ladder: internal track/TestFlight internal → beta (open testing / TestFlight external) → production at 1% → 5% → 25% → 50% → 100%.
- Promotion between stages is a **decision made against written gates**, not a timer:
  - Crash-free sessions ≥ target (rules/05 budget) and no *new* top-10 crash signature.
  - ANR rate and p95 cold start flat versus the previous release.
  - Core business metrics (activation, purchase success) flat.
- Automate the gate check against the crash/APM dashboards; a human approves, a dashboard decides.
- Platform mechanics to internalize:
  - **Play:** halting a staged rollout strands affected users on the bad build until you roll out a higher `versionCode` — keep a hotfix branch + fast-track release process rehearsed.
  - **App Store:** phased release pauses only slow *automatic* updates; manual updaters still get it. For a truly bad build, pause phased release *and* submit an expedited-review hotfix (Apple grants expedited review sparingly — have the justification ready).
- Hotfix discipline: the hotfix branches from the released tag, contains only the fix, and rides the same gates at an accelerated ramp.

### 6.6 Crash reporting and symbolication are release blockers

- Crash SDK (Crashlytics, Sentry, Embrace, …) initializes **first** in the app lifecycle — before the DI graph, before anything that can crash. Early-startup crashes in uninstrumented code are the ones you can least afford to lose.
- **Symbol upload is automated in CI and verified per release:** dSYMs (iOS — including for frameworks and extensions) and R8 `mapping.txt` + NDK native symbols (Android). An unsymbolicated crash report is noise; discovering missing dSYMs during an incident is the standard failure. Make "RC crash symbolicates correctly" a checklist item (force a test crash in the RC build).
- Attach context: app version/build, OS, device class, low-memory indicator, **active feature flags** (6.4), and PII-scrubbed breadcrumbs (navigation + key actions). Flag state on crashes is what turns "crash rate up" into "kill switch X, now."
- Watch platform-native sources too — they see what your SDK can't: **Xcode Organizer + MetricKit** diagnostics catch watchdog kills, hangs, and pre-SDK-init crashes; **Play vitals** catches ANRs and crashes from before instrumentation and feeds store ranking.
- Triage SLO wired to rollouts: a new signature affecting more than N users during a ramp halts promotion automatically (6.5).

### 6.7 OTA updates (RN/Expo): powerful, policy-bounded, operationally identical to releases

- React Native: Expo Updates / self-hosted OTA ships JS bundle changes without store review. Policy boundaries (long-standing, both stores): downloaded code must run in the platform's sanctioned interpreter (JavaScriptCore/Hermes/WebKit), must not change the app's primary purpose, and must not circumvent review for things that deserve review. Flutter compiles Dart AOT — **no generally store-sanctioned code push for Flutter on iOS**; evaluate any "code push for Flutter" product's current store standing before adopting it.
- Treat every OTA push as a production deploy with the full 6.5 discipline:
  - **Version-targeted:** an OTA bundle declares which binary versions it's compatible with. Shipping JS that calls a native module absent from older binaries is a crash factory aimed precisely at your slowest-updating users. CI must verify bundle↔binary compatibility (Expo runtime versions / manual native-interface versioning).
  - **Staged and instantly rollback-able** — rollback is the entire point of OTA; if your OTA pipeline can't revert in minutes, it's only an outage accelerator.
  - **Gated on the same crash metrics** as binary rollouts, with OTA bundle ID attached to crash reports.
- OTA never delivers: new native modules, permission changes, or payment/purchase-flow changes that would merit review. Keep regular store builds shipping regardless — an app that only OTAs accumulates binary debt (stale SDKs, unpatched native CVEs) invisibly.

### 6.8 The API must serve every binary still alive

Server teams deploy hourly; your two-year-old binary is still calling them tonight. The contract:

- **Every request self-identifies:** `X-App-Version`, build number, platform, OS version headers. The server can then branch, throttle, or sunset *by explicit version predicate* — never by accident.
- **Additive-only evolution** on endpoints old clients touch: never remove, rename, or retype fields; never repurpose enum values (old clients will render them); new required request fields get server-side defaults. New semantics → new endpoint or version, not mutated meaning on the old path.
- Mirror-image client rule: **decoders tolerate unknown fields and absent optionals.** A strict decoder that throws on a new server field is a self-inflicted, fleet-wide outage triggered by a routine backend deploy.

```swift
// BAD: any new enum case from the server kills every shipped build
enum OrderStatus: String, Decodable { case pending, shipped, delivered }

// GOOD: forward-compatible
enum OrderStatus: RawRepresentable, Decodable {
    case pending, shipped, delivered
    case unknown(String)                      // renders as a neutral state in UI
    init(rawValue: String) { ... }
}
```

- **CI contract tests pin the oldest supported client:** record the oldest supported app version's API expectations (request/response fixtures) and run them against every server build. The server team breaking a three-year-old client should fail *their* CI, not your crash dashboard.
- Deliberate sunsetting is a process, not a deploy: measure the affected cohort → announce in-app to that cohort → raise `minSupportedBuild` (6.3) with a grace window → server returns explicit `426 Upgrade Required` (with a client-rendered message) after the cutoff — never a silent 500 or, worse, subtly wrong data.

### 6.9 Testing strategy: a pyramid with device reality at the top

- **Unit (the bulk):** view models, reducers, repositories, sync/outbox logic against fakes — milliseconds each, every commit. Cheap because the architecture made it cheap (rules/02 §2.9).
- **Snapshot:** design-system components and key screens per sealed-state case, across dark mode, large dynamic type/font scale, and RTL. This layer catches the visual regressions E2E suites are too slow and flaky to police.
- **Integration:** repository ↔ real local DB; sync engine against a fake server scripted with the rules/03 edge cases (conflict, resync, poison message); **DB schema migration tests** (Room's `MigrationTestHelper`, GRDB migrator tests) — a failed migration bricks the app for exactly your most loyal, longest-installed users.
- **UI/E2E (a handful):** login, the core loop, purchase — per-PR on emulators/simulators; nightly on a **real-device farm** (Firebase Test Lab, AWS Device Farm, BrowserStack) across an OS × device matrix mirroring your actual user base. Emulators miss OEM skins, real keyboards, memory pressure, and vendor-modified WebViews.
- **Release-candidate ritual**, written down and checked off:
  1. Upgrade-path test: install the previous production build, log in, create data → upgrade to RC → verify data and session survive (migrations, 2.3 restoration).
  2. Fresh-install test (first-run experience, permission pre-prompts).
  3. Forced-update blocking screen exercised (6.3).
  4. Forced test crash symbolicates (6.6).
  5. Play pre-launch report / TestFlight feedback reviewed.

### 6.10 Release cadence and build hygiene

- Ship on a **fixed cadence** (1–2 weeks) from a release branch/train. Small diffs make rollout gates meaningful, regressions bisectable, and hotfixes surgical; quarterly big-bang releases maximize undiagnosable risk and gate-meaningless rollouts.
- **CI-only builds reach stores.** No laptop builds: signing keys and store credentials live in CI secrets with least privilege; provisioning/signing is reproducible (fastlane match or equivalent, Play App Signing).
- Every production build is traceable: commit SHA, CI run, and flag snapshot embedded in the binary and visible in a hidden debug/about screen — "which exact code is crashing" must never require archaeology.
- Maintain user-readable release notes and an internal changelog recording active experiments/flags per build — six months later, "what was different about 4.12?" must have an answer.

## Audit checklist

- [ ] iOS privacy manifest present; required-reason API declarations match actual code and SDK usage; Nutrition Label consistent with observed traffic.
- [ ] Android Data safety form matches observed behavior; Play App Signing on; upload-key reset process documented.
- [ ] Built against currently mandated SDKs/targets (iOS 26 SDK since Apr 2026; Play target API per current deadline); a named owner exists for the annual ratchets and quarterly policy review.
- [ ] Forced-update mechanism: implemented on owned infrastructure, fail-open, localized, blocking path exercised in the RC ritual; Play In-App Updates integrated on Android.
- [ ] Server-dependent/risky features behind remote flags with safe hardcoded defaults; kill switches exist for pinning, sync, and each third-party SDK init; kill paths actually tested; flag-removal tickets created with experiment flags.
- [ ] Staged rollout ladder with written promotion gates (crash-free, no new signatures, ANR/p95/business metrics flat); gate checks automated; hotfix fast-track rehearsed for both stores' mechanics (Play halt-strands-users; iOS phased-release limits).
- [ ] Crash SDK initialized first; dSYM/mapping/native-symbol upload automated and *verified* via forced test crash per RC; flag state and scrubbed breadcrumbs attached; Organizer/MetricKit and Play vitals reviewed alongside the SDK dashboard.
- [ ] OTA (if used): bundle↔binary compatibility enforced in CI; staged, rollback-able in minutes, crash-gated; nothing review-worthy shipped via OTA; store builds still ship regularly.
- [ ] All API requests carry version headers; additive-only evolution on live endpoints; client decoders tolerate unknown fields/enum cases; contract tests pin the oldest supported client; sunsets use cohort measurement → in-app notice → forced update → explicit 426.
- [ ] Test pyramid intact: unit bulk; snapshots incl. dark mode/font-scale/RTL; integration incl. DB migration tests and sync edge cases; ≤ ~10 E2E flows; nightly real-device-farm matrix.
- [ ] RC ritual documented and followed (upgrade-path, fresh-install, forced-update, symbolication, pre-launch report).
- [ ] Fixed release cadence; CI-only signed builds; commit SHA + flag snapshot traceable from any production binary.
