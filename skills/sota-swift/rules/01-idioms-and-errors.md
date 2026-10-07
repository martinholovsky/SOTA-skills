# 01 — Idioms, optionals, errors, numbers and time

The baseline every Swift file is held to. Moved from the former Swift-language file in `sota-mobile`
(its value-type, optionals and errors sections) on 2026-10-07, when Swift became its own skill, and extended with numeric and time rules.

## 1. Value types by default; classes only for identity

- Default to `struct` + `let`. Value semantics make code trivially `Sendable`, testable and free
  of mutation at a distance. Reach for `class` only when identity or shared mutable state is the
  point — and if that state crosses concurrency domains it is an `actor` (rules/03), not a class.
- Standard collections are **copy-on-write**: assignment is O(1) until mutation, so passing large
  collections is cheap; mutating a shared instance copies it. Custom large value types wrapping
  a reference buffer implement COW with `isKnownUniquelyReferenced(&storage)`.
- Mark classes `final` unless subclassing is a designed extension point.
- Model state with **enums with associated values**, and switch exhaustively **without
  `default`** on enums you own — a new case then fails to compile at every site that must care.
  `@unknown default` is for non-frozen enums from other modules.

## 2. Optionals: unwrap early, crash never by accident

- `guard let` at the top of a function, then straight-line code. Nested `if let` pyramids and
  long `a?.b?.c` chains signal a missing early exit or a type that should not be optional.

```swift
// BAD — pyramid
if let user = session.user { if let email = user.email { register(email) } }
// GOOD
guard let user = session.user, let email = user.email else { return .missingProfileData }
register(email)
```

- **`!`, `try!` and `as!` are assertions, not error handling.** The Swift book: *"Force unwrapping
  a `nil` value triggers a runtime error"*; `try!` likewise — *"If an error actually is thrown,
  you'll get a runtime error."* On anything derived from input each is a remote crash. A
  legitimate use (a bundled resource) carries a comment stating the invariant, or becomes
  `preconditionFailure("why")`.
- Implicitly unwrapped optionals (`var x: T!`) only for two-phase initialisation.
- No in-band sentinels: absence is `Optional`, never `-1`, `0` or `""` (`sota-architecture`
  rules/02 §8a). "Not loaded / failed / empty" is an enum, not one flat `nil`.

## 3. Errors: untyped `throws` by default

- Errors are `enum`s conforming to `Error` with associated values for context, thrown with
  `throw` — not `NSError` codes, not sentinel returns, not `fatalError` for recoverable failure.
- **Typed throws** (`throws(ParseError)`, Swift 6.0, SE-0413): the proposal itself says
  *"untyped `throws` is better for most scenarios"*. Use it for closed, same-module boundaries,
  generic pass-through and embedded code; never type a public API's throws to today's one error
  enum (rules/02).
- `try?` discards the error: fine for optional lookups, a finding on writes, sync and payments.
- Every `catch` handles, adds context and rethrows, or reports. `catch { }` is swallow-all.
- `fatalError`/`precondition` are for programmer errors. Note the Swift book: *"If you compile
  in unchecked mode (`-Ounchecked`), preconditions aren't checked"* — so a `precondition` is not
  a security check, and `-Ounchecked` in a release config removes them all.

## 4. Integers and money

- Arithmetic **traps on overflow** (the Swift book: *"Overflow behavior is trapped and reported
  as an error"*): a crash, not wraparound. `&+`, `&-`, `&*` wrap silently — audit each one on a
  size, index or length computed from input, where wraparound becomes an under-allocation.
- **Money is `Decimal` built from a string, or integer minor units — never `Double`.** Trap
  verified in swift-foundation: `let d: Decimal = 0.1` goes through
  `init(floatLiteral value: Double)`, so the literal is a `Double` first and the binary error
  is already in it. Use `Decimal(string: "0.1")` or `Decimal(sign:exponent:significand:)`.

## 5. Dates, clocks and time zones

- **Elapsed time and timeouts use a clock, not `Date`**: `ContinuousClock` (does not stop while
  the system sleeps) or `SuspendingClock`, with `Duration` (SE-0329, Swift 5.7). `Date()`
  subtraction moves with wall-clock adjustments.
- `Date` is an instant, *"independent of any calendar or time zone"* (Apple docs). Store and
  transmit instants as UTC / ISO 8601 (`ISO8601FormatStyle`); pass `TimeZone` and `Calendar`
  explicitly — `TimeZone.current` on a server is the host's zone, a deployment accident.

## 6. Strings: graphemes, bytes and decoding

- `String.count` counts **grapheme clusters** (`Character`s), not bytes or UTF-16 units: measured
  on Swift 6.3.2, `"e\u{301}".count` is `1` and its `.utf8.count` is `3`. A byte limit (a
  column width, a header cap, a buffer) is checked on `.utf8.count`; a length shown to a user is
  `.count`. `NSString.length` is UTF-16 units — a third answer.
- `==` is **canonical equivalence**: `"e\u{301}" == "\u{e9}"` is `true` although their UTF-8
  bytes differ. Normalise before a byte-level comparison, hash or signature, never after.
- `String(data:encoding:)` returns `nil` on invalid input (measured: `[0xff,0xfe,0xfd]` as UTF-8);
  handle it — a force-unwrap turns hostile bytes into a crash.

## Audit checklist

- [ ] Encoding, unicode & text (§6): `grep -rnE 'String\(data:[^)]*\)!' --include='*.swift' .` (a force-unwrapped decode crashes on invalid bytes) ; `grep -rnE '\.count[[:space:]]*[<>]=?' --include='*.swift' . | grep -iE 'byte|header|column|limit|max'` (a byte limit checked on grapheme count — it must be `.utf8.count`).

- [ ] Types default to `struct`/`let`; classes are `final` unless designed for subclassing; owned-enum `switch`es are exhaustive without `default`.
- [ ] Absence / null handling: no force unwraps on input-derived optionals — grep `[A-Za-z0-9_)\]]!(\.|\s|\)|$)`, `as!`, `try!`; IUO `T!` only in two-phase init; no in-band sentinel (`-1`, `""`) where an optional or enum belongs.
- [ ] Error handling: public APIs use plain `throws`; no `try?` on write/sync/payment paths; no empty `catch { }`; no `fatalError`/`precondition` standing in for input validation; no `-Ounchecked` in release settings.
- [ ] Wrapping operators (`&+`, `&-`, `&*`) on input-derived sizes and indices are justified; money uses `Decimal(string:)` or integer minor units — grep `: *Decimal *= *[0-9]+\.[0-9]` and `(price|amount|total|balance)\w* *: *(Double|Float)`.
- [ ] Date, time & timezone: elapsed time and timeouts use `ContinuousClock`/`Duration`, not `Date()` subtraction (grep `timeIntervalSince`); instants stored as UTC/ISO 8601; no `TimeZone.current`/`Calendar.current` in server logic that must not depend on the host.
