# AGENTS.md

Operational guidance for AI assistants (and humans) working **on** this repository. This
is the SOTA-skills library — Markdown skills that an AI assistant reads to build and
audit software. There is no application to run; changes are edits to Markdown held to a
few hard invariants. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full conventions.

This file is the single source of truth for every agent: tools that follow the
[AGENTS.md standard](https://agents.md) (Codex, Cursor, Copilot, …) read it directly,
while `CLAUDE.md` (Claude Code) and `GEMINI.md` (Gemini CLI) are symlinks to it — edit
only this file, never the symlinks.

## Landing a change

`main` is a protected branch and **direct pushes are rejected for everyone** (admin
enforcement is on). Every change goes through a pull request:

1. `git checkout -b <branch>`
2. make the edit, then run `./scripts/check-invariants.sh` (and optionally
   `pre-commit run --all-files`). `pre-commit install` sets up **both** stages —
   pre-push re-runs the invariants, the first moment the **diff-based** ones
   (11, 14) have a commit to read
3. push the branch and open a PR
4. all four required checks must pass, then squash-merge — invariants, secret scan,
   shell lint, and the negative-control harness that proves the gates can still fail

## Invariants (enforced in pre-commit and CI)

`scripts/check-invariants.sh` runs **19 checks** and fails the build on any of them. One
line each below. The *rationale* — and the real incident behind every one — lives in the
script's own header, at the point of use, and the practical "what this means for your
PR" version is in [CONTRIBUTING.md](CONTRIBUTING.md#the-invariants-enforced).

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
| 14 | a **release** (VERSION changed) carries no `**Front door checked:**` line in its CHANGELOG section, or a declared term is missing from `README.md`/`docs/INDEX.md` **or** from the release's own entry |
| 15 | the router's **library map** omits a `rules/NN` file that exists, or names one that doesn't — checks 7 and 10 both miss this, and `rules/11` went unlisted for two releases |
| 16 | the hook `README.md` **documents** differs from the one `install.sh` **writes** (`HOOK_CMD`) — the README's is what a reader copies by hand, so a stale block is the version that spreads |
| 17 | a document that **describes** the checks disagrees with them — a stated count that isn't the script's, or a restated negative-control coverage list that isn't the harness's. Counts inside `"quotes"` are read as history, not claims |
| 18 | a **`§` section reference** resolves nowhere — invariant 8 reads only `[text](file.md)` links, so ~1,300 prose references went unchecked and broke silently on any renumber or split |
| 19 | a **check has no known-bad** and no pinned reason it cannot — and the exempt set may not *grow*, since silencing the coverage check by exempting your new check is a one-line move. Runs on every invocation (~50 ms), not behind a flag |

**Only instruction files are capped** — a file is capped iff an agent loads it *as
instructions*: `skills/*/SKILL.md` and `skills/*/rules/*.md`, nothing else. README,
CHANGELOG, `docs/`, `evals/`, this file and every script are **uncapped**,
deliberately (decided 2026-07-15) — navigability there comes from a table of contents
and [docs/INDEX.md](docs/INDEX.md), not a ceiling. **A line-cap claim anywhere that
does not say *skill files* is stale — fix it.** The 500 matches the Agent Skills
guidance (*"keep `SKILL.md` under 500 lines; move detailed reference material to
separate files"*), and `rules/*.md` are exactly those separate files.

**This file is the exception.** `CLAUDE.md` and `GEMINI.md` symlink here, so it loads
into **every** session, where the platform's guidance is *"target under 200 lines"* —
long always-loaded files reduce adherence. Ungated, and a different constraint from
invariant 1. Keep it under 200: detail goes to `CONTRIBUTING.md` behind a pointer.

**Every file-list-driven check reports its denominator** (`ok (261 rules files)`) and
**fails closed on an empty scope** — `0 checked, 0 failed, exit 0` is the signature of a
gate that verifies nothing (`sota-code-security` rules/11 §2.2). Added 2026-07-30 after
checks 2 and 10 printed `ok` over *zero* files; 4 and 8 were only retrofitted
2026-08-16, so this very sentence was false for a while in the one file that states the
rule. If you add a check that is a promise you must keep, and the script's header
carries the three rules the lesson produced: watch it fail first, print your
denominator, skip rather than guess.

*Adding a `rules/NN` file?* Invariant 10 checks its own `SKILL.md` indexes it and
**invariant 15** checks the router's library map lists it, both directions — that
map went unchecked long enough for `rules/11` to sit unlisted for two releases.
`skills/sota/SKILL.md` is at **499/500** (re-counted 2026-08-29); `rules/01` split into 01 (process) +
03 (findings) on 2026-08-29, the same move as 2026-08-26's BUILD/AUDIT offload: **detail belongs in
`rules/`, imperatives in the router.** This count has been wrong **five** times — **re-count with `grep -c ''`**.
Editing the router's **BUILD section** moves `ROUTER_BUILD_SHA` and aborts the evals; AUDIT does not.
The gates enumerate via `git ls-files`, so an **unstaged new file is invisible** to
them — `git add` before believing a count.

**`scripts/check-negative-controls.sh` proves our gates can still fail.** Its CI job runs
it plus `evals/smoke-runners.py`, over **two** subjects: `check-invariants.sh` (part A) and `verify-setup.sh`
(part B). Each probe injects a known-bad and requires *the intended check* to be the one
that complains — a non-zero exit for any other reason is a **FALSE PASS**, not a catch.
Part A mutates a good tree in a disposable git worktree; part B is inverted, building a
fully-configured fake machine (`CLAUDE_CONFIG_DIR` + throwaway repo + stub `gh`) and
removing one thing per probe. **25 probes** (re-run 2026-09-01: `PASS: 25/25`; wrong twice
before, and deliberately **not** gated — a static count of call sites under-reads, so only
running it is authoritative): invariants **1, 2, 3, 4, 6, 7, 8, 10, 13, 15, 16,
17, 18, 19** — 14 of 19 — and verify-setup checks 1, 2, 3, 4, 6a, 6b, 7, 8, 9, 9a, 10a. The five
unprobed invariants (5, 9, 11, 12, 14) need state a worktree lacks (a tag, a merge base,
an mtime); the harness prints that reason, so what is *not* covered is printed rather than
implied. **A probe asserts its own mutation landed** — they are hardcoded literals, and a
stale one printed `NOT CAUGHT: INERT`, accusing a healthy gate.
Adding a check? **Invariant 19 already enforces that it has a known-bad** — nothing to
remember. `--self-test` runs the suite and then this harness.

Separately, `scripts/check-freshness.sh` (run monthly by
`.github/workflows/freshness.yml`) tracks the root `LAST-VERIFIED` stamp — the date
of the last full-library re-verification sweep against primary sources. Update it
only after such a sweep; the run goes red past the **6-month** window. Per-file
line-1 markers are retired. Sweep runbook and eval harness:
[docs/MAINTENANCE.md](docs/MAINTENANCE.md) and [evals/](evals/).

Secrets are scanned by **gitleaks** (`.gitleaks.toml`, which disables only the
noisy entropy-based `generic-api-key` rule so the security skills' intentional
secret-shaped examples don't false-positive). CI scans the **full git history**
(`gitleaks git` on a `fetch-depth: 0` checkout), not just the working tree, and
**asserts that scope**: a shallow checkout scans 1 commit, reports "no leaks
found", and exits 0, so the workflow fails on a shallow clone rather than trusting
the setting. The pre-commit hook scans each commit locally.

## Conventions that matter

- **Keep it generic.** Never commit personal or company-specific stacks or project
  names, and never phrase guidance as an assumption about the reader's setup. Products
  appear only as neutral examples ("e.g. PostgreSQL").
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
  ledger**: every idea from an outside repo, paper or review, with a verdict and
  reason (adopted / adopted-with-a-correction / rejected / deferred / superseded).
  A recorded rejection stops the idea being re-litigated; `rejected: already
  covered` must cite the file:line that covers it. Intake is not only external —
  a session *applying* the library, and an unlicensed source whose ideas can be
  taken but whose text cannot, both land here on the same terms
- [docs/CONVENTIONS-LEDGER.md](docs/CONVENTIONS-LEDGER.md) — which of this repo's
  conventions are **enforced** (19 invariants + 9 more inside the eval runners) and
  which are prose, with the three filters a convention must pass to earn a gate
  (has it already failed · does it fail silently · is it mechanically checkable).
  Read it before proposing a new gate — it argues against gating the ~18 judgment
  conventions, because a flaky gate gets disabled and leaves you worse off
- [CONTRIBUTING.md](CONTRIBUTING.md) — full contribution guide and PR checklist
- [RELEASING.md](RELEASING.md) — how to cut a release, including every
  version- and count-bearing surface (README, router, manifests, social
  preview)
- [docs/MAINTENANCE.md](docs/MAINTENANCE.md) — accuracy sweep runbook + eval harness
- [docs/WHY-IT-WORKS.md](docs/WHY-IT-WORKS.md) — the measured-efficacy case
  (lift **vs. an unguided model**, plus a scoped head-to-head vs. named competing
  libraries) + the design
  benefits; keep its numbers in sync with the eval results when they change
- [docs/WHY-COMPLETENESS-RESIDUAL.md](docs/WHY-COMPLETENESS-RESIDUAL.md) — why a
  with-library build still drops a cross-cutting rule now and then (a salience /
  context-length attention effect, **not** a coverage gap) + the counter-design
- [SECURITY.md](SECURITY.md) — reporting bad guidance or a leaked secret
- [CHANGELOG.md](CHANGELOG.md) — release history (top entry = current version;
  also mirrored in `VERSION`); older releases are archived to keep every file
  for navigability (CHANGELOG is no longer line-capped, so archiving is now
  optional hygiene, not forced): **1.10.0–1.5.0** in
  [docs/CHANGELOG-archive.md](docs/CHANGELOG-archive.md) and **1.4.0 and earlier**
  in [docs/CHANGELOG-archive-2.md](docs/CHANGELOG-archive-2.md)
