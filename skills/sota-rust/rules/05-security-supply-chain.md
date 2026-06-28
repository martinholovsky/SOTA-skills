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
- This is not theoretical: Feb–Mar 2026 saw a coordinated campaign of five
  fake "time utility" crates (`time-sync`, `dnp3times`, `chrono_anchor`, … —
  RUSTSEC-2026-0030/0031/0032/0036) that typosquatted/brandjacked real crates
  and exfiltrated `.env` files from developer and CI machines. Mitigations are
  exactly the above plus secret hygiene: no long-lived credentials in `.env`
  on build machines; rotate anything exposed to an unvetted build.
- Pin GitHub Actions by SHA, not tag; CI tokens least-privilege
  (`permissions: contents: read` default).

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

## Audit checklist

- [ ] CI has `cargo deny check` (or `cargo audit`) on PRs **and** a scheduled
      run; `deny.toml` ignore entries have reasons + expiry. Missing = High
      for deployed services.
- [ ] `Cargo.lock` committed; `rg 'git = "' Cargo.toml */Cargo.toml` — git
      deps without `rev =` pin = Medium; wildcard versions = Medium.
- [ ] `cargo vet` (or documented dep-review process) for new dependencies;
      build.rs / proc-macro deps enumerated and reviewed.
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
- [ ] Severity calibration: RCE/memory corruption = Critical; authn/authz
      bypass, SQLi, traversal = Critical/High; attacker-reachable panic or
      unbounded allocation = High; missing CI audit gates = Medium-High;
      hygiene (locks, lints) = Low-Medium.
