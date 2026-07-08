# Audit Methodology — Process, Tooling, Severity, Evidence & Reporting

Scope: this file governs **how** an audit is run and reported — scoping,
inventory, tool selection, triage, severity, evidence, report format, hygiene.
It does not contain domain findings. **What** to check comes from each domain
skill's AUDIT mode and the Audit checklist at the end of every rules file;
route into those via the table in `SKILL.md`. Read this file first in any
full or multi-domain audit; the checklist at the end is the quality gate on
the audit deliverable itself.

---

## 1. Scoping & rules of engagement

Agree these before reading a single line of code:

- **Target**: which repos/services, which branch, **pinned to a commit hash**.
  Findings against a moving target are not reproducible.
- **Environments**: static analysis only, or dynamic testing against running
  systems too? If dynamic: which environment (never production by default),
  what traffic/load is acceptable, who is informed.
- **Stop-and-ask rule**: before touching anything live, shared, or
  destructive — running scanners against deployed endpoints, mutating CI/CD,
  rotating credentials, opening cloud consoles — stop and confirm. An audit
  that breaks the system under audit is a failed audit.
- **State the yardstick up front.** Name the standards the audit asserts
  against; this makes findings defensible and disputes resolvable:
  - OWASP ASVS (state the level: L1 baseline, L2 standard, L3 high-assurance)
  - OWASP Top 10 (2025) and OWASP API Security Top 10 (2023)
  - CWE for weakness identification
  - MITRE ATT&CK for attacker-technique mapping
  - For LLM/agent code: OWASP Top 10 for LLM Applications, OWASP Agentic AI
    guidance, MITRE ATLAS
- **Time-box and prioritize crown jewels.** When time is bounded, depth beats
  breadth. Audit first, in order: authentication/session code, secrets
  handling and history, money and sensitive-data flows, internet-facing entry
  points, any path where untrusted LLM input reaches a tool or privileged
  action. Everything else comes after.
- **Record exclusions.** Anything out of scope (vendored code, generated
  files, a service owned by another team) is written down, not silently
  skipped.

## 2. Inventory & recon — build the map before judging

You cannot audit what you have not mapped. Enumerate:

- **Languages, frameworks, runtimes — with versions.** This selects the
  language skills, the tool matrix rows, and flags EOL runtimes immediately.
- **Entry points / attack surface**: HTTP routes, WebSocket/SSE endpoints,
  queue/stream consumers, cron and scheduled jobs, webhooks (inbound and
  outbound), CLI surfaces, MCP tools/servers and any other agent-reachable
  interfaces.
- **Trust boundaries & data flows**: where untrusted input enters, where it
  crosses a privilege boundary, where sensitive data lives and moves. Sketch
  a DFD — follow `sota-threat-modeling` rules/02 (decomposition) and rules/06
  (reconstructing a threat model from an existing codebase). The threat model
  output prioritizes every later pass.
- **Secrets surface**: how secrets are stored and injected (env, files,
  SOPS/age, Vault, cloud secret managers, workload identity), plus a history
  scan for past leaks (tools in §3).
- **Dependencies & supply chain**: lockfiles and manifests, base images,
  CI workflow definitions and third-party actions, existing SBOMs,
  signing/provenance setup.
- **Deploy & runtime config**: Dockerfiles/Containerfiles, K8s manifests and
  Helm charts, Terraform/IaC, network policies, GitOps definitions.

Then **map every inventory item to the routing table in `SKILL.md`** and load
the matching skills' AUDIT modes. Skip skills with no matching surface; record
that you skipped them and why. An inventory item with no owning skill is
itself a gap worth noting.

## 3. Tool matrix & triage

Tools find the mechanical 60%; manual review finds the design flaws. Run
both, never just one. The matrix below was verified current as of 2026-06;
tools rename, fork, and die — **verify the current name and version of each
tool before invoking it** (one quick search; e.g. Semgrep's OSS engine was
forked to Opengrep in 2025 after a license split). Prefer the open-source
option where capability is equivalent.

| Area | Tools (verify current before use) | Notes |
|---|---|---|
| Secrets in code & git history | gitleaks; trufflehog | gitleaks is feature-complete (security patches only); still the standard scanner. trufflehog additionally *verifies* credentials live — never run verification against creds you must not touch. detect-secrets (Yelp, actively maintained) is a solid baseline scanner; prefer the first two for breadth and live verification. |
| Python SAST + deps | bandit; Opengrep/Semgrep CE; pip-audit | pip-audit is PyPA-maintained and can suggest fixes. |
| Rust | cargo-audit; cargo-deny; clippy `-D warnings` | cargo-deny also covers licenses and banned crates; clippy ships with the toolchain. |
| Go | gosec; govulncheck; staticcheck; `go test -race` | govulncheck is the official Go team scanner — call-graph-aware, low false positives. |
| JS/TS + Node | eslint-plugin-security (eslint-community); `npm audit`/`pnpm audit`; osv-scanner | Socket.dev (commercial, free tier) adds behavioral malicious-package detection beyond CVE lookup. |
| Multi-language SAST | Opengrep or Semgrep CE + community rulesets | Opengrep (LGPL fork, multi-vendor consortium) restores cross-function taint analysis that Semgrep CE gated commercially; rule format is compatible across both. |
| SCA — any ecosystem | osv-scanner (Google); trivy; grype | Run one as primary; a second only to cross-check noisy results. |
| Containers / images | trivy; grype; dockle | Verify base-image digest pinning manually. dockle's release cadence is slow — treat as supplementary lint, not the primary gate. |
| SBOM | syft (generate) → grype (scan) | trivy can also emit SBOMs (CycloneDX/SPDX). |
| Supply-chain signing & provenance | cosign verify (with `--certificate-identity` / `--certificate-oidc-issuer` for keyless); slsa-verifier | Verify provenance/attestations actually chain to the expected builder identity, not merely that a signature exists. |
| IaC / K8s | checkov; trivy (misconfig scanning); kubescape; kube-linter | kubescape is CNCF-incubating; kube-linter is lightweight and CI-friendly. |
| CI workflow security | zizmor | Static analysis of GitHub Actions workflows: template injection, credential persistence, ref spoofing, excessive permissions. |
| Licenses | cargo-deny (Rust); trivy license scan; syft SBOM license fields | Filter against the project's allowed-license policy. |

Run each tool against the pinned commit; record the exact tool version and
command line (needed for §7 reproducibility).

### Triage discipline — tool output is raw material, not findings

- **Never paste raw scanner dumps into the report.** A scanner hit becomes a
  finding only after a human (you) confirms it.
- **Confirm each hit is real**: read the flagged code in context; filter
  false positives and unreachable code paths.
- **Deduplicate** across tools and across domain passes — one weakness
  reported by four tools is one finding.
- **Re-rate exploitability in this context.** A tool's "high" in dead code
  may be Info; a tool's "low" on an internet-facing auth path may be your
  worst finding. Tool severity is an input, never the output.
- **Suppressions are findings too**: inspect existing `#nosec`,
  `# nosemgrep`, `nolint`, audit-ignore files and the like — each one is
  either justified (note it) or a hidden finding.

### Manual review — what tools cannot see

Budget explicit manual passes for the classes SAST is structurally blind to:

- Business-logic flaws (order of operations, state machines, refund/limit
  logic).
- Authorization and object-level access (BOLA/IDOR) — tools verify *authn*
  exists, rarely that *authz* is correct per object.
- Trust-boundary crossings the DFD revealed: does validation actually happen
  at the boundary, or three layers later?
- Race conditions and TOCTOU (pair with `sota-async-concurrency` rules/07).
- Crypto misuse: right primitive, wrong protocol; key handling; nonce reuse.
- Prompt-injection, excessive-agency, and tool-poisoning paths in LLM/agent
  code (pair with `sota-code-security` rules/08).

## 4. Severity model

Rate **impact × likelihood/exploitability, in context**. CVSS may inform the
rating; it is never the rating. The deployment context (internet-facing vs
internal, data sensitivity, existing mitigations) decides the final level.

- **Critical** — exploitable now with severe impact: RCE, auth bypass,
  secrets/keys exposed in repo or logs, unauthenticated access to sensitive
  data, prompt injection reaching a privileged tool. Fix immediately; ask
  whether it is already an incident (was the secret ever live? rotate first,
  then fix).
- **High** — serious impact or likely exploitation: injection (SQL/command/
  NoSQL), broken access control (BOLA/IDOR), missing authn on a sensitive
  route, weak or hand-rolled crypto, SSRF. Fix this sprint.
- **Medium** — real weakness requiring conditions or chaining: missing rate
  limits, verbose error leakage, absent security headers/CSP, weak
  validation behind an authenticated boundary.
- **Low** — defense-in-depth and hygiene: minor info disclosure, hardening
  gaps with low standalone impact, lint-level issues with a security flavor.
- **Info** — no direct risk: observations, tech-debt notes, future-proofing,
  positive-pattern caveats.

Two hard rules:

1. **Borderline ratings state the deciding assumption explicitly** — "High
   if this endpoint is internet-facing; Medium if internal-only" — and ask
   when the answer is knowable. Do not silently pick the scarier level.
2. **Uncertain findings are marked "needs verification", never asserted.**
   A speculative Critical that turns out false costs the whole report its
   credibility.

## 5. Evidence standard — no finding without it

Every finding carries all of the following. A finding missing any item is
not ready to ship:

1. **Title** — concise statement of what is wrong.
2. **Severity** + one-line justification (impact × likelihood, per §4).
3. **Location** — `file:line` at the pinned commit (or manifest key, route,
   workflow step). Exact, clickable, reproducible.
4. **Evidence** — the minimal code/config snippet or triaged tool output
   that proves the issue. Minimal: enough to verify, no page-long dumps.
5. **Standard mapping** — CWE id; OWASP Top 10 / API Top 10 / ASVS item;
   MITRE ATT&CK or ATLAS technique where it applies.
6. **Impact** — what the attacker (or affected user) *actually gets*:
   "reads any tenant's invoices", not "improper access control".
7. **Remediation** — concrete and diff-level where possible ("parameterize
   this query", with the changed line), referencing the relevant skill's
   rules file for the full pattern. Never "sanitize input".
8. **Effort estimate** — trivial / small / medium / large. Severity says
   what hurts; effort enables the roadmap in §6.

The library's short finding format (`file:line | rule | severity | effort | fix`)
is the working format during passes; expand each surviving finding into the
full evidence block for the report. Skill-local block formats are fine during
a single-domain pass, but they must carry the effort field — §6's roadmap is
sequenced by risk-reduction-per-effort and can't be built without it.

## 6. Report structure

Deliver in exactly this order:

1. **Executive summary** — overall posture in plain language, counts by
   severity, the top 3–5 risks and what they mean for the business. A
   non-engineer must be able to read only this section and make decisions.
2. **Scope & methodology** — repos and commit hash, what was and was not
   covered (with the recorded exclusions from §1), standards asserted
   against, tools run with exact versions and commands, audit date. This
   makes the audit reproducible and bounds its claims.
3. **Findings** — grouped Critical → High → Medium → Low → Info; within a
   severity, ordered by exploitability. Each in the full §5 evidence block.
4. **Prioritized remediation roadmap** — *not a finding dump in severity
   order*. Sequence by **risk-reduction-per-effort**: quick critical wins
   first (trivial/small fixes to Critical/High), then high-impact larger
   work, then hardening. Group related fixes that share a root cause or a
   code area into one work item. The reader should be able to start work
   from the roadmap alone.
5. **Positive observations** — what is already done well (good patterns,
   solid boundaries, tooling in place), so it is preserved through
   remediation rather than accidentally regressed.
6. **Appendix** — full triaged tool output, the inventory from §2, DFDs and
   trust-boundary sketches, suppression-comment review.

## 7. Audit hygiene

- **Reproducible**: pin the commit; record exact tool versions and full
  command lines so anyone can re-run the audit and re-verify each finding.
- **Read-only by default**: do not mutate the audited system — no fixes
  applied silently, no CI/CD edits, no secret rotation, no infra changes.
  Propose changes; apply only on explicit instruction, as a separate task.
- **No secret values in the report**: when you find a leaked secret, redact
  the value, reference its location (`file:line`, commit) and type, and flag
  rotation as the remediation. Treat the report itself as a sensitive
  artifact — it is a map of the system's weaknesses.
- **Findings stay in the report**, not scattered in code comments or TODOs
  added to the audited repo.
- **Re-audit loop**: after remediation, re-run the same tools at the new
  commit and re-execute the relevant skill checklists against the changed
  code — confirm fixes, catch regressions, and check that fixes did not
  introduce new findings. State this loop in the roadmap.

---

## Audit checklist — quality gate on the audit itself

**Coverage**
- [ ] Scope agreed: repos, branch, pinned commit, environments,
      static-vs-dynamic — and exclusions documented?
- [ ] Standards set named up front (ASVS level, OWASP Top 10 2025,
      API Top 10 2023, CWE, ATT&CK; LLM/ATLAS where applicable)?
- [ ] Full inventory done: languages+versions, entry points, trust
      boundaries/DFD, secrets surface, dependencies, deploy configs?
- [ ] Every inventory item mapped to a skill via the routing table, and each
      applicable skill's AUDIT mode executed (skips recorded with reasons)?
- [ ] Crown-jewel paths (auth, secrets, money/data flows, internet-facing,
      untrusted-LLM-input) audited in depth, first?

**Tooling & triage**
- [ ] Tool names/versions verified current before running (renames/forks
      checked), versions and commands recorded?
- [ ] Matrix coverage run per detected language plus secrets-history, SCA,
      containers, IaC/K8s, CI workflows, signing as applicable?
- [ ] Every reported finding human-confirmed — no raw scanner dumps,
      false positives filtered, duplicates merged?
- [ ] Exploitability re-rated in context (tool severity treated as input)?
- [ ] Existing suppression comments reviewed?
- [ ] Manual passes done for logic, authz/BOLA, boundary crossings, races,
      crypto misuse, prompt-injection paths?

**Finding quality**
- [ ] Every finding has title, severity+justification, file:line@commit,
      minimal evidence, standard mapping, concrete impact, diff-level
      remediation, and effort estimate?
- [ ] Borderline severities state the deciding assumption explicitly?
- [ ] Uncertain findings marked "needs verification", not asserted?

**Report**
- [ ] Executive summary in plain language with severity counts and top
      3–5 risks?
- [ ] Scope/methodology section sufficient to reproduce the audit?
- [ ] Findings grouped by severity, ordered by exploitability within?
- [ ] Remediation roadmap sequenced by risk-reduction-per-effort, related
      fixes grouped — actionable without re-reading every finding?
- [ ] Positive observations included?
- [ ] No secret values anywhere in the report; leaks redacted and referenced
      by location only?

**Hygiene**
- [ ] Audit was read-only; nothing in the target mutated without explicit
      instruction?
- [ ] Re-audit loop defined for verifying remediation?

A report that ships unverified findings, raw tool dumps, or no prioritized
roadmap is itself a failed deliverable — treat missing evidence or missing
remediation as a blocker on the audit, not a polish item.
