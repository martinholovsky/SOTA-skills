# 02 — Error Handling & Panic Policy

Errors are API. Panics are program-integrity violations, not control flow.
These rules define the library/application split, the unwrap policy, and how
panics interact with servers and FFI.

## 1. The library/application split

- **Libraries**: concrete, structured error enums via `thiserror`. Callers must
  be able to match on failure modes without string-parsing.
- **Applications** (binaries, services, CLIs): `anyhow` (or `eyre` if you want
  custom report handlers/spantrace) — context-rich, cheap to propagate, rendered
  once at the top.
- Never expose `anyhow::Error` in a library's public API; never build elaborate
  error enums in app code that only ever get printed.

```rust
// LIBRARY (thiserror)
#[derive(Debug, thiserror::Error)]
pub enum StoreError {
    #[error("key not found: {0}")]
    NotFound(String),
    #[error("serialization failed")]
    Serde(#[from] serde_json::Error),
    #[error("io error accessing {path}")]
    Io { path: PathBuf, #[source] source: std::io::Error },
}

// APPLICATION (anyhow)
use anyhow::{Context, Result};
fn load_config(path: &Path) -> Result<Config> {
    let raw = fs::read_to_string(path)
        .with_context(|| format!("reading config {}", path.display()))?;
    toml::from_str(&raw).context("parsing config TOML")
}
```

## 2. Designing library error types

- One error enum **per fallible subsystem**, not one giant crate-wide enum where
  every function claims it can fail in 14 ways it can't. If a function has two
  failure modes, its error type should show two.
- Preserve sources: `#[source]` (or `#[from]`) so `Error::source()` chains work
  and `anyhow` callers get full causality. Don't flatten causes into strings.
- `#[from]` only when the conversion is unambiguous; if two variants wrap
  `io::Error`, use explicit constructors with context (path, operation) instead.
- Mark public error enums `#[non_exhaustive]` so adding failure modes is
  non-breaking.
- Errors must be `Debug + Display + Send + Sync + 'static` (and implement
  `std::error::Error`) — otherwise they won't flow through `anyhow`/`Box<dyn>`.
- Don't `impl From<MyError> for String` or stringly-type errors. Display is for
  humans; variants are for machines.
- Big errors slow every `Result` return: keep error types ≤ ~3 words or box the
  payload (`clippy::result_large_err` flags >128 bytes).

## 3. Context discipline

- Add context **at each boundary where information exists that the callee
  lacked**: file paths, IDs, request params. `?` alone up a 6-frame stack
  yields "No such file or directory" with no idea which file.
- `with_context(|| ...)` (lazy) over `context(format!(...))` (eager allocation
  on success path).
- In services, attach machine context to spans (`tracing` fields), human
  context to the error. Log errors **once**, at the handling site, with
  `{:#}`/error-chain rendering — not at every propagation hop (double-logging
  audit smell).

## 4. unwrap/expect policy

**Production code paths: no `unwrap()`. `expect()` only with an invariant
message — a message stating why this cannot fail, not what failed.**

```rust
// BAD
let port = env::var("PORT").unwrap();
let re = Regex::new(pattern).unwrap();           // user-supplied pattern!

// ACCEPTABLE: invariant expect — message states the reason it can't fail
let re = Regex::new(r"^[a-z]+$").expect("static regex is valid");
let ts = UNIX_EPOCH.elapsed().expect("system clock before 1970");

// GOOD: fallible inputs propagate
let port: u16 = env::var("PORT")
    .context("PORT not set")?
    .parse()
    .context("PORT is not a valid u16")?;
```

- Convention: messages read as "this holds because…" — `expect("mutex not
  poisoned: no panicking critical sections")`. If you can't write the
  invariant, you don't have one; return an error.
- `unwrap()` is fine in: tests, benches, examples, doc-tests, build scripts,
  and `const`/static init where failure is a compile-mistake. Gate the rest:
  `#![warn(clippy::unwrap_used)]` (and `clippy::expect_used` in the strictest
  crates), with `#[allow]` + justification at the call site when truly needed.
- Slicing/indexing (`xs[i]`, `&s[a..b]`) and integer `as` casts are implicit
  unwraps — use `.get(i)`, `s.get(a..b)`, `try_into()` on untrusted values
  (string slicing also panics on non-char-boundary).
- `unreachable!()` must carry the proof: `unreachable!("len checked > 0 above")`.

## 5. Panics: when, and what they cost

Panic only for **bugs** — violated invariants, impossible states — never for
bad input, missing files, network failure, or anything an attacker controls.

- Servers: a panic in a handler must not kill the process, and a reachable
  panic is a DoS primitive (rules/05 §4). Catch at the task boundary —
  `tokio::spawn` already isolates panics into `JoinError`; check
  `JoinError::is_panic()` and log. Axum/tower: `CatchPanicLayer`. But treat
  every caught panic as a bug to fix, not a handled case.
- `panic = "abort"` in release profiles (rules/06) means no unwinding: no
  `catch_unwind`, panics kill the process. Decide deliberately for servers —
  abort+supervisor-restart is a valid stance, but then panic-freedom of
  handlers is load-bearing.
- **FFI**: unwinding across `extern "C"` is UB. Wrap Rust callbacks invoked
  from C in `std::panic::catch_unwind` (or use `extern "C-unwind"` only when
  both sides genuinely support it).
- **`Drop` impls must not panic.** `drop()` itself runs during unwinding from
  another panic; a panic there is a *double panic* that — per the std `Drop`
  docs — "will likely abort the program." So a panicking destructor turns one
  recoverable failure into process death (DoS). Destructors clean up and return
  normally; if a Drop genuinely must signal misuse, gate it on
  `std::thread::panicking()` first. This applies to RAII guards, buffer
  flushers, and `Zeroize`-on-drop types alike. (ANSSI `LANG-DROP-NO-PANIC`)
- Poisoned mutexes (`std::sync::Mutex`): a panic while holding the lock poisons
  it. Decide policy once: propagate (`lock().expect("not poisoned: …")`) or
  recover (`unwrap_or_else(PoisonError::into_inner)`) — document which.
- Allocation failure aborts; for memory-bound parsing of untrusted sizes use
  `try_reserve` (rules/05 §6).

## 6. Option/Result flow patterns

- `?` everywhere it applies, including `Option` in functions returning `Option`.
- Convert at the edges: `ok_or_else(|| StoreError::NotFound(key.into()))` turns
  `Option` into `Result` exactly where "absence is an error" becomes true —
  not earlier.
- `let Some(x) = ... else { return ... };` for guard clauses; keeps the happy
  path unindented.
- Fallible iteration: `collect::<Result<Vec<_>, _>>()` fail-fast; or
  `partition_result` / inspect-and-log per item when partial success is the
  semantics. Choose explicitly — silent `filter_map(Result::ok)` **discards
  errors** and is an audit finding unless commented.
- Don't `match` on a `Result` just to re-wrap (`Ok(v) => Ok(f(v)), Err(e) =>
  Err(e)`) — that's `.map(f)`. Clippy: `manual_map`, `question_mark`,
  `needless_match`.

## 7. Retryability & error classification

Services need errors classified for *behavior*, not just display. Encode the
decision the caller must make:

```rust
#[derive(Debug, thiserror::Error)]
pub enum FetchError {
    #[error("transient: {0}")]
    Transient(#[source] anyhow::Error),   // timeouts, 503, conn reset
    #[error("permanent: {0}")]
    Permanent(#[source] anyhow::Error),   // 4xx, validation, auth
}
impl FetchError {
    pub fn is_retryable(&self) -> bool { matches!(self, Self::Transient(_)) }
}
```

- Classify at the site that knows (the HTTP client wrapper knows 503 vs 400);
  upper layers consume `is_retryable()` instead of re-inspecting causes.
- Retries always carry backoff + jitter + a cap (`backon`/`tokio-retry`
  style); retrying permanent errors is load amplification, retrying without
  jitter is a thundering herd.
- Map the same classification to HTTP/gRPC status at the boundary in ONE
  place (an `IntoResponse`/`From<Error> for Status` impl), not per-handler.
- Idempotency: only auto-retry operations that are idempotent or carry an
  idempotency key — a retried non-idempotent POST is a correctness bug, not
  resilience.

## 8. Testing error paths

Error paths are code; untested error paths are where prod incidents live.

- Unit-test that fallible constructors reject bad input with the *right
  variant*: `assert!(matches!(parse(""), Err(ParseError::Empty)))` — not just
  `.is_err()` (a panic-turned-error or wrong variant passes `.is_err()`).
  `assert_matches!`/`debug_assert_matches!` (stable since 1.96) do the same
  and panic with the actual value on mismatch — prefer them in new tests.
- Test `Display` output of user-facing errors (snapshot with `insta`) —
  error messages are UI and regress silently.
- Fault injection at trait boundaries: a mock `Storage` whose `get` returns
  `Err(Io(...))` proves the caller's context/retry/cleanup logic. If errors
  can't be injected, the seam is missing (concrete deps where traits/generics
  belong).
- For panics that are part of a documented contract: `#[should_panic(expected
  = "...")]` pins the message; for `Result`-returning tests use
  `fn test() -> anyhow::Result<()>` and `?` freely.

## 9. Error reporting at the top

```rust
fn main() -> anyhow::Result<()> { ... } // Debug-renders the chain on error
// or for custom exit codes / human rendering:
fn main() -> ExitCode {
    if let Err(e) = run() {
        eprintln!("error: {e:#}");      // {:#} renders the full context chain
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
}
```

- Services: render error chain into structured logs
  (`tracing::error!(error = ?err)` or the `err` field shorthand), map to a
  client-safe status — never leak internal error text to HTTP responses
  (info disclosure, rules/05).
- Install a panic hook that logs through your structured logger
  (`std::panic::set_hook`) so panics in production aren't lost to stderr.

## Audit checklist

- [ ] `rg '\.unwrap\(\)' -t rust -g '!*test*' -g '!benches/*' -g '!examples/*'`
      — every hit in production paths is a finding; severity scales with input
      reachability (attacker-reachable unwrap = High).
- [ ] `rg '\.expect\("' -t rust` — messages must state invariants ("valid
      static regex"), not restate the failure ("failed to parse").
- [ ] `rg '\.unwrap_or_default\(\)|filter_map\(Result::ok\)|\.ok\(\)[;)]' -t rust`
      — silently swallowed errors; require a comment justifying each.
- [ ] `rg 'panic!|unreachable!|todo!|unimplemented!' -t rust -g '!*test*'` —
      `todo!`/`unimplemented!` in shipped code = High; `panic!` on
      input-derived conditions = High (DoS).
- [ ] Indexing on untrusted data: `rg '\[[a-z_]+\]' -t rust` near
      parse/decode code; string slicing `&s[`, plus `clippy::indexing_slicing`
      (restriction lint) on parser crates.
- [ ] Library crates exporting `anyhow::Error`/`Box<dyn Error>` in public
      signatures: `rg 'pub fn .*-> .*(anyhow|Box<dyn Error)' -t rust`.
- [ ] thiserror enums: variants missing `#[source]`/`#[from]` on wrapped
      errors (broken causality chains); public error enums missing
      `#[non_exhaustive]`.
- [ ] Double-logging: error logged at propagation site AND handler.
- [ ] `?` chains with no `.context(...)` anywhere between syscall and `main` —
      undebuggable errors.
- [ ] FFI: `extern "C"` functions whose bodies can panic without
      `catch_unwind` → UB, Critical.
- [ ] `Drop` impls that can panic: `rg -A15 'impl Drop' -t rust` then scan for
      `unwrap`/`expect`/`panic!`/indexing/`?` inside `fn drop` — double-panic
      aborts the process (DoS), High. `LANG-DROP-NO-PANIC`.
- [ ] Retry loops: `rg 'retry|backoff' -t rust -i` — retries without
      classification (retrying 4xx), without jitter/cap, or around
      non-idempotent operations.
- [ ] Error tests assert variants (`matches!`), not just `.is_err()`; error
      seams injectable (trait boundaries) for fault testing.
- [ ] Lints to enforce in CI: `clippy::unwrap_used`, `clippy::panic` (servers),
      `clippy::result_large_err`, `clippy::or_fun_call`,
      `clippy::manual_let_else`; consider `#![deny(clippy::unwrap_used)]` at
      crate roots of network-facing crates.
