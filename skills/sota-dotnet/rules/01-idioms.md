# 01 — Idioms: modern C#, nullability, error handling

Write to current C# (14 / .NET 10), not C# 7. The through-line is
**immutability, the nullable-aware type system, and expression-oriented code**.
Reference: [What's new in C#](https://learn.microsoft.com/en-us/dotnet/csharp/whats-new/),
[.NET 10](https://learn.microsoft.com/en-us/dotnet/core/whats-new/dotnet-10/overview).

## 1. Records and immutability

- **`record`** (reference) and **`record struct`** for immutable data carriers —
  value equality, `with` expressions, deconstruction, concise `ToString`.
  Replace hand-written DTO/value classes. Use `init`-only setters for
  immutable-after-construction.
- Prefer immutable by default: `readonly` fields, `init` properties, immutable
  collections where it matters. Immutable types are thread-safe (`rules/03`).
- `record class` for entities with identity-by-value semantics; plain `class` for
  mutable services/stateful objects; `struct`/`record struct` for small values
  (`rules/05`).
- **A timestamp field is `DateTimeOffset` or a UTC `DateTime`, never `DateTime.Now`.** `Now`
  is *"expressed as the local time"* and returns `Kind` `Local` (measured on the .NET 10 SDK
  image: `Now.Kind=Local`, `UtcNow.Kind=Utc`), so a stored value depends on the host's zone
  and shifts across DST. The docs point to `DateTimeOffset` for *"a single point in time"*.
  Intervals and timeouts are not dates: the same page calls `Now` unsuitable for measuring
  and names `Stopwatch` instead.
- **Money is `decimal`, never `double`/`float`.** `decimal` is a built-in 16-byte decimal
  type of 28-29 digits (measured on the .NET 10 SDK image: `0.1m + 0.2m == 0.3m` is `true`; the `double` sum
  is not). Three traps remain. `Math.Round` and `decimal.Round` default to
  `MidpointRounding.ToEven` (the docs: *"By default, the Round method uses the round to
  nearest even convention"*; measured, `Math.Round(2.5m)` is `2`), so pass the mode the
  business rule names. `(long)(d * 100)` on a `double` truncates (`19.99` gives `1998`,
  measured). And a `double`→`decimal` conversion rounds to 15 significant digits (measured:
  `(decimal)(0.1 + 0.2)` is `0.3`), so converting late hides the binary error instead of
  removing it: keep the value `decimal` from parse to storage (`decimal.Parse`,
  `JsonElement.GetDecimal`).

## 2. Nullable reference types (NRT)

- Enable `<Nullable>enable</Nullable>` solution-wide. The compiler then tracks
  null-flow: `string` is non-null, `string?` may be null. This eliminates a huge
  class of `NullReferenceException` at compile time.
- **Honor the warnings** — don't silence with the null-forgiving operator `!`
  unless you've genuinely proven non-null (and comment why). Scattered `!` is a
  MEDIUM finding: it disables the very safety you enabled.
- Annotate APIs precisely (`?`, `[NotNullWhen]`, `[MaybeNull]`); guard external/
  deserialized input at the boundary (it can be null regardless of annotations).

## 3. Pattern matching & expressions

- Prefer `switch` **expressions** and pattern matching (type/property/relational/
  list patterns) over if-cascades and `switch` statements — exhaustive, concise,
  value-returning.
- Use expression-bodied members, target-typed `new`, collection expressions
  (`[1, 2, 3]`), and `nameof`. Use `var` when the type is obvious from the RHS.

## 4. C# 12–14 niceties

- Primary constructors (classes/structs), collection expressions, file-scoped
  namespaces (`namespace Foo;`), required members (`required`), raw string
  literals.
- C# 14: **extension members** (extension properties/operators/static members),
  the **`field`** contextual keyword (access the synthesized backing field in an
  accessor without declaring it), and broader `Span<T>`/`ReadOnlySpan<T>`/`T[]`
  conversions. Use where they clarify; don't chase novelty.

## 5. LINQ discipline

- LINQ for clarity over hand loops, but beware: multiple enumeration of an
  `IEnumerable` (materialize with `ToList()` once if iterated repeatedly), hidden
  N+1 with `IQueryable` and EF Core lazy loading (`rules/05` §4), and allocation/closure cost on hot
  paths (`rules/05`). Know when a query executes (deferred vs eager).

## 6. Error handling

- Throw the most specific exception type; don't catch `Exception`/`Exception e`
  just to swallow or log-and-continue on a path that must abort. Preserve stack
  with `throw;` (not `throw ex;`).
- Don't use exceptions for control flow. Use the `TryParse`/`Try...` pattern or a
  result type for expected failures on hot paths. `ArgumentNullException.ThrowIfNull`
  and `ArgumentException.ThrowIf...` for guard clauses.
- Exceptions are unchecked in C#; document what a public API throws.

## Audit checklist

- [ ] **Null-forgiving overuse — MEDIUM (defeats NRT)** —
      `grep -rnE '[A-Za-z0-9_)\]]\!\.' --include='*.cs' . | grep -v '!=' | head` (x!.Member)
- [ ] **Is NRT even enabled?** —
      `grep -rniE '<Nullable>\s*enable' . --include='*.csproj' --include='Directory.Build.props' || echo "NRT not enabled — HIGH"`
- [ ] **Swallowed exceptions / throw ex — MEDIUM** —
      `grep -rnzoE 'catch\s*\([^)]*\)\s*\{\s*\}' --include='*.cs' .` ;
      `grep -rnE 'throw ex;' --include='*.cs' .` (loses stack trace);
      `grep -rnE 'catch \(Exception' --include='*.cs' . | head`
- [ ] **Local time and wall-clock intervals (§1) — MEDIUM** —
      `grep -rnE 'DateTime\.Now([^[:alnum:]_]|$)' --include='*.cs' .` (local time: read each —
      stored, compared or sent is the finding; shown to a local user is not) ;
      `grep -rnE 'DateTime\.(Utc)?Now[[:space:]]*-|-[[:space:]]*[A-Za-z_.]*DateTime\.(Utc)?Now' --include='*.cs' .`
      (an interval on the wall clock; use `Stopwatch`)
- [ ] **Money in binary floats, default rounding (§1) — MEDIUM, HIGH in money paths** —
      `grep -rniE '(double|float)[[:space:]]+[a-z_]*(price|amount|total|balance|cost|fee|tax)' --include='*.cs' .`
      (money typed as a binary float) ;
      `grep -rnE '(Math|decimal|Decimal)\.Round\(' --include='*.cs' . | grep -v 'MidpointRounding'`
      (banker's rounding by default: confirm it is the rule the business names) ;
      `grep -rnE '\((long|int)\)[[:space:]]*\([^;]*\*[[:space:]]*100' --include='*.cs' .`
      (scaled to minor units by a truncating cast)
- [ ] **Legacy idioms — LOW** — `grep -rnE '\bclass\b' --include='*.cs' . | head` (DTOs that
      should be records?); `grep -rnE 'namespace [A-Za-z0-9_.]+\s*\{' --include='*.cs' .`
      (non-file-scoped namespaces)
- [ ] **Multiple enumeration / LINQ on hot path — LOW (verify)** —
      `grep -rnE '\.Where\(|\.Select\(|\.Count\(\)' --include='*.cs' . | head`
- [ ] **Broad analyzer pass (idioms): enable .NET analyzers + IDE rules in CI (rules/06)**