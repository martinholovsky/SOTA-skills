# 02 — API & package design: interfaces, layout, context, options

Go rewards small, concrete, boring designs. Most design debt in Go codebases
is premature abstraction: interfaces nobody needed, packages named after
grab-bags, context misused as a dependency bag.

## 1. Interfaces: accept interfaces, return structs

- **Define interfaces where they are consumed**, not where implemented. The
  consumer declares the minimal capability it needs; producers just happen to
  satisfy it. This kills import cycles and keeps interfaces honest.
- **Return concrete types.** Callers get the full method set, godoc, and zero
  indirection; you can add methods without breaking anyone. Returning an
  interface is justified only when multiple implementations are returned from
  the same constructor (e.g. `io.Reader` chosen at runtime) or to hide an
  internal type on purpose.
- **Keep interfaces small.** 1–2 methods is the sweet spot (`io.Reader`,
  `http.Handler`, `fmt.Stringer`). A 5+ method interface is a sign you're
  modeling an implementation, not a need.

```go
// BAD — producer-side, fat, forces every consumer to depend on everything
package storage
type Store interface {
    GetUser(ctx context.Context, id int) (*User, error)
    PutUser(ctx context.Context, u *User) error
    ListUsers(ctx context.Context) ([]User, error)
    GetOrder(ctx context.Context, id int) (*Order, error)
    // ... 9 more
}

// GOOD — consumer-side, minimal
package billing
type userGetter interface {
    GetUser(ctx context.Context, id int) (*storage.User, error)
}
func NewInvoicer(users userGetter) *Invoicer { ... }
```

- **No interfaces "for mocking" by default.** A concrete dependency with a
  consumer-side 1-method interface at the test boundary is enough; you don't
  need a package-wide `XInterface` + `XImpl` pair (a Java-ism; audit as LOW).
- Compile-time conformance checks where they add safety:
  `var _ http.Handler = (*Server)(nil)`.
- Don't add methods to satisfy hypothetical future interfaces. Interface
  upgrades via type assertion (`if f, ok := w.(http.Flusher); ok`) are the
  escape hatch when you must sniff optional behavior — document it.

## 2. Package layout

- **Packages are named after what they provide, not what they contain.**
  `util`, `common`, `helpers`, `misc`, `shared`, `base`, `types` are dumping
  grounds — audit as LOW, refactor target. If a function has no home, it
  belongs next to its single caller, unexported.
- Package name is part of the call site: `bytes.Buffer`, not
  `bytespkg.BytesBuffer`. No stutter (`http.HTTPServer` → `http.Server`).
  Short, lowercase, no underscores.
- **`internal/` for anything not meant for external import.** In applications,
  most code goes under `internal/`; `pkg/` is cargo cult — only keep it if the
  repo genuinely exports libraries and the team likes the convention.
- Typical service shape (don't over-nest; flat beats deep):

```
cmd/api/main.go          // wiring only: flags/env, construct deps, call run()
internal/server/         // HTTP handlers, middleware, routes
internal/billing/        // domain logic, owns its consumer-side interfaces
internal/postgres/       // storage impl named after the technology
go.mod
```

- **No package-level mutable state.** Package vars make code untestable,
  order-dependent (`init` graphs), and racy. Dependencies are constructed in
  `main` and passed down (plain constructor injection — no DI framework).

```go
// BAD
var db *sql.DB
func init() { db = mustOpen() }

// GOOD
type Server struct{ db *sql.DB }
func New(db *sql.DB) *Server { return &Server{db: db} }
```

  Acceptable package-level state: true constants, `regexp.MustCompile` of
  constant patterns, registered `expvar`/metrics where the ecosystem demands
  it. `init()` should be rare and side-effect-light; audit nontrivial `init`
  as MEDIUM.
- One package per directory; `_test` package suffix (`foo_test`) for
  black-box tests is encouraged for exported-API tests.

## 3. Naming

- MixedCaps, never snake_case. Acronyms keep case: `ServeHTTP`, `userID`,
  `parseURL` (not `Id`, `Url`).
- Short names for short scopes (`i`, `r`, `buf`); descriptive names for wide
  scopes and exported identifiers. The wider the scope, the longer the name.
- Getters drop `Get`: `c.Name()`, not `c.GetName()`. Setters keep `Set`.
- Constructor: `New` if the package has one main type (`bytes.NewBuffer`...
  actually `buf := bytes.Buffer{}` — prefer usable zero values, §4);
  `NewX` when several.
- Single-method interface names: method + `er` (`Reader`, `Closer`,
  `Validator`) even when slightly awkward.
- Receiver names: 1–2 letters, consistent across methods (`s *Server`
  everywhere — never `this`/`self`).
- Errors: `ErrX` sentinels, `XError` types (see `rules/01`).

## 4. Zero values as a design tool

Make the zero value useful; it removes constructors, nil checks, and
initialization ordering bugs.

```go
// stdlib exemplars: ready with no constructor
var buf bytes.Buffer        // usable
var mu sync.Mutex           // usable
var wg sync.WaitGroup       // usable

// GOOD — design your types the same way
type Limiter struct {
    mu    sync.Mutex
    burst int // 0 = unlimited, documented
}
```

- Document zero-value semantics on the type's doc comment.
- If the zero value is *invalid* (must-have dependencies), force the
  constructor: unexported fields + `NewX`, and make misuse fail fast (nil
  check with a clear panic in the constructor's absence is worse than a
  compile-time-unavoidable constructor).
- `nil` slices and maps: nil slice reads/appends/ranges fine — don't
  `make([]T, 0)` just to avoid nil (exception: JSON `[]` vs `null` matters).
  Nil **map writes panic** — maps that get written need `make`.
- Don't return pointers just to enable `nil` as "absent"; prefer
  `(T, bool)` or a zero value with documented meaning.
- **`time.Time` is a value with two hidden parts, and `==` compares both.** The `time`
  package docs: *"the Go == operator compares not just the time instant but also the Location
  and the monotonic clock reading"*. Measured on go1.27.1, `t == t.Round(0)` and
  `t == t.UTC()` are both `false` while `t.Equal(...)` is `true`. So compare with
  `Equal`/`Before`/`After` and test absence with `IsZero()`. Time an interval with
  `time.Since(start)` or `t.Sub(u)` on `time.Now()` values: they use the monotonic reading,
  which the docs call *"robust against wall clock resets"*. `t.Unix()` and friends carry
  no monotonic reading, so subtracting them measures the wall clock. And *"in the absence of a
  time zone indicator, Parse returns a time in UTC"*: parsing a user's local time with a
  zone-less layout needs `time.ParseInLocation`.

### Numeric edges: NaN, zero divisors, the most negative integer

Extends `rules/05` §5 (conversions, money). Go never traps on these; it hands back a value.

- **`strconv.ParseFloat` accepts `"NaN"`, `"Inf"` and `"Infinity"`** (signed, any case) with a
  nil error; an out-of-range literal like `"1e400"` returns `±Inf` *and* `ErrRange`. A
  `float64` struct field tagged `json:",string"` takes `"NaN"` the same way. Every comparison
  with NaN is false, so `if x < lo || x > hi { reject }` lets NaN through. Reject non-finite
  input by name — `math.IsNaN(x) || math.IsInf(x, 0)` — or write the check as
  `!(x >= lo && x <= hi)`, which NaN fails. Converting NaN/Inf to an integer is
  implementation-dependent per the spec (measured on go1.27.1/amd64: `MinInt64`).
- **Integer `/` or `%` by a zero variable panics** (`integer divide by zero`); float
  division yields `±Inf` silently. Guard the divisor and return an error; a handler's
  `recover` is not the validation.
- **Signed overflow wraps and never panics** (spec, "Integer overflow"). `math.MinInt64 / -1`
  is `MinInt64` and `-math.MinInt64 == math.MinInt64`, so `abs` and sign flips need a
  `MinInt` check. Intermediates wrap too: `(a*b)/b` with `a = MaxInt64, b = 2` is `-1`.
  `time.Duration(n) * time.Second` for `n = 1e10` is a negative duration — bound `n` first
  (`|n| <= math.MaxInt64/int64(time.Second)`). The stdlib has no checked signed ops:
  `math/bits.Add64`/`Mul64` report unsigned carry and the high word, `math/big` never
  overflows, and any hand-rolled arithmetic on untrusted values needs a bound proved first.

OWASP: Go Secure Coding Practices (general coding practices); OWASP SCSVS (arithmetic).

## 5. Generics: judicious use only

Generics (1.18+) are for **code that is identical except for the type**:
containers, slice/map algorithms (`slices`, `maps` packages), constraints on
ordered/numeric types, type-safe pools.

Do NOT use generics when:

- An interface already expresses it: `func Print(s fmt.Stringer)` beats
  `func Print[T fmt.Stringer](s T)` unless you measured the devirtualization
  win.
- Only one type instantiation exists in the codebase — YAGNI; write the
  concrete version.
- The constraint is `any` and you're just avoiding writing two functions —
  readability cost exceeds duplication cost.
- You're building a generic "repository/service" framework. Domain code stays
  concrete.

Prefer stdlib generics over hand-rolling: `slices.Contains/SortFunc/Index`,
`maps.Keys`, `cmp.Or` (1.22), `min`/`max` builtins (1.21), `sync.OnceValue`
(1.21). Audit hand-written loops duplicating these as LOW.

## 6. Embedding vs composition

- Embedding is **not inheritance**: no overrides seen by the embedded type's
  methods, no LSP. It's automatic delegation only.
- Embed to satisfy interfaces wholesale or compose behaviors
  (`struct { sync.Mutex; m map[string]int }` is fine for small unexported
  types; for exported types a named `mu sync.Mutex` field is better — embedding
  exports `Lock`/`Unlock` into your API).
- **Never embed types whose method set becomes accidental public API**
  (embedding `*sql.DB` in your exported `Store` exposes all of it forever).
- Embedding interfaces in structs to partially implement (test fakes:
  `struct{ storage.Store }` + override one method) is idiomatic in tests;
  in production code a nil embedded interface panics at runtime — audit.
- Marshal trap: embedding flattens JSON fields and can silently change wire
  formats; promoted `MarshalJSON` from an embedded type hijacks the whole
  struct's encoding. MEDIUM if found on API types.

## 7. Functional options pattern

Use when a constructor has ≥3 optional knobs or needs future extensibility
without breaking callers. For ≤2 stable options, a config struct parameter or
plain arguments are simpler — don't cargo-cult.

```go
type Option func(*Server)

func WithTimeout(d time.Duration) Option {
    return func(s *Server) { s.timeout = d }
}
func WithLogger(l *slog.Logger) Option {
    return func(s *Server) { s.log = l }
}

func New(addr string, opts ...Option) *Server {
    s := &Server{addr: addr, timeout: 30 * time.Second, log: slog.Default()}
    for _, o := range opts {
        o(s)
    }
    return s
}
```

Rules: required params are positional args, never options; every option has a
sane default; options validate or the constructor returns `error` if
combinations can be invalid; for cross-package extensibility use
`Option interface{ apply(*config) }` instead of a bare func type.

## 8. context.Context discipline

- **First parameter, named `ctx`, of every function on a request/IO path.**
  Not last, not in a struct, not optional.
- **Never store ctx in a struct.** A struct outlives requests; storing ctx
  ties the object to one call's lifetime and hides cancellation flow. The
  known exceptions (`http.Request`) exist for compatibility — don't copy them.
  Audit `ctx context.Context` struct fields as MEDIUM.
- **Values: request-scoped metadata only** — trace ID, auth principal,
  deadline-irrelevant telemetry. Never dependencies (DB handles, loggers as
  the *only* way to get them), never function parameters in disguise. If
  removing the value breaks business logic, it was a parameter.
- Use **unexported key types** to avoid collisions:

```go
type ctxKey struct{}
func WithUser(ctx context.Context, u *User) context.Context {
    return context.WithValue(ctx, ctxKey{}, u)
}
func UserFrom(ctx context.Context) (*User, bool) {
    u, ok := ctx.Value(ctxKey{}).(*User)
    return u, ok
}
```

- Pass `ctx` down every blocking call: DB (`QueryContext`), HTTP
  (`http.NewRequestWithContext`), exec (`exec.CommandContext`). A blocking
  call without ctx on a request path is a HIGH leak/latency hazard.
- `context.Background()` only in `main`, init paths, and tests
  (`t.Context()` in 1.24+); `context.TODO()` is a tracked refactor marker —
  audit lingering TODOs as LOW.
- Always `defer cancel()` from `WithTimeout`/`WithCancel` (vet's
  `lostcancel` catches misses).
- Detach correctly: to outlive a request (async audit log), use
  `context.WithoutCancel(ctx)` (1.21+) — keeps values, drops cancellation —
  with your own timeout. Don't pass the request ctx into background work
  (dies with request) and don't pass `Background()` (loses trace metadata).
- `ctx.Err()` after select; return it unwrapped or wrapped with `%w` so
  callers can `errors.Is(err, context.Canceled)`.

## Audit checklist

- [ ] **Grab-bag packages — LOW** —
      `find . -type d | grep -iE '/(util|utils|common|helpers|shared|misc)($|/)'`
- [ ] **Returned interfaces from constructors (manual review) — LOW** —
      `grep -rnE 'func New\w*\([^)]*\) [A-Z]\w*(Interface| interface)' --include='*.go' .`
- [ ] **Fat interfaces: >4 methods (then inspect)** —
      `grep -rn -A 12 'interface {' --include='*.go' . | less` (manual)
- [ ] **Package-level mutable state — MEDIUM** —
      `grep -rnE '^var \w+ (=|\*|map\[|\[\])' --include='*.go' . | grep -vE '(Err|_test|MustCompile|regexp)'`
      ; `grep -rn 'func init()' --include='*.go' .`
- [ ] **Time values (§4) — MEDIUM** —
      `grep -rnE '\.Unix(Milli|Micro|Nano)?\(\)[[:space:]]*-' --include='*.go' .` (an interval
      from wall-clock integers; use `time.Since`) ;
      `grep -rnE '[!=]=[[:space:]]*time\.(Time\{\}|Now\(\))' --include='*.go' .` (use `IsZero`
      or `Equal`) ; `grep -rnF 'time.Parse(' --include='*.go' .` (read each layout: with no
      `Z07`, `-0700` or `MST` element the result is UTC, so local input needs `ParseInLocation`)
- [ ] **NaN/Infinity accepted from input; divide-by-zero and overflow at MinInt (§4) — MEDIUM,
      HIGH where the value gates money, limits or allocation** —
      `grep -rlE 'strconv\.ParseFloat\(' --include='*.go' . | xargs grep -LE 'math\.Is(NaN|Inf)\('`
      (files that parse floats and never test for non-finite values) ; then read integer
      `/`, `%`, negation and `time.Duration(n) *` sites on untrusted values for a guard
- [ ] **Context violations** —
      `grep -rnE 'ctx\s+context\.Context' --include='*.go' . | grep -E 'struct|^\s+[A-Za-z]+ +context\.Context'`
      (ctx in struct — MEDIUM);
      `grep -rnE 'func [^(]*\([^)]*\bctx context\.Context' --include='*.go' . | grep -vE '\(ctx context\.Context'`
      (ctx not first param); `grep -rn 'context.WithValue' --include='*.go' .` (check key types
      & payloads); `grep -rn 'context.TODO()' --include='*.go' .` (LOW, should be tracked);
      `grep -rnE 'context\.Background\(\)' --include='*.go' . | grep -v 'main\|_test'`
      (suspicious mid-stack)
- [ ] **Blocking calls missing ctx variants — HIGH on request paths** —
      `grep -rnE '\.(Query|QueryRow|Exec)\(' --include='*.go' . | grep -v Context` ;
      `grep -rn 'http.Get(\|http.Post(' --include='*.go' .` ;
      `grep -rn 'exec.Command(' --include='*.go' . | grep -v CommandContext`
- [ ] **Naming drift — INFO** — `grep -rnE 'func.*Get[A-Z]\w*\(\) ' --include='*.go' .`
      (Get-prefixed getters); `grep -rnE '\b(Id|Url|Http|Api)\b' --include='*.go' .` (acronym
      casing)
- [ ] **Tooling** — `go vet ./...` (lostcancel, composites);
      `golangci-lint run --enable-only revive,ireturn,containedctx,contextcheck,fatcontext ./...`
      ; `staticcheck ./...` (ST1003 naming, S1021, SA1029 ctx keys)

Severity guide: ctx in struct / dependency-in-ctx MEDIUM; missing
ctx on blocking request-path call HIGH; util-package and returned
interfaces LOW; mutable package state MEDIUM (HIGH if written concurrently).