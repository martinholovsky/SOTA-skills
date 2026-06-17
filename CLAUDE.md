# CLAUDE.md

Operational guidance for AI assistants (and humans) working **on** this
repository. This is the SOTA-skills library — Markdown skills that an AI
assistant reads to build and audit software. There is no application to run;
changes are edits to Markdown held to a few hard invariants. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the full conventions.

## Landing a change

`main` is a protected branch and **direct pushes are rejected for everyone**
(admin enforcement is on). Every change goes through a pull request:

1. `git checkout -b <branch>`
2. make the edit, then run `./scripts/check-invariants.sh`
   (and optionally `pre-commit run --all-files`)
3. push the branch and open a PR
4. both required checks must pass, then squash-merge

## Invariants (enforced in pre-commit and CI)

`scripts/check-invariants.sh` fails the build on:

1. any tracked `*.md` over **500 lines**;
2. any `skills/*/rules/*.md` missing an **`## Audit checklist`** heading;
3. an **internal-name denylist** — the library must stay generic.

Secrets are scanned by **gitleaks** (`.gitleaks.toml`, which disables only the
noisy entropy-based `generic-api-key` rule so the security skills' intentional
secret-shaped examples don't false-positive).

## Conventions that matter

- **Keep it generic.** Never commit personal or company-specific stacks or
  project names, and never phrase guidance as an assumption about the reader's
  setup. Products appear only as neutral examples ("e.g. PostgreSQL").
  Personalization lives in a local `profiles/<you>.md`, which is git-ignored
  (`profiles/*` except `profiles/example.md.template`) and must never be
  committed.
- **Verify claims.** Fast-moving facts (versions, specs, advisories) are checked
  against a primary source and cited; uncertain items are marked
  "needs verification", never asserted.
- **Skill anatomy.** `skills/sota-<domain>/SKILL.md` (two-field frontmatter —
  `name` + `description`; BUILD/AUDIT workflows; top-10 non-negotiables; a rules
  index) plus `rules/NN-topic.md` files, each ≤ 500 lines and ending in an
  `## Audit checklist`. Audit findings use the format
  `file:line | rule | severity | effort | fix`.

## Pointers

- [CONTRIBUTING.md](CONTRIBUTING.md) — full contribution guide and PR checklist
- [SECURITY.md](SECURITY.md) — reporting bad guidance or a leaked secret
- [CHANGELOG.md](CHANGELOG.md) — release history (current: v1.0.0)
