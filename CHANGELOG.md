# Changelog

All notable changes to SOTA-skills are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`sota-web-frameworks`** — React 19 + Next.js and Vue 3 + Nuxt 4 engineering,
  plus the cross-cutting concerns of server rendering (40 skills total). SKILL.md
  + 7 rules files: 01 baseline (support/EOL matrix, render-mode selection, React
  Compiler), 02 React 19 (hooks, Suspense, the Actions model, `dangerouslySetInnerHTML`),
  03 Next.js (App Router, Server Actions as public endpoints, the caching model —
  `use cache`/Cache Components/PPR/ISR — `proxy.ts`, the Data Access Layer), 04 Vue 3
  (Composition API, reactivity pitfalls, `defineModel`, `v-html`), 05 Nuxt 4
  (`useFetch`/`useAsyncData`, `useState`, `runtimeConfig`, Nitro server routes,
  `routeRules`), 06 SSR & hydration (mismatches, state-serialization XSS,
  cross-request state pollution, cache safety, CSP with streaming SSR), and 07
  framework security (server/client secret boundary, authorization placement,
  SSRF surfaces, consolidated CVE reference). Every version and CVE claim
  web-verified against primary sources (react.dev, nextjs.org, vuejs.org, nuxt.com,
  GitHub Security Advisories) and stamped `last-verified: 2026-07`. Notable
  security coverage: the 2025-12 React Server Components RCE (CVE-2025-55182
  "React2Shell" / CVE-2025-66478), the middleware auth bypass (CVE-2025-29927),
  Next cache-poisoning and SSRF CVEs, and the Nuxt/Nitro/h3/IPX/devalue advisory
  waves. Router routing table + library map + cross-cutting rule 6 updated;
  count surfaces updated to 40 skills / 289 files / ~57k lines (README
  badge/hero/alt/table, plugin.json, marketplace.json, social-preview pill + PNG).

## [1.10.0] - 2026-07-04

Coverage complete + auditable promises: two new language skills (39 total),
Swift-language and AD/Kerberos depth, and every remaining roadmap item
executed — invariant lint gate, freshness ledger, structured feedback intake.

The four coverage builds approved under roadmap item 6 (39 skills total):

- **`sota-php`** — PHP 8.3+ floor / 8.5 current (verified php.net), strict
  idioms, OWASP-grade security (PDO, escaping, uploads/LFI, unserialize/Phar,
  sessions), Composer supply chain (`composer audit`), PHPStan/Psalm,
  OPcache/FPM/JIT. SKILL.md + 6 rules files.
- **`sota-ruby`** — Ruby 4.0 current / 3.4 maintained (verified
  ruby-lang.org), idioms & typing (RBS/Sorbet), security (SQLi, ERB escaping,
  Marshal/`YAML.load` semantics since Psych 4, ReDoS + `Regexp.timeout`),
  Bundler supply chain (bundler-audit, lockfile checksums since Bundler 2.6),
  GVL/Ractors/YJIT (ZJIT flagged experimental). SKILL.md + 5 rules files.
- **Swift as a language** — `sota-mobile` rules/07: Swift 6.3 strict
  concurrency (verified swift.org), actors/Sendable, structured concurrency,
  ARC/retain cycles, unsafe interop, SPM registry security, Swift Testing.
- **Active Directory/Kerberos/ADCS** — `sota-identity-access` rules/07
  (Enterprise Access Model, delegation, Kerberoasting/gMSA/dMSA, ESC classes,
  KB5014754 enforcement, Windows LAPS) + `sota-detection-engineering`
  rules/07 (event-ID telemetry baseline, Sigma-style detections with ATT&CK
  IDs, AD deception), cross-linked. README "Coverage & non-goals" now lists
  only true non-goals; router/manifests/counts updated to 39 skills.

Roadmap items 2, 3, 5, and 6 executed (see `docs/ROADMAP.md` annotations):

- **Invariants 5 & 6** in `check-invariants.sh`: version lockstep (`VERSION`
  == `plugin.json` == CHANGELOG top; newest tag never ahead) and count-surface
  drift (README badge/hero/alt, router body, plugin/marketplace descriptions,
  social-preview pill vs a recount of the tree). CI invariants job now checks
  out full history so the tag comparison runs.
- **Freshness ledger**: rules files carry a line-1
  `<!-- last-verified: YYYY-MM -->` marker (18 files stamped from their
  existing in-text dates — never retroactively); `scripts/check-freshness.sh`
  + a monthly `freshness.yml` workflow report stale markers and the unstamped
  backlog.
- **Feedback intake**: bad-guidance and skill-request issue forms (primary
  source required; security-sensitive reports routed to private advisories)
  and GitHub Discussions enabled.
- **README "Coverage & non-goals"**: PHP, Ruby, Swift-as-a-language, and
  Active Directory/Kerberos depth declared out of scope for now and queued as
  approved follow-up builds.

## [1.9.0] - 2026-07-03

Cross-tool support: the library now works with Gemini CLI, Codex, and any
other agent that reads `AGENTS.md` — not just Claude Code.

- Cross-tool contributor guidance: root `CLAUDE.md` renamed to **`AGENTS.md`**
  (the open standard Codex/Cursor/Copilot read natively); `CLAUDE.md` and
  `GEMINI.md` are now symlinks to it, so Claude Code and Gemini CLI load it too.
- README hero now states the supported tools (native on Claude Code; Gemini
  CLI, Codex, and other `AGENTS.md` agents via `scripts/gen-agents-md.sh`).
- CHANGELOG: releases 1.4.0 and earlier moved to `docs/CHANGELOG-archive.md`
  (the file had reached the 500-line invariant cap); the archive step is now
  part of the release procedure in `RELEASING.md`.
- Added **`RELEASING.md`** — the release procedure in-repo (roadmap item 4):
  version- and count-bearing surfaces, PNG re-render, pre-tag checklist.
- Fixed **social-preview image saying "30 skills"** (stale through three
  releases): regenerated at 37; tagline now count-free by design (PR #41).

## [1.8.0] - 2026-07-02

Two new user-facing-words skills (37 skills total) plus a README overhaul for
first-screen impact.

### Added

- **`sota-ux-writing`** — the words *inside* the product: voice/tone systems
  and plain language (ISO 24495-1:2023), microcopy (buttons, labels, empty
  states, onboarding, notifications), error/feedback message craft (incl.
  security-sensitive errors), and accessible/localizable interface text
  (WCAG 2.2 language criteria, accessible names, ICU plurals, i18n-safe
  strings, inclusive language). 4 rules files with grep-able audit checklists.
- **`sota-copywriting`** — outward-facing content: positioning and value
  propositions, headlines/landing pages/CTAs, SEO content (search intent,
  E-E-A-T, Google spam policies incl. scaled-content and site-reputation
  abuse), and the claims/legal layer — substantiation, FTC Endorsement Guides
  (16 CFR 255, 2023) and Consumer Reviews Rule (16 CFR 465, 2024), dark
  patterns, email law (CAN-SPAM, GDPR/ePrivacy). Regulations verified against
  primary sources (eCFR, Federal Register, ISO, Google Search Central).
- Router: routing-table rows and library-map entries for both skills, plus
  cross-cutting rule 16 splitting user-facing words (UI text vs marketing vs
  technical docs).
- **README "Standards & practices baked in" section** — named standards by
  area (each verified as actually cited in the rules files) plus the practice
  layer no regulation writes down.
- **"Built with SOTA Skills" attribution badge** — copy-paste shields.io
  snippet in README → Optional setup ("Built with", deliberately not
  "certified by" — unverifiable certification is what `sota-copywriting`
  rules/04 §6 flags).

### Changed

- **README restructured for the skimming reader**: hook → two install
  commands → two example prompts → standards → skills table; directory tree
  and modes detail moved down beside "How it works".

## [1.7.1] - 2026-07-01

Fixes every confirmed finding of the 2026-07-01 adversarial audit
(`docs/AUDIT-2026-07-01.md`) except the accepted-risk history disclosure
(finding S1 — names remain in pre-July-2026 git history by decision).

### Fixed

- **`sota-security-compliance` frontmatter was invalid strict YAML** (HIGH):
  the inline description contained `Trigger keywords: …`, which strict loaders
  reject — the skill could be silently skipped. Now a `>-` block scalar
  (994 chars); invariant 4 additionally rejects unquoted inline descriptions
  containing `: ` so the class can't recur.
- **`init-gates.sh` could silently skip whole language gates** (HIGH): the
  `has()` file-list probe piped `printf` into `grep -q`, which under
  `pipefail` can die by SIGPIPE on large repos and read as "language not
  detected". Now a herestring; reproduced before/after with a 200k-file list.
- **`init-gates.sh` silent no-ops**: a `repos: []`-style config produced
  "wrote .pre-commit-config.yaml" with no gates inserted (now dies with
  instructions); altered/re-indented `sota-gates` markers made every re-run a
  silent unchanged rewrite (now detected exact-line and refused); running in a
  non-git dir crashed on `pre-commit install` after writing the config (now a
  warning); Bun ≥ 1.2 text lockfile `bun.lock` now selects `bun audit`.
- **`install.sh` `--copy` → default-install switch corrupted the target**:
  `ln -sfn` can't replace a real directory, so the stale snapshot stayed (with
  a self-named symlink nested inside) while the script reported success. Now
  detected and replaced after a prompt. Altered routing markers in
  `~/.claude/CLAUDE.md` are refused instead of looping "out of date" forever.
- **`gen-agents-md.sh`**: orphaned/altered managed-block markers now refuse to
  touch the file (previously a lone BEGIN marker set up content loss on the
  next run); marker splice is exact-line so a *quoted* marker can't misfire;
  skill count uses `find -L` (symlinked layouts reported "0 skills indexed").
- **`check-invariants.sh` hardening**: check 1 counts a missing final newline
  and skips deleted-but-tracked files instead of aborting; check 2 requires
  the audit checklist to be the file's LAST `## ` heading ("ends with", as
  documented); check 3 is case-insensitive, also scans file/directory names,
  and surfaces scan errors instead of failing open.
- **sota-jvm mislabeled JDK 25 scoped values as preview**: JEP 506 is final in
  Java 25 (structured concurrency remains preview, JEP 505). SKILL.md body and
  rules/03 corrected against openjdk.org.
- **sota-golang baseline raised to Go 1.25+**: 1.24 left security support with
  1.26's release (go.dev/doc/devel/release); feature notes unchanged.
- **Count/format drift**: README hero counts restored to the skills-markdown
  basis (255 files, ~52k lines — "279 files" counted every tracked file);
  README/CONTRIBUTING rules-file line-range claims now match reality (~80–350);
  the v1.5.0 pre-fix description lengths corrected to invariant 4's own
  measurements; plugin/marketplace descriptions say 34 domains + router
  (35 skills); router cross-cutting rules renumbered sequentially (were
  1-9, 13-16, 10-12); audit-methodology short finding format regains the
  `effort` field and 11 skill finding templates gained an `Effort:` line;
  five bare `rules/08` references in sota-llm-engineering now name
  sota-code-security; a garbled cross-reference in sota-code-security
  rules/09 reworded.
- **Secret-scanning guidance reconciled** (was duplicated with drift):
  sota-devsecops rules/05 §5.2 owns pipeline gate layering,
  sota-secrets-management rules/04 owns tool config + leak response — now
  cross-referenced both ways, and gitleaks commands use the current
  `gitleaks git` CLI (the official pre-commit hook's own invocation).
- Stale docs: `CLAUDE.md` pointed at the changelog with "(current: v1.0.0)"
  seven releases later — the pointer is now version-less; gitleaks scan scope
  documented accurately in `CLAUDE.md`, `CONTRIBUTING.md`, and `README.md`.

### Changed

- **CI secret scan now covers the full git history**: the gitleaks job checks
  out with `fetch-depth: 0` and runs `gitleaks git` (every commit) instead of
  `gitleaks detect --no-git` (working tree only). Validated locally first:
  44 commits scanned, no leaks.
- **CI hardening**: `actions/checkout` re-pinned to v7.0.0 (SHA-pinned;
  was v4.2.2, three majors old), `persist-credentials: false` on every
  checkout, and a new `shellcheck` job gates `scripts/*.sh`. The
  sota-devsecops SHA-pinning example no longer hard-codes an aging SHA.
- **Internal-name denylist externalized**: the private patterns moved out of
  the tracked script into a git-ignored `.denylist.local` (pre-commit) and the
  `SOTA_DENYLIST` repository secret (CI). The tracked script keeps only the
  generic reader-assumption phrases; fork PRs run those and the maintainer's
  CI runs the full list. Pre-2026-07 history still contains the old inline
  list — reviewed and accepted (audit finding S1).
- **`scripts/install.sh` checks contributor pre-commit hygiene**: when run from
  a git checkout it detects a missing pre-commit hook and offers to install it
  (or prints an install tip when the `pre-commit` tool itself is absent).
  Non-fatal for end users; CI enforces the same checks regardless.

### Added

- `docs/AUDIT-2026-07-01.md` — full adversarial audit report (decision ledger,
  findings, reproduction status), and `docs/ROADMAP.md` — audit-derived
  priorities.

## [1.7.0] - 2026-07-01

Adds a security & compliance engineering skill — the cybersecurity-regulation
counterpart to `sota-privacy-compliance` (which stays data/privacy-centric). It
covers the control frameworks and product-security regulations that drive
architecture, code, and CI gates rather than the organizational policy binder,
with an explicit engineering-vs-organizational scope boundary. The library goes
from 34 to 35 skills.

### Added

- **`sota-security-compliance` — security & compliance engineering skill** (35th
  skill): SKILL.md + 5 rules — `01-control-frameworks-as-code` (NIST CSF 2.0 as
  the organizing spine; control → mechanism → evidence crosswalk; policy-as-code
  gates; baselines/tailoring/OSCAL), `02-nist-800-53-171-cmmc-fedramp` (SP
  800-53 Rev 5 families & baselines, SP 800-171 Rev 3 CUI boundary +
  FIPS-validated crypto, CMMC 2.0 levels & phase-in, FedRAMP + FedRAMP 20x),
  `03-ssdf-secure-sdlc` (SP 800-218 PO/PS/PW/RV practices as CI gates, federal
  secure-software self-attestation, SP 800-218A for AI/model development),
  `04-eu-cyber-resilience-act` (Regulation (EU) 2024/2847 — SBOM, coordinated
  vulnerability disclosure, signed update channel, secure-by-default, the 24h/72h
  ENISA reporting clocks, phased timeline), `05-iec-62443-ot-ics` (OT/ICS zones &
  conduits, Security Levels SL-T/C/A, the 7 Foundational Requirements, 62443-4-1
  vs SSDF, 62443 as a CRA conformity route). Cross-links to
  `sota-privacy-compliance`, `sota-devsecops`, `sota-identity-access`,
  `sota-network-security`, and `sota-detection-engineering` rather than
  duplicating them. Statuses verified July 2026 against NIST CSRC, EUR-Lex, the
  Federal Register, and ISA/IEC (CSF 2.0 Feb 2024; 800-53 Rev 5; 800-171 Rev 3
  May 2024; SSDF v1.1 / 800-218A; CMMC 32 CFR eff. Dec 2024 + 48 CFR eff. Nov
  2025; CRA reporting from 11 Sep 2026, main obligations from 11 Dec 2027).

### Changed

- Router (`sota/SKILL.md`) catalog table, rules index, and description updated to
  include `sota-security-compliance`.
- README skill count (34 → 35), file/line counts (279 files, ~53k lines), and
  skills table updated.
- `scripts/install.sh` always-on routing is now **update-aware**: re-running (or
  `--update`) refreshes the managed `~/.claude/CLAUDE.md` directive and the
  `settings.json` reminder hook in place when their wording changes upstream —
  prompting first, backing up, editing only the content between the managed
  markers, writing through a symlink so dotfiles keep their link, and leaving a
  hook with custom wording untouched. Previously the block was write-once
  (detected by marker presence and skipped), so wording changes never propagated.
  README "Always-on routing" and "Updating" sections document the new behavior.

## [1.6.0] - 2026-06-29

Adds four language/domain skills found missing in a coverage gap-analysis,
closing the conspicuous holes against 2026 usage data (TIOBE/Stack Overflow):
the most-used languages without coverage (C/C++, JVM, .NET) plus classical
ML/MLOps as a discipline distinct from LLM-application engineering. The library
goes from 30 to 34 skills.

### Added

- **`sota-dotnet` — C# / .NET engineering skill** (34th skill): SKILL.md +
  6 rules — `01-idioms` (records, nullable reference types, pattern matching,
  spans, C# 14 `field`/extension members), `02-design-api` (nullability
  contract, disposal/`IDisposable`+`using`, `IHttpClientFactory`, DI lifetimes/
  options), `03-async-concurrency` (async-all-the-way, never-block,
  `ConfigureAwait(false)`, cancellation, channels, `async void`),
  `04-security` (EF Core/Dapper parameterization, `BinaryFormatter` removed in
  .NET 9 + JSON `TypeNameHandling`, ASP.NET Core authn/authz/antiforgery/CORS,
  `RandomNumberGenerator`/AES-GCM/Data Protection), `05-performance` (GC, Span/
  ArrayPool, BenchmarkDotNet, Native AOT), `06-build-tooling-ci` (TFM/SDK
  pinning, nullable + analyzers as errors, NuGet lockfiles + source mapping +
  CVE scan). Baselines verified: .NET 10 LTS (Nov 2025–2028), C# 14,
  BinaryFormatter removed in .NET 9; OWASP .NET cheat sheet + Roslyn security
  CA rules. Router, README counts (34 skills), and rules index updated.
- **`sota-ml-engineering` — ML engineering / MLOps skill** (33rd skill):
  classical/predictive ML systems, explicitly distinct from `sota-llm-engineering`
  (LLM apps) and `sota-data-engineering` (pipelines). SKILL.md + 7 rules —
  `01-ml-systems-architecture` (model-is-small-part, train/serve paths, feature
  store, model registry, the Hidden-Technical-Debt anti-patterns),
  `02-data-and-features` (data/label leakage, train/serve skew, splits,
  versioning, PII), `03-training-experimentation` (tracking, reproducibility/
  seeds, config-as-code, HPO), `04-evaluation-validation` (objective-aligned
  metrics, baselines, sliced/fairness eval, ML Test Score, promotion gates),
  `05-deployment-serving` (batch/online/streaming, registry-gated promotion,
  shadow/canary, rollback), `06-monitoring-drift` (data/concept drift via PSI/KS,
  performance decay, label lag, retraining triggers), `07-security-governance`
  (poisoning/extraction/inversion, unsafe-pickle supply chain, model cards,
  MITRE ATLAS, NIST AI RMF, EU AI Act). Grounded in Google's Rules of ML, the
  ML Test Score rubric, and Hidden Technical Debt in ML Systems. Router, README
  counts (33 skills), and rules index updated.
- **`sota-jvm` — Java & Kotlin (JVM) engineering skill** (32nd skill):
  SKILL.md + 6 rules — `01-idioms` (records/sealed/pattern-matching, Kotlin
  null-safety/scope functions, interop, error handling), `02-design-api`
  (nullability discipline, immutability, `equals`/`hashCode`, resources/
  try-with-resources/`use`, JPMS), `03-concurrency` (virtual threads + pinning,
  the JMM, `java.util.concurrent`, Kotlin coroutines/structured concurrency;
  structured concurrency noted as *preview* in Java 25), `04-security` (native
  deserialization/gadget chains + `ObjectInputFilter`, XXE, JNDI/Log4Shell-class,
  SQL/command/EL injection, JCA crypto, TLS), `05-performance` (G1/Generational
  ZGC, JFR/async-profiler, allocation, GraalVM native image), `06-build-tooling-ci`
  (Maven/Gradle, dependency-check/OSV-Scanner supply chain, Error Prone/NullAway,
  SpotBugs/Find-Sec-Bugs, detekt/ktlint, JaCoCo). Baselines verified against
  primary sources: Java 25 LTS, virtual threads final since JEP 444 (Java 21),
  structured concurrency still preview (JEP 505/525), Kotlin 2.x; SEI CERT
  Oracle Java + OWASP. Router, README counts (32 skills), and rules index
  updated.
- **`sota-c-cpp` — C & C++ engineering skill** (31st skill): SKILL.md +
  7 rules — `01-idioms` (RAII, rule of zero/five, ownership, value semantics,
  `std::expected` error handling), `02-memory-safety` (bounds, UAF/dangling,
  iterator invalidation, ASan/UBSan/MSan, hardened stdlib assertions),
  `03-undefined-behavior` (integer overflow, strict aliasing, the optimizer,
  UBSan), `04-security` (SEI CERT C/C++, MISRA, banned APIs, format-string/
  injection/TOCTOU, CSPRNG, the OpenSSF compiler-hardening flag set),
  `05-concurrency` (C++ memory model, data races, atomics/memory order, RAII
  locks, `std::jthread`, TSan), `06-build-tooling-ci` (CMake, clang-tidy/
  clang-format, cppcheck/analyzer, sanitizer + fuzzing CI, vcpkg/Conan supply
  chain), `07-performance` (profiling, allocation, cache locality, LTO/PGO).
  Every external claim verified against primary sources (C++ Core Guidelines,
  SEI CERT, MISRA C:2023/C++:2023, OpenSSF Compiler Hardening Guide). Router,
  README counts (31 skills), and rules index updated.

## [1.5.0] - 2026-06-29

### Fixed

- **Skill descriptions over the 1024-character Agent Skills cap** (issue #4):
  eight `SKILL.md` descriptions exceeded the spec limit — `sota-identity-access`
  (1629), `sota-detection-engineering` (1366), `sota-architecture` (1314),
  `sota-kubernetes` (1186), `sota-network-security` (1181), `sota-testing`
  (1165), `sota-code-security` (1106), `sota-secrets-management` (1103)
  as measured by invariant 4's own counter (corrected 2026-07-01; the
  originally published figures were 2–3 higher from a different parser) — so
  loaders (Claude Code, Codex, …) silently skipped them. All condensed to ≤ 1024
  (now 955–1016) by trimming prose while preserving the trigger-keyword routing
  signal. Verified against the
  [Agent Skills spec](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).

### Added

- **`check-invariants.sh` invariant 4 — `SKILL.md` description ≤ 1024 chars**:
  a new gate (pre-commit + CI) that counts Unicode characters of every skill
  description (parsing folded `>-` and plain scalars) and fails the build over
  the cap, so the regression behind issue #4 can't recur. Uses `python3` for
  correct character counting; skipped with a warning if `python3` is absent
  locally (CI always enforces it). Documented in `CLAUDE.md` and
  `CONTRIBUTING.md`.
- **`sota-testing/rules/09-security-testing.md` — security testing as a test
  type**: the gap surfaced by adopting the OWASP Developer Guide + Web Security
  Testing Guide (WSTG). The library covered the *vulnerabilities* and *scanners*
  but had no consolidated methodology for a test author. New file uses WSTG as the
  verification map and defines the security-regression set (IDOR/BOLA, BFLA,
  authn/session, injection, mass-assignment, rate-limit, SSRF, tenant isolation),
  business-logic/abuse-case tests from threat models, where SAST/DAST/fuzz fit and
  their ceiling, and a ~90% security-critical coverage floor. SKILL.md index,
  non-negotiables, and triggers updated. Also added an **XSSI** (cross-site script
  inclusion) note to `sota-code-security/rules/05` — the one WSTG client-side item
  with no prior coverage.
- **`sota-api-design/rules/05` — WebRTC security** (`## 6`): the one technical
  area an OpenCRE/ASVS-v5.0 coverage check found missing. Self-hosted TURN
  (relay-abuse = SSRF over UDP; allowlist non-special IPv4+IPv6, cap allocations),
  media servers (DTLS-SRTP cipher/key policy, SRTP auth vs RTP injection,
  malformed/flood resilience, DTLS `ClientHello` race DoS, DTLS-cert↔SDP-fingerprint
  binding), and signaling (rate-limit + malformed-input-safe). Scoped to
  self-hosted infra — CPaaS-SDK consumers are provider-owned. Grounded in OWASP
  ASVS v5.0 V17 + RFC 8826/8827. SKILL.md index/triggers updated.

### Changed

- **`sota-golang/rules/05-security.md`** — closed two OWASP Go-SCP gaps that are
  Go-language-specific: a CSPRNG section (`crypto/rand`/`rand.Text` vs the
  predictable `math/rand`/`math/rand/v2`, plus the deprecated-`math/rand.Read`
  import footgun) folded into the cryptography section, and an output-encoding
  note (`html/template` contextual auto-escaping vs `text/template`, and the
  `template.HTML`/`JS`/`URL` escape-hatch sinks) cross-referencing
  sota-code-security `05`. Added matching audit greps and severity guidance.
  SKILL.md index and description updated to match.
- **`sota-rust`** — closed three gaps found by diffing the skill against the
  ANSSI *Secure Rust Guidelines* (the nearest equivalent to OWASP Go-SCP):
  no panicking in `Drop` impls (double-panic aborts the process — `rules/02 §5`,
  `LANG-DROP-NO-PANIC`, verified against the std `Drop` docs); don't rely *only*
  on `Drop` for secret erasure since `mem::forget`/`Box::leak`/cycles/
  `panic=abort` skip it (`rules/05 §5`, `LANG-DROP-SEC`); and uphold the
  `Eq`/`Ord` comparison-trait invariants or `sort`/`BinaryHeap`/`BTreeMap`
  silently corrupt or panic (`rules/01 §6`, `LANG-CMP-INV`). Added matching
  audit-checklist greps (clippy lint names verified against clippy 0.1.91);
  SKILL.md index updated.
- **`sota-kubernetes/rules/01`** — added two items from the OWASP Kubernetes
  Security cheat sheet that the skill didn't call out: API Priority & Fairness
  (stable since v1.29, on by default; don't disable it, give high-value
  controllers a dedicated `PriorityLevelConfiguration`, alert on flowcontrol
  rejects) and a Kubernetes Dashboard hardening caveat (don't expose it; never
  bind it to `cluster-admin`). Both with audit-checklist entries. The rest of
  the cheat sheet was already met or exceeded by the existing rules.
- **AI/LLM skills** — closed gaps found by diffing against the new OWASP
  AI/LLM cheat sheets (MCP Security, RAG Security, AI Agent Security, Secure AI
  Model Ops): MCP **server-operator** hardening — bind localhost, validate
  `Origin`/`Host` (DNS-rebinding), context-bound session IDs, narrow scopes
  (`sota-llm-engineering/rules/04`); self-hosted vector DBs ship auth-OFF
  (Qdrant) — require API key/TLS/internal network, restrict writes, hash chunks
  (`sota-code-security/rules/08 §4`); RAG corpus integrity — content-hash +
  verify, don't leak raw similarity scores (`sota-llm-engineering/rules/03 §7`);
  strip invisible/bidi/Trojan-Source Unicode at ingest
  (`sota-code-security/rules/09 §4`).
- **API & web skills** — closed gaps from the OWASP REST/GraphQL/WebSocket/
  Clickjacking cheat sheets: per-route method allowlist + `405` + per-method
  authz and content-negotiation hygiene (`406`, never reflect `Accept` into
  `Content-Type`) in `sota-api-design/rules/01`; `wss://`-only + disable
  `permessage-deflate` (CRIME/BREACH) in `rules/05`; GraphQL alias/batch as an
  auth **brute-force** (not just cost-DoS) vector in `rules/03`; server-side
  business-flow state-machine enforcement on API6 in `rules/07`; and
  **double-clickjacking** (bypasses `frame-ancestors`/XFO → needs interaction
  confirmation) in `sota-code-security/rules/05 §5`.
- **`sota-devsecops`** — closed gaps from the OWASP GitHub Actions / CI-CD /
  Software Supply Chain / Vulnerable Dependency Management cheat sheets:
  impostor-commit verification (a SHA pin can point at a fork-network commit —
  zizmor `impostor-commit`) and CodeQL `actions` workflow analysis in `rules/01`;
  ban `secrets: inherit` + `::add-mask::` for derived secrets + disable build
  caching in release/publish workflows in `rules/01`; a no-upstream-patch
  mitigation playbook and **slopsquatting** (AI-hallucinated packages) in
  `rules/03`. External facts (zizmor rule, CodeQL `actions` GA Apr 2025) verified.
- **Identity, secrets & crypto skills** — closed gaps from the OWASP
  Authentication/Authorization/OAuth2/Session/Secrets/Key-Management/TLS cheat
  sheets: OAuth **mix-up** defense via the RFC 9207 `iss` authorization-response
  parameter for multi-AS brokers (`sota-identity-access/rules/01`); log
  authorization decisions/denials (`rules/03`); treat the vault as tier-0 — HA,
  off-box snapshot + DR-restore drill, break-glass (`sota-secrets-management/rules/02`);
  design for key **loss** — escrow/back up data keys, never signing keys
  (`sota-code-security/rules/04`); session renewal timeout + `Clear-Site-Data`/
  `no-store` on logout (`rules/02`); hybrid PQ KEX `X25519MLKEM768` and
  trust-store-injection control (`sota-network-security/rules/06`).
- **Server-side attack coverage** — closed gaps from the OWASP Business Logic,
  SSRF, Injection, and Deserialization cheat sheets. The injection/IDOR/mass-
  assignment/upload/DoS families were already strong; added the under-covered
  **business-logic** doctrine: semantic/cross-field validation + treat
  hidden/disabled/echoed fields as adversarial (`sota-code-security/rules/01`),
  server-side re-derivation of prices/totals/quotas (`rules/07`), and full
  workflow state-machine integrity — consume one-time ops, expire partial state,
  no client-side workflow position (`rules/03`). Plus SSRF blocklist broadened to
  all multicast + CGNAT 100.64/10 (`rules/01`), serialized-payload (pickle/Java/
  PHP) signature detection at ingest (`rules/09`), and Redis `EVAL`/Qdrant-filter
  injection guidance (`sota-databases/rules/06`).

---

Releases **1.4.0 and earlier** are archived in
[docs/CHANGELOG-archive.md](docs/CHANGELOG-archive.md).

[1.10.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.10.0
[1.9.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.9.0
[1.8.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.8.0
[1.7.1]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.7.1
[1.7.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.7.0
[1.6.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.6.0
[1.5.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.5.0
