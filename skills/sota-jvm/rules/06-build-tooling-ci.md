# 06 — Build, tooling, supply chain, CI

JVM project safety lives in the build: dependency locking and CVE scanning,
static analysis, and consistent CI gates. This file owns build/test
*mechanics*; test **strategy** (suite shape, doubles, coverage philosophy)
lives in `sota-testing`.

## 1. Build tool: Maven or Gradle

- **Maven** — declarative, stable, ubiquitous; predictable for libraries and
  most services. **Gradle** — flexible, faster incremental builds, Kotlin DSL;
  pick it for complex/multi-module or Android-adjacent builds. Either is fine;
  consistency and reproducibility matter more than the choice.
- Pin the build-tool version (Maven Wrapper `mvnw` / Gradle Wrapper `gradlew`
  with a checksum) so every machine and CI uses the same version.
- Target the current LTS (Java 25) via `release`/toolchains; set
  `--release N` (not just `-source`/`-target`) so you don't accidentally use
  newer APIs on an older bytecode target.

## 2. Dependency management & supply chain

- **Lock dependencies**: Gradle dependency locking / version catalogs; Maven
  via the dependency-management section + a reproducible resolution (or the
  `maven-lockfile`-style plugins). Pin versions; avoid version ranges and
  `latest`. Commit the lock state.
- **Scan for known CVEs in CI**: OWASP **dependency-check** or **OSV-Scanner**
  (or Snyk/GitHub Dependabot) gating the build; triage transitive CVEs. Log4Shell
  and Spring4Shell were dependency CVEs — this gate is non-negotiable.
- Resolve only from trusted repositories (Maven Central / your mirror) over
  HTTPS; verify signatures/checksums; beware dependency confusion (don't let an
  internal coordinate resolve from a public repo). Generate an **SBOM**
  (CycloneDX) for releases. See `sota-devsecops`.
- Minimize the tree — each transitive dep is attack surface and a future CVE.

## 3. Static analysis & formatting

- **Error Prone** (+ **NullAway** for null-safety) on the Java compile — catches
  real bugs at build time; treat as errors in CI.
- **SpotBugs** + **Find-Sec-Bugs** for bug/security patterns (incl. crypto,
  injection, deserialization sinks from `rules/04`); **PMD** for additional
  rules.
- **Kotlin**: **detekt** (static analysis) + **ktlint** (style); both in CI.
- **spotless** (or google-java-format/ktlint) to enforce formatting in CI
  (`--check`) so style never enters review.

## 4. CI gates

- A PR build runs: compile with `-Werror`-equivalent (Error Prone as error),
  unit + integration tests, SpotBugs/detekt, dependency CVE scan, coverage
  (**JaCoCo**) with a threshold, and format check. Fail the build on any.
- **JUnit 5** is the standard runner; **Testcontainers** for real-dependency
  integration tests (DB/broker) — wire them here; *strategy* is `sota-testing`.
  Run with a fixed timezone/locale/seed for determinism.
- Build reproducibly: `-Dproject.build.outputTimestamp` / Gradle reproducible
  archives; pin plugin versions.

## Audit checklist

- [ ] **What has been SILENCED? -- the analyser's escape hatch (ROADMAP 60) javac:
      @SuppressWarnings is CATEGORY-SCOPED. Measured on JDK 21.0.12: a method annotated
      @SuppressWarnings("unchecked") still emitted BOTH [rawtypes] warnings while the unchecked
      one vanished. So read the ARGUMENT, never just the annotation.** —
      `grep -rn '@SuppressWarnings' --include='*.java' --include='*.kt' src/` ;
      `grep -rn '@SuppressWarnings("all")\|@SuppressWarnings({"all"' --include='*.java' src/`
      (HIGH: silences every category)
- [ ] **SpotBugs: edu.umd.cs.findbugs.annotations.SuppressFBWarnings (needs the
      spotbugs-annotations artifact on the classpath, so its presence is also a dependency
      fact)** — `grep -rn 'SuppressFBWarnings' --include='*.java' --include='*.kt' src/` ;
      `grep -rn 'NOSONAR\|CHECKSTYLE:OFF\|noinspection' --include='*.java' --include='*.kt' src/`
- [ ] **...and the BULK forms, which no per-site grep above will find** —
      `grep -rn 'excludeFilterFile\|<exclude>\|baseline' pom.xml build.gradle* 2>/dev/null` ;
      `find . -name 'spotbugs-exclude*.xml' -o -name 'checkstyle-suppressions.xml' 2>/dev/null`
- [ ] **Each hit needs a written reason. A suppression with no justification is the finding, not
      the warning it hides -- a silenced analyser is how a green gate stops meaning anything (
      `sota-code-security` rules/10).**
- [ ] **Wrapper pinned? LTS targeted?** —
      `ls mvnw gradlew 2>/dev/null | grep -q . || echo "no build wrapper (version not pinned)"`
      ;
      `grep -rnE 'release|sourceCompatibility|targetCompatibility|languageVersion' pom.xml build.gradle* 2>/dev/null`
- [ ] **Dependency CVE scan + locking in CI?** —
      `grep -rniE 'dependency-check|osv-scanner|dependabot|snyk|cyclonedx' .github/ pom.xml build.gradle* 2>/dev/null || echo "no dependency CVE scan — HIGH"`
      ;
      `ls gradle.lockfile gradle/dependency-locks 2>/dev/null; grep -rn 'dependencyLocking' build.gradle* 2>/dev/null`
      ; `grep -rnE 'version ranges|\[.*,.*\)|latest\.release|\+' build.gradle* 2>/dev/null`
      (unpinned ranges)
- [ ] **Static analysis configured?** —
      `grep -rniE 'errorprone|nullaway|spotbugs|findsecbugs|pmd|detekt|ktlint|spotless' . --include='pom.xml' --include='build.gradle*' --include='*.yml' || echo "no static analysis configured"`
- [ ] **Coverage gate + JUnit5/Testcontainers?** —
      `grep -rniE 'jacoco|junit-jupiter|testcontainers' pom.xml build.gradle* 2>/dev/null`
- [ ] **Repository over HTTPS, trusted only** —
      `grep -rnE 'http://|maven \{|repositories' pom.xml build.gradle* settings.* 2>/dev/null | grep -i 'http://'`