# Changelog

All notable changes to SOTA-skills are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Eval golden sets + efficacy baseline + clean isolated control** (roadmap
  Next, done). Cases expanded to 20 routing + 13 audit + 7 harder audit
  (`evals/cases/`). New `evals/run-clean.py` — a **raw model-API** harness
  (OpenRouter, key from `.env`, never committed) that removes the in-session
  contamination entirely (no HOME/`CLAUDE.md`/skill-registry) for a true
  library-vs-nothing control. Findings (all in
  `evals/results/2026-07-10/BASELINE.md`, raw in `results/2026-07-11/`):
  **routing recall lift replicates ~+0.10 in the clean control** — +0.09
  (sonnet-4.6), +0.14 (sonnet-5), +0.09 (opus-4.8), with-library 1.00 each;
  even opus-4.8 misses the same rule-driven skills without the router (r01
  testing, r02 sandboxing, r07 code-security, r09 web-frameworks). So the
  in-session +0.08/+0.11 was **not** a contamination artifact — the routing
  lift is real and attributable to the cross-cutting rules. README now cites
  the freshness evidence ("Measured, not asserted") linking `evals/`. **Audit
  lift = +0.00, model-independent** (haiku→sonnet-4.6, original + harder cases):
  strong models recognize textbook vulns library-or-not. **Freshness lift =
  +0.75 (sonnet-4.6) / +0.50 (opus-4.8)** — the decisive finding: a new
  `cases/freshness.jsonl` (8 objective 2026-current facts, each carried in a
  rules file) shows the base model is not just missing current facts but
  **confidently wrong** (asserts RFC 7489 not 9989, OWASP A04 not A06,
  ingress-nginx "maintained", NIST "8 chars" not 15, TorchServe "maintained"),
  while the with-library arm is 1.00. So the library's value is currency (large
  lift, ~5–7× routing), not routing/recognition (small/zero). Also: `.env`
  added to `.gitignore` (was untracked but unignored).

## [1.13.0] - 2026-07-10

### Added

- **Content-accuracy runbook + eval harness** (2026-07-10 audit STRAT-HIGH-1/2,
  the two top strategic gaps). `docs/MAINTENANCE.md` documents the reproducible
  per-skill re-verification sweep (extract rot-prone claims → verify vs primary
  sources → fix under the no-pins/EOL policies → adversarial re-verify → bump
  `LAST-VERIFIED`) that previously lived only in maintainer memory, and states
  honestly which dimensions are CI-automated vs human/agent discipline. The
  freshness re-verify window is cut **12 → 6 months** (content drifts far
  faster; 6mo stays clearable). New `evals/` prototype: a runnable
  efficacy-regression harness — golden-set cases (`cases/router.jsonl`,
  `cases/audit.jsonl`) + `score.py` (recall/precision vs an agent's
  predictions, exit 1 on any miss). Deliberately not in CI (an LLM eval is
  non-deterministic); it gives a repeatable with-vs-without baseline. Harness
  verified end-to-end this session (perfect predictions → exit 0, misses →
  exit 1); AGENTS.md/CONTRIBUTING.md link the runbook.
- **Invariant 7 — router completeness** (`check-invariants.sh`): every domain
  skill must appear in the router's routing table AND library map; every map
  entry must name a real skill. Automates the drift class the 2026-07-10 audit
  found (the 41st skill was missing from the map for a full release).
  Documented in AGENTS.md/CONTRIBUTING.md.

### Changed

- **Roadmap re-cut around the 2026-07-10 audit** (`docs/ROADMAP.md`): the
  2026-07-01 cycle (fully executed) demoted to history; a fresh Now/Next/Later
  reflects the audit — Now (prove/protect accuracy) closed this cycle, Next
  (grow evals + first 6-month sweep), Later (distribution over coverage,
  STRAT-MED-1). Fixed two STALE bookkeeping items the audit flagged: the
  2026-07-08 sweep is a "34-skill" pass (not "full-library" — it covered 34 of
  40 skills), and the low-severity-triage tally no longer implies 58+32=75
  (the ~75 candidate findings split across files into more line-items).
- **Invariant-gate hardening** (2026-07-10 audit): check 2 now tracks code-fence
  state so a `## Audit checklist` inside a fence no longer satisfies the
  "ends-with" rule (the 2026-07-01 fix was incomplete; verified identical
  verdicts on all current files); check 5's semver guard is a strict
  `X.Y.Z` regex that rejects interior malformations (`1..2`, `1.2`, `1.2.3.4`);
  and CI now fails loudly if `SOTA_DENYLIST` is empty on a trusted (push-to-main
  or same-repo-PR) run instead of silently degrading check 3 to generic-only
  (S-MED-1). Each change adversarially tested to confirm it catches the
  violation.

### Fixed

- **Installer script defects** (2026-07-10 audit): `install.sh` no longer
  aborts (`set -e`, exit 1) when the user declines a routing prompt — routing
  setup is best-effort and now always returns success, so pre-commit setup and
  the final instructions still run (Q-MED-4, reproduced fixed: exit 0, reaches
  the end); `install.sh` profile-linking no longer silently clobbers a real
  file in `~/.claude/profiles` — it backs up + asks first, matching
  `setup_claude_md`'s contract, and keeps the file untouched non-interactively
  (Q-MED-5, reproduced: user content preserved); and `init-gates.sh` writes
  `.pre-commit-config.yaml` as 644 instead of the `mktemp` 600 (Q-LOW).
- **Audit 2026-07-10 content corrections** (all primary-source verified):
  OWASP Top 10 2025 mislabel — Insecure Design is **A06**, not A04
  (`sota-code-security` rules/09); JSON Merge Patch citation **RFC 7386 →
  7396** (obsoleted 2014, `sota-api-design` rules/01); ingress-nginx wording —
  the 2026 CVE wave **was** patched in the final releases (≥1.13.9/1.14.5/
  1.15.1), the standing risk is post-EOL CVEs (`sota-kubernetes` rules/01);
  Iceberg v3 "GA across major engines" overstated → GA on Snowflake/Databricks/
  Spark, Trino still lagging (`sota-data-engineering` rules/01); a
  `grep -v "--"` end-of-options bug in an audit checklist
  (`sota-javascript-typescript` rules/07); a dangling retired-convention
  "last-verified" reference (`sota-confidential-computing` rules/04); and
  ~7 rot-prone version pins reworded to the no-pins policy (Rust 1.96→"recent
  stable", golangci-lint, Swift, Flutter, PHP, Ruby, Vue/Nuxt patch→minor).
- **Router library map** (`skills/sota/SKILL.md`) — added the missing
  `sota-confidential-computing` bullet (41st skill) and refreshed the stale
  `sota-testing` (→09) and `sota-docs-workflow` (→05) bullets. Routing table
  and per-skill indexes were already correct; only the map overview drifted.

### Added

- **`docs/AUDIT-2026-07-10.md`** — second adversarial repository audit (13
  fan-out auditors across 4 lenses + refutation pass, at v1.12.1). Verdict:
  **strong health** — all 6 invariants pass, supply-chain pins genuine, ~150
  rot-prone content claims sampled and primary-source-verified with only a
  handful of small errors, no dangerous advice. Headline findings are
  strategic: no automated content-accuracy gate, no eval harness, coverage
  expansion exhausted vs near-zero adoption. Plus a tail of low-severity
  content/script defects (OWASP A04→A06 mislabel, RFC 7386→7396, ingress-nginx
  "unpatched" wording, router library-map omission of the 41st skill,
  `check-invariants` check-2 fence bypass, two `install.sh` interactive-path
  bugs, ~8 residual version-pins). 11/11 non-trivial findings survived
  adversarial verification; 0 refuted.

## [1.12.1] - 2026-07-10

### Added

- **`sota-network-security` rules/06 — email authentication & anti-spoofing**
  (R12–R14): the library had no coverage of SPF/DKIM/DMARC beyond incidental
  mentions — a real gap given domain spoofing (BEC/phishing) and deliverability.
  Adds SPF (RFC 7208, `-all`, 10-lookup limit), DKIM (RFC 6376, >=2048-bit +
  rotation), **DMARC** (RFC 9989 — the 2026 Proposed Standard obsoleting the
  original RFC 7489; reporting RFC 9990/9991) with the `p=none→quarantine→reject`
  progression and alignment as the actual anti-spoofing control, MTA-STS
  (RFC 8461) + TLS-RPT (RFC 8460) + DANE-for-SMTP (RFC 7672), parked/non-sending
  domain lockdown, ARC (RFC 8617), and the Gmail/Yahoo bulk-sender requirements
  (5,000+/day: SPF+DKIM+aligned DMARC, RFC 8058 one-click unsubscribe, spam
  <0.3%). BIMI noted accurately as an IETF draft (not an RFC), VMC optional.
  Three audit-checklist items + SKILL/router routing updates. Cross-refs
  sota-copywriting rules/04 (marketing-mail content law) and
  sota-detection-engineering (DMARC RUA as a spoofing feed). Every claim
  primary-sourced (RFC editor/IETF datatracker + the Gmail/Yahoo sender rules).
- **`sota-network-security` rules/05 — self-hosted / bare-metal DDoS
  hardening** (R8.1): the one gap in the library's DDoS coverage. Existing
  guidance assumed a scrubbing edge (Cloudflare/Shield/Cloud Armor); this
  adds the L3/4 kernel layer for edges with no provider in front — TCP SYN
  cookies + nftables synproxy (prereqs per the nftables wiki), conntrack-table
  exhaustion sizing/alerting, reverse-path filtering (RFC 3704), and
  not-being-an-amplifier hygiene (BCP 38 / RFC 2827 — no open DNS/NTP/
  memcached/SSDP/chargen reflectors). R8 reframed to name edge scrubbing
  generically (Anycast/provider tiers), with cross-refs to
  sota-cloud-infrastructure rules/03 §10. Two audit-checklist items + SKILL
  index/scope/trigger updates. All claims primary-sourced (nftables wiki,
  kernel.org ip-sysctl, RFC 2827/3704).

## [1.12.0] - 2026-07-09

### Added

- **`sota-confidential-computing`** — confidential computing and cryptographic
  PETs (41 skills total): protecting workloads and data in use from the
  infrastructure they run on — the explicit inverse of `sota-sandboxing`
  (router cross-cutting rule 19 encodes the boundary). SKILL.md + 5 rules:
  01 threat model & selection (CCC definition test — memory encryption alone
  is not CC; five-rung escalation ladder; adversary→mechanism table),
  02 TEE technologies (SEV→SEV-ES→SEV-SNP insufficiency ladder, TDX on
  TME/TME-MK, ARM CCA status incl. Azure Cobalt 200, SGX/LibOS reality,
  Nitro Enclaves' distinct trust model, NVIDIA confidential GPUs,
  side-channel posture), 03 remote attestation (RATS RFC 9334 roles,
  attest-then-release, evidence hard rules, hosted vs self-hosted verifiers,
  TCB recovery, RA-TLS/IETF SEAT), 04 confidential Kubernetes (nodes vs pods,
  CoCo/Kata/Trustee KBS, AKS preview retirement caveat, operational reality),
  05 PETs/COED (FHE families + ISO/IEC 28033 + NIST PEC, MPC/threshold, ZKP
  circuit risk, PSI/OPRF, TEE-vs-PET-vs-DP selection). Built by 5 parallel
  research agents + 2 adversarial verifiers; 54 claims re-verified, 8
  corrected against primary sources (CCC, AMD/Intel/Arm docs, RFC editor,
  Azure/GCP docs, CNCF, NIST, ISO). Per repo policy no current-version pins —
  "latest stable, verify at time of use" throughout.
- **README "how it works" diagram** (`assets/how-it-works.png` + HTML source):
  a four-stage invocation flow (plain prompt → auto-routing → selective
  rules-file loading → BUILD/AUDIT application) with a worked file-upload
  example showing 4 skills loading automatically. Deliberately count-stable
  ("40+") so it never needs re-rendering on skill additions. Also clarified
  two README lines: the language-standards bullet no longer reads as
  "only 4 languages supported", and the invoicing example prompts no longer
  imply the user must name a stack (profile/skill defaults fill it in).
- **Count-surface floor model for the social preview**: the image pill and
  README alt now read **"40+"** so the PNG needs no re-render/re-upload per
  skill addition; `check-invariants.sh` gained `ck_floor` (fails only if the
  tree count drops below the floor); PNG re-rendered once; RELEASING.md
  updated.

### Fixed

- **Low-severity sweep triage (2026-07-09)** — the never-verified
  low-severity suggestions from the 2026-07-08 sweep (~75 candidate findings)
  were re-verified hypothesis-by-hypothesis against primary sources by one
  agent per skill: **58 applied** (each cites the verifying source; e.g.
  GraphQL @oneOf per the September 2025 spec edition, Mercurius WS depth-bypass
  CVE-2026-30241 checklist item, NATS 2.12–2.15 feature gates + the 2.15
  ack-subject ACL migration warning, PEP 734 subinterpreters + Python 3.14
  asyncio introspection, Go 1.25 testing/synctest, C++26 DIS status),
  **32 skipped** with recorded reasons (refuted, already covered by the
  verified-fix pass, or not worth the lines). The applied+skipped tallies
  exceed 75 because some findings split across multiple files. No version pins
  added; all invariants green.
- **Freshness sweep 2026-07-08** — 34-skill research pass (one web-research
  agent per skill; every high/medium finding independently
  adversarially verified against primary sources) fixed **7 high + 58 medium**
  confirmed gaps across 31 skills. Highlights: SurrealDB 3.1.5 security batch
  (databases/08); Argo CD repo-server unpatched gRPC RCE → require
  NetworkPolicy isolation (devsecops/06); ASP.NET Core Data Protection
  CVE-2026-40372 (dotnet/04); TorchServe archived → maintained serving
  runtimes (ml-engineering/05); Cilium mTLS guidance moved to the ztunnel
  integration (network-security/04); ingress-nginx EOL 2026-03-24 + migration
  guidance (network-security/05, kubernetes/01); jqwik 1.10.0 protestware
  advisory (testing/06); NIST SP 800-63B-4 15-char password floor
  (code-security/02); OCSP-stapling guidance retired after Let's Encrypt
  ended OCSP (code-security/04, network-security/06); ATT&CK v18/v19
  restructuring + BadSuccessor/dMSA detection (detection-engineering);
  JDK 24 ZGC/virtual-thread-pinning updates (jvm); K8s user-namespaces GA,
  Landlock ABI correction, 2025 runc CVE triple (sandboxing); TypeScript 7 GA,
  npm v12 script-blocking defaults, June-2026 supply-chain campaigns
  (javascript-typescript); Kyverno CVE-2026-4789 + CEL policy-type
  stabilization (devsecops/07, kubernetes/03); and more — see the PR for the
  full list.
- Genericity: removed three internal-abbreviation/reader-assumption phrasings
  that had slipped past the denylist; patterns added to the private denylist.

### Changed

- Contributor docs synced to this cycle's policy changes: AGENTS.md and
  CONTRIBUTING.md now state the **no-version-pins rule** (latest stable +
  semantic boundaries only, EOL→successor) as a standing convention and
  describe invariant 6's exact-count vs "N+"-floor split; RELEASING.md's
  pre-tag checklist matches the floor model; docs/ROADMAP.md logs
  `sota-confidential-computing` under coverage additions.
- **Version-claim policy applied library-wide**: rot-prone "current release is
  X.Y" claims replaced with "use the latest stable release — verify via a
  quick web search"; version numbers that mark semantic boundaries
  ("introduced/fixed/removed in vX", CVE fix versions, GA milestones) are
  kept. EOL/unmaintained tools are replaced by their maintained successors
  (project-recommended target first, then CNCF-maintained alternatives), with
  a one-line EOL note kept for auditors.
- **Freshness tracking model**: per-file line-1 `<!-- last-verified: YYYY-MM -->`
  markers retired (they duplicated git metadata and stayed 84% unstamped);
  replaced by a single root `LAST-VERIFIED` stamp recording the date of the
  last full-library verification sweep (initialized to 2026-07-08).
  `scripts/check-freshness.sh` rewritten for the new model (red when the
  stamp exceeds the 12-month window; warns on stray per-file markers);
  `freshness.yml`, AGENTS.md, CONTRIBUTING.md, and the README maintenance
  prompt updated accordingly.
- Router (`skills/sota/SKILL.md`): added cross-cutting routing rule 18,
  **"Cryptography fans out"** — a single lookup that maps a crypto task to its
  distributed owners (algorithm/AEAD/key-handling/TLS-client/PQC →
  `sota-code-security` rules/04; key material/storage/rotation →
  `sota-secrets-management`; TLS server/PKI/cert lifecycle →
  `sota-network-security` rules/06; FIPS-validated-module →
  `sota-security-compliance` rules/02). Documents the deliberate no-single-crypto-skill
  design; no content moved.

## [1.11.0] - 2026-07-06

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

---

Releases **1.7.1 and earlier** are archived in
[docs/CHANGELOG-archive.md](docs/CHANGELOG-archive.md).

[1.13.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.13.0
[1.12.1]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.12.1
[1.12.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.12.0
[1.11.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.11.0
[1.10.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.10.0
[1.9.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.9.0
[1.8.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.8.0
