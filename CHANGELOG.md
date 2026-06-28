# Changelog

All notable changes to SOTA-skills are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

## [1.4.0] - 2026-06-27

### Added

- **Plugin first-run notice** (`hooks/hooks.json` + `scripts/plugin-notice.sh`)
  — a one-time `SessionStart` notice for plugin installs that points users at the
  opt-in extras a sandboxed plugin can't auto-configure (always-on routing, status
  line, pre-commit gates, AGENTS.md). Shows once (marker-guarded); clone users get
  the same from `install.sh`.
- **README "Optional extras (for plugin users)"** — documents how plugin users
  turn on the routing hook, status line, and generators (which ship with the
  plugin) to match the clone experience.

## [1.3.0] - 2026-06-27

### Added

- **`scripts/statusline.sh`** — a Claude Code status line showing which skills
  you've actually used this session (read from the transcript's `Skill`
  invocations), plus model / context % / dir / branch; falls back to the count
  of installed skills before any are used. Requires `jq`.

### Changed

- **`scripts/install.sh` now offers always-on routing setup** (global CLAUDE.md
  directive + `UserPromptSubmit` hook) after linking — interactive and
  dotfiles-aware: detects existing/symlinked `~/.claude/CLAUDE.md` and
  `settings.json`, asks before changing anything (recommended pre-filled), backs
  up, writes through symlinks so dotfiles stay authoritative, and is idempotent
  via managed markers. Flags: `--routing`, `--no-routing`, `--yes`.

## [1.2.0] - 2026-06-27

### Added

- **`sota-docs-workflow` rules/05 — spec-driven development**: the
  intent→plan→tasks→implement→verify loop, separating what from how, testable
  acceptance criteria, `[NEEDS CLARIFICATION]` markers, specs-in-repo and
  spec-drift control, steering vs per-feature specs, and when SDD is overhead.
- **`sota-testing` rules/08 — BDD / specification by example**: declarative
  Given-When-Then, the three-amigos value, the outside-in double loop with TDD,
  scenario-explosion and UI-script anti-patterns, and tracing scenarios to spec
  acceptance criteria.
- **`scripts/gen-agents-md.sh`** — generate an `AGENTS.md` entry point so
  non-Claude agents (Codex, Cursor, Copilot, Gemini CLI, Windsurf, Zed, …) route
  through the skills. Thin pointer built from each skill's frontmatter; reads
  rules on demand, no duplication; idempotent managed block.
- **`scripts/init-gates.sh --docs-gate`** — opt-in pre-commit hook (helper at
  `.sota/docs-gate.sh`) that blocks a commit changing code without updating any
  docs (README/CHANGELOG/`docs/`/`*.md`). Heuristic and bypassable
  (`SKIP=sota-docs-gate`).

### Changed

- The always-on directive (generated `AGENTS.md` and the README `CLAUDE.md`
  example) now leads with two standing rules that apply to **every answer**:
  *validate every claim against a primary source before asserting*, and *keep
  docs current in the same change*.

## [1.1.0] - 2026-06-26

### Added

- **Claude Code plugin + marketplace** (`.claude-plugin/`): install with
  `/plugin marketplace add martinholovsky/SOTA-skills` then
  `/plugin install sota-skills@sota-skills`, and update with `/plugin update`.
- **`scripts/install.sh`** — installer that doubles as the updater: re-run after
  `git pull` to link newly-added skills and prune removed ones (idempotent);
  `--update`, `--project DIR`, `--copy`. Also links the local profile.
- **`scripts/init-gates.sh`** — detects a repo's languages and generates a
  SOTA-aligned `.pre-commit-config.yaml`: ruff/mypy/pytest/pip-audit,
  gofumpt/golangci-lint/govulncheck, clippy/cargo-audit, eslint/tsc/audit,
  shellcheck/shfmt, plus gitleaks. Fast checks on commit, heavy on push;
  idempotent via a managed marker block.
- **README**: "Always-on routing", "Enforcing the gates", and "Updating"
  sections documenting how to keep the skills applied and current.

## [1.0.0] - 2026-06-17

First public release.

### Added

- **30 skills** spanning architecture; security (code security, threat
  modeling, secrets management, sandboxing); API design; async/concurrency;
  performance; databases; observability; testing; LLM engineering; frontend
  design; cloud infrastructure; Kubernetes; identity & access; network security;
  detection engineering; data engineering; privacy/compliance; mobile; CLI UX;
  shell scripting; docs/workflow; and the Rust, Go, Python, and
  JavaScript/TypeScript language skills.
- **`sota` master router** with task-to-skill routing and operating principles,
  including a mandatory claim-validation principle.
- **BUILD and AUDIT modes** for every skill. Findings carry severity + effort +
  standard mapping + fix; every rules file ends with an executable audit
  checklist; every file stays under 500 lines for incremental loading.
- **Audit methodology**: scoping/rules of engagement, a verified static-analysis
  tool matrix, an evidence standard, and a report template.
- **Per-user `profiles/`** mechanism with `example.md.template`; real profiles
  are git-ignored so the library stays generic.
- **Repository invariants** enforced in pre-commit and CI: ≤500-line files,
  audit-checklist presence in every rules file, and an internal-reference
  denylist, plus gitleaks secret scanning.
- **Governance**: contributor guide, security policy, and code of conduct;
  `main` protected with required status checks.

[1.4.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.4.0
[1.3.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.3.0
[1.2.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.2.0
[1.1.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.1.0
[1.0.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.0.0
