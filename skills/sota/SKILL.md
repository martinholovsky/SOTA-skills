---
name: sota
description: >-
  Master router for the SOTA engineering skills library. Use this skill whenever the user asks to build, design, implement, refactor, harden, optimize, review, or audit an application, service, or codebase and the request spans more than one domain — or when you are unsure which specific sota-* skill applies. It maps the task (build or audit mode) to the right domain skills (architecture, code security, threat modeling, secrets, sandboxing, performance, async/concurrency, APIs, devsecops, databases, frontend, web frameworks, observability, testing, LLM engineering, ML engineering, cloud, kubernetes, identity & access, network security, confidential computing, detection engineering, data engineering, privacy/compliance, security/compliance, mobile, CLI UX, UX writing, copywriting, shell scripting, docs/workflow) and language skills (Rust, Go, C/C++, JVM, Python, JS/TS, .NET/C#, PHP, Ruby). Trigger keywords: SOTA, best practices, audit my code, security review, compliance, hardening, prod readiness, code quality.
---

# SOTA Engineering Skills — Master Router

A library of 40 domain skills, each with a `SKILL.md` entry point and a `rules/`
folder of focused rule files (every file < 500 lines). Each skill works in two
modes:

- **BUILD** — apply the rules while designing or writing code.
- **AUDIT** — review existing code against the rules and emit findings in the
  canonical format below (it supersedes any per-skill variant):
  `file:line | rule violated | severity (Critical/High/Medium/Low/Info) |
  effort (trivial/small/medium/large) | fix`.

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
   What cannot be validated is either omitted or explicitly marked
   "needs verification" — never asserted.
1. **Freshness first.** The library's version/spec/regulation facts were
   web-verified as of the last refresh (see README). Never trust them — or
   training data — for anything version- or CVE-sensitive at use time:
   re-verify current releases and advisories before pinning or recommending.
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
   actually ran.
4. **Stack profile.** If the repo or `~/.claude` contains a `profiles/*.md`
   stack profile (preferred stores, auth provider, license policy, platform
   conventions), its choices are the defaults for BUILD mode and the expected
   baseline for AUDIT mode.
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

## Routing table

| Skill | Use when the task involves... |
|---|---|
| `sota-architecture` | System design, service boundaries, monolith vs microservices, DDD, event-driven design, sagas/outbox, resilience (timeouts/retries/circuit breakers), scalability, multi-tenancy, 12-factor/cloud-native, architectural anti-patterns |
| `sota-code-security` | Writing or reviewing code that touches untrusted input, authn/authz, sessions/JWT/OAuth, crypto, XSS/CSRF/CORS, file uploads, deserialization, error/log hygiene, LLM/agent app security, silent control failure (a safeguard that looks enabled and does nothing) |
| `sota-threat-modeling` | Designing a new system/feature with security in mind, drawing trust boundaries and DFDs, STRIDE/LINDDUN, risk rating, reconstructing a threat model from an existing codebase |
| `sota-secrets-management` | API keys, passwords, tokens, signing/TLS/SSH keys, .env files, Vault/cloud secret managers, workload identity (OIDC), secret rotation, leak detection and remediation |
| `sota-sandboxing` | Isolation of untrusted code or input, least privilege, seccomp/Landlock/capabilities, container/K8s hardening, microVMs, WASM sandboxes, subprocess hygiene, sandboxing AI-agent code execution |
| `sota-performance` | Latency, throughput, profiling, memory usage, caching (incl. stampede protection), I/O and network efficiency, Core Web Vitals, performance regression in CI |
| `sota-async-concurrency` | async/await, threads, goroutines, channels, races, deadlocks, event-loop blocking, cancellation/timeouts, graceful shutdown, backpressure, bounded queues |
| `sota-api-design` | REST/HTTP semantics, pagination, idempotency, versioning/deprecation, GraphQL, gRPC/proto evolution, websockets/SSE/realtime, webhooks, API rate limiting and tenant isolation |
| `sota-devsecops` | CI/CD pipelines, GitHub Actions hardening, supply chain (SLSA, Sigstore, SBOM, dependency confusion), container builds, SAST/secret-scanning gates, Terraform/GitOps, admission control |
| `sota-databases` | Schema design, Postgres/NoSQL choice, migrations (zero-downtime), indexes/EXPLAIN, transactions/isolation, connection pooling, replication/backups, Redis, RLS/DB security, pgvector |
| `sota-frontend-design` | UI/UX, visual design, typography/color/layout, design systems and tokens, components, forms, accessibility (WCAG 2.2), motion/animation design, modern CSS, responsive design |
| `sota-web-frameworks` | React/Next.js and Vue/Nuxt engineering — Server Components & Server Actions, the RSC/client trust boundary, Next caching (`use cache`/PPR/ISR), Nitro server routes, hydration correctness, SSR state serialization, and framework-specific security & CVEs |
| `sota-observability` | Logging, metrics, tracing (OpenTelemetry), SLOs/error budgets, alerting, health checks, dashboards, debugging production, "can we answer why is this slow?" |
| `sota-testing` | Test strategy (pyramid/trophy), unit vs integration boundaries, test design/smells, mocks/fakes/test data, contract testing, e2e, property-based/fuzzing/mutation testing, flaky tests, coverage policy |
| `sota-llm-engineering` | Building LLM features — evals, prompt/context engineering, structured output, RAG, agents/tool design, MCP, model selection/routing, latency/cost engineering, LLM observability |
| `sota-ml-engineering` | Production ML/MLOps (classical/predictive, *not* LLM apps) — training→serving→monitoring lifecycle, feature stores & registries, data leakage & train/serve skew, evaluation (ML Test Score, slices), deployment (canary/shadow/rollback), drift monitoring (PSI/KS) & retraining, ML security/governance (poisoning, MITRE ATLAS, NIST AI RMF) |
| `sota-cloud-infrastructure` | Cloud accounts/landing zones, cloud IAM, VPC/subnet/DNS/CDN setup, compute selection (serverless vs containers vs K8s), object storage, FinOps/cost, RTO/RPO and disaster recovery |
| `sota-kubernetes` | Kubernetes platform security & ops — RBAC & escalation paths, admission control (PSA/Kyverno/Gatekeeper/VAP, Audit→Enforce), GitOps controllers (Argo CD/Flux, AppProject scoping), operators/CRDs/webhooks, control plane & etcd encryption, Helm supply chain, multi-tenancy, cluster lifecycle, K8s audit logging; self-hosted (Talos/k3s) and managed |
| `sota-identity-access` | Identity infrastructure & access management — OIDC/OAuth2.1/SAML/SCIM protocols, running an IdP (Kanidm/Keycloak/etc.), RBAC/ABAC/ReBAC authorization design, group→role mapping, joiner-mover-leaver lifecycle, deprovisioning, privileged access & break-glass, SPIFFE/workload identity, phishing-resistant MFA/passkeys, federation risk |
| `sota-network-security` | Network security as a discipline — zero-trust (NIST 800-207), segmentation & blast-radius, the `world`/`any` over-broad-rule trap, Kubernetes NetworkPolicy depth (Cilium L7, default-deny egress), service mesh & mTLS / internal encryption, edge/ingress/WAF, egress control & metadata-endpoint blocking, DNS/TLS/PKI & cert lifecycle, email auth (SPF/DKIM/DMARC) |
| `sota-confidential-computing` | Protecting workloads/data from the infrastructure operator — TEEs (AMD SEV-SNP, Intel TDX, ARM CCA, SGX enclaves, Nitro Enclaves, confidential GPUs), remote attestation (RATS, attest-then-release), confidential VMs/nodes/containers on K8s (CoCo/Kata/Trustee), and cryptographic PETs (FHE, MPC, ZKP, PSI) when hardware trust is off the table |
| `sota-detection-engineering` | Detective controls, SOC & IR — detection-as-code, Sigma/YARA/Suricata/Falco/Tetragon rules, ATT&CK coverage, SIEM & telemetry coverage, alert tuning/SOAR, threat hunting & intel (STIX/TAXII), deception/honeytokens, incident response (NIST 800-61), detection validation (Atomic Red Team/Caldera) |
| `sota-data-engineering` | Data pipelines, ELT/orchestration, dbt, Kafka/streaming, CDC, schema registry, lakehouse (Iceberg/Delta/Parquet), data quality/contracts, warehouse modeling |
| `sota-privacy-compliance` | PII inventory/classification, privacy by design, consent, DSAR/deletion architecture, retention, GDPR/CCPA/HIPAA/PCI/AI Act engineering obligations, SOC 2/ISO 27001 audit readiness, breach response |
| `sota-security-compliance` | Cybersecurity control frameworks & product-security regulations as engineering — NIST CSF 2.0, SP 800-53, 800-171/CMMC, SSDF (800-218), FedRAMP, EU Cyber Resilience Act (SBOM/CVD/signed updates), ISA/IEC 62443 (OT zones & conduits, Security Levels); control-framework-as-code crosswalks, CUI boundaries, FIPS-validated crypto |
| `sota-mobile` | iOS/Android/cross-platform apps — stack choice, offline-first/sync, push, mobile security (Keychain/Keystore, attestation), performance budgets, store requirements, staged rollouts |
| `sota-cli-ux` | CLI/developer-tool design — flags/subcommands, config precedence, stdout/stderr and --json contracts, exit codes, TTY detection, signals, completions, distribution |
| `sota-shell-scripting` | Bash/sh scripts, CI run blocks, entrypoints, Makefiles — safety baseline (quoting, set -euo pipefail, traps), injection, secrets in scripts, shellcheck/shfmt |
| `sota-docs-workflow` | Documentation (Diátaxis, READMEs, runbooks, API docs, changelogs, AGENTS.md), code review/PR workflow, commit/branch/release discipline |
| `sota-ux-writing` | Any user-facing interface text — microcopy, button/label wording, error messages, empty states, onboarding copy, notifications, tone of voice, terminology, alt text, i18n-ready strings |
| `sota-copywriting` | Outward-facing content — landing pages, headlines/CTAs, value propositions, SEO content, testimonials/social proof, claim substantiation, email marketing, app-store listings |
| `sota-rust` | Any Rust code — ownership/API design, error handling, unsafe discipline, tokio/async, supply chain (cargo audit/deny/vet), performance, clippy/CI |
| `sota-golang` | Any Go code — errors, package/interface design, goroutines/channels/leaks, net/http hardening, security (os/exec, os.Root, govulncheck), pprof/performance, golangci-lint/CI |
| `sota-c-cpp` | Any C/C++ code — RAII/idioms, memory safety (UAF/overflow/sanitizers), undefined behavior, security (CERT/MISRA, banned APIs, OpenSSF hardening flags), concurrency/atomics, CMake/clang-tidy/fuzzing CI, performance |
| `sota-jvm` | Any Java/Kotlin code — modern idioms (records/sealed/pattern-matching, Kotlin null-safety/coroutines), API/null/immutability design, concurrency (virtual threads, JMM, j.u.c, coroutines), security (deserialization/JNDI/XXE/injection, JCA crypto), GC/JFR/GraalVM performance, Maven/Gradle supply-chain & CI |
| `sota-python` | Any Python code — uv/ruff/typing setup, idioms/pitfalls, asyncio, security (pickle/subprocess/SQL), performance, FastAPI/Django/pytest |
| `sota-javascript-typescript` | Any JS/TS code — strict tsconfig/type design, idioms, promises/AbortController, Node backend hardening, XSS/supply-chain security, bundle/React performance, vitest/ESLint |
| `sota-dotnet` | Any C#/.NET code — modern idioms (records, nullable reference types, pattern matching, spans), API/disposal/DI design, async/await & concurrency (ConfigureAwait, cancellation, channels), security (EF/Dapper SQL, deserialization, ASP.NET Core auth, crypto), GC/Span/AOT performance, NuGet supply chain & analyzers/CI |
| `sota-php` | Any PHP code — strict_types/modern idioms (enums, readonly, match), security (PDO/SQLi, XSS escaping, uploads/LFI, unserialize/Phar, sessions, password_hash/sodium), framework-neutral web hardening, Composer supply chain, PHPStan/Psalm, OPcache/FPM/JIT performance |
| `sota-ruby` | Any Ruby code — idioms (frozen strings, pattern matching, RBS/Sorbet), security (AR/SQLi, ERB escaping, strong params, Marshal/YAML.load, command injection, ReDoS), Bundler supply chain (bundler-audit, lockfile checksums), RuboCop/Brakeman, GVL/Ractors/YJIT performance |

## Cross-cutting routing rules

1. **Language skills stack on domain skills.** Auditing a Go API server →
   `sota-golang` + `sota-api-design` + `sota-code-security`. The language skill
   covers idioms and runtime-specific traps; domain skills cover the design.
2. **Security tasks usually need three skills.** Code-level flaws →
   `sota-code-security`; design-level gaps → `sota-threat-modeling`; leaked or
   mishandled credentials → `sota-secrets-management`. Pipeline/supply-chain →
   `sota-devsecops`; isolation blast-radius → `sota-sandboxing`.
3. **Performance complaints about queries** → start in `sota-databases`
   (EXPLAIN, indexes, N+1) before `sota-performance` (caching, I/O).
4. **Anything realtime** (websockets, SSE, pub/sub fanout) →
   `sota-api-design` rules/05 + `sota-async-concurrency` (backpressure).
5. **AI/LLM features** → `sota-code-security` rules/08 (prompt injection,
   tool authorization) + `sota-sandboxing` rules/05 (executing model output) +
   `sota-databases` rules/07 (vectors/RAG).
6. **Frontend work** → `sota-frontend-design` for design/UX/a11y/motion;
   `sota-web-frameworks` for React/Next or Vue/Nuxt engineering (RSC/client
   boundary, Server Actions, caching, hydration, SSR security);
   `sota-javascript-typescript` for the language/TS; `sota-performance` rules/06
   for Web Vitals. A React/Next or Vue/Nuxt security review pulls all four.
7. **Tests accompany everything.** Any BUILD task that writes logic also loads
   `sota-testing` (strategy + design rules); any AUDIT includes a suite-health
   pass. Language-specific runner mechanics stay in the language skills.
8. **LLM features split three ways.** Quality/architecture →
   `sota-llm-engineering`; security (prompt injection, tool authz) →
   `sota-code-security` rules/08; executing model output → `sota-sandboxing`
   rules/05; PII in prompts/logs → `sota-privacy-compliance`.
9. **Infra layers split four ways.** Cloud-provider setup (accounts, VPC,
   compute, cost, DR) → `sota-cloud-infrastructure`; the Kubernetes platform
   itself (RBAC, admission, GitOps controllers, operators, etcd) →
   `sota-kubernetes`; pod/container/workload isolation mechanics →
   `sota-sandboxing`; CI/CD and supply chain → `sota-devsecops`. A K8s cluster
   audit loads `sota-kubernetes` + `sota-network-security` + `sota-sandboxing`.
10. **Identity is its own layer.** App-level login/session/JWT-validation code →
   `sota-code-security` rules/02-03; identity *infrastructure* (IdP, OIDC/SAML
   config, RBAC/role-mapping design, provisioning, break-glass, SPIFFE) →
   `sota-identity-access`; the credentials themselves → `sota-secrets-management`.
11. **Network: setup vs security.** Cloud VPC/DNS/CDN provisioning →
   `sota-cloud-infrastructure` rules/03; segmentation, zero-trust, NetworkPolicy
   depth, service mesh/mTLS, egress/DNS/PKI posture → `sota-network-security`.
12. **Prevention vs detection.** Building the control → the relevant domain
   skill; verifying you'd *catch* the attack at runtime (logs, rules, hunting,
   IR) → `sota-detection-engineering`. Ops telemetry plumbing stays in
   `sota-observability`; design-time threat enumeration in `sota-threat-modeling`.
13. **Ingesting untrusted/attacker-authored data** (feeds, scraping, uploads,
   webhooks, RAG corpora, hostile parsers) → `sota-code-security` rules/09,
   with `sota-sandboxing` rules/04 for parser isolation.
14. **Data: OLTP vs analytics.** App databases → `sota-databases`; pipelines,
    streaming, warehouse/lakehouse → `sota-data-engineering`; anything touching
    personal data → add `sota-privacy-compliance`.
15. **Any handling of user/personal data** (new fields, exports, logs,
    analytics, ML training) → check `sota-privacy-compliance` minimization and
    retention rules, even when the task isn't "about" privacy.
16. **User-facing words split three ways.** In-product UI text (labels,
    errors, empty states) → `sota-ux-writing`; marketing/site/email content →
    `sota-copywriting`; technical docs → `sota-docs-workflow`. The component
    patterns the text lives in stay `sota-frontend-design`.
17. **Shell scripts hide everywhere** — CI run blocks, Dockerfile RUN lines,
    Makefiles, entrypoints. Audit them with `sota-shell-scripting` even when
    the repo's "language" is something else.
18. **Cryptography fans out — there is no single crypto skill (by design).**
    Algorithm choice, AEAD/nonce discipline, CSPRNG, in-code key handling, TLS
    client config, constant-time comparison, tamper-evident logs/audit ledgers
    (keyed hash chains, external anchoring, integrity-vs-completeness), crypto
    agility, and post-quantum migration → `sota-code-security` rules/04. The key *material* — storage
    backends (KMS/HSM, Vault, SOPS+age), lifecycle, rotation, per-credential-type
    handling → `sota-secrets-management`. Transport/PKI — TLS server config, cert
    lifecycle/ACME, private CA, mTLS → `sota-network-security` rules/06.
    FIPS-140-3-validated-module requirements → `sota-security-compliance`
    rules/02. Language-specific APIs (JCA, `crypto/*`, .NET) stay in the language
    skill. The stance throughout is **use a vetted library, don't roll your own**.
19. **Which direction does the trust boundary point?** Protecting the *host
    from the workload* (untrusted code, seccomp/microVMs/WASM sandboxes) →
    `sota-sandboxing`. Protecting the *workload from the host/operator* —
    TEEs (SEV-SNP/TDX/CCA/SGX), remote attestation, confidential
    VMs/containers, or computing on encrypted data (FHE/MPC/ZKP) →
    `sota-confidential-computing`. Both can apply to one system. Key
    custody/release stays `sota-secrets-management`; differential privacy and
    de-identification stay `sota-privacy-compliance`.
20. **"It's enabled" is a claim, not a fact.** Whenever a control's *presence*
    is established but its *effect* isn't — a banner, a config flag, a green
    test, "we have a scanner" — route to `sota-code-security` rules/10 (silent
    control failure). It pairs with `sota-testing` rules/06 (mutation-probe the
    control) and rules/09 (a security test must be watched to fail),
    `sota-observability` rules/05 (degradation must be visible), and
    `sota-devsecops` rules/04 (does the shipped artifact contain what the
    control needs at runtime?). Not for controls that are simply *missing* —
    that's the owning domain skill's audit checklist.

## BUILD mode — workflow

1. Identify the domains the feature touches (table above) and the language(s).
2. **Load lean.** Read each relevant skill's `SKILL.md` and, from its index,
   open **only** the rules files that match the work (e.g. a websocket endpoint
   → api-design rules/05, async rules/06, code-security rules/02). Loading
   unrelated rules is not free: a long context of similar-looking guidance
   *measurably reduces* how many rules the model actually applies (transformer
   attention degrades with length and near-duplicate distractors). Lean is
   correctness, not just economy.
3. **Plan first, with the checks in the plan.** Before writing code, list a
   short **requirements checklist for this task** — the top-10 non-negotiables
   of each loaded skill + the **universal build non-negotiables** (operating
   principle 5) that apply to any endpoint/handler. Make each item **concrete
   and checkable** — a specific outcome you can mark done/not-done at step 4
   ("rate-limit login to N/min per IP", not "add rate limiting"; "reject uploads
   over N MB", not "validate uploads"); vague items ("handle errors", "make it
   secure") don't survive to the plan. Named up front and verified at the end,
   constraints are followed far better than when left implicit. Then implement
   against that checklist; apply detailed rules as code demands.
4. **Self-audit gate (do this LAST — do not present code until it passes).**
   Re-read each loaded rules file's **Audit checklist** (every rules file ends
   with one) *and* operating principle 5, and verify your diff satisfies every
   item. For each unmet item, **implement it** or state why it's out of scope —
   silence is not allowed. For every control, safeguard, or check in the diff,
   also ask the **falsification question**: *if this were silently a no-op,
   would anything observable differ?* If nothing would — no log, no metric, no
   test that fails — the control is not done (`sota-code-security` rules/10).
   Doing this *last* is deliberate: a long build context
   makes mid-context rules fade, so a final re-read is what catches the rate
   limiting, transport, tests, and logging a model otherwise silently drops
   (measured: this recovery is the bulk of the library's completeness lift,
   `evals/run-completeness.py`). For a large build, run this as a **separate
   pass over the diff** (a fresh, minimal context beats a long polluted one),
   and push the few truly critical invariants into **deterministic gates** (a
   lint/CI check that fails if an endpoint has no rate limiting or TLS) — don't
   rely on attention for what a test can enforce.

## AUDIT mode — workflow

Process and reporting are governed by `rules/01-audit-methodology.md` — read it
first for any full audit: scoping/rules-of-engagement, the verified tool
matrix and triage discipline, the evidence standard, and the report template.

For a focused audit, load the matching skills and follow their AUDIT sections.
For a **full project audit**, work in passes:

1. **Recon.** Inventory the repo: languages, frameworks, entry points (HTTP
   routes, queues, cron, webhooks), data stores, CI config, Dockerfiles, IaC.
   This determines which skills apply; skip skills with no matching surface.
2. **Threat model first.** `sota-threat-modeling` rules/06 (reconstruction):
   assets, trust boundaries, entry points. Its output prioritizes the rest.
3. **Per-domain passes.** For each applicable skill, follow its AUDIT mode and
   audit checklists. Suggested order: secrets sweep (fast, high yield) →
   code security (incl. rules/09 untrusted-data ingestion) → language-specific
   (incl. shell scripts) → API → database → async/concurrency →
   identity & access → sandboxing/devsecops → kubernetes platform →
   network security → cloud infrastructure → privacy/compliance → architecture
   → testing suite health → performance → observability → detection-engineering
   posture → frontend/a11y → LLM features, data pipelines, mobile, CLI, docs as
   applicable. For an infrastructure/cluster audit the heavy hitters are
   `sota-kubernetes`, `sota-network-security`, `sota-identity-access`,
   `sota-sandboxing`, and `sota-detection-engineering`.
4. **Silent-control pass (always run it).** The per-domain passes ask "is the
   control there?" — this one asks "does it *do* anything?". For every control
   they confirmed exists, apply `sota-code-security` rules/10: swallowed
   enforcement exceptions, presence decided by `exists()` rather than a loaded
   artifact, rulesets that load zero rules, truncation before inspection,
   attacker-triggerable early returns, config keys silently ignored, defaults
   that differ between docs and code, degradation nothing logs, and controls
   whose tests still pass when the body is replaced with a no-op. This class is
   invisible to the other passes — the code isn't wrong, it's inert — and to
   pattern-based SAST for the same reason.
5. **Findings.** Emit every finding in the canonical cross-domain format
   (`file:line | rule | severity | effort | fix`) — skill-local block formats
   are fine within a domain pass but must carry an effort field so the
   roll-up can be sequenced — deduplicate across domains,
   and roll up into the report structure from `rules/01-audit-methodology.md`:
   executive summary → scope & methodology → findings by severity →
   remediation roadmap sequenced by risk-reduction-per-effort → positive
   observations → appendix. Severity meanings:
   - **Critical** — exploitable now or data-loss risk; fix before anything else.
   - **High** — serious weakness or reliability hazard; fix this sprint.
   - **Medium** — deviation from SOTA with real but bounded impact.
   - **Low** — hygiene, polish, future-proofing.
   - **Info** — no direct risk: observations, tech-debt notes, future-proofing.
6. **Refute before reporting.** Re-reading your own finding re-runs the reasoning
   that produced it — it is the weakest check available. Every Critical/High gets
   an **independent pass prompted to kill it** (a separate agent, or a
   fresh-context hostile read), working from the code at the pinned commit rather
   than your write-up, defaulting to REFUTED when the evidence is ambiguous. Use
   distinct lenses where a finding can fail more than one way — is the mechanism
   real, is it reachable, is the stated impact inflated. Survivors ship; the rest
   are dropped or downgraded **with the refutation recorded**, so the next auditor
   doesn't re-raise them. Absence claims ("no X found") get a refuter too, and
   carry the heavier burden of principle 3. Full procedure and failure modes:
   `rules/01-audit-methodology.md` §6.

## Library map (rules files per skill)

- **sota/rules**: 01 audit methodology (process, tool matrix, evidence
  standard, report template — read first for any full audit)
- **sota-architecture/rules**: 01 styles & decisions, 02 domain modeling,
  03 distributed systems & events, 04 resilience, 05 scalability & state,
  06 cloud-native config & delivery, 07 anti-patterns catalog,
  08 NATS JetStream messaging
- **sota-code-security/rules**: 01 input & injection, 02 authentication,
  03 authorization, 04 cryptography, 05 web security, 06 memory & resource
  safety, 07 data exposure, 08 LLM/AI security, 09 untrusted-data ingestion,
  10 silent control failure (controls that look enabled and do nothing)
- **sota-threat-modeling/rules**: 01 methodologies, 02 decomposition,
  03 threat catalogs, 04 risk rating & treatment, 05 outputs &
  operationalization, 06 audit reconstruction
- **sota-secrets-management/rules**: 01 lifecycle & workload identity,
  02 storage backends, 03 application patterns, 04 detection & remediation,
  05 credential types
- **sota-sandboxing/rules**: 01 isolation boundaries, 02 Linux/OS hardening,
  03 containers & microVMs, 04 process/app sandboxing, 05 AI-agent sandboxing
- **sota-performance/rules**: 01 methodology, 02 algorithms & data structures,
  03 memory, 04 I/O & network, 05 caching, 06 frontend/web
- **sota-async-concurrency/rules**: 01 models & structure, 02 correctness,
  03 primitives, 04 event-loop hygiene, 05 cancellation/timeouts/shutdown,
  06 backpressure & flow control, 07 audit bug catalog
- **sota-api-design/rules**: 01 REST/HTTP, 02 versioning & evolution,
  03 GraphQL, 04 gRPC & protocols, 05 realtime/websockets/SSE, 06 webhooks,
  07 security & operations
- **sota-devsecops/rules**: 01 pipeline security, 02 provenance & signing,
  03 dependencies, 04 build & containers, 05 analysis gates,
  06 IaC & deployment, 07 runtime & ops, 08 registry security
- **sota-databases/rules**: 01 choosing & modeling, 02 schema & migrations,
  03 queries & indexes, 04 transactions & concurrency, 05 reliability & scale,
  06 security & compliance, 07 vector & AI, 08 SurrealDB & multi-model
- **sota-frontend-design/rules**: 01 typography & color, 02 layout/spacing/
  responsive, 03 design systems & components, 04 UX patterns,
  05 accessibility, 06 motion design, 07 visual craft & distinctiveness
- **sota-web-frameworks/rules**: 01 baseline (versions/support, render modes),
  02 React 19 (hooks, Actions, React Compiler), 03 Next.js (App Router, Server
  Actions, caching, CVEs), 04 Vue 3 (Composition API, reactivity, XSS),
  05 Nuxt 4 (data fetching, server routes, CVEs), 06 SSR & hydration
  (mismatches, serialization, caching, CSP), 07 framework security & CVEs
- **sota-observability/rules**: 01 structured logging, 02 metrics, 03 tracing,
  04 SLOs & alerting, 05 operational readiness, 06 audit playbook
- **sota-testing/rules**: 01 strategy & shape, 02 test design & quality,
  03 doubles & test data, 04 integration/contract/system, 05 e2e & UI,
  06 property/fuzzing/mutation, 07 suite health & CI, 08 BDD/spec-by-example,
  09 security testing
- **sota-llm-engineering/rules**: 01 evals, 02 prompt & context engineering,
  03 RAG & retrieval, 04 agents & tools, 05 production engineering,
  06 data & lifecycle
- **sota-ml-engineering/rules**: 01 ML systems architecture, 02 data & features
  (leakage/skew), 03 training & experimentation, 04 evaluation & validation,
  05 deployment & serving, 06 monitoring & drift, 07 security & governance
- **sota-cloud-infrastructure/rules**: 01 org/accounts/governance, 02 IAM
  design, 03 networking, 04 compute selection, 05 data & storage,
  06 cost/FinOps, 07 resilience & DR
- **sota-kubernetes/rules**: 01 control plane & etcd, 02 RBAC &
  serviceaccounts, 03 admission & policy, 04 GitOps controllers,
  05 operators/CRDs/webhooks, 06 workloads & tenancy, 07 supply chain & audit
- **sota-identity-access/rules**: 01 federation protocols, 02 IdP operations,
  03 authorization models, 04 lifecycle & provisioning, 05 privileged &
  workload identity, 06 MFA/federation/assurance, 07 Active Directory &
  Kerberos/ADCS hardening
- **sota-network-security/rules**: 01 zero-trust architecture,
  02 segmentation & blast radius, 03 K8s network policy, 04 service mesh &
  mTLS, 05 edge/ingress/egress, 06 DNS/TLS/PKI
- **sota-confidential-computing/rules**: 01 threat model & selection,
  02 TEE technologies, 03 remote attestation, 04 confidential Kubernetes,
  05 PETs & computing on encrypted data
- **sota-detection-engineering/rules**: 01 detection-engineering discipline,
  02 telemetry & SIEM data layer, 03 rule languages & engines, 04 alerting/
  triage/SOC/SOAR, 05 hunting/intel/deception, 06 incident response &
  validation, 07 AD attack detection (Kerberoasting/DCSync/ADCS)
- **sota-data-engineering/rules**: 01 architecture & modeling, 02 pipelines &
  orchestration, 03 streaming & CDC, 04 data quality & contracts, 05 storage &
  performance, 06 operations & governance
- **sota-privacy-compliance/rules**: 01 data inventory & classification,
  02 privacy by design, 03 consent & user rights, 04 regulatory landscape,
  05 audit-ready engineering, 06 incident & breach readiness
- **sota-security-compliance/rules**: 01 control-frameworks-as-code (CSF 2.0
  spine), 02 NIST 800-53/800-171/CMMC/FedRAMP, 03 SSDF secure SDLC, 04 EU Cyber
  Resilience Act, 05 ISA/IEC 62443 (OT/ICS)
- **sota-mobile/rules**: 01 platform & stack, 02 architecture & state,
  03 offline/background/push, 04 security, 05 performance,
  06 release & operations, 07 Swift language (Swift 6 concurrency, ARC, SPM)
- **sota-cli-ux/rules**: 01 commands/flags/config, 02 output & interaction,
  03 behavior & lifecycle, 04 distribution & docs
- **sota-shell-scripting/rules**: 01 safety baseline, 02 robustness &
  correctness, 03 security, 04 CI & operational scripts
- **sota-docs-workflow/rules**: 01 documentation architecture, 02 API
  reference & changelogs, 03 code review & PR workflow, 04 commits/branches/
  releases, 05 spec-driven development
- **sota-ux-writing/rules**: 01 voice/tone & plain language, 02 microcopy &
  components, 03 errors & feedback, 04 accessibility & localization
- **sota-copywriting/rules**: 01 positioning & value proposition,
  02 headlines/landing pages/CTAs, 03 SEO content, 04 claims/legal/trust
- **sota-rust/rules**: 01 ownership & API design, 02 errors & panics,
  03 unsafe discipline, 04 async/tokio, 05 security & supply chain,
  06 performance, 07 tooling & CI
- **sota-golang/rules**: 01 errors, 02 design, 03 concurrency,
  04 HTTP services, 05 security, 06 performance, 07 tooling & CI
- **sota-c-cpp/rules**: 01 idioms (RAII/ownership), 02 memory safety,
  03 undefined behavior, 04 security (CERT/MISRA/hardening), 05 concurrency,
  06 build/tooling & CI, 07 performance
- **sota-jvm/rules**: 01 idioms (Java/Kotlin), 02 API/null/immutability design,
  03 concurrency (virtual threads, JMM, coroutines), 04 security
  (deserialization/injection/XXE/JNDI/crypto), 05 performance (GC/JFR/GraalVM),
  06 build/tooling & CI
- **sota-python/rules**: 01 tooling & project setup, 02 typing & correctness,
  03 idioms & pitfalls, 04 async, 05 security, 06 performance,
  07 frameworks & testing
- **sota-javascript-typescript/rules**: 01 tsconfig & types, 02 language
  idioms, 03 async patterns, 04 Node backend, 05 security, 06 performance,
  07 testing & tooling
- **sota-dotnet/rules**: 01 idioms (records/NRT/patterns), 02 API/disposal/DI
  design, 03 async & concurrency, 04 security (SQL/deserialization/ASP.NET
  Core/crypto), 05 performance (GC/Span/AOT), 06 build/tooling & CI
- **sota-php/rules**: 01 language baseline & idioms, 02 injection (SQL/XSS),
  03 files/deserialization/SSRF, 04 sessions/auth/web hardening, 05 Composer &
  tooling, 06 performance & runtime
- **sota-ruby/rules**: 01 language & idioms, 02 security, 03 web hardening,
  04 supply chain & tooling, 05 concurrency & performance

## Context budget discipline

Each rules file is 200–310 lines. A typical focused task needs 2–5 rules files;
a full audit pass should load one skill at a time, finish its findings, then
move on. If context is tight, prefer the skill's top-10 non-negotiables plus
the single most relevant rules file.
