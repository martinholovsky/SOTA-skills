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

1. any **skill** Markdown (`skills/*/SKILL.md` or `skills/*/rules/*.md`) over
   **500 lines** — the cap is load-bearing only there (it keeps incremental
   loading working; the model reads the rules that match the task, not a wall of
   text). Non-skill Markdown (README, CHANGELOG, `docs/`) is human/agent-facing
   prose, **not** loaded as a skill, so it is intentionally **uncapped** (decided
   2026-07-15) — navigability there comes from a table of contents and
   [docs/INDEX.md](docs/INDEX.md), not a line ceiling;
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
8. **link rot** — every relative Markdown link to a `*.md` target (in any
   tracked `*.md`) must resolve to a file that exists, so a moved/renamed file
   can't leave a dead link in the README, `docs/`, CHANGELOG, or a skill.
   Scoped to `*.md` targets (non-`.md` relative links overlap `[text](x)`-shaped
   prose/code and false-positive); needs `python3`, skipped-with-warning if
   absent locally, enforced in CI. Adopted 2026-07-24 from the
   training-knowledge-vault vault-doctor — see [docs/ADOPTION-LOG.md](docs/ADOPTION-LOG.md).
9. **duplicate `[Unreleased]`** — `CHANGELOG.md` carries at most one
   `## [Unreleased]` heading and it must be the topmost entry; the archives
   carry none. Invariant 5 reads only the *first* `## [` heading, so a second
   `[Unreleased]` further down was invisible to CI: on 2026-07-28 two feature
   PRs each opened one above `[1.19.3]` and `main` carried both until a human
   noticed during the release cut. Fence-aware, so a heading quoted inside a
   code block doesn't count.
10. **unindexed rules file** — every `skills/*/rules/*.md` must be referenced by
    its own `SKILL.md`. The model reads only the rules files the index points at,
    so an unindexed one is written, capped, checklist-ed — and never loaded. It is
    the skill-level twin of invariant 7 (a skill missing from the router) and the
    same class as `sota-devsecops` rules/03 §3.9, turned on ourselves. Invariant 8
    does **not** cover it: **30 of 41** `SKILL.md` files list their rules as
    plain backticked text rather than Markdown links, so a rename leaves nothing
    for the link checker to resolve (measured 2026-07-30). All 255 rules files
    passed when this landed — it is a regression gate, watched to fail on an
    injected file and on a renamed reference first.

**Every file-list-driven check reports its denominator** (`ok (255 rules files)`)
and **fails closed on an empty scope**. Added 2026-07-30 after a mutation showed
checks 2 and 10 printing `ok` — and the script exiting 0 — while examining *zero*
files, because the `skills/*/rules/*.md` pathspec had been made to match nothing;
invariant 6's tree recount did not catch it, since the `SKILL.md` count it
recounts was unaffected. `0 checked, 0 failed, exit 0` is the signature of a gate
that verifies nothing (`sota-code-security` rules/11 §2.2).

11. **`LAST-VERIFIED` moves only with a sweep** — the stamp records the last
    *full* re-verification pass, not the newest verified fact, so a rules section
    may carry today's verification dates while the stamp is months old. Bumping it
    on an ordinary edit asserts a sweep that never happened, planting a false green
    in the one control whose job is detecting stale claims. Two escapes, matching
    the batched and rolling passes [docs/MAINTENANCE.md](docs/MAINTENANCE.md)
    allows: a **sweep-shaped diff** (≥ 20 skill files — the real 2026-07-08 sweep
    touched **100**), or **naming `LAST-VERIFIED` in the CHANGELOG**, which the
    runbook already requires. Added 2026-07-31 after the rule — already written in
    three places — was still nearly broken twice: a convention that keeps almost
    failing is `sota-code-security` rules/10 §2.12, an instruction standing in for
    an enforced control. This is the first **diff-based** invariant; with no merge
    base it skips with a note rather than guessing.

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
- [docs/VERIFY-SETUP.md](docs/VERIFY-SETUP.md) — the **read-only setup check**: a
  paste-in prompt that reports whether the library reaches a repo, whether its
  agent file is *true*, and whether its gates are real rather than merely
  configured. `init-gates.sh` sets a repo up; this is what checks the result
- [docs/ADOPTION-LOG.md](docs/ADOPTION-LOG.md) — the **external-idea intake
  ledger**: every idea evaluated from an outside repo, paper, or review with a
  verdict and reason (adopted / rejected / deferred / superseded). A rejection
  with its reason stops the same idea being re-litigated; a `rejected: already
  covered` verdict must cite the file:line that covers it. **Adoptions do not
  only come from outside**: at v1.19.9 a separate agent session applying the
  library handed back three proposals citing this repo's own `file:line` — the
  ledger takes those on the same terms, rejections included
- [docs/CONVENTIONS-LEDGER.md](docs/CONVENTIONS-LEDGER.md) — which of this repo's
  conventions are **enforced** (11 invariants + 4 more inside the eval runners) and
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
