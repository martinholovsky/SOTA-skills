---
name: sota-jvm
description: >-
  State-of-the-art JVM engineering rules (2026 baseline) for Java and Kotlin
  that Claude applies when writing or auditing JVM code. Baseline Java 25 LTS
  (virtual threads final since 21; structured concurrency still preview),
  Kotlin 2.x. Covers modern idioms (records, sealed types, pattern matching,
  Kotlin null-safety/coroutines), API/null/immutability design, concurrency
  (virtual threads, JMM, java.util.concurrent, coroutines), security
  (deserialization/gadget chains, XXE, JNDI/Log4Shell-class, injection, JCA
  crypto; SEI CERT Oracle Java + OWASP), performance (G1/ZGC, JFR, GraalVM),
  and build/tooling/CI (Maven/Gradle, dependency-check, Error Prone/NullAway,
  SpotBugs, ktlint/detekt). Trigger keywords - Java, Kotlin, JVM, JDK,
  Spring, record, sealed, virtual thread, Loom, coroutine, suspend,
  ObjectInputStream, deserialization, XXE, JNDI, Log4Shell, Maven, Gradle,
  G1, ZGC, GraalVM, JMH, Optional, null-safety. Use for BOTH building JVM
  services/libraries and reviewing or auditing them.
---

# SOTA JVM — Java & Kotlin (2026)

Expert-level rules for producing and auditing production JVM code. The JVM is
memory-safe (no buffer overflows/UAF), so the risk shifts to **deserialization
and injection RCE, concurrency correctness, and dependency supply chain**.
Baseline: **Java 25 LTS** (records, sealed types, pattern matching, virtual
threads finalized in 21 via JEP 444; scoped values finalized in 25 via JEP 506;
structured concurrency is still *preview* — JEP 505 in 25 — don't present it
as final), **Kotlin 2.x**.
Per-language idioms differ; shared concerns (the JMM, the JCA, the build/
supply-chain story) are unified here. Every rule states the *why*; every rules
file ends with an audit checklist of grep/analyzer patterns.

## Purpose

Two consumers, one source of truth:

- **BUILD mode** — generating Java/Kotlin: follow the rules as defaults. Prefer
  immutability, null-safety, and the standard concurrency primitives. Deviate
  only with a comment justifying it.
- **AUDIT mode** — reviewing existing code: hunt violations with the audit
  checklists, classify by severity, report in the finding format below.
  Deserialization of untrusted data and string-built queries are presumed
  exploitable.

## BUILD mode

1. Before writing, read the rules files relevant to the task (see index). A web
   service handling untrusted input + threads + a DB needs `02`, `03`, `04`.
2. Apply the **top-10 non-negotiables** (below) unconditionally.
3. New projects: target the current LTS (Java 25), Maven or Gradle with a
   lockfile, Error Prone + NullAway (Java) or detekt + ktlint (Kotlin),
   SpotBugs/Find-Sec-Bugs, OWASP dependency-check/OSV-Scanner, and CI running
   all of it from day one (`rules/06`).
4. Prefer immutability (records, `final`, Kotlin `val`/`data class`,
   unmodifiable collections) and the type system (sealed hierarchies, no raw
   types, `Optional`/Kotlin nullable types) over runtime checks.
5. Never let untrusted bytes reach a deserializer, an XML parser with DTDs on,
   a JNDI lookup, or a string-built query/EL expression (`rules/04`).
6. When you must use a sharp tool (reflection, `ObjectInputStream`, `Unsafe`,
   a `@SuppressWarnings`), leave a `// NOTE(sota):` comment explaining why and
   what bounds it.

## AUDIT mode

Work each relevant rules file's audit checklist against the target. Run the
greps and analyzers (SpotBugs/Find-Sec-Bugs, Error Prone, detekt); confirm hits
manually. Check the dependency tree against known-CVE databases.

### Severity conventions

| Severity | Meaning | Examples |
|---|---|---|
| **CRITICAL** | Exploitable on reachable input | `ObjectInputStream.readObject` on untrusted data, JNDI lookup of attacker URL (Log4Shell), SpEL/OGNL/`ScriptEngine` eval of input, SQL via string concat, XXE with DTD enabled |
| **HIGH** | Likely incident or security weakness | `Runtime.exec`/`ProcessBuilder` with a shell + interpolation, missing TLS verification, `MessageDigest` MD5/SHA-1 or `Cipher` ECB/`DES` for security, `SecureRandom` seeded predictably, blocking pinning a carrier thread under load |
| **MEDIUM** | Correctness/maintainability hazard | Data race on shared mutable state, `equals` without `hashCode`, mutable static state, swallowed exceptions, Kotlin platform-type NPE, resource not in try-with-resources/`use` |
| **LOW** | Idiom/perf debt | Mutable collections returned from APIs, raw types, `Optional` fields/params, needless boxing on hot path, `synchronized` where `j.u.c` fits |
| **INFO** | Style/doc/hygiene | Formatting, naming, missing `@Override`/`@Nullable` annotations |

### Finding format

```
[SEVERITY] File.java:LINE — short title
  Rule: rules/NN-name.md § section
  Evidence: the offending line(s), verbatim
  Impact: one sentence — what executes/leaks/races, under what input
  Fix: concrete replacement code or action
  Effort: trivial | small | medium | large
```

Group findings by severity, CRITICAL first. End with: counts per severity, the
three highest-leverage fixes, and which checklists/analyzers were run.

## Rules index

| File | Read this when... |
|---|---|
| `rules/01-idioms.md` | Writing/reviewing any Java/Kotlin: records, sealed types, pattern matching, switch expressions, text blocks, `var`; Kotlin null-safety, `data`/`value` classes, `when`, scope functions, immutability, Java↔Kotlin interop, error handling |
| `rules/02-design-api.md` | Designing types/APIs: nullability discipline (`Optional`, `@Nullable`, Kotlin types, platform types), immutability, `equals`/`hashCode`/`toString`, exceptions (checked vs unchecked, Kotlin), `AutoCloseable`/try-with-resources/`use`, JPMS/package layout, DI |
| `rules/03-concurrency.md` | Anything with threads, executors, or shared state: virtual threads and pinning, structured concurrency (preview), `ExecutorService`, `CompletableFuture`, the Java Memory Model (`volatile`/`final`/happens-before), concurrent collections, Kotlin coroutines/structured concurrency/cancellation |
| `rules/04-security.md` | Any input crossing a trust boundary: Java deserialization + gadget chains + serialization filters, XXE, JNDI/LDAP (Log4Shell-class), expression-language/`ScriptEngine` injection, SQL/`Runtime.exec`, path traversal, JCA crypto (AES-GCM, `SecureRandom`, no MD5/ECB), TLS, secrets; SEI CERT Oracle Java + OWASP |
| `rules/05-performance.md` | Latency/throughput/memory work: GC choice (G1 default, Generational ZGC for low pause, Parallel for throughput), heap/`-Xmx` and container awareness, JIT/tiered/`-XX` basics, JFR + async-profiler, allocation/escape analysis, GraalVM native image trade-offs, JMH benchmarking |
| `rules/06-build-tooling-ci.md` | Setting up or auditing build/CI: Maven vs Gradle, dependency locking + supply chain (dependency-check/OSV-Scanner, signing, reproducible builds, SBOM), Error Prone/NullAway, SpotBugs/Find-Sec-Bugs, PMD, ktlint/detekt, spotless, JaCoCo. **Test *strategy* lives in `sota-testing`; this file owns JVM build/test mechanics (JUnit 5, Testcontainers wiring).** |

## Top-10 non-negotiables

1. **Never deserialize untrusted data with Java native serialization.**
   `ObjectInputStream.readObject` on attacker-controlled bytes is RCE via gadget
   chains. Use JSON/protobuf with a schema; if unavoidable, apply a strict
   `ObjectInputFilter` allowlist (JEP 290). (`rules/04`)
2. **No string-built queries or commands.** Parameterized JDBC/JPA only;
   `ProcessBuilder` with an argument list and no shell. String concat into
   SQL/HQL/JPQL/LDAP/OS commands is CRITICAL. (`rules/04`)
3. **XML parsers disable DTDs/external entities; no JNDI lookups or EL/script
   eval of input.** XXE, Log4Shell-class JNDI, and SpEL/OGNL/`ScriptEngine`
   injection are CRITICAL. (`rules/04`)
4. **Shared mutable state is correctly synchronized.** Respect the JMM: publish
   via `volatile`/`final`/`j.u.c`; prefer immutability and concurrent
   collections over hand-rolled locking. A data race is a real bug, not a
   nondeterministic annoyance. (`rules/03`)
5. **Virtual threads for blocking I/O concurrency (Java 21+); don't pin.**
   Avoid `synchronized` around blocking calls on virtual threads (pins the
   carrier — use `ReentrantLock`); never pool virtual threads. (`rules/03`)
6. **Resources are closed deterministically** — try-with-resources (Java) or
   `use {}` (Kotlin) for everything `AutoCloseable`. A leak on the exception
   path is the default failure of manual `finally`. (`rules/02`)
7. **Crypto uses the JCA correctly.** AES-GCM (not ECB/CBC-without-MAC),
   `SecureRandom` (never `Random`/`Math.random`) for keys/tokens/IVs, no
   MD5/SHA-1 for security, constant-time compare for secrets. Don't roll your
   own. (`rules/04`)
8. **Null is designed, not hoped.** Kotlin: lean on non-null types, guard
   platform types from Java; Java: `Optional` for return values (not fields/
   params), `@Nullable`/NullAway to make nullness checked. (`rules/01`,
   `rules/02`)
9. **Exceptions are handled or propagated, never swallowed.** No empty `catch`;
   don't catch `Exception`/`Throwable` to hide errors; preserve the cause when
   wrapping. (`rules/01`, `rules/02`)
10. **Dependencies are locked, scanned, and minimal.** Lockfile committed,
    OWASP dependency-check/OSV-Scanner gates CI, transitive CVEs triaged,
    plugins/artifacts from trusted repos. (`rules/06`)
