# 05 — Security & Supply Chain

Memory safety is the floor, not the ceiling. Rust services still fall to logic
bugs, integer wrapping, panic-DoS, malicious dependencies, secret leakage, and
hostile input. These rules are written for network-facing code; relax
consciously for offline tools.

## 1. Dependency auditing in CI — cargo audit & cargo deny

Non-negotiable for anything deployed: advisory + policy checks on every PR and
on a schedule (new advisories land against old lockfiles).

```toml
# deny.toml (core)
[advisories]
yanked = "deny"
# RUSTSEC advisories: deny by default; ignore list requires expiry + reason
ignore = [
  # { id = "RUSTSEC-2026-0001", reason = "not reachable: feature off", expire = "2026-09-01" }
]

[licenses]
allow = ["MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "Unicode-3.0"]

[bans]
multiple-versions = "warn"
wildcards = "deny"            # no `foo = "*"`
[[bans.deny]]
name = "openssl"              # example policy: rustls-only stack

[sources]
unknown-registry = "deny"
unknown-git = "deny"          # git deps pinned by rev only, allowlisted
```

- `cargo deny check` (advisories, licenses, bans, sources) in PR CI;
  `cargo audit` nightly via cron so existing `Cargo.lock` gets re-checked.
- Commit `Cargo.lock` for binaries **and** (current guidance) for libraries —
  reproducible CI; `cargo update` is a reviewed PR, not a side effect.
- Dependabot/Renovate for bumps; review changelogs of security-sensitive deps
  (crypto, TLS, parsing) instead of auto-merging.
- Minimize the tree first: every dep is attack surface and build time.
  `cargo tree -d` for duplicates; question deps that pull in 50 transitive
  crates for one function.

## 2. Vetting dependencies — cargo vet / supply-chain hygiene

- `cargo vet`: record audits (`safe-to-deploy`) for each dep version; import
  trusted audit sets (Mozilla, Google, Bytecode Alliance) so you only audit
  the residue. `cargo vet` in CI fails on unaudited new deps — turns "someone
  added a crate" into a reviewed event.
- New-dep review minimum: maintenance signal, repo matches crates.io package
  (`cargo crev`/inspect tarball — typosquats and repo/package divergence are
  the common attacks), `cargo geiger` unsafe density, build.rs and proc-macros
  (these run code **at build time** — highest-trust tier). Check the crate's
  Security tab on crates.io (since Jan 2026 it surfaces RustSec advisories,
  CVE aliases, and affected ranges at the point of discovery).
- **Before adding a dependency** (yours or an AI assistant's pick — it can name crates that do
  not exist, or that a squatter registered after the name was hallucinated): `cargo info <name>`
  must resolve (exit 101 if unknown); read licence and repository there, then
  `https://crates.io/api/v1/crates/<name>` (`created_at`, `recent_downloads`) and `…/owners` —
  a days-old crate, one owner, or a repository that is not the project you meant stops it.
  Cross-check `https://deps.dev/cargo/<name>` and the repo's OpenSSF Scorecard
  (`https://api.securityscorecards.dev/projects/github.com/<owner>/<repo>`). A newest release
  can be a tombstone: `bincode` 3.0.0 is one `compile_error!` line.
- **A crate's defaults become your code — set each security-relevant option yourself.** Read in
  source: async `reqwest::Client` (0.13.5) has `timeout`, `read_timeout` and `connect_timeout`
  all `None`, while the blocking client defaults to 30 s; `bincode` 2 `config::standard()` and
  `legacy()` carry `NoLimit`, so a decoded `Vec<u8>` allocates the length the input claims —
  decode untrusted bytes with `.with_limit::<N>()`; `minijinja` picks auto-escaping from the
  template *name* (`.html`/`.htm`/`.xml` → HTML, `.json`/`.js`/`.yaml` → JSON with the `json`
  feature, any other name → none), so `add_template("page", …)` renders values raw unless you
  set `set_auto_escape_callback`.
- **A README or example snippet is a demo config.** `tower_http::cors::CorsLayer::permissive()`
  allows any origin, method and header; `very_permissive()` also allows credentials and mirrors
  the caller's origin — right for an example, a finding in a service; so is a pasted
  `danger_accept_invalid_certs(true)` (§7). (OWASP: Vulnerable Dependency Management, Software
  Supply Chain Security, Secure Coding with AI cheat sheets; SCVS V1, V6.)
- This is not theoretical: Feb–Mar 2026 saw a coordinated campaign of five
  fake "time utility" crates (`time-sync`, `dnp3times`, `chrono_anchor`, … —
  RUSTSEC-2026-0030/0031/0032/0036) that typosquatted/brandjacked real crates
  and exfiltrated `.env` files from developer and CI machines. Mitigations are
  exactly the above plus secret hygiene: no long-lived credentials in `.env`
  on build machines; rotate anything exposed to an unvetted build.
- Pin GitHub Actions by SHA, not tag; CI tokens least-privilege
  (`permissions: contents: read` default).
- **Build-time code runs before any test or review of your code does.** Each `build.rs`
  (picked up at a package root with no `build =` key) and each `proc-macro = true` crate is
  compiled and run on the developer machine and CI runner with that user's environment.
  Measured on cargo 1.97.1: `cargo check` ran a path dependency's `build.rs` and a proc-macro,
  and an env var exported for the command was readable inside that `build.rs`; `cargo
  metadata`, `cargo fetch` and `cargo tree` ran neither. rust-analyzer also runs them on
  opening a project (`rust-analyzer.cargo.buildScripts.enable` and
  `rust-analyzer.procMacro.enable`, both default `true`) — set both `false` before opening an
  untrusted checkout. `[build] rustc-wrapper` is the same trust from config (rules/07 §4a).
  **There is no off switch**: `cargo build --help` and `cargo -Z help` (1.97.1) offer no flag
  that skips build scripts or proc-macros, so the controls are review and isolation.
  Review: list what runs with the audit probe below; on every bump read
  `cargo vet diff <crate> <old> <new>` for those crates' `build.rs` and macro source first.
  Your OWN `build.rs`, proc-macro crates, `.cargo/config.toml`, `Cargo.toml`, `Cargo.lock` and
  `rust-toolchain.toml` get CODEOWNERS entries plus the branch rule "Require review from Code
  Owners" — an agent-authored PR included. CI: `cargo fetch --locked` is the networked step
  and runs no dependency code; build and test with `--frozen` in a job that holds no publish,
  deploy or cloud credentials, and hand the artifact to a separate job that does. (OWASP: CI/CD
  Security cheat sheet; Software Supply Chain Security cheat sheet; NPM Security cheat sheet.)
- **Declared but not reached**: an unused crate is still install/build-time trust
  granted (`build.rs`, proc-macros) for zero function. `cargo machete` runs on
  stable but is deliberately imprecise — false positives for crates used only
  from `build.rs`-generated code and for import names that differ from package
  names (`--with-metadata` fixes the latter); `cargo +nightly udeps` needs
  nightly and documents false *negatives*. Neither settles it alone: prove a
  candidate by removing it in a scratch copy and running the real build, clippy,
  and full suite — `sota-devsecops` rules/10.

## 3. Integer overflow — release mode wraps

Debug builds panic on overflow; **release builds wrap silently** (unless
`overflow-checks = true`). Wrapping on attacker-influenced arithmetic is how
length checks, allocations, and billing go wrong.

```rust
// BAD: attacker sends len = u32::MAX; len + 4 wraps to 3, check passes
if header.len + 4 <= buf.len() as u32 { read(&buf[..header.len as usize]) }

// GOOD: checked arithmetic on untrusted input, fail closed
let total = header.len.checked_add(4).ok_or(Error::BadLength)?;
if (total as usize) <= buf.len() { ... }
```

- Policy: **untrusted input → `checked_*` / `try_into`**; counters/metrics →
  `saturating_*`; intentional modular arithmetic (hashes, crypto, ring
  buffers) → `wrapping_*` / `Wrapping<T>` so intent is greppable. Bare `+ - *`
  is for values you've already bounded.
- Set `overflow-checks = true` in the **release profile** for security-critical
  services — the cost is usually <2% and it converts silent corruption into a
  caught panic. (Then see §4: that panic must be contained.)
- `as` casts truncate silently (`u64 as u32`, `i64 as usize`): use
  `try_from` on untrusted values; clippy `cast_possible_truncation`,
  `cast_sign_loss` (pedantic) on parser/protocol crates.

## 4. Panics as DoS

Any attacker-reachable panic is a denial-of-service primitive — one request
kills a worker or (with `panic=abort`) the whole process.

- Hunt the implicit panic surface in request paths: `unwrap`/`expect`
  (rules/02), slice indexing, `&s[a..b]` on non-char boundaries, integer
  division by zero, `with_capacity(attacker_len)` (capacity overflow /
  OOM-abort), recursion depth on nested input (stack overflow — **abort, not
  catchable**; see §6 on serde recursion).
- Containment at the boundary: per-connection/per-request `tokio::spawn`
  isolates unwinding panics (`JoinError::is_panic`); `CatchPanicLayer` for
  tower stacks. With `panic = "abort"`, containment is gone — pair abort with
  a supervisor (systemd `Restart=always`, k8s) and treat reachable panics as
  Critical, plus rate-limit restarts to blunt crash-loop DoS.
- Resource-exhaustion siblings of panic-DoS: unbounded channels (rules/04),
  missing request body limits, decompression bombs (cap decompressed size),
  unbounded `read_to_end` on sockets — set explicit limits at every ingest.

## 5. Secrets in memory — zeroize & constant time

- Wrap key material in `zeroize`/`secrecy`:

```rust
use secrecy::{SecretString, ExposeSecret};
struct DbConfig { url: String, password: SecretString }
// Debug prints REDACTED; memory zeroized on drop; .expose_secret() is greppable
```

  Zeroize is best-effort (moves/reallocations copy bytes — avoid resizing
  buffers holding secrets; `Box::pin` long-lived keys), but it shrinks the
  window and kills the "secret in a core dump / Debug log" class.
- **Don't rely *only* on `Drop` for security erasure.** `Drop` is skipped
  entirely by `mem::forget`, `Box::leak`, reference cycles (`Rc`/`Arc`), a
  panic mid-drop, and `panic = "abort"` / process exit — so Drop-based
  zeroization is a window-shrinker, not a guarantee. Don't structure a security
  argument ("the key is erased after use") on the destructor running; minimize
  the secret's lifetime, avoid leaking/forgetting secret-bearing values, and
  keep Drop impls panic-free (rules/02 §5) so the erasure path isn't skipped by
  an abort. (ANSSI `LANG-DROP-SEC`; soundness corollary in rules/03.)
- **No `Debug`/`Display`/`Serialize` leaking secrets**: manual `Debug` impls
  redacting sensitive fields; never `#[derive(Debug)]` on a struct holding a
  raw key. Audit `tracing` events for token/password fields.
- Comparisons of MACs/tokens/password hashes: constant-time only —
  `subtle::ConstantTimeEq` (`a.ct_eq(&b)`), or the comparison built into the
  crypto crate (e.g. `hmac`'s `verify_slice`). `==` on secret bytes is a
  timing oracle.
- Don't hand-roll crypto: RustCrypto crates, `ring`, `aws-lc-rs`, or libsodium
  bindings; password hashing via `argon2`; randomness via `rand::rngs::OsRng`
  / `getrandom` only (never `SmallRng`/`thread_rng` for key material —
  thread_rng is a CSPRNG but OsRng removes the argument).
- Env/config: secrets via files or secret managers over env vars where
  possible (`/proc/<pid>/environ` leaks); never in `Cargo.toml`, never
  compiled into the binary (`strings target/release/app | rg -i secret`).

## 6. Parsing untrusted input — serde hardening

Deserialization is the front door. Rules for any `serde` boundary fed by the
network:

- **Size-limit before parse**: enforce body/frame limits at the transport
  (axum `DefaultBodyLimit`, manual `Content-Length` + streaming cap) — parsing
  a 2GB JSON body allocates before serde can object.
- **`deny_unknown_fields`** on security-relevant configs and requests
  (prevents smuggling fields through proxies/validators that the backend
  interprets) — but note it breaks `#[serde(flatten)]` and forward-compat;
  choose per-type.
- **Untagged enum DoS**: `#[serde(untagged)]` tries each variant in order —
  on deep/nested input this multiplies parse work and produces useless errors;
  worst case is exponential blowup with nested untagged enums. Prefer tagged
  (`#[serde(tag = "type")]`) or manual discriminator dispatch on hostile
  input. Adjacent risk: recursion depth — `serde_json` has a default 128-level
  limit, but `serde_yaml`-style formats and custom `Deserialize` impls may
  not; use `serde_stacker`/explicit depth caps for deeply-nested formats
  (stack overflow = abort = DoS).
- Validate after parse: serde checks shape, not semantics. Lengths, ranges,
  string charsets via `TryFrom` newtypes (rules/01 §3) or `validator`/`garde`
  — the deserialized type should already be the validated type
  ("parse, don't validate").
- `Vec` preallocation from attacker-controlled length prefixes
  (`Vec::with_capacity(hdr.count)`): cap or `try_reserve`. Binary formats
  (`bincode` etc.): configure size limits explicitly.
- Don't deserialize to `Box<dyn Trait>`/arbitrary types via
  `typetag`-style registries from untrusted sources without an allowlist.
- Fuzz every parser of untrusted bytes: `cargo fuzz` target per format, in
  scheduled CI. Combine with rules/03 sanitizers when the parser has unsafe.

## 7. Service-edge defaults

- TLS: `rustls` stack by default (memory-safe, modern defaults).
- **TLS / transport verification is on and stays on.** The escape hatches are named, which
  makes them easy to audit: reqwest's `danger_accept_invalid_certs(true)` and
  `danger_accept_invalid_hostnames(true)`, native-tls's methods of the same names, and in
  rustls anything built through `.dangerous()` — a custom `ServerCertVerifier` whose
  `verify_server_cert` returns `Ok` for everything is certificate checking switched off.
  None belongs outside test code; a pinned or private CA goes into the root store (or a
  verifier that delegates to `WebPkiServerVerifier` first), never around it. For mTLS on the
  server, use `WebPkiClientVerifier` and authorise on a SAN, not on the subject CN.
  Verified against reqwest 0.13.5, native-tls 0.2.18 and rustls 0.23.45 sources.
- **Outbound requests to a caller-influenced destination (SSRF)** — policy in
  `sota-code-security` rules/01 §5; the reqwest idiom (read in reqwest 0.13.5, hyper-util 0.1.20):
  - Take a host key or ID from the caller and build the `Url` from your own allowlist
    entry; relaying a caller-supplied URL is the pattern to design out.
  - **The check belongs on the address being dialled.** Implement `reqwest::dns::Resolve`,
    run the real lookup inside it, drop every unsafe `SocketAddr`, fail if none remain,
    and install it with `ClientBuilder::dns_resolver(...)`. Because the connector uses
    whatever the resolver returns, a rebinding answer after an earlier "safe" lookup is
    never dialled. Reject after `IpAddr::to_canonical()` (stable 1.75; without it an
    IPv4-mapped `::ffff:127.0.0.1` is not `is_loopback()`): loopback, unspecified
    (0.0.0.0/8 by range), `is_private()`, `is_link_local()` (covers 169.254.169.254),
    multicast, broadcast, and IPv6 `is_unique_local()` / `is_unicast_link_local()`
    (both stable 1.84). `is_global()` is still unstable. Also refuse your cloud
    provider's metadata hostnames by name.
  - **The resolver never sees an IP literal**: hyper-util's `HttpConnector` dials a host
    that parses as an address directly. So validate `url.host()` as well, before the
    request and on every redirect hop. Use the parsed `url::Host::Ipv4/Ipv6`, never the
    raw string: `url` (WHATWG) turns `0177.0.0.1`, `0x7f.1` and `2130706433` into
    `127.0.0.1`, while std's `Ipv4Addr::from_str` rejects all three. Parse bare IP
    input with std; do not use `url` for that.
  - Redirects: `.redirect(Policy::none())`, or `Policy::custom(|a| ...)` that re-runs the
    host check on `a.url()` and calls `a.error(..)` on a failure. The default follows up to 10.
  - `.https_only(true)` limits the first request and every redirect hop to https.
  - `.no_proxy()`: the default `system-proxy` feature reads the system/env proxy. Through a
    proxy, the proxy resolves the target, so your resolver's check never sees that address.
  OWASP: SSRF Prevention, .NET Security and GraphQL cheat sheets.
- **A regex used as a control** (validation, allowlist, routing, redaction) — read in
  `regex` 1.13.1 and `fancy-regex` 0.19.2 sources, behaviour measured on rustc 1.97.1:
  - **Escaping.** Untrusted text spliced into a pattern goes through `regex::escape(&s)`
    (`fancy_regex::escape` for that crate); raw `Regex::new(&format!(..))` lets the caller
    write `.*`. Propagate the build `Err`, never `unwrap()` it (rules/02 §4).
  - **Anchoring.** Every search, `is_match` included, is unanchored (the crate prepends an
    implicit `(?s:.)*?`), so `[a-z]+` accepts `abc;rm`. Group before anchoring:
    `^(?:a|b)$` — measured, `^a|b$` accepts `axxx`. Without multi-line mode `$` is end of
    haystack only (measured: `^[a-z]+$` rejects `abc\n`). `(?m)` or
    `RegexBuilder::multi_line(true)` makes `^`/`$` line anchors, so `ok\nEVIL!` passes;
    write `\A…\z` where that flag may be on.
  - **Unicode classes.** `\d`/`\w` are Unicode by default: `^\d+$` accepts `١٢٣`
    (measured). Use `[0-9]` or `(?-u:\d)` when the consumer expects ASCII.
  - **Bounds.** Counted repetition in the pattern (`{1,64}`) plus a byte-length check on
    the input first. For patterns you did not write: cap the pattern length and set a small
    `RegexBuilder::size_limit` (the builder's default NFA limit is 10 MiB).
  - **Engine.** `regex` is finite-automata: worst case O(m·n) per search, linear in the
    haystack, and it rejects lookaround and backreferences at build time (measured). Its
    docs note `find_iter`/`captures_iter` are O(m·n²) worst case. `fancy-regex` adds
    those features by **backtracking**; `is_match` returns `Result<bool>` and
    `RegexBuilder::backtrack_limit` (default 1,000,000) bounds the work — measured,
    `^(a|aa)+\1?$` on a 29-byte input returned `Err(BacktrackLimitExceeded)`. Treat that
    `Err` as a reject, lower the limit on request paths, and prefer staying in `regex`.
  OWASP: Input Validation cheat sheet; Proactive Controls 2024 C3; ASVS 5.0 V1.2.9;
  OWASP Go-SCP (validation, regular expressions).
- **Cookies the app sets itself** (the session cookie is `sota-code-security` rules/17).
  Measured with cookie 0.18.2, axum-extra 0.12.6, actix-web 4.15.0 and rocket 0.5.1:
  - `Cookie::new("a", "b")` and `Cookie::build(("a", "b")).build()` serialise as a bare
    `a=b`. There is no Secure, HttpOnly, SameSite or Path. axum-extra's `CookieJar::add` and
    actix-web's `HttpResponseBuilder::cookie` send that unchanged (measured `x=y`), so the
    browser picks the SameSite default, and MDN says only "some browsers" use `Lax`.
  - Rocket's `CookieJar::add` fills in `Path=/` and `SameSite=Strict` but **not HttpOnly**.
    It sets Secure **only when Rocket itself serves TLS** (`config.tls_enabled()`). Behind a
    TLS-terminating proxy it sent `pub=v; SameSite=Strict; Path=/`. `add_private` also adds
    HttpOnly and a one-week `Expires`.
  - Set every attribute yourself:
    `Cookie::build(("__Host-id", v)).secure(true).http_only(true).same_site(SameSite::Lax).path("/")`,
    with no `.domain(..)`. Measured output: `__Host-id=v; HttpOnly; SameSite=Lax; Secure; Path=/`.
    The `__Host-` prefix makes the browser require Secure and `Path=/` and reject any Domain
    (MDN). Drop HttpOnly only for a cookie that script must read, such as a double-submit
    CSRF token.
  OWASP: Session Management and Cookie Theft Mitigation cheat sheets; ASVS 5.0 V3.3.
- **Debug builds and dev tooling stay out of production.** Rust frameworks have no
  debug page to switch off. The switches are the build profile and the tooling:
  - `cargo run` and `cargo build` without `--release` use the dev profile. With it,
    `debug_assertions` is on, so any `#[cfg(debug_assertions)]` dev-only route is compiled
    in. Rocket picks its profile from `ROCKET_PROFILE`, which defaults to `debug` in a debug
    build and `release` in a release build (rocket 0.5.1 source). With the `secrets`
    feature and no `secret_key`, the `debug` profile quietly generates a random key, while
    any other profile refuses to launch (`InsecureSecretKey`). `ROCKET_PROFILE=debug` on a
    release binary therefore re-enables that fallback.
  - Check production mode at startup. When your deployment environment says production,
    refuse to start if `cfg!(debug_assertions)` is true, and for Rocket if
    `rocket.config().profile != Config::RELEASE_PROFILE`. Build images with
    `cargo build --release --locked`, never `cargo run`.
  - tokio-console: `console_subscriber::init()` serves task internals over gRPC on
    `127.0.0.1:6669` by default. `TOKIO_CONSOLE_BIND` can move it to another address, and
    the 0.5.0 builder has no authentication or TLS setting. It also needs
    `--cfg tokio_unstable`. Put it behind a cargo feature that release builds leave off,
    and never bind it off loopback.
  OWASP: Error Handling cheat sheet; Secure Headers Project; ASVS 5.0 V13.4.
- Timeouts on **everything**: connect, read, write, total-request, idle
  (`TimeoutLayer`, `tower` middleware). Missing timeouts = slowloris.
- Error responses: generic client text, full chain only into logs (rules/02
  §9); no `Debug`-formatted internals in HTTP bodies.
- Path handling on user input: reject `..` traversal — canonicalize then
  verify prefix (`path.canonicalize()?.starts_with(root)`), never just join.
- SQL via parameterized queries (`sqlx` compile-checked, `diesel`); any
  `format!` into a query string is a finding regardless of current inputs.

## 8. Release provenance & logging hygiene

- **`cargo auditable`**: embeds the dependency list in the binary so deployed
  artifacts can be scanned against future advisories (`cargo audit bin app`).
  Pair with SBOM generation (`cargo cyclonedx`/`cargo sbom`) where compliance
  requires it. Reproducible-ish builds: pinned toolchain + locked deps +
  `--locked` in release CI (`cargo build --release --locked` — fails instead
  of silently updating the lockfile).
- Release binaries built in CI from tags, not laptops; artifacts checksummed
  and (where distribution warrants) signed; `--locked` and the pinned
  toolchain make the build attributable to the lockfile that was audited.
- **Log injection**: user-controlled strings logged raw can forge log lines
  (embedded `\n`) or poison downstream parsers — log via `tracing` structured
  fields (`tracing::info!(user = %name)` escapes on JSON output) rather than
  interpolating into the message; never log full request bodies or headers
  carrying credentials (`Authorization`, `Cookie`) — redact at the middleware
  layer once.
- Don't log at error level on client mistakes (4xx) — that's an
  alert-fatigue vector that buries real errors; reserve `error!` for
  operator-actionable events.

Running external programs (formerly section 9) moved to
[rules/08](08-external-programs.md) §1 on 2026-09-25.

## Audit checklist

- [ ] CI has `cargo deny check` (or `cargo audit`) on PRs **and** a scheduled
      run; `deny.toml` ignore entries have reasons + expiry. Missing = High
      for deployed services.
- [ ] `Cargo.lock` committed; `rg 'git = "' Cargo.toml */Cargo.toml` — git
      deps without `rev =` pin = Medium; wildcard versions = Medium.
- [ ] `cargo vet` (or documented dep-review process) for new dependencies;
      build.rs / proc-macro deps enumerated and reviewed.
- [ ] **Build-time code (build.rs / proc-macro) is inventoried, owned and isolated (§2) —
      High** — `cargo metadata --format-version 1 --locked | jq -r '.packages[] | select(any(.targets[]; any(.kind[]; . == "custom-build" or . == "proc-macro"))) | "\(.name) \(.version)"'`
      (every line is code that runs on `cargo check`: each needs a review record, e.g. a
      `cargo vet` audit). Then `rg -n --no-messages 'build\.rs|Cargo\.(toml|lock)|\.cargo/' .github/CODEOWNERS CODEOWNERS docs/CODEOWNERS`
      — no line means your own build-executing files merge without an owner. A CI job that
      runs cargo build/test with publish or deploy secrets in scope is also High.
- [ ] **New dependency adoption and insecure defaults (§2) — High on a deployed service,
      else Medium** — each crate a diff adds has a selection record (`cargo info` resolves;
      owners, age, repository, deps.dev/Scorecard read). Then
      `rg -n -t rust 'CorsLayer::(very_)?permissive\(|config::(standard|legacy)\(\)|with_no_limit\(|reqwest::Client::new\(\)' . | rg -v 'with_limit'`
      (each hit is a library default kept: permissive CORS, unbounded bincode decode, a client
      with no timeout); also read every `reqwest::Client::builder()` for `.timeout(`.
- [ ] **TLS / transport verification (§7) — CRITICAL outside tests** —
      `rg -n 'danger_accept_invalid_(certs|hostnames)\(\s*true|\.dangerous\(\)|impl\s+ServerCertVerifier\s+for' -t rust`
      (each hit outside `#[cfg(test)]` is a finding unless the verifier delegates to
      `WebPkiServerVerifier` before its own check)
- [ ] **SSRF / outbound request to a caller-influenced URL (§7) — High (Critical if
      cloud metadata endpoint 169.254.169.254 is reachable)** —
      `rg -n -t rust 'reqwest::(blocking::)?get\(' .` (the default client cannot carry a
      resolver or redirect policy; any hit that takes a caller-influenced URL is a finding) and
      `rg -l0 -t rust 'Client::(new|builder)\(\)' . | xargs -0 -r rg --files-without-match 'dns_resolver\('`
      (these files build a client with no connect-time address check). In a file that does
      have one, confirm `.redirect(` is `none()` or re-checks the host, that `.no_proxy()` is
      set, and that IP-literal hosts are checked via `url.host()`.
- [ ] **Regex escaping, anchoring and engine choice (§7) — High on an auth/allowlist
      path, else Medium** —
      `rg -n -t rust 'Regex(Builder)?::new\(\s*&?format!\(|fancy_regex::|\(\?m\)|multi_line\(true\)' . | rg -v 'escape\('`
      (a `format!` pattern without `regex::escape`, a backtracking engine, or line-mode
      anchors). For each `fancy_regex` hit confirm `backtrack_limit` and that an `Err` rejects;
      then read every validation regex for whole-input `^(?:…)$`/`\A…\z` and a length bound.
- [ ] **App-set cookie attribute defaults (§7): a missing Secure flag, HttpOnly or SameSite.
      High on an auth or identifier cookie, else Medium.** Run
      `rg -n -t rust 'Cookie::(new|build)\(|(jar|cookies)\.add(_private)?\(' . | rg -v 'secure\(true\)'`.
      Each hit builds a cookie without `secure(true)` on that line. Read multi-line builders
      for `.secure(true)`, `.http_only(true)`, `.same_site(..)`, `.path("/")` and no `.domain(`.
      Rocket's defaults do not add Secure behind a TLS-terminating proxy.
- [ ] **Debug build or dev tooling in production (§7), meaning the service is not in release
      mode. High if it is reachable off-host, else Medium.** Run
      `rg -n --hidden -g '!target' '#\[cfg\((all\(|any\()?debug_assertions|console_subscriber::|ROCKET_PROFILE|TOKIO_CONSOLE_BIND|tokio_unstable|cargo("?,\s*"|\s+)run' .`.
      It covers `.cargo/` config, Dockerfiles and manifests. Each hit needs a reason it
      cannot reach production: a dev-only route, a console behind a feature that is off, no
      `ROCKET_PROFILE=debug`, and images built with `--release`. Also confirm the startup
      check that refuses a debug build.
- [ ] Arithmetic on input: `rg '(len|size|count|offset|idx)\s*[+*-]' -t rust`
      near parsing code — wrapped math on untrusted values = High;
      `rg 'as u(8|16|32)|as usize' -t rust` in protocol code for truncating
      casts; release profile `overflow-checks` decision documented.
- [ ] Panic surface in handlers: run rules/02 checklist scoped to
      request-reachable code; `rg 'with_capacity\(' -t rust` where the arg
      derives from input = High.
- [ ] `rg '#\[derive\(.*Debug' -t rust` on structs with `password|secret|key|
      token` fields; `rg '==' -t rust` comparing MACs/tokens (want `ct_eq`);
      secrets not in `SecretString`/`Zeroizing` = Medium-High.
- [ ] `rg 'thread_rng|SmallRng|StdRng::seed' -t rust` in key/nonce/token
      generation paths → require OsRng/getrandom.
- [ ] `rg 'untagged' -t rust` on network-facing types = review for DoS;
      `rg 'deny_unknown_fields'` absent on auth/config types = Low-Medium;
      body-size limits present at every ingest (axum `DefaultBodyLimit`,
      manual caps) — absent = High.
- [ ] `rg 'format!\(.*(SELECT|INSERT|UPDATE|DELETE|WHERE)' -t rust -i` = High;
      `rg '\.join\(' -t rust` on user-supplied path segments without
      canonicalize+prefix check = High.
- [ ] Fuzz targets exist for each untrusted-input parser; absent on a
      network-facing parser = Medium.
- [ ] Release CI uses `--locked`; binaries built from tags in CI;
      `cargo auditable` (or SBOM) for deployed artifacts = recommended.
- [ ] Logs: `rg 'info!|warn!|error!|debug!' -t rust` near auth/headers — no
      `Authorization`/`Cookie`/body logging; user strings as structured
      fields, not message interpolation.
- [ ] `rg 'output\(\)|wait_with_output' -t rust` where the child's output size is
      not bounded by the caller = Medium (R9.6); `rg 'pre_exec' -t rust` — the
      closure must be async-signal-safe (R9.7).
- [ ] Severity calibration: RCE/memory corruption = Critical; authn/authz
      bypass, SQLi, traversal = Critical/High; attacker-reachable panic or
      unbounded allocation = High; missing CI audit gates = Medium-High;
      hygiene (locks, lints) = Low-Medium.
