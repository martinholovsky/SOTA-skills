# 02 — API, nullability, immutability, exceptions, resources

Good JVM APIs make illegal states unrepresentable and lifecycles explicit. This
file covers type/API design; idioms are in `01`, concurrency in `03`.

## 1. Nullability is part of the type

- **Kotlin**: the type system carries it — design APIs in non-null types,
  accept/return `T?` only where absence is meaningful. Guard Java platform
  types (`rules/01`) at the boundary with `requireNotNull`.
- **Java**: there is no built-in nullable type, so make it *checked*:
  - `Optional<T>` as a **return** type for "maybe absent" (Bloch: not for
    fields, parameters, or collections — an empty collection is the absence).
  - Annotate with `@Nullable`/`@NonNull` (JSpecify is the emerging standard) and
    enforce with **NullAway**/Error Prone so violations fail the build.
  - Never return `null` for a collection/array — return empty.
- Validate arguments at public-method entry (`Objects.requireNonNull`,
  `require`/`check` in Kotlin) and fail fast with a clear message.

## 2. Immutability and value semantics

- Prefer immutable types (records, `final` fields, Kotlin `data class` with
  `val`). Immutable = thread-safe and cache-friendly.
- Return defensive copies or unmodifiable views (`List.copyOf`,
  `Collections.unmodifiableList`, Kotlin read-only `List`) — never hand out a
  reference to internal mutable state. (Note Kotlin read-only types are not
  *immutable*, just a read-only view; the backing list can still change.)
- Builders for objects with many optional fields (or Kotlin named/default
  args, which remove most builder needs).

## 3. equals / hashCode / toString

- Override them as a set or none. Records and Kotlin `data class` generate a
  consistent set — prefer them over hand-written equality.
- Hand-written `equals` must be reflexive/symmetric/transitive/consistent and
  match `hashCode`; an object used as a `HashMap` key with `equals` but no
  `hashCode` (or mutated after insertion) silently misbehaves (MEDIUM).
- Don't put mutable fields in `equals`/`hashCode` if the object is a map key.

## 4. Exceptions in the API contract

- Document thrown exceptions (`@throws`); throw the most specific standard type
  (`IllegalArgumentException`, `IllegalStateException`,
  `UnsupportedOperationException`) before inventing one.
- Don't declare `throws Exception`; don't leak implementation exceptions across
  an abstraction boundary — translate to the layer's exception, preserving the
  cause.
- Checked exceptions only for recoverable conditions the caller must act on;
  overuse pushes callers to swallow. Kotlin has none — document failure modes.

## 5. Resource lifecycle

- Everything `AutoCloseable`/`Closeable` is acquired in **try-with-resources**
  (Java) or **`use {}`** (Kotlin) — never a bare `close()` in a `finally` you
  can forget on an early return/throw. Multiple resources nest correctly and
  close in reverse order.
- For pooled resources (DB connections, HTTP clients), return them to the pool
  in the same construct. Don't store a resource you opened in a field without a
  clear close contract and an `AutoCloseable` owner.

## 6. Module/package structure

- Package by feature, not by layer; keep visibility tight (`private`/
  package-private; Kotlin `internal`). Expose the minimum public surface.
- **JPMS** (`module-info.java`) for libraries that benefit from strong
  encapsulation and explicit `requires`/`exports`; many apps use the classpath
  with a build-tool module structure instead — choose deliberately.
- Dependency injection (constructor injection, Spring/Dagger/Koin) over static
  singletons and service locators; mutable static state is a MEDIUM finding
  (testability + concurrency hazard).

## Audit checklist

```bash
# Optional misuse — LOW (field/param/collection)
grep -rnE '(private|protected|public)\s+Optional<' --include='*.java' .
grep -rnE '\(.*Optional<[^>]+>\s+\w+\)' --include='*.java' .

# Mutable internal state handed out — MEDIUM
grep -rnE 'return [a-zA-Z_]+;\s*$' --include='*.java' . | grep -iE 'list|map|set|array'  # verify copy/unmodifiable

# equals without hashCode (and vice versa) — MEDIUM
grep -rln 'public boolean equals' --include='*.java' . | xargs -I{} sh -c 'grep -L "hashCode" {}'

# Bare close()/no try-with-resources — MEDIUM
grep -rnE '\.close\(\)' --include='*.java' --include='*.kt' .   # verify try-with-resources/use
grep -rn 'finally' --include='*.java' . | grep -i close

# Mutable static state — MEDIUM
grep -rnE 'static (?!final)[A-Za-z<>]+ [a-z]' --include='*.java' .

# throws Exception / overbroad — LOW/MEDIUM
grep -rn 'throws Exception' --include='*.java' .

# Enforcement: Error Prone + NullAway, SpotBugs, detekt
```
