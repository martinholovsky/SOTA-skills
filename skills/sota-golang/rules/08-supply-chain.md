# 08 — Supply Chain & Vulnerability Management

Split out of rules/05 (formerly section 8) on 2026-09-25, when rules/05 reached the 500-line
cap; the section is now §1. Scope: modules, the checksum database, vulnerability scanning,
code that runs at build time, adopting a dependency, and GODEBUG overrides (§2).

## 1. Supply chain & vuln management

- **`govulncheck ./...` in CI** (it's call-graph aware — low false positives;
  also run `govulncheck -mode=binary` on shipped artifacts — it now checks the
  binary's main module too, and `-format sarif` feeds code-scanning UIs).
  Fails the build on findings; triage with documented suppressions, not
  removal of the step.
- **The stdlib itself is the top vuln surface** — H1 2026 alone patched DoS
  CVEs in `crypto/tls` (CVE-2026-32283, TLS 1.3 key-update flood),
  `crypto/x509` (CVE-2026-32280, CVE-2026-27145) and `net/mail`
  (CVE-2026-42499); 1.26.5/1.25.12 (2026-07) fixed CVE-2026-39822 (os.Root
  symlink escape, rules/05 §4) and CVE-2026-42505 (`crypto/tls` ECH leaked pre-shared
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
- **Minimal deps philosophy**: stdlib first; `golang.org/x/*` second; each third-party
  module needs maintenance signal (recent releases, issue hygiene), a license check, and a
  reason a 50-line vendored function can't replace it. Transitives count: `go mod graph | wc -l`
  before/after. Selection checks before `go get`, and library insecure defaults: `rules/07 §4`.
- **Audit side — already-landed deps**: `go mod why -m <module>` prints
  `(main module does not need module …)` for an unreached one — verbatim, exit 0
  — but its graph includes tests of reachable packages (`-vendor` excludes tests
  *of dependencies*; your own test-only deps still read as reached). A tool's
  silence is not proof — the sweep, the deletion proof, and the leverage-ratio
  and upstream-health checks are `sota-devsecops` rules/10.
- `go mod tidy` enforced in CI (`git diff --exit-code go.mod go.sum` after).
- Pin tool versions via 1.24 `tool` directives in go.mod (`rules/07`) so the
  linter/codegen supply chain is hash-verified too.
- **Build-time code execution.** The toolchain is designed so fetching or building a module
  never runs it — Go has no install hooks. What *does* run code: every `//go:generate` line
  (only on an explicit `go generate`; a `go run pkg@ver` there fetches and runs outside
  go.mod, so use a `tool` directive + `go tool`), `go tool`/`go test all` (dependency code),
  cgo (`#cgo` flags are allowlisted, but `CGO_*FLAGS_ALLOW`, `CGO_*FLAGS` env and `-toolexec`
  bypass it; `#cgo pkg-config:` runs `PKG_CONFIG`), `GOVCS` beyond its `public:git|hg,private:all`
  default, and `GOTOOLCHAIN=auto` (default) running the compiler named by go.mod/go.work.
  Diff generate lines and tool bumps per PR; CODEOWNERS on go.mod, go.work, Makefile, CI and
  `//go:generate` files, AI-authored too; run generate/tool steps in a job with no secrets.
  (OWASP: CI/CD Security; Software Supply Chain Security; NPM Security cheat sheets.)
- Don't `replace` to forks silently — audit `replace` directives (MEDIUM:
  hidden fork drift; CRITICAL if pointing at an unreviewed repo).
- Secrets: never in code/env-committed files; load via env/secret manager at
  start; `slog.LogValuer` redaction (`rules/04 §5`).

## 2. GODEBUG: security behaviour set by go.mod

GODEBUG settings switch stdlib behaviour back to an older, often weaker default, and three
of the four places that set them are source files (go.dev/doc/godebug; `$GOROOT/doc/godebug.md`):

- **The `go` line itself.** Defaults follow the main module's (or `go.work`'s) language
  version, so a new toolchain building `go 1.24` keeps pre-1.25 behaviour: container-aware
  GOMAXPROCS stays off (`containermaxprocs=0`, `updatemaxprocs=0`) and, measured on go1.27.1,
  `tlssecpmlkem=0` and `x509sha256skid=0` too. Settings added in security releases are the
  exception — they apply at every language version.
- **`godebug` blocks in go.mod/go.work** (1.23+; only the main module's count, and
  `default=go1.X` pulls in a whole older set) and **`//go:debug` lines** above `package main`.
- **`GODEBUG=` in the environment** — Dockerfiles, manifests, systemd units, CI.

Treat as findings any value that restores a weaker behaviour — e.g. `tlssha1=1`,
`tlsmlkem=0`/`tlssecpmlkem=0`, `x509negativeserial=1`, `x509usepolicies=0`,
`httpmuxgo121=1` — and note that `tarinsecurepath`/`zipinsecurepath` default to the
permissive `1`: `=0` is the hardening. Settings removed in 1.27 (`tlsrsakex`, `tls10server`,
`tls3des`, …) set to their old value now fail the build from go.mod or `//go:debug`, and
from the environment abort the binary at startup with `fatal error: removed GODEBUG`
(measured, go1.27.1) — so a stale deploy-file entry is an outage on upgrade. Ground truth:
`go version -m <bin>` prints a binary's `DefaultGODEBUG`; `go list -f '{{.DefaultGODEBUG}}'`
prints it for a main package — empty means current defaults.

## Audit checklist

- [ ] **Supply chain** — `test -f go.sum && echo OK || echo 'MISSING go.sum — HIGH'` ;
      `grep -E '^replace' go.mod` ;
      `go env GOFLAGS GONOSUMDB GOSUMDB GOPRIVATE GOPROXY GOINSECURE` (flag `GOPROXY` of
      `direct`/`off` for public modules, any `GOINSECURE`, a wildcard `GONOSUMDB`, `GOSUMDB=off`,
      `GOFLAGS=-mod=mod` in CI — the §1 list) ; `go mod verify` ;
      `govulncheck ./...` ; `go mod tidy && git diff --exit-code go.mod go.sum`
- [ ] **Build-time code execution (§1) — MEDIUM, HIGH if CI secrets are in scope** —
      `grep -rnE '^//go:generate[[:space:]]+(go run [^ ]+@|sh |bash |curl |wget )' --include='*.go' .` ;
      `grep -rnE 'CGO_[A-Z]+FLAGS_ALLOW|GOVCS.*[*c]:all|-toolexec' . | grep -v '\.go:'` ;
      no CODEOWNERS line for go.mod / CI files = finding
- [ ] **GODEBUG overrides that weaken security defaults (§2) — HIGH for TLS/x509, MEDIUM
      otherwise** — `go list -f '{{.ImportPath}} {{.DefaultGODEBUG}}' ./...` (main packages;
      read every non-empty value) ;
      `grep -rnE '^godebug|^//go:debug|GODEBUG|(tlssha1|tlsmlkem|tlssecpmlkem|x509[a-z0-9]+|httpmuxgo121|(tar|zip)insecurepath)=' --include='go.mod' --include='go.work' --include='*.go' --include='Dockerfile*' --include='*.y*ml' --include='*.env' --include='*.service' --include='Makefile' .`
      ; `grep -E '^go ' go.mod` (below the toolchain's minor = older GODEBUG defaults)
