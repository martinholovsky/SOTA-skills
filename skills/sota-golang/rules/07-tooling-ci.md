# 07 — Tooling, testing, CI, go.mod hygiene

A Go repo without lint+race+vuln gates accumulates every defect class in this
skill silently. Tooling is cheap; retrofitting it is not. This file defines
the SOTA gate set and test discipline.

## 1. CI gate set (minimum viable, in order)

```bash
gofumpt -l -d .                          # formatting (superset of gofmt)
go vet ./...
golangci-lint run                        # curated config below
go test -race -shuffle=on ./...          # shuffle kills inter-test ordering deps
go test -race -coverprofile=cover.out ./...
govulncheck ./...
go mod tidy && git diff --exit-code go.mod go.sum
go build ./...                           # catches main-package breakage tests miss
```

Pin tool versions (see §6); cache `~/go/pkg/mod` and golangci-lint cache.
A repo missing `-race` or govulncheck in CI: HIGH audit finding.

On toolchain upgrades, run Go 1.26's revamped `go fix` — it now applies
"modernizer" fixers (built on the vet analysis framework) that rewrite code
to current idioms; review the diff like any refactor.

## 2. golangci-lint curated config

Don't enable-all (noise kills adoption); don't run bare defaults (misses too
much). Curated `.golangci.yml` (v2 schema):

```yaml
version: "2"
linters:
  default: none
  enable:
    # correctness
    - govet          # includes shadow-ish checks, lostcancel, copylocks
    - staticcheck    # the big one: SA bugs, ST style, S simplifications
    - errcheck       # unchecked errors
    - errorlint      # %w misuse, err == comparisons
    - nilerr         # return nil after err != nil
    - bodyclose      # unclosed http response bodies
    - rowserrcheck   # rows.Err() after iteration
    - sqlclosecheck  # rows/stmt Close
    - noctx          # http requests without context
    - contextcheck   # ctx not propagated
    - containedctx   # ctx stored in struct
    - copyloopvar    # obsolete loop-var copies (go >= 1.22)
    - gosec          # security incl. G115
    - musttag        # struct tags on (un)marshaled types
  settings:
    errcheck:
      check-type-assertions: true
    gosec:
      excludes: []        # triage per-finding with #nosec + justification
    staticcheck:
      checks: ["all"]
formatters:
  enable: [gofumpt, goimports]
```

Add per-repo: `prealloc`/`perfsprint` (perf-sensitive), `revive` (style
depth), `exhaustive` (enum switches), `gomodguard` (dependency policy).
Inline suppressions require a reason:
`//nolint:gosec // G304: path validated by os.Root above` — bare `//nolint`
is itself a LOW finding.

`staticcheck` ships inside golangci-lint; running the standalone binary too
is fine but redundant. `gofumpt` over `gofmt`: stricter, zero-config,
no debates.

Version notes (2026-06): golangci-lint v2.9.0+ is required for Go 1.26
support (use the latest stable). `noctx` now also flags missing-ctx `log/slog`,
`os/exec` and `crypto/tls` call sites, not just HTTP requests; `errcheck`
v1.10+ excludes `crypto/rand.Read` by default (it never fails).

## 3. Test discipline

**Table tests** are the default shape; name cases, use subtests:

```go
func TestParseLevel(t *testing.T) {
    t.Parallel()
    tests := map[string]struct {
        in      string
        want    Level
        wantErr error
    }{
        "info":    {in: "info", want: LevelInfo},
        "unknown": {in: "nope", wantErr: ErrBadLevel},
    }
    for name, tt := range tests {
        t.Run(name, func(t *testing.T) {
            t.Parallel()
            got, err := ParseLevel(tt.in)
            if tt.wantErr != nil {
                if !errors.Is(err, tt.wantErr) {
                    t.Fatalf("err = %v, want %v", err, tt.wantErr)
                }
                return
            }
            if err != nil { t.Fatal(err) }
            if got != tt.want { t.Errorf("got %v, want %v", got, tt.want) }
        })
    }
}
```

- **`t.Parallel()` correctness**: with `go.mod` ≥1.22 the loop-var capture
  trap is gone; on older modules every parallel subtest needs `tt := tt`.
  Parallel subtests + shared fixtures = races — fixtures must be per-subtest
  or immutable. `t.Setenv`/`t.Chdir` are incompatible with `t.Parallel`
  (panics — by design).
- Use `t.Helper()` in assertion helpers, `t.Cleanup` over manual defers (runs
  even on Fatal, ordered LIFO, works with subtests), `t.TempDir()` for files,
  `t.Context()` (1.24+) for ctx.
- Test behavior through exported APIs (`package foo_test`); reaching into
  internals couples tests to refactors. `export_test.go` for the rare
  internal hook.
- Assertions: stdlib comparisons + `github.com/google/go-cmp` for deep diffs
  (`cmp.Diff(want, got)` in the error message). testify is acceptable if
  already in-house; don't mix styles.
- **No time.Sleep synchronization** in tests — flaky by construction
  (MEDIUM). Use channels, fakes for clocks, or `testing/synctest` (1.25):
  `synctest.Test(t, func(t *testing.T){ ... })` runs goroutines in a bubble
  with virtual time — `time.Sleep` completes instantly and deterministically.

**Integration tests — testcontainers** over mocks for DB/queue behavior:

```go
func TestUserStore(t *testing.T) {
    if testing.Short() { t.Skip("integration") }
    ctx := t.Context()
    pg, err := postgres.Run(ctx, "postgres:17-alpine",
        postgres.WithDatabase("app"), postgres.BasicWaitStrategies())
    testcontainers.CleanupContainer(t, pg)
    if err != nil { t.Fatal(err) }
    // connect, migrate, exercise the real store
}
```

Gate with `testing.Short()` or build tags so `go test ./...` stays fast;
CI runs both tiers. Mock at *your* consumer-side interfaces (hand-written
fakes or `moq`/`mockgen` if codegen helps) — never mock `*sql.DB`.

**Golden files** for large/structured outputs (rendered templates, JSON,
codegen): store under `testdata/` (toolchain-ignored), compare bytes, update
via flag:

```go
var update = flag.Bool("update", false, "rewrite golden files")

golden := filepath.Join("testdata", t.Name()+".golden")
if *update { os.WriteFile(golden, got, 0o644) }
want, _ := os.ReadFile(golden)
if diff := cmp.Diff(string(want), string(got)); diff != "" {
    t.Errorf("mismatch (-want +got):\n%s", diff)
}
```

Review golden diffs like code — `-update` runs that get rubber-stamped make
the tests decorative.

**Fuzzing** (native, 1.18+) for every parser/decoder/validator that touches
untrusted bytes:

```go
func FuzzParseManifest(f *testing.F) {
    f.Add([]byte(`{"v":1}`))                  // seed corpus
    f.Fuzz(func(t *testing.T, data []byte) {
        m, err := ParseManifest(data)
        if err != nil { return }              // invalid input may error — must not panic
        round, err := m.MarshalBinary()       // invariants: roundtrip, no panic, bounded output
        if err != nil { t.Fatal(err) }
        _ = round
    })
}
```

`go test -fuzz=FuzzParseManifest -fuzztime=60s` in a periodic CI job; commit
found crashers from `testdata/fuzz/` as permanent regression seeds. Seeds run
on every normal `go test`.

Coverage: track trend, don't worship a number; `-coverprofile` +
`go tool cover -func` in CI. Untested error paths matter more than the
percentage.

## 4. go.mod hygiene

```
module github.com/org/app

go 1.25.0          // language version (1.26's `go mod init` writes the previous minor by design)
toolchain go1.26.5 // exact toolchain: reproducible builds across dev/CI (pin the current patch — verify at go.dev/doc/devel/release)

require ( ... )

tool (             // 1.24+: tool dependencies, versioned & sum-verified
    golang.org/x/tools/cmd/stringer
    github.com/sqlc-dev/sqlc/cmd/sqlc
)
```

- **`go` directive** is semantic, not decorative: it selects language
  behavior per-module (loop-var scoping needs ≥1.22 — `rules/03 §5`). Keep it
  within two releases of current (only the last two minors get security
  fixes — an EOL `go` directive with no newer toolchain is a MEDIUM finding).
- **`toolchain` directive** pins the exact compiler; CI and developers build
  identically. Update deliberately (Dependabot/Renovate handle it).
- **`tool` directives (1.24+)** replace the `tools.go` blank-import hack and
  ad-hoc `go install tool@version` drift: `go get -tool <pkg>`, run via
  `go tool stringer`. Tools become sum-verified supply chain (`rules/05 §8`).
  Audit repos still using floating `go install foo@latest` in CI: MEDIUM.
- `go mod tidy` clean in CI (diff check); `go mod verify` on release builds.
- Versioning: tag semver; v2+ requires the `/v2` module path suffix —
  retagging without it breaks consumers. Avoid `v0` forever for published
  libraries; commit to v1 once the API settles.
- Workspaces (`go.work`) for local multi-module dev only — **never commit
  go.work to a library repo**; it's developer-machine state (`.gitignore` it).
- `replace` directives in committed go.mod: temporary at best, document an
  expiry; they don't apply to downstream consumers of a library (so a library
  relying on `replace` is broken for users — HIGH).

## 5. Reproducible builds & release

- Build with `-trimpath`; inject version via
  `-ldflags="-X main.version=$(git describe --tags)"` or read
  `debug.ReadBuildInfo()` (embeds VCS revision automatically).
- `CGO_ENABLED=0` for static binaries unless cgo is required (`rules/05 §7`);
  distroless/scratch base images.
- `go version -m ./bin/app` audits any binary's module versions and build
  settings — use it on artifacts you didn't build.

## Audit checklist

```bash
# CI gates present? Inspect workflow files
grep -rnE '(go test|race|govulncheck|golangci-lint|staticcheck|gofumpt)' .github/workflows/ Makefile* 2>/dev/null
grep -rn 'test -race' .github/ Makefile* 2>/dev/null || echo 'NO RACE IN CI — HIGH'

# Lint config exists and is curated (not empty, not enable-all)
ls .golangci.yml .golangci.yaml 2>/dev/null
grep -n 'enable-all\|disable-all' .golangci.y*ml 2>/dev/null

# Suppression hygiene
grep -rn 'nolint' --include='*.go' . | grep -v '//' | head            # malformed
grep -rnE '//nolint(:\w+)?$' --include='*.go' .                       # no justification — LOW
grep -rn '#nosec' --include='*.go' .                                  # justify each

# go.mod hygiene
grep -E '^(go|toolchain) ' go.mod         # version current? toolchain pinned?
grep -A5 '^tool' go.mod                   # 1.24 tool directives in use?
grep -rn 'tools.go' . 2>/dev/null         # legacy pattern — migrate (LOW)
grep -rn 'go install .*@latest' .github/ Makefile* 2>/dev/null   # floating tools — MEDIUM
git ls-files | grep 'go.work$' && echo 'go.work committed — check intent'
grep -E '^replace' go.mod

# Test quality
grep -rln 'func Test' --include='*_test.go' . | wc -l
grep -rn 't.Parallel' --include='*_test.go' . | wc -l
grep -rn 'time.Sleep' --include='*_test.go' .                         # flaky sync — MEDIUM
grep -rln 'func Fuzz' --include='*_test.go' .                         # parsers fuzzed?
ls testdata/fuzz 2>/dev/null                                          # crash corpus committed?
grep -rn 'testcontainers' go.mod
go test -shuffle=on ./...                                             # ordering deps?
go test -race -count=3 ./...

# Formatting drift
gofumpt -l . | head
goimports -l . | head

# Toolchain & vuln state
go version; go env GOTOOLCHAIN
govulncheck ./...
```

Severity guide: no `-race`/govulncheck in CI HIGH; library shipping `replace`
HIGH; EOL toolchain MEDIUM; floating tool versions MEDIUM; sleep-synced or
order-dependent tests MEDIUM; missing table tests / `t.Parallel` / golden
review discipline LOW.
