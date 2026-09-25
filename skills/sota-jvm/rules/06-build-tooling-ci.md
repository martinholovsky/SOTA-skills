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
  The concrete mechanisms: Gradle records the expected hash of every artifact in
  `gradle/verification-metadata.xml` and fails the build on a mismatch (Gradle's
  dependency-verification guide). Maven repositories take a `<checksumPolicy>` of
  `fail`, `warn` or `ignore`. Make it `fail`, stated in the POM or `settings.xml`, rather
  than relying on a default.
- **Code that runs at build time is a dependency with your credentials.** A JVM build
  executes third-party code before any test or review of yours does: every Maven plugin
  goal (notably `exec-maven-plugin`, `maven-antrun-plugin`), Maven build extensions
  (`<extensions>true</extensions>`, `<build><extensions>`) and core extensions
  (`.mvn/extensions.xml`, `-Dmaven.ext.class.path`, `${maven.home}/lib/ext`); every Gradle
  plugin (project and settings), `buildSrc`/included builds, and init scripts (`-I`/`--init-script`,
  `GRADLE_USER_HOME/init.gradle(.kts)`, `*.init.gradle(.kts)` in `GRADLE_USER_HOME/init.d/` or
  `GRADLE_HOME/init.d/` — all found run, so a CI image can carry one the repo never shows);
  the wrapper jar and the distribution it downloads; and annotation processors / KSP
  processors, which run inside the compiler. Controls:
  **(a)** javac on **JDK 23+** no longer runs processors it merely *finds on the class
  path* (JDK 21/22 did, with only a note); a processor on `--processor-path`, named by
  `-processor`, or enabled by `-proc:full` still runs, so declare processors explicitly
  (Maven `annotationProcessorPaths`, Gradle `annotationProcessor(...)`/`ksp(...)` — Gradle
  ignores processors on the compile classpath) and pass `-proc:none` to modules that need
  none. **(b)** Pin every plugin version and let artifact verification cover them —
  Gradle's `verification-metadata.xml` checks project and settings plugins too; set Maven's
  `checksumPolicy` to `fail` under `<pluginRepositories>` too, not only `<repositories>`. **(c)** Pin the wrapper:
  `distributionSha256Sum` in `gradle-wrapper.properties`; `distributionSha256Sum` **and**
  `wrapperSha256Sum` in `.mvn/wrapper/maven-wrapper.properties`; on GitHub, `gradle/actions/setup-gradle`
  v4+ validates the Gradle wrapper jar itself. **(d)** Review: on each plugin/processor
  bump, read the changelog and diff the released artifact, not only the version string;
  put `pom.xml`, `build.gradle*`, `settings.gradle*`, `buildSrc/`, `gradle/`, `.mvn/` and
  CI workflow files under **CODEOWNERS** with required code-owner review, including when an
  AI agent wrote the change. **(e)** CI: resolve and build in a job that holds no publish,
  deploy or cloud credentials, on an ephemeral runner; hand the artifact to a separate
  signing/publishing job. *OWASP: CI/CD Security cheat sheet; Software Supply Chain Security
  cheat sheet; NPM Security cheat sheet (the install-script analogue).*
- **Adopting a new dependency is a decision with evidence, taken before the coordinate lands
  in `pom.xml`, `build.gradle(.kts)` or `gradle/libs.versions.toml`** — whether a person
  typed it or an AI assistant suggested it. **(a) Is it the project you meant?** A
  coordinate that sounds right can be absent, freshly registered, or a look-alike. Confirm it
  resolves on Maven Central (`https://repo1.maven.org/maven2/<group/path>/<artifact>/maven-metadata.xml`
  answers 404 for a coordinate that does not exist), and that the `groupId` is the upstream
  project's own namespace — Central grants a namespace only after DNS-TXT or code-host
  verification, so an `io.github.<someone>` or look-alike group re-hosting a famous artifact is
  a red flag, not a mirror. **(b) Is it alive and clean?** Read the release history
  (first-publish date, cadence), advisories and licence from deps.dev
  (`https://api.deps.dev/v3/systems/maven/packages/<group>%3A<artifact>`, then `/versions/<v>`
  for `licenses` and `advisoryKeys`); maintainer count and activity from the source repo; and
  the OpenSSF Scorecard (`scorecard --repo=github.com/<org>/<repo>`, or the `scorecard` block
  of deps.dev's `/v3/projects/github.com%2F<org>%2F<repo>`). deps.dev marks the POM's
  source-repo link `UNVERIFIED_METADATA` — confirm the repo really builds this artifact. **(c)
  Its defaults are now your code.** Construct every security-relevant library object with
  its options explicit, and review each option you pass. Verified examples:
  `DocumentBuilderFactory.newInstance()` expands an external `file:` entity out of the box
  (Temurin 25.0.4, harden per `rules/07`); SnakeYAML **1.x** `new Yaml()` builds a
  `Constructor` that resolves global tags to arbitrary classes (2.0 added
  `LoaderOptions`' `UnTrustedTagInspector`, which rejects them — still prefer
  `new Yaml(new SafeConstructor(new LoaderOptions()))` for untrusted input); and a JDK
  `HttpRequest` built without `.timeout(Duration)` waits forever, per its javadoc.
  **(d) A README snippet is a demo, not a config.** Getting-started code routinely carries a
  trust-all `TrustManager`/`HostnameVerifier`, `@CrossOrigin("*")`, a widened actuator
  exposure or a debug flag; strip those before the snippet reaches a branch (`rules/04` §4–§6).
  *OWASP: Vulnerable Dependency Management cheat sheet; Software Supply Chain Security cheat
  sheet; Secure Coding with AI cheat sheet; SCVS V1, V6.*
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
      `err=$(grep -rniE 'dependency-check|osv-scanner|dependabot|snyk|cyclonedx' --include='*.yml' --include='*.yaml' --include='pom.xml' --include='build.gradle*' . 2>&1 >/dev/null); rc=$?` ;
      `case $rc in 0) ;; 1) echo "no dependency CVE scan — HIGH" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
      ;
      `ls gradle.lockfile gradle/dependency-locks 2>/dev/null; grep -rn 'dependencyLocking' build.gradle* 2>/dev/null`
      ; `grep -rnE 'version ranges|\[.*,.*\)|latest\.release|\+' build.gradle* 2>/dev/null`
      (unpinned ranges)
- [ ] **Artifact checksums verified, not just downloaded? (the provenance half of §2)** —
      `if test -f gradle/verification-metadata.xml; then echo "ok: gradle/verification-metadata.xml present"; else echo "FINDING: no gradle/verification-metadata.xml, so artifact checksums are not verified (Gradle builds)"; fi`
      ; `grep -rn 'checksumPolicy' --include='pom.xml' --include='settings.xml' .`
      (Maven: no hit leaves the policy to the Maven version's default, and `warn`/`ignore`
      let a bad checksum through; only `fail` blocks it)
- [ ] **Code that runs at build time: inventoried, pinned, owned? (§2, HIGH when a hit has
      no pinned version, the wrapper has no SHA-256 pin, or CODEOWNERS does not cover it)**
      — every hit is third-party or repo code the build executes; diff it on each bump:
      `grep -rnE '<extensions>true</extensions>|<extension>|exec-maven-plugin|maven-antrun-plugin|annotationProcessorPaths|-proc:full|annotationProcessor[ (]|ksp[ (]|--init-script|initscript' --include='pom.xml' --include='extensions.xml' --include='*.gradle' --include='*.gradle.kts' .`
      ; `find . -path '*/buildSrc/*' -name '*.gradle*' -o -name '*.init.gradle*'` ;
      `grep -L 'distributionSha256Sum' gradle/wrapper/gradle-wrapper.properties .mvn/wrapper/maven-wrapper.properties 2>/dev/null`
      (each file printed lacks a pin; the Maven one also needs `wrapperSha256Sum`) ;
      `grep -nE 'pom\.xml|build\.gradle|settings\.gradle|buildSrc|\.mvn|gradle/|\*' $(ls CODEOWNERS .github/CODEOWNERS docs/CODEOWNERS 2>/dev/null) /dev/null || echo "FINDING: no CODEOWNERS entry covers the build files"`
- [ ] **New dependency: selection evidence recorded, insecure defaults overridden? (§2; HIGH for
      a coordinate nobody can show was checked on Central/deps.dev, or a default-constructed
      parser/client that reads untrusted input)** — list coordinates this branch adds, then
      look each one up as §2 (a)–(b) describes (a version bump on a Gradle line or a one-line `<dependency>` prints
      too; its `-` line names the same coordinate):
      `git diff -U0 "$(git merge-base origin/main HEAD)" -- '*pom.xml' '*.gradle' '*.gradle.kts' '*.versions.toml' | grep -E '^\+[^+].*(<artifactId>|(implementation|api|runtimeOnly|compileOnly|annotationProcessor|ksp)[ (]|module *=)'`
      ; default-constructed SnakeYAML (HIGH on 1.x with untrusted input):
      `grep -rnE '(^|[^A-Za-z0-9_])Yaml\((\)|(new )?Constructor\()' --include='*.java' --include='*.kt' .`
      ; files building a JDK `HttpRequest` with no `.timeout(` anywhere in them:
      `grep -rlE 'HttpRequest\.newBuilder' --include='*.java' --include='*.kt' . | while IFS= read -r f; do grep -q '\.timeout(' "$f" || echo "$f: HttpRequest without .timeout"; done`
- [ ] **Static analysis configured?** —
      `grep -rniE 'errorprone|nullaway|spotbugs|findsecbugs|pmd|detekt|ktlint|spotless' . --include='pom.xml' --include='build.gradle*' --include='*.yml' || echo "no static analysis configured"`
- [ ] **Coverage gate + JUnit5/Testcontainers?** —
      `grep -rniE 'jacoco|junit-jupiter|testcontainers' pom.xml build.gradle* 2>/dev/null`
- [ ] **Repository over HTTPS, trusted only** —
      `grep -rnE 'http://|maven \{|repositories' pom.xml build.gradle* settings.* 2>/dev/null | grep -i 'http://'`