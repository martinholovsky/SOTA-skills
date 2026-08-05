# Contributing to SOTA-skills

Thanks for helping improve the library. SOTA-skills is a collection of Markdown
skills that an AI assistant reads to build and audit software using
state-of-the-art practices. There is no code to run — contributions are edits to
Markdown, held to a few hard invariants.

By contributing you agree your contribution is licensed under
[CC BY 4.0](LICENSE), the same as the rest of the library.

## Ground rules

1. **Keep it generic.** The library must apply to anyone. Do not hard-code one
   person's or company's stack, project names, or infrastructure. Name products
   only as neutral *examples* ("e.g. PostgreSQL"), never as an assumption about
   the reader ("you run PostgreSQL"). Personalization belongs in a local
   `profiles/<you>.md`, which is git-ignored and never committed.
2. **Verify every claim.** Fast-moving facts (versions, specs, advisories,
   regulations) must be checked against a **primary source** — a spec, vendor
   doc, CVE/CWE, or official release — and cited. Prefer "needs verification"
   over a confident guess. The library's value is that its claims hold up.
   Corollary — **no rot-prone version pins**: never write "the current release
   is X.Y"; say "latest stable, verify at the official source". Version
   numbers are for semantic boundaries only ("GA since", "fixed in", CVE fix
   versions, spec editions). Recommend maintained tools; when one goes EOL,
   point at its maintained successor and keep a one-line EOL note.
3. **Stay lean — instruction files only.** Every **skill** file
   (`skills/*/SKILL.md`, `skills/*/rules/*.md`) is **≤ 500 lines** so skills load
   incrementally without blowing the context window. Nothing else in the repo has
   a line cap. If a topic outgrows that, split it into another `rules/NN-topic.md`.
   The cap is load-bearing *only* there: README, CHANGELOG and `docs/` are read
   by humans and agents rather than loaded as skills, so they are deliberately
   **uncapped** (decided 2026-07-15, PR #100) — navigability there comes from a
   table of contents and [docs/INDEX.md](docs/INDEX.md).

## Repository layout

```
skills/
  sota/                       # master router — routing + operating principles
  sota-<domain>/
    SKILL.md                  # when-to-use, BUILD/AUDIT workflows,
                              # top-10 non-negotiables, rules index
    rules/
      01-<topic>.md           # ≤500 lines, ends with "## Audit checklist"
      02-<topic>.md
profiles/
  example.md.template         # copy to profiles/<you>.md (git-ignored)
scripts/check-invariants.sh   # the invariants below, enforced
AGENTS.md                     # guidance for AI assistants working on the repo
                              # (CLAUDE.md and GEMINI.md are symlinks to it)
```

## Anatomy of a skill

**`SKILL.md`**

- YAML frontmatter with exactly two fields: `name` and `description`. If the
  description contains a colon, use a block scalar (`>` or `|`) so the YAML stays
  valid. Per the [Agent Skills spec][skills-spec], `name` is ≤ 64 chars
  (lowercase, digits, hyphens) and `description` is **≤ 1024 characters** — a
  loader skips any skill whose description exceeds the cap, so keep it tight
  (trim prose before trigger keywords). Enforced by invariant 4 below.
- A `description` that says *when* to use the skill (BUILD and AUDIT triggers)
  and a list of trigger keywords — Claude Code matches prompts against this.
- Body: a short "when to use", a **BUILD** workflow and an **AUDIT** workflow, a
  **top-10 non-negotiables** list, and a **rules index** table pointing at the
  `rules/` files.

**`rules/NN-topic.md`**

- Roughly 80–350 lines of concrete, current guidance with short examples
  (a target, not a floor — compact rules files are fine; the hard cap is 500).
- Ends with an **`## Audit checklist`** — yes/no questions, ideally with
  grep/lint patterns, so the rule can be used to hunt violations.
- Fast-moving claims must be verified against primary sources when written.
  Library-wide re-verification is tracked by the root **`LAST-VERIFIED`** file
  (YYYY-MM-DD of the last full-library sweep: per-skill research against
  primary sources, findings adversarially verified, fixes applied). Update it
  only after such a sweep — not on ordinary edits. A monthly CI job
  (`scripts/check-freshness.sh`) goes red when the stamp exceeds the
  re-verify window (**6 months**). Do not add per-file `<!-- last-verified -->`
  line-1 markers (retired convention; the script warns about strays). The
  step-by-step sweep runbook is [docs/MAINTENANCE.md](docs/MAINTENANCE.md).

**Findings format** (AUDIT mode, used throughout):

```
file:line | rule violated | severity | effort | fix
```

- Severity: **Critical** · **High** · **Medium** · **Low** · **Info**
- Effort: **trivial** · **small** · **medium** · **large**

Borderline severities should state the deciding assumption; unconfirmed findings
are marked "needs verification", never asserted.

## The invariants (enforced)

`scripts/check-invariants.sh` runs in pre-commit and CI and fails the build on:

1. any **skill** Markdown (`skills/*/SKILL.md` or `skills/*/rules/*.md`) over
   **500 lines** — **only instruction files are capped**: a file is capped iff an
   agent loads it *as instructions*. Everything else in the repo (README,
   CHANGELOG, `docs/`, `evals/`, scripts) is uncapped prose or code, decided
   2026-07-15;
2. any `skills/*/rules/*.md` that doesn't **end** with an
   **`## Audit checklist`** (it must be the file's last `## ` heading);
3. any **internal/private reference** leaking into tracked files (the private
   pattern list is intentionally not in the repo; PRs from forks run the
   generic checks and the maintainer's CI runs the full list);
4. any `skills/*/SKILL.md` `description` over **1024 characters** (the Agent
   Skills cap) or written as an unquoted inline scalar containing `: ` —
   invalid YAML that makes loaders skip the skill; use `description: >-`.
   Also rejected: an **XML tag** in `name` or `description`, and a reserved
   word (`anthropic`, `claude`) in `name` — both stated in Anthropic's Agent
   Skills reference. `sota-dotnet` carried `Span<T>/Memory<T>`, a well-formed
   XML start tag, until 2026-08-02.
   (Check 4 needs `python3`, and is skipped with a warning if it is absent
   locally — CI always enforces it.)
5. **version drift**: `VERSION`, `plugin.json`, and the CHANGELOG top entry
   must agree; the newest `v*` tag must never be ahead of `VERSION`;
6. **count drift**: the exact-count surfaces (README badge/hero, router body,
   plugin/marketplace descriptions) must match a recount of the `skills/`
   tree — adding or removing a skills file means updating them in the same
   PR. The social-preview pill and README alt carry an **"N+" floor** instead
   (checked only against dropping below it), so the image needs no per-release
   re-render.
7. **router drift**: every domain skill must appear in the router's routing
   table AND its library map (both in `skills/sota/SKILL.md`) — adding a skill
   means updating both.
8. **link rot**: every relative Markdown link to a `*.md` target (in any
   tracked `*.md`) must resolve — a moved or renamed file can't leave a dead
   link behind. Scoped to `*.md` targets to avoid false-positives on
   `[text](x)`-shaped prose/code; needs `python3` (skipped-with-warning if
   absent locally, enforced in CI). Adopted from the training-knowledge-vault
   vault-doctor (see [docs/ADOPTION-LOG.md](docs/ADOPTION-LOG.md)).
9. **duplicate `[Unreleased]`**: `CHANGELOG.md` may carry at most one
   `## [Unreleased]` heading, and it must be the topmost entry; the archive
   files carry none. Practical effect for contributors: if `[Unreleased]`
   already exists, **add to it** — don't open a second one. Invariant 5 only
   inspects the first `## [` heading, so duplicates below it used to pass CI
   (two PRs did exactly that on 2026-07-28).
10. **unindexed rules file**: every `skills/*/rules/*.md` must be referenced by
    its own `SKILL.md`. Practical effect: when you add a rules file, add a row
    for it to that skill's rules index in the same PR — otherwise the model
    never loads it, because it reads only the files the index names. Invariant 8
    does not catch this: **30 of 41** `SKILL.md` files list rules as plain
    backticked text rather than links, so a rename leaves no link to resolve.

11. **`LAST-VERIFIED` moves only with a sweep**: the stamp is the date of the last
    *full* re-verification pass, not a recency marker. Practical effect: don't touch
    it on an ordinary edit, even one that verified its own facts. If you really did
    complete a pass, either the diff is sweep-shaped (≥ 20 skill files) or you name
    `LAST-VERIFIED` in the CHANGELOG entry.
12. **rendered assets are current**: every `assets/*.png` must be committed no
    earlier than the `assets/*.html` it renders. Practical effect: edit the HTML,
    re-render the PNG, commit **both together** (see
    [Rendered assets](#rendered-assets)). If the edit genuinely cannot change the
    output, put `[no-render]` in the commit subject. Added the day it failed —
    #173's whole point was fixing a claim in `how-it-works.html`, the PNG was not
    re-rendered, and the README kept showing the old text.
13. **every scoreboard row declares its sample size**: each row of the results
    table in `evals/results/RESULTS.md` must fill its `Samples` cell. Practical
    effect: adding a row means stating its `n` (`3×, temp 0.7`, `1×`) — a number
    without one reads exactly like a number with one. A regression guard: it passes
    today and exists to keep it that way.
14. **a release declares its front-door terms**: only fires when `VERSION`
    changes, so an ordinary PR is unaffected. Practical effect: a release PR adds
    `**Front door checked:** term · term` to its CHANGELOG section, and each term
    must appear in `README.md` or `docs/INDEX.md` **and** in that release's own
    entry. See [RELEASING.md](RELEASING.md) §2b for why.
15. **the router's library map lists every rules file**, both directions: a
    `skills/<skill>/rules/NN-*.md` that the map in `skills/sota/SKILL.md` does not
    enumerate, or a number the map enumerates with no such file. Practical effect:
    adding a `rules/NN` means editing that map too — and `skills/sota/SKILL.md` is
    at **exactly 500 lines** (invariant 1), so reflow an existing line rather than
    adding one. Invariant 7 checks the map lists every *skill* and invariant 10
    checks a rules file is indexed by its *own* `SKILL.md`; neither reads the map's
    contents, which is how `sota-code-security/rules/11` went unlisted from v1.19.8
    to v1.21.0 with every check green.

**Proving the gate can still fail.** `scripts/check-invariants.sh` passing means the
tree is clean — it does not mean the checks still work, and those two states print
identically. `scripts/check-negative-controls.sh` (CI job *Negative controls*) injects
a known-bad per invariant into a disposable git worktree and requires **the intended
check** to be the one that complains; a non-zero exit for any other reason is reported
as a FALSE PASS, because a harness that accepts any failure reports full coverage while
testing nothing. It covers invariants 1, 2, 6, 10 and 15 and says plainly which it does
not cover. **Adding an invariant? Add its known-bad there too** — otherwise you have
shipped a check nobody has ever watched fail. Not in pre-commit: it runs the whole gate
once per mutation.

Secrets are scanned separately by **gitleaks** (config in `.gitleaks.toml`);
CI scans the full git history, the pre-commit hook scans each commit.

[skills-spec]: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

## Local setup

```sh
pipx install pre-commit     # or: brew install pre-commit
pre-commit install          # run the same checks on every commit
```

(`scripts/install.sh` also checks for the hook when run from a checkout and
offers to install it, or prints this tip if the `pre-commit` tool is missing.)

Run the invariant checks any time:

```sh
./scripts/check-invariants.sh
```

### Rendered assets

`assets/*.png` are **build outputs** of the `assets/*.html` next to them, and
both are committed. Nothing regenerates them — so editing the HTML without
re-rendering leaves the README showing the *old* claim while the diff looks
fixed. Re-render over localhost (`file://` is typically blocked by the
browser's local-file policy) at the size the existing PNG already is:

```sh
cd assets && python3 -m http.server 8731     # then screenshot headless:
# how-it-works.html  -> how-it-works.png   at 1400x672
# social-preview.html -> social-preview.png at 1280x640
```

Confirm the result with `sips -g pixelWidth -g pixelHeight assets/<name>.png`
before committing — a wrong-sized re-render is a silent regression in the
README's layout. `social-preview.png` additionally needs a manual re-upload at
GitHub **Settings → Social preview**; the repo file does not refresh it.

## Submitting a change

1. Fork and branch (`git checkout -b improve-sota-databases-indexing`).
2. Make the edit; keep diffs focused (one skill / one concern per PR).
3. Run `pre-commit run --all-files` (or at least `./scripts/check-invariants.sh`).
4. Open a PR describing **what** changed, **why**, and **how the claims were
   verified** (cite sources for any new version/spec/advisory claim).

### PR checklist

- [ ] Stays generic — no personal/company stack, project names, or "you run X".
- [ ] New fast-moving claims cite a primary source.
- [ ] Every touched `rules/*.md` still ends with `## Audit checklist`.
- [ ] Any **new** `rules/*.md` has a row in its skill's rules index (invariant 10).
- [ ] All touched **skill** files (`skills/**`) are ≤ 500 lines (README/CHANGELOG/`docs/` are uncapped).
- [ ] No secrets in examples (masked/placeholder only).
- [ ] Touched an `assets/*.html`? **Re-render its `.png` in the same commit.**
      The README embeds the *image*, never the source, so an un-rendered fix is
      invisible to every reader while looking done in the diff — which is
      exactly what happened to `how-it-works` in #173 (see
      [rendered assets](#rendered-assets) for the render command).
- [ ] `pre-commit` / `scripts/check-invariants.sh` passes.

## Adding a whole new skill

Same structure: a `skills/sota-<domain>/` folder with a `SKILL.md` (two-field
frontmatter, BUILD/AUDIT workflows, top-10, rules index) and `rules/NN-*.md`
files each ending in an audit checklist. Add the skill to the router
(`skills/sota/SKILL.md`) routing table and to the table in `README.md`. Open an
issue first if you want to discuss scope.

## Questions

Open an issue. For anything security-sensitive (bad security guidance, or a real
secret accidentally committed), follow [SECURITY.md](SECURITY.md) instead.
