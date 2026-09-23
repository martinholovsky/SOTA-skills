# 04 — HTTP & services: timeouts, shutdown, middleware, slog

`net/http` defaults are tuned for compatibility, not production: zero server
timeouts, infinite client waits, unlimited header sizes. Every production
service overrides them. This file covers server, client, lifecycle, and
observability.

## 1. http.Server — set ALL the timeouts

`http.ListenAndServe(addr, h)` is unfit for production: no timeouts means any
slow/malicious client (slowloris) holds a connection and goroutine forever —
HIGH finding on any internet-facing service.

```go
// GOOD — every production server
srv := &http.Server{
    Addr:              ":8080",
    Handler:           mux,
    ReadHeaderTimeout: 5 * time.Second,   // slowloris defense; cheap, always set
    ReadTimeout:       10 * time.Second,  // full request incl. body
    WriteTimeout:      30 * time.Second,  // from end of headers (HTTP/1.1) to last byte written
    IdleTimeout:       120 * time.Second, // keep-alive connections between requests
    MaxHeaderBytes:    1 << 20,           // default 1MB; set explicitly
}
```

What each guards:

| Timeout | Covers | If unset |
|---|---|---|
| `ReadHeaderTimeout` | Client sending request headers | Slowloris: drip headers forever |
| `ReadTimeout` | Headers + entire body read | Slow body upload pins the conn |
| `WriteTimeout` | Writing the response | Slow reader pins handler + buffers |
| `IdleTimeout` | Keep-alive idle gap | Falls back to ReadTimeout; if both 0, idle conns live forever |

- Large uploads/downloads/streaming/SSE: coarse `ReadTimeout`/`WriteTimeout`
  kill legitimate transfers. Use per-route control:
  `http.TimeoutHandler(h, d, msg)` for handler deadlines,
  `rc := http.NewResponseController(w); rc.SetWriteDeadline(...)` (1.20+) to
  extend deadlines per request. Keep `ReadHeaderTimeout` regardless.
- Per-request deadlines for *work* belong in ctx:
  `context.WithTimeout(r.Context(), d)` around downstream calls. Server
  timeouts protect the transport; ctx protects the business logic.
- Body limits: `http.MaxBytesReader(w, r.Body, maxSize)` on every endpoint
  that reads a body — unbounded `io.ReadAll(r.Body)` is a memory DoS (HIGH).
- Routing: stdlib `http.ServeMux` (1.22+) supports methods and wildcards —
  `mux.HandleFunc("GET /users/{id}", h)`, `r.PathValue("id")`. Default to it;
  reach for chi/echo only for needed extras (route-scoped middleware trees).
- Go 1.25+: `http.CrossOriginProtection` gives stdlib CSRF protection via
  Sec-Fetch-Site; use it or an equivalent for cookie-authenticated mutations.

## 2. HTTP clients — timeouts, body hygiene, reuse

**`http.DefaultClient` has NO timeout** — a hung server hangs your goroutine
forever. Never use `http.Get/Post/...` package functions in services (HIGH).

```go
// GOOD — explicit client, reused (it's goroutine-safe; pools connections)
client := &http.Client{
    Timeout: 10 * time.Second, // absolute cap: dial+TLS+request+read body
}

// Per-attempt control with ctx (preferred for request-scoped deadlines)
ctx, cancel := context.WithTimeout(ctx, 3*time.Second)
defer cancel()
req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
```

`Client.Timeout` includes reading the body; for streaming responses, leave it
0 and use ctx + `Transport` knobs instead:

```go
t := &http.Transport{
    Proxy:                 http.ProxyFromEnvironment,
    DialContext:           (&net.Dialer{Timeout: 5 * time.Second, KeepAlive: 30 * time.Second}).DialContext,
    TLSHandshakeTimeout:   5 * time.Second,
    ResponseHeaderTimeout: 5 * time.Second,
    ExpectContinueTimeout: 1 * time.Second,
    MaxIdleConns:          100,
    MaxIdleConnsPerHost:   100, // DEFAULT IS 2 — throttles any single-host workload
    IdleConnTimeout:       90 * time.Second,
}
client := &http.Client{Transport: t, Timeout: 10 * time.Second}
```

`DefaultMaxIdleConnsPerHost = 2` is the classic hidden bottleneck for
service-to-service traffic: connections churn, ports exhaust (TIME_WAIT),
latency spikes. Set `MaxIdleConnsPerHost` ≈ peak concurrency to that host.

**Body discipline — every response, every path:**

```go
resp, err := client.Do(req)
if err != nil {
    return err // resp is nil on error; do NOT touch resp.Body here
}
// Connection reuse requires the body fully read before Close. Defers run
// LIFO: register Close first so the bounded drain executes before it.
defer resp.Body.Close()
defer io.Copy(io.Discard, io.LimitReader(resp.Body, 4<<10))
```

Unclosed bodies leak FDs and goroutines;
undrained bodies kill connection reuse (LOW perf, MEDIUM at scale). Always
check `resp.StatusCode` — `err == nil` for 4xx/5xx.

Create **one client per upstream at startup**, inject it; never build a
client (or Transport) per request — each Transport owns a fresh pool.

## 3. Graceful shutdown

Pattern: catch signals via ctx, stop accepting, drain in-flight with a
deadline, then close dependencies.

```go
func run(ctx context.Context) error {
    ctx, stop := signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)
    defer stop()

    srv := &http.Server{ /* ...timeouts as §1... */ }
    errCh := make(chan error, 1)
    go func() { errCh <- srv.ListenAndServe() }()

    select {
    case err := <-errCh:
        return fmt.Errorf("server: %w", err) // ListenAndServe always returns non-nil
    case <-ctx.Done():
    }

    shCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
    defer cancel()
    if err := srv.Shutdown(shCtx); err != nil {       // stops Accept, waits for handlers
        return fmt.Errorf("shutdown: %w", err)        // DeadlineExceeded => srv.Close() already forced
    }
    return nil
}
```

- `Shutdown` does NOT cancel handler contexts or wait for hijacked conns
  (WebSockets); use `srv.RegisterOnShutdown` to signal those, and propagate a
  "draining" ctx to long-running handlers.
- `http.ErrServerClosed` from `ListenAndServe` after Shutdown is expected —
  filter it: `if !errors.Is(err, http.ErrServerClosed)`.
- Shutdown deadline must be **shorter than** the orchestrator's kill grace
  period (K8s `terminationGracePeriodSeconds`, default 30s) and account for
  readiness-probe propagation: flip readiness to failing first, sleep a
  beat (or rely on `preStop`), then Shutdown — otherwise traffic still
  arrives at a closed listener.
- Close order after drain: server → background workers (cancel + join) →
  DB pools/queues → flush telemetry. Reverse of startup.

## 4. Middleware

Standard shape — `func(http.Handler) http.Handler`, composed outermost-first:

```go
func RequestLogger(log *slog.Logger) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            start := time.Now()
            ww := &statusWriter{ResponseWriter: w, status: http.StatusOK}
            next.ServeHTTP(ww, r)
            log.LogAttrs(r.Context(), slog.LevelInfo, "request",
                slog.String("method", r.Method),
                slog.String("path", r.URL.Path),
                slog.Int("status", ww.status),
                slog.Duration("dur", time.Since(start)),
            )
        })
    }
}

type statusWriter struct {
    http.ResponseWriter
    status int
}
func (w *statusWriter) WriteHeader(c int) { w.status = c; w.ResponseWriter.WriteHeader(c) }
```

- Order matters: recover (outermost) → request ID/trace → logging → auth →
  rate limit → handler. Recovery middleware logs `debug.Stack()` and returns
  500; check `errors.Is(err, http.ErrAbortHandler)` style sentinel —
  re-panic `http.ErrAbortHandler` rather than swallowing it.
- Wrapper `ResponseWriter`s hide optional interfaces (`http.Flusher`,
  `http.Hijacker`); implement passthroughs or use
  `http.NewResponseController(w)` (1.20+), which unwraps automatically — SSE
  and WebSockets break otherwise (MEDIUM).
- Don't read `r.Body` in middleware unless you replace it
  (`r.Body = io.NopCloser(bytes.NewReader(buf))`) — handlers get an empty body.
- Prefer returning errors from handlers via a small adapter
  (`func(w, r) error` → `http.Handler`) so the error mapper from
  `rules/01 §7` is the single response-shaping point.

## 4a. Cookies: the attributes are the security, not the value

`http.SetCookie` writes exactly what you give it and defaults to nothing. A session cookie
with no attributes is sent over plaintext, readable from JavaScript, and attached to
cross-site requests.

```go
// BAD — three missing attributes, none of them reported by anything at runtime
http.SetCookie(w, &http.Cookie{Name: "session", Value: tok, Path: "/"})

// GOOD
http.SetCookie(w, &http.Cookie{
    Name: "session", Value: tok, Path: "/",
    Secure:   true,                    // TLS only
    HttpOnly: true,                    // not reachable from document.cookie
    SameSite: http.SameSiteLaxMode,    // Strict where the flow allows it
    MaxAge:   int(8 * time.Hour / time.Second),
})
```

- **`SameSite` unset is not the same as `SameSiteDefaultMode`** — set it explicitly and pick
  `Strict` unless a cross-site entry flow (OAuth callback, payment return) needs `Lax`.
  `SameSiteNoneMode` requires `Secure` or browsers drop the cookie.
- **`__Host-` prefix** when the cookie is origin-scoped: browsers then enforce `Secure`, a
  `/` path, and no `Domain`, so a subdomain cannot overwrite it.
- Session identifiers get `HttpOnly`; a CSRF token the page must read does not — that split
  is deliberate, not an oversight to fix.

## 4b. Redirects: two different bugs

**Open redirect (the server's).** A `Location` built from user input turns your domain into a
credible phishing launchpad. Validate against an allowlist of paths, or parse and require
`u.Host == ""` — a leading `//evil.com` is a protocol-relative URL, not a path.

**Header propagation on the client's.** `http.Client` follows redirects by default and
**re-sends your headers to the new host**. A redirect to an attacker-controlled origin then
receives the `Authorization` header. Go's default `CheckRedirect` stops after 10 hops but
does not strip credentials across hosts.

```go
// GOOD — do not carry credentials across an origin change
client.CheckRedirect = func(req *http.Request, via []*http.Request) error {
    if req.URL.Host != via[0].URL.Host {
        req.Header.Del("Authorization")
        req.Header.Del("Cookie")
    }
    return nil
}
```

## 5. Structured logging with slog

`log/slog` (1.21+) is the standard. `fmt.Println`/`log.Printf` in services is
LOW debt; unstructured logs can't be queried.

```go
log := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
    Level: slog.LevelInfo,           // make it a flag/env; use slog.LevelVar for runtime changes
}))
slog.SetDefault(log)                  // also reroutes legacy log.Printf

log.InfoContext(ctx, "payment processed",
    "order_id", orderID,             // alternating key/value
    slog.Int("attempts", n),         // or typed attrs — faster, type-safe
)
```

- **Always the `*Context` variants on request paths** — handlers can extract
  trace/span IDs from ctx (OTel bridges do).
- Inject `*slog.Logger` as a dependency (constructor arg) in libraries;
  `slog.Default()` is acceptable at app level. Pre-bind request attrs once:
  `log = log.With("request_id", id)` in middleware, pass via ctx value or
  handler closure.
- Hot paths: `log.LogAttrs(ctx, level, msg, attrs...)` avoids
  `[]any` allocs; guard expensive computation with
  `if log.Enabled(ctx, slog.LevelDebug)`.
- Fan-out to several sinks (e.g. JSON to stdout + a file handler):
  `slog.NewMultiHandler(h1, h2)` (1.26+) replaces hand-rolled multi-handler
  wrappers and third-party equivalents.
- Never log secrets/PII: implement `slog.LogValuer` on sensitive types to
  redact by construction:

```go
func (t Token) LogValue() slog.Value { return slog.StringValue("REDACTED") }
```

- Levels: Debug (dev diagnosis), Info (state changes worth auditing), Warn
  (degraded, self-healed), Error (failed operation, human may act). Don't log
  Error for client mistakes (4xx) — that's Info/Warn; alert noise kills oncall.

## 6. Request-scoped values

- Request ID/trace context: set in middleware, store in ctx (unexported key —
  `rules/02 §8`), read everywhere via accessor funcs.
- Auth principal: middleware authenticates, puts `*User`/claims in ctx;
  handlers call `auth.UserFrom(ctx)`. Handlers never re-parse tokens.
- Everything else (parsed body, query params) is plain function arguments —
  ctx is not a parameter bag.
- Propagate outbound: when calling downstream services pass `ctx` into
  `http.NewRequestWithContext` and inject trace headers (otelhttp transport
  does both).

## Audit checklist

- [ ] **Naked servers — HIGH** —
      `grep -rn 'http.ListenAndServe\|http.ListenAndServeTLS' --include='*.go' .` ;
      `grep -rn -A8 'http.Server{' --include='*.go' .` (verify all four timeouts present)
- [ ] **Default client / package-level helpers — HIGH** —
      `grep -rnE 'http\.(Get|Post|PostForm|Head)\(' --include='*.go' .` ;
      `grep -rn 'http.DefaultClient' --include='*.go' .` ;
      `grep -rn -A6 'http.Client{' --include='*.go' .` (Timeout set? Transport tuned?);
      `grep -rn 'MaxIdleConnsPerHost' --include='*.go' .` (absent + high fan-out = bottleneck)
- [ ] **Body hygiene** — `grep -rn 'client.Do\|\.Get(\|\.Post(' --include='*.go' .` (then verify
      defer Close + drain near each); `grep -rn 'resp.Body.Close' --include='*.go' .` ;
      `grep -rn 'io.ReadAll(r.Body\|io.ReadAll(req.Body' --include='*.go' .` (MaxBytesReader
      present? — HIGH); `grep -rn 'MaxBytesReader' --include='*.go' .`
- [ ] **Shutdown** — `grep -rn 'signal.NotifyContext\|signal.Notify' --include='*.go' .` ;
      `grep -rn 'srv.Shutdown\|.Shutdown(' --include='*.go' .` (absent => no graceful drain —
      MEDIUM); `grep -rn 'ErrServerClosed' --include='*.go' .`
- [ ] **Per-request client/transport construction — MEDIUM perf** —
      `grep -rn -B3 'http.Client{' --include='*.go' . | grep -E 'func.*\(w http|Handler'`
- [ ] **Logging** —
      `grep -rnE '\b(fmt\.Print|log\.Print)' --include='*.go' . | grep -v _test.go` (LOW);
      `grep -rn 'slog.' --include='*.go' . | grep -v Context` (request paths should use
      *Context);
      `grep -rnE '(password|token|secret|authorization|api_?key)' --include='*.go' . | grep -i 'slog\|log\.'`
      (PII in logs — HIGH)
- [ ] **Middleware ResponseWriter wrappers missing Flush/Hijack passthrough** —
      `grep -rn -A4 'http.ResponseWriter$' --include='*.go' . | grep 'struct'`
- [ ] **Tooling** — `golangci-lint run --enable-only bodyclose,noctx,gosec ./...` (noctx:
      requests without ctx); `go vet ./...`
- [ ] **--- Cookies and redirects (§4a, §4b) ---** —
      `grep -rn 'SetCookie' --include='*.go' . | grep -v _test` (then read each for
      Secure/HttpOnly/SameSite [HIGH]);
      `grep -rnE 'http\.Cookie\{' -A6 --include='*.go' . | grep -L 'HttpOnly' 2>/dev/null` ;
      `grep -rnE 'Redirect\(|Location.*r\.(URL|Form|Header)' --include='*.go' .` (open redirect
      [HIGH]); `grep -rn 'CheckRedirect' --include='*.go' .` (absent = headers cross origins
      [MEDIUM])

Severity guide: no server timeouts internet-facing HIGH; default client in
service HIGH; unbounded body read HIGH; missing graceful shutdown MEDIUM;
unclosed/undrained bodies MEDIUM; unstructured logging LOW; secrets in logs
HIGH.