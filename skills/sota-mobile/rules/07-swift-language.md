# 07 — Swift as a Language

Rules 01–06 cover the mobile *platform*; this file covers **Swift the language** — idioms, concurrency, memory, unsafe interop, packaging, testing. It applies to any Swift target: an iOS app, a server-side service (e.g. Vapor or Hummingbird on SwiftNIO), a CLI, or embedded firmware. Audit Swift code against this file even when the deliverable is not a mobile app.

Baseline (verified July 2026 at [swift.org/blog](https://www.swift.org/blog/)): **Swift 6.3** shipped 2026-03-24; the current toolchain is the 6.3.x patch line (6.3.3 at verification time). The load-bearing line, though, is not the toolchain version but the **language mode**: Swift 6 language mode turns data-race safety into compile-time errors, and Swift 6.2+ made that mode adoptable module-by-module without annotation blizzards.

## Concurrency & data-race safety

### 7.1 Build in Swift 6 language mode; migrate module-by-module

- Swift 6 language mode enforces **complete data-race safety at compile time**: `Sendable` checking across actor/task boundaries, actor isolation, and region-based isolation analysis that proves some non-`Sendable` transfers safe. A codebase still on Swift 5 mode with strict-concurrency warnings suppressed is accumulating latent races — HIGH in audit for concurrent code paths.
- Migration is **per-module** (`swiftLanguageMode(.v6)` in Package.swift / `SWIFT_VERSION = 6`), so "the app is too big" is not a reason to stay on 5 mode; leaf modules first, then work inward. Intermediate step: Swift 5 mode + `-strict-concurrency=complete` to see the diagnostics as warnings.
- Swift 6.2's "approachable concurrency" (verified: [swift.org/blog/swift-6.2-released/](https://www.swift.org/blog/swift-6.2-released/)) removed the main adoption pain:
  - **Default main-actor isolation** per module (`defaultIsolation(MainActor.self)` SwiftSetting): UI/app modules get `@MainActor` implicitly instead of annotating every type. Use it for app targets; leave libraries at `nonisolated` default so they stay usable off the main actor.
  - **Caller's-actor async functions** (opt-in upcoming feature): `nonisolated` async functions run in the caller's execution context instead of always hopping to the global executor — eliminating a whole class of spurious `Sendable` errors.
  - **`@concurrent`** explicitly marks the functions that *should* leave the actor and run in parallel — concurrency becomes something you opt into where profiling justifies it, not the ambient default.
- Audit greps: `@unchecked Sendable`, `@preconcurrency`, `-strict-concurrency=minimal`, `nonisolated(unsafe)`. None is banned, but each is a suppressed check and needs a justification comment stating the manual invariant (e.g. "guarded by `lock`").

### 7.2 Actors: isolation is per-suspension, not per-method

- `actor` is the tool for shared mutable state; a class + `DispatchQueue`/`NSLock` in new code is legacy style and easier to get wrong. But actors are **reentrant**: every `await` inside an actor method is a point where *other* messages interleave. Check invariants **after** each `await`, not just at entry.

```swift
actor AccountCache {
    private var balances: [AccountID: Int] = [:]

    // BAD — balance read before await, written after: interleaved calls double-apply
    func applyBAD(_ tx: Tx) async throws {
        let current = balances[tx.account] ?? 0
        try await ledger.validate(tx)              // suspension: others run here
        balances[tx.account] = current + tx.amount // stale `current`
    }
    // GOOD — re-read state after the suspension; mutation is one synchronous step
    func apply(_ tx: Tx) async throws {
        try await ledger.validate(tx)
        balances[tx.account, default: 0] += tx.amount
    }
}
```

- Don't funnel everything through one global actor: `@MainActor` on business logic serializes it behind UI work (and on server-side Swift there may be no main run loop doing UI at all). Main actor for UI state; separate actors (or plain `Sendable` value pipelines) for the rest.
- `Sendable`: value types with `Sendable` members conform for free — prefer them. `@unchecked Sendable` is an unverified promise; require an adjacent comment naming the synchronization mechanism, and treat one on a class with public mutable `var`s as a finding.
- `Sendable` errors at a boundary are usually telling you a *type* is wrong, not that you need `@unchecked`. Fix order: make it a value type → make it an actor → transfer ownership with a `sending` parameter (region isolation proves the caller keeps no reference) → only then consider `@unchecked Sendable` with a lock.

### 7.3 Structured concurrency, cancellation, and streams

- **Structured first**: `async let` for a fixed set of children, `withTaskGroup`/`withThrowingTaskGroup` for dynamic fan-out. Children are bounded by the scope and cancelled together — no orphans, no leaks.

```swift
// GOOD — bounded fan-out with propagated cancellation and per-item error policy
func thumbnails(for ids: [ImageID]) async throws -> [ImageID: Thumbnail] {
    try await withThrowingTaskGroup(of: (ImageID, Thumbnail).self) { group in
        for id in ids {
            group.addTask { (id, try await self.render(id)) }
        }
        var out: [ImageID: Thumbnail] = [:]
        for try await (id, thumb) in group { out[id] = thumb }  // first throw cancels siblings
        return out
    }
}
```

- Unstructured `Task { }` needs an owner that cancels it (store the handle; cancel in teardown — SwiftUI's `.task` modifier does this for you). `Task.detached` also discards priority and task-locals — it is almost never what you want; each use needs a reason.
- **Cancellation is cooperative.** A task that never checks never stops. Long loops call `try Task.checkCancellation()` or check `Task.isCancelled`; wrap callback resources in `withTaskCancellationHandler`. Audit: search long-running loops and retry/polling code for any cancellation check.
- **Never block the cooperative pool**: no `DispatchSemaphore.wait()`, `sleep()`, or synchronous I/O to bridge sync→async — under load this deadlocks the width-limited thread pool. Bridge with continuations instead (`withCheckedThrowingContinuation`, resumed **exactly once** on every path — double/never-resume is a runtime crash or a permanent hang).
- `AsyncStream`/`AsyncThrowingStream` bridge callback and delegate APIs into `for await` loops — but choose the **buffering policy** deliberately. The default buffers unboundedly: a fast producer (sensor events, socket frames) with a slow consumer is a memory leak with extra steps. `.bufferingNewest(n)`/`.bufferingOldest(n)` make the drop policy explicit; if every element matters, the design needs real backpressure (pull-based iteration or an explicit bounded queue), not a bigger buffer.
- One `AsyncSequence` instance generally supports **one** consumer; a second `for await` on the same stream silently splits elements between them. Multicast needs an explicit fan-out layer.

## Value semantics & type design

### 7.4 Structs by default; classes only for identity

- Default to `struct` + `let`. Value semantics make code trivially `Sendable`, testable, and free of spooky mutation at a distance. Reach for `class` only when identity or shared mutable state is the point — and if the state is shared *across concurrency domains*, that's an `actor`, not a class.
- Standard collections (`Array`, `Dictionary`, `String`, `Data`) are **copy-on-write**: assignment is O(1) until mutation. Two consequences: passing big collections around is cheap (don't "optimize" with classes), and mutating a shared instance triggers a full copy — in hot loops, mutate in place and watch for accidental extra references defeating uniqueness. Custom large value types wrapping a reference-typed buffer implement COW the same way:

```swift
struct Bitmap {
    private var storage: PixelStorage          // reference type holding the buffer
    mutating func set(_ p: Pixel, at i: Int) {
        if !isKnownUniquelyReferenced(&storage) {   // shared → copy before write
            storage = storage.copy()
        }
        storage[i] = p
    }
}
```

- Mark classes `final` unless subclassing is a designed extension point — enables static dispatch and stops unplanned inheritance. `struct` needs no such marking; that's another point for structs.
- **Noncopyable types** (`~Copyable`, available since Swift 5.9) encode unique ownership of a resource — file descriptors, connections, locks — so "two owners" is a compile error instead of a double-close at runtime. Pair with the `borrowing`/`consuming` parameter modifiers: `borrowing` reads without taking ownership; `consuming` takes the value and ends the caller's access (the natural signature for `close()`/`send()`-style terminal operations). Use them at resource boundaries; don't retrofit them onto ordinary model types.

### 7.5 Protocols, generics, and enums

- Protocol-oriented design: depend on capabilities (`protocol Clock`, `protocol TokenStore`), not concrete types — this is also the DI seam rules/02 requires. But don't invent a protocol per type "for testability" when a struct of closures or a generic parameter is simpler.
- **`some` over `any`**: `some P` (opaque type) keeps static dispatch and zero boxing; `any P` (existential) allocates a box and dynamically dispatches. Use `any` only where heterogeneity is required (mixed-type collections, storage). Hot-path code full of `any P` parameters instead of generics is a performance finding (rules/05 discipline applies to CPU too).
- Model state with **enums with associated values**, and switch exhaustively **without `default`** on enums you own — then adding a case is a compile error at every site that must care, instead of a silent fallthrough. `default` is acceptable only on non-frozen enums from other modules (where `@unknown default` is the right spelling).

## Optionals & error handling

### 7.6 Optionals: unwrap early, crash never (accidentally)

- `guard let` at function top is the idiom: unwrap-or-exit, then straight-line code with non-optionals. Nested `if let` pyramids and repeated `foo?.bar?.baz` chains signal a missing early exit or a type that should not be optional.

```swift
// BAD — pyramid; the happy path is three indents deep
if let user = session.user {
    if let email = user.email {
        if let domain = email.split(separator: "@").last { register(domain) }
    }
}
// GOOD — invariants established once, straight-line code after
guard let user = session.user,
      let email = user.email,
      let domain = email.split(separator: "@").last
else { return .missingProfileData }
register(domain)
```
- **`!` force-unwrap, `try!`, and `as!` are assertions, not error handling.** In production code paths each is a crash waiting for input you didn't foresee. Legitimate uses (programmer invariant, e.g. a bundled resource) get a comment stating the invariant — or better, `preconditionFailure("...")` with a message so the crash report says *why*. Audit grep: `!` unwraps, `try!`, `as!`, and implicitly-unwrapped `var x: T!` outside @IBOutlet-style two-phase init.
- Don't use `Optional` to encode "not loaded yet / failed / empty" as one flat `nil` — that's an enum (`enum Loadable<T> { case idle, loading, loaded(T), failed(Error) }`, per rules/02 state modeling).

### 7.7 Errors: `throws` untyped by default; typed where the boundary is closed

- Errors are typed Swift `enum`s conforming to `Error` (with associated values for context), thrown with `throw`/`throws` — not `NSError` codes, not sentinel returns, not `fatalError` for recoverable conditions.
- **Typed throws** (`throws(ParseError)`) is implemented since Swift 6.0 (SE-0413, verified: [proposal status](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0413-typed-throws.md)) — and the proposal itself says plain `throws` "remains the better default error-handling mechanism for most Swift code." Use typed throws where the proposal recommends: same-module/package code where the error set is closed, generic code passing through a caller's error type (`rethrows` replacement), and embedded/no-existential environments. Do **not** type a public API's throws to today's single error enum — you've frozen your error surface into the ABI.

```swift
// Good typed-throws fit: closed, internal, exhaustive at the catch site
enum FrameError: Error { case truncated(needed: Int), badMagic(UInt32) }
func parseFrame(_ s: inout Span<UInt8>) throws(FrameError) -> Frame { ... }

// Wrong fit: public API frozen to today's one failure mode
public func loadConfig() throws(FileError) -> Config { ... }  // network/keychain sources later = source break
```
- `try?` silently discards the error. Fine for genuinely optional lookups; a finding on operations whose failure someone must observe (writes, sync, payments) — at minimum log before dropping. Audit grep: `try?` on non-read paths.
- Every `catch` either handles meaningfully, adds context and rethrows, or routes to the observability layer. `catch { }` (swallow-all) is the Swift equivalent of `except: pass` — MEDIUM by default.

## Memory: ARC & retain cycles

### 7.8 Closures capturing `self` are the leak factory

- ARC frees objects when the last strong reference drops; **reference cycles never drop**. The canonical cycle: an object stores a closure that captures `self` strongly. Escaping closures stored in properties, handlers, observers, and long-lived `Task`s all qualify.

```swift
// BAD — self → task → closure → self: VM leaks until the task ends (maybe never)
final class Poller {
    var task: Task<Void, Never>?
    func start() {
        task = Task { while true { await self.tick(); try? await Task.sleep(for: .seconds(5)) } }
    }
}
// GOOD — weak capture + early exit; cancel in deinit-adjacent teardown
func start() {
    task = Task { [weak self] in
        while !Task.isCancelled {
            guard let self else { return }
            await self.tick()
            try? await Task.sleep(for: .seconds(5))
        }
    }
}
```

- **`weak` vs `unowned`**: `weak` becomes `nil` when the target deallocates (safe, requires unwrap); `unowned` crashes if touched after deallocation. Use `unowned` only when lifetime containment is *structural* (the closure cannot outlive the target) — when in doubt, `weak`. `unowned` chosen "because it's faster" is a finding.
- After `[weak self]`, the `guard let self else { return }` line decides semantics: with it, the work completes atomically while self lives; without it, each `self?.` call silently no-ops mid-work. Choose deliberately for multi-step operations.
- Standard cycle suspects to audit: delegates declared without `weak`; `NotificationCenter`/KVO observer tokens never removed; timers (`Timer.scheduledTimer` retains its target — invalidate it); Combine `AnyCancellable`s capturing self strongly while stored on self; long-lived `Task`s as above.
- Verification is empirical, not by inspection: memory-graph debugger / Instruments Leaks on device (rules/05), plus `deinit`-fires assertions in tests for controller-like objects. On Linux/server, track RSS per request under load — same ARC, same cycles, no memory-graph UI.

## Unsafe interop

### 7.9 Unsafe pointers: the compiler stops checking exactly where you type `Unsafe`

- **Pointers must not escape their scope.** `withUnsafePointer(to:)`, `withUnsafeBytes`, and friends hand you a pointer valid *only inside the closure*; returning or storing it is undefined behavior that works until it doesn't. Same trap in one token: passing `&array` or a `String` to a C function creates a pointer valid **only for that call** — capturing it C-side is a dangling pointer.
- `UnsafeBufferPointer` subscripts are **not bounds-checked in release builds**. Every index is your proof obligation. Prefer **`Span`** (Swift 6.2+, verified: [swift.org/blog/swift-6.2-released/](https://www.swift.org/blog/swift-6.2-released/)) — safe, bounds-checked, non-escapable access to contiguous memory at zero overhead — and **`InlineArray`** (`[40 of UInt8]`) for fixed-size inline storage without heap allocation. New code reaching for `UnsafeBufferPointer` where `Span` suffices is a finding.
- Swift 6.2 also added **opt-in strict memory safety** which flags every unsafe construct for review — turn it on for parser/codec/crypto modules that handle attacker-controlled bytes (this is the trust-boundary code where UB becomes exploitable, per rules/04's threat model).
- C interop pitfalls: ownership across the boundary is a contract, not inferred — document who frees (`UnsafeMutablePointer.deallocate` vs C-side `free`); un-annotated C headers import pointers as implicitly-unwrapped — add nullability annotations rather than sprinkling `!`; `unsafeBitCast` and `assumingMemoryBound(to:)` assert type facts the compiler can't see and each needs a comment proving the layout claim. Swift 6.3's `@c` attribute (verified: [swift.org/blog/swift-6.3-released/](https://www.swift.org/blog/swift-6.3-released/)) exports Swift functions/enums directly to C — prefer it over hand-maintained shim headers.
- Audit grep: `Unsafe`, `unsafeBitCast`, `assumingMemoryBound`, `unsafeDowncast`, `withMemoryRebound` — the list of hits *is* the manual-review surface; it should be short and concentrated in a few audited files, not smeared across the app.

## Supply chain: Swift Package Manager

### 7.10 Pin, checksum, and treat macros as build-time code execution

- **Commit `Package.resolved`** (and the Xcode-embedded copy for app projects). CI must build against the committed resolution, not silently re-resolve — resolve with the equivalent of "fail if resolved file is out of date" so a hijacked upstream tag can't slide in. Version rules: semver ranges (`from:`) for libraries; **no `branch:`/`revision:` dependencies in anything that ships** — they are unpinned by definition.
- **Remote `binaryTarget`s require a SHA-256 checksum** in the manifest (`swift package compute-checksum` produces it); SwiftPM refuses mismatches. The checksum authenticates the artifact you first vetted — it does not make an unauditable binary safe. Keep an inventory of binary dependencies (they also carry the rules/04 SDK-privacy obligations on iOS).

```swift
// Package.swift — pinned range, checksummed binary; no branch:/revision: in shipping code
dependencies: [
    .package(url: "https://github.com/example/parser.git", from: "2.4.0"),   // resolved exactly in Package.resolved
    // BAD in a release product: .package(url: "...", branch: "main")
],
targets: [
    .binaryTarget(
        name: "AnalyticsSDK",
        url: "https://cdn.example.com/AnalyticsSDK-3.1.0.xcframework.zip",
        checksum: "6d988a1a27418674b4d7c31732f6d60e60734ceb11a0ce9b54d1871918d9c194"
    ),
]
```
- **Registry-based dependencies** get real security machinery (verified: [SwiftPM PackageRegistryUsage.md](https://github.com/swiftlang/swift-package-manager/blob/main/Documentation/PackageRegistry/PackageRegistryUsage.md)): package **signing** with publisher **TOFU** (signer must stay consistent across versions; `--resolver-signing-entity-checking strict`), **checksum TOFU** persisted under `~/.swiftpm/security/fingerprints/` (`--resolver-fingerprint-checking` defaults to `strict`), and per-registry policy in `registries.json` (`signing.onUnsigned: error|prompt|warn|silentAllow`). If you consume from a registry, set `onUnsigned` and signing-entity checking to the strict end in CI.
- **Macros and build plugins execute code at build time.** A malicious macro dependency owns your build machine and your CI credentials. Review macro/plugin dependencies at the same bar as CI config changes; Swift 6.3's prebuilt swift-syntax also removes the historic build-time tax that pushed teams to fork or vendor macros.
- Dependency hygiene is the same discipline as any ecosystem: fewer deps, review the diff on updates, and a scanner/audit step in CI. SwiftPM has no built-in vulnerability audit command — wire an external checker or at minimum subscribe to advisories for your dependency list.

## Testing

### 7.11 Swift Testing for new tests; XCTest where it still owns the ground

- **Swift Testing** ships in Swift 6 toolchains and Xcode 16+ — no package dependency — and runs **side-by-side with XCTest in the same target**, so adoption is incremental, not a rewrite (verified: [swift-testing README](https://github.com/swiftlang/swift-testing)). It is cross-platform (Apple platforms, Linux, Windows; Wasm/Android experimental), so server-side Swift uses the same framework.
- Default for new unit tests: `@Test` functions with `#expect`/`#require`, parameterized tests (`@Test(arguments:)`) instead of copy-pasted cases, suites as structs (fresh instance per test — instance state instead of `setUp` mutation), tags and traits for organization. `#expect` records-and-continues; `#require` aborts the test — use `#require` for preconditions whose failure makes the rest noise.

```swift
@Suite struct FrameParserTests {
    @Test(arguments: [
        ("empty", Data(), FrameError.truncated(needed: 8)),
        ("badMagic", Data([0xde, 0xad, 0xbe, 0xef]), FrameError.badMagic(0xdeadbeef)),
    ])
    func rejectsMalformedInput(_ name: String, _ bytes: Data, _ expected: FrameError) throws {
        #expect(throws: expected) { try FrameParser().parse(bytes) }
    }

    @Test func roundTrips() throws {
        let frame = Frame.fixture()
        let parsed = try #require(try? FrameParser().parse(frame.encoded))  // abort if precondition fails
        #expect(parsed == frame)                                            // record-and-continue
    }
}
```
- Async is native (`@Test func x() async throws`); callback APIs bridge via `confirmation()`. Recent additions, verified against release posts: **exit tests** (assert a process terminates — finally testable `precondition` paths) and **attachments** in 6.2; warning-severity issues, `Test.cancel()`, and image attachments in 6.3 (ST-0012–0017, ST-0020).
- **XCTest is not dead**: UI automation (XCUITest) and performance measurement (`measure`) have no Swift Testing equivalent as of mid-2026 — keep those suites in XCTest and re-verify before planning any "full migration" (fast-moving; check current Xcode release notes).
- Framework choice doesn't change test *strategy*: behavior-first, deterministic, real dependencies where cheap — sota-testing owns that layer; rules/06 owns the mobile CI pyramid.

## Swift beyond the app

### 7.12 One language, several deployment realities

- Everything above applies unchanged to **server-side Swift** (e.g. Vapor, Hummingbird — both on SwiftNIO), CLIs (swift-argument-parser), and embedded targets. Swift officially supports Linux, Windows, WebAssembly (since 6.2), and — new in 6.3 — a first official **Android SDK** (verified: [swift.org/blog/swift-6.3-released/](https://www.swift.org/blog/swift-6.3-released/)).
- Server specifics worth flagging in audit: concurrency pressure is *higher* (thousands of concurrent requests make 7.1–7.3 violations statistical certainties, not rare crashes); blocking the cooperative pool stalls request handling for everyone (7.3); NIO `EventLoopFuture` code bridges to async/await at the edges — new logic should be async/await-native. Don't assume Darwin-only Foundation behavior on Linux; prefer the portable `FoundationEssentials`-level APIs and run CI on the deployment OS.
- Cross-compilation and the static Linux SDK make single-binary deployment normal — which also means containerized Swift services follow the ordinary backend rules (sota-sandboxing, sota-observability), not mobile ones. Use this file for the language; route platform concerns to the right skill.

## Audit checklist

- [ ] All first-party modules build in Swift 6 language mode (or have a dated migration plan); no `-strict-concurrency=minimal`; UI modules use default main-actor isolation rather than blanket `@MainActor` annotations.
- [ ] Every `@unchecked Sendable`, `nonisolated(unsafe)`, and `@preconcurrency` has an adjacent comment naming the synchronization invariant; none sits on a class with public mutable state.
- [ ] Actor methods re-establish invariants after each `await` (reentrancy reviewed); no read-await-write on the same actor state with a stale local.
- [ ] Unstructured `Task { }` handles are owned and cancelled; `Task.detached` is justified per use; long loops/retries check cancellation; no `DispatchSemaphore.wait`/sync I/O bridging inside async contexts; continuations resume exactly once on all paths.
- [ ] `AsyncStream` bridges set an explicit buffering policy (no unbounded default between fast producer and slow consumer); no stream is consumed by two `for await` loops.
- [ ] Types default to `struct`/`let`; classes are `final` or deliberately designed for subclassing; shared mutable state crossing concurrency domains lives in actors; unique resources (descriptors, connections) use `~Copyable` or a single-owner wrapper rather than copyable handles.
- [ ] Hot paths prefer generics/`some` over `any` existentials; owned-enum switches are exhaustive without `default` (`@unknown default` only on non-frozen external enums).
- [ ] Grep clean (or comment-justified): force unwraps `!`, `try!`, `as!`, IUO properties, `try?` on write/sync/payment paths, empty `catch {}` blocks.
- [ ] Public API errors use plain `throws`; typed `throws(E)` appears only in closed same-module/package boundaries, generic pass-through, or embedded code.
- [ ] Closure/`Task`/timer/observer/Combine captures reviewed for cycles; delegates are `weak`; `unowned` only with structurally bounded lifetime; leak checks are empirical (memory graph/Instruments, or RSS-under-load on server) and `deinit` fires in tests for controller-like objects.
- [ ] `Unsafe*`/`unsafeBitCast`/`assumingMemoryBound` hits are few, concentrated, and comment-justified; no pointer escapes its `with*` closure or C call; attacker-input parsing modules use `Span`/`InlineArray` (or enable strict memory safety) instead of raw buffer pointers.
- [ ] `Package.resolved` committed and enforced in CI (build fails on drift); no `branch:`/`revision:` dependencies in release products; remote binary targets carry checksums and appear in the SDK/binary inventory.
- [ ] Registry consumers set fingerprint and signing-entity checking to `strict` and `signing.onUnsigned` to `error`/`prompt` in CI; macro and build-plugin dependencies are reviewed at CI-config rigor.
- [ ] New unit tests use Swift Testing (`#expect`/`#require`, parameterized over copy-paste); UI-automation and performance suites remain on XCTest knowingly, not accidentally.
- [ ] Server-side Swift services run CI on the deployment OS (e.g. Linux), avoid Darwin-only Foundation assumptions, and bridge NIO futures to async/await at the edges only.
