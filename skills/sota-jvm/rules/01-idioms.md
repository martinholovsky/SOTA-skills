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
- **Time: `java.time`, an instant type for instants, `nanoTime` for intervals.**
  `LocalDateTime` *"does not store or represent a time-zone"* and *"cannot represent an
  instant on the time-line"* (its javadoc), so an event timestamp is an `Instant`,
  `OffsetDateTime` or `ZonedDateTime`. `System.nanoTime()` *"can only be used to measure
  elapsed time and is not related to any other notion of system or wall-clock time"*, which
  is exactly what a timeout or latency wants. `currentTimeMillis()` differences follow the wall
  clock. The legacy `SimpleDateFormat` is *"not synchronized"*, so a shared (`static`)
  instance races. `DateTimeFormatter` *"is immutable and thread-safe"*.
- **Exact decimals: `BigDecimal` from a `String` or `BigDecimal.valueOf(double)`, never
  `new BigDecimal(double)`.** Measured on JDK 25: `new BigDecimal(0.1)` is
  `0.1000000000000000055511151231257827021181583404541015625`, while `new BigDecimal("0.1")`
  and `valueOf(0.1)` are `0.1`. `equals` compares scale (`1.0` equals `1.00` is `false`;
  `compareTo` is `0`), and a `divide` without a scale and `RoundingMode` throws
  `ArithmeticException` on `1/3`. Money is never `double`.
- **Arithmetic edge cases: reject non-finite input, use the `Math.*Exact` family at the
  extremes.** Measured on JDK 25 and 21: `Double.parseDouble` (and Kotlin's `String.toDouble()`,
  which calls it) accepts `"NaN"`, `"Infinity"`, `"-Infinity"`, padded `" NaN "`, hex `"0x1p3"`,
  and returns `Infinity` for `"1e400"`; lowercase `"nan"`/`"inf"` throw. Every comparison with
  NaN is false, so `if (x < min || x > max) reject()` lets NaN through, and `(long) NaN` is `0`.
  Call `Double.isFinite(x)` (Kotlin `x.isFinite()`) *before* the range check; `Math.clamp`
  (21+) passes NaN straight through. Integer `/` and `%` by zero throw `ArithmeticException`
  (so does `BigDecimal.divide` by zero), but `double` division yields `Infinity`: guard the
  divisor explicitly. Plain `int`/`long` ops wrap silently: `Integer.MIN_VALUE / -1`, `-MIN_VALUE`
  and `Math.abs(MIN_VALUE)` all return `MIN_VALUE` (so `Math.abs(hashCode()) % n` can be
  negative; use `Math.floorMod`). Use `Math.addExact`/`subtractExact`/`multiplyExact`/
  `negateExact`/`toIntExact`, `absExact` (15+) and `divideExact`/`floorDivExact` (18+), which
  throw on overflow, or `long`/`BigInteger` for a multi-term product (`qty * priceCents / 1000`
  on `int` returned `705032` for `1_000_000 * 5_000`). Unit conversion: `secs * 1_000_000_000L`
  wraps, `TimeUnit.SECONDS.toNanos(x)` *saturates* to `Long.MAX_VALUE` without telling you, and
  `Duration.ofSeconds(x).toNanos()` throws: pick the throwing form, or bound `x` first. (OWASP
  Go-SCP general coding practices; OWASP SCSVS arithmetic.)

## 2. Modern Kotlin idioms (2.x)

- Null-safety is the headline feature: prefer non-null types; use `?`, `?.`,
  `?:` (Elvis), and `requireNotNull`/`checkNotNull` at boundaries. Avoid `!!`
  (it's an assertion that throws) except where you've truly proven non-null.
- `data class` for value types; `val` over `var`; `when` (exhaustive over
  sealed/enum) over if-chains; immutable collections (`listOf`/`mapOf`) by
  default.
- **A `data class` with a `private` or `internal` constructor still has a public `copy()`.**
  So `PositiveInt.create(42)!!.copy(value = -1)` builds an instance the validating factory
  would have refused (KT-11914). The fix was planned as a default change: Kotlin 2.0.20 warns,
  and the plan was to make it an error and then switch the default. That plan was **declined
  on 2026-09-08** (KTLC-22). KT-89123, in 2.5.0-Beta1, keeps it a warning with no end date,
  because too much code had not migrated and value classes are expected to take this role.
  So `copy()` stays public by default. Opt in per class with `@ConsistentCopyVisibility`, or
  for a whole module with `-Xconsistent-data-class-copy-visibility`. `@ExposedCopyVisibility`
  silences the warning and keeps the hole. Either way, **put the invariant in `init {}`**
  (`require(value > 0)`). `copy()` goes through the primary constructor, so the check runs on
  every copy too. A factory is not the place for it
  ([KTLC-22](https://youtrack.jetbrains.com/issue/KTLC-22),
  [KT-89123](https://youtrack.jetbrains.com/issue/KT-89123),
  [ConsistentCopyVisibility](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/-consistent-copy-visibility/)).
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
- **An `Error` is not a failure to recover from.** A `catch` of `Error`, or of `Throwable`
  (which contains it), may log and rethrow, and nothing else: no fallback, no retry, no
  carrying on. The JDK Javadoc says an `Error` signals "serious problems that a reasonable
  application should not try to catch"; a `VirtualMachineError` (`OutOfMemoryError`,
  `StackOverflowError`) says the JVM "is broken or has run out of resources necessary for it
  to continue operating"; a `LinkageError` says a class you depend on changed incompatibly
  after you were compiled. Code interrupted by one may have left its own state half-updated.
  Wrapping it in an unchecked exception that a caller catches is the same recovery by another
  route. Kotlin's `runCatching` is a `catch (e: Throwable)` (stdlib `Result.kt`), so rethrow
  an `Error` out of its failure path. The one place to catch `Throwable` is a last-resort
  boundary (an `UncaughtExceptionHandler`, a worker loop) that logs and then exits or rethrows.
  OWASP: Code Review Guide v2.

## 5. Immutability and finality

- Default to immutable: records, `final` fields/vars, Kotlin `val`, unmodifiable
  collection views. Immutable objects are inherently thread-safe (`rules/03`).
- Mark classes not designed for inheritance `final` (Java) — Kotlin classes are
  final by default (`open` to allow). Favor composition over inheritance.

## Audit checklist

- [ ] **Kotlin !! (non-null assertion) — MEDIUM (latent NPE)** —
      `grep -rnE '!!' --include='*.kt' . | grep -v '!!='`
- [ ] **`data class` whose non-public constructor leaks through `copy()` (§2) — MEDIUM, HIGH
      when the factory enforces a security or money invariant** — prints each such class with
      no `@ConsistentCopyVisibility` on its own line or the line above:
      `grep -rnE -B1 'data[[:space:]]+class[[:space:]]+[A-Za-z0-9_]+[[:space:]]*(<[^>]*>)?[[:space:]]*(@[A-Za-z]+[[:space:]]+)*(private|internal)[[:space:]]+constructor' --include='*.kt' . | awk '/data[[:space:]]+class/ && /(private|internal)[[:space:]]+constructor/ {if(p !~ /ConsistentCopyVisibility/ && $0 !~ /ConsistentCopyVisibility/) print; p=""; next} {p=$0}'`
      ; `grep -rn 'consistent-data-class-copy-visibility' --include='*.gradle*' --include='pom.xml' . || echo "flag not set: every hit above is live"`
      (a hit is clean if its `init {}` enforces the factory's rule; read it)
      `grep -rnzoE 'catch *\([^)]*\) *\{\s*\}' --include='*.java' --include='*.kt' .` ;
      `grep -rnE 'catch *\((Exception|Throwable)|catch *\([^)]*:[[:space:]]*(Exception|Throwable)[[:space:]]*\)' --include='*.java' --include='*.kt' .`
      (the second form is Kotlin's `catch (e: Exception)`, which the Java form never matched)
- [ ] **`Error`/`Throwable` caught and not rethrown (§4) — HIGH (the program keeps running on a
      JVM that reported itself broken)** — prints each such `catch` with no `throw` in the
      four lines after it:
      `grep -rnE -A4 'catch[[:space:]]*\(([^)]*[^A-Za-z.])?(java\.lang\.)?(Throwable|Error|VirtualMachineError|OutOfMemoryError|StackOverflowError|LinkageError)([^A-Za-z]|$)' --include='*.java' --include='*.kt' . | awk '/catch[[:space:]]*\(([^)]*[^A-Za-z.])?(java\.lang\.)?(Throwable|Error|VirtualMachineError|OutOfMemoryError|StackOverflowError|LinkageError)([^A-Za-z]|$)/ {if(h!=""&&!t)print h; h=$0; t=($0 ~ /throw[[:space:]]/); next} /throw[[:space:]]/{t=1} /^--$/{if(h!=""&&!t)print h; h=""} END{if(h!=""&&!t)print h}'`
      (a `throw new ...Exception(e)` passes the probe but is recovery by wrapping; read those;
      `runCatching` needs a separate read)
- [ ] **Legacy idioms — LOW** —
      `grep -rnE 'new (ArrayList|HashMap|HashSet)<>\(\)' --include='*.java' .` (consider List.of
      / records); `grep -rnE '\braw\b|new Vector|new Hashtable' --include='*.java' .` ;
      `grep -rn 'Optional<' --include='*.java' . | grep -iE 'private .*Optional|(Optional<[^>]+>) [a-z]+\)'`
      (Optional field/param)
- [ ] **Time handling (§1) — MEDIUM, HIGH for a shared formatter** —
      `grep -rnE 'static[^=;(]*(SimpleDateFormat|DateFormat)[[:space:]]' --include='*.java' --include='*.kt' .`
      (a shared legacy formatter: a data race) ;
      `grep -rnE 'currentTimeMillis\(\)[[:space:]]*-|-[[:space:]]*System\.currentTimeMillis\(\)' --include='*.java' --include='*.kt' .`
      (an interval on the wall clock; use `nanoTime`) ;
      `grep -rnE 'java\.util\.(Date|Calendar)|LocalDateTime\.now\(' --include='*.java' --include='*.kt' .`
      (legacy types, or a zone-less "now" that is later stored or compared as an instant)
- [ ] **Mutable returns / collections from APIs — LOW** —
      `grep -rnE 'return (this\.)?[a-zA-Z]*[Ll]ist;' --include='*.java' .` (verify defensive
      copy / unmodifiable)
- [ ] **Exact decimals (§1) — MEDIUM, HIGH in money paths** —
      `grep -rnE 'new BigDecimal\([[:space:]]*-?[0-9]+\.[0-9]|new BigDecimal\([[:space:]]*[a-z][A-Za-z0-9_]*[[:space:]]*\)' --include='*.java' --include='*.kt' .`
      (a double literal, or a variable whose type you then check) ;
      `grep -rnE '\.divide\([^,()]*\)|BigDecimal[^;]*\.equals\(' --include='*.java' --include='*.kt' .`
      (a divide with no scale or `RoundingMode`; scale-sensitive equality)
- [ ] **Arithmetic edge cases: NaN/Infinity input, overflow at MIN_VALUE, unit conversion (§1) —
      MEDIUM, HIGH on money, quota or timeout paths** —
      `grep -rlE 'Double\.(parseDouble|valueOf)\(|Float\.(parseFloat|valueOf)\(|\.to(Double|Float)(OrNull)?\(\)' --include='*.java' --include='*.kt' . | while IFS= read -r f; do grep -qE 'isFinite|isNaN' "$f" || echo "$f"; done`
      (a file that parses a float and never checks finiteness) ;
      `grep -rnE 'Math\.abs\([^;]*hashCode\(\)|TimeUnit\.[A-Z]+\.to(Nanos|Micros|Millis)\(|\*[[:space:]]*1_?000_?000' --include='*.java' --include='*.kt' .`
      (`abs` of a hash that can be `MIN_VALUE`; a saturating or hand-rolled unit conversion)
- [ ] **Analyzer enforcement Error Prone + NullAway (Java); detekt + ktlint (Kotlin)**