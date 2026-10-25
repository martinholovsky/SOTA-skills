# 08 — Tooling, CI gates and testing

What makes a Swift build reproducible and its checks enforceable. Testing guidance moved from the
former Swift-language file in [`sota-mobile`](../../sota-mobile/SKILL.md) on 2026-10-07. Test strategy itself is [`sota-testing`](../../sota-testing/SKILL.md).

## 1. Pinned toolchain, reproducible build

- Pin the toolchain: a `.swift-version` file read by **swiftly** (*"share your toolchain
  preference with the rest of your team"*), or a versioned container image (`swift:6.x`, never
  `swift:latest`/`swift:nightly` in CI).
- CI builds what ships: `swift build -c release`, resolving from the committed lockfile with
  `--force-resolved-versions` ([rules/09](09-supply-chain.md)).
- Swift 6.4 made **Swift Build** the default build system in SwiftPM (swift.org 6.4 post) — a
  toolchain bump can change build behaviour; bump deliberately, in its own change.

## 2. Warnings are errors, and every suppression is visible

- CI: `-warnings-as-errors` (`swift build -Xswiftc -warnings-as-errors`), or per diagnostic group
  with `-Werror <group>` / `-Wwarning <group>` (SE-0443, Swift 6.1). In `Package.swift`:
  `.treatAllWarnings(as: .error)` and `.treatWarning("Group", as: .warning)` (SE-0480, Swift 6.2).
- **Every suppression mechanism, including the bulk and config-level ones**, is audited:
  - SwiftLint: `// swiftlint:disable[:next|:this|:previous] rule`, and `disabled_rules:` /
    `excluded:` in `.swiftlint.yml` (a whole rule or directory switched off project-wide);
    `blanket_disable_command` (on by default) flags a disable with no matching enable.
  - Compiler: `-Wwarning <group>` and `.treatWarning(..., as: .warning)` demote a group;
    source-level `@diagnose(Group, as: …)` (SE-0522, Swift 6.4) changes severity at a
    declaration; `@preconcurrency import` silences concurrency diagnostics for a module;
    `@available(*, deprecated)` on your own wrapper hides callers' deprecation warnings.
  - Each needs a reason in a comment; a project-level `disabled_rules` entry is a decision for
    review, not a convenience.
- **Suppressions that expire.** Name the rule, scope it, and give the reason after it:
  `// swiftlint:disable:next force_cast - NSNumber by API contract`. Never `swiftlint:disable all`,
  which the SwiftLint README says disables *"all rules until the linter sees a matching enable
  comment"*. `superfluous_disable_command` (on by default) reports a disable whose rule would not
  have fired, and `blanket_disable_command` (on by default) reports a disable that is neither
  scoped (`:next`, `:this`, `:previous`) nor closed by a matching `enable`. Both default to **warning** severity (SwiftLint rule docs), so
  plain `swiftlint lint` exits 0 on them. Gate with `swiftlint lint --strict` (*"Upgrades
  warnings to serious violations (errors)"*) or `strict: true` in `.swiftlint.yml`.
- **Strict rules versus test code: exempt by path in config.** When a rule the tests may break
  by design trips there (`force_try`, `force_unwrapping` in fixtures), put a nested
  `Tests/.swiftlint.yml` that disables only those rules. The README: a nested config *"applies
  only to files in its directory subtree"*, and nested configs are ignored when `--config` is
  passed. A safety rule in the root `disabled_rules`, switched off for production code because
  the tests failed it, is a finding. In Swift Testing, `try #require(x)` replaces `x!` in tests.

## 3. Static analysis and formatting

- **swift-format** ships in the toolchain since Swift 6 (*"Swift 6 (included with Xcode 16) and
  above include swift-format in the toolchain… `swift format`"*): run `swift format lint
  --strict` in CI with a committed `.swift-format`.
- **SwiftLint** with a committed `.swiftlint.yml`. Several safety rules are **opt-in** and off by
  default — `force_unwrapping`, `implicitly_unwrapped_optional`, `unowned_variable_capture` —
  enable them; `force_try` is on by default.
- **CodeQL** has built-in Swift queries; run them in CI where GitHub code scanning is available.

## 4. Tests

- **Swift Testing** for new tests: `@Test` with `#expect`/`#require`, `@Test(arguments:)` instead
  of copy-pasted cases, suites as structs (fresh state per test). It ships in Swift 6 toolchains,
  runs beside XCTest in one target, and is cross-platform.
- XCTest still owns UI automation (XCUITest) and `measure`-style performance tests.
- **Determinism**: Swift Testing runs tests *"in parallel with respect to each other"* by
  default. `.serialized` on a `@Test`/`@Suite` opts out and usually marks shared global state — a
  test-suite health smell to fix, not a flake to hide. No `Task.sleep`/`sleep` to wait for
  async work: await it, or use `confirmation()`.
- Sanitizers in CI, per swift.org's server guide: `swift test --sanitize=thread` and
  `--sanitize=address` on the deployment OS. **Required for any target that uses the escape
  hatch** (`Unsafe*Pointer`, `unsafeBitCast`, `Unmanaged`, C interop): that code runs its tests
  under ASan/TSan (`swift build --sanitize=`, `swiftc -sanitize=`), and any
  `.strictMemorySafety()` target builds with its warnings gated ([rules/04](04-memory-and-unsafe.md) §4).
- **Fuzz the parsers** with Swift's built-in libFuzzer integration: `-sanitize=fuzzer` (plus
  `-parse-as-library`), or `swift build --sanitize=fuzzer`, on a **swift.org Linux toolchain** —
  Apple's Xcode toolchain rejects the option (measured: `unsupported option '-sanitize=fuzzer'`
  on macOS, Swift 6.3.2). SwiftCheck is unmaintained since 2021; `@Test(arguments:)` is
  parameterised, not property-based. A fuzz target that returns early on invalid input must
  also prove reach: [`sota-testing` rules/06](../../sota-testing/rules/06-property-fuzzing-mutation.md) §6.6.

## Audit checklist

- [ ] Build reproducibility & CI gates: toolchain pinned (`.swift-version` or a versioned image — grep `swift:latest|swift:nightly`); CI builds `-c release` with `--force-resolved-versions`.
- [ ] Static analysis / linter configuration: CI runs the compiler with `-warnings-as-errors` (or `.treatAllWarnings(as: .error)`), `swift format lint --strict` and SwiftLint with `force_unwrapping`, `implicitly_unwrapped_optional` and `unowned_variable_capture` enabled.
- [ ] Suppressions that expire (§2) (LOW, MEDIUM on a security rule): `grep -rnE 'swiftlint:disable' --include='*.swift' . | grep -vE 'swiftlint:disable(:next|:this|:previous)?[[:space:]]+[a-z_ ]+[[:space:]]-[[:space:]]+[^[:space:]]'` (no ` - reason`) ; `grep -rnE 'swiftlint:disable(:next|:this|:previous)?[[:space:]]+all([^a-z_]|$)' --include='*.swift' .` ; CI runs `swiftlint lint --strict` or the config sets `strict: true` (grep `swiftlint[^|]*--strict` in CI files) — without it the superfluous and blanket disable reports are warnings at exit 0.
- [ ] Test-code exemptions by path (§2) (MEDIUM): `awk '/^[a-z_]+:/{s=($0 ~ /^disabled_rules:/)} s && /force_(try|unwrapping|cast)/' .swiftlint.yml` — a safety rule disabled for the whole project; scope it in `Tests/.swiftlint.yml` instead.
- [ ] Escape hatch without its runtime checker (§4) (HIGH): `grep -rlE 'Unsafe(Mutable)?(Raw)?(Buffer)?Pointer|unsafeBitCast' --include='*.swift' .` ; then `grep -rnE -- '-?-sanitize[= ](address|thread)' .github/workflows/` — files with unsafe code and no sanitizer job is the finding.
- [ ] Suppressing a linter / type check: every `swiftlint:disable`, `.swiftlint.yml` `disabled_rules`/`excluded` entry, `-Wwarning`/`.treatWarning(..., as: .warning)`, `@diagnose(` and `@preconcurrency import` (grep) carries a reason; none hides a security rule.
- [ ] Test suite health & determinism: tests run in parallel without `.serialized` except with a stated reason; no `sleep`/`Task.sleep` waits in tests; CI runs the suite under `--sanitize=thread` and `--sanitize=address`.
- [ ] Version floor / EOL awareness: the minimum supported Swift version is declared (`swift-tools-version`, `swiftLanguageModes:` language version) and documented; swift.org publishes no end of life policy, so the project states which toolchains it supports and bumps deliberately.
- [ ] New unit tests use Swift Testing; XCTest is kept knowingly for UI automation and `measure` performance tests.
- [ ] Property-based / fuzz testing of parsers (LOW, MEDIUM for a parser of untrusted bytes): `grep -rnE 'sanitize[= ]fuzzer|LLVMFuzzerTestOneInput|import SwiftCheck' --include='*.swift' --include='*.yml' --include='*.yaml' --include='Package.swift' .` — none means nothing is fuzzed; a fuzz job must run on a swift.org Linux toolchain, and `import SwiftCheck` is an unmaintained dependency.
