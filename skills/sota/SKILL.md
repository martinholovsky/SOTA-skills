---
name: sota
description: >-
  Master router for the SOTA engineering skills library. Use this skill whenever the user asks to build, design, implement, refactor, harden, optimize, review, or audit an application, service, or codebase and the request spans more than one domain — or when you are unsure which specific sota-* skill applies. It maps the task (build mode or audit mode) to the right domain skills (architecture, code security, threat modeling, secrets, sandboxing, performance, async/concurrency, APIs/websockets, devsecops, databases, frontend, observability, testing, LLM engineering, cloud infrastructure, kubernetes, identity & access, network security, detection engineering, data engineering, privacy/compliance, mobile, CLI UX, shell scripting, docs/workflow) and language skills (Rust, Go, C/C++, Java/Kotlin, Python, JavaScript/TypeScript), and defines how to run a full multi-domain audit. Trigger keywords: SOTA, best practices, audit my code, security review, full review, hardening, production readiness, code quality.
---

# SOTA Engineering Skills — Master Router

A library of 29 domain skills, each with a `SKILL.md` entry point and a `rules/`
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
   internet-facing; Medium if internal-only").
4. **Stack profile.** If the repo or `~/.claude` contains a `profiles/*.md`
   stack profile (preferred stores, auth provider, license policy, platform
   conventions), its choices are the defaults for BUILD mode and the expected
   baseline for AUDIT mode.

## Routing table

| Skill | Use when the task involves... |
|---|---|
| `sota-architecture` | System design, service boundaries, monolith vs microservices, DDD, event-driven design, sagas/outbox, resilience (timeouts/retries/circuit breakers), scalability, multi-tenancy, 12-factor/cloud-native, architectural anti-patterns |
| `sota-code-security` | Writing or reviewing code that touches untrusted input, authn/authz, sessions/JWT/OAuth, crypto, XSS/CSRF/CORS, file uploads, deserialization, error/log hygiene, LLM/agent app security |
| `sota-threat-modeling` | Designing a new system/feature with security in mind, drawing trust boundaries and DFDs, STRIDE/LINDDUN, risk rating, reconstructing a threat model from an existing codebase |
| `sota-secrets-management` | API keys, passwords, tokens, signing/TLS/SSH keys, .env files, Vault/cloud secret managers, workload identity (OIDC), secret rotation, leak detection and remediation |
| `sota-sandboxing` | Isolation of untrusted code or input, least privilege, seccomp/Landlock/capabilities, container/K8s hardening, microVMs, WASM sandboxes, subprocess hygiene, sandboxing AI-agent code execution |
| `sota-performance` | Latency, throughput, profiling, memory usage, caching (incl. stampede protection), I/O and network efficiency, Core Web Vitals, performance regression in CI |
| `sota-async-concurrency` | async/await, threads, goroutines, channels, races, deadlocks, event-loop blocking, cancellation/timeouts, graceful shutdown, backpressure, bounded queues |
| `sota-api-design` | REST/HTTP semantics, pagination, idempotency, versioning/deprecation, GraphQL, gRPC/proto evolution, websockets/SSE/realtime, webhooks, API rate limiting and tenant isolation |
| `sota-devsecops` | CI/CD pipelines, GitHub Actions hardening, supply chain (SLSA, Sigstore, SBOM, dependency confusion), container builds, SAST/secret-scanning gates, Terraform/GitOps, admission control |
| `sota-databases` | Schema design, Postgres/NoSQL choice, migrations (zero-downtime), indexes/EXPLAIN, transactions/isolation, connection pooling, replication/backups, Redis, RLS/DB security, pgvector |
| `sota-frontend-design` | UI/UX, visual design, typography/color/layout, design systems and tokens, components, forms, accessibility (WCAG 2.2), motion/animation design, modern CSS, responsive design |
| `sota-observability` | Logging, metrics, tracing (OpenTelemetry), SLOs/error budgets, alerting, health checks, dashboards, debugging production, "can we answer why is this slow?" |
| `sota-testing` | Test strategy (pyramid/trophy), unit vs integration boundaries, test design/smells, mocks/fakes/test data, contract testing, e2e, property-based/fuzzing/mutation testing, flaky tests, coverage policy |
| `sota-llm-engineering` | Building LLM features — evals, prompt/context engineering, structured output, RAG, agents/tool design, MCP, model selection/routing, latency/cost engineering, LLM observability |
| `sota-cloud-infrastructure` | Cloud accounts/landing zones, cloud IAM, VPC/subnet/DNS/CDN setup, compute selection (serverless vs containers vs K8s), object storage, FinOps/cost, RTO/RPO and disaster recovery |
| `sota-kubernetes` | Kubernetes platform security & ops — RBAC & escalation paths, admission control (PSA/Kyverno/Gatekeeper/VAP, Audit→Enforce), GitOps controllers (Argo CD/Flux, AppProject scoping), operators/CRDs/webhooks, control plane & etcd encryption, Helm supply chain, multi-tenancy, cluster lifecycle, K8s audit logging; self-hosted (Talos/k3s) and managed |
| `sota-identity-access` | Identity infrastructure & access management — OIDC/OAuth2.1/SAML/SCIM protocols, running an IdP (Kanidm/Keycloak/etc.), RBAC/ABAC/ReBAC authorization design, group→role mapping, joiner-mover-leaver lifecycle, deprovisioning, privileged access & break-glass, SPIFFE/workload identity, phishing-resistant MFA/passkeys, federation risk |
| `sota-network-security` | Network security as a discipline — zero-trust (NIST 800-207), segmentation & blast-radius, the `world`/`any` over-broad-rule trap, Kubernetes NetworkPolicy depth (Cilium L7, default-deny egress), service mesh & mTLS / internal encryption, edge/ingress/WAF, egress control & metadata-endpoint blocking, DNS/TLS/PKI & cert lifecycle |
| `sota-detection-engineering` | Detective controls, SOC & IR — detection-as-code, Sigma/YARA/Suricata/Falco/Tetragon rules, ATT&CK coverage, SIEM & telemetry coverage, alert tuning/SOAR, threat hunting & intel (STIX/TAXII), deception/honeytokens, incident response (NIST 800-61), detection validation (Atomic Red Team/Caldera) |
| `sota-data-engineering` | Data pipelines, ELT/orchestration, dbt, Kafka/streaming, CDC, schema registry, lakehouse (Iceberg/Delta/Parquet), data quality/contracts, warehouse modeling |
| `sota-privacy-compliance` | PII inventory/classification, privacy by design, consent, DSAR/deletion architecture, retention, GDPR/CCPA/HIPAA/PCI/AI Act engineering obligations, SOC 2/ISO 27001 audit readiness, breach response |
| `sota-mobile` | iOS/Android/cross-platform apps — stack choice, offline-first/sync, push, mobile security (Keychain/Keystore, attestation), performance budgets, store requirements, staged rollouts |
| `sota-cli-ux` | CLI/developer-tool design — flags/subcommands, config precedence, stdout/stderr and --json contracts, exit codes, TTY detection, signals, completions, distribution |
| `sota-shell-scripting` | Bash/sh scripts, CI run blocks, entrypoints, Makefiles — safety baseline (quoting, set -euo pipefail, traps), injection, secrets in scripts, shellcheck/shfmt |
| `sota-docs-workflow` | Documentation (Diátaxis, READMEs, runbooks, API docs, changelogs, AGENTS.md), code review/PR workflow, commit/branch/release discipline |
| `sota-rust` | Any Rust code — ownership/API design, error handling, unsafe discipline, tokio/async, supply chain (cargo audit/deny/vet), performance, clippy/CI |
| `sota-golang` | Any Go code — errors, package/interface design, goroutines/channels/leaks, net/http hardening, security (os/exec, os.Root, govulncheck), pprof/performance, golangci-lint/CI |
| `sota-c-cpp` | Any C/C++ code — RAII/idioms, memory safety (UAF/overflow/sanitizers), undefined behavior, security (CERT/MISRA, banned APIs, OpenSSF hardening flags), concurrency/atomics, CMake/clang-tidy/fuzzing CI, performance |
| `sota-jvm` | Any Java/Kotlin code — modern idioms (records/sealed/pattern-matching, Kotlin null-safety/coroutines), API/null/immutability design, concurrency (virtual threads, JMM, j.u.c, coroutines), security (deserialization/JNDI/XXE/injection, JCA crypto), GC/JFR/GraalVM performance, Maven/Gradle supply-chain & CI |
| `sota-python` | Any Python code — uv/ruff/typing setup, idioms/pitfalls, asyncio, security (pickle/subprocess/SQL), performance, FastAPI/Django/pytest |
| `sota-javascript-typescript` | Any JS/TS code — strict tsconfig/type design, idioms, promises/AbortController, Node backend hardening, XSS/supply-chain security, bundle/React performance, vitest/ESLint |

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
   `sota-javascript-typescript` for the code; `sota-performance` rules/06 for
   Web Vitals.
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
13. **Identity is its own layer.** App-level login/session/JWT-validation code →
   `sota-code-security` rules/02-03; identity *infrastructure* (IdP, OIDC/SAML
   config, RBAC/role-mapping design, provisioning, break-glass, SPIFFE) →
   `sota-identity-access`; the credentials themselves → `sota-secrets-management`.
14. **Network: setup vs security.** Cloud VPC/DNS/CDN provisioning →
   `sota-cloud-infrastructure` rules/03; segmentation, zero-trust, NetworkPolicy
   depth, service mesh/mTLS, egress/DNS/PKI posture → `sota-network-security`.
15. **Prevention vs detection.** Building the control → the relevant domain
   skill; verifying you'd *catch* the attack at runtime (logs, rules, hunting,
   IR) → `sota-detection-engineering`. Ops telemetry plumbing stays in
   `sota-observability`; design-time threat enumeration in `sota-threat-modeling`.
16. **Ingesting untrusted/attacker-authored data** (feeds, scraping, uploads,
   webhooks, RAG corpora, hostile parsers) → `sota-code-security` rules/09,
   with `sota-sandboxing` rules/04 for parser isolation.
10. **Data: OLTP vs analytics.** App databases → `sota-databases`; pipelines,
    streaming, warehouse/lakehouse → `sota-data-engineering`; anything touching
    personal data → add `sota-privacy-compliance`.
11. **Any handling of user/personal data** (new fields, exports, logs,
    analytics, ML training) → check `sota-privacy-compliance` minimization and
    retention rules, even when the task isn't "about" privacy.
12. **Shell scripts hide everywhere** — CI run blocks, Dockerfile RUN lines,
    Makefiles, entrypoints. Audit them with `sota-shell-scripting` even when
    the repo's "language" is something else.

## BUILD mode — workflow

1. Identify the domains the feature touches (table above) and the language(s).
2. Read each relevant skill's `SKILL.md`; from its index, open only the rules
   files matching the work (e.g. adding a websocket endpoint → api-design
   rules/05, async rules/06, code-security rules/02 for auth at upgrade).
3. Apply the **top-10 non-negotiables** of every loaded skill unconditionally;
   apply detailed rules as the code demands.
4. Before finishing, run each loaded rules file's **Audit checklist** against
   your own diff — every rules file ends with one.

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
4. **Findings.** Emit every finding in the canonical format
   (`file:line | rule | severity | effort | fix`), deduplicate across domains,
   and roll up into the report structure from `rules/01-audit-methodology.md`:
   executive summary → scope & methodology → findings by severity →
   remediation roadmap sequenced by risk-reduction-per-effort → positive
   observations → appendix. Severity meanings:
   - **Critical** — exploitable now or data-loss risk; fix before anything else.
   - **High** — serious weakness or reliability hazard; fix this sprint.
   - **Medium** — deviation from SOTA with real but bounded impact.
   - **Low** — hygiene, polish, future-proofing.
   - **Info** — no direct risk: observations, tech-debt notes, future-proofing.
5. **Verify before reporting.** Re-read each Critical/High finding's code in
   full context; drop or downgrade anything you cannot substantiate with a
   concrete failure scenario, or mark it "needs verification".

## Library map (rules files per skill)

- **sota/rules**: 01 audit methodology (process, tool matrix, evidence
  standard, report template — read first for any full audit)
- **sota-architecture/rules**: 01 styles & decisions, 02 domain modeling,
  03 distributed systems & events, 04 resilience, 05 scalability & state,
  06 cloud-native config & delivery, 07 anti-patterns catalog,
  08 NATS JetStream messaging
- **sota-code-security/rules**: 01 input & injection, 02 authentication,
  03 authorization, 04 cryptography, 05 web security, 06 memory & resource
  safety, 07 data exposure, 08 LLM/AI security, 09 untrusted-data ingestion
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
- **sota-observability/rules**: 01 structured logging, 02 metrics, 03 tracing,
  04 SLOs & alerting, 05 operational readiness, 06 audit playbook
- **sota-testing/rules**: 01 strategy & shape, 02 test design & quality,
  03 doubles & test data, 04 integration/contract/system, 05 e2e & UI,
  06 property/fuzzing/mutation, 07 suite health & CI
- **sota-llm-engineering/rules**: 01 evals, 02 prompt & context engineering,
  03 RAG & retrieval, 04 agents & tools, 05 production engineering,
  06 data & lifecycle
- **sota-cloud-infrastructure/rules**: 01 org/accounts/governance, 02 IAM
  design, 03 networking, 04 compute selection, 05 data & storage,
  06 cost/FinOps, 07 resilience & DR
- **sota-kubernetes/rules**: 01 control plane & etcd, 02 RBAC &
  serviceaccounts, 03 admission & policy, 04 GitOps controllers,
  05 operators/CRDs/webhooks, 06 workloads & tenancy, 07 supply chain & audit
- **sota-identity-access/rules**: 01 federation protocols, 02 IdP operations,
  03 authorization models, 04 lifecycle & provisioning, 05 privileged &
  workload identity, 06 MFA/federation/assurance
- **sota-network-security/rules**: 01 zero-trust architecture,
  02 segmentation & blast radius, 03 K8s network policy, 04 service mesh &
  mTLS, 05 edge/ingress/egress, 06 DNS/TLS/PKI
- **sota-detection-engineering/rules**: 01 detection-engineering discipline,
  02 telemetry & SIEM data layer, 03 rule languages & engines, 04 alerting/
  triage/SOC/SOAR, 05 hunting/intel/deception, 06 incident response &
  validation
- **sota-data-engineering/rules**: 01 architecture & modeling, 02 pipelines &
  orchestration, 03 streaming & CDC, 04 data quality & contracts, 05 storage &
  performance, 06 operations & governance
- **sota-privacy-compliance/rules**: 01 data inventory & classification,
  02 privacy by design, 03 consent & user rights, 04 regulatory landscape,
  05 audit-ready engineering, 06 incident & breach readiness
- **sota-mobile/rules**: 01 platform & stack, 02 architecture & state,
  03 offline/background/push, 04 security, 05 performance,
  06 release & operations
- **sota-cli-ux/rules**: 01 commands/flags/config, 02 output & interaction,
  03 behavior & lifecycle, 04 distribution & docs
- **sota-shell-scripting/rules**: 01 safety baseline, 02 robustness &
  correctness, 03 security, 04 CI & operational scripts
- **sota-docs-workflow/rules**: 01 documentation architecture, 02 API
  reference & changelogs, 03 code review & PR workflow, 04 commits/branches/
  releases
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

## Context budget discipline

Each rules file is 200–310 lines. A typical focused task needs 2–5 rules files;
a full audit pass should load one skill at a time, finish its findings, then
move on. If context is tight, prefer the skill's top-10 non-negotiables plus
the single most relevant rules file.
