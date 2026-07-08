# 05 — Security: injection, paths, TLS, integers, supply chain

Threat model every input by origin: network, files, env, CLI args, DB
contents, and inter-service messages are all untrusted until validated.
Go removes memory-corruption classes but injection, traversal, SSRF, and
misconfiguration are entirely yours.

## 1. Input validation at trust boundaries

- Validate at the **boundary** (handler/consumer), once, into a typed value;
  interior code trusts its types. Re-validating everywhere means nobody knows
  where the real check is.
- Allowlist over denylist: enums via `ParseX(string) (X, error)`, bounded
  lengths/sizes on every string/slice, `utf8.ValidString` on text that
  reaches storage or other parsers.
- JSON: `dec := json.NewDecoder(r.Body); dec.DisallowUnknownFields()` for
  strict APIs; remember `encoding/json` ignores case in field matching and
  silently drops unknown fields by default — security-relevant for
  privilege fields. Pair with `http.MaxBytesReader` (`rules/04`).
- Numbers from JSON into `any` become `float64` — large int64 IDs silently
  lose precision; decode into concrete struct types or `json.Number`.
- Never echo raw input into errors/logs without bounding
  (`%.100q`) — log injection and PII leak.
- Don't reflect internal errors to clients (`rules/01 §7`): stack traces,
  SQL text, and file paths in responses are recon gifts — MEDIUM.
- Output encoding is contextual and separate from input validation: render
  HTML through `html/template` (it auto-escapes per context), never
  `text/template` or `fmt.Fprintf` into a page — that's stored/reflected XSS.
  The `template.HTML`/`JS`/`URL`/`CSS`/`HTMLAttr` cast types switch escaping
  off; each is a sink that must be independently sanitized. Full
  XSS/CSP/output-encoding rules live in sota-code-security `05`.

## 2. SQL — parameterized always

String-built SQL is CRITICAL regardless of the value's provenance ("it's an
int", "it's internal") — provenance changes, code is copied.

```go
// BAD — CRITICAL
q := fmt.Sprintf("SELECT * FROM users WHERE email = '%s'", email)
rows, err := db.Query(q)

// GOOD — database/sql placeholders
rows, err := db.QueryContext(ctx,
    "SELECT id, name FROM users WHERE email = $1", email)

// GOOD — pgx native
row := pool.QueryRow(ctx, "SELECT id FROM users WHERE email = $1", email)
```

- **sqlc** is SOTA for query-heavy services: SQL in `.sql` files, generated
  type-safe Go, parameterization by construction, schema-checked at codegen.
  **pgx/v5** as the runtime driver/pool (`pgxpool`) for Postgres.
- Identifiers (table/column names, ORDER BY direction) can't be placeholders:
  map them through a hardcoded allowlist, never interpolate input:

```go
orderCol, ok := map[string]string{"name": "name", "created": "created_at"}[req.Sort]
if !ok { return ErrBadSort }
q := "SELECT ... ORDER BY " + orderCol // safe: values are program constants
```

- `IN (...)` lists: build placeholders programmatically or use pgx's array
  binding (`= ANY($1)`).
- LIKE patterns: escape `%`/`_` in user input before binding.
- Always `defer rows.Close()`; check `rows.Err()` after the loop; use
  `QueryContext`/`ExecContext` (ctx discipline). Pool settings
  (`SetMaxOpenConns`, `SetMaxIdleConns`, `SetConnMaxLifetime`) explicit —
  default unlimited open conns can flatten the DB.
- ORMs: if GORM/ent are in use, audit every `Raw`, `Exec`, `Where(fmt.Sprintf`
  call site — string interpolation there is the same CRITICAL.

## 3. os/exec — argv, never shell

`exec.Command` does NOT invoke a shell — that's the security feature. Each
argument is a separate argv entry; metacharacters are inert.

```go
// BAD — CRITICAL command injection
out, err := exec.Command("sh", "-c", "convert "+userFile+" out.png").Output()

// GOOD — argv vector, ctx-bound
cmd := exec.CommandContext(ctx, "convert", userFile, "out.png")
cmd.Stdout, cmd.Stderr = &outBuf, &errBuf
err := cmd.Run()
```

- `sh -c` / `bash -c` with ANY interpolated data is CRITICAL. With constant
  strings only, it's MEDIUM (fragile pattern, invites edits that interpolate).
- Argument injection still applies: a userFile like `-trim` becomes a flag.
  Use `--` end-of-options where the tool supports it, validate the value
  shape, or prefix paths (`./`+name).
- Set `cmd.Dir`, pass minimal `cmd.Env` (don't inherit secrets-laden environ
  into child processes: `cmd.Env = []string{"PATH=/usr/bin"}`).
- Binary resolution: Go 1.19+ `exec.LookPath`/`Command` refuse relative-path
  matches from the current directory on Unix; still prefer absolute paths
  for security-sensitive helpers.
- `CommandContext` kills on ctx cancel but **waits for copied pipes**; set
  `cmd.WaitDelay` (1.20+) so a child that inherits the pipe can't block
  `Wait` forever.

## 4. Path traversal

Joining user input into paths without containment is HIGH/CRITICAL
(read: arbitrary file read/write).

```go
// BAD — ../../../etc/passwd
f, err := os.Open(filepath.Join(baseDir, userPath))
```

**Go 1.24+: `os.Root` is the answer** — kernel-enforced containment
(openat2/RESOLVE_BENEATH semantics), immune to `..`, absolute paths, and
symlink escapes:

```go
root, err := os.OpenRoot(baseDir)
if err != nil { return err }
defer root.Close()
f, err := root.Open(userPath) // cannot escape baseDir, even via symlinks
```

Caveat: containment is only as good as the toolchain — CVE-2026-39822
(fixed in 1.26.5/1.25.12, 2026-07) let `root.Open("symlink/")` follow a
trailing-slash symlink out of the Root on Unix (go.dev issue #79005).
Reinforces the §8 keep-the-toolchain-current rule.

Pre-1.24 fallback (and for path *strings* not yet opened):

```go
func securePath(baseDir, userPath string) (string, error) {
    if !filepath.IsLocal(userPath) { // 1.20+: rejects ../, absolute, reserved names
        return "", fmt.Errorf("invalid path %q", userPath)
    }
    return filepath.Join(baseDir, userPath), nil
}
```

- `filepath.Clean` alone is NOT containment (it normalizes; `Clean("../x")`
  is still `../x`). Prefix-checking `strings.HasPrefix(abs, base)` misses
  symlinks and `base`-sibling prefixes (`/srv/app` vs `/srv/app-secrets`) —
  if you must, compare against `filepath.Separator`-terminated resolved
  (`filepath.EvalSymlinks`) paths.
- Zip/tar extraction: validate every entry name with `filepath.IsLocal` +
  reject absolute/`..` (zip-slip); bound total size and file count
  (decompression bomb).
- Serving files: `http.ServeFile` rejects `..` but build the path with
  `http.FileServer`/`http.FS` over a rooted FS rather than manual joins;
  `os.DirFS` + `fs.Sub`, or `os.Root.FS()` on 1.24+.

## 5. Integer conversion overflow (gosec G115)

Conversions between int sizes/signs silently truncate/wrap — exploitable when
the value gates an allocation, length, offset, or privilege check.

```go
// BAD — attacker sends length = 4294967296; on 32-bit int wraps to 0
n := int32(req.Length)          // truncates
buf := make([]byte, n)

// BAD — negative int → huge uint
u := uint64(off)                // off = -1 → 18446744073709551615

// GOOD — bounds-check before every narrowing/sign-changing conversion
if req.Length < 0 || req.Length > math.MaxInt32 {
    return fmt.Errorf("length %d out of range", req.Length)
}
n := int32(req.Length)
```

- High-risk sites: `len()` math into smaller ints, binary protocol parsing,
  `strconv.Atoi` (returns platform `int`) then narrowed — use
  `strconv.ParseInt(s, 10, 32)` with the explicit bit size instead.
- gosec rule G115 flags these; triage rather than blanket-`nolint`. For
  hot paths a tiny generic helper (`func conv[T, U constraints.Integer]`)
  centralizes the check.
- Durations: `time.Duration(n) * time.Second` where `n` is attacker-supplied
  can overflow int64 — bound first.

## 6. Cryptographic practices: CSPRNG & TLS

### Randomness — `crypto/rand`, never `math/rand`

Security-bearing randomness — tokens, session IDs, password-reset codes, API
keys, salts, nonces, IVs — MUST come from `crypto/rand`. `math/rand` *and*
`math/rand/v2` are PRNGs whose "outputs might be easily predictable regardless
of how it's seeded" (package docs); using either for anything an attacker must
not guess is HIGH (CRITICAL when it gates auth — a guessable reset token is
account takeover).

```go
// BAD — predictable; applies to math/rand and math/rand/v2 alike
token := strconv.FormatInt(mrand.Int63(), 36)

// GOOD — Go 1.24+: ready-made secret string (RFC 4648 base32, ≥128 bits)
token := rand.Text()                  // crypto/rand.Text

// GOOD — raw bytes; Read never errors and always fills b entirely
b := make([]byte, 32)
rand.Read(b)                          // crypto/rand.Read
```

- `crypto/rand.Read`/`Text` cannot hand back a short or weak read — on a
  failing source they crash the program rather than degrade. Don't wrap them in
  `if err != nil` logic that silently falls back to `math/rand`.
- Watch the import line, not just the call: `math/rand.Read` is **deprecated**
  precisely because an unqualified `rand.Read` under `import "math/rand"`
  reads like the crypto one but isn't. Grep imports, then call sites.
- `math/rand/v2` is the right tool — and the better PRNG API — for *non-secret*
  work: jitter, load distribution, sampling, test fixtures. The dividing line
  is "does predictability help an attacker", not "which package is newer".
- Keys, signing, AEAD: use `crypto/*` (`ed25519`, `crypto/ecdsa`,
  `crypto/aes` + `cipher.NewGCM`) drawing from `crypto/rand.Reader`; never
  hand-roll. Password hashing is `golang.org/x/crypto/bcrypt`/`argon2` —
  algorithm choice and parameters are owned by sota-code-security `04`.

### TLS configuration

Go's `crypto/tls` defaults are good (1.22+ defaults to strong suites; 1.24+
enables post-quantum X25519MLKEM768 key exchange, and 1.26 also enables
SecP256r1MLKEM768/SecP384r1MLKEM1024 by default; the legacy GODEBUG opt-outs
`tlsrsakex`/`tls10server`/`tls3des` are slated for removal in 1.27). The main
sins are *downgrades*:

```go
// CRITICAL — disables all certificate verification
cfg := &tls.Config{InsecureSkipVerify: true}

// GOOD — modern floor, otherwise stdlib defaults
cfg := &tls.Config{MinVersion: tls.VersionTLS12} // TLS13 for internal-only
```

- `InsecureSkipVerify: true` is CRITICAL anywhere near production code paths,
  including "temporary" test toggles compiled into the binary. Pinning or
  custom CA? Use `RootCAs` with the CA pool, or `VerifyPeerCertificate` with
  real verification — never blanket skip.
- Don't set `CipherSuites`/`CurvePreferences` manually unless compliance
  forces it — stale hand-picked lists rot; stdlib defaults track best
  practice per release.
- mTLS: server `ClientAuth: tls.RequireAndVerifyClientCert` + `ClientCAs`.
- Plain `http://` to internal services carrying credentials is HIGH unless
  the transport is otherwise authenticated/encrypted (mTLS mesh).

## 7. unsafe and cgo policy

- `unsafe`: forbidden outside a designated, documented, owner-reviewed
  package. Each use carries a comment proving the invariant (per
  `unsafe.Pointer` rules) and a fuzz/race-tested wrapper. Audit any new
  `unsafe.Pointer` arithmetic as HIGH until proven.
- `//go:linkname`, `reflect.SliceHeader`/`StringHeader` (deprecated): treat
  as `unsafe`; 1.20+ `unsafe.String/StringData/Slice/SliceData` are the only
  sanctioned forms.
- cgo: each C dependency reintroduces memory-unsafety, complicates
  cross-compilation and static linking, and bypasses govulncheck's call
  analysis. Require justification (no pure-Go alternative), pin and scan the
  C library separately, and isolate behind one package. `CGO_ENABLED=0` for
  builds unless cgo is required.

## 8. Supply chain & vuln management

- **`govulncheck ./...` in CI** (it's call-graph aware — low false positives;
  also run `govulncheck -mode=binary` on shipped artifacts — it now checks the
  binary's main module too, and `-format sarif` feeds code-scanning UIs).
  Fails the build on findings; triage with documented suppressions, not
  removal of the step.
- **The stdlib itself is the top vuln surface** — H1 2026 alone patched DoS
  CVEs in `crypto/tls` (CVE-2026-32283, TLS 1.3 key-update flood),
  `crypto/x509` (CVE-2026-32280, CVE-2026-27145) and `net/mail`
  (CVE-2026-42499); 1.26.5/1.25.12 (2026-07) fixed CVE-2026-39822 (os.Root
  symlink escape, §4) and CVE-2026-42505 (`crypto/tls` ECH leaked pre-shared
  key identities, de-anonymizing server hostnames). govulncheck only helps
  if the *toolchain* is current: track the monthly patch releases (verify
  the current level at go.dev/doc/devel/release) and rebuild/redeploy on
  security point releases.
- **`go.sum` committed always**; builds verify hashes against it and the
  checksum DB (sum.golang.org), on by default. `GONOSUMDB` and `GONOPROXY`
  exempt matching module patterns from sumdb/proxy; `GOPRIVATE` sets both —
  use `GOPRIVATE=*.corp.example.com` for internal modules and nothing else.
  `GOSUMDB=off`, `GOFLAGS=-mod=mod` in CI, or wildcard `GONOSUMDB=*` disable
  verification repo-wide — HIGH finding. Everything public must flow through
  proxy.golang.org + sumdb verification.
- **Minimal deps philosophy**: stdlib first; `golang.org/x/*` second; each
  third-party module needs maintenance signal (recent releases, issue
  hygiene), a license check, and a reason a 50-line vendored function can't
  replace it. Transitives count: `go mod graph | wc -l` before/after.
- `go mod tidy` enforced in CI (`git diff --exit-code go.mod go.sum` after).
- Pin tool versions via 1.24 `tool` directives in go.mod (`rules/07`) so the
  linter/codegen supply chain is hash-verified too.
- Don't `replace` to forks silently — audit `replace` directives (MEDIUM:
  hidden fork drift; CRITICAL if pointing at an unreviewed repo).
- Secrets: never in code/env-committed files; load via env/secret manager at
  start; `slog.LogValuer` redaction (`rules/04 §5`).

## Audit checklist

```bash
# SQL injection — CRITICAL
grep -rnE '(Sprintf|fmt\.Sprint|\+ ?\w+ ?\+).*((?i)select|insert|update|delete|where)' --include='*.go' .
grep -rnE '(Query|Exec|QueryRow)[^(]*\(("[^"]*"\s*\+|fmt\.Sprintf)' --include='*.go' .
grep -rnE '\.(Raw|Where)\(fmt\.Sprintf' --include='*.go' .       # GORM-style

# Command injection — CRITICAL
grep -rnE 'exec\.Command(Context)?\(\s*"(sh|bash|cmd|powershell)"' --include='*.go' .
grep -rn 'exec.Command' --include='*.go' .                        # verify argv construction per site

# Path traversal — HIGH
grep -rnE 'filepath\.Join\([^)]*(r\.|req\.|input|name|param|id)' --include='*.go' .
grep -rn 'os.Root\|filepath.IsLocal' --include='*.go' .           # mitigations present?
go version   # os.Root containment needs >=1.26.5/1.25.12 — CVE-2026-39822 symlink escape
grep -rnE 'os\.(Open|Create|ReadFile|WriteFile|Remove)' --include='*.go' . # trace path provenance

# TLS — CRITICAL/HIGH
grep -rn 'InsecureSkipVerify' --include='*.go' .
grep -rnE 'MinVersion:\s*tls\.VersionTLS1[01]' --include='*.go' .
grep -rn '"http://' --include='*.go' . | grep -v 'localhost\|127.0.0.1\|test'

# Integer conversion — gosec G115
grep -rnE '\b(int8|int16|int32|uint8|uint16|uint32|uint64|uintptr)\(' --include='*.go' . | grep -vE '(_test|const)'
gosec -include=G115,G118,G201,G202,G204,G304,G401,G402 ./...
# gosec 2.24+ adds G113 (request smuggling via conflicting headers),
# G118 (ctx-propagation goroutine leaks), G408 (SSH PublicKeyCallback bypass)

# CSPRNG misuse — HIGH (security-bearing randomness from a PRNG)
grep -rn 'math/rand' --include='*.go' .                 # any import: verify each call site is non-secret
grep -rnE '\brand\.(Int|Intn|Int31|Int63|Uint|Float|Perm|Shuffle|N)\b' --include='*.go' . # PRNG calls — crypto context?

# Output encoding / XSS — HIGH
grep -rn 'text/template' --include='*.go' . | grep -iv _test   # HTML rendered via text/template?
grep -rnE 'template\.(HTML|JS|URL|CSS|HTMLAttr)\(' --include='*.go' . # escaping bypass — verify sanitized

# unsafe / cgo
grep -rn 'unsafe.Pointer\|go:linkname' --include='*.go' .
grep -rln 'import "C"' --include='*.go' .

# Supply chain
test -f go.sum && echo OK || echo 'MISSING go.sum — HIGH'
grep -E '^replace' go.mod
go env GOFLAGS GONOSUMDB GOSUMDB GOPRIVATE GONOSUMCHECK 2>/dev/null
go mod verify
govulncheck ./...
go mod tidy && git diff --exit-code go.mod go.sum

# Secrets in repo
grep -rnE '(api[_-]?key|secret|password|token)\s*[:=]\s*"[A-Za-z0-9+/_-]{16,}"' --include='*.go' .
```

Severity guide: string-built SQL / `sh -c` with input / InsecureSkipVerify /
`math/rand` for an auth-gating token CRITICAL; traversal-reachable file ops,
disabled sumdb, unchecked narrowing on attacker-controlled sizes, `math/rand`
for other secrets, HTML via `text/template` MEDIUM-to-HIGH; raw error echo to
clients, silent `replace` MEDIUM.
