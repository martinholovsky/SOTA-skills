---
name: sota-golang
description: State-of-the-art Go engineering rules (2026 baseline, Go 1.24+) that Claude applies when writing new Go code or auditing existing Go code. Covers error handling, interface/package design, goroutine and channel correctness, net/http hardening, security (SQL, exec, path traversal, CSPRNG, TLS, supply chain), performance (pprof, allocations, GC, PGO), and tooling/CI. Trigger keywords - Go, golang, goroutine, channel, go.mod, errgroup, context.Context, pprof, govulncheck, net/http, slog. Use for BOTH building Go services/libraries/CLIs and reviewing or auditing Go codebases.
---

# SOTA Go (2026)

Expert-level rules for producing and auditing production Go. Baseline language
version: Go 1.24+ (loop-var scoping from 1.22, `b.Loop`/`os.Root`/tool
directives from 1.24, `testing/synctest` and container-aware GOMAXPROCS from
1.25, `errors.AsType` and the default-on Green Tea GC from 1.26 — released
2026-02 — noted where relevant). Every rule states the *why*; every rules file
ends with an audit checklist of grep/vet/lint patterns.

## Purpose

Two consumers, one source of truth:

- **BUILD mode** — generating new Go code: follow the rules as defaults, not
  suggestions. Deviate only with an explicit comment justifying it.
- **AUDIT mode** — reviewing existing Go code: hunt violations using the audit
  checklists, classify by severity, report in the finding format below.

## BUILD mode

1. Before writing code, read the rules files relevant to the task (see index).
   A service touching HTTP + DB + goroutines needs `03`, `04`, `05`.
2. Apply the **top-10 non-negotiables** (below) unconditionally.
3. New modules: `go mod init` with a real module path; since 1.26 it writes
   the previous minor as the `go` directive (e.g. `go 1.25.0`) for ecosystem
   compatibility — keep that unless you need newer language features; pin the
   `toolchain` directive to the current patch release. Add `golangci-lint`
   config and a CI step
   running `go vet`, `golangci-lint run`, `go test -race ./...`,
   `govulncheck ./...` from day one (see `rules/07`).
4. Prefer stdlib. Each dependency must earn its place (see `rules/05` supply
   chain section).
5. Write table tests alongside the code, not after. Exported behavior gets a
   test; concurrency gets a `-race` test; parsers get a fuzz target.
6. When generating code that violates a rule for a legitimate reason (e.g.
   `sync.Pool` complexity, `unsafe`), leave a `// NOTE(sota):` comment
   explaining the trade-off so auditors don't flag it blind.

## AUDIT mode

Work through each relevant rules file's audit checklist against the target
repo. Run the listed grep/vet/lint commands; confirm each hit manually before
reporting (greps are recall-oriented, expect false positives).

### Severity conventions

| Severity | Meaning | Examples |
|---|---|---|
| **CRITICAL** | Exploitable or guaranteed-incorrect in production | SQL built with `fmt.Sprintf`, command injection via `sh -c`, unbounded goroutine leak on hot path, `InsecureSkipVerify: true`, data race confirmed by `-race` |
| **HIGH** | Likely production incident or security weakness | Missing `http.Server` timeouts, no ctx cancellation on blocking goroutine, unchecked integer truncation on attacker input (G115), `resp.Body` never closed, panic for control flow in a server |
| **MEDIUM** | Correctness/maintainability hazard, latent bug | Error strings compared with `strings.Contains`, context stored in struct, `time.After` in a loop, map writes without lock under suspected concurrency, missing `errors.Is/As` |
| **LOW** | Idiom/perf debt, works but wrong shape | Returning interfaces, `util` package dumps, missing preallocation on hot path, non-table tests, no `t.Parallel` |
| **INFO** | Style, doc, or hygiene note | Naming, missing doc comments, gofumpt drift |

### Finding format

```
[SEVERITY] file.go:LINE — short title
  Rule: rules/NN-name.md § section
  Evidence: the offending line(s), verbatim
  Impact: one sentence — what goes wrong, under what conditions
  Fix: concrete replacement code or action
```

Group findings by severity, CRITICAL first. End the audit with: counts per
severity, the three highest-leverage fixes, and which checklists were run.

## Rules index

| File | Read this when... |
|---|---|
| `rules/01-errors.md` | Writing/reviewing any error path: wrapping with `%w`, `errors.Is/As`, sentinel vs typed errors, panic/recover policy, error API design for libraries vs apps |
| `rules/02-design.md` | Designing packages or APIs: interface placement and size, package layout and `internal/`, naming, zero values, generics restraint, embedding, functional options, `context.Context` discipline |
| `rules/03-concurrency.md` | Anything with `go`, `chan`, `sync`, or `select`: goroutine lifecycle ownership, leak catalog, errgroup fan-out, channels-vs-mutex decision, race patterns, worker pools, semaphores, `time.After` traps |
| `rules/04-http-services.md` | Building or auditing HTTP servers/clients: all five server timeouts, client timeouts and body hygiene, connection reuse, graceful shutdown, middleware, `slog` structured logging, request-scoped values |
| `rules/05-security.md` | Any input crossing a trust boundary: SQL parameterization, `os/exec` safety, path traversal and `os.Root`, integer overflow (G115), output encoding (`html/template`), CSPRNG (`crypto/rand` vs `math/rand`), TLS config, `unsafe`/cgo policy, govulncheck, supply chain and go.sum |
| `rules/06-performance.md` | Latency/memory work: pprof workflow, `testing.B` + `b.Loop`, allocation reduction, `strings.Builder`, `sync.Pool` criteria, escape analysis, GOGC/GOMEMLIMIT, PGO |
| `rules/07-tooling-ci.md` | Setting up or auditing CI and tests: golangci-lint curated config, staticcheck/gofumpt/vet, table tests, `t.Parallel` correctness, testcontainers, golden files, fuzzing, go.mod hygiene and `tool` directives. **Test *strategy* — suite shape, TDD, doubles, test data, flake policy — lives in `sota-testing`; load it for any build that writes logic. This file owns Go runner mechanics only.** |

## Top-10 non-negotiables

1. **Every error is handled or wrapped with `%w` and context** — never
   discarded with `_`, never logged-and-ignored on a path that must abort.
   Compare with `errors.Is`/`errors.As`, never string matching. (`rules/01`)
2. **No panics for control flow.** `panic` is for unreachable programmer
   errors only; servers recover at goroutine boundaries and log. (`rules/01`)
3. **Every goroutine has an owner and a guaranteed exit path** — tied to a
   `context.Context`, a closed channel, or a `WaitGroup`/`errgroup` join. If
   you can't say how it stops, don't start it. (`rules/03`)
4. **`go test -race ./...` in CI, always.** A race detector failure is a
   CRITICAL finding, not flaky-test noise. (`rules/03`, `rules/07`)
5. **`http.Server` sets `ReadHeaderTimeout`, `ReadTimeout`, `WriteTimeout`,
   `IdleTimeout`; clients set timeouts and `defer resp.Body.Close()` with
   drain.** Default zero timeouts are a DoS. (`rules/04`)
6. **SQL only via parameterized queries** (`database/sql` placeholders, pgx,
   or sqlc-generated code). String-built SQL is CRITICAL, no exceptions for
   "internal" values. (`rules/05`)
7. **`os/exec` with argv lists, never `sh -c` with interpolated input;
   file paths validated against a root** (`os.Root` on 1.24+, else
   `filepath.Clean` + prefix check after resolving symlinks). (`rules/05`)
8. **`context.Context` is the first parameter, flows down, is never stored in
   a struct**, and carries only request-scoped metadata — never dependencies.
   (`rules/02`)
9. **Accept interfaces, return structs; define interfaces at the consumer,
   keep them small.** No premature interfaces "for mocking". (`rules/02`)
10. **`govulncheck ./...` and `golangci-lint` gate CI**; `go.sum` committed;
    dependencies minimal and justified. (`rules/05`, `rules/07`)
