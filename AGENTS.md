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
   (11, 14) have a commit to read. **Neither runs CI's other steps**: touched a skill file?
   `python3 scripts/gen-skill-map.py` and commit any diff, or CI's skill-map check goes red
3. push the branch and open a PR
4. **every** required check must pass, then squash-merge — invariants, secret scan, shell
   lint, executable claims, and the negative-control harness that proves the gates can
   still fail. The count is deliberately not written here: it rotted once when a job was
   added and never made required, so read it from
   `gh api repos/OWNER/REPO/branches/main/protection --jq '.required_status_checks.contexts'`

## Invariants (enforced in pre-commit and CI)

`scripts/check-invariants.sh` runs **36 checks** and fails the build on any of them. One line
each — with the real incident behind every one — in **[docs/INVARIANTS.md](docs/INVARIANTS.md)**,
offloaded out of this file on 2026-09-13 because each new invariant cost a line of the
always-loaded budget and the cap had been breached by an invariant's own table row — twice landing at 201 and 202, and hitting exactly 200 twice more while editing this session. **The precise total is not recoverable from git**, because the gate catches a breach pre-commit so it never lands; what is recoverable is that every one was a table row. Read it before changing a gate. The
full *rationale* lives at the point of use in the script's own header; the practical "what this
means for your PR" version is in [CONTRIBUTING.md](CONTRIBUTING.md#the-invariants-enforced).

**Only instruction files are capped** — a file is capped iff an agent loads it *as instructions*:
`skills/*/SKILL.md` and `skills/*/rules/*.md`, nothing else. README, CHANGELOG, `docs/`, `evals/`
and every script are **uncapped**, deliberately (2026-07-15) — navigability there comes from
[docs/INDEX.md](docs/INDEX.md), not a ceiling. **A line-cap claim anywhere that does not say
*skill files* is stale — fix it.** The 500 matches the Agent Skills guidance (*"keep `SKILL.md`
under 500 lines; move detailed reference material to separate files"*) — `rules/*.md` are those.
**This file is the exception**: `CLAUDE.md`/`GEMINI.md` symlink here, so it loads into **every**
session, where the guidance is *"target under 200 lines"* — long always-loaded files reduce
adherence. Keep it under 200 (**re-check with `awk 'END{print NR}'` each cut** — breached only ever by an invariant's
own table row, which is why that table now lives in `docs/INVARIANTS.md`), detail to `CONTRIBUTING.md`.

**Every file-list-driven check reports its denominator** (`ok (N rules files)`) and **fails
closed on an empty scope** — `0 checked, 0 failed, exit 0` is the signature of a gate that
verifies nothing (`sota-code-security` rules/11 §2.2). Added 2026-07-30 after checks 2 and 10
printed `ok` over *zero* files; 4 and 8 were retrofitted only on 2026-08-16, so this sentence was
itself false for a while. The script's header carries the three rules it produced: **watch it
fail first, print your denominator, skip rather than guess.**

*Adding a `rules/NN` file?* Invariant 10 checks its `SKILL.md` indexes it, **invariant 15** that
the library map (`skills/sota/rules/04`) lists it — both directions. `skills/sota/SKILL.md` is at
**under 500 — `grep -c '' skills/sota/SKILL.md` before you assume headroom.** The number used to be
written here and was wrong **nine times**, including twice in one day and once in this very sentence,
whose two halves disagreed with each other. It is deleted rather than corrected: a figure that rots on
every edit, in a file loaded into every session, with a one-command source of truth, is pure liability.
**Detail belongs in `rules/`, imperatives in the router.**
Editing the router's **BUILD section** moves `ROUTER_BUILD_SHA` and aborts the evals; AUDIT does not. The
gates enumerate via `git ls-files`, so an **unstaged new file is invisible** — `git add` first.

**`scripts/check-negative-controls.sh` proves our gates can still fail.** Its CI job runs it plus
`evals/smoke-runners.py` over **two** subjects — `check-invariants.sh` (part A) and
`verify-setup.sh` (part B). Each probe injects a known-bad and requires *the intended check* to
complain; any other non-zero exit is a **FALSE PASS**. **It reads the COMMITTED tree**
(`git worktree add HEAD`) — commit first, or you test a new script against old docs. Part A mutates
a good tree in a disposable worktree; part B is inverted, building a fully-configured fake machine
(`CLAUDE_CONFIG_DIR` + throwaway repo + stub `gh`) and removing one thing per probe. **69 probes** (`PASS: 69/69` on a small-diff branch, measured 2026-09-25; it said 67, 63, 62, 61, 53, 52, 49, 44 and 43 before that. Counting the log's `  [` lines gives **71**: the extra two are the per-part **positive controls**, not probes — read the harness's own total. **A sweep-shaped branch legitimately runs fewer**: invariant 11's probes need a non-sweep diff, so they skip with a printed reason and the total should read `66/66` plus a `NOTE:` naming the skipped invariant (derived: 69 minus invariant 11's 3 probes, not yet observed on a sweep branch; the NOTE itself was measured 2026-09-23 at 53 changed skill files). A number below 69 is not a regression if that NOTE is present)
(deliberately **not** gated — a static count of call sites under-reads, so only running it is
authoritative): invariants **1, 2, 3, 4, 6, 7, 8, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,
24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36** — 33 of 36 — and verify-setup checks 1, 1c, 1d, 2, 3, 4, 6a, 6b, 7, 8, 9, 9a, 10a, 13.
Only **5, 9, 12** are unprobed, needing a tag or an mtime, and the harness prints that reason. *A
diff-based check is not unprobeable*: 11 and 14 were exempt on that false ground until a probe
**committed** its mutation (2026-09-09). **A probe asserts its own mutation landed** (a stale
literal once printed `NOT CAUGHT: INERT`, accusing a healthy gate) and a catch for the wrong
reason is refused — probe 21 was a FALSE PASS on its first draft. Adding a check? **Invariant 19
already enforces that it has a known-bad.** `--self-test` runs the suite and then this harness.

Separately, `scripts/check-freshness.sh` (run monthly by `.github/workflows/freshness.yml`)
tracks the root `LAST-VERIFIED` stamp — the date of the last full-library re-verification sweep
against primary sources. Update it only after such a sweep; the run goes red past the **6-month**
window. Per-file line-1 markers are retired. The same job also reads `evals/ROUTING-BASELINE`
(**3-month** window — model releases, not fact rot, are what age it): routing is the one
measurement that can regress with **no diff here**, because the classifier is a model ranking
42 competing descriptions. The measurement is **deliberately local** — **CI** holds no API key and only
compares a date — so refresh it with `scripts/routing-baseline.sh`. A maintainer's working
tree usually *does* have one: every runner reads `OPENROUTER_API_KEY` from the environment or
`./.env` (gitignored, never committed). Read as "this repo has no key" the sentence stops a
local re-run that is actually available — which happened twice on 2026-09-22. Sweep runbook and eval harness:
[docs/MAINTENANCE.md](docs/MAINTENANCE.md) and [evals/](evals/).

Secrets are scanned by **gitleaks** (`.gitleaks.toml` disables only the noisy
entropy-based `generic-api-key` rule, so the security skills' intentional
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
- **The read-only setup check, in two halves** — `init-gates.sh` sets a repo up; these check the
  result, because "configured" and "working" render identically. `scripts/verify-setup.sh` does the
  mechanical half (skills **and slash commands** reachable **vs the checkout's own count** — a `git pull` refreshes
  existing links and creates none, so a newly added one stays silently uninstalled, whether their descriptions fit the listing budget or arrive name-only, hook installed vs merely
  configured, licence under any name, whether CI ever *executed* and ever *rejected*, and **§F: what
  your searcher silently skips** — behavioural, INFO-only, the positive control the one thing that
  can fail; `--runs N` widens the CI sample, `--reach-only` is what `install.sh` runs, `--no-color` forces the
  plain rows that part B's probes match on);
  [docs/VERIFY-SETUP.md](docs/VERIFY-SETUP.md) is the paste-in prompt for the half a script cannot
  do — whether the agent file's content is meaningful and whether its claims are still *true*
- [docs/ADOPTION-LOG.md](docs/ADOPTION-LOG.md) — the **external-idea intake
  ledger**: every idea from an outside repo, paper or review, with a verdict and
  reason (adopted / adopted-with-a-correction / rejected / deferred / superseded).
  A recorded rejection stops the idea being re-litigated; `rejected: already
  covered` must cite the file:line that covers it. Intake is not only external —
  a session *applying* the library, and an unlicensed source whose ideas can be
  taken but whose text cannot, both land here on the same terms
- [docs/CONVENTIONS-LEDGER.md](docs/CONVENTIONS-LEDGER.md) — which of this repo's
  conventions are **enforced** (36 invariants + 9 more inside the eval runners) and
  which are prose, with the three filters a convention must pass to earn a gate
  (has it already failed · does it fail silently · is it mechanically checkable).
  Read it before proposing a new gate — it argues against gating the ~18 judgment
  conventions, because a flaky gate gets disabled and leaves you worse off
- [CONTRIBUTING.md](CONTRIBUTING.md) — full contribution guide and PR checklist
- [RELEASING.md](RELEASING.md) — how to cut a release, including every
  version- and count-bearing surface (README, router, manifests, social
  preview)
- [docs/MAINTENANCE.md](docs/MAINTENANCE.md) — accuracy sweep runbook + eval harness
- [docs/WHY-IT-WORKS.md](docs/WHY-IT-WORKS.md) — the measured-efficacy case (lift **vs.
  an unguided model**, plus a scoped head-to-head vs. named competing libraries) + the
  design benefits; keep its numbers in sync with the eval results when they change
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
