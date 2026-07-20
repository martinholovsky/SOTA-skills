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
command line (needed for §9 reproducibility).

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
- **Controls that exist but are inert** — a safeguard whose success and whose
  total failure look identical from outside. SAST is blind to this by
  construction: the code isn't wrong, it's a no-op. Run it as its own pass
  (`sota-code-security` rules/10) over the controls the earlier passes
  confirmed exist.

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
   what hurts; effort enables the roadmap in §8.

Two asymmetries the evidence standard has to carry:

- **Negative claims need more proof than positive ones.** "No hardcoded secrets
  remain", "authorization is enforced everywhere", "nothing in this class was
  found" — a narrow search and a true absence produce identical output. Before
  any absence claim, widen the search (synonyms, other languages, generated and
  vendored trees, config as well as code) and confirm with a **second
  independent method** (grep *and* AST/call-graph *and* a dynamic or mutation
  probe). Then state the search performed, so the reader can judge its reach.
  An unqualified absence claim is the one finding-type nobody can falsify.
- **"The control is present" is not "the control works."** Evidence for a
  positive observation must show *effect*, not existence — the log line it
  emitted, the request it rejected, the test that fails when it's disabled.
  See `sota-code-security` rules/10; this applies to §8's positive-observations
  section too, where an inert control praised as a strength is the worst
  possible reporting error.

The library's short finding format (`file:line | rule | severity | effort | fix`)
is the working format during passes; expand each surviving finding into the
full evidence block for the report. Skill-local block formats are fine during
a single-domain pass, but they must carry the effort field — §8's roadmap is
sequenced by risk-reduction-per-effort and can't be built without it.

## 6. Decision-ledger review — audit the decisions, not just the code

Code review finds defects in what was built. It cannot find the defect where the
code is a faithful implementation of a choice that **stopped being right** — a
datastore picked for a scale that never arrived, a benchmark-justified rewrite
whose benchmark no longer reproduces, a constraint that expired two years ago and
is still shaping the design. That class is invisible to every pass above and is
often the most expensive thing in the repo.

`sota-architecture` rules/01 §4 owns **writing** ADRs. This is the audit side:
reading them back and asking whether they still hold.

**Reconstruct the ledger.** Sources, in order of reliability: ADRs
(`docs/adr/`), design docs and RFCs, the CHANGELOG, PR descriptions on the
commits that introduced each major component, and — last — comments. Where no
record exists, the decision is still there, just undocumented: infer it from the
code and label it *reconstructed, unconfirmed*. A major component with no
discoverable rationale is itself a finding.

**For each significant decision, classify it:**

- **JUSTIFIED** — the reasoning holds and the evidence still reproduces.
- **STALE** — sound when made, no longer: the constraint expired, the alternative
  got better, the load never materialized, the dependency went EOL. Not a mistake;
  a decision that has outlived its inputs. Say what changed.
- **UNJUSTIFIED** — the stated reasoning does not support the decision, or the
  evidence cited was never checked. Distinguish this from STALE plainly; it is a
  judgment about the decision as made.
- **UNVERIFIABLE** — no rationale survives and none can be reconstructed. Record
  it rather than guessing.

**Re-measure anything a decision rests on.** When the justification is a number —
a benchmark, a latency or throughput target, a recall/false-positive rate, "X is
faster than Y", "this doesn't scale" — **re-run it this session** and report the
result, including in heavyweight environments when that is the only honest way to
check. A number in a two-year-old ADR is a historical claim, not a current fact.
If you cannot re-run it, mark the decision UNVERIFIABLE and say precisely what
would confirm it (principles 0 and 6 apply here with full force). Respect the
repo's documented environment constraints and teardown rules when you do.

**Check the ledger against reality, both directions.** A decision recorded but
never implemented is as much a finding as one implemented but never recorded —
the ADR says "we use the outbox pattern", the code dual-writes. And a superseded
ADR still describing current behavior misleads every future reader.

**Report as findings.** STALE and UNJUSTIFIED entries carry a severity like any
other finding (impact of continuing on the current path × likelihood it bites),
and feed §8's roadmap — reversing an expensive decision is usually *large* effort
and belongs sequenced, not buried in prose. Quote both sides: the recorded
rationale and what you measured.

Scope it: the decisions worth this treatment are the expensive-to-reverse ones —
datastore, broker, service boundaries, auth model, tenancy model, language or
framework, build/deploy topology. Do not ledger-review every merged PR.

## 7. Adversarial verification — try to kill your own findings

Re-reading your own finding is the weakest possible check: you re-run the
reasoning that produced it and reach the same conclusion. Confirmation bias is
not defeated by attention. Before a finding ships, someone — a separate agent, a
colleague, or you in a deliberately hostile pass with fresh context — must try
to **refute** it.

The pass:

1. **State the finding as a falsifiable claim.** "An unauthenticated caller can
   read any tenant's invoices via `GET /invoices/{id}`" — not "weak access
   control in the invoices module". A claim you cannot refute is a claim you
   cannot verify.
2. **Assign refuters, prompted to kill it.** The instruction is *find the reason
   this is wrong*, not *check this*. Default the verdict to REFUTED when the
   evidence is ambiguous — an unrefutable finding must earn its survival.
3. **Use distinct lenses when a finding can fail in more than one way.** Three
   identical reviewers are worth less than three different questions:
   - **Correctness** — is the mechanism real? Read the full path, not the
     snippet. Is there an upstream guard the finding missed?
   - **Reachability** — can attacker-controlled input actually get here? Dead
     code, an unregistered route, or a caller that always sanitizes downgrades
     it to hardening debt.
   - **Severity inflation** — does the stated impact follow, or is a Medium
     dressed as a Critical? Rate the *demonstrated* impact.
4. **Majority-refute kills it.** Survivors ship; the rest are dropped or
   downgraded with the refutation recorded — a refuted finding is a result, not
   waste, and stops the next auditor re-raising it.
5. **Verify the negatives too.** "Authorization is enforced everywhere" is a
   finding-shaped claim with the heavier burden of `SKILL.md` principle 3. Give
   absence claims a refuter whose job is to find one counter-example.

Scale it to stakes: every Critical/High gets refuted, always. Mediums get a pass
when the audit is high-stakes or the finding drives an expensive fix. Skip it for
Low/Info hygiene items — the overhead outruns the value.

Two failure modes to avoid:

- **The rubber-stamp refuter.** An agent told to "verify" agrees. Prompt it to
  *refute*, give it the code rather than your summary, and do not show it your
  confidence level — a refuter that reads "I'm certain this is exploitable"
  inherits the certainty.
- **Refuting the description instead of the code.** The refuter must open the
  file at the pinned commit. A refutation built on the finding's prose only
  tests your writing.

## 8. Report structure

Deliver in exactly this order:

1. **Executive summary** — overall posture in plain language, counts by
   severity, the top 3–5 risks and what they mean for the business. A
   non-engineer must be able to read only this section and make decisions.
2. **Scope & methodology** — repos and commit hash, what was and was not
   covered (with the recorded exclusions from §1), standards asserted
   against, tools run with exact versions and commands, audit date. This
   makes the audit reproducible and bounds its claims.
3. **Decision ledger** — the §6 table: each significant decision →
   JUSTIFIED / STALE / UNJUSTIFIED / UNVERIFIABLE, with the recorded rationale
   and the evidence you re-checked. Omit the section only if the repo has no
   discoverable decisions; say so if you do.
4. **Findings** — grouped Critical → High → Medium → Low → Info; within a
   severity, ordered by exploitability. Each in the full §5 evidence block, and
   each Critical/High having survived the §7 refutation pass.
5. **Prioritized remediation roadmap** — *not a finding dump in severity
   order*. Sequence by **risk-reduction-per-effort**: quick critical wins
   first (trivial/small fixes to Critical/High), then high-impact larger
   work, then hardening. Group related fixes that share a root cause or a
   code area into one work item. The reader should be able to start work
   from the roadmap alone.
6. **Positive observations** — what is already done well (good patterns,
   solid boundaries, tooling in place), so it is preserved through
   remediation rather than accidentally regressed.
7. **Appendix** — full triaged tool output, the inventory from §2, DFDs and
   trust-boundary sketches, suppression-comment review.

## 9. Audit hygiene

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
- [ ] **Silent-control pass run** over the controls confirmed to exist — inert
      safeguards, fail-open catches, degradation nothing logs, tests that pass
      against a no-op'd body (`sota-code-security` rules/10)?

**Finding quality**
- [ ] Every finding has title, severity+justification, file:line@commit,
      minimal evidence, standard mapping, concrete impact, diff-level
      remediation, and effort estimate?
- [ ] Borderline severities state the deciding assumption explicitly?
- [ ] Uncertain findings marked "needs verification", not asserted?
- [ ] **Decision ledger reviewed** — expensive-to-reverse decisions reconstructed
      and classified JUSTIFIED / STALE / UNJUSTIFIED / UNVERIFIABLE, every number a
      decision rests on **re-measured this session** (or the decision marked
      unverifiable), and ledger-vs-code checked both directions (§6)?
- [ ] **Every Critical/High refuted by an independent pass** — a separate agent
      or a fresh-context hostile read prompted to *kill* the finding, working
      from the code and not from your write-up, with survivors kept and
      refutations recorded (§7)?
- [ ] Every **absence claim** ("no X found", "enforced everywhere") backed by a
      widened search plus a second independent method, with the search stated?
- [ ] Positive observations evidenced by **effect** (a rejection, a log, a test
      that fails when disabled), not by the control's mere presence?

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
