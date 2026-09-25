# 04 — Commits, Branches & Releases

Commit message and atomicity discipline, conventional commits and when they pay,
branch strategy, versioning, and release/changelog mechanics.

## §1 Atomic commits

A commit is the unit of `bisect`, `revert`, `cherry-pick`, and `blame`. Optimize
for those four operations.

- **One logical change per commit**: the change and its tests together, nothing
  unrelated. "Fix X and also format the file" poisons blame; "half of feature
  X" breaks bisect.
- **Every commit on the main branch builds and passes tests.** A bisect that
  lands on "WIP, doesn't compile" is a bisect wasted. With squash-merge this is
  automatic (each merged PR = one green commit); with merge/rebase flows, clean
  the branch (autosquash fixups) before merge — rules/03 §4.
- Mechanical changes (rename, format, codemod) get their own commit, labeled as
  such, so reviewers and blame can skip them. Consider
  `.git-blame-ignore-revs` for repo-wide reformat commits.
- **Don't commit what the build produces or the developer machine leaks**:
  artifacts, `.env`, editor droppings — enforce via `.gitignore` + pre-commit
  secret scanning (deeper treatment: `sota-secrets-management`).

## §2 Commit messages and Conventional Commits

- **Subject**: imperative mood ("Add", not "Added"/"Adds"), ≤72 characters
  (50 is the classic ideal), no trailing period, capable of completing "if
  applied, this commit will ___".
- **Body**: explains *why* and what the alternatives were — the diff already
  shows the what. Wrap at 72. Link issues/incidents. A one-line `fix typo` body
  is fine; a one-line body on a 300-line behavioral change is a finding.
- **Conventional Commits** (conventionalcommits.org, spec v1.0.0 — still the
  current version as of 2026): `type(scope)!: description` with `feat`, `fix`,
  and friends; `!` or a `BREAKING CHANGE:` footer marks breaking changes.
  - **When it pays**: you automate something with it — changelog drafts and
    version bumps via semantic-release / release-please / git-cliff, monorepo
    per-scope releases, commit-lint gates. `feat` → minor, `fix` → patch,
    breaking → major gives you releases as a by-product of merging.
  - **When it doesn't**: no automation consuming the types. Then it's ceremony;
    plain well-written messages (above) are the actual requirement. Don't adopt
    the syntax without the pipeline.
  - If adopted: enforce mechanically (commitlint/PR-title check on squash
    merges), keep the type honest (`feat` that's really a `fix` corrupts the
    generated changelog), and remember the generated changelog still gets a
    human edit (rules/02 §6).

**Bad**: `fixed stuff`, `WIP`, `address review comments`, `Update scheduler.py`.
**Good**:

```
fix(payouts): skip frozen accounts in preview

Preview ran the eligibility check but not the account-status check,
so frozen creators saw payouts that execution would reject (#892).
Reuse StatusGate from the execution path instead of duplicating the
check, so the two paths cannot drift again.
```

## §3 Branch strategy honesty

Pick the simplest strategy your release reality allows, and admit which one
you're actually running.

- **Default: trunk-based with short-lived branches.** Branch from main, PR
  within a day or two, merge, delete. Long-lived feature branches are merge
  debt with interest; integrate continuously behind feature flags instead.
  Branch age is a metric worth alerting on (>3 days: ask why).
- **Gitflow only with real release trains**: multiple maintained versions in
  the field (on-prem, mobile, embedded), genuine hardening windows. If you
  deploy from main continuously, `develop` + `release/*` + `hotfix/*` is
  process cosplay — every extra long-lived branch is a divergence to reconcile.
- **Release branches without gitflow** are a legitimate middle: cut
  `release/1.4` from main at code freeze, cherry-pick fixes, tag from it —
  while feature work continues on main. Use when you ship versioned artifacts
  but develop trunk-based.
- Hotfix path is defined *before* the incident: where it branches from (the
  release tag), where it must land back (main, always — a fix that exists only
  on a release branch regresses in the next release).
- Default branch is protected: required reviews + checks, no direct pushes, no
  force push (rules/03 §6).

## §4 Versioning discipline

- **SemVer means the numbers are promises**: major = breaking, minor =
  additive, patch = fixes. Breaking in a minor is a contract violation no
  matter what the release notes say. If you can't honor that, use explicit
  CalVer or 0.x rather than fake SemVer — consumers' tooling (`^`, `~`,
  dependabot) acts on the numbers, not your intentions.
- **What counts as breaking is broader than compilation**: removed/renamed
  symbols and endpoints, tightened validation, changed defaults, changed error
  codes/types callers branch on, changed wire formats, raised minimum
  runtime/OS versions. Behavioral contracts documented in rules/02 §2 are part
  of the API.
- 0.x is an explicit "anything may change" signal — fine for pre-stable, but
  don't live there for years while telling users you're production-ready.
- **Breaking-change communication is a pipeline, not a number**: deprecation
  warnings in code → changelog `Deprecated` section → migration guide
  (rules/02 §7) → major release → removal. The version bump is the last step,
  never the first notice.
- API surface evolution rules (additive change, deprecation headers, sunset)
  are covered in `sota-api-design`; this file covers the release mechanics.

## §5 Releases, tags, and release notes

- **Releases are tagged, and tags are immutable**: never delete or re-point a
  published tag — downstream caches, lockfiles, and humans have already
  resolved it; a moved tag is a supply-chain incident (signed tags, provenance,
  artifact immutability: `sota-devsecops`). A bad release gets a *new* patch
  version, not a recycled tag.
- **Releases are reproducible from the tag**: version is derived from the tag
  (not hand-edited in three files — or if files must contain it, the bump is
  automated and the tag is the source of truth), built by CI, never from a
  laptop. **Write the recipe down** (a `BUILDING.md` or a section of
  `RELEASING.md`/`CONTRIBUTING.md`): the toolchain and its exact version, where
  pinned inputs come from (lockfiles, base-image digests), the one command that
  produces each release artifact, and how to compare the result with the
  published one. A build only the CI config can explain cannot be re-derived by
  a user or auditor checking your artifacts. Mechanics of hermetic and
  reproducible builds: `sota-devsecops` rules/04 §4.1. (OWASP: SCVS 3.2)
- **Automate the release train**: tag (or merged release PR) triggers build,
  changelog finalization (move `Unreleased` → version section), artifact
  publish, docs version publish (rules/02 §5). release-please / semantic-release
  style tooling does this off conventional commits (§2); the more humans in
  the loop, the rarer and scarier releases become.
- **Release notes are the curated story** (highlights, upgrade notes, breaking
  changes up top, who should care); the changelog is the complete record
  (rules/02 §6). Generate the skeleton, edit for humans; leading with
  "Bump deps (#1042)" tells users you didn't.
- Pre-releases use ordered, machine-readable identifiers
  (`2.0.0-rc.1`), published to pre-release channels (`next` dist-tag, pre-release
  flag) so they never resolve as `latest`.
- Ship breaking changes in a release that contains *only* the breaking changes
  and their migration affordances where feasible — mixing "must-have fix" with
  "must-rewrite-callers" forces users to take the break to get the fix.

## Audit checklist

- [ ] History bisects: sampled main-branch commits build and pass tests; no WIP/broken commits on main.
- [ ] Commits are atomic — one logical change with its tests; mechanical changes isolated (and in `.git-blame-ignore-revs` where repo-wide).
- [ ] Subjects imperative and ≤72 chars; bodies on non-trivial commits explain why; sampled `git log` is readable as a narrative.
- [ ] If Conventional Commits: enforced by commitlint/PR-title check, types honest, and an automation pipeline actually consumes them; if not adopted, no half-applied `feat:` cargo-culting.
- [ ] Branches are short-lived (check age of open branches); no zombie long-lived feature branches; flags used for incomplete work.
- [ ] Branch model matches release reality (no gitflow on a continuous-deploy service); hotfix path documented and lands back on main.
- [ ] Version numbers honor SemVer (diff a recent minor for breaking changes) or the project explicitly uses CalVer/0.x.
- [ ] Breaking changes followed the pipeline: deprecation → changelog → migration guide → major; never a surprise minor.
- [ ] Published tags never moved/deleted (compare tag dates vs. registry artifacts if suspicious); releases built by CI from the tag.
- [ ] Release notes curated with breaking changes first; changelog `Unreleased` section flows into versioned sections at release; pre-releases can't resolve as latest.
- [ ] **(Low; Medium for a distributed artifact) Build reproduction is documented** (§5): toolchain version, pinned inputs and the exact release command are written in the repo. Probe: `grep -rli -E 'reproduc(e|ible|ing)[^.]*build' README.md BUILDING.md RELEASING.md CONTRIBUTING.md docs 2>/dev/null | grep -q . || echo "no build-reproduction doc"`.
