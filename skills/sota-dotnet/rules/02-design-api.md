# 02 — API design, disposal, exceptions, DI

Good .NET APIs make nullability and lifetimes explicit and lean on the built-in
DI and options patterns. Idioms are in `01`, async in `03`.

## 1. Nullability as contract

- With NRT enabled (`rules/01`), the API signature *is* the null contract:
  return `T?` only when null is meaningful; accept `T` to require non-null.
  Annotate with `[NotNullWhen(true)]` etc. for `Try` patterns.
- Validate external input at the boundary regardless of annotations
  (deserialized/wire data can violate them): `ArgumentNullException.ThrowIfNull`,
  range/format guards.

## 1a. In-band sentinels vs `int?` and the Try pattern

`String.IndexOf` returns `-1` for not-found, and `Int32.TryParse` sets its `out`
parameter to **zero on failure** — *"contains the … value equivalent … if the
conversion succeeded, or zero if the conversion failed"* (learn.microsoft.com,
`System.Int32.TryParse`, .NET 10; some overloads say *"an undefined value on
failure"*). So `TryParse` is the right shape — the `bool` return is out-of-band —
but the `out` value **is** an in-band sentinel the moment the `bool` is ignored.

- §1's nullability contract extends to value types: `int?`/`Nullable<T>` is the
  answer for an absent number, not `-1` or `0`. `int?` participates in
  `HasValue`/pattern matching; a magic `int` participates in nothing.
- Prefer `TryParse` over `Parse`, and **use the `bool`** — `if (int.TryParse(s, out
  var n))`, never `int.TryParse(s, out var n); use(n);`. A discarded `bool` converts
  a correct API into the class in `sota-architecture` rules/02 §8a.
- Nullable reference types cover references only; NRT being on says nothing about a
  `-1` in an `int`. Don't let a clean NRT build read as absence being modeled.
- Audit: `grep -rnE 'return -1;|out var [a-z]+\);' --include='*.cs' src/` and
  comparisons where one operand is `-1`-filtered.

## 2. Immutability & value semantics

- Prefer immutable public types (records, `init` properties, `IReadOnlyList<T>`/
  `IReadOnlyDictionary<T>` return types). Don't expose mutable internal
  collections — return read-only views/copies.
- Choose `struct`/`record struct` for small, short-lived values; `class`/`record`
  for entities and larger objects (`rules/05` for the perf trade-offs).

## 3. Disposal & resource lifetime

- Everything `IDisposable`/`IAsyncDisposable` is scoped with `using`/`await using`
  or owned by a DI lifetime — never a manual `Dispose()` you can skip on an
  exception. Implement the dispose pattern correctly (and `IAsyncDisposable` for
  async cleanup).
- **`HttpClient`**: never `new HttpClient()` per call (socket exhaustion) — use
  `IHttpClientFactory` (typed/named clients) or a single long-lived instance **built on a
  `SocketsHttpHandler` with `PooledConnectionLifetime` set** (for example a few minutes). A client
  resolves DNS only when it opens a connection, so a static client without that lifetime keeps
  talking to an old address after a DNS change (Microsoft: HttpClient guidelines for .NET).
- Don't dispose objects you don't own (e.g. injected/DI-managed singletons,
  `HttpClient` from the factory).

## 4. Exceptions in the contract

- Throw specific BCL exceptions (`ArgumentException`, `InvalidOperationException`,
  `ArgumentNullException`) before custom ones; document thrown types. Don't leak
  low-level exceptions across an abstraction — wrap, preserving `InnerException`.
- Validate arguments with guard helpers (`ArgumentNullException.ThrowIfNull`,
  `ArgumentOutOfRangeException.ThrowIf...`).
- **In ASP.NET Core the outermost boundary is the pipeline, so register the exception handler
  first.** `UseExceptionHandler` only catches what middleware registered *after* it throws
  (Microsoft's middleware-order docs put it first for that reason). Measured on .NET 10 with a
  throwing middleware registered before it: in Production the client got an empty 500 that skipped
  the handler (no problem response, no handler logging); in Development the auto-added developer
  exception page returned the exception text (the environment trap is `rules/04` §7).
  *(OWASP: Error Handling cheat sheet.)*

## 5. Dependency injection & options

- Use the built-in `Microsoft.Extensions.DependencyInjection` container;
  register with the correct **lifetime** (`Singleton`/`Scoped`/`Transient`).
  Classic bug: a `Scoped` (e.g. `DbContext`) captured by a `Singleton` →
  captive dependency / cross-request state. Don't inject `IServiceProvider`
  and resolve manually (service-locator anti-pattern) except at composition
  roots.
- Constructor injection over property/field; avoid mutable static state (MEDIUM
  — concurrency + testability hazard). Use the **options pattern**
  (`IOptions<T>`/`IOptionsMonitor<T>`) for configuration, validated on start
  (`ValidateOnStart`).

## 6. Visibility & API surface

- Keep the public surface minimal: `internal` by default, `public` deliberately;
  `sealed` classes not designed for inheritance. Use `InternalsVisibleTo` for
  test access rather than widening visibility.

## 7. Request limits and rate limiting (ASP.NET Core)

The generic rules (a budget per caller, 429 with `Retry-After`, size limits before parsing) are
`sota-api-design` rules/07 §2–§3. This is the .NET spelling. Sources: Microsoft Learn, "Rate
limiting middleware in ASP.NET Core" and "Configure options for the ASP.NET Core Kestrel web
server". Defaults below were read from the option objects on .NET 10.0.12 (2026-09-25).

- **Nothing is limited until you opt in.** `builder.Services.AddRateLimiter(...)` defines the
  policies and `app.UseRateLimiter()` enforces them. Attach a named policy with
  `.RequireRateLimiting("name")` on an endpoint, `MapGroup` or `MapControllers()`, or with
  `[EnableRateLimiting("name")]` on a controller, action or page. `[DisableRateLimiting]` switches
  off every limiter on that endpoint, the global one included, so each use needs a reason.
  `RateLimiterOptions.GlobalLimiter` is `null` by default and a rejection returns **503**
  (measured). Set `RejectionStatusCode = StatusCodes.Status429TooManyRequests` and set
  `Retry-After` in `OnRejected` from `MetadataName.RetryAfter`.
- **Order matters.** Microsoft requires `UseRateLimiter` after `UseRouting` when you use
  endpoint policies. When the partition key reads the user, it must also come after
  `UseAuthentication`. Measured with the §8 example: with `UseRateLimiter` moved above
  authentication, every caller fell into the anonymous bucket, and after one user had used up
  the budget a second user's first request got 429.
- **Partition by caller, not one global bucket.** One unpartitioned limiter lets a single client
  use up the budget for everyone. Build the limiter with `PartitionedRateLimiter.Create` or
  `RateLimitPartition.Get*Limiter`, keyed on the authenticated subject
  (`ClaimTypes.NameIdentifier`) or an API-key id you have already validated. The client IP is a
  valid key only once forwarded headers trust only your proxies (`rules/04` §7): Microsoft warns
  that IP partitions are open to spoofed-source DoS. Each distinct key creates and caches its own
  limiter, and Microsoft names memory exhaustion as the result of keying on unbounded
  user-controlled input. So never key on a raw header or path value.
- **Rate-limit the anonymous authentication endpoints: HIGH if absent.** Login, token, register,
  password reset and OTP/MFA verification are anonymous by design, so `FallbackPolicy` does not
  cover them and the rate limit is the brute-force control. Key them by client IP (after the
  forwarded-headers fix). Per-account throttling is `sota-code-security`.
- **Request size limits.** Measured defaults: Kestrel `MaxRequestBodySize` 30,000,000 bytes;
  `FormOptions.MultipartBodyLengthLimit` 134,217,728 (128 MiB), `ValueCountLimit` 1024,
  `ValueLengthLimit` 4 MiB, `KeyLengthLimit` 2048; `MaxRequestHeadersTotalSize` 32 KiB;
  `RequestHeadersTimeout` 30 s. Lower them to what each endpoint needs with
  `[RequestSizeLimit(n)]`, `[RequestFormLimits(...)]`, `Configure<FormOptions>`, or
  `IHttpMaxRequestBodySizeFeature` (set it before the body is read, or it throws). Minimal APIs
  have no `DisableRequestSizeLimit()` extension (compile-checked); the attribute is MVC's. Any of
  these removes the bound: `MaxRequestBodySize = null`, `[DisableRequestSizeLimit]`, a
  `FormOptions` limit set to `int.MaxValue`/`long.MaxValue`, or `"MaxRequestBodySize": null` in
  the `Kestrel:Limits` config section. That is MEDIUM, and HIGH on an anonymous endpoint. Behind
  IIS out-of-process, IIS sets the limit and Kestrel's body limit is disabled.
- **Connections and slow clients.** `MaxConcurrentConnections` and
  `MaxConcurrentUpgradedConnections` are `null` (unlimited) by default (measured). Upgraded
  (WebSocket) connections do not count against the first. Set both when Kestrel faces the
  internet; behind a proxy that caps connections, write down where the cap lives. Setting
  `MinRequestBodyDataRate` or `MinResponseDataRate` to `null` removes the slow-client (slowloris)
  guard. Kestrel does not enforce its timeouts and data rates while a debugger is attached, so a
  debug session proves nothing about them.

## 8. Worked example: one minimal-API endpoint done right

Built with SDK 10.0.401 and `TreatWarningsAsErrors` (0 warnings), then driven through
`WebApplicationFactory` in the `Production` environment (2026-09-25): anonymous → 401
problem+json; `limit=5000` or a missing `status` → 400 validation problem; a quote-injection
`status` → 200 `[]`; a 21st request in the window → 429 problem+json, while a second user
still got 200. The packages are `Microsoft.AspNetCore.Authentication.JwtBearer` and
`Microsoft.EntityFrameworkCore.Sqlite`. In `Development`, a missing required query value threw
`BadHttpRequestException` and the handler returned **500** rather than 400, so test validation
in the environment you ship.

```csharp
using System.ComponentModel.DataAnnotations;
using System.Security.Claims;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddAuthentication().AddJwtBearer();            // issuer/audience/keys from config
builder.Services.AddAuthorization(o => o.FallbackPolicy =        // deny by default (rules/04 §4)
    new AuthorizationPolicyBuilder().RequireAuthenticatedUser().Build());
builder.Services.AddRateLimiter(o =>
{
    o.RejectionStatusCode = StatusCodes.Status429TooManyRequests;  // default is 503
    o.AddPolicy("per-user", ctx => RateLimitPartition.GetTokenBucketLimiter(
        ctx.User.FindFirstValue(ClaimTypes.NameIdentifier) ?? "anon", // key = caller, not global
        _ => new() { TokenLimit = 20, TokensPerPeriod = 20, QueueLimit = 0,
                     ReplenishmentPeriod = TimeSpan.FromMinutes(1) }));
});
builder.Services.AddValidation();                                 // .NET 10 minimal-API validation
builder.Services.AddProblemDetails();
builder.Services.AddDbContext<ShopDb>(o => o.UseSqlite(builder.Configuration.GetConnectionString("Shop")));
var app = builder.Build();
app.UseExceptionHandler();                                        // first: problem+json 500, no stack
app.UseStatusCodePages();                                         // 401/429 bodies as problem+json
app.UseAuthentication(); app.UseAuthorization();
app.UseRateLimiter();                                             // after auth: the key sees the user

app.MapGet("/orders", async ([AsParameters] OrderQuery q, ShopDb db, ClaimsPrincipal user,
    ILogger<Program> log, CancellationToken ct) =>
{
    if (user.FindFirstValue(ClaimTypes.NameIdentifier) is not { } owner) return Results.Forbid();
    var rows = await db.Orders.Where(o => o.OwnerId == owner && o.Status == q.Status)
        .OrderBy(o => o.Id).Take(q.Limit).ToListAsync(ct);        // LINQ: parameterised SQL
    log.LogInformation("Listed {Count} orders for {OwnerId}", rows.Count, owner); // no token, no body
    return Results.Ok(rows);
}).RequireRateLimiting("per-user");
app.Run();

public record OrderQuery([Required, StringLength(16)] string Status, [Range(1, 100)] int Limit = 20);
public record Order(int Id, string OwnerId, string Status);
public class ShopDb(DbContextOptions<ShopDb> o) : DbContext(o) { public DbSet<Order> Orders => Set<Order>(); }
```

`AddValidation` is the .NET 10 minimal-API validation (DataAnnotations on query, header and body
parameters). The `"anon"` fallback key is never used here, because authorization rejects
anonymous callers before the limiter runs; on an anonymous endpoint, key by client IP (§7).
Logging a subject id is fine; never log the bearer token, the body, or a credential-bearing
record (`rules/04` §4).

## Audit checklist

- [ ] **HttpClient per-call — HIGH (socket exhaustion)** —
      `grep -rnE 'new HttpClient\(' --include='*.cs' . | head` (prefer IHttpClientFactory)
- [ ] **IDisposable not in using — MEDIUM** —
      `grep -rnE 'new (SqlConnection|FileStream|StreamReader|StreamWriter|MemoryStream|HttpResponseMessage)\(' --include='*.cs' . | head`
      (verify using/await using)
- [ ] **DI lifetime bugs — MEDIUM/HIGH (captive dependency)** —
      `grep -rnE 'AddSingleton|AddScoped|AddTransient' --include='*.cs' . | head` ;
      `grep -rnE 'GetService|GetRequiredService|IServiceProvider' --include='*.cs' . | head`
      (service locator?)
- [ ] **Mutable static state — MEDIUM** —
      `grep -rnE '^[[:space:]]*((public|private|protected|internal)[[:space:]]+)*static[[:space:]]+[A-Za-z_][A-Za-z0-9_<>,?. ]*(\[\])?[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]*(=|;|\{)' --include='*.cs' . | grep -vwE 'readonly|const|class|struct|record|interface|enum|delegate'`
      (static fields and properties. The earlier one-pattern form used a `(?!` lookahead, which
      POSIX ERE rejects: exit 2 under BSD grep and ugrep alike, measured 2026-09-24)
- [ ] **Exception handler not first in the pipeline (§4) — MEDIUM** — per file, the first
      `app.Use…` call other than the developer page should be the handler:
      `grep -rlE 'UseExceptionHandler' --include='*.cs' . | while IFS= read -r f; do grep -E 'app\.Use[A-Z]' "$f" | grep -v UseDeveloperExceptionPage | head -n 1 | grep -q UseExceptionHandler || echo "$f: middleware registered before UseExceptionHandler"; done`
- [ ] **throw ex / swallow — MEDIUM (see rules/01)** —
      `grep -rnE 'throw ex;' --include='*.cs' .`
- [ ] **Mutable collection exposed — LOW** —
      `grep -rnE 'public (List|Dictionary|HashSet)<' --include='*.cs' . | head` (prefer
      IReadOnly* / encapsulate)
- [ ] **Assembly boundary widened for production code (§6) — MEDIUM** —
      `grep -rn 'InternalsVisibleTo' --include='*.cs' --include='*.csproj' --include='*.props' . | grep -vi 'test'`
      (§6 keeps it for test access; a production friend assembly couples two assemblies'
      internals. Measured on SDK 10.0.401: a csproj `<InternalsVisibleTo Include="..." />` item
      emits the same `[assembly: InternalsVisibleTo]` attribute, so search both)
- [ ] **In-band sentinels (§1a) — `int?` over a magic int; TryParse's bool is the signal** —
      `grep -rnE 'return -1;' --include='*.cs' .` (producer; prefer int?);
      `grep -rnE 'TryParse\([^)]*out var [a-z]+\);' --include='*.cs' .` (bool DISCARDED -> out
      is 0 on failure)
- [ ] **Authentication endpoints with no rate limit — HIGH** (§7) — auth-looking routes with no
      limiter on the same line:
      `grep -rniE 'MapIdentityApi|(Map(Post|Get|Put|Group)|Http(Post|Get|Put)|Route)\("[^"]*(login|signin|sign-in|token|register|signup|password|otp|mfa|2fa)' --include='*.cs' . | grep -vE 'RequireRateLimiting|EnableRateLimiting'`
      (a policy on the parent `MapGroup`, on the next line, on the controller class, or a
      `GlobalLimiter` is invisible to this, so confirm each hit) ; and whether anything is
      limited at all:
      `err=$(grep -rlE 'AddRateLimiter' --include='*.cs' . 2>&1 >/dev/null); rc=$?; case $rc in 0) ;; 1) echo "no AddRateLimiter: nothing is rate limited -- HIGH if the sweep above listed an auth route" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
      ; then read each `PartitionedRateLimiter`/`RateLimitPartition` key: a constant key is one
      global bucket, and a raw header or path value is unbounded
- [ ] **Request limits removed — MEDIUM, HIGH on an anonymous endpoint** (§7) —
      `grep -rnE 'MaxRequestBodySize"?[[:space:]]*[=:][[:space:]]*null|DisableRequestSizeLimit|(MultipartBodyLengthLimit|MultipartHeadersLengthLimit|ValueCountLimit|ValueLengthLimit|KeyLengthLimit|BufferBodyLengthLimit|MaxRequestBodySize)[[:space:]]*=[[:space:]]*(int|long)\.MaxValue|Min(RequestBody|Response)DataRate[[:space:]]*=[[:space:]]*null' --include='*.cs' --include='*.json' .`
      ; connection caps (default unlimited):
      `grep -rnE 'MaxConcurrent(Upgraded)?Connections' --include='*.cs' --include='*.json' . || echo "no Kestrel connection cap (default unlimited): confirm a proxy caps connections"`
