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
- **Pick baseline or diff, and say which.** Reviewing only the change is the default. A
  whole-codebase **baseline** is owed for: a new application, a major release, taking
  over legacy code, a compliance cycle, a change to the architecture, and after an
  incident. A diff review that turns up a serious concern **escalates** to a baseline of
  the affected component — the defect class it exposed rarely lives only in the diff.
  Where a full baseline is out of reach, extend it one component per cycle and record
  the covered set, and hold a recurring joint review in which security, development and
  operations read code together. OWASP: Secure Code Review cheat sheet; DSOMM.

## 1a. A changeset too large to hold at once — partition it, don't skim it

The authoring side of this is covered elsewhere (`sota-docs-workflow` rules/03: keep
PRs small, because large ones converge on "LGTM"). This is the **reviewer's** half,
which is the one you need when the large PR exists anyway and is yours to review.

**The failure mode is silent and it is not laziness.** Given more changed files than
fit comfortably in one pass, a reviewer — human or model — does not announce that it
ran out of room. It reviews some files carefully, skims others, and produces a report
whose *shape* is identical to a complete one. Nothing in the output says "I covered 9
of 23 files". Reported at scale by Alibaba's Open Code Review (Apache-2.0) as the
first of three failure modes of language-driven review, and it matches this library's
own measured **completeness residual** — a cross-cutting requirement quietly dropped
as context fills (`docs/WHY-COMPLETENESS-RESIDUAL.md`).

So do not let the model decide coverage. Decide it deterministically, before review:

1. **Enumerate the units first, mechanically.** `git diff --name-only <base>...<head>`
   is the denominator. Write it down. Every file is either reviewed, or explicitly
   excluded with a reason (§1's *record exclusions*) — never neither.
2. **Bundle related files into one unit.** Files that must be read together to be
   judged go together: a handler and its test, a migration and the model it alters,
   the four locale files that must stay in sync, an interface and its implementations.
   A bundle is the unit whose *internal consistency* is the thing being checked, and
   splitting one across passes is how a mismatch survives review.
3. **Give each bundle its own pass with fresh context.** Isolated context per bundle
   is what keeps pass 9 as sharp as pass 1; it also parallelises, but that is a
   side benefit, not the reason.
4. **Report the denominator with the findings.** "23 files changed, 23 reviewed in 7
   bundles, 2 excluded (generated, vendored)" is part of the result. A findings list
   with no coverage statement is indistinguishable from a partial one — the same
   fail-closed discipline the gates in this repo apply to their own file counts.

**Partitioning is not the same as sampling.** A sample is a defensible answer to
"what is the state of this codebase"; it is never a defensible answer to "is this
change safe to merge", where the unreviewed file is exactly where the defect is.

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
  (`sota-devsecops` rules/10).
- **Deploy & runtime config**: Dockerfiles/Containerfiles, K8s manifests and
  Helm charts, Terraform/IaC, network policies, GitOps definitions.
- **History and people**: read the target's past incidents, postmortems and earlier
  findings — a component that failed once is where to look again. Code in a language or
  framework the team has little experience with raises the risk rating on its own. And
  check that whoever judges the high-risk code knows both the language and its security
  context; where they do not, write the gap into the report's scope rather than let a
  pass look deeper than it was. OWASP: Code Review Guide v2; Secure Code Review cheat sheet.

**Rank what to read first by complexity × churn.** Inside §1's crown jewels, order files
by change frequency (`git log --since=1.year --format= --name-only | sort | uniq -c |
sort -rn`) crossed with per-function cyclomatic complexity from any metrics tool. As a
rough guide from the OWASP Code Review Guide v2: up to 10 is ordinary, 11–15 warrants a
closer read, 16–20 a deep one, and above 20 also record a recommendation (Info) to split
the function. Complexity sets reading order, not severity; the scoring model
is `sota-testing` rules/01 §1.4, not repeated here.

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
- **Deprecated and banned APIs are findings in every language.** A call the platform has
  marked deprecated is unmaintained surface with a known replacement; report it, and check
  CI fails on it rather than printing a warning nobody reads — verified 2026-09-25:
  `javac -Xlint:deprecation -Werror`, `clang -Werror=deprecated-declarations`,
  `rustc -D deprecated`, `python -W error::DeprecationWarning` each exit non-zero on a use;
  Go's staticcheck reports it as SA1019. Suppressing the warning is the suppression case
  above. Per-language banned lists live in the language skills (e.g. `sota-c-cpp`
  rules/04 §1). Source: SCSVS S2.1.A2.

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

### An empty page is a fact about your fetcher, not about the source

A client-rendered site returns **HTTP 200 with no content** to a plain fetcher, and that is
indistinguishable from a page that genuinely says nothing. The failure presents as *"the
source is empty"* — a finding about the **content** — when it is a finding about the
**instrument**.

Measured 2026-09-13 on a source four separate research passes had written off as unreachable:

```console
GET evals.mitre.org/results/enterprise   → HTTP 200,   3,150 bytes,       2 words of text
GET evals.mitre.org/api/adversaries/     → HTTP 200, 1,854,829 bytes, 124,872 words
```

**The fix is usually one level down, and frequently unauthenticated.** Before concluding a
source is gated or empty, look for the API feeding the page: an `/api/` path, a
`__NEXT_DATA__` or `window.__INITIAL_STATE__` blob in the HTML, a sitemap, or an `.json`
sibling of the route. Where none exists, browser automation renders it; where even that
fails, an archive's capture of a retired **API endpoint** often survives when the archived
HTML is only a redirect stub.

- **Treat a body under a few hundred words from a documentation or data site as a broken
  instrument**, not a short page. Print the byte count and the visible-word count beside any
  claim you draw from a fetch — the denominator rule (`sota-shell-scripting` rules/06 §2)
  applied to retrieval.
- **"The page was empty" is never evidence the fact does not exist.** Say which retrieval
  method failed. An absence sourced to one fetcher carries the burden in `rules/03` §2, and
  a second method with the *same* failure mode is not a second method.

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

## 4a. Knowledge that lives only in an agent's memory

An assistant working a repository over months accumulates a private store — Claude Code's
`~/.claude/projects/<repo>/memory/`, an IDE's workspace notes, a chat history someone greps.
It is genuinely useful and some of it *must* stay there: facts about the machine (which
binary `grep` really is, which commands the harness refuses), account state, and anything a
public repo's own denylist would reject. **The audit question is narrower: is anything in
there a fact about the repository that the repository does not have?**

That fact is invisible to review, absent from a fresh clone, missing on a second machine, and
gone when the store is cleared — and nobody discovers this until the one person or session
that held it is not there. Known gaps, open items, why a decision was made, a measured
number, a deferral: if the only copy is in an agent's memory, the repo has a hole shaped
exactly like the thing everyone assumes is written down.

**How to run it**

1. **Enumerate the store** and classify each entry: *environment* (stays), *behavioural
   correction to the agent* (stays), or *repository fact* (must exist in the repo).
2. For every repository fact, **find its home**: an item ledger, a decision record, a results
   file, a changelog entry. Not "is it mentioned somewhere" — *which file owns it*.
3. **Report the ones with no home as findings**, and fix them by moving the fact into the
   repo, leaving the memory entry as a pointer.

**This is an absence claim, so it carries §3's burden — and the naive form of it lies.**
Measured on a 50-file store against a 16-million-character corpus: a literal scan of 148
distinct measured claims flagged **11** as memory-only, and **every one that was checked
turned out to be in the repo under different wording** — "10 of 32" was written there as *"10
of the old 32 freshness cases"*. A numeral is the worst possible search key for this, because
prose paraphrases numerals freely. Use a **distinctive neighbouring phrase** as the second
method (`signed-char`, `plugin-scanner`, `per-case progress`), run a positive control in the
same invocation, and read the hits rather than the count
(`sota-shell-scripting` rules/06 §2).

**The durable fix is a convention, not a sweep.** Memory should *cite* the repo, never
restate it — "landed v1.36.2", "ROADMAP 44" — so a stale note reads as a pointer to re-check
rather than a competing claim. Restated status drifts; that is the same failure the summary
table has (`rules/03` §2), one layer further out, and it is the reason this pass exists at
all rather than being a one-off cleanup.

## 4b. Resolve every citation before you ship it — position drift

`rules/03` §2 requires each finding's location to be "exact, clickable, reproducible".
That states the requirement and checks nothing, which is this library's most common
gap shape: the rule is written, the probe is missing. Here is the probe.

**Position drift is a finding that is right about the defect and wrong about where it
is.** The mechanism is ordinary: line numbers read off a diff hunk rather than the
file, a quote paraphrased from memory after the file scrolled out of context, a
`file:line` carried forward while the surrounding analysis moved on, or a path that is
correct in one module and repeated for its near-identical sibling. Alibaba's Open Code
Review (Apache-2.0) reports it from two years of production review as one of three
dominant failure modes; this repo has its own version, which is why **invariant 18**
exists — roughly 1,300 prose `§` references that broke silently on a renumber, and 20
more caught during a single rules-file split.

**It is dangerous because it degrades trust rather than triggering an error.** A
report whose citations do not resolve looks exactly like one whose citations do. The
reader who cannot find the code usually assumes they are looking in the wrong place;
if they do apply the fix, they apply it to whatever is at that line now.

Before any finding ships — and **before the adversarial pass of `rules/03` §4, not
after** — resolve every citation mechanically:

- [ ] **Re-read the file at the pinned commit.** Not your notes, not the diff, not
      the snippet you already quoted. Restating from your own earlier output re-runs
      the reasoning that produced the error (`SKILL.md` principle 7).
- [ ] **The quoted evidence appears at the cited line, byte-identical.** A paraphrase
      that "means the same thing" is a failed check: it means the quote was
      reconstructed, and a reconstructed quote is not evidence.
- [ ] **Diff line numbers were converted.** Hunk-relative and file-absolute numbers
      differ by the hunk offset, and the mistake is invisible because the result is
      still a plausible line in a real file.
- [ ] **The path is the one you read**, not its sibling — check the full path, not the
      basename. `src/auth/session.go` and `src/authz/session.go` both exist.

A citation that does not resolve **fails the finding, it does not soften it**. Fix the
location or drop the finding; never ship it with an approximate one. The cost
asymmetry is the whole argument for putting this first: this check is mechanical and
takes seconds, the refutation pass in `rules/03` §4 is expensive, and a finding that
cannot even be located does not deserve a refuter's attention.

**Run it as a real check, not an intention.** Verify it can fail before you trust a
clean result — point it at a citation you have deliberately broken and watch it
complain (`sota-code-security` rules/11 §7). A verification pass that has never
produced a failure is not evidence that the citations are right.

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

- [ ] **Any source written off as empty or unreachable?** (§3) A client-rendered page returns
      **200 with almost no text** — measured, 2 words of visible text where the API behind it
      returned 124,872. Look for the `/api/` path, a `__NEXT_DATA__`/`__INITIAL_STATE__` blob
      or a sitemap before concluding a source says nothing, and print bytes plus visible-word
      count beside any claim drawn from a fetch.

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
- [ ] **Medium** — Baseline-or-diff choice stated against the §1 triggers, and every
      serious diff-review concern escalated to a baseline of that component (§1)?
- [ ] **Medium** — Past incidents/postmortems read, unfamiliar languages rated up,
      reviewer competence gaps named in scope, and files ordered by complexity × churn (§2)?

**Tooling & triage**
- [ ] Tool names/versions verified current before running (renames/forks
      checked), versions and commands recorded?
- [ ] Matrix coverage run per detected language plus secrets-history, SCA,
      containers, IaC/K8s, CI workflows, signing as applicable?
- [ ] Every reported finding human-confirmed — no raw scanner dumps,
      false positives filtered, duplicates merged?
- [ ] Exploitability re-rated in context (tool severity treated as input)?
- [ ] Existing suppression comments reviewed?
- [ ] **Medium** — Deprecated-API use reported, CI fails on deprecation warnings, and each
      silenced one justified (§3): `grep -rnE 'SuppressWarnings\(.*"(deprecation|removal)"|allow\(deprecated\)|-Wno-deprecated|ignore::DeprecationWarning|"ignore"[^)]*DeprecationWarning|SA1019|disable CS0618' .`
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

**Coverage and citations**
- [ ] For a changeset too large for one pass: units **enumerated mechanically**
      first, related files **bundled** so each bundle is judged whole, every file
      either reviewed or explicitly excluded, and the **denominator reported**
      alongside the findings (§1a)?
- [ ] Every finding's `file:line` **resolved against the file at the pinned
      commit**, with the quoted evidence byte-identical, diff-relative numbers
      converted, and the full path checked against its siblings — run *before*
      the adversarial pass, and watched to fail at least once (§4b)?

**Hygiene**
- [ ] Audit was read-only; nothing in the target mutated without explicit
      instruction?
- [ ] Re-audit loop defined for verifying remediation — and does it verify each fix
      by **re-pointing the original hunt at the patched code**, rather than only
      confirming the reported input stopped working (§4)?
- [ ] On a repeat audit, was the **yield curve** read — count falling while
      difficulty rises — and were the previous wave's findings carried in as an
      explicit exclusion so the waves are independent (§4)?
