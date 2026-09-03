# 04 — Library map: which `rules/` file holds what

The per-skill index of every `rules/NN` file in the library, so a routing decision can
name the file to open without loading a `SKILL.md` first.

**This lived in the router until it was offloaded.** It is pure lookup — every entry is a
condensed second copy of the index inside that skill's own `SKILL.md`, which the BUILD
workflow (`rules/02` step 2) tells you to read anyway. Keeping it in the router charged
its tokens to *every* session that loaded the router, including the ones that never
consult it. The router's length was measured as **not** costing routing accuracy (flat at
2.6x the length, `evals/results/2026-08-26/ROUTER-LENGTH.md`), so this is a
tokens-per-load change, not an accuracy one.

Read it when you know the domain but not the file. If you are already opening a skill's
`SKILL.md`, prefer that skill's own index — it carries "read this when…" guidance this
map deliberately drops.

**Both directions are gated.** Invariant 7 requires every skill to appear here; invariant
15 requires every `rules/NN` file that exists to be listed, and every listed file to
exist. `sota-code-security/rules/11` sat unlisted for two releases before 15 existed.

## Library map (rules files per skill)

- **sota/rules**: 01 audit methodology (scoping, tool matrix, triage, hygiene), 02 build workflow
  (the four BUILD steps, and the four surfaces a BUILD change must be mirrored into), 03 audit
  findings (severity & chain closure, evidence, decision ledger, refutation, report template),
  04 library map (this file — which `rules/NN` holds what, across every skill)
- **sota-architecture/rules**: 01 styles & decisions, 02 domain modeling, 03 distributed systems &
  events, 04 resilience, 05 scalability & state, 06 cloud-native config & delivery, 07 anti-
  patterns catalog, 08 NATS JetStream messaging
- **sota-code-security/rules**: 01 input & injection, 02 authentication, 03 authorization, 04
  cryptography, 05 web security, 06 memory & resource safety, 07 data exposure, 08 LLM/AI
  security, 09 untrusted-data ingestion, 10 silent control failure, 11 dead-path diagnostics, 12
  verifying the verifier, 13 context-dependent silence, 14 the control that is not in force
- **sota-threat-modeling/rules**: 01 methodologies, 02 decomposition, 03 threat catalogs, 04 risk
  rating & treatment, 05 outputs & operationalization, 06 audit reconstruction
- **sota-secrets-management/rules**: 01 lifecycle & workload identity, 02 storage backends, 03
  application patterns, 04 detection & remediation, 05 credential types
- **sota-sandboxing/rules**: 01 isolation boundaries, 02 Linux/OS hardening, 03 containers &
  microVMs, 04 process/app sandboxing, 05 AI-agent sandboxing
- **sota-performance/rules**: 01 methodology, 02 algorithms & data structures, 03 memory, 04 I/O &
  network, 05 caching, 06 frontend/web
- **sota-async-concurrency/rules**: 01 models & structure, 02 correctness, 03 primitives, 04
  event-loop hygiene, 05 cancellation/timeouts/shutdown, 06 backpressure & flow control, 07 audit
  bug catalog
- **sota-api-design/rules**: 01 REST/HTTP, 02 versioning & evolution, 03 GraphQL, 04 gRPC &
  protocols, 05 realtime/websockets/SSE, 06 webhooks, 07 security & operations
- **sota-devsecops/rules**: 01 pipeline security, 02 provenance & signing, 03 dependencies (incl.
  §3.9 declared-but-not-reached), 04 build & containers, 05 analysis gates, 06 IaC & deployment,
  07 runtime & ops, 08 registry security
- **sota-databases/rules**: 01 choosing & modeling, 02 schema & migrations, 03 queries & indexes,
  04 transactions & concurrency, 05 reliability & scale, 06 security & compliance, 07 vector & AI,
  08 SurrealDB & multi-model
- **sota-frontend-design/rules**: 01 typography & color, 02 layout/spacing/ responsive, 03 design
  systems & components, 04 UX patterns, 05 accessibility, 06 motion design, 07 visual craft &
  distinctiveness
- **sota-web-frameworks/rules**: 01 baseline (versions/support, render modes), 02 React 19 (hooks,
  Actions, React Compiler), 03 Next.js (App Router, Server Actions, caching, CVEs), 04 Vue 3
  (Composition API, reactivity, XSS), 05 Nuxt 4 (data fetching, server routes, CVEs), 06 SSR &
  hydration (mismatches, serialization, caching, CSP), 07 framework security & CVEs
- **sota-observability/rules**: 01 structured logging, 02 metrics, 03 tracing, 04 SLOs & alerting,
  05 operational readiness, 06 audit playbook
- **sota-testing/rules**: 01 strategy & shape, 02 test design & quality, 03 doubles & test data,
  04 integration/contract/system, 05 e2e & UI, 06 property/fuzzing/mutation, 07 suite health & CI,
  08 BDD/spec-by-example, 09 security testing
- **sota-llm-engineering/rules**: 01 evals, 02 prompt & context engineering, 03 RAG & retrieval,
  04 agents & tools, 05 production engineering, 06 data & lifecycle
- **sota-ml-engineering/rules**: 01 ML systems architecture, 02 data & features (leakage/skew), 03
  training & experimentation, 04 evaluation & validation, 05 deployment & serving, 06 monitoring &
  drift, 07 security & governance
- **sota-cloud-infrastructure/rules**: 01 org/accounts/governance, 02 IAM design, 03 networking,
  04 compute selection, 05 data & storage, 06 cost/FinOps, 07 resilience & DR
- **sota-kubernetes/rules**: 01 control plane & etcd, 02 RBAC & serviceaccounts, 03 admission &
  policy, 04 GitOps controllers, 05 operators/CRDs/webhooks, 06 workloads & tenancy, 07 supply
  chain & audit
- **sota-identity-access/rules**: 01 federation protocols, 02 IdP operations, 03 authorization
  models, 04 lifecycle & provisioning, 05 privileged & workload identity, 06
  MFA/federation/assurance, 07 Active Directory & Kerberos/ADCS hardening
- **sota-network-security/rules**: 01 zero-trust architecture, 02 segmentation & blast radius, 03
  K8s network policy, 04 service mesh & mTLS, 05 edge/ingress/egress, 06 DNS/TLS/PKI
- **sota-confidential-computing/rules**: 01 threat model & selection, 02 TEE technologies, 03
  remote attestation, 04 confidential Kubernetes, 05 PETs & computing on encrypted data
- **sota-detection-engineering/rules**: 01 detection-engineering discipline, 02 telemetry & SIEM
  data layer, 03 rule languages & engines, 04 alerting/ triage/SOC/SOAR, 05
  hunting/intel/deception, 06 incident response & validation, 07 AD attack detection
  (Kerberoasting/DCSync/ADCS)
- **sota-data-engineering/rules**: 01 architecture & modeling, 02 pipelines & orchestration, 03
  streaming & CDC, 04 data quality & contracts, 05 storage & performance, 06 operations &
  governance
- **sota-privacy-compliance/rules**: 01 data inventory & classification, 02 privacy by design, 03
  consent & user rights, 04 regulatory landscape, 05 audit-ready engineering, 06 incident & breach
  readiness
- **sota-security-compliance/rules**: 01 control-frameworks-as-code (CSF 2.0 spine), 02 NIST
  800-53/800-171/CMMC/FedRAMP, 03 SSDF secure SDLC, 04 EU Cyber Resilience Act, 05 ISA/IEC 62443
  (OT/ICS)
- **sota-mobile/rules**: 01 platform & stack, 02 architecture & state, 03 offline/background/push,
  04 security, 05 performance, 06 release & operations, 07 Swift language (Swift 6 concurrency,
  ARC, SPM)
- **sota-cli-ux/rules**: 01 commands/flags/config, 02 output & interaction, 03 behavior &
  lifecycle, 04 distribution & docs
- **sota-shell-scripting/rules**: 01 safety baseline, 02 robustness & correctness, 03 security, 04
  CI & operational scripts
- **sota-docs-workflow/rules**: 01 documentation architecture, 02 API reference & changelogs, 03
  code review & PR workflow, 04 commits/branches/ releases, 05 spec-driven development
- **sota-ux-writing/rules**: 01 voice/tone & plain language, 02 microcopy & components, 03 errors
  & feedback, 04 accessibility & localization
- **sota-copywriting/rules**: 01 positioning & value proposition, 02 headlines/landing pages/CTAs,
  03 SEO content, 04 claims/legal/trust
- **sota-rust/rules**: 01 ownership & API design, 02 errors & panics, 03 unsafe discipline, 04
  async/tokio, 05 security & supply chain, 06 performance, 07 tooling & CI
- **sota-golang/rules**: 01 errors, 02 design, 03 concurrency, 04 HTTP services, 05 security, 06
  performance, 07 tooling & CI
- **sota-c-cpp/rules**: 01 idioms (RAII/ownership), 02 memory safety, 03 undefined behavior, 04
  security (CERT/MISRA/hardening), 05 concurrency, 06 build/tooling & CI, 07 performance
- **sota-jvm/rules**: 01 idioms (Java/Kotlin), 02 API/null/immutability design, 03 concurrency
  (virtual threads, JMM, coroutines), 04 security (deserialization/injection/XXE/JNDI/crypto), 05
  performance (GC/JFR/GraalVM), 06 build/tooling & CI
- **sota-python/rules**: 01 tooling & project setup, 02 typing & correctness, 03 idioms &
  pitfalls, 04 async, 05 security, 06 performance, 07 frameworks & testing
- **sota-javascript-typescript/rules**: 01 tsconfig & types, 02 language idioms, 03 async
  patterns, 04 Node backend, 05 security, 06 performance, 07 testing & tooling
- **sota-dotnet/rules**: 01 idioms (records/NRT/patterns), 02 API/disposal/DI design, 03 async &
  concurrency, 04 security (SQL/deserialization/ASP.NET Core/crypto), 05 performance
  (GC/Span/AOT), 06 build/tooling & CI
- **sota-php/rules**: 01 language baseline & idioms, 02 injection (SQL/XSS), 03
  files/deserialization/SSRF, 04 sessions/auth/web hardening, 05 Composer & tooling, 06
  performance & runtime
- **sota-ruby/rules**: 01 language & idioms, 02 security, 03 web hardening, 04 supply chain &
  tooling, 05 concurrency & performance

## Audit checklist

- [ ] Does every `skills/sota-*/rules/NN-*.md` in the tree appear in the map above, and
      does every number in the map name a file that exists (invariant 15 checks both
      directions — a missing entry is invisible to a router-driven load, and a stale one
      sends the model after nothing)?
- [ ] Does every domain skill have a `**<skill>/rules**` entry (invariant 7)?
- [ ] When a `rules/NN` file is added, split or renumbered, was this map updated in the
      **same commit** — and the owning `SKILL.md` index too (invariant 10)?
- [ ] Is this file still only a lookup table? Guidance that belongs at the point of use
      has drifted here if an entry has grown a rule rather than a title.
