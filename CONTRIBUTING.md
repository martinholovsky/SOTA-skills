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
- **The two halves must correspond, in both directions.** Invariant 2 checks the
  checklist *exists*; nothing checks that it matches the guidance above it, and the
  mismatch is silent either way:
  - **A checklist item with no build rule** tells an auditor to flag something the
    build half never told anyone to do. That is the direction that wastes other
    people's time — a team follows the library, ships, and is then marked down by the
    same library. If an item has no counterpart above it, either add the build rule or
    move the item to the file that owns it.
  - **A build rule with no checklist item** is the more common direction (it is the
    library's most frequently rediscovered gap — see `docs/ADOPTION-LOG.md`): the rule
    is stated, often more than once, and no one wrote down how an auditor would detect
    the violation. When adding a build rule, ask separately *how would I find this in
    someone else's codebase* — and if the honest answer is "you would not", say so in
    the rule rather than leaving a silent hole.
  - **The exception, stated so it is not treated as a defect:** advisory sections
    ("prefer X where it fits") and sections whose check genuinely lives in a sibling
    skill do not need a local item. Cross-reference the owner instead.
  This is a **judgement** convention and is deliberately not gated — see
  [docs/CONVENTIONS-LEDGER.md](docs/CONVENTIONS-LEDGER.md) for the measurement that
  showed why a mechanical version does not work.
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
   table (`skills/sota/SKILL.md`) AND its library map (`skills/sota/rules/04-library-map.md`) — adding a skill
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
20. **the router's `§AUDIT` changes without its pin being re-read**: `§BUILD` has
    been hash-pinned since v1.15.0 (`ROUTER_BUILD_SHA` in `run-completeness.py`) and has
    caught real drift twice; `§AUDIT` had no equivalent, and `sota/rules/01` §5 said so
    outright — *"nothing catches this automatically"*. The item was parked on "no eval
    consumes §AUDIT", which was **false when re-read**: `run-repo-audit.py` pastes the
    whole router, §AUDIT included. The pin lives in `check-invariants.sh` rather than a
    runner because the drift that matters is not eval-vs-router (that runner pastes
    verbatim and cannot drift) but **router-vs-rules**: §AUDIT states seven passes whose
    procedure lives in `sota/rules/01` and `rules/03`, and a pass that contradicts the
    file it points at is worse than no pass, because the reader follows whichever they
    loaded. To change §AUDIT: make the edit, re-read `rules/01` §5 and `rules/03`, then
    set the new `ROUTER_AUDIT_SHA` in the same commit. Added 2026-09-01 (ROADMAP 26).

21. **a CHANGELOG version below the top entry has no git tag**: invariant 5 checks that a
    tag is never *ahead* of `VERSION`. Nothing checked the other direction, and it failed
    twice before anyone asked — **v1.30.0** and **v1.31.2** each had a CHANGELOG section, a
    `VERSION` bump and a merge to `main`, with no tag and no release. A version that ships
    in the CHANGELOG and never gets tagged is unreachable: `git tag -l` skips it and the
    notes live only in a file nobody clones for that. **The top entry is exempt** — the tag
    is pushed *after* the squash-merge ([RELEASING.md](RELEASING.md) §4 forbids chaining
    them), so on a release PR the current version legitimately has no tag yet. The check
    **skips with a note** when the checkout has no tags at all (shallow CI clones do not
    fetch them) rather than failing every version at once.

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
7, 8, 10, 13, 15, 16, 17, 18, 19, 20, 21 — 16 of 21; the harness prints the list and why the rest are
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

### Changing the router's BUILD or AUDIT workflow

The router (`skills/sota/SKILL.md`) is capped at **500 lines** and is read on every task,
so both workflow sections hold **imperatives only**; the procedure and reasoning live in
`skills/sota/rules/`. That split means a change usually lands in more than one file.

**BUILD is mirrored in four places** and three of them fail silently — the table is in
[`skills/sota/rules/02-build-workflow.md`](skills/sota/rules/02-build-workflow.md) §5.
The one loud surface is `ROUTER_BUILD_SHA` in `evals/run-completeness.py`: it pins a hash
over the router's §BUILD, so editing that section **aborts the completeness eval** until
you deal with it. Never bump the hash without first re-reading `BUILD_WORKFLOW` against
the new §BUILD clause by clause, then say in the commit which case it was — *an imperative
changed* (re-sync the mirror first) or *only prose moved* (hash alone is correct).

**AUDIT is mirrored in three** — the router's §AUDIT,
[`rules/01-audit-methodology.md`](skills/sota/rules/01-audit-methodology.md) §5 (which owns
running the audit) and [`rules/03-audit-findings.md`](skills/sota/rules/03-audit-findings.md)
(severity, evidence, refutation, reporting). There is **no hash pin over §AUDIT**, so nothing
catches divergence automatically; a new pass needs a line in the router *and* a section in
whichever rules file owns it.

Adding a `skills/sota/rules/NN` file also touches the **library map** in `skills/sota/rules/04` (invariant
15) and the README's file count (invariant 6) — and both gates read `git ls-files`, so
`git add` the new file before believing either of them.

### Dependency updates

`.github/dependabot.yml` watches **`github-actions` only**. There is no pip or npm
manifest here — the library is Markdown and every script is stdlib-only Python or
POSIX shell — so Actions is the single third-party supply-chain surface.

Actions are pinned to **commit SHAs, not tags**, because a tag is mutable and a
compromised upstream can move it (`sota-devsecops` rules/01). Dependabot handles SHA
pins: it bumps the SHA and rewrites the trailing `# vX.Y.Z` comment. Keep that comment
on every pin — it is the only thing that makes the SHA readable to a human.

Minor and patch bumps are **grouped into one weekly PR** so the four required checks
run once per batch rather than once per action.

**Dependabot PRs need `SOTA_DENYLIST` in the *Dependabot* secret store, not just the
repository one.** They run on same-repo branches, so CI's *"Require denylist secret on
trusted runs"* step applies to them — but Dependabot's token is denied repository secrets,
so the secret reads empty and `Repository invariants` fails. That gate is **correct**: on
such a run invariant 3's authoritative denylist scan genuinely is not running. The fix is
to give Dependabot its own copy, never to exempt `dependabot[bot]`:

```sh
grep -vE '^[[:space:]]*(#|$)' .denylist.local | paste -sd'|' - \
  | gh secret set SOTA_DENYLIST --app dependabot
```

Note the value is the **pipe-joined ERE**, matching how `check-invariants.sh` consumes the
env var — `.denylist.local` is one pattern per line and the script joins it at read time.
A Dependabot PR opened before a release will also fail invariant 5 (`tag ahead of
VERSION`); `gh pr update-branch <n>` fixes that.

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

**The three charts are different** — they are generated from a `.py` beside them,
not screenshotted, and each writes both themes as SVG plus a 2× PNG (needs
`rsvg-convert`; without it the SVGs still write and the script says so):

```sh
python3 assets/gen-benchmark-chart.py   # benchmark-{light,dark}.{svg,png}
python3 assets/gen-breadth-chart.py     # breadth-{light,dark}.{svg,png}
python3 assets/gen-lift-chart.py        # lift-{light,dark}.{svg,png}
```

The numbers are **hardcoded in each script**, mirrored by hand from
`evals/results/RESULTS.md` — so a re-measured result means editing the `ROWS`/
`GROUPS` table and re-running, in the same commit that updates the prose.
Invariant 12 does **not** cover these (it pairs `*.html` with `*.png`), so nothing
will catch a chart left stale — check them when you change a published number.

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
