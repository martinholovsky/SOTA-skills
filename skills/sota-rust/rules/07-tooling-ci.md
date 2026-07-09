# 07 — Tooling, CI & Crate Hygiene

A SOTA Rust repo is recognizable from its CI config alone: lints are deny,
tests run under nextest, MSRV is tested not guessed, features are additive,
and docs build clean. This file defines that baseline.

## 1. Clippy — policy, not vibes

Configure lints **in Cargo.toml** (`[lints]`, inherited workspace-wide), not
scattered `#![allow]`s:

```toml
# workspace Cargo.toml
[workspace.lints.rust]
unsafe_code = "warn"               # forbid in crates that can (rules/03)
missing_docs = "warn"              # libraries: consider deny
unused_must_use = "deny"

[workspace.lints.clippy]
all = { level = "warn", priority = -1 }
pedantic = { level = "warn", priority = -1 }
# triaged pedantic opt-outs — each with a reason, reviewed yearly:
module_name_repetitions = "allow"  # naming convention conflicts
must_use_candidate = "allow"       # too noisy for app crates
# hard floors:
unwrap_used = "deny"               # production crates (rules/02)
dbg_macro = "deny"
todo = "deny"
undocumented_unsafe_blocks = "deny"
await_holding_lock = "deny"

# member crates: [lints] workspace = true
```

- **Pedantic triage**, not pedantic-blanket: enable the group, then `allow`
  specific lints with a comment — this catches new pedantic lints on toolchain
  updates instead of opting out of the future.
- **Deny-warnings in CI only**: `cargo clippy --all-targets --all-features --
  -D warnings` in CI; locally keep warn so WIP compiles. For build warnings,
  Cargo's `build.warnings = "allow"/"warn"/"deny"` config (stable since Rust
  1.97) is the first-class knob — set `CARGO_BUILD_WARNINGS=deny` in the CI
  environment, not in committed config, so local builds stay on warn.
  Hardcoding `#![deny(warnings)]` in source breaks builds on every new rustc
  lint — don't.
- Per-site `#[allow(clippy::xyz, reason = "...")]` (lint reasons are stable)
  over module-level allows; an allow without a reason is a finding.
- Run clippy on the same pinned toolchain as the build (lint sets drift across
  versions).

## 2. rustfmt — zero-config by default

- `cargo fmt --check` in CI. Default style; a `rustfmt.toml` should contain
  only deliberate deviations (e.g. `imports_granularity = "Crate"`,
  `group_imports = "StdExternalCrate"` — nightly-only options mean fmt runs
  on nightly toolchain in CI if used).
- Never hand-format against rustfmt; never argue style in review — that's the
  tool's job.

## 3. Tests & cargo-nextest

- `cargo nextest run` over `cargo test`: process-per-test isolation (one
  test's panic/env pollution can't poison others), better parallelism, flaky
  retries with detection (`--retries N` + reporting), per-test timeouts
  (`slow-timeout` + `terminate-after` — hangs fail instead of stalling CI),
  JUnit output. Note: nextest doesn't run doctests — keep a separate
  `cargo test --doc` step.
- Test taxonomy: unit tests in-module (`#[cfg(test)]`), integration tests in
  `tests/` (compile as separate crates — each file is a binary; group to keep
  link time sane), doctests on every public API example (they're the only
  examples guaranteed to compile).
- Property tests (`proptest`) for parsers/serializers/invariant-heavy code;
  snapshot tests (`insta`) for rendered output; `loom` for atomics (rules/03);
  fuzz for untrusted-input parsers (rules/05).
- Coverage: `cargo llvm-cov nextest` — track trend, don't worship the number.

## 4. MSRV policy

- Declare it: `rust-version = "1.85"` in `[package]`/`[workspace.package]` —
  cargo refuses to build on older toolchains with a clear error instead of
  cryptic syntax failures.
- **Test it**: a CI job building with the pinned MSRV toolchain
  (`cargo +1.85 check --all-features`); `cargo msrv verify` / `cargo msrv find`
  to maintain. An untested MSRV claim is false within two dependency bumps —
  note deps' MSRV bumps in *minor* versions can break you; this is what the
  MSRV-aware resolver (Rust 1.84+, `resolver.incompatible-rust-versions =
  "fallback"`) mitigates.
- Policy in README/CONTRIBUTING: which versions you support and whether an
  MSRV bump is a semver-minor (common convention) — pick one and say it.
- Applications: pin the toolchain exactly with `rust-toolchain.toml`
  (reproducible builds, same clippy everywhere). Libraries: MSRV floor +
  stable-latest CI matrix.

## 5. Feature flag hygiene

Features must be **additive**: enabling a feature may only add API/behavior,
never remove or change it. Cargo unifies features across the graph — if crate
A needs `foo` without feature X and crate B enables X, A gets X too; mutually
exclusive features break the ecosystem.

```toml
[features]
default = ["std"]
std = []
serde = ["dep:serde", "uuid?/serde"]   # dep: = no implicit feature for optional deps
                                        # ?/ = enable serde on uuid only if uuid is on
full = ["serde", "metrics"]            # convenience aggregate, still additive
```

- `dep:` syntax for optional dependencies (no accidental public
  `features = ["serde"]` exposure of dep names); `pkg?/feat` for weak
  (conditional) feature forwarding.
- No `no-std`-style **negative features** (`no_std = []` that removes things);
  model it as positive `std` in `default`, with `default-features = false`
  consumers opting in.
- **Test the matrix**: `cargo hack check --feature-powerset --depth 2` (or at
  minimum: `--no-default-features`, default, `--all-features`) in CI — feature
  combinations nobody compiles are broken combinations.
- Don't gate public API breaking-ly (a feature that changes a type's layout or
  a function's signature = non-additive = ecosystem breakage).
- Keep default features lean; heavyweight integrations (TLS stacks, runtimes)
  always optional and documented.
- cfg dispatch: prefer built-in `cfg_select!` (stable since Rust 1.95,
  compile-time match on cfgs) over adding the `cfg-if` dependency in new code.

## 6. Documentation discipline (docs.rs)

- Every public item documented; `#![warn(missing_docs)]` on libraries.
  First line = one-sentence summary (it's the item's listing line); then
  details, then `# Examples` (doctested), `# Errors` (when `Result`),
  `# Panics` (every documented panic path — clippy `missing_panics_doc`),
  `# Safety` (every `unsafe fn` — rules/03).
- Crate root (`lib.rs`) gets the long-form intro: what/why/quickstart —
  `#![doc = include_str!("../README.md")]` keeps README and docs in sync
  (and doctests the README's examples).
- Feature-gated items: build docs.rs with all features and label them:

```toml
[package.metadata.docs.rs]
all-features = true
rustdoc-args = ["--cfg", "docsrs"]
```

```rust
#[cfg_attr(docsrs, doc(cfg(feature = "serde")))]   // renders "Available on feature serde"
```

- Intra-doc links (`[`Vec`]`, `[`crate::Config`]`) over bare URLs — checked at
  build (`rustdoc::broken_intra_doc_links` is deny-worthy).
- CI: `RUSTDOCFLAGS="-D warnings" cargo doc --no-deps --all-features` so doc
  rot fails the build.

## 7. Edition 2024 notes

Current edition as of mid-2026; new code starts here (`edition = "2024"`,
Rust ≥1.85; verify latest stable at releases.rs). The next edition is expected
~2027 on the usual three-year cadence — nothing to migrate toward yet.
Migration: `cargo fix --edition` then review. Key changes that affect rules in
this skill:

- `unsafe_op_in_unsafe_fn`: unsafe fns need explicit inner `unsafe {}` blocks
  (rules/03 §2 — good: per-obligation SAFETY comments).
- `static_mut_refs` denied: references to `static mut` rejected — migrate to
  atomics/`OnceLock`/`Mutex` (rules/03 §3).
- **RPIT lifetime capture**: return-position `impl Trait` now captures *all*
  in-scope lifetimes by default (was: only named ones) — use
  `+ use<'a, T>` precise-capture syntax to opt out; check existing APIs whose
  returned opaques suddenly borrow more.
- `unsafe extern` blocks and unsafe attributes (`#[unsafe(no_mangle)]`) —
  FFI declarations are now explicitly trust-me-marked.
- Temporaries in `if let`/match scrutinees drop sooner (tail-expression
  temporary scope) — re-check `RefCell`/lock guards in conditions.
- `Future`/`IntoFuture` in prelude; `gen` keyword reserved.
- Resolver v3 (MSRV-aware) default with edition 2024 (§4).

## 8. Semver enforcement & release automation

- **`cargo semver-checks`** in CI for published libraries: diffs the public
  API against the last release and fails on undeclared breaking changes
  (removed items, changed signatures, new non-defaulted trait methods, auto
  trait leaks like a type silently becoming `!Send`). Run on release PRs at
  minimum; it catches the breakage humans reliably miss.
- Semver hazards it can't fully see — review manually: blanket impl
  additions, `#[non_exhaustive]` removal (breaking to *remove*), MSRV bumps
  (declare policy, §4), feature removals/renames (features are public API),
  and doc-promised behavior changes.
- **Release automation**: `release-plz` (or `cargo-release`) — version bump
  from conventional commits, changelog generation, tag, `cargo publish` with
  `--locked` from CI with a scoped registry token. Manual `cargo publish`
  from laptops drifts from the audited lockfile and skips the gates.
- Changelog discipline: keep a human-readable CHANGELOG.md (generated or
  curated); "see git log" is not a changelog. Yanked releases
  (`cargo yank`) for published-broken versions — yank doesn't delete, it
  stops *new* resolution.
- Binaries: `cargo dist` (or equivalent) for multi-target release artifacts,
  checksums, and installers from one config; cross-compilation via `cross`
  or toolchain targets exercised in CI *before* the release tag, not during.

## 9. The CI baseline (copy this shape)

```yaml
jobs:
  check:   # fmt + clippy + doc, pinned stable toolchain
    - cargo fmt --check
    - cargo clippy --workspace --all-targets --all-features -- -D warnings
    - RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps --all-features
  test:
    - cargo nextest run --workspace --all-features
    - cargo test --doc --workspace
  msrv:
    - cargo +${MSRV} check --workspace --all-features
  features:
    - cargo hack check --workspace --feature-powerset --depth 2
  supply-chain:        # rules/05
    - cargo deny check
  unsafe-crates-only:  # rules/03
    - cargo +nightly miri test -p crate-with-unsafe
```

Plus scheduled: `cargo audit` (new advisories), fuzz jobs, bench regression
gate (rules/06). Cache with `Swatinem/rust-cache`; pin action SHAs (rules/05).

## Audit checklist

- [ ] `[lints]` table present and workspace-inherited; `rg '#!\[allow' -t rust`
      — blanket crate-level allows without reasons = Low each, pattern = Medium.
- [ ] CI runs clippy with `-D warnings` on `--all-targets --all-features`;
      source does NOT hardcode `#![deny(warnings)]`.
- [ ] `cargo fmt --check` green and in CI; `rustfmt.toml` deviations are
      deliberate and few.
- [ ] Tests: nextest in CI + separate doctest step; per-test timeout
      configured; `rg '#\[ignore\]' -t rust` — ignored tests have reasons.
- [ ] `rust-version` declared AND exercised by a CI job; binaries have
      `rust-toolchain.toml`. `cargo msrv verify` passes.
- [ ] Features: `rg 'no[-_](std|default)' Cargo.toml` style negative features
      = Medium (non-additive); optional deps using `dep:`; feature matrix job
      (`cargo hack`) present; `--no-default-features` builds.
- [ ] Docs: `missing_docs` on lib crates; `# Errors`/`# Panics`/`# Safety`
      sections present (`clippy::missing_errors_doc`, `missing_panics_doc`,
      `missing_safety_doc`); docs.rs metadata for feature-gated crates;
      doc job with `-D warnings`.
- [ ] Edition: new crates on 2024; pre-2024 crates have a migration note or
      reason; post-migration, re-audit `static mut` and RPIT capture changes.
- [ ] Published libraries: `cargo semver-checks` in release CI; publishing
      automated (`release-plz`/`cargo-release`) with `--locked`, not from
      laptops; CHANGELOG maintained.
- [ ] Reproducibility: `Cargo.lock` committed, toolchain pinned, CI action
      SHAs pinned, `rust-cache` keyed correctly (not caching stale clippy).
- [ ] Quick greps: `rg 'dbg!|println!' -t rust -g '!*test*' -g '!*/bin/*'`
      (debug leftovers in libs); `rg 'FIXME|HACK|XXX' -t rust` triaged.
