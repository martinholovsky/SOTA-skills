# 01 — Idioms: modern Java & Kotlin, error handling

Write to the current language, not Java 8. The through-line is **immutability,
the type system, and expression-oriented code**. References:
[Java 25 docs](https://docs.oracle.com/en/java/javase/25/),
[Kotlin docs](https://kotlinlang.org/docs/home.html), Effective Java (Bloch).

## 1. Modern Java idioms (21/25)

- **Records** for immutable data carriers — auto `equals`/`hashCode`/`toString`,
  final fields. Add compact constructors for validation. Replace hand-written
  POJOs and most "value" classes.
- **Sealed** interfaces/classes + **pattern matching for `switch`** for closed
  hierarchies — the compiler enforces exhaustiveness, no `default` needed.
  Replaces visitor boilerplate and instanceof-cascades.
- `switch` *expressions* (arrow form, yields a value) over fall-through
  statements; record deconstruction patterns in `switch`/`instanceof`.
- **Text blocks** (`"""`) for multi-line literals; `var` for local inference
  where the type is obvious (not for public API). Streams for transformation,
  but a plain loop when it's clearer.
- Prefer `List.of`/`Map.of`/`toList()` (immutable) over mutable collections you
  return from APIs.

## 2. Modern Kotlin idioms (2.x)

- Null-safety is the headline feature: prefer non-null types; use `?`, `?.`,
  `?:` (Elvis), and `requireNotNull`/`checkNotNull` at boundaries. Avoid `!!`
  (it's an assertion that throws) except where you've truly proven non-null.
- `data class` for value types; `val` over `var`; `when` (exhaustive over
  sealed/enum) over if-chains; immutable collections (`listOf`/`mapOf`) by
  default.
- Scope functions (`let`/`run`/`apply`/`also`/`with`) for null-safe transforms
  and configuration — but don't over-nest them into write-only code.
- Extension functions over utility classes; `sealed`/`enum` + `when` for state;
  `object` for singletons; `companion object` for factories.
- `value class` (inline class) for type-safe wrappers without allocation
  overhead. `Result<T>` / sealed result types for expected failures.

## 3. Java ↔ Kotlin interop

- **Platform types** (`String!`) are the #1 interop NPE source: a Java method
  with no nullability annotation is seen by Kotlin as "could be null but
  unchecked." Treat Java return values as nullable at the boundary, or annotate
  the Java side with JSpecify `@Nullable`/`@NonNull` (the standard — Kotlin 2
  translates JSpecify to its nullability) so Kotlin enforces it.
- Annotate Java APIs consumed by Kotlin; use `@JvmStatic`/`@JvmOverloads`/
  `@JvmName` when exposing Kotlin to Java. Kotlin `data class` `copy`/
  destructuring won't appear in Java — design the cross-language surface
  deliberately.

## 4. Error handling

- **Unchecked exceptions** for programming errors and most application errors;
  reserve checked exceptions for recoverable conditions the caller must handle
  (and they don't exist in Kotlin — all exceptions are unchecked).
- Never swallow: an empty `catch {}` or `catch (Exception e) {}` that drops the
  error is a MEDIUM–HIGH finding. Catch the narrowest type; rethrow or wrap
  preserving the cause (`new XException("...", e)`); log-or-throw, not both.
- Don't use exceptions for control flow. For *expected* failures prefer a typed
  return: Java sealed result or `Optional`; Kotlin `Result<T>`/sealed class.
- Kotlin: don't catch `CancellationException` and swallow it in coroutines (it
  breaks structured cancellation — `rules/03`). Use `runCatching` judiciously,
  not as a blanket swallow.

## 5. Immutability and finality

- Default to immutable: records, `final` fields/vars, Kotlin `val`, unmodifiable
  collection views. Immutable objects are inherently thread-safe (`rules/03`).
- Mark classes not designed for inheritance `final` (Java) — Kotlin classes are
  final by default (`open` to allow). Favor composition over inheritance.

## Audit checklist

```bash
# Kotlin !! (non-null assertion) — MEDIUM (latent NPE)
grep -rnE '!!' --include='*.kt' . | grep -v '!!='

# Swallowed exceptions — MEDIUM/HIGH
grep -rnzoE 'catch *\([^)]*\) *\{\s*\}' --include='*.java' --include='*.kt' .
grep -rnE 'catch *\((Exception|Throwable)' --include='*.java' --include='*.kt' .

# Legacy idioms — LOW
grep -rnE 'new (ArrayList|HashMap|HashSet)<>\(\)' --include='*.java' .   # consider List.of / records
grep -rnE '\braw\b|new Vector|new Hashtable' --include='*.java' .
grep -rn 'Optional<' --include='*.java' . | grep -iE 'private .*Optional|(Optional<[^>]+>) [a-z]+\)'  # Optional field/param

# Mutable returns / collections from APIs — LOW
grep -rnE 'return (this\.)?[a-zA-Z]*[Ll]ist;' --include='*.java' .   # verify defensive copy / unmodifiable

# Analyzer enforcement
#   Error Prone + NullAway (Java); detekt + ktlint (Kotlin)
```
