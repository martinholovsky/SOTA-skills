---
name: sota-dotnet
description: >-
  State-of-the-art C# / .NET engineering rules (2026 baseline, .NET 10 LTS /
  C# 14) that Claude applies when writing or auditing .NET code. Covers modern
  idioms (records, nullable reference types, pattern matching, spans, file-scoped
  namespaces), API/null/immutability/`IDisposable` design, async/await &
  concurrency (ConfigureAwait, channels, cancellation, TPL), security (OWASP
  .NET, deserialization — BinaryFormatter removed in .NET 9, EF/Dapper SQL
  injection, ASP.NET Core auth, Data Protection, crypto), performance (GC,
  Span<T>/Memory<T>, BenchmarkDotNet, Native AOT), and build/tooling/CI (dotnet
  CLI, NuGet lockfiles & supply chain, Roslyn analyzers, nullable). Trigger
  keywords - C#, .NET, dotnet, ASP.NET Core, async, await, Task, record,
  nullable reference types, Span, EF Core, Dapper, LINQ, NuGet, Roslyn analyzer,
  BinaryFormatter, Native AOT, BenchmarkDotNet, IDisposable, ConfigureAwait. Use
  for BOTH building .NET services/libraries and auditing them.
---

# SOTA C# / .NET (2026)

Expert-level rules for producing and auditing production .NET. The runtime is
memory-safe, so risk concentrates in **injection, deserialization, async
correctness, and dependency supply chain**. Baseline: **.NET 10 LTS** (released
Nov 2025, supported to Nov 2028) and **C# 14** (records, nullable reference
types, pattern matching, spans, extension members, the `field` keyword) — flag
where a control needs a specific version. Every rule states the *why*; every
rules file ends with an audit checklist of grep/analyzer patterns.

## Purpose

Two consumers, one source of truth:

- **BUILD mode** — generating C#/.NET: follow the rules as defaults. Enable
  **nullable reference types** and treat analyzer warnings as errors; prefer
  immutability and the async-all-the-way model. Deviate only with a comment.
- **AUDIT mode** — reviewing existing code: hunt violations with the audit
  checklists, classify by severity, report in the finding format below. SQL
  string-building and legacy deserialization are presumed exploitable.

## BUILD mode

1. Before writing, read the rules files relevant to the task (see index). A web
   API touching untrusted input + a DB + async needs `02`, `03`, `04`.
2. Apply the **top-10 non-negotiables** (below) unconditionally.
3. New projects: target the current LTS (`net10.0`), `<Nullable>enable</Nullable>`,
   `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>`,
   `<AnalysisLevel>latest-Recommended</AnalysisLevel>`, NuGet lockfile +
   `RestoreLockedMode` in CI, and `dotnet format` from day one (`rules/06`).
4. Async all the way down — never block on async (`.Result`/`.Wait()`/
   `GetAwaiter().GetResult()`) (`rules/03`). Use `CancellationToken` end to end.
5. Prefer the BCL and well-known libraries; parameterize all data access; use
   the framework's auth/Data Protection rather than rolling your own (`rules/04`).
6. When you take a sharp path (reflection, `unsafe`, `DynamicMethod`, suppressing
   a nullable/analyzer warning), leave a `// NOTE(sota):` explaining why.

## AUDIT mode

Work each relevant rules file's audit checklist against the target. Run the
greps and the Roslyn analyzers (incl. the security CA rules); confirm hits
manually. Check the dependency tree against known-CVE databases.

### Severity conventions

| Severity | Meaning | Examples |
|---|---|---|
| **CRITICAL** | Exploitable on reachable input | SQL via string interpolation/concat into `FromSqlRaw`/`ExecuteSqlRaw`/Dapper, `BinaryFormatter`/`NetDataContractSerializer`/`LosFormatter` or JSON `TypeNameHandling.All` on untrusted data, command injection, deserialization gadget |
| **HIGH** | Likely incident or security weakness | Missing auth on an endpoint, disabled cert validation (`ServerCertificateCustomValidationCallback => true`), MD5/SHA-1 or `DES`/ECB for security, `Random` for tokens, blocking on async causing deadlock/thread-pool starvation, secrets in config/source |
| **MEDIUM** | Correctness/maintainability hazard | `async void` (non-handler), missing `ConfigureAwait(false)` in a library, `IDisposable` not disposed / no `using`, nullable warnings suppressed with `!`, swallowed exceptions, mutable static state |
| **LOW** | Idiom/perf debt | Sync-over-collection LINQ on hot path, needless allocations/boxing, `class` where a `record`/`struct` fits, not using `Span`/pooling on hot path |
| **INFO** | Style/doc/hygiene | formatting, naming, missing XML docs, nullable annotations absent (not enabled) |

### Finding format

```
[SEVERITY] File.cs:LINE — short title
  Rule: rules/NN-name.md § section
  Evidence: the offending line(s), verbatim
  Impact: one sentence — what executes/leaks/deadlocks, under what input
  Fix: concrete replacement code or action
  Effort: trivial | small | medium | large
```

Group findings by severity, CRITICAL first. End with: counts per severity, the
three highest-leverage fixes, and which checklists/analyzers were run.

## Rules index

| File | Read this when... |
|---|---|
| `rules/01-idioms.md` | Writing/reviewing any C#: records & `record struct`, nullable reference types, pattern matching/`switch` expressions, spans, LINQ discipline, `var`, expression vs statement, file-scoped namespaces, error handling, modern C# 12–14 features |
| `rules/02-design-api.md` | Designing types/APIs: nullable reference type discipline, immutability, `IDisposable`/`IAsyncDisposable` and `using`, exceptions, value vs reference types, `internal`/visibility, DI (the built-in container), options pattern |
| `rules/03-async-concurrency.md` | Anything `async`/`Task`/threads: async-all-the-way, never block (`.Result`/`.Wait()`), `ConfigureAwait(false)` in libraries, `CancellationToken` flow, `async void`, `Channel<T>`, `IAsyncEnumerable`, TPL/`Parallel`, thread-safety, `ValueTask` |
| `rules/04-security.md` | Any input crossing a trust boundary: SQL (EF Core/Dapper parameterization), legacy serializers (`BinaryFormatter` removed .NET 9) + JSON `TypeNameHandling`, command/path injection, ASP.NET Core authn/authz, antiforgery/CORS, Data Protection, crypto (`RandomNumberGenerator`, AES-GCM), secrets; OWASP .NET |
| `rules/05-performance.md` | Latency/throughput/memory work: GC (gen/SOH/LOH, server vs workstation), allocation reduction, `Span<T>`/`Memory<T>`/`ArrayPool`, `struct`/`record struct`, BenchmarkDotNet, async overhead, Native AOT / trimming, string handling |
| `rules/06-build-tooling-ci.md` | Setting up or auditing build/CI: SDK/TFM targeting, `Directory.Build.props`, nullable + warnings-as-errors, Roslyn analyzers (incl. security CA rules), `dotnet format`, NuGet lockfiles + supply chain (lock mode, source mapping, signed packages, CVE scan), SBOM. **Test *strategy* lives in `sota-testing`; this owns .NET build/test mechanics (xUnit/NUnit, Testcontainers).** |

## Top-10 non-negotiables

1. **No string-built SQL.** Parameterize: EF Core LINQ or parameters
   (`FromSql`/interpolated `FromSql`, never `FromSqlRaw`/`ExecuteSqlRaw` with
   concatenation); Dapper with parameters. Interpolated/concatenated SQL is
   CRITICAL. (`rules/04`)
2. **No unsafe deserialization.** `BinaryFormatter` is removed in .NET 9+ (throws);
   never reintroduce it or `NetDataContractSerializer`/`LosFormatter`/`SoapFormatter`,
   and never use `Json.NET` `TypeNameHandling.Auto/All` or `JsonSerializer` with
   an unrestricted type resolver on untrusted data. Use `System.Text.Json` with
   known types. (`rules/04`)
3. **Async all the way; never block on async.** No `.Result`, `.Wait()`,
   `.GetAwaiter().GetResult()` on a hot/request path (deadlock + thread-pool
   starvation). `async void` only for event handlers. (`rules/03`)
4. **Flow `CancellationToken` end to end** through async APIs and honor it.
   (`rules/03`)
5. **`ConfigureAwait(false)` in library code** (code with no sync context that
   doesn't need to resume on the original context). (`rules/03`)
6. **Nullable reference types enabled and honored.** `<Nullable>enable</Nullable>`;
   don't paper over warnings with the null-forgiving `!`. (`rules/01`, `rules/02`)
7. **Deterministic disposal.** Everything `IDisposable`/`IAsyncDisposable` is in a
   `using`/`await using` or owned by a DI-managed lifetime — `HttpClient` via
   `IHttpClientFactory`, not new-per-call. (`rules/02`)
8. **Crypto uses the right primitives.** `RandomNumberGenerator` (never `Random`)
   for tokens/keys/IVs; AES-GCM (not ECB); no MD5/SHA-1 for security; ASP.NET
   Core **Data Protection** for at-rest tokens; never disable TLS cert
   validation. (`rules/04`)
9. **AuthN/AuthZ enforced server-side** on every non-public endpoint
   (`[Authorize]`/policies/endpoint auth), antiforgery for cookie-auth POSTs,
   CORS locked to known origins. (`rules/04`)
10. **Analyzers + nullable + lockfile gate CI.** `TreatWarningsAsErrors`,
    Roslyn analyzers (incl. security CA rules), `dotnet format --verify-no-changes`,
    NuGet locked-mode restore + CVE scan. (`rules/06`)
