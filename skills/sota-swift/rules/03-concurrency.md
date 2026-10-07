# 03 — Concurrency: data-race safety, isolation, cancellation

Moved from the former Swift-language file in `sota-mobile` on 2026-10-07 and extended. Applies to every target:
a server under load turns a latent race into a statistical certainty.

## 1. Build in Swift 6 language mode; migrate module by module

- Swift 6 mode enforces data-race safety at compile time (the migration guide: *"By default,
  Swift 6 enables full data race safety checking"*): `Sendable` across isolation boundaries,
  actor isolation, region-based analysis. A module still on Swift 5 mode with concurrency
  diagnostics silenced is accumulating latent races.
- Migration is per target (`.swiftLanguageMode(.v6)`); intermediate step: Swift 5 mode with
  `-strict-concurrency=complete`.
- Swift 6.2 "approachable concurrency" made adoption cheaper:
  - **Default isolation** per module (SE-0466): `-default-isolation MainActor` /
    `.defaultIsolation(MainActor.self)`. The proposal: *"If no `-default-isolation` flag is
    specified, the default isolation for the module is `nonisolated`."* Use `MainActor` default
    for UI/app modules; leave libraries and servers `nonisolated`.
  - `NonisolatedNonsendingByDefault` (SE-0461, upcoming feature) runs `nonisolated` async
    functions in the caller's context; `@concurrent` marks the ones that should leave it.

## 2. The escape hatches — audit every one

SE-0458 names these as constructs *"where safety checking can be disabled locally despite that
having wide-ranging consequences"*:

| Construct | What it turns off |
|---|---|
| `nonisolated(unsafe)` | static isolation checking for that declaration (SE-0412: *"will disable static checking of data isolation"*) |
| `@unchecked Sendable` | the compiler's proof a type is safe to share |
| `@preconcurrency` (import or conformance) | concurrency diagnostics for that module/conformance |
| `unowned(unsafe)` | lifetime checking (rules/04) |

None is banned; each needs an adjacent comment naming the synchronisation that makes it safe
("guarded by `lock`"). `@unchecked Sendable` on a class with public mutable `var`s is a finding.
Mutable `static var`/global state is a shared-state hazard the same way.

## 3. Actors: isolation is per suspension, not per method

- `actor` is the tool for shared mutable state; a class plus `DispatchQueue`/`NSLock` in new code
  is legacy style. Actors are **reentrant**: every `await` inside an actor method lets other
  calls interleave — re-establish invariants after each `await`.

```swift
actor AccountCache {
    private var balances: [AccountID: Int] = [:]
    func applyBAD(_ tx: Tx) async throws {          // read, await, write a stale value
        let current = balances[tx.account] ?? 0
        try await ledger.validate(tx)
        balances[tx.account] = current + tx.amount
    }
    func apply(_ tx: Tx) async throws {             // mutate in one synchronous step
        try await ledger.validate(tx)
        balances[tx.account, default: 0] += tx.amount
    }
}
```

- Do not funnel everything through `@MainActor`; on a server there is no UI to protect.
- Fix order for a `Sendable` error: make it a value type → an actor → transfer ownership with a
  `sending` parameter → only then `@unchecked Sendable` with a lock.

## 4. Structured concurrency, cancellation and timeouts

- **Structured first**: `async let` for a fixed set, `withTaskGroup`/`withThrowingTaskGroup` for
  dynamic fan-out — children are bounded by the scope and cancelled together.
- An unstructured `Task { }` needs an owner that stores the handle and cancels it (no
  fire-and-forget task leaks). `Task.detached` drops priority and task-locals; each use needs a
  reason. The Swift book on unstructured tasks: *"you're also completely responsible for their
  correctness."*
- **Cancellation is cooperative** (*"Swift concurrency uses a cooperative cancellation model"*):
  long loops call `try Task.checkCancellation()`; callback resources use
  `withTaskCancellationHandler`.
- **Timeouts**: `withDeadline` (SE-0526) is *accepted, not shipped* as of 2026-10-07. Until it
  ships, race the work against a `Task.sleep(for:)` child in a task group and cancel the loser.
  Every network call, lock wait and external process gets a bound.
- **Never block the cooperative pool**: no `DispatchSemaphore.wait()`, `sleep()` or synchronous
  I/O inside async code — under load it deadlocks the width-limited pool. Bridge callbacks with
  `withCheckedThrowingContinuation`, resumed exactly once on every path.

## 5. Streams and backpressure

- `AsyncStream`'s default buffering is unbounded: a fast producer and slow consumer is a memory
  leak. Choose `.bufferingNewest(n)`/`.bufferingOldest(n)`, or pull-based backpressure when every
  element matters.
- One `AsyncSequence` generally supports one consumer; a second `for await` silently splits
  elements. Fan-out is an explicit layer.
- Bound fan-out: a task group adding a child per input item needs a concurrency limit.

## Audit checklist

- [ ] All first-party targets build in Swift 6 language mode (or carry a dated plan); no `-strict-concurrency=minimal`; UI modules use default `MainActor` isolation, libraries stay `nonisolated`.
- [ ] Data race / shared mutable state: every `nonisolated(unsafe)`, `@unchecked Sendable`, `@preconcurrency` and mutable `static var` (grep `nonisolated\(unsafe\)|@unchecked +Sendable|@preconcurrency|static +var `) has a comment naming its synchronisation; none sits on a class with public mutable state.
- [ ] Actor methods re-establish invariants after each `await`; no read-await-write with a stale local.
- [ ] Unstructured `Task { }` handles are owned and cancelled (no fire-and-forget task leaks); `Task.detached` justified per use (grep `Task\.detached|Task *\{`).
- [ ] Cancellation / timeouts: long loops and retries check cancellation; every network call, wait and subprocess has a timeout bound.
- [ ] No `DispatchSemaphore.wait`, `sleep(` or blocking I/O inside async code (blocking the executor); continuations resume exactly once on every path.
- [ ] `AsyncStream` sets an explicit buffering policy (no unbounded queue between fast producer and slow consumer); task-group fan-out is bounded; no stream has two consumers.
