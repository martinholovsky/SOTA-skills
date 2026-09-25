# 05 — Performance: GC, JIT, profiling, allocation, native image

JVM performance is mostly about **garbage collection, allocation rate, and
letting the JIT warm up** — not micro-tweaks. Measure with a profiler and a
proper benchmark harness; never tune GC flags by guess. Cross-reference
`sota-performance` for methodology. [Java 25 perf docs](https://docs.oracle.com/en/java/javase/25/).

## 1. Garbage collectors — pick by goal

- **G1** — balanced throughput/latency; good for most server apps. **It is not the default
  everywhere before JDK 27.** Since JDK 9 the JVM has picked **Serial** when it sees a
  single CPU or less than 1792 MB of memory, and a container with a 1-CPU or 1 GiB limit
  meets that test. JEP 523 makes G1 the default in every environment from JDK 27. On earlier
  JDKs, set `-XX:+UseG1GC` (or your chosen collector) explicitly in the container image. You
  can also confirm the choice at startup: `-Xlog:gc` names the collector on its first line,
  and `java -XX:+PrintFlagsFinal -version | grep -E 'Use(Serial|G1)GC'` shows it too
  ([JEP 523](https://openjdk.org/jeps/523)).
- **Generational ZGC** (`-XX:+UseZGC` — generational-only since JDK 24, JEP
  490; the `ZGenerational` flag is obsolete and will eventually make the JVM
  refuse to start) — sub-millisecond pauses for large heaps / latency-sensitive
  services; slightly lower peak throughput.
- **Parallel** — max throughput for batch jobs where pause time doesn't matter.
- Set `-Xmx`/`-Xms` deliberately; in containers rely on container-awareness
  (`-XX:+UseContainerSupport`, default on) or `-XX:MaxRAMPercentage` rather than
  hardcoding — and verify the JVM sees the cgroup limit. Don't tune collectors
  before profiling shows GC is the bottleneck.

## 2. JIT and warmup

- HotSpot interprets then JIT-compiles hot code (tiered C1→C2). Benchmarks and
  latency SLOs must account for **warmup** — cold p99 is not steady-state.
- Don't prematurely "optimize" in source for the JIT (it inlines, escapes-
  analyzes, devirtualizes). Write clear code; let C2 work. Megamorphic call
  sites (many implementations behind one interface) defeat inlining — relevant
  only when profiled.
- **For startup and warmup, try the JDK's AOT cache before native image.** It keeps the
  JIT, full Java semantics and peak throughput. A training run records which classes load and
  link (JEP 483, JDK 24) and method profiles (JEP 515, JDK 25). From JDK 25 one step creates
  the cache: `java -XX:AOTCacheOutput=app.aot …` (JEP 514). Production then runs with
  `-XX:AOTCache=app.aot`. Since JDK 26 the cache works with any collector, including ZGC
  (JEP 516). **A mismatched cache is silently skipped.** The default mode warns and runs
  without it. JEP 483 requires the same JDK release, OS and architecture, the same class path
  (plain JARs, with extra entries allowed only at the end) and identical `-m`/`--module`,
  `--module-path`, `--add-modules` and `--enable-native-access` arguments. It bans
  `--illegal-native-access` (**any** value), `--add-opens`, `--add-reads`, `--limit-modules`,
  `--patch-module`, `--upgrade-module-path` and class-rewriting JVMTI agents. `--add-exports`
  is allowed from JDK 25 only if identical in every phase (JDK-8352437). **So the cache and
  `rules/04` §7's `--illegal-native-access=deny` are a trade-off, not a pair.** Run the
  `--illegal-native-access=deny` / `--sun-misc-unsafe-memory-access=deny` gate in a CI job
  that runs **without** the cache, so a new native dependency still fails the build. In
  production pick one: the cache, with native access left at the default `warn` and the same
  `--enable-native-access=<modules>` in every phase, **or** `deny` without the cache. (From
  the documents — JEP 483, updated 2026-08-26 — not measured here.) Prove the cache is used
  in a smoke test with `-XX:AOTMode=on`; JDK 27 adds `-XX:AOTMode=required` as an alias for
  it (JDK-8374348), not a rename — keep one of them in the smoke test. Either fails the launch
  instead of warning, so a skipped cache fails loudly; JEP 483 advises care before using it
  in production. Treat the `.aot` file as a build artifact, rebuilt with the JDK it was trained on. **Classic
  AppCDS** (`-XX:SharedArchiveFile`) is the older subset. **GraalVM Native Image** (§5) is
  for when even that is not enough
  ([JEP 483](https://openjdk.org/jeps/483), [JEP 514](https://openjdk.org/jeps/514),
  [JEP 515](https://openjdk.org/jeps/515), [JEP 516](https://openjdk.org/jeps/516)).

## 3. Allocation is the usual cost

- Allocation rate drives GC frequency. Reduce churn on hot paths: reuse buffers,
  avoid needless boxing (`Integer` vs `int`, autoboxing in loops/collections —
  prefer primitive specializations / `IntStream`), avoid per-call temporary
  collections and string concatenation in loops (`StringBuilder`).
- Escape analysis can stack-allocate non-escaping objects — keep short-lived
  objects local. Avoid finalizers and excessive `ThreadLocal` (esp. with
  virtual threads, `rules/03`).
- Right-size collections (initial capacity) to avoid resize churn.

## 4. Profiling — measure, don't guess

- **JDK Flight Recorder (JFR)** — low-overhead, always-on-capable profiling of
  allocation, locks, GC, I/O; analyze in JDK Mission Control. The default first
  tool for production.
- **A JFR recording is a sensitive artifact.** Its standard events copy the command line and
  the initial environment variables and system properties verbatim. So a token in
  `ACCESS_TOKEN`, a `-Djavax.net.ssl.keyStorePassword=…` or a `--dbpassword x` argument ends
  up in `dump.jfr`. Store recordings and the JFR repository directory like heap dumps (which
  hold all process memory). Restrict who can start or dump a recording: `jcmd` on the host,
  or JMX where `FlightRecorderMXBean` and `RemoteRecordingStream` can stream events off the
  host. Before sharing a file, run `jfr scrub`. **JDK 27 redacts by default** (JEP 536). The
  values of arguments, environment variables and system properties whose names match built-in
  filters (`*password*`, `*token*`, `*secret*`, …) become `[REDACTED]` inside the process,
  before a crash can leave them in the repository. Add your own names with
  `-XX:FlightRecorderOptions:redact-key=+…`, and treat `redact-key=none` or
  `redact-argument=none` as a finding. The redaction covers only those three kinds of data,
  so every other event payload is unchanged, and earlier JDKs have none of it
  ([JEP 536](https://openjdk.org/jeps/536)).
- **async-profiler** — low-overhead CPU/alloc/lock flame graphs without the
  safepoint bias of older samplers.
- Benchmark microbenchmarks with **JMH** (handles warmup, dead-code
  elimination, fork isolation) — never `System.nanoTime()` around a loop. Report
  distributions (`sota-performance`).

## 5. GraalVM Native Image (trade-offs)

- Ahead-of-time compiles to a native binary: fast startup, low memory — great
  for serverless/CLI/short-lived workloads. Costs: closed-world assumption means
  **reflection/proxies/resources need configuration** (or framework support —
  Spring AOT, Quarkus, Micronaut), longer build, and lower peak throughput than
  a warmed-up JIT for long-running compute.
- Choose native image for startup/footprint-bound services; stay on the JIT for
  long-running throughput-bound ones. Test the native binary — behavior can
  differ from JVM mode.

## Audit checklist

- [ ] **Allocation/boxing on hot paths — LOW/MEDIUM (verify with profiler)** —
      `grep -rnE '\+ ?"' --include='*.java' . | grep -iE 'for|while|loop'` (string concat in
      loops); `grep -rnE 'new (Integer|Long|Double|Boolean)\(' --include='*.java' .` (boxing /
      deprecated ctors);
      `grep -rnE 'List<Integer>|Map<Integer,|Map<.*,Integer>' --include='*.java' . # boxing-heavy collections`
- [ ] **GC/heap flags sane and container-aware?** —
      `grep -rnE 'Xmx|Xms|MaxRAMPercentage|UseZGC|UseG1GC|UseParallelGC' --include='Dockerfile*' --include='Containerfile*' --include='*.y*ml' --include='*.sh' --include='jvm.config' .`
      ; `grep -rn 'ZGenerational' --include='Dockerfile*' --include='*.y*ml' --include='*.sh' --include='jvm.config' .` (obsolete since JDK
      24 (JEP 490)); `grep -rn 'UseContainerSupport' . 2>/dev/null`
- [ ] **Collector left to ergonomics on a small container before JDK 27 — MEDIUM** (§1) —
      `grep -rLE 'Use(G1|Z|Parallel|Serial|Shenandoah)GC' --include='Dockerfile*' --include='Containerfile*' .`
      (each printed file launches a JVM with no explicit collector. With a 1-CPU or
      under-1792 MB limit, a pre-27 JVM runs Serial)
- [ ] **Benchmark hygiene — verify JMH, not nanoTime loops** —
      `grep -rn 'System.nanoTime\|currentTimeMillis' --include='*.java' --include='*.kt' . | grep -i bench` ;
      `grep -rln '@Benchmark' --include='*.java' --include='*.kt' . || echo "no JMH benchmarks"`
- [ ] **Native image config present if used?** —
      `grep -rn 'native-image\|GraalVM\|reflect-config\|reachability-metadata' . 2>/dev/null`
- [ ] **Profile first: JFR (-XX:StartFlightRecording) or async-profiler — no static grep**
- [ ] **JFR recordings and heap dumps: where they land, who can pull them, redaction off — HIGH
      when a recording leaves the host** (§4) —
      `grep -rnE 'StartFlightRecording|FlightRecorderOptions|HeapDumpOnOutOfMemoryError|HeapDumpPath|jmxremote|RemoteRecordingStream|FlightRecorderMXBean' --include='*.java' --include='*.kt' --include='Dockerfile*' --include='Containerfile*' --include='*.y*ml' --include='*.sh' --include='jvm.config' --include='*.gradle*' --include='pom.xml' .`
      (read each output path: a world-readable or shared volume is the finding; an
      unauthenticated `jmxremote` is HIGH on sight) ;
      `grep -rnE 'redact-(key|argument)=none' --include='Dockerfile*' --include='Containerfile*' --include='*.y*ml' --include='*.sh' --include='jvm.config' --include='*.gradle*' --include='pom.xml' .`
      (redaction switched off on JDK 27+)
- [ ] **Startup-bound service without an AOT cache, or a cache it never uses — LOW** (§2) —
      `grep -rnE 'AOTCache(Output)?=|AOTMode=|SharedArchiveFile|native-image' --include='Dockerfile*' --include='Containerfile*' --include='*.y*ml' --include='*.sh' --include='jvm.config' --include='*.gradle*' --include='pom.xml' .`
      (no hit on a service with a startup SLO: try `-XX:AOTCacheOutput` first. A cache beside
      `--illegal-native-access` or `--add-opens` in the same launch is skipped with only a
      warning, so read the launch line)