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
  N+1 with `IQueryable` (`rules/04`/perf), and allocation/closure cost on hot
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

```bash
# Null-forgiving overuse — MEDIUM (defeats NRT)
grep -rnE '[A-Za-z0-9_)\]]\!\.' --include='*.cs' . | grep -v '!=' | head    # x!.Member
# Is NRT even enabled?
grep -rniE '<Nullable>\s*enable' *.csproj Directory.Build.props 2>/dev/null || echo "NRT not enabled — HIGH"

# Swallowed exceptions / throw ex — MEDIUM
grep -rnzoE 'catch\s*\([^)]*\)\s*\{\s*\}' --include='*.cs' .
grep -rnE 'throw ex;' --include='*.cs' .                     # loses stack trace
grep -rnE 'catch \(Exception' --include='*.cs' . | head

# Legacy idioms — LOW
grep -rnE '\bclass\b' --include='*.cs' . | head             # DTOs that should be records?
grep -rnE 'namespace [A-Za-z0-9_.]+\s*\{' --include='*.cs' .  # non-file-scoped namespaces

# Multiple enumeration / LINQ on hot path — LOW (verify)
grep -rnE '\.Where\(|\.Select\(|\.Count\(\)' --include='*.cs' . | head

# Broad analyzer pass (idioms): enable .NET analyzers + IDE rules in CI (rules/06)
```
