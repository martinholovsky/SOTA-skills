---
name: sota-rust
description: >-
  State-of-the-art Rust engineering (2026) for writing and auditing Rust code.
  Covers idiomatic ownership and API design, error handling and panic policy,
  unsafe discipline with Miri, async/tokio (cancellation safety, structured
  concurrency, graceful shutdown), security and supply chain (cargo
  audit/deny/vet, integer overflow, serde hardening, zeroize), performance
  (profiling, allocation reduction, release profiles), and tooling/CI (clippy
  policy, nextest, MSRV, feature hygiene, edition 2024). Use when writing new
  Rust code, reviewing or auditing existing Rust, designing crate APIs,
  debugging borrow checker or Send/Sync errors, or hardening Rust services.
  Triggers: Rust, cargo, crate, tokio, unsafe, lifetime, borrow checker,
  clippy, async Rust, Cargo.toml, thiserror, anyhow, serde, Miri, MSRV.
---

# SOTA Rust (2026)

## Purpose

This skill encodes the 2026 state of the art for production Rust: the idioms,
security posture, performance discipline, and CI baseline expected of an
expert Rust codebase. Baseline as of mid-2026: a recent stable Rust toolchain (verify the current
release at blog.rust-lang.org),
edition 2024 (next edition expected ~2027), tokio still 1.x. It serves two modes — **BUILD** (write new code to this
standard) and **AUDIT** (find where existing code falls short, with severity
and evidence). The detailed rules live in `rules/*.md`; load only the files
relevant to the task (see index below). Every rules file ends with an "Audit
checklist" of grep/clippy patterns — use those verbatim in AUDIT mode.

## BUILD mode

When writing or modifying Rust code:

1. **Scope the work, load the rules.** Pick the relevant `rules/` files from
   the index. Touching async code? Load 04. Adding a dependency or parsing
   network input? Load 05. Writing any `unsafe`? Load 03 — no exceptions.
2. **Design types first.** Newtypes for domain primitives, errors per
   subsystem (thiserror for libs, anyhow for apps), ownership tree before
   `Arc<Mutex<_>>`, public API minimal and borrowed (`&str`/`&[T]` params).
   Parse, don't validate: constructors enforce invariants.
3. **Write to the non-negotiables** (bottom of this file) without being asked.
   They are defaults, not suggestions; deviations carry a written
   justification at the site (e.g. `expect` with invariant message,
   `#[allow(lint, reason = "...")]`).
4. **Wire the scaffolding with the code**, not after: lints in `[lints]`,
   `deny.toml` + `cargo deny` in CI for anything deployed, Miri job if unsafe
   exists, nextest, MSRV declared and tested, benches for claimed-hot paths.
   See rules/07 §9 for the CI shape to copy.
5. **Verify before claiming done:** `cargo fmt --check`, `cargo clippy
   --all-targets --all-features -- -D warnings`, `cargo nextest run` +
   `cargo test --doc`, and `cargo doc` warning-free for libraries. If you
   wrote unsafe: `cargo +nightly miri test` over it. If you claimed
   performance: show the benchmark.
6. **Comment intent at decision points** the next reader will question:
   justified clones, cancel-safety of `select!` arms, SAFETY comments,
   channel-capacity choices, poisoning policy.

## AUDIT mode

When reviewing or auditing existing Rust:

1. **Recon first:** `cargo metadata`/workspace layout, `Cargo.toml` profiles
   and features, CI config, `rg 'unsafe' --count-matches`, dependency tree
   (`cargo tree -d`). This decides which rules files to load and where risk
   concentrates (network input? unsafe? async service?).
2. **Run the audit checklists** at the end of each loaded rules file — they
   are ordered grep/clippy hunts with pre-calibrated severities.
3. **Validate every finding**: read the surrounding code; a grep hit is a
   lead, not a finding. Confirm reachability (is the unwrap on an
   attacker-influenced path?) before assigning severity.
4. **Report with the finding format below.** Prefer few, true, prioritized
   findings over volume. Note positive observations where the code is already
   SOTA (prevents "fixes" that regress good decisions).

### Severity conventions

| Severity | Meaning | Examples |
|---|---|---|
| **Critical** | Exploitable now, or UB | reachable UB, unsound safe API, SQLi/path traversal, authn bypass, unwinding across FFI, secrets in logs+repo |
| **High** | Exploitable under realistic conditions, or correctness loss | attacker-reachable panic/OOM (DoS), wrapped arithmetic on untrusted lengths, cancellation data loss, deadlock (`block_on` in async, lock across await), unbounded channels fed by network, missing dep-audit in deployed-service CI |
| **Medium** | Latent defect or eroded defense | missing SAFETY comments, no Miri CI on unsafe crate, swallowed errors (`.ok()`, `filter_map(Result::ok)`) uncommented, untested MSRV, non-additive features, orphaned spawned tasks |
| **Low** | Hygiene, idiom, maintainability | clone-to-satisfy-borrowck, index loops, missing `#[non_exhaustive]`, missing `# Errors` docs, blanket `#[allow]` without reason |

Severity scales with **reachability** (attacker-controlled > user > operator >
build-time) and **blast radius** (process death > request failure > slow).

### Finding format

```
[SEVERITY] short title
  Where: path/to/file.rs:123 (fn name / module)
  What:  the defect, in one or two sentences
  Why:   concrete consequence (exploit path, failure mode, cost)
  Fix:   specific change — code sketch or named pattern from rules/NN
  Effort: trivial | small | medium | large
  Refs:  rules/NN §M; clippy lint or RUSTSEC id if applicable
```

Group findings by severity, Critical first. End with: checklist coverage (which
rules files were applied), what was *not* reviewed, and quick wins (one-line
fixes with outsized value).

## Rules index

| File | Read this when... |
|---|---|
| [rules/01-ownership-and-api-design.md](rules/01-ownership-and-api-design.md) | Designing structs/traits/modules/workspaces; fighting the borrow checker; deciding clone vs borrow vs Rc/Arc; newtype, typestate, builder patterns; sealed traits, coherence; comparison-trait (`Eq`/`Ord`) invariants; exhaustive matching; iterator-chain idioms |
| [rules/02-errors-and-panics.md](rules/02-errors-and-panics.md) | Choosing thiserror vs anyhow/eyre; designing error enums; unwrap/expect policy and invariant messages; context discipline; panic policy for servers, FFI, and `Drop` (no panic in destructors); Option/Result combinator flow |
| [rules/03-unsafe-discipline.md](rules/03-unsafe-discipline.md) | Writing or reviewing ANY `unsafe`; SAFETY comment standards; UB catalog (aliasing, uninit, transmute, FFI lifetimes); Miri/sanitizers/loom in CI; cargo-geiger; soundness review protocol |
| [rules/04-async-tokio.md](rules/04-async-tokio.md) | Anything async: tokio, spawn vs spawn_blocking, Send/Sync bound errors, `select!` and cancellation safety, JoinSet/TaskTracker, channel selection, locks across await, async traits, graceful shutdown |
| [rules/05-security-supply-chain.md](rules/05-security-supply-chain.md) | Network-facing or deployed code; adding dependencies; cargo audit/deny/vet; integer overflow on untrusted input; panic-DoS; zeroize/constant-time for secrets; serde hardening (untagged enums, size limits); service-edge defaults |
| [rules/06-performance.md](rules/06-performance.md) | Performance work or claims: profiling (samply/perf/flamegraph, criterion/divan), allocation reduction (Cow/SmallVec/buffer reuse), accidental clones, iterator fusion, release profile (LTO, codegen-units, panic=abort), PGO |
| [rules/07-tooling-ci.md](rules/07-tooling-ci.md) | Setting up or auditing repo scaffolding: clippy policy and pedantic triage, rustfmt, nextest, MSRV declaration+testing, additive feature flags, docs.rs discipline, edition 2024 migration, CI baseline. **Test *strategy* — suite shape, TDD, doubles, test data, flake policy — lives in `sota-testing`; load it for any build that writes logic. This file owns Rust runner mechanics only.** |

## Top-10 non-negotiables

1. **No `unwrap()`/bare `expect()` on production paths.** Propagate with `?` +
   context; `expect("...")` only with a message proving the invariant. An
   attacker-reachable panic is a DoS. (rules/02)
2. **Every `unsafe` block has a `// SAFETY:` comment** discharging the called
   API's documented preconditions, and lives behind a sound safe abstraction.
   Unsafe code without Miri in CI is unaudited code. (rules/03)
3. **Libraries: thiserror enums with `#[source]` chains. Applications:
   anyhow with `.context()`.** Never `anyhow::Error` in a public lib API;
   never silently swallowed errors. (rules/02)
4. **Never block the async runtime:** no sync I/O, `std::thread::sleep`, or
   sustained CPU inside `async fn`; `spawn_blocking` or a compute pool. No
   `std::sync::MutexGuard` held across `.await`. (rules/04)
5. **Every `select!`/timeout/abort path is cancellation-reviewed:** futures
   dropped at any `.await`; cancel-unsafe ops don't go in `select!` arms;
   invariants spanning awaits get drop guards. Spawned tasks are owned
   (JoinSet/TaskTracker), never orphaned. (rules/04)
6. **Untrusted input gets checked arithmetic, size limits, and depth limits:**
   `checked_*`/`try_into` on lengths (release mode wraps silently), body-size
   caps before parsing, no `#[serde(untagged)]` or uncapped
   `with_capacity` on hostile data. (rules/05)
7. **Supply chain is CI-enforced:** `cargo deny`/`cargo audit` on PRs +
   scheduled, `Cargo.lock` committed, new deps vetted (cargo vet or
   documented review), git deps pinned by rev. (rules/05)
8. **Secrets are typed (`SecretString`/`Zeroizing`), redacted from
   Debug/logs, and compared in constant time** (`ct_eq`). Key material only
   from OS randomness. (rules/05)
9. **Don't clone to satisfy the borrow checker; don't take owned params you
   only read.** `&str`/`&[T]` in signatures, split borrows, `mem::take`;
   newtypes over primitive obsession; exhaustive matches (no lazy `_ =>` on
   owned enums). (rules/01)
10. **CI gate: fmt + clippy `-D warnings` (triaged pedantic) + nextest +
    doctests + MSRV job + feature-matrix check.** Performance claims require
    benchmarks; release profile (LTO/codegen-units/panic strategy) is a
    deliberate, documented choice. (rules/06, 07)
