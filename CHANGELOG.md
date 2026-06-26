# Changelog

All notable changes to SOTA-skills are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.1.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.1.0
[1.0.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.0.0
