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
  `IHttpClientFactory` (typed/named clients) or a single long-lived instance.
- Don't dispose objects you don't own (e.g. injected/DI-managed singletons,
  `HttpClient` from the factory).

## 4. Exceptions in the contract

- Throw specific BCL exceptions (`ArgumentException`, `InvalidOperationException`,
  `ArgumentNullException`) before custom ones; document thrown types. Don't leak
  low-level exceptions across an abstraction — wrap, preserving `InnerException`.
- Validate arguments with guard helpers (`ArgumentNullException.ThrowIfNull`,
  `ArgumentOutOfRangeException.ThrowIf...`).

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

## Audit checklist

```bash
# HttpClient per-call — HIGH (socket exhaustion)
grep -rnE 'new HttpClient\(' --include='*.cs' . | head           # prefer IHttpClientFactory

# IDisposable not in using — MEDIUM
grep -rnE 'new (SqlConnection|FileStream|StreamReader|StreamWriter|MemoryStream|HttpResponseMessage)\(' --include='*.cs' . \
  | head     # verify using/await using

# DI lifetime bugs — MEDIUM/HIGH (captive dependency)
grep -rnE 'AddSingleton|AddScoped|AddTransient' --include='*.cs' . | head
grep -rnE 'GetService|GetRequiredService|IServiceProvider' --include='*.cs' . | head  # service locator?

# Mutable static state — MEDIUM
grep -rnE 'static (?!readonly|class|void|async|partial)[A-Za-z<>\[\]?]+ [A-Za-z]' --include='*.cs' . | head

# throw ex / swallow — MEDIUM (see rules/01)
grep -rnE 'throw ex;' --include='*.cs' .

# Mutable collection exposed — LOW
grep -rnE 'public (List|Dictionary|HashSet)<' --include='*.cs' . | head   # prefer IReadOnly* / encapsulate

# In-band sentinels (§1a) — `int?` over a magic int; TryParse's bool is the signal
grep -rnE 'return -1;' --include='*.cs' .                       # producer; prefer int?
grep -rnE 'TryParse\([^)]*out var [a-z]+\);' --include='*.cs' .   # bool DISCARDED -> out is 0 on failure
```
