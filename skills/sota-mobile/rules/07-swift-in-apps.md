# 07 — Swift in apps

**The Swift language now has its own skill, `sota-swift`** (2026-10-07): concurrency and
data-race safety, optionals and errors, ARC and retain cycles, unsafe code, security, SwiftPM
supply chain, tooling and testing all live there, for every target. Read it for any Swift code.
This file keeps only what is specific to Swift inside an iOS or macOS **app**. (Until 2026-10-07
this file held the language rules; they moved to `sota-swift` rules/01–09.)

## 1. Isolation for UI code

- App and UI modules use **default main-actor isolation** (SE-0466, Swift 6.2:
  `.defaultIsolation(MainActor.self)`) instead of `@MainActor` on every type; keep domain and
  networking modules `nonisolated` so they run off the main actor (`sota-swift` rules/03 §1).
- Work that would block a frame (decoding, image processing, crypto) leaves the main actor
  explicitly — a `@concurrent` function or a separate actor — and returns its result to it.

## 2. View-owned tasks

- SwiftUI's `.task { }` modifier ties a task to the view's lifetime and cancels it on
  disappearance; prefer it to a `Task { }` started in `onAppear`, which nothing cancels.
- View models that start unstructured tasks store the handle and cancel it in teardown
  (`sota-swift` rules/03 §4).

## 3. Leaks in UI code

- The usual app cycles: a view model capturing `self` in a stored closure, delegates declared
  without `weak`, `Timer` targets, notification observers and Combine `AnyCancellable`s stored on
  the object they capture. Rules and fixes: `sota-swift` rules/04 §1.
- Verify on device: the memory-graph debugger and Instruments Leaks (rules/05), plus a
  `deinit`-fires assertion in tests for view models and controllers.

## 4. Tests that stay on XCTest

- Swift Testing is the default for new unit tests (`sota-swift` rules/08 §4). UI automation
  (XCUITest) and `measure`-based performance tests remain XCTest; keep them there knowingly.

## 5. Binary SDKs in an app

- Every remote `binaryTarget` and vendored framework is in the binary inventory, carries a
  checksum (`sota-swift` rules/09 §1), and its privacy manifest and required-reason APIs are
  accounted for in the app's own manifest (rules/04).

## Audit checklist

- [ ] UI modules use default `MainActor` isolation; domain/networking modules stay `nonisolated`; frame-blocking work leaves the main actor explicitly.
- [ ] View-owned async work uses `.task { }` or a stored, cancelled `Task` handle — no uncancelled `Task { }` from `onAppear`.
- [ ] View models and controllers have `deinit`-fires tests; cycles in closures, delegates, timers, observers and stored cancellables reviewed; leaks checked with the memory graph on device.
- [ ] XCUITest and `measure` suites remain on XCTest deliberately; new unit tests use Swift Testing.
- [ ] Binary SDKs carry checksums and their privacy manifests are reflected in the app's own.
- [ ] Every language-level Swift finding in the app is reported against `sota-swift`, not this file.
