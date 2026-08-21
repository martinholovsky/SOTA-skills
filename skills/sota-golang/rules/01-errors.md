# 01 — Errors: handling, wrapping, design

Errors are values. They are part of your API surface and your observability
story. Most production incidents in Go services trace back to an error that
was dropped, double-logged, string-matched, or panicked on.

## 1. Handle every error, exactly once

**Handle = one of:** return it (usually wrapped), act on it (retry, fallback,
default), or — only at the top of a call stack — log it and continue/abort.
Doing two of these for the same error is a bug: log-and-return produces
duplicate log lines with no extra information.

```go
// BAD — double handling: caller will log it again
if err != nil {
    log.Printf("query failed: %v", err)
    return err
}

// GOOD — add context, return once; the top-level handler logs
if err != nil {
    return fmt.Errorf("query user %d: %w", id, err)
}
```

Never discard with `_` unless the API genuinely cannot fail in context and you
say why:

```go
// BAD
b, _ := json.Marshal(resp)

// GOOD — justified discard, documented
// Marshal of a struct with no chan/func/cycles cannot fail.
b, _ := json.Marshal(resp) //nolint:errcheck // statically infallible
```

In practice prefer handling anyway; `errcheck` (via golangci-lint) enforces
this and exceptions should be rare and annotated.

`defer f.Close()` on **writes** loses the error that tells you the write
failed (buffered data flushes on close). Capture it:

```go
// GOOD — close error matters for writers
defer func() {
    if cerr := w.Close(); cerr != nil && err == nil {
        err = fmt.Errorf("close %s: %w", path, cerr)
    }
}()
```

For read-only files, `defer f.Close()` discarding the error is acceptable.

## 2. Wrap with %w; add context, not noise

`fmt.Errorf("...: %w", err)` preserves the chain for `errors.Is/As`. Use `%v`
only when you deliberately want to *break* the chain (hiding an internal error
from callers — a real, intentional choice at package boundaries).

Context rules:

- Say what *you* were doing, with identifiers: `"load config %q: %w"`. Do not
  restate what the callee already says (`"failed to open file: open file..."`).
- No `"failed to"` / `"error:"` prefixes — chains read as
  `"a: b: c: underlying"`. Lowercase, no trailing punctuation
  (staticcheck ST1005).
- Wrap at each layer that adds information; pass through (`return err`)
  when you have nothing to add. Mechanical wrapping at every return is noise.

```go
// BAD — no chain (%v), redundant phrasing, capitalized
return fmt.Errorf("Failed to read the file: %v", err)

// GOOD
return fmt.Errorf("read manifest %s: %w", path, err)
```

Multiple causes: `errors.Join(errA, errB)` (Go 1.20+) or
`fmt.Errorf("...: %w; also: %w", e1, e2)`. `errors.Is/As` traverse joined
trees. Typical use: accumulating cleanup errors, validating many fields.

## 3. Inspect with errors.Is / errors.As — never strings

```go
// BAD — breaks on wrapping, wording changes, localization
if strings.Contains(err.Error(), "not found") { ... }
if err == sql.ErrNoRows { ... } // breaks once anything wraps it

// GOOD
if errors.Is(err, sql.ErrNoRows) { ... }

var pgErr *pgconn.PgError
if errors.As(err, &pgErr) && pgErr.Code == pgerrcode.UniqueViolation { ... }

// GOOD — Go 1.26+: errors.AsType[E error](err) (E, bool) is the type-safe,
// faster replacement for errors.As; prefer it on 1.26+ codebases
if pgErr, ok := errors.AsType[*pgconn.PgError](err); ok &&
    pgErr.Code == pgerrcode.UniqueViolation { ... }
```

`==` on errors is only valid where wrapping is impossible (comparing to `nil`,
or inside the package that just created the sentinel). Audit any `err ==`
against exported sentinels as MEDIUM.

Context errors: check `errors.Is(err, context.Canceled)` /
`context.DeadlineExceeded` before counting a failure as a real one — a
canceled request is not a dependency outage; don't page on it.

### 4a. In-band sentinels — Go's are documented, yours are not

Go's stdlib deliberately returns in-band sentinels and **documents them**:
`strings.Index`/`LastIndex` return `-1` when not found (verified, go1.26.5). That is
idiomatic and fine *because the contract is published and every caller is expected
to test it*. The defect is the undocumented one you write yourself — the class is
`sota-architecture` rules/02 §8a.

- `strconv.Atoi("x")` returns `(0, err)` (verified, go1.26.5). The `0` is a perfectly
  ordinary value; the error is the only thing distinguishing it from `Atoi("0")`.
  Dropping `err` converts an out-of-band signal into an in-band one, which is
  precisely what `errcheck` exists to stop.
- Go has no sum type, so the out-of-band alternatives are **comma-ok**
  (`v, ok := m[k]`) or `(T, error)`. Return one of them; a `func f() int` that
  answers `-1` for "no value" has no way to say why.
- `*int` for "optional int" is legal and usually worse than comma-ok — it moves the
  check to a nil dereference and heap-allocates. Prefer `(int, bool)`.
- Audit: `grep -rnE 'return -1|return 0, nil' --include='*.go' .` for producers, then
  the tell that actually finds the bug — a comparison where one side is filtered
  against the sentinel and the other is not.

## 4. Sentinel vs typed vs opaque — choosing the error kind

| Kind | When | Example |
|---|---|---|
| **Opaque** (just `error`) | Caller can only propagate/log. Default. | most internal funcs |
| **Sentinel** (`var ErrX = errors.New`) | Caller branches on *which* condition, no payload needed | `io.EOF`, `sql.ErrNoRows`, `fs.ErrNotExist` |
| **Typed** (struct implementing `error`) | Caller needs structured data from the failure | `*fs.PathError`, validation errors with field names |

Rules:

- Every exported sentinel/type is **API forever**. Export the minimum; start
  opaque, promote to sentinel/typed when a real caller needs to branch.
- Sentinels: `Err` prefix, `var ErrQuotaExceeded = errors.New("quota exceeded")`.
  Wrap them when returning: `fmt.Errorf("user %d: %w", id, ErrQuotaExceeded)`.
- Typed errors: name ends in `Error`, pointer receiver, and **return the
  concrete pointer only into an `error` variable immediately** — a typed nil
  pointer stored in an `error` interface is non-nil:

```go
// BAD — classic typed-nil bug: returns non-nil error interface
func do() *QueryError { ... return nil }
var err error = do() // err != nil even though pointer is nil!

// GOOD — functions return `error`, not concrete error types
func do() error {
    if bad {
        return &QueryError{Query: q, Err: cause}
    }
    return nil
}
```

- Implement `Unwrap() error` (or `Unwrap() []error`) on wrapper types so
  `errors.Is/As` see through them.
- Libraries: prefer behavior interfaces over exported types when feasible
  (`interface{ Timeout() bool }` à la `net.Error`), so callers depend on
  capability, not identity.

## 5. No panic for control flow

`panic` means "programmer bug, state is corrupt, crashing is correct":
impossible switch cases, broken invariants, failed init of must-exist state.
It is never a substitute for returning an error on input, I/O, network, parse,
or not-found conditions.

```go
// BAD — user input panics the server
func ParseLevel(s string) Level {
    l, ok := levels[s]
    if !ok { panic("bad level: " + s) }
    return l
}

// GOOD
func ParseLevel(s string) (Level, error) {
    l, ok := levels[s]
    if !ok {
        return 0, fmt.Errorf("unknown level %q", s)
    }
    return l, nil
}
```

Legitimate panic patterns:

- `MustCompile`-style helpers for package-level init with constant input:
  `var pathRe = regexp.MustCompile(...)`. Write your own `MustX` only for
  init-time constants, never runtime data.
- `panic` across goroutines is fatal: **a panic in a goroutine you spawned
  kills the whole process** regardless of recovers elsewhere. Any goroutine
  running third-party or panic-capable code needs its own deferred recover
  (errgroup does NOT recover for you; `golang.org/x/sync/errgroup` ≥ v0.11
  still propagates panics by re-panicking in `Wait`).
- HTTP: `net/http` recovers per-request panics by default but the response is
  broken; middleware should recover, log with stack
  (`debug.Stack()`), and return 500. Recover converts to error at the
  boundary; it never resumes business logic.

`recover()` only works in a deferred function in the same goroutine. Audit any
`recover` outside `defer` as dead code (vet catches some of these).

## 6. Error flow patterns

- **Guard clauses, happy path left-aligned.** `if err != nil { return ... }`
  immediately; no `else` after a return.
- **Don't pre-declare `var err error`** and reuse across unrelated calls;
  shadowing bugs (`:=` in an inner scope silently ignoring the outer err)
  are common — `go vet` + golangci-lint `govet` shadow check help.
- **Errors in loops**: decide explicitly — fail fast (`return` first error),
  or collect (`errors.Join`) and continue. Comment which and why.
- **errors as part of concurrency**: never send on an error channel without a
  receiver guarantee; prefer `errgroup` which does this correctly
  (see `rules/03`).
- **Don't log below the top.** Libraries return errors; binaries log them
  once, at the handler/main level, with `slog` and the full chain
  (`slog.Any("err", err)` or `"err", err` — `%+v` style stacks need
  a wrapper lib; stdlib chains carry context strings instead of stacks).
- **main() pattern**:

```go
func main() {
    if err := run(context.Background(), os.Args, os.Stdout); err != nil {
        fmt.Fprintln(os.Stderr, err)
        os.Exit(1)
    }
}
```

`run` returns errors; `main` is the only place that exits. `os.Exit` skips
defers — never call it (or `log.Fatal`) outside `main`.

## 7. Library vs application error policy

- **Libraries**: no logging, no `os.Exit`/`log.Fatal`, no leaking
  implementation errors as API (wrap third-party errors with `%v` or your own
  type at the boundary if callers shouldn't depend on them). Document which
  sentinels/types you return.
- **Applications**: map errors to user/transport meaning in ONE place —
  e.g. an HTTP error mapper translating `ErrNotFound`→404,
  validation type→400, default→500 + log. Scattered status-code decisions
  drift.

```go
// GOOD — single translation point
func httpError(w http.ResponseWriter, err error) {
    switch {
    case errors.Is(err, ErrNotFound):
        http.Error(w, "not found", http.StatusNotFound)
    case errors.As(err, new(*ValidationError)):
        http.Error(w, err.Error(), http.StatusBadRequest)
    default:
        slog.Error("internal error", "err", err)
        http.Error(w, "internal error", http.StatusInternalServerError)
    }
}
```

Never echo internal error chains to external clients (information disclosure —
see `rules/05`).

## Audit checklist

Run from repo root; verify each hit manually.

**In-band sentinels — a value standing in for absence** (§4a). Go's own `-1` from
`strings.Index` is documented and fine when tested immediately; yours is not:

```bash
grep -rnE 'return -1$|return -1,' --include='*.go' .        # producer — prefer (T, bool) comma-ok
grep -rnE ':?= .*strconv\.Atoi\(' --include='*.go' . | grep -v 'err'   # the 0 is in-band if err is dropped
```

```bash
# Discarded errors (also rely on errcheck via golangci-lint)
grep -rnE '^\s*[a-zA-Z_].*,\s*_\s*(:?=).*\(' --include='*.go' . | grep -v _test.go
grep -rn '_ = ' --include='*.go' . | grep -vE '(test|//)'

# String matching on errors — MEDIUM+
grep -rnE 'strings\.(Contains|HasPrefix|HasSuffix)\(\s*err\.Error\(\)' --include='*.go' .
grep -rn '\.Error() ==' --include='*.go' .

# == comparison against sentinels (should be errors.Is) — MEDIUM
grep -rnE 'err\s*[!=]=\s*(sql\.ErrNoRows|io\.EOF|os\.ErrNotExist|context\.(Canceled|DeadlineExceeded))' --include='*.go' .

# %v wrapping where %w likely intended (manual review)
grep -rnE 'fmt\.Errorf\([^)]*%v[^)]*err\s*\)' --include='*.go' .

# Panics outside main/init/Must/tests — HIGH if reachable from input
grep -rn 'panic(' --include='*.go' . | grep -vE '(_test\.go|Must|init\()'

# log.Fatal / os.Exit outside main package — HIGH in libraries
grep -rnE '(log\.Fatal|os\.Exit)' --include='*.go' . | grep -v 'main\.go'

# Error strings: capitalized or "failed to" noise — INFO/LOW (ST1005)
grep -rnE 'errors\.New\("[A-Z]|fmt\.Errorf\("[A-Z]' --include='*.go' .
grep -rn 'failed to' --include='*.go' . | grep -E '(errors\.New|fmt\.Errorf)'

# Typed-nil hazard: functions returning concrete error pointer types
grep -rnE 'func .*\) \*\w+Error( |$)' --include='*.go' .

# recover outside defer; missing Unwrap on wrapper types (manual)
grep -rn 'recover()' --include='*.go' .
grep -rln 'type .*Error struct' --include='*.go' . | xargs grep -L 'func (.*) Unwrap()'

# Tooling
go vet ./...
golangci-lint run --enable-only errcheck,errorlint,err113,wrapcheck,nilerr ./...
staticcheck ./...   # ST1005 error strings, SA4006 unused err, SA1019
```

Severity guide: string-matched errors MEDIUM (HIGH if driving retry/billing
logic); dropped error on write/commit path HIGH; panic reachable from external
input HIGH; double logging LOW; phrasing INFO.
