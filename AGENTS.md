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

`scripts/check-invariants.sh` runs **13 checks** and fails the build on any of
them. One line each below. The *rationale* — and the real incident behind every
one — lives in the script's own header, at the point of use, and the practical
"what this means for your PR" version is in
[CONTRIBUTING.md](CONTRIBUTING.md#the-invariants-enforced).

| # | The build fails when… |
|---|---|
| 1 | a **skill** file (`skills/*/SKILL.md`, `skills/*/rules/*.md`) exceeds **500 lines** |
| 2 | a `skills/*/rules/*.md` doesn't end with `## Audit checklist` |
| 3 | an internal-name denylist hits (the library must stay generic) |
| 4 | a `SKILL.md` `description` exceeds **1024 chars** (spec cap — loaders silently skip it), is unquoted YAML containing `: `, or either `name`/`description` contains an **XML tag**; also a reserved word (`anthropic`, `claude`) in `name` |
| 5 | `VERSION`, `plugin.json` and the CHANGELOG top entry disagree, or a tag is ahead of `VERSION` |
| 6 | a count-bearing surface drifts from a recount of `skills/` (the social-preview pill and README alt are **"N+" floors**) |
| 7 | a skill is missing from the router's routing table **or** its library map |
| 8 | a relative Markdown link to a `*.md` target doesn't resolve |
| 9 | `CHANGELOG.md` carries more than one `## [Unreleased]`, or it isn't the top entry |
| 10 | a `rules/*.md` isn't referenced by its own `SKILL.md` — written, capped, checklist-ed, and never loaded |
| 11 | `LAST-VERIFIED` moves without a sweep. Escapes: a sweep-shaped diff (≥ 20 skill files) or naming it in the CHANGELOG. The only **diff-based** check; skips with a note when there's no merge base |
| 12 | an `assets/*.png` is older than the `*.html` it renders — the README embeds the *image*, never the source, so an un-rendered fix reaches nobody. Escape: `[no-render]` in the commit subject |
| 13 | a scoreboard row in `evals/results/RESULTS.md` leaves its `Samples` cell empty |

**Only instruction files are capped.** A file is capped if and only if an agent
loads it *as instructions* — `skills/*/SKILL.md` and `skills/*/rules/*.md`, and
nothing else in the repo. README, CHANGELOG, `docs/`, `evals/`, this file and every
script are **uncapped** and deliberately so (decided 2026-07-15): navigability there
comes from a table of contents and [docs/INDEX.md](docs/INDEX.md), not a line
ceiling. **If you find a line-cap claim anywhere that does not say *skill files*, it
is stale — fix it.** The 500 matches the Agent Skills guidance (*"keep `SKILL.md`
under 500 lines; move detailed reference material to separate files"*), and those
separate files are exactly what `rules/*.md` are.

**This file is the exception that proves it.** `CLAUDE.md` and `GEMINI.md` symlink
here, so this file loads into **every** session — the platform's guidance is to
*"target under 200 lines per CLAUDE.md file"*, because long always-loaded files
reduce adherence. That is a different constraint from invariant 1 and is not gated.
Keep it under 200: put detail in `CONTRIBUTING.md` and leave a pointer.

**Every file-list-driven check reports its denominator** (`ok (256 rules files)`)
and **fails closed on an empty scope**. Added 2026-07-30 after a mutation showed
checks 2 and 10 printing `ok` — and the script exiting 0 — while examining *zero*
files. `0 checked, 0 failed, exit 0` is the signature of a gate that verifies
nothing (`sota-code-security` rules/11 §2.2). Adding a check? The script's header
carries the three rules that file learned the hard way: watch it fail first, print
your denominator, and skip rather than guess.

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
(`gitleaks git` on a `fetch-depth: 0` checkout), not just the working tree, and
**asserts that scope**: a shallow checkout scans 1 commit, reports "no leaks
found", and exits 0, so the workflow fails on a shallow clone rather than trusting
the setting. The pre-commit hook scans each commit locally.

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

- [docs/INDEX.md](docs/INDEX.md) — **find-it-fast index**: where every topic is
  documented, organized by what you're trying to do (start here if lost)
- [docs/CONTEXT-MANAGEMENT.md](docs/CONTEXT-MANAGEMENT.md) — how the library keeps
  the model applying rules as context fills (re-injection hook, principle 5,
  terminal re-read, gates) + the decay measurement
- [evals/results/RESULTS.md](evals/results/RESULTS.md) — consolidated scoreboard of
  every measured number
- [evals/README.md](evals/README.md) — the efficacy harness: what each case set
  measures, how to run it, and the **harness conventions** (guards abort rather than
  warn; watch a guard fail before trusting it; wait on a terminal artifact, not a log
  substring; assert a scripted edit landed; pin anything hand-mirrored from the
  library). Read it before changing anything under `evals/` — four harness changes in
  one day silently measured nothing while still printing plausible numbers
- **The read-only setup check, in two halves** — `init-gates.sh` sets a repo up;
  these check the result, because "configured" and "working" render identically.
  `scripts/verify-setup.sh` does the mechanical half (skills reachable, hook
  installed vs merely configured, licence under any name, whether CI has ever
  *executed* and ever *rejected* — `--runs N` widens that sample);
  [docs/VERIFY-SETUP.md](docs/VERIFY-SETUP.md) is the paste-in prompt for the half
  a script cannot do — whether the agent file's content is meaningful and whether
  its claims are still *true*
- [docs/ADOPTION-LOG.md](docs/ADOPTION-LOG.md) — the **external-idea intake
  ledger**: every idea evaluated from an outside repo, paper, or review with a
  verdict and reason (adopted / rejected / deferred / superseded). A rejection
  with its reason stops the same idea being re-litigated; a `rejected: already
  covered` verdict must cite the file:line that covers it. **Adoptions do not
  only come from outside**: at v1.19.9 a separate agent session applying the
  library handed back three proposals citing this repo's own `file:line` — the
  ledger takes those on the same terms, rejections included
- [docs/CONVENTIONS-LEDGER.md](docs/CONVENTIONS-LEDGER.md) — which of this repo's
  conventions are **enforced** (13 invariants + 4 more inside the eval runners) and
  which are prose, with the three filters a convention must pass to earn a gate
  (has it already failed · does it fail silently · is it mechanically checkable).
  Read it before proposing a new gate — it argues against gating the ~18 judgment
  conventions, because a flaky gate gets disabled and leaves you worse off
- [CONTRIBUTING.md](CONTRIBUTING.md) — full contribution guide and PR checklist
- [RELEASING.md](RELEASING.md) — how to cut a release, including every
  version- and count-bearing surface (README, router, manifests, social
  preview)
- [docs/MAINTENANCE.md](docs/MAINTENANCE.md) — accuracy sweep runbook +
  eval harness (keeping fast-moving claims true and measuring efficacy)
- [docs/WHY-IT-WORKS.md](docs/WHY-IT-WORKS.md) — the measured-efficacy case
  (lift **vs. an unguided model**, plus a scoped head-to-head vs. named competing
  libraries) + the design
  benefits; keep its numbers in sync with the eval results when they change
- [docs/WHY-COMPLETENESS-RESIDUAL.md](docs/WHY-COMPLETENESS-RESIDUAL.md) — why a
  with-library build still occasionally drops a cross-cutting rule (a salience /
  context-length attention effect, **not** a coverage gap) and the BUILD-workflow
  design that counters it
- [SECURITY.md](SECURITY.md) — reporting bad guidance or a leaked secret
- [CHANGELOG.md](CHANGELOG.md) — release history (top entry = current version;
  also mirrored in `VERSION`); older releases are archived to keep every file
  for navigability (CHANGELOG is no longer line-capped, so archiving is now
  optional hygiene, not forced): **1.10.0–1.5.0** in
  [docs/CHANGELOG-archive.md](docs/CHANGELOG-archive.md) and **1.4.0 and earlier**
  in [docs/CHANGELOG-archive-2.md](docs/CHANGELOG-archive-2.md)
