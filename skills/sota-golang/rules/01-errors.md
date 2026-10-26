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
`strings.Index`/`LastIndex` return `-1` when not found (verified, go1.26.5 and go1.27.1). That is
idiomatic and fine *because the contract is published and every caller is expected
to test it*. The defect is the undocumented one you write yourself — the class is
[`sota-architecture` rules/02](../../sota-architecture/rules/02-domain-modeling-and-boundaries.md) §8a.

- `strconv.Atoi("x")` returns `(0, err)` (verified, go1.26.5 and go1.27.1). The `0` is a perfectly
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
  *inside* the function. errgroup does NOT recover for you: `golang.org/x/sync`
  v0.14–v0.15 briefly re-panicked in `Wait`, but v0.16+ reverted that, so a
  panic in a `g.Go` func crashes the process (read `errgroup.go` at your
  pinned version — its comment on `Go` explains why propagation was dropped).
- HTTP: `net/http` recovers per-request panics by default but the response is
  broken; middleware should recover, log with stack
  (`debug.Stack()`), and return 500. Recover converts to error at the
  boundary; it never resumes business logic.

`recover()` only works in a deferred function in the same goroutine. Audit any
`recover` outside `defer` as dead code (vet catches some of these).

**Failures `recover` never sees.** These end the process and every connection on it, and no
middleware `recover` runs: runtime `fatal error`s, plus a panic in a goroutine with no recover of its own:

- goroutine stack past `runtime/debug.SetMaxStack` (default 1 GB on 64-bit, 250 MB on 32-bit),
  which is where unbounded recursion over nested input ends;
- concurrent map read and write ([rules/03](03-concurrency.md) §5), and `Unlock` of an unlocked
  `sync.Mutex`;
- a panic in a child goroutine with no deferred recover of its own (above);
- `make([]T, n)`: an out-of-range `n` (negative, or past the limit) is a recoverable panic, but a
  legal `n` the runtime cannot reserve is `fatal error: out of memory`. Overcommit may let it
  succeed and fail later. **Cap `n` against a constant before `make`**, never after.

So the limits come **before** allocation and recursion. Bound bytes with `http.MaxBytesReader`
([rules/04](04-http-services.md)). Bound every length read from the input before `make`. Give
every recursive descent you write a depth parameter, and reject at a stated limit. The stdlib
decoders cap depth for you, but not at your limit. `encoding/json` hard-codes 10000 nesting levels
(`const maxNestingDepth` in both v1's `scanner.go` and v2's `jsontext/state.go`, read at go1.27.1).
**Neither v1 nor `encoding/json/v2` has a depth option**, and `jsontext.WithMaxDepth` does not
exist. `encoding/xml` caps unmarshal depth at 10000 (5000 on wasm). `encoding/gob`'s limit only
covers skipping ignored fields. For a lower JSON limit, pre-scan the tokens: v1 `Decoder.Token`,
or v2 `jsontext.Decoder.ReadToken` with `StackDepth()`. Then reject before you decode.

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
  (see [`rules/03`](03-concurrency.md)).
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
see [`rules/05`](05-security.md)).

## Audit checklist

Run from repo root; verify each hit manually.

**In-band sentinels — a value standing in for absence** (§4a). Go's own `-1` from
`strings.Index` is documented and fine when tested immediately; yours is not:

- [ ] `grep -rnE 'return -1$|return -1,' --include='*.go' .` (§3) (producer — prefer (T, bool)
      comma-ok); `grep -rnE ':?= .*strconv\.Atoi\(' --include='*.go' . | grep -v 'err'` (the 0
      is in-band if err is dropped)

- [ ] **Discarded or double-handled errors (§1) (also rely on errcheck via golangci-lint)** —
      `grep -rnE '^\s*[a-zA-Z_].*,\s*_\s*(:?=).*\(' --include='*.go' . | grep -v _test.go` ;
      `grep -rn '_ = ' --include='*.go' . | grep -vE '(test|//)'` (each kept discard says why it
      cannot fail) ; `grep -rnE -A2 '(log|slog)\.[A-Za-z]+\(.*err' --include='*.go' . | grep -E -- '-[0-9]+-[[:space:]]*return .*err'`
      (log-and-return: the caller handles it a second time — LOW) ;
      `grep -rlE 'os\.(Create|OpenFile)\(' --include='*.go' . | xargs -r grep -nHE 'defer [A-Za-z_][A-Za-z0-9_.]*\.Close\(\)'`
      (a writer's `Close` error discarded; capture it in a deferred func — HIGH on a write/commit path)
- [ ] **String matching on errors (§3) — MEDIUM+** —
      `grep -rnE 'strings\.(Contains|HasPrefix|HasSuffix)\(\s*err\.Error\(\)' --include='*.go' .`
      ; `grep -rn '\.Error() ==' --include='*.go' .`
- [ ] **== comparison against sentinels (should be errors.Is) (§3) — MEDIUM** —
      `grep -rnE 'err\s*[!=]=\s*(sql\.ErrNoRows|io\.EOF|os\.ErrNotExist|context\.(Canceled|DeadlineExceeded))' --include='*.go' .`
      ; manual: failure counters and alerts skip `context.Canceled`/`DeadlineExceeded` first
- [ ] **%v wrapping where %w likely intended (§2) (manual review: `%v` only where breaking the
      chain is deliberate; each wrap names what this layer was doing, with identifiers, and does
      not restate the callee)** —
      `grep -rnE 'fmt\.Errorf\([^)]*%v[^)]*err\s*\)' --include='*.go' .`
- [ ] **Panics outside main/init/Must/tests — HIGH if reachable from input** (§5) —
      `grep -rl 'panic(' --include='*.go' . | grep -v '_test\.go$' | xargs -r awk '/^func /{f=$0} /panic\(/ && f !~ /(Must|^func init\()/ {print FILENAME":"FNR": "$0}'`
- [ ] **Limits before allocation and recursion (§5) — HIGH when the input is untrusted** —
      `grep -rnE 'make\(\[\][^,]+,[[:space:]]*(int(32|64)?\()?[a-z][A-Za-z0-9_]*\.[A-Z][A-Za-z0-9_]*' --include='*.go' .`
      (a slice sized by a decoded field: read back for a cap against a constant) ;
      `grep -rn 'debug.SetMaxStack' --include='*.go' .` (a raised stack cap hides deep recursion)
      ; each recursive function over decoded data takes and checks a depth bound (manual). A
      `recover` middleware is not the fix for any of these: a stack overflow or an unreservable `make`
      is a fatal error, and an out-of-range length, though a recoverable panic, must still be capped
      before `make`
- [ ] **Error flow shape (§6) — LOW** — no `else` after a `return`:
      `grep -rnE -B1 '^[[:space:]]*\} else( if .*)? \{' --include='*.go' . | grep -E -- '-[0-9]+-[[:space:]]*return'`
      ; golangci-lint `govet` with its `shadow` analyzer enabled (an inner `:=` hiding the outer
      `err`) ; manual: each error-collecting loop says fail-fast or `errors.Join` and why, and every
      send on an error channel has a guaranteed receiver (prefer `errgroup`)
- [ ] **log.Fatal / os.Exit outside main package; library logging; leaked error chains (§6, §7)
      — HIGH in libraries** —
      `grep -rnE '(log\.Fatal|os\.Exit)' --include='*.go' . | grep -v 'main\.go'` ;
      `grep -rLE '^package main' --include='*.go' . | grep -v '_test\.go$' | xargs -r grep -nHE '(^|[^A-Za-z0-9_.])s?log\.(Print|Fatal|Panic|Info|Warn|Error|Debug)'`
      (a non-main package that logs instead of returning) ;
      `grep -rnE 'http\.Error\([^,]+,[[:space:]]*err\.Error\(\)' --include='*.go' .` (an error chain
      echoed to a client: only a validation error's message may go out) ; manual: errors map to
      status codes in ONE place, and a library documents the sentinels/types it returns
- [ ] **Error strings: capitalized or "failed to" noise (§2) — INFO/LOW (ST1005)** —
      `grep -rnE 'errors\.New\("[A-Z]|fmt\.Errorf\("[A-Z]' --include='*.go' .` ;
      `grep -rn 'failed to' --include='*.go' . | grep -E '(errors\.New|fmt\.Errorf)'`
- [ ] **Typed-nil hazard; error kinds and names (§4)** —
      `grep -rnE 'func .*\) \*\w+Error( |$)' --include='*.go' .` (functions return `error`) ;
      `grep -rnE '^(var[[:space:]]+|[[:space:]]+)[A-Z][A-Za-z0-9_]*[[:space:]]+=[[:space:]]+errors\.New\(' --include='*.go' . | grep -vE '[[:space:]]Err[A-Z]'`
      (exported sentinel without the `Err` prefix) ; manual: each exported sentinel or type has a
      caller that branches on it (exports are API forever); wrapper types are in the next item
- [ ] **recover outside defer; missing Unwrap on wrapper types (§4, §5) (manual)** —
      `grep -rl 'recover()' --include='*.go' . | xargs -r awk 'FNR==1{d=-99} /defer func/{d=FNR} /recover\(\)/ && FNR-d>3 {print FILENAME":"FNR": "$0}'` ;
      `grep -rln 'type .*Error struct' --include='*.go' . | xargs grep -L 'func (.*) Unwrap()'`
- [ ] **Tooling** (§1, §2) — `go vet ./...` ;
      `golangci-lint run --enable-only errcheck,errorlint,err113,wrapcheck,nilerr ./...` ;
      `staticcheck ./...` (ST1005 error strings, SA4006 unused err, SA1019)

Severity guide: string-matched errors MEDIUM (HIGH if driving retry/billing
logic); dropped error on write/commit path HIGH; panic reachable from external
input HIGH; double logging LOW; phrasing INFO.
