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

   The list lives in **two places that cannot see each other**: `.denylist.local`
   (git-ignored) for the pre-commit hook, and the `SOTA_DENYLIST` repository
   secret for CI. The secret is **write-only** — nothing can read it back to diff
   it — so a pattern added to one place and not the other leaves a gate that is
   green in one lane and blocking in the other. Add a new name to **both**, in
   the same sitting.

   **A green check 3 means "no match", which is not the same as "clean".** On
   2026-08-11 a sweep found a project name in two tracked docs that the check had
   passed over for a month, because the name was simply not in the list — the
   guard's predicate did not cover its own target (`sota-code-security/rules/12`
   §3, in our own machinery). When your set of private names changes, the list is
   what has to change; the check will not discover the gap for you.

   **To prove the secret is live, use the canary — never a real name.** Both
   copies of the list carry one synthetic pattern that matches nothing real
   (see the comment in `.denylist.local`). Push a branch with a file containing
   it and check 3 must fail; that demonstrates the secret is loaded, parsed and
   blocking, while the only string reaching the **public** CI log is an invented
   one. Probing with a real internal name would publish exactly what the control
   exists to suppress. The canary literal must never appear in a tracked file
   either — it is on the list, so it would fail the build permanently.
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
    adding a `rules/NN` means editing that map too — and `skills/sota/SKILL.md` sits
    close to the 500-line cap (invariant 1), so reflow an existing line rather than
    adding one. **Re-count it, never trust a number in prose**
    (`grep -c '' skills/sota/SKILL.md` — 494 on 2026-08-19; this sentence has read
    "exactly 500" and "491" at other times, both wrong when written). Invariant 7 checks the map lists every *skill* and invariant 10
    checks a rules file is indexed by its *own* `SKILL.md`; neither reads the map's
    contents, which is how `sota-code-security/rules/11` went unlisted from v1.19.8
    to v1.21.0 with every check green.
16. **the hook `README.md` documents matches the one `install.sh` writes**
    (`HOOK_CMD`). Practical effect: change the re-injection hook's wording in one
    place and you must change it in the other. On 2026-08-05 three texts existed at
    once — the README block, `HOOK_CMD`, and what was in a real `settings.json` —
    and the README's is the one a reader copies by hand, so the stale one is the
    one that spreads. The check parses the fenced JSON rather than regexing the
    string, so reformatting the block is not a false positive.
18. **a `§` section reference resolves nowhere**: invariant 8 resolves
    `[text](file.md)` links; a `§` reference is **prose**, so the ~1,300 of them
    across `skills/` were checked by nothing and broke silently whenever a section
    was renumbered or a rules file split. Practical effect: if you renumber a
    section, move one between files, or add a cross-skill pointer, name the skill
    (`` `sota-golang` rules/05 §3 ``) — a bare `rules/NN` resolves against **your
    own** skill. Added 2026-08-20, immediately before splitting `rules/10` and
    `rules/11`, and it found **six** live defects on its first run over the
    unmodified tree. Two conventions it had to learn, both found by *reading* the
    findings rather than trusting the count: a heading may number itself `## 3.`
    **or** `## §3 ` (missing the second form hid 102 valid references), and `§N.M`
    means a `### N.M` heading in some files and **item M of the ordered list in
    §N** in others — both legitimate. It is deliberately **fail-open on ambiguity**
    (a bare `rules/NN` is tried against every skill named on the line and your own,
    and any hit passes), because a gate that flags correct prose gets disabled.
    **What it does not check**: plain `rules/NN` mentions with no `§` beside them,
    and it cannot tell a *wrong-but-existing* section from a right one.
19. **a check has no known-bad, or the exempt set grew**: every check in
    `check-invariants.sh` must be either probed by `check-negative-controls.sh` or
    listed in that script's own *NOT COVERED* block — and that exempt set is
    **pinned** in `EXPECTED_UNPROBED`, because otherwise the cheapest way to satisfy
    this check is to add your new check number to the exempt list. Growing it is a
    deliberate edit a reviewer sees. Runs on **every** invocation (~50 ms), not behind
    `--self-test`: a check you have to remember to run is a convention, not a
    property. Added 2026-08-20 after invariant 18 shipped **probe-less in the very
    commit that introduced it**; 19 caught *itself* the same way on introduction,
    which is the shortest possible demonstration that it works. `--self-test` still
    exists and now means "run the suite, then run the harness that watches each check
    fail". **What it does not check**: the probe *count* (a static count of call sites
    reads 13 against an actual 25), or whether a probe's assertion is meaningful —
    only that one exists.
17. **a document that describes the checks disagrees with them**: any stated count
    of invariants/checks that isn't the number `check-invariants.sh` prints, or a
    restatement of the negative-control coverage lists that isn't what
    `check-negative-controls.sh` prints. Practical effect: if you add a check,
    the count in `AGENTS.md`, `CONTRIBUTING.md`, `docs/CONVENTIONS-LEDGER.md` and
    `docs/MAINTENANCE.md` must move with it. Added 2026-08-19 after this file
    understated part A's coverage by six invariants and the ledger headed its
    enforced section "(14)" while 16 were gated. A number inside `"quotes"` is
    treated as a quotation of old wording, not as a claim — that is how a
    correction note can record what a document *used* to say. It also requires
    `AGENTS.md`'s table and this list to enumerate **1..N** with no gaps, since
    the stated count and the actual list can drift apart independently. **What it
    does not check**: that row 12 and item 12 *describe the same invariant* — only
    that both enumerate all of them. Matching prose across two deliberately
    different granularities is not mechanically checkable, and a flaky gate gets
    disabled ([CONVENTIONS-LEDGER](docs/CONVENTIONS-LEDGER.md)).

**Proving our gates can still fail.** `check-invariants.sh` passing means the tree is
clean — it does not mean the checks still work, and those two states print identically.
The same is true of `verify-setup.sh`. `scripts/check-negative-controls.sh` (CI job
*Negative controls*) covers **both**: it injects a known-bad and requires **the intended
check** to be the one that complains; a non-zero exit for any other reason is reported
as a FALSE PASS, because a harness that accepts any failure reports full coverage while
testing nothing.

Part A mutates a good tree inside a disposable git worktree (invariants 1, 2, 3, 4, 6,
7, 8, 10, 13, 15, 16, 17, 18, 19 — 14 of 19; the harness prints the list and why the rest are
not covered, so read its output rather than this sentence). Part B is the inverse: `verify-setup.sh` audits a *machine*, so the fixture is a
fully-configured fake one — `CLAUDE_CONFIG_DIR` pointed at a temp home, a throwaway git
repo, and a stub `gh` on `PATH` so run history is decidable — and each probe removes one
thing (checks 1, 2, 3, 4, 6a, 6b, 7, 8, 9, 9a, 10a). What is *not* covered is printed rather
than implied. Not in pre-commit: it runs a whole gate per mutation.

**Adding a check? Run `./scripts/check-invariants.sh --self-test`.** Its structural pass
takes a second and fails if your new check has neither a known-bad in
`check-negative-controls.sh` nor an entry in that script's *NOT COVERED* block saying
why it cannot have one — so "I'll add the probe later" stops being possible rather than
being discouraged. (It then runs the full harness, which is the slow part.) This exists
because the instruction it replaces — *add its known-bad there too* — was prose, and
prose did not stop invariant 18 shipping probe-less in its own commit. It is the rule
from `sota-code-security` rules/12 §1b applied to us.

Secrets are scanned separately by **gitleaks** (config in `.gitleaks.toml`);
CI scans the full git history, the pre-commit hook scans each commit.

[skills-spec]: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

## Local setup

```sh
pipx install pre-commit     # or: brew install pre-commit
pre-commit install          # installs BOTH stages (see .pre-commit-config.yaml)
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
