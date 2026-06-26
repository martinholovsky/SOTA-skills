# SOTA Engineering Skills

<p align="center">
  <a href="https://github.com/martinholovsky/SOTA-skills/releases"><img src="https://img.shields.io/github/v/release/martinholovsky/SOTA-skills?color=2fa45f&label=release" alt="Latest release"></a>
  <a href="https://github.com/martinholovsky/SOTA-skills/actions/workflows/ci.yml"><img src="https://github.com/martinholovsky/SOTA-skills/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  <img src="https://img.shields.io/badge/skills-30-2fa45f" alt="30 skills">
  <img src="https://img.shields.io/badge/modes-BUILD%20%2B%20AUDIT-2fa45f" alt="BUILD + AUDIT">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-CC%20BY%204.0-blue" alt="License: CC BY 4.0"></a>
</p>

<p align="center">
  <img src="assets/social-preview.png" alt="SOTA Engineering Skills — 30 Claude Code skills to build and audit software at state-of-the-art practices" width="100%">
</p>

**Make your AI coding assistant build and audit like your most senior engineer.**

Your assistant is brilliant — it just doesn't know your standards. SOTA-skills
teaches it: a library of Claude Code skills that encode state-of-the-art (2026)
practices for building **and** auditing software, and that verify their own
claims. 30 skills, 216 files, ~46k lines — every file under 500 lines, so the
right rules load exactly when your task needs them, never bloating the context
window. Fast-moving claims (versions, specs, regulations) are web-verified
against primary sources; last refresh: 2026-06-14.

Two cross-cutting pieces live outside the domain skills:

- `skills/sota/rules/01-audit-methodology.md` — how to run an audit: scoping &
  rules of engagement, a verified static-analysis tool matrix with triage
  discipline, the evidence standard (every finding carries severity, effort,
  standard mapping, and a concrete fix), and the report template (executive
  summary → findings → remediation roadmap by risk-reduction-per-effort →
  positive observations).
- `profiles/` — per-user stack profiles (preferred stores, auth, license
  policy, project triggers). The router treats a profile as the default in
  BUILD mode and the expected baseline in AUDIT mode, keeping the library
  itself generic and shareable.

## Structure

```
skills/
  sota/                          # master router — start here
    SKILL.md                     # routing, operating principles, workflows
    rules/
      01-audit-methodology.md    # how to audit: tooling, evidence, reporting
  sota-<domain>/
    SKILL.md                     # when to use, BUILD/AUDIT workflows,
                                 # severity conventions, rules index, top-10
    rules/
      01-<topic>.md              # 150–320 lines each, ends with an
      02-<topic>.md              # executable Audit checklist
      ...
profiles/
  <user>.md                      # personal stack defaults consulted by router
```

Every skill works in two modes:

- **BUILD** — apply the rules while designing/writing code.
- **AUDIT** — review existing code; findings are emitted as
  `file:line | rule violated | severity (Critical/High/Medium/Low/Info) |
  effort (trivial/small/medium/large) | fix`.

## Skills

| Skill | Covers |
|---|---|
| `sota` | Master router: operating principles, task→skill routing, full-audit workflow + audit methodology (tool matrix, evidence standard, report template) |
| `sota-architecture` | Styles & ADRs, DDD, distributed systems, resilience, scalability, cloud-native, anti-patterns |
| `sota-code-security` | Injection, authn/authz, crypto, web security, resource safety, data exposure, LLM appsec |
| `sota-threat-modeling` | STRIDE/LINDDUN, DFDs & trust boundaries, threat catalogs, risk rating, model reconstruction |
| `sota-secrets-management` | Lifecycle & workload identity, storage backends, app patterns, leak detection, credential types |
| `sota-sandboxing` | Isolation boundaries, seccomp/Landlock/capabilities, containers/microVMs, parsers, AI-agent sandboxing |
| `sota-performance` | Measure-first methodology, algorithms, memory, I/O & network, caching, Web Vitals |
| `sota-async-concurrency` | Concurrency models, races/deadlocks, primitives, event-loop hygiene, cancellation, backpressure |
| `sota-api-design` | REST/HTTP, versioning, GraphQL, gRPC, websockets/SSE/realtime, webhooks, API security & ops |
| `sota-devsecops` | Pipeline hardening, SLSA/Sigstore provenance, dependencies/SBOM, container builds, IaC, admission control |
| `sota-databases` | Modeling & engine choice, zero-downtime migrations, indexes, transactions, reliability, security, pgvector/Qdrant, SurrealDB |
| `sota-frontend-design` | Typography/color, layout, design systems, UX patterns, WCAG 2.2 accessibility, motion design, visual craft |
| `sota-observability` | Structured logging, metrics, OpenTelemetry tracing, SLOs & alerting, operational readiness |
| `sota-testing` | Test strategy & design, doubles/test data, contract testing, e2e, property/fuzzing/mutation, suite health |
| `sota-llm-engineering` | Evals, prompt/context engineering, RAG, agents & tools, LLM production engineering, data lifecycle |
| `sota-cloud-infrastructure` | Accounts/landing zones, cloud IAM, VPC/DNS/CDN setup, compute selection, storage, FinOps, resilience & DR |
| `sota-kubernetes` | Cluster platform security: RBAC & escalation, admission control, GitOps controllers, operators/CRDs, etcd, Helm supply chain, multi-tenancy, Talos/k3s |
| `sota-identity-access` | IdP ops (OIDC/SAML/SCIM), RBAC/ABAC/ReBAC design, joiner-mover-leaver, privileged access & break-glass, SPIFFE, phishing-resistant MFA |
| `sota-network-security` | Zero-trust & segmentation, NetworkPolicy depth, service mesh/mTLS, egress control, WAF/edge, DNS/TLS/PKI & cert lifecycle |
| `sota-detection-engineering` | Detection-as-code (Sigma/YARA/Falco), SIEM & telemetry coverage, alert tuning/SOAR, threat hunting & intel, deception, incident response |
| `sota-data-engineering` | Pipelines & orchestration, streaming/CDC, lakehouse & Parquet, data quality/contracts, governance |
| `sota-privacy-compliance` | Data inventory, privacy by design, consent & user rights, GDPR/CCPA/HIPAA/PCI/AI Act, SOC 2/ISO 27001, breach readiness |
| `sota-mobile` | Platform/stack choice, offline-first & push, mobile security, performance budgets, store releases |
| `sota-cli-ux` | Command/flag design, output & exit-code contracts, lifecycle behavior, distribution |
| `sota-shell-scripting` | Bash safety baseline, robustness, script security, CI/entrypoint/Makefile scripts |
| `sota-docs-workflow` | Documentation architecture, API docs & changelogs, code review/PR workflow, commits & releases |
| `sota-rust` | Ownership/API design, errors & panics, unsafe discipline, tokio, supply chain, performance, CI |
| `sota-golang` | Errors, package design, goroutine safety, net/http hardening, security, pprof, CI |
| `sota-python` | uv/ruff/typing, idioms, asyncio, security, performance, FastAPI/Django/pytest |
| `sota-javascript-typescript` | Strict TS, idioms, async, Node hardening, security, bundle/React performance, testing |

## Installation

Skills are discovered from `.claude/skills/` (per project) or
`~/.claude/skills/` (personal, all projects). Clone the repo, then run the
installer — it symlinks every skill (and your profile, if you have one):

```sh
git clone https://github.com/martinholovsky/SOTA-skills && cd SOTA-skills
./scripts/install.sh                 # personal: ~/.claude/skills (all projects)
./scripts/install.sh --project DIR   # one project: DIR/.claude/skills
./scripts/install.sh --copy          # copy instead of symlink (pin a snapshot)
```

Prefer no script? The personal install is just:

```sh
mkdir -p ~/.claude/skills
for d in skills/*/; do ln -sfn "$(pwd)/$d" ~/.claude/skills/"$(basename "$d")"; done
```

### Updating

Because install is symlink-based, **existing skills update the moment you pull**
— the symlinks already point at the live files, no re-install needed:

```sh
git -C /path/to/SOTA-skills pull
```

To also pick up **newly added** skills (a pull alone won't link a brand-new
skill directory) and prune links to removed ones, re-run the installer — or do
both at once:

```sh
./scripts/install.sh --update        # git pull --ff-only, then re-link
```

It's idempotent: re-running only links what's new and prunes what's gone, and
never touches symlinks it didn't create. (Snapshot installs done with `--copy`
don't auto-update — re-run the installer to refresh them.)

### Always-on routing (recommended)

Skill descriptions are matched per prompt, so routing is opt-in and depends on
how you phrase the request. To make the skills apply to **every** session
regardless of wording, pin the routing instruction where Claude Code always
sees it. Three layers, strongest last:

**1. A stack profile.** Copy the template, fill in your stack, and symlink it
into `~/.claude/` so the router finds it in every project (not just this repo):

```sh
cp profiles/example.md.template profiles/<you>.md   # edit it — profiles/*.md is git-ignored
mkdir -p ~/.claude/profiles
ln -sfn "$(pwd)/profiles/<you>.md" ~/.claude/profiles/<you>.md
```

**2. A global directive.** `~/.claude/CLAUDE.md` is loaded into every session,
every project. Add a routing mandate so the skills apply without trigger words:

```md
# Global engineering directive

For any task that builds, designs, refactors, debugs, reviews, or audits code —
in any language or repo — consult the `sota` router skill first, load the
matching `sota-*` skills, and apply their rules before acting. This holds even
when I never say "SOTA" or "audit". Treat `~/.claude/profiles/<you>.md` as the
BUILD default and AUDIT baseline. Validate claims against primary sources and
stop-and-ask on security-relevant choices.
```

**3. (Optional) A per-prompt reminder.** In long sessions a directive read many
turns ago can fade from context. A `UserPromptSubmit` hook in
`~/.claude/settings.json` re-injects it on every prompt:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command",
        "command": "echo 'Route code tasks through the sota router and apply the matching sota-* skills; the profile is the stack baseline.'" } ] }
    ]
  }
}
```

No mechanism *forces* a model to run a skill — all three layers feed it
instructions it then chooses to follow. Together they make routing reliable
instead of phrasing-dependent.

### Enforcing the gates

Routing makes the model *apply* the rules; to make them stick regardless of who
(or what) commits, wire them as git hooks. `scripts/init-gates.sh` generates a
SOTA-aligned `.pre-commit-config.yaml` for whatever languages it finds in the
target repo:

```sh
cd /path/to/your/project
/path/to/SOTA-skills/scripts/init-gates.sh        # add --dry-run to preview first
```

It detects Python / Go / Rust / JS-TS / shell by manifest and extension, then
writes the exact tools each skill prescribes — ruff·mypy·pytest·pip-audit,
gofumpt·golangci-lint·govulncheck, clippy·cargo-audit, eslint·tsc·`<pm> audit`,
shellcheck·shfmt, plus gitleaks everywhere. Fast checks (lint, format, secrets)
run on **commit**; heavy ones (type-check, tests, vuln scans) run on **push** —
the split `sota-python` rules/01 §6 and `sota-devsecops` rules/05 require, so
commits stay quick.

It is **idempotent**: re-run it after adding a language and it rewrites only the
block between its `# >>> sota-gates >>>` markers, leaving any hooks you added
yourself in place. The hooks call your project's own toolchain, so install the
per-language tools it lists on exit (and `pre-commit install` if the script
couldn't).

## How it works

Claude Code matches your prompt against each skill's frontmatter description
and loads what's relevant automatically — you don't have to name a skill.
Naming one (or the `sota` router) just makes the routing explicit. From there:

1. The skill's `SKILL.md` loads first (workflows, severity conventions, an
   index of its `rules/` files). Only the rules files matching your task are
   read — never the whole library.
2. **BUILD mode** applies the rules while writing code and self-checks the
   diff against each loaded rules file's Audit checklist before presenting it.
3. **AUDIT mode** hunts violations and reports findings as
   `file:line | rule | severity | effort | fix`. Full audits follow
   `sota/rules/01-audit-methodology.md` (scoping → inventory → tooling →
   per-domain passes → report with a prioritized roadmap).
4. If `profiles/<you>.md` exists, its stack choices are BUILD defaults and the
   AUDIT baseline (deviations get flagged).

## Prompt examples

**Building:**

> Design a multi-tenant invoicing service — follow sota. Postgres, FastAPI.

> Add a websocket endpoint for live notifications, following SOTA practices.
> (→ api-design rules/05 + async backpressure + auth-at-upgrade rules)

> Build the settings page with sota-frontend-design — needs dark mode and
> WCAG 2.2 AA.

> Add a RAG search feature over our docs — use sota-llm-engineering, and
> write the evals first.

> Scaffold the GitHub Actions pipeline for this repo per sota-devsecops:
> SHA-pinned actions, OIDC, SBOM + signing.

**Auditing:**

> Run a full SOTA audit of this repo. Static analysis only, audit the current
> commit, report per the audit methodology.

> Audit this PR against sota-code-security and sota-golang before I merge it.

> Sweep the repo and git history for secrets per sota-secrets-management.
> Rotate-first recommendations for anything you find.

> Threat-model this service from the code: DFD, trust boundaries, STRIDE —
> sota-threat-modeling rules/06.

> Audit our Kubernetes manifests and Dockerfiles with sota-sandboxing and
> sota-devsecops. Severity + effort on every finding.

> Why is checkout slow? Profile-first per sota-performance — no guessing.

> Review our agent's MCP setup against the named attack taxonomy in
> sota-code-security rules/08 (tool poisoning, rug pulls, shadowing).

**Scoped & cross-cutting:**

> Is this migration zero-downtime safe? Check against sota-databases
> rules/02 (expand/contract, lock-aware DDL).

> Review test suite health: flaky policy, coverage ratchets, speed budgets
> (sota-testing rules/07).

> We're adding a "delete my account" feature — what does
> sota-privacy-compliance require for deletion propagation and retention?

> Check this bash deploy script with sota-shell-scripting before it goes
> into CI.

**Maintaining the library:**

> Refresh the library against current versions/advisories — re-verify the
> fast-moving claims and update the rules files (cite sources).

> Create profiles/<name>.md for my stack: <stores, auth, platform, policies>.

> Add a new skill for <domain>, same structure: SKILL.md + rules/ under
> 500 lines each, claims web-verified.

## Usage tips

- **Say the mode if ambiguous** — "audit", "review", "harden" vs "build",
  "add", "design". The skills key off those verbs.
- **Scope audits explicitly**: which commit/branch, static-only or
  may-run-tools, time budget ("crown jewels only"). The methodology file
  stops and asks otherwise.
- **Ask for the report format you want** — by default a full audit produces
  executive summary → findings by severity → roadmap by
  risk-reduction-per-effort → positive observations.
- **Stack skills freely**: language + domain ("sota-rust + sota-api-design
  for this axum service"). The router does this automatically when you just
  describe the task.
- **Re-verify anything version-sensitive**: the library's pinned facts are
  as-of the last refresh date above; the freshness-first principle tells the
  model to web-check before pinning versions — hold it to that.

## Conventions

- Every rules file ends with an **Audit checklist** (yes/no questions, often
  with grep/lint patterns to hunt violations).
- Severity scale everywhere: **Critical** (exploitable/data loss) · **High**
  (fix this sprint) · **Medium** (bounded impact) · **Low** (hygiene) ·
  **Info** (observations, no direct risk). Each finding also carries an
  **effort** estimate (trivial/small/medium/large) so remediation can be
  sequenced by risk-reduction-per-effort.
- Each SKILL.md carries a **top-10 non-negotiables** list — apply these
  unconditionally; load detailed rules files only as the task demands.
- Borderline severities state the deciding assumption; unconfirmed findings
  are marked "needs verification", never asserted.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: keep skills generic,
verify fast-moving claims against primary sources, keep every file ≤ 500 lines,
and end each rules file with an audit checklist. These are enforced by
`scripts/check-invariants.sh` (pre-commit + CI) plus gitleaks. Security issues
and conduct: [SECURITY.md](SECURITY.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

© 2026 Martin Holovsky. Licensed under [CC BY 4.0](LICENSE) — Creative Commons
Attribution 4.0 International. Use, adapt, and share freely (including
commercially); just give attribution: *"SOTA Engineering Skills by Martin
Holovsky, CC BY 4.0."*

`profiles/` holds personal stack profiles and is git-ignored except
`profiles/example.md.template` — copy that to `profiles/<you>.md` and edit it;
your real profile stays local and is never committed.
