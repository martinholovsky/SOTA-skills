# 08 — Tooling, CI gates and testing

What makes a Swift build reproducible and its checks enforceable. Testing guidance moved from
`sota-mobile` rules/07 §7.11 on 2026-10-07. Test strategy itself is `sota-testing`.

## 1. Pinned toolchain, reproducible build

- Pin the toolchain: a `.swift-version` file read by **swiftly** (*"share your toolchain
  preference with the rest of your team"*), or a versioned container image (`swift:6.x`, never
  `swift:latest`/`swift:nightly` in CI).
- CI builds what ships: `swift build -c release`, resolving from the committed lockfile with
  `--force-resolved-versions` (rules/09).
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
  `--sanitize=address` on the deployment OS.

## Audit checklist

- [ ] Build reproducibility & CI gates: toolchain pinned (`.swift-version` or a versioned image — grep `swift:latest|swift:nightly`); CI builds `-c release` with `--force-resolved-versions`.
- [ ] Static analysis / linter configuration: CI runs the compiler with `-warnings-as-errors` (or `.treatAllWarnings(as: .error)`), `swift format lint --strict` and SwiftLint with `force_unwrapping`, `implicitly_unwrapped_optional` and `unowned_variable_capture` enabled.
- [ ] Suppressing a linter / type check: every `swiftlint:disable`, `.swiftlint.yml` `disabled_rules`/`excluded` entry, `-Wwarning`/`.treatWarning(..., as: .warning)`, `@diagnose(` and `@preconcurrency import` (grep) carries a reason; none hides a security rule.
- [ ] Test suite health & determinism: tests run in parallel without `.serialized` except with a stated reason; no `sleep`/`Task.sleep` waits in tests; CI runs the suite under `--sanitize=thread` and `--sanitize=address`.
- [ ] Version floor / EOL awareness: the minimum supported Swift version is declared (`swift-tools-version`, `swiftLanguageModes:` language version) and documented; swift.org publishes no end of life policy, so the project states which toolchains it supports and bumps deliberately.
- [ ] New unit tests use Swift Testing; XCTest is kept knowingly for UI automation and `measure` performance tests.
