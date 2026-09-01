# Audit Methodology — Process, Tooling, Triage & Hygiene

Scope: this file governs **how** an audit is run — scoping, inventory, tool
selection, triage, and the hygiene rules that keep it reproducible and
non-destructive. What happens to what it finds — severity, evidence, the
decision-ledger pass, adversarial verification and the report template — is
`rules/03`. It does not contain domain findings either: **what** to check comes
from each domain skill's AUDIT mode and the Audit checklist at the end of every
rules file; route into those via the table in `SKILL.md`. Read this file and
`rules/03` first in any full or multi-domain audit; the checklist at the end of
each is the quality gate on the audit deliverable itself.

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
  signing/provenance setup. Record which declared dependencies, registered
  modules, and plugins are actually **reached from an entrypoint** — the
  declared-but-inert ones are a finding CVE scanning structurally cannot see
  (`sota-devsecops` rules/03 §3.9).
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
command line (needed for §4 reproducibility).

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

### Collect deterministically, then judge

Keep the two halves apart, in this order. **Enumeration is a script's job**: it must be
exhaustive over a scope you can state, and it must print its denominator (`261 rules
files`, `47 handlers`, `12 workflows`) so the number is auditable. **Judgment is the
model's job**, and it runs over the *complete* collected set, not over whatever the
search happened to surface.

Inverting them is the standard way an audit acquires a confident blind spot. A judgment
pass over a sampled or grep-shaped set inherits the sample's gaps and reports with the
same confidence as one that saw everything — and the miss is invisible in the output,
because a finding list looks identical whether the census behind it was 12 of 12 or 12
of 61. The corollary for the write-up: a **count** is a claim about the denominator, so
"9 of 61 call sites are guarded" is a finding, while "several call sites are unguarded"
is an impression (`sota-code-security` rules/14 §6–§7). Where the enumeration cannot be
scripted, say so and bound the claim to what you did read.

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
- **Controls that exist but are inert** — a safeguard whose success and whose
  total failure look identical from outside. SAST is blind to this by
  construction: the code isn't wrong, it's a no-op. Run it as its own pass
  (`sota-code-security` rules/10) over the controls the earlier passes
  confirmed exist.

## 4. Audit hygiene

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
  introduce new findings. State this loop in the roadmap. **A fix is verified
  when a fresh search cannot get around it, not when the reported input stops
  working**: re-point the original hunt at the patched code with no knowledge of
  the fix. Anthropic's defending-code reference harness makes this its fourth
  patch gate — the code builds, the proof of concept no longer fires, the test
  suite passes, *and* *"a fresh find agent can't find a way around the fix."* A
  patch that closes one input and leaves the class open passes all three of the
  narrower checks.
- **Read the yield curve across waves.** Repeated audits of one codebase should
  show the finding **count fall while the difficulty rises** — earlier findings
  are fixed, so later passes have to reach deeper; the harness reports the same
  shape (*"the number of findings will likely go down, but the complexity will
  likely also go up"*). A count that stays flat wave after wave is a statement
  about the audit, not about the code: the waves were not independent — same
  prompt, same salient files, nothing carried over. Carry the already-reported
  findings into the next wave as an explicit exclusion so it is steered past them
  instead of re-deriving them, and treat a wave that returns the previous wave's
  list as a failed wave.

---

## 5. Changing the AUDIT workflow? Change all three places

The audit workflow lives in **three** surfaces and they drift independently:

| Surface | What it holds |
|---|---|
| `skills/sota/SKILL.md` §AUDIT | the seven passes, one imperative each — read on every audit |
| this file | scoping, recon, the tool matrix, triage, hygiene |
| `rules/03` | severity, evidence, the decision ledger, refutation, report template |

The router's §AUDIT is deliberately terse because it is read every time; detail belongs in
the two rules files. So a new pass needs **a line in the router and a section in whichever
rules file owns it**, and a change to an existing pass needs both updated together — a step
whose procedure contradicts the file it points at is worse than no step, because the reader
follows whichever they loaded. The split itself is a drift risk: a pass about *rating or
reporting* a finding belongs in `rules/03`, one about *running* the audit belongs here, and
a section added to the wrong file is found by nobody looking for it.

§AUDIT **is** hash-pinned, as of 2026-09-01 — invariant 20 in `scripts/check-invariants.sh`
holds `ROUTER_AUDIT_SHA`, and the build fails when the section moves. The pin does not know
whether the two rules files still agree; it only guarantees that **someone had to come and
look**, because bumping it is a deliberate edit in the same commit. So the sequence is:
change §AUDIT, re-read this section and `rules/03`, fix whichever half is now wrong, then set
the new hash. (Before that date this paragraph read *"nothing catches this automatically"*,
and it was true — the gate was parked on a trigger that had already been met without anyone
noticing: `run-repo-audit.py` pastes the whole router, §AUDIT included.)

## Audit checklist — quality gate on running the audit

Finding quality and report structure are checked by `rules/03`'s checklist; this
one covers coverage, tooling and hygiene. Both run.

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
- [ ] **Silent-control pass run** over the controls confirmed to exist — inert
      safeguards, fail-open catches, degradation nothing logs, tests that pass
      against a no-op'd body (`sota-code-security` rules/10)?
- [ ] **Census, not spot-check**, for every mitigation the audit confirms exists:
      the protected operation enumerated and each call site marked guarded or
      unguarded, with the ratio reported (`sota-code-security` rules/14 §6)?
- [ ] **Universal claims in the security prose falsified by counting** — threat
      model, `security_model.md`, module docstrings, ADRs (`sota-code-security`
      rules/14 §7)?

**Hygiene**
- [ ] Audit was read-only; nothing in the target mutated without explicit
      instruction?
- [ ] Re-audit loop defined for verifying remediation — and does it verify each fix
      by **re-pointing the original hunt at the patched code**, rather than only
      confirming the reported input stopped working (§4)?
- [ ] On a repeat audit, was the **yield curve** read — count falling while
      difficulty rises — and were the previous wave's findings carried in as an
      explicit exclusion so the waves are independent (§4)?
