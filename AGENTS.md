# AGENTS.md

Operational guidance for AI assistants (and humans) working **on** this
repository. This is the SOTA-skills library — Markdown skills that an AI
assistant reads to build and audit software. There is no application to run;
changes are edits to Markdown held to a few hard invariants. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the full conventions.

This file is the single source of truth for every agent: tools that follow
the [AGENTS.md standard](https://agents.md) (Codex, Cursor, Copilot, …) read
it directly, while `CLAUDE.md` (Claude Code) and `GEMINI.md` (Gemini CLI) are
symlinks to it — edit only this file, never the symlinks.

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
2. any `skills/*/rules/*.md` whose **last `## ` heading isn't
   `## Audit checklist`** (the checklist must end the file);
3. an **internal-name denylist** — the library must stay generic. The private
   patterns are deliberately untracked (git-ignored `.denylist.local` locally,
   `SOTA_DENYLIST` secret in CI); without them only the generic
   reader-assumption phrases are checked, e.g. on external fork PRs;
4. any `skills/*/SKILL.md` **`description` over 1024 characters** — the Agent
   Skills spec cap; loaders silently skip a skill whose description exceeds it
   — or an unquoted inline description containing `: ` (invalid YAML; strict
   loaders reject the skill — use `description: >-`).
   (Needs `python3`; skipped with a warning if absent locally, enforced in CI.)
5. **version drift** — `VERSION`, `plugin.json` `"version"`, and the CHANGELOG
   top entry must agree, and the newest `v*` tag must never be ahead of
   `VERSION` (it may lag during an open release PR);
6. **count drift** — the README badge/hero, the router body's "N domain
   skills", and the plugin + marketplace descriptions must match a recount of
   the `skills/` tree; the social-preview pill and README alt are **"N+"
   floors** (they fail only if the tree count drops below the floor), so the
   PNG is not re-rendered per release.
7. **router drift** — every domain skill must appear in the router's routing
   table AND its library map (both in `skills/sota/SKILL.md`); a skill added
   to one but not the other is a finding (added after the 2026-07-10 audit
   found the 41st skill missing from the map for a full release).

Separately, `scripts/check-freshness.sh` (run monthly by
`.github/workflows/freshness.yml`) tracks the root `LAST-VERIFIED` stamp —
the date of the last full-library re-verification sweep against primary
sources. Update it only after such a sweep; the run goes red when the stamp
exceeds the **6-month** window. Per-file line-1 markers are retired. The
sweep runbook and the efficacy eval harness live in
[docs/MAINTENANCE.md](docs/MAINTENANCE.md) and [evals/](evals/).

Secrets are scanned by **gitleaks** (`.gitleaks.toml`, which disables only the
noisy entropy-based `generic-api-key` rule so the security skills' intentional
secret-shaped examples don't false-positive). CI scans the **full git history**
(`gitleaks git` on a `fetch-depth: 0` checkout), not just the working tree; the
pre-commit hook scans each commit locally.

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
- **No rot-prone version pins.** Skills never claim "the current release is
  X.Y" — write "latest stable" and tell the reader to verify at the official
  source. Version numbers mark **semantic boundaries only** ("GA since",
  "introduced/fixed/removed in", CVE fix versions, spec editions). When a
  recommended tool goes EOL/unmaintained, replace it with the maintained
  successor (project-recommended target first, then CNCF), keeping a one-line
  EOL note for auditors. (Policy since the 2026-07-08 freshness sweep.)
- **Skill anatomy.** `skills/sota-<domain>/SKILL.md` (two-field frontmatter —
  `name` + `description`; BUILD/AUDIT workflows; top-10 non-negotiables; a rules
  index) plus `rules/NN-topic.md` files, each ≤ 500 lines and ending in an
  `## Audit checklist`. Audit findings use the format
  `file:line | rule | severity | effort | fix`.

## Pointers

- [CONTRIBUTING.md](CONTRIBUTING.md) — full contribution guide and PR checklist
- [RELEASING.md](RELEASING.md) — how to cut a release, including every
  version- and count-bearing surface (README, router, manifests, social
  preview)
- [docs/MAINTENANCE.md](docs/MAINTENANCE.md) — accuracy sweep runbook +
  eval harness (keeping fast-moving claims true and measuring efficacy)
- [docs/WHY-IT-WORKS.md](docs/WHY-IT-WORKS.md) — the measured-efficacy case
  (lift **vs. an unguided model**, not vs. other libraries) + the design
  benefits; keep its numbers in sync with the eval results when they change
- [docs/WHY-COMPLETENESS-RESIDUAL.md](docs/WHY-COMPLETENESS-RESIDUAL.md) — why a
  with-library build still occasionally drops a cross-cutting rule (a salience /
  context-length attention effect, **not** a coverage gap) and the BUILD-workflow
  design that counters it
- [SECURITY.md](SECURITY.md) — reporting bad guidance or a leaked secret
- [CHANGELOG.md](CHANGELOG.md) — release history (top entry = current version;
  also mirrored in `VERSION`); older releases are archived to keep every file
  under the 500-line cap — **1.10.0–1.5.0** in
  [docs/CHANGELOG-archive.md](docs/CHANGELOG-archive.md) and **1.4.0 and earlier**
  in [docs/CHANGELOG-archive-2.md](docs/CHANGELOG-archive-2.md) (split 2026-07-14);
  when an archive nears 500, start the next numbered part rather than growing it
