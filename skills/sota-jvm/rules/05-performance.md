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
- For fast startup/low footprint (serverless, CLIs): consider **AppCDS**/
  class-data sharing, or **GraalVM Native Image** (§5).

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