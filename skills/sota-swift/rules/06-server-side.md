# 06 — Server-side Swift: Vapor, Hummingbird, SwiftNIO

The defaults and traps of Swift's server frameworks. Framework names are neutral examples; the
rules apply to any SwiftNIO-based server. Defaults quoted were read from source on 2026-10-07
(vapor/vapor `main` at bf77fc6, 2026-10-04; hummingbird and hummingbird-auth main) — frameworks
change defaults between releases, so re-check yours.

## 1. Authentication and authorization: middleware order

- **Vapor**: authenticators *populate* the user; they do not *require* one. A protected group
  needs a guard after them — the docs: *"`GuardMiddleware` is added after the authenticators to
  require that `User` was successfully authenticated."*

```swift
let protected = app.grouped(UserToken.authenticator(), User.guardMiddleware())  // GOOD
let leaky     = app.grouped(UserToken.authenticator())                           // BAD: anonymous passes
```

- **Hummingbird** (hummingbird-auth): an authenticator, then `IsAuthenticatedMiddleware`, then
  `AuthorizationPolicyMiddleware` (*"Place this middleware *after* an authenticator and
  `IsAuthenticatedMiddleware`"*).
- Authorization is per object: after authenticating, every handler that loads by ID checks the
  object belongs to the caller (`sota-code-security` rules/03).

## 2. Cookies and sessions: the defaults are not production defaults

- **Vapor `SessionsConfiguration.default()`** sets the session cookie to `isSecure: false,
  isHTTPOnly: false, sameSite: .lax`. Production sets `isSecure: true` and `isHTTPOnly: true`
  explicitly (a custom `cookieFactory`).
- **Hummingbird `SessionCookieParameters`** defaults to `secure: false` and `sameSite: nil` (its
  `Cookie` type defaults `httpOnly: true`). Set `secure: true` and a `sameSite` value.
- Session lifetime, rotation on login and invalidation on logout → `sota-code-security` rules/17.

## 3. Debug versus production: build configuration decides

- **Vapor's `Environment.isRelease` is decided at compile time** (`!_isDebugAssertConfiguration()`;
  the source: `Environment.production.isRelease == false` for a debug build). Its error middleware
  returns `"Something went wrong."` only when `isRelease` — so a **debug build run with
  `--env production` returns raw error descriptions to clients**.
- SwiftPM builds debug by default. Ship `swift build -c release`; check at startup that the
  binary is a release build and the environment is production, and refuse to start otherwise.
- Code behind `#if DEBUG` (test routes, verbose errors, auth bypasses) must not be reachable in a
  release build; grep for it.

## 4. Requests, errors and resource limits

- Body size: Vapor's `defaultMaxBodySize` is `"16kb"`; routes that raise it (`body: .collect(maxSize:)`)
  raise it to a stated number, never unlimited; streaming uploads cap total bytes.
- Error responses carry no stack, SQL or file paths; log the detail server-side with a request ID
  (`sota-observability`).
- Every outbound call from a handler has a timeout (rules/03 §4); rate limiting per caller is the
  router's principle 5.

## 5. SwiftNIO and Linux

- New logic is async/await; bridge `EventLoopFuture` APIs at the edges only. Never block an
  event loop thread (no synchronous file I/O, `sleep`, or semaphore waits on it).
- Shut down clients and event-loop groups on exit (rules/04 §2).
- Foundation on Linux is swift-corelibs-foundation / FoundationEssentials: do not assume Darwin
  behaviour; run CI on the deployment OS.
- Containers: a static Linux SDK binary in a minimal image, non-root → `sota-sandboxing`.

## Audit checklist

- [ ] Authn / authz checks: every protected route group has a guard after its authenticators (grep `\.grouped\(` with an authenticator and no `guardMiddleware`/`IsAuthenticatedMiddleware`); object-level authorization checked per handler.
- [ ] App-set cookie defaults: session cookies set `isSecure`/`secure: true` and `isHTTPOnly: true` with a `sameSite` value — grep `SessionsConfiguration\.default\(\)|isSecure: *false|isHTTPOnly: *false|secure: *false`.
- [ ] Debug mode never ships: the shipped binary is a release mode build (`swift build -c release`); startup asserts a release build in a production environment; no `#if DEBUG` route or bypass reachable in release.
- [ ] Resource limits / DoS guards: body sizes capped per route (no unlimited `maxSize`); streaming uploads capped; outbound calls time out; per-caller rate limiting present or delegated to the edge and stated.
- [ ] Error responses expose no stack traces, SQL or paths; detail is logged server-side with a request ID.
- [ ] No blocking calls on NIO event-loop threads; `EventLoopFuture` bridged only at edges; clients and event-loop groups shut down on exit.
- [ ] CI runs on the deployment OS (Linux) and does not rely on Darwin-only Foundation behaviour.
