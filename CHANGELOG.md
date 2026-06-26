# Changelog

All notable changes to SOTA-skills are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`scripts/statusline.sh`** — a Claude Code status line showing which skills
  you've actually used this session (read from the transcript's `Skill`
  invocations), plus model / context % / dir / branch; falls back to the count
  of installed skills before any are used. Requires `jq`.

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

[1.2.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.2.0
[1.1.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.1.0
[1.0.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.0.0
