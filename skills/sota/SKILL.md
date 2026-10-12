---
name: sota
description: >-
  Master router for the SOTA engineering skills library. Use this skill whenever the user asks to
  build, design, implement, refactor, harden, optimize, review, or audit an application, service, or
  codebase and the request spans more than one domain — or when you are unsure which specific sota-*
  skill applies. Also use when working on a codebase you do not own: reviewing a pull request or
  diff, responding to code review, evaluating someone else's patch, or preparing an upstream
  contribution — including mid-session, once you are already reading source, a diff, or CI config.
  It maps the task (build or audit mode) to the right domain and language skills (Rust, Go, C/C++,
  JVM, Python, JS/TS, .NET/C#, PHP, Ruby, Swift). Trigger keywords: SOTA, best practices, audit my code,
  security review, compliance, hardening, prod readiness, code quality, pull request, PR review,
  review comment, maintainer feedback, patch, diff, upstream, contribute, merge request.
---

# SOTA Engineering Skills — Master Router

A library of 42 domain skills, each with a `SKILL.md` entry point and a `rules/`
folder of focused rule files (each under 500 lines). Each skill works in two
modes:

- **BUILD** — apply the rules while designing or writing code.
- **AUDIT** — review existing code against the rules and emit findings in the
  canonical format below (it supersedes any per-skill variant):
  `file:line | rule violated | severity (Critical/High/Medium/Low/Info) |
  effort (trivial/small/medium/large) | fix`.
  **Severity resolves the same way:** [`rules/03`](rules/03-audit-findings.md) §1 is the floor. A skill's own
  Critical/High/Medium/Low table may refine it *within that skill's domain* and must
  say that it is doing so; an unscoped per-skill table does not outrank the model, and
  a cross-domain roll-up is always rated on it.

Read only what the task needs: first the relevant skill's `SKILL.md` (it has its
own index of `rules/` files with "read this when..." guidance), then only the
rules files that match the code in front of you. Never load all skills at once.

## Operating principles (always apply)

0. **Validate every claim — mandatory.** No claim ships unvalidated, in any
   mode. A claim is validated only by checking it against a primary source:
   code read in full context at the pinned commit (for findings), official
   docs/release notes/advisories fetched at use time (for versions, specs,
   CVEs, tool capabilities), or a reproduced behavior (for bugs). Training
   data, plausibility, and "the rules file says so" do not validate anything.
   **A doc page states intent; only running it reports behaviour.** "What does
   this command do when the input is missing/stale/hostile" is a *behaviour*
   question even though it reads like a tool capability, and the vendor's page
   can be stale or simply wrong: measured 2026-09-14, Poetry's own docs say a
   desynced lock produces a "Warning" while the tool exits **1**, and a mechanism
   published from that summary had to be retracted. If a command is installable
   in two minutes, run it — both the failing and the passing case.
   **A retraction is a claim and carries the same burden.** Withdrawing a
   statement needs the primary source that falsifies it, exactly as asserting it
   did; *"I was probably wrong"* is not a finding, and it costs the reader a true
   statement. A wrong claim gets challenged because it asserts something; a wrong
   retraction sounds like humility and is waved through — **nobody audits a
   confession**. Three tells of over-correcting: it arrives within a message or
   two of an *unrelated* correction; it withdraws something you have evidence on
   screen for; it is a general loss of confidence rather than a named false
   proposition and what falsifies it. **The moment after being corrected is the
   highest-risk moment in a session** — the next claim needs *more* evidence, in
   **both** directions. Conceding everything is not the opposite of
   overconfidence; it is overconfidence about your own unreliability.
   What cannot be validated is either omitted or explicitly marked
   "needs verification" — never asserted. **Before measuring, state what result
   would falsify the claim.** If no obtainable result could, the experiment is
   theater — read the code path that decides the behavior instead of
   benchmarking its symptoms.
1. **Freshness first.** The library's version/spec/regulation facts were
   web-verified as of the last refresh (see README). Never trust them — or
   training data — for anything version- or CVE-sensitive at use time:
   re-verify current releases and advisories before pinning or recommending —
   **and equally when you are merely *measuring* a third party's artifact**,
   which does not feel like a version decision and is where this rule is
   skipped. **Record the end-of-life date beside the version**, every time. A
   version can be recalled fluently and with no felt uncertainty; an EOL date
   effectively cannot, so requiring it forces the lookup that "check this is
   current" does not. A version with no EOL date beside it has not been looked
   up. Detail, and what to do with a lapsed one: [`sota-devsecops` rules/03](../sota-devsecops/rules/03-dependencies.md) §3.9.
2. **Stop-and-ask on security-relevant decisions.** When a choice materially
   affects security posture (authn/z model, crypto primitive, trust boundary,
   secrets handling, network exposure), present the options with a
   recommendation and ask before proceeding. Do not silently pick.
3. **Evidence over vibes.** Every audit finding cites file:line, maps to a
   standard (CWE, OWASP, MITRE ATT&CK/ATLAS) where one applies, and proposes a
   concrete fix. Uncertain findings are marked "needs verification", never
   asserted. Borderline severities state the deciding assumption ("High if
   internet-facing; Medium if internal-only"). **A negative claim needs more
   proof than a positive one**: "no instances of X" and "I only looked one way"
   are indistinguishable from the outside, so before asserting absence, widen
   the search and use a second independent method — and state the search you
   actually ran. **"Independent" means a different failure mode, not a different
   phrasing.** Field-reported: two searches of the same tree agreed on zero and
   both were wrong, because both were `grep -r` over a directory of symlinks,
   which `-r` does not follow. The only check that works is a **positive
   control** — search for something you have already seen there, in the same
   invocation; if the control returns nothing, the instrument is broken and the
   absence is not evidence ([`sota-shell-scripting` rules/06](../sota-shell-scripting/rules/06-ad-hoc-commands.md) §2).
   **A control proves the instrument works; it does not prove the query asks the
   corpus's question.** Varying the phrasing is not a second *method*, but it is
   a separate check you still owe: field-reported 2026-09-14, a gap was declared
   after searching *"one instance | a single observation"* with a control
   returning four files, while the corpus says **"one sample"** in six — a named
   failure mode among them. Working instrument, wrong vocabulary, false absence.
   Before asserting a gap, name the term the corpus itself would use — read a
   neighbouring section's headings — and search that. **And a failed reproduction is
   an absence claim too** — it carries this same burden and almost never gets it,
   because it does not feel like a search ([`sota-code-security` rules/12](../sota-code-security/rules/12-verifying-the-verifier.md) §1a.1). Where a
   control is unavailable because nothing is yet known to be in the target,
   print a **denominator** instead — bytes, members, total rows — beside the
   zero. **And weigh who benefits from the source**: a claim sourced to a party
   that sells the remedy is a hypothesis, not a measurement
   ([`sota/rules/03`](rules/03-audit-findings.md) §2).
4. **Stack profile.** If the repo or `~/.claude` contains a `profiles/*.md`
   stack profile (preferred stores, auth provider, license policy, platform
   conventions), its choices are the defaults for BUILD mode and the expected
   baseline for AUDIT mode. A profile may make a deviation a finding and raise its
   *default* severity; a Critical or High still needs chain closure ([`rules/03`](rules/03-audit-findings.md) §1
   rule 3). When they disagree, report the chain's rating with the profile's beside
   it — "Critical by profile default; Medium on the chain: the cluster is local".
5. **Universal build non-negotiables (apply regardless of routing).** On **any
   network-reachable endpoint or handler** (HTTP, RPC, queue, webhook, upload),
   always include: **(a)** abuse control — rate limiting / quotas keyed to the
   caller; **(b)** transport enforcement — TLS, HSTS, no plaintext fallback;
   **(c)** tests for the logic; **(d)** structured logging without secrets/PII.
   These are cross-cutting, so they get silently dropped under a long, dense
   task even when a rules file covers them — a measured attention effect, not a
   coverage gap. Keep this list short and **re-check it last, before you ship**
   (BUILD step 4). If one is deliberately handled elsewhere (e.g. rate limiting
   at the gateway), say so — don't silently omit it.
6. **Claim "done" only with evidence.** Never report a task complete or a fix
   working from plausibility — "should work", "this fixes it", "Done!" are not
   evidence. State the check you actually ran and its result: test output with
   pass/fail counts and exit code, the command and its output, or the reproduced
   behavior. If you did not run it, say so plainly. Unverified completion is not
   completion — this applies to your own build output before you hand it back.
7. **Restate from the artifact, never from your own summary.** Re-reading your
   own write-up re-runs the reasoning that produced it — the weakest check
   available. Before a claim reaches anything user-visible, go back to the
   primary source: re-read the tool output, or re-run the command. Your earlier
   prose in this session is not a primary source — **and neither is a verbatim
   copy of a file injected into context earlier in it.** A quoted file reads as
   primary evidence in a way a summary does not, which is exactly what makes it
   the easier mistake: it may predate an edit made since. Re-read the path before
   asserting or editing against its contents. **Nor is a project's own index, tracker row
   or status table** — a summary an earlier session wrote; open the record it summarises
   before repeating its status (field-reported 2026-09-26: "NOT filed", ten days after
   filing). Summaries silently drop the case
   that contradicts them and raw output does not. Full adversarial procedure for
   audit findings: AUDIT step 7 and [`rules/03`](rules/03-audit-findings.md) §4.
8. **Publishing under someone else's name raises the bar.** A claim to the
   person who asked costs one reader's trust and is cheap to retract. A claim
   published as them — a PR review comment, an issue, a commit message, a
   mailing-list post — is public, attributed and effectively permanent. Verify
   every factual claim by execution rather than inference, say which parts you
   did not test, check the thread first for whether it is already known, and
   never publish on someone's behalf without approval of the final text. Full
   procedure: [`sota-docs-workflow` rules/03](../sota-docs-workflow/rules/03-code-review-pr-workflow.md) §8.
9. **Match the rigour to the stakes — and name the level you chose.** A spike, a
   one-off script, a local experiment: build it, say in one line that it is a
   prototype and what you left out, stop. Anything reachable by an untrusted caller
   or touching money, credentials or another tenant's data gets the full treatment
   including principle 5, whether or not the request said "quick"; if it is
   genuinely ambiguous, ask in one line. An *unnamed* shortcut is not a prototype.

## Routing table

| Skill | Use when the task involves... |
|---|---|
| [`sota-architecture`](../sota-architecture/SKILL.md) | System design, service boundaries, monolith vs microservices, DDD, event-driven design, sagas/outbox, reconciliation against a third party that holds authoritative state, resilience (timeouts/retries/circuit breakers), scalability, multi-tenancy, 12-factor/cloud-native, architectural anti-patterns |
| [`sota-code-security`](../sota-code-security/SKILL.md) | Writing or reviewing code that touches untrusted input, authn/authz, sessions/JWT/OAuth, crypto, XSS/CSRF/CORS, file uploads, deserialization, error/log hygiene, LLM/agent app security, silent control failure (a safeguard that looks enabled and does nothing) |
| [`sota-threat-modeling`](../sota-threat-modeling/SKILL.md) | Designing a new system/feature with security in mind, drawing trust boundaries and DFDs, STRIDE/LINDDUN, risk rating, reconstructing a threat model from an existing codebase |
| [`sota-skill-security`](../sota-skill-security/SKILL.md) | Installing, authoring, reviewing or auditing anything an **agent loads as instructions** — skills, plugins, rulesets, `AGENTS.md`/`CLAUDE.md`/`.cursorrules`: provenance and pinning, review-before-install, the instruction trust boundary (a PR that edits an agent file changes what your agent does), precedence and shadowing between overlapping skills, capability minimisation, and guidance that is confidently wrong |
| [`sota-secrets-management`](../sota-secrets-management/SKILL.md) | API keys, passwords, tokens, signing/TLS/SSH keys, .env files, Vault/cloud secret managers, workload identity (OIDC), secret rotation, leak detection and remediation |
| [`sota-sandboxing`](../sota-sandboxing/SKILL.md) | Isolation of untrusted code or input, least privilege, seccomp/Landlock/capabilities, container/K8s hardening, microVMs, WASM sandboxes, subprocess hygiene, sandboxing AI-agent code execution |
| [`sota-performance`](../sota-performance/SKILL.md) | Latency, throughput, profiling, memory usage, caching (incl. stampede protection), I/O and network efficiency, Core Web Vitals, performance regression in CI |
| [`sota-async-concurrency`](../sota-async-concurrency/SKILL.md) | async/await, threads, goroutines, channels, races, deadlocks, event-loop blocking, cancellation/timeouts, graceful shutdown, backpressure, bounded queues |
| [`sota-api-design`](../sota-api-design/SKILL.md) | REST/HTTP semantics, pagination, idempotency, versioning/deprecation, GraphQL, gRPC/proto evolution, websockets/SSE/realtime, webhooks, API rate limiting and tenant isolation |
| [`sota-devsecops`](../sota-devsecops/SKILL.md) | CI/CD pipelines, GitHub Actions hardening, supply chain (SLSA, Sigstore, SBOM, dependency confusion), unused/inert dependencies and upstream-health checks, container builds, SAST/secret-scanning gates, Terraform/GitOps, admission control |
| [`sota-databases`](../sota-databases/SKILL.md) | Schema design, Postgres/NoSQL choice, migrations (zero-downtime), indexes/EXPLAIN, transactions/isolation, ledgers & account balances, connection pooling, replication/backups, Redis, RLS/DB security, pgvector |
| [`sota-frontend-design`](../sota-frontend-design/SKILL.md) | UI/UX, visual design, typography/color/layout, design systems and tokens, components, forms, accessibility (WCAG 2.2), motion/animation design, modern CSS, responsive design |
| [`sota-web-frameworks`](../sota-web-frameworks/SKILL.md) | React/Next.js and Vue/Nuxt engineering — Server Components & Server Actions, the RSC/client trust boundary, Next caching (`use cache`/PPR/ISR), Nitro server routes, hydration correctness, SSR state serialization, and framework-specific security & CVEs |
| [`sota-observability`](../sota-observability/SKILL.md) | Logging, metrics, tracing (OpenTelemetry), SLOs/error budgets, alerting, health checks, dashboards, debugging production, "can we answer why is this slow?" |
| [`sota-testing`](../sota-testing/SKILL.md) | Test strategy (pyramid/trophy), unit vs integration boundaries, test design/smells, mocks/fakes/test data, contract testing, e2e, property-based/fuzzing/mutation testing, flaky tests, coverage policy |
| [`sota-llm-engineering`](../sota-llm-engineering/SKILL.md) | Building LLM features — evals, prompt/context engineering, structured output, RAG, agents/tool design, MCP, model selection/routing, latency/cost engineering, LLM observability — **and any question about a model's tokens, context window, pricing or limits**, including measuring your own files |
| [`sota-ml-engineering`](../sota-ml-engineering/SKILL.md) | Production ML/MLOps (classical/predictive, *not* LLM apps) — training→serving→monitoring lifecycle, feature stores & registries, data leakage & train/serve skew, evaluation (ML Test Score, slices), deployment (canary/shadow/rollback), drift monitoring (PSI/KS) & retraining, ML security/governance (poisoning, MITRE ATLAS, NIST AI RMF) |
| [`sota-cloud-infrastructure`](../sota-cloud-infrastructure/SKILL.md) | Cloud accounts/landing zones, cloud IAM, VPC/subnet/DNS/CDN setup, compute selection (serverless vs containers vs K8s), object storage, FinOps/cost, RTO/RPO and disaster recovery |
| [`sota-kubernetes`](../sota-kubernetes/SKILL.md) | Kubernetes platform security & ops — RBAC & escalation paths, admission control (PSA/Kyverno/Gatekeeper/VAP, Audit→Enforce), GitOps controllers (Argo CD/Flux, AppProject scoping), operators/CRDs/webhooks, control plane & etcd encryption, Helm supply chain, multi-tenancy, cluster lifecycle, K8s audit logging; self-hosted (Talos/k3s) and managed |
| [`sota-identity-access`](../sota-identity-access/SKILL.md) | Identity infrastructure & access management — OIDC/OAuth2.1/SAML/SCIM protocols, running an IdP (Kanidm/Keycloak/etc.), RBAC/ABAC/ReBAC authorization design, group→role mapping, joiner-mover-leaver lifecycle, deprovisioning, privileged access & break-glass, SPIFFE/workload identity, phishing-resistant MFA/passkeys, federation risk |
| [`sota-network-security`](../sota-network-security/SKILL.md) | Network security as a discipline — zero-trust (NIST 800-207), segmentation & blast-radius, the `world`/`any` over-broad-rule trap, Kubernetes NetworkPolicy depth (Cilium L7, default-deny egress), service mesh & mTLS / internal encryption, edge/ingress/WAF, egress control & metadata-endpoint blocking, DNS/TLS/PKI & cert lifecycle, email auth (SPF/DKIM/DMARC) |
| [`sota-confidential-computing`](../sota-confidential-computing/SKILL.md) | Protecting workloads/data from the infrastructure operator — TEEs (AMD SEV-SNP, Intel TDX, ARM CCA, SGX enclaves, Nitro Enclaves, confidential GPUs), remote attestation (RATS, attest-then-release), confidential VMs/nodes/containers on K8s (CoCo/Kata/Trustee), and cryptographic PETs (FHE, MPC, ZKP, PSI) when hardware trust is off the table |
| [`sota-detection-engineering`](../sota-detection-engineering/SKILL.md) | Detective controls, SOC & IR — detection-as-code, Sigma/YARA/Suricata/Falco/Tetragon rules, ATT&CK coverage, SIEM & telemetry coverage, alert tuning/SOAR, threat hunting & intel (STIX/TAXII), deception/honeytokens, incident response (NIST 800-61), detection validation (Atomic Red Team/Caldera) |
| [`sota-data-engineering`](../sota-data-engineering/SKILL.md) | Data pipelines, ELT/orchestration, dbt, Kafka/streaming, CDC, schema registry, lakehouse (Iceberg/Delta/Parquet), data quality/contracts, warehouse modeling |
| [`sota-privacy-compliance`](../sota-privacy-compliance/SKILL.md) | PII inventory/classification, privacy by design, consent, DSAR/deletion architecture, retention, GDPR/CCPA/HIPAA/PCI/AI Act engineering obligations, SOC 2/ISO 27001 audit readiness, breach response |
| [`sota-security-compliance`](../sota-security-compliance/SKILL.md) | Cybersecurity control frameworks & product-security regulations as engineering — NIST CSF 2.0, SP 800-53, 800-171/CMMC, SSDF (800-218), FedRAMP, EU Cyber Resilience Act (SBOM/CVD/signed updates), ISA/IEC 62443 (OT zones & conduits, Security Levels); control-framework-as-code crosswalks, CUI boundaries, FIPS-validated crypto |
| [`sota-mobile`](../sota-mobile/SKILL.md) | iOS/Android/cross-platform apps — stack choice, offline-first/sync, push, mobile security (Keychain/Keystore, attestation), performance budgets, store requirements, staged rollouts |
| [`sota-cli-ux`](../sota-cli-ux/SKILL.md) | CLI/developer-tool design — flags/subcommands, config precedence, stdout/stderr and --json contracts, exit codes, TTY detection, signals, completions, distribution |
| [`sota-shell-scripting`](../sota-shell-scripting/SKILL.md) | Bash/sh scripts, CI run blocks, entrypoints, Makefiles — safety baseline (quoting, set -euo pipefail, traps), injection, secrets in scripts, shellcheck/shfmt |
| [`sota-docs-workflow`](../sota-docs-workflow/SKILL.md) | Documentation (Diátaxis, READMEs, runbooks, API docs, changelogs, AGENTS.md), code review/PR workflow, commit/branch/release discipline |
| [`sota-ux-writing`](../sota-ux-writing/SKILL.md) | Any user-facing interface text — microcopy, button/label wording, error messages, empty states, onboarding copy, notifications, tone of voice, terminology, alt text, i18n-ready strings |
| [`sota-copywriting`](../sota-copywriting/SKILL.md) | Outward-facing content — landing pages, headlines/CTAs, value propositions, SEO content, testimonials/social proof, claim substantiation, email marketing, app-store listings |
| [`sota-rust`](../sota-rust/SKILL.md) | Any Rust code — ownership/API design, error handling, unsafe discipline, tokio/async, supply chain (cargo audit/deny/vet), performance, clippy/CI |
| [`sota-golang`](../sota-golang/SKILL.md) | Any Go code — errors, package/interface design, goroutines/channels/leaks, net/http hardening, security (os/exec, os.Root, govulncheck), pprof/performance, golangci-lint/CI |
| [`sota-c-cpp`](../sota-c-cpp/SKILL.md) | Any C/C++ code — RAII/idioms, memory safety (UAF/overflow/sanitizers), undefined behavior, security (CERT/MISRA, banned APIs, OpenSSF hardening flags), concurrency/atomics, CMake/clang-tidy/fuzzing CI, performance |
| [`sota-jvm`](../sota-jvm/SKILL.md) | Any Java/Kotlin code — modern idioms (records/sealed/pattern-matching, Kotlin null-safety/coroutines), API/null/immutability design, concurrency (virtual threads, JMM, j.u.c, coroutines), security (deserialization/JNDI/XXE/injection, JCA crypto), GC/JFR/GraalVM performance, Maven/Gradle supply-chain & CI |
| [`sota-python`](../sota-python/SKILL.md) | Any Python code — uv/ruff/typing setup, idioms/pitfalls, asyncio, security (pickle/subprocess/SQL), performance, FastAPI/Django/pytest |
| [`sota-javascript-typescript`](../sota-javascript-typescript/SKILL.md) | Any JS/TS code — strict tsconfig/type design, idioms, promises/AbortController, Node backend hardening, XSS/supply-chain security, bundle/React performance, vitest/ESLint |
| [`sota-dotnet`](../sota-dotnet/SKILL.md) | Any C#/.NET code — modern idioms (records, nullable reference types, pattern matching, spans), API/disposal/DI design, async/await & concurrency (ConfigureAwait, cancellation, channels), security (EF/Dapper SQL, deserialization, ASP.NET Core auth, crypto), GC/Span/AOT performance, NuGet supply chain & analyzers/CI |
| [`sota-php`](../sota-php/SKILL.md) | Any PHP code — strict_types/modern idioms (enums, readonly, match), security (PDO/SQLi, XSS escaping, uploads/LFI, unserialize/Phar, sessions, password_hash/sodium), framework-neutral web hardening, Composer supply chain, PHPStan/Psalm, OPcache/FPM/JIT performance |
| [`sota-ruby`](../sota-ruby/SKILL.md) | Any Ruby code — idioms (frozen strings, pattern matching, RBS/Sorbet), security (AR/SQLi, ERB escaping, strong params, Marshal/YAML.load, command injection, ReDoS), Bundler supply chain (bundler-audit, lockfile checksums), RuboCop/Brakeman, GVL/Ractors/YJIT performance |
| [`sota-swift`](../sota-swift/SKILL.md) | Any Swift code — on any target (server-side Vapor/Hummingbird/SwiftNIO, CLIs, packages, apps): optionals/errors, Swift 6 data-race safety (Sendable, actors, cancellation), ARC/retain cycles, unsafe pointers & strict memory safety, security (CryptoKit, Codable/NSKeyedUnarchiver, SQLKit raw SQL, Process, TLS), server defaults (auth middleware, cookies, release builds), SwiftPM supply chain (Package.resolved, plugins/macros, SBOM) |

## What your code does: the rules file to read

When the code you are about to write does one of these things, read the file in full, then
check your change against it and its Audit checklist before you finish. These rules apply to this change: they are part of what was asked, not extras beyond the spec. Build what each one requires now, with a conservative default (a cap, a limit, an allow-list, a guard). Do not hand it back as a question or a note instead of building it, unless the user's request explicitly rules it out. In your final message, name each default you chose in one line, so the user can change it.

| When your code... | Read in full, then check |
|---|---|
| fetches a URL (§5 SSRF); writes CSV or spreadsheet output (§11, CSV/formula injection); builds an email or a message header (§11, CRLF / header injection); runs a process (§3 command injection); builds a database query (§2 SQL injection); parses or builds XML (§6 XXE and XML); deserialises data (§8 unsafe deserialization) | [`sota-code-security` rules/01](../sota-code-security/rules/01-input-injection.md) |
| reads or extracts an archive | [`sota-code-security` rules/01](../sota-code-security/rules/01-input-injection.md) §4 path traversal and Zip Slip; [`sota-code-security` rules/09](../sota-code-security/rules/09-untrusted-data-ingestion.md) untrusted data ingestion |
| accepts a file or image from outside | [`sota-code-security` rules/21](../sota-code-security/rules/21-file-uploads.md) §1 file upload handling; [`sota-code-security` rules/09](../sota-code-security/rules/09-untrusted-data-ingestion.md) untrusted data ingestion |
| renders HTML or a template (XSS and web security) | [`sota-code-security` rules/05](../sota-code-security/rules/05-web-security.md) |
| checks a password or handles a login (§1, credential stuffing, lockout and enumeration) | [`sota-code-security` rules/02](../sota-code-security/rules/02-authentication.md) |
| issues or checks a session or token | [`sota-code-security` rules/17](../sota-code-security/rules/17-sessions-and-tokens.md) §2 session management; [`sota-code-security` rules/02](../sota-code-security/rules/02-authentication.md) authentication |
| decides who may do what (§1-§3 deny by default, IDOR, function-level authorization) | [`sota-code-security` rules/03](../sota-code-security/rules/03-authorization.md) |
| sends or receives a webhook or callback (webhooks) | [`sota-api-design` rules/06](../sota-api-design/rules/06-webhooks.md) |
| returns a list that can grow (§4 pagination); moves money or must not run twice (§6 idempotency keys) | [`sota-api-design` rules/01](../sota-api-design/rules/01-rest-http-design.md) |
| calls something that can fail or hang (§1-§3 timeouts, retries, circuit breakers) | [`sota-architecture` rules/04](../sota-architecture/rules/04-resilience-and-failure-design.md) |
| logs, returns errors, or returns records about people (§1, §2 and §4: errors, logs, response over-exposure) | [`sota-code-security` rules/07](../sota-code-security/rules/07-data-exposure.md) |
| adds a request handler or endpoint | [`sota-api-design` rules/07](../sota-api-design/rules/07-security-operations.md) §2 rate limiting; [`sota-code-security` rules/06](../sota-code-security/rules/06-memory-resource-safety.md) §5 resource exhaustion |

## Cross-cutting routing rules

1. **Language skills stack on domain skills.** Auditing a Go API server → [`sota-golang`](../sota-golang/SKILL.md) + `sota-
   api-design` + [`sota-code-security`](../sota-code-security/SKILL.md). The language skill covers idioms and runtime-specific
   traps; domain skills cover the design. **A language with no skill** (Scala, Elixir, Dart, …) is
   not a dead end: apply the domain skills, say once that no language skill covers it, and take its
   idioms from that language's official docs. Swift on **any** target → [`sota-swift`](../sota-swift/SKILL.md).
2. **Security tasks usually need three skills.** Code-level flaws → [`sota-code-security`](../sota-code-security/SKILL.md); design-
   level gaps → [`sota-threat-modeling`](../sota-threat-modeling/SKILL.md); leaked or mishandled credentials → `sota-secrets-
   management`. Pipeline/supply-chain → [`sota-devsecops`](../sota-devsecops/SKILL.md); isolation blast-radius → `sota-
   sandboxing`.
3. **Performance complaints about queries** → start in [`sota-databases`](../sota-databases/SKILL.md) (EXPLAIN, indexes, N+1)
   before [`sota-performance`](../sota-performance/SKILL.md) (caching, I/O).
4. **Anything realtime** (websockets, SSE, pub/sub fanout) → [`sota-api-design` rules/05](../sota-api-design/rules/05-realtime-websockets-sse.md) + `sota-
   async-concurrency` (backpressure).
5. **AI/LLM features** → [`sota-code-security` rules/08](../sota-code-security/rules/08-llm-ai-security.md) (prompt injection, tool authorization) +
   [`sota-sandboxing` rules/05](../sota-sandboxing/rules/05-ai-agent-sandboxing.md) (executing model output) + [`sota-databases` rules/07](../sota-databases/rules/07-vector-and-ai.md) (vectors/RAG).
6. **Frontend work** → [`sota-frontend-design`](../sota-frontend-design/SKILL.md) for design/UX/a11y/motion; [`sota-web-frameworks`](../sota-web-frameworks/SKILL.md) for
   React/Next or Vue/Nuxt engineering (RSC/client boundary, Server Actions, caching, hydration,
   SSR security); [`sota-javascript-typescript`](../sota-javascript-typescript/SKILL.md) for the language/TS; [`sota-performance` rules/06](../sota-performance/rules/06-frontend-web.md)
   for Web Vitals. A React/Next or Vue/Nuxt security review pulls all four.
7. **Tests accompany everything.** Any BUILD task that writes logic also loads [`sota-testing`](../sota-testing/SKILL.md)
   (strategy + design rules); any AUDIT includes a suite-health pass. Language-specific runner
   mechanics stay in the language skills.
8. **LLM features split three ways.** Quality/architecture → [`sota-llm-engineering`](../sota-llm-engineering/SKILL.md); security
   (prompt injection, tool authz) → [`sota-code-security` rules/08](../sota-code-security/rules/08-llm-ai-security.md); executing model output → `sota-
   sandboxing` [rules/05](../sota-sandboxing/rules/05-ai-agent-sandboxing.md); PII in prompts/logs → [`sota-privacy-compliance`](../sota-privacy-compliance/SKILL.md).
9. **Infra layers split four ways.** Cloud-provider setup (accounts, VPC, compute, cost, DR) →
   [`sota-cloud-infrastructure`](../sota-cloud-infrastructure/SKILL.md); the Kubernetes platform itself (RBAC, admission, GitOps
   controllers, operators, etcd) → [`sota-kubernetes`](../sota-kubernetes/SKILL.md); pod/container/workload isolation mechanics →
   [`sota-sandboxing`](../sota-sandboxing/SKILL.md); CI/CD and supply chain → [`sota-devsecops`](../sota-devsecops/SKILL.md). A K8s cluster audit loads `sota-
   kubernetes` + [`sota-network-security`](../sota-network-security/SKILL.md) + [`sota-sandboxing`](../sota-sandboxing/SKILL.md).
10. **Identity is its own layer.** App-level login/session/JWT-validation code →
    [`sota-code-security` rules/02](../sota-code-security/rules/02-authentication.md) (authn), [rules/17](../sota-code-security/rules/17-sessions-and-tokens.md) (sessions/JWT), [rules/03](../sota-code-security/rules/03-authorization.md) (authz); identity
    *infrastructure* (IdP, OIDC/SAML config, RBAC/role-mapping
    design, provisioning, break-glass, SPIFFE) → [`sota-identity-access`](../sota-identity-access/SKILL.md); the credentials
    themselves → [`sota-secrets-management`](../sota-secrets-management/SKILL.md).
11. **Network: setup vs security.** Cloud VPC/DNS/CDN provisioning → [`sota-cloud-infrastructure`
    rules/03](../sota-cloud-infrastructure/rules/03-networking.md); segmentation, zero-trust, NetworkPolicy depth, service mesh/mTLS, egress/DNS/PKI
    posture → [`sota-network-security`](../sota-network-security/SKILL.md).
12. **Prevention vs detection.** Building the control → the relevant domain skill; verifying you'd
    *catch* the attack at runtime (logs, rules, hunting, IR) → [`sota-detection-engineering`](../sota-detection-engineering/SKILL.md). Ops
    telemetry plumbing stays in [`sota-observability`](../sota-observability/SKILL.md); design-time threat enumeration in `sota-
    threat-modeling`.
13. **Ingesting untrusted/attacker-authored data** (feeds, scraping, uploads, webhooks, RAG
    corpora, hostile parsers) → [`sota-code-security` rules/09](../sota-code-security/rules/09-untrusted-data-ingestion.md), with [`sota-sandboxing` rules/04](../sota-sandboxing/rules/04-process-app-sandboxing.md) for
    parser isolation. A tool ingesting whole **repositories** (scanner, SAST wrapper, review bot,
    agentic analyser) adds [`sota-sandboxing` rules/05](../sota-sandboxing/rules/05-ai-agent-sandboxing.md) §7 — staging, build execution, egress.
14. **Data: OLTP vs analytics.** App databases → [`sota-databases`](../sota-databases/SKILL.md); pipelines, streaming,
    warehouse/lakehouse → [`sota-data-engineering`](../sota-data-engineering/SKILL.md); anything touching personal data → add `sota-
    privacy-compliance`.
15. **Any handling of user/personal data** (new fields, exports, logs, analytics, ML training) →
    check [`sota-privacy-compliance`](../sota-privacy-compliance/SKILL.md) minimization and retention rules, even when the task isn't
    "about" privacy.
16. **User-facing words split three ways.** In-product UI text (labels, errors, empty states) →
    [`sota-ux-writing`](../sota-ux-writing/SKILL.md); marketing/site/email content → [`sota-copywriting`](../sota-copywriting/SKILL.md); technical docs → `sota-
    docs-workflow`. The component patterns the text lives in stay [`sota-frontend-design`](../sota-frontend-design/SKILL.md).
17. **Shell scripts hide everywhere** — CI run blocks, Dockerfile RUN lines, Makefiles,
    entrypoints, **and the one-liners you type to verify a claim**: unlinted shell run
    against the system under test, which when wrong produces a false finding *about the
    product* (a usage error, exit 2, from the callee is the tell — but a failed glob is
    **silent** and fakes a clean result). Audit it all with [`sota-shell-scripting`
    rules/01](../sota-shell-scripting/rules/01-safety-baseline.md) §3 and **[rules/06](../sota-shell-scripting/rules/06-ad-hoc-commands.md)**, the file for pasted and agent-issued commands. And a script that **produces or
    verifies evidence** (attestations, ledgers, gate records, audit trails) is a security
    control written in shell: add [`sota-code-security` rules/10](../sota-code-security/rules/10-silent-control-failure.md), [rules/12](../sota-code-security/rules/12-verifying-the-verifier.md), [rules/15](../sota-code-security/rules/15-instruments-and-guards.md) and, for
    a ledger or audit trail, [rules/18](../sota-code-security/rules/18-tamper-evident-logs.md).
18. **Cryptography fans out — there is no single crypto skill (by design).** Algorithm choice,
    AEAD/nonce discipline, CSPRNG, in-code key handling, TLS client config, crypto agility, and
    post-quantum migration → [`sota-code-security` rules/04](../sota-code-security/rules/04-cryptography.md); constant-time comparison → [rules/22](../sota-code-security/rules/22-constant-time-comparison.md);
    tamper-evident logs/audit ledgers (keyed hash chains, external anchoring,
    integrity-vs-completeness) → [rules/18](../sota-code-security/rules/18-tamper-evident-logs.md). The key *material* — storage backends (KMS/HSM, Vault, SOPS+age), lifecycle,
    rotation, per-credential-type handling → [`sota-secrets-management`](../sota-secrets-management/SKILL.md). Transport/PKI — TLS server
    config, cert lifecycle/ACME, private CA, mTLS → [`sota-network-security` rules/06](../sota-network-security/rules/06-dns-tls-pki.md).
    FIPS-140-3-validated-module requirements → [`sota-security-compliance` rules/02](../sota-security-compliance/rules/02-nist-800-53-171-cmmc-fedramp.md). Language-
    specific APIs (JCA, `crypto/*`, .NET) stay in the language skill. The stance throughout is
    **use a vetted library, don't roll your own**.
19. **Which direction does the trust boundary point?** Protecting the *host from the workload*
    (untrusted code, seccomp/microVMs/WASM sandboxes) → [`sota-sandboxing`](../sota-sandboxing/SKILL.md). Protecting the
    *workload from the host/operator* — TEEs (SEV-SNP/TDX/CCA/SGX), remote attestation,
    confidential VMs/containers, or computing on encrypted data (FHE/MPC/ZKP) → `sota-
    confidential-computing`. Both can apply to one system. Key custody/release stays `sota-
    secrets-management`; differential privacy and de-identification stay `sota-privacy-
    compliance`.
20. **"It's enabled" is a claim, not a fact.** Whenever a control's *presence* is established but
    its *effect* isn't — a banner, a config flag, a green test, "we have a scanner" — route to
    [`sota-code-security` rules/10](../sota-code-security/rules/10-silent-control-failure.md) (silent control failure). It pairs with [`sota-testing` rules/06](../sota-testing/rules/06-property-fuzzing-mutation.md)
    (mutation-probe the control) and [rules/09](../sota-testing/rules/09-security-testing.md) (a security test must be watched to fail), `sota-
    observability` [rules/05](../sota-observability/rules/05-operational-readiness.md) (degradation must be visible), and [`sota-devsecops` rules/04](../sota-devsecops/rules/04-build-containers.md) (does the
    shipped artifact contain what the control needs at runtime?). Not for controls that are simply
    *missing* — that's the owning domain skill's audit checklist.

21. **Model facts hide in your own tooling** — the same shape as rule 17. Any question
    about a model's **tokens, context window, pricing or limits** is [`sota-llm-engineering`](../sota-llm-engineering/SKILL.md)
    ([rules/02](../sota-llm-engineering/rules/02-prompt-context-engineering.md) §2 for counting, [rules/05](../sota-llm-engineering/rules/05-production-engineering.md) for cost), *including* measuring your own files,
    prompts or docs, and even when the surrounding task is repo maintenance and nothing
    looks like an LLM feature. The tell is a chars/4 estimate or another vendor's tokenizer
    instead of the provider's `count_tokens` (measured 2026-08-26: 54% under).

## Day zero — a repo this library has not been applied to yet

Installing is *ambient*: the rules apply in every directory, including a repo with no gates, no
agent file and no LICENSE. They then govern the code you write and nothing else — the repo keeps
accepting unscanned commits. Check this **once per repo**, on the first BUILD task in an
unfamiliar one, by looking (not inferring): is there a `.pre-commit-config.yaml` **or any other
hook manager or CI job** running a secret scan; a license file (`LICENSE*`, `COPYING*` or
`COPYRIGHT` — never match the bare name, projects name it after the licence); an
`AGENTS.md`/`CLAUDE.md`; and how long is the git history? Two or more missing **and** a history
of a few commits = day zero. A long history means a mature repo that likely decided against
them; say nothing.

When it fires, say it **once, in a line, with the command**, then get on with the
task: `scripts/init-gates.sh` for gates — it installs both the pre-commit and
pre-push hooks; a bare `--hook-type pre-push` would install only the latter
(before the first commit, while a leaked credential is still free to
remove), `scripts/gen-agents-md.sh` for the cross-tool entry point. Full ordering
and reasoning — LICENSE, `.gitignore`, ambient-vs-repo-resident, the
`core.symlinks` trap — in [`sota-docs-workflow` rules/01](../sota-docs-workflow/rules/01-documentation-architecture.md) §10.

**Offer, never perform.** These write config into the user's repo. Mention once,
act only on a yes, and treat a decline as decided.

## BUILD mode — workflow

Reasoning and worked examples: [`rules/02-build-workflow.md`](rules/02-build-workflow.md). **Changing a step below?
It is mirrored in four places — [`rules/02`](rules/02-build-workflow.md) §5 lists them, and three fail silently.**

1. Identify the domains the feature touches (table above) and the language(s).
2. **Load lean.** Read each relevant skill's `SKILL.md` and, from its index, open **only**
   the rules files that match the work. Lean costs less and measures no worse; the
   degradation this step once claimed is **not supported** — [`rules/02`](rules/02-build-workflow.md) §1.
   **One rules file is not selected by subject.** [`sota-shell-scripting` **rules/06](../sota-shell-scripting/rules/06-ad-hoc-commands.md)**
   governs the commands *you* type to check things — sweeps, counts, absence claims — and
   no task description ever matches it, because the task is never *about* checking. Load
   it on any task where you will verify a claim with a command, which is nearly all of
   them. Subject routing cannot reach it: cross-cutting rule 17 names it and still does
   not fire, because it reads as advice about where shell code hides in a repository
   rather than about your own next command. Field-reported twice, 2026-09-18 and
   2026-09-21 — the second by a reader who had rule 17 in context.
3. **Plan first, with the checks in the plan.** Before writing code, list the task's
   requirements as **concrete, checkable items** — a specific outcome you can mark
   done/not-done ("rate-limit login to N/min per IP", not "add rate limiting") — covering
   the top-10 non-negotiables of each loaded skill plus operating principle 5. Vague items
   don't survive to step 4. Then implement against that list.
4. **Self-audit gate (do this LAST — do not present code until it passes).** **First list the rules files step 2
   loaded**: none, or no [`sota-shell-scripting` rules/06](../sota-shell-scripting/rules/06-ad-hoc-commands.md) when you verified by command, and this gate has FAILED — go back. Re-read each
   loaded rules file's **Audit checklist** *and* operating principle 5, and verify your
   diff satisfies every item. For each unmet item, **implement it** or state why it is out
   of scope — silence is not allowed. For every control, ask the **falsification
   question**: *if this were silently a no-op, would anything observable differ?* If
   nothing would — no log, no metric, no failing test — it is not done
   ([`sota-code-security` rules/10](../sota-code-security/rules/10-silent-control-failure.md)). **If the control emits an artifact, read back the one
   this run just produced.** Doing this *last* is deliberate: a long context makes
   mid-context rules fade, and the final re-read is what recovers the rate limiting,
   transport, tests and logging a model otherwise drops — measured as the bulk of the
   library's completeness lift (`evals/run-completeness.py`). For a large build, run it as
   a separate pass over the diff, and push the few critical invariants into deterministic
   gates ([`rules/02`](rules/02-build-workflow.md) §3).

## AUDIT mode — workflow

Procedure lives in two rules files, read together for any full audit: [`rules/01-audit-methodology.md`](rules/01-audit-methodology.md)
(scoping, the verified tool matrix, triage, hygiene) and [`rules/03-audit-findings.md`](rules/03-audit-findings.md) (severity —
chain closure, the diff baseline — evidence, the decision ledger, refutation, the report template).
**A new pass needs a line in this router and a section in the rules file that owns it, never here.**

For a focused audit, load the matching skills and follow their AUDIT sections. For a
**full project audit**, work in passes:

1. **Recon.** Inventory languages, frameworks, entry points (HTTP routes, queues, cron,
   webhooks), data stores, CI config, Dockerfiles, IaC. This determines which skills
   apply; skip skills with no matching surface. Full procedure: [`rules/01`](rules/01-audit-methodology.md) §2.
2. **Threat model first.** [`sota-threat-modeling` rules/06](../sota-threat-modeling/rules/06-audit-reconstruction.md) (reconstruction): assets, trust
   boundaries, entry points. Its output prioritizes the rest.
3. **Per-domain passes.** For each applicable skill, follow its AUDIT mode and audit
   checklists. Suggested order: secrets sweep (fast, high yield) → code security (incl.
   [rules/09](../sota-code-security/rules/09-untrusted-data-ingestion.md) untrusted-data ingestion) → language-specific (incl. shell scripts) → API →
   database → async/concurrency → identity & access → sandboxing/devsecops → kubernetes
   platform → network security → cloud infrastructure → privacy/compliance → architecture
   → testing suite health → performance → observability → detection-engineering posture →
   frontend/a11y → LLM features, data pipelines, mobile, CLI, docs as applicable. For an
   infrastructure/cluster audit the heavy hitters are [`sota-kubernetes`](../sota-kubernetes/SKILL.md),
   [`sota-network-security`](../sota-network-security/SKILL.md), [`sota-identity-access`](../sota-identity-access/SKILL.md), [`sota-sandboxing`](../sota-sandboxing/SKILL.md) and
   [`sota-detection-engineering`](../sota-detection-engineering/SKILL.md).
4. **Silent-control pass (always run it).** The per-domain passes ask "is the control
   there?" — this one asks "does it *do* anything?", then "does it cover **every** site it
   is credited with?". Apply [`sota-code-security` rules/10](../sota-code-security/rules/10-silent-control-failure.md) (inert controls — invisible to
   the other passes and to SAST), sweeping with [`rules/11`](../sota-code-security/rules/11-dead-path-diagnostics.md) first to find *where* to look:
   stage duration vs work claimed, every gate's denominator (`0 checked, 0 failed, exit 0`),
   size-gated paths no fixture crosses, cache keys narrower than the behaviour, one-sample
   parsers, `assert`-as-control. Then **count**: [`sota-code-security` rules/14](../sota-code-security/rules/14-control-not-in-force.md) §6 censuses
   what a *working* mitigation guards (9 of 61 is the finding), §7 falsifies the prose.
5. **Decision-ledger review.** Code passes find defects in what was built; they cannot
   find the defect where the code faithfully implements a choice that **stopped being
   right** — a store picked for scale that never arrived, an expired constraint still
   shaping the design. Reconstruct the expensive-to-reverse decisions (ADRs, design docs,
   CHANGELOG, the PRs behind each major component) and classify each **JUSTIFIED / STALE /
   UNJUSTIFIED / UNVERIFIABLE**. Where a decision rests on a number, **re-measure it this
   session**. Full procedure: [`rules/03`](rules/03-audit-findings.md) §3. **Then ask where else the team's knowledge
   lives** — an agent's private memory store, an IDE's notes, a chat log. Anything in
   there that is a *fact about the repository* with no home in the repository is a
   finding: invisible to review, absent from a fresh clone, gone when the store is
   cleared. It is an absence claim and the naive search for it lies — [`rules/01`](rules/01-audit-methodology.md) §4a.
6. **Findings.** Emit every finding in the canonical cross-domain format (`file:line |
   rule | severity | effort | fix`) — skill-local formats are fine within a domain pass but
   must carry an effort field so the roll-up can be sequenced — deduplicate across domains,
   and roll up into the report structure from [`rules/03`](rules/03-audit-findings.md) §5. **Severity: [`rules/03`](rules/03-audit-findings.md) §1** —
   a Critical/High names its chain, and a diff is rated against the code it replaced.
7. **Refute before reporting.** Re-reading your own finding re-runs the reasoning that
   produced it — it is the weakest check available. Every Critical/High gets an
   **independent pass prompted to kill it** (a separate agent, or a fresh-context hostile
   read), working from the code at the pinned commit rather than your write-up, defaulting
   to REFUTED when the evidence is ambiguous. Survivors ship; the rest are dropped or
   downgraded **with the refutation recorded** — and **swept first**: the refuted pattern
   routinely closes somewhere else, and that sweep is where the report's strongest finding
   comes from. Absence claims ("no X found") get a refuter too, and carry the heavier
   burden of principle 3. Full procedure and failure modes: [`rules/03`](rules/03-audit-findings.md) §4.

## Library map (rules files per skill)

Which `rules/NN` file holds what, for all 43 skills (42 domain skills + this router): **[rules/04-library-map.md](rules/04-library-map.md)**.
Read it when you know the domain but not the file. When you are already opening a skill's
`SKILL.md` (BUILD step 2), use that skill's own index instead — it carries the "read this
when…" guidance the map drops.

What keeps a delivered audit report usable once remediation starts — reproduction steps on every
finding, the finding lifecycle and retest, report provenance, verdicts that expire with their
commit, and the three-run bar for "fixed": **[rules/05-audit-report-and-tracking.md](rules/05-audit-report-and-tracking.md)**,
read with [`rules/03`](rules/03-audit-findings.md).

## Context budget discipline

Rules files run **52–500 lines, median 262.5** (over all 294 on 2026-09-26; dated because the
figure has gone stale before). So budget by the file you are actually opening, not by an
average: 2–5 files is a typical focused task and can be 400 lines or 2,000. A full audit pass
should load one skill at a time, finish its findings, then move on. If context is tight, prefer
the skill's top-10 non-negotiables plus the single most relevant rules file.

## When this library is wrong or missing something

These rules are maintained and measured, and they are still incomplete — the
library has no telemetry and learns nothing from use unless someone says so.
You are the only observer of the gap at the moment it appears.

If, while applying a skill, you hit one of these, **say so in one line at the end
of your answer** and point the user at the report path — then carry on with the
task:

- a rule contradicted by a primary source you just checked (version, spec, API,
  advisory) — freshness rot;
- a rule that does not fit the situation and states no exception for it;
- real surface area in the task with **no owning skill** — a routing gap;
- guidance that, followed literally, would have shipped a defect.

**Two loaded rules that contradict each other** are usually a scope collision:
one is a general default, the other a requirement inside a narrower domain. The
narrower wins *in its domain* — pick by which failure mode is worse here (a
needless idiom vs an outage), never silently: name the rule you followed and why
in a comment beside the code, or the next reader reverts it. Then report it —
the fix is an explicit exception in whichever rule was too broad.

**A routing gap should end as a test, not just a report**: how, in [`rules/04`](rules/04-library-map.md), its last section.

Report: `https://github.com/martinholovsky/SOTA-skills/issues/new/choose`
(bad-guidance / skill-request templates). Anything dangerous or
security-sensitive goes to a **private advisory** instead — see `SECURITY.md`.

Do not fire this for personal preference, for a rule you simply did not need, or
mid-task. One line, at the end, only when the library actually let the user down.
An unreported gap stays in the library for everyone.
