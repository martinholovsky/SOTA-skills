# 02 — API design: protocols, generics, access control, evolution

How a Swift module or package presents itself to callers. Partly moved from `sota-mobile`
rules/07 §7.5 (2026-10-07). The naming baseline is swift.org's API Design Guidelines:
*"Clarity at the point of use"*.

## 1. Protocols and generics

- Depend on capabilities (`protocol Clock`, `protocol TokenStore`), not concrete types — the
  dependency-injection seam. Do not invent a protocol per type "for testability" when a struct of
  closures or a generic parameter is simpler.
- **`some` over `any`**: `some P` keeps static dispatch and no boxing; `any P` is an existential
  box with dynamic dispatch. Use `any` only where heterogeneity is required. (Cost: rules/07.)
- Generics constrain with the smallest protocol that works; a public generic signature is API
  and changing its constraints is a breaking change.

## 2. Access control is the public API surface

- Default `internal`. `public` is a promise to every caller; keep it minimal and deliberate.
- **`package` access** (SE-0386, Swift 5.9) shares symbols across the modules of one package
  without making them public — use it instead of `public` for cross-module internals.
- `open` only for designed subclassing points; a class made `open` cannot later become `final`
  without breaking subclasses.
- `@_spi`, `@testable import` and `internal`-for-tests are not API; nothing public should depend
  on them.

## 3. Evolving a public API without breaking callers

- **SemVer** for packages (the SSWG asks for it); a removed or retyped `public` symbol is a major
  version.
- Deprecate before removing: `@available(*, deprecated, renamed: "newName")` keeps old callers
  compiling with a fix-it, then remove in the next major.
- **Typed throws on public API freezes the error surface**: `public func load() throws(FileError)`
  cannot later throw a network error without a source break. Public APIs use plain `throws`
  (rules/01 §3).
- **Library evolution** (`-enable-library-evolution`) is only for binary frameworks built and
  shipped separately from their clients — swift.org: *"Library evolution support should only be
  used when a framework is going to be built and updated separately from its clients"*. With it,
  `@frozen` publishes a type's layout forever and `@inlinable` publishes a function's body into
  the client binary: both are permanent commitments, not optimisations to sprinkle.
- Public enums in a library-evolution module are non-frozen by default; clients must handle
  `@unknown default`.
- Declare the language mode per package (`swiftLanguageModes:`) and per target
  (`.swiftLanguageMode(.v5)` only with a dated migration note); `swiftLanguageVersions` is
  deprecated (SE-0441).

## 4. Shape of calls

- Argument labels make call sites read as phrases; omit the first label only when the base name
  already says it. Booleans that change behaviour are enums (`.strict`/`.lenient`), not `Bool`.
- Return values the caller must not ignore are not `@discardableResult`.
- Prefer non-throwing initialisers plus a validating factory over `init` that half-builds state.

## Audit checklist

- [ ] Public API surface & evolution: every `public`/`open` symbol is intended; module boundaries hold — cross-module internals use `package`, not `public`, and no target depends on another's internals through `@testable import` outside tests; `open` only on designed extension points.
- [ ] Removed or retyped public symbols bump the major version; deprecations use `@available(*, deprecated, renamed:)` first.
- [ ] No public function uses typed `throws(E)`; `@frozen`/`@inlinable`/`@usableFromInline` (grep) appear only in a library-evolution binary framework, each justified.
- [ ] Hot or library-facing signatures use `some`/generics; `any` only where heterogeneity is needed.
- [ ] `Package.swift` declares `swiftLanguageModes:` (no deprecated `swiftLanguageVersions`); any target pinned to `.v5` has a dated migration note.
- [ ] Behaviour-switching `Bool` parameters on public APIs are enums; results that must be used are not `@discardableResult`.
