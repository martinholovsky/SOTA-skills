# 04 — Memory, resources and unsafe code

ARC, ownership of resources, and the places the compiler stops checking. Moved from the
former Swift-language file in `sota-mobile` (noncopyable types, ARC, unsafe interop) on
2026-10-07, plus strict memory safety.

## 1. Retain cycles: closures capturing `self`

- ARC frees an object when its last strong reference drops; **cycles never drop**. The canonical
  cycle: `self` stores a closure (handler, observer, long-lived `Task`) that captures `self`.

```swift
// BAD — self → task → closure → self
task = Task { while true { await self.tick(); try? await Task.sleep(for: .seconds(5)) } }
// GOOD
task = Task { [weak self] in
    while !Task.isCancelled {
        guard let self else { return }
        await self.tick()
        try? await Task.sleep(for: .seconds(5))
    }
}
```

- `weak` becomes `nil` when the target goes; `unowned` crashes if touched after deallocation —
  the Swift book: *"ARC never sets an unowned reference's value to `nil`."* Use `unowned` only
  when the closure structurally cannot outlive its target; `unowned(unsafe)` turns the crash into
  undefined behaviour and is an escape hatch (rules/03 §2).
- Cycle suspects: delegates not declared `weak`, notification/KVO tokens never removed,
  `Timer` retaining its target, stored cancellables capturing `self`.
- Verify empirically: a `deinit`-fires assertion in tests for controller-like objects; on a
  server, RSS per request under load (rules/07).

## 2. Resource lifecycle and ownership

- Release resources deterministically with `defer` right after acquisition:
  `let h = try FileHandle(forReadingFrom: url); defer { try? h.close() }`. A file descriptor,
  socket or database connection released "when ARC gets to it" is a leak under load.
- **Noncopyable types** (`~Copyable`, SE-0390, Swift 5.9) make unique ownership a compile-time
  fact — two owners of a descriptor become a compile error instead of a double close. Pair with
  `borrowing`/`consuming` parameters; `consuming func close()` ends the caller's access.
- Connection pools and NIO channels have explicit shutdown (`try await client.shutdown()`);
  skipping it leaks threads and file descriptors in tests and on reload.

## 3. Unsafe pointers: the checking stops where you type `Unsafe`

- Pointers from `withUnsafePointer(to:)`, `withUnsafeBytes` and passing `&array` to C are valid
  **only inside that closure or call**; storing or returning them is undefined behaviour.
- `UnsafeBufferPointer` subscripts are not bounds-checked in release builds. Prefer **`Span`**
  (Swift 6.2) — bounds-checked, non-escapable, zero overhead — and `InlineArray` for fixed-size
  inline storage.
- `unsafeBitCast`, `assumingMemoryBound(to:)`, `withMemoryRebound`, `Unmanaged` assert facts the
  compiler cannot check; each needs a comment proving the layout or lifetime claim.
- C interop: document who frees (`deallocate` vs C `free`); add nullability annotations to C
  headers rather than sprinkling `!`.

## 4. Strict memory safety (opt-in, Swift 6.2)

- SE-0458: enable with `-strict-memory-safety`, or in SwiftPM
  `swiftSettings: [.strictMemorySafety()]`; diagnostics land in the `StrictMemorySafety` group,
  and each unsafe use must be acknowledged with an `unsafe` expression or `@unsafe`. The
  proposal is explicit about its limits: *"strict safety checking does not by itself make the code
  more memory-safe… making it easier to audit for unsafe behavior."*
- Turn it on for modules that parse attacker-controlled bytes (codecs, protocol parsers,
  crypto glue): it turns the unsafe surface into a reviewable list.

## Audit checklist

- [ ] Escaping closures and long-lived `Task`s stored by `self` capture `[weak self]`; delegates are `weak`; `unowned`/`[unowned` (grep) only with structurally bounded lifetime; no `unowned(unsafe)` without justification.
- [ ] Resource lifecycle: every file handle, socket, connection pool and client is released on all paths — a `defer ` block right after acquisition, or explicit shutdown; unique resources use `~Copyable` or a single-owner wrapper.
- [ ] Unsafe surface is small, concentrated and comment-justified — grep `Unsafe(Mutable)?(Raw)?(Buffer)?Pointer|unsafeBitCast|assumingMemoryBound|withMemoryRebound|Unmanaged|withUnsafe`; no pointer escapes its closure or C call.
- [ ] Modules parsing untrusted bytes use `Span`/`InlineArray`, or enable `.strictMemorySafety()` (SE-0458) and acknowledge each `unsafe` use.
- [ ] Leak checks are empirical: `deinit`-fires tests for controller-like objects, RSS-under-load for servers.
