# Conventions ledger — which rules are enforced, which are prose, and why

A rule written in prose is a **hypothesis that people will read it**. This repo has
one measured counter-example: `LAST-VERIFIED` was documented in three separate
places, mentioned across nine files, and **two separate sessions still proposed
bumping it wrongly**, catching themselves only on verification. That is
`sota-code-security` rules/14 §3 — *a natural-language instruction standing in
for an enforced control* — occurring in this repo's own tooling, so it became
invariant 11 (2026-07-31).

This ledger exists so the next such case is found deliberately rather than by luck.
It is **not** an argument for gating everything: a gate per convention means false
positives, and rules/12 §2 is explicit that a flaky gate gets disabled, which leaves
you worse off than the prose you replaced.

## Method

Extracted mechanically from the five agent-facing docs — `AGENTS.md`,
`CONTRIBUTING.md`, `RELEASING.md`, `evals/README.md`, `docs/MAINTENANCE.md` — by
matching the repo's convention format (a bolded lead-in on a bullet or numbered
item).

| | |
|---|---|
| Raw entries | 49 |
| Duplicates (the invariant list appears in both `AGENTS.md` and `CONTRIBUTING.md`) | 8 |
| **Distinct conventions** | **41** |
| Already enforced as invariants | **20** (19 before 2026-09-01, 17 when that row was last corrected, 11 when this ledger was derived) |

An earlier estimate of "~122" came from a loose regex that matched any bold line or
any line containing *must/never/always*. It was an over-count by ~3×, and is
recorded here so the number is not repeated.

## Gates added since the ledger was derived

| Gate | Already failed? | Fails silently? | Mechanically checkable? | Verdict |
|---|---|---|---|---|
| **`evals/smoke-runners.py` — every runner can start, is import-safe, and existence-checks `.env`** (2026-08-27, CI) | **yes** — `run-desc-routing.py` raised before its first API call from 2026-08-05 to 2026-08-27 | **yes** — nothing reported it for three weeks; the last recorded run of that eval predated the guard that killed it | **yes** — patch the one network choke point, run each `main()`, any other exception is a dead runner | **earned a gate.** Watched to fail on a reintroduction of the exact bug before wiring in. **Ceiling stated**: it proves a runner can *start*, not that it is correct |
| **The router's `§AUDIT` cannot move without someone re-reading the rules files that hold its procedure** (2026-09-01, invariant 20) | **yes, and in the ledger rather than the code** — ROADMAP 26 parked this gate on *"no eval consumes §AUDIT"*, and that reason was **false when re-read**: `run-repo-audit.py:89` returns `f"{router}\n\n{rules}"`, the whole router, §AUDIT included. An audit eval had been measuring against an unpinned §AUDIT for as long as that runner existed | **yes** — §BUILD's pin has caught drift twice since v1.15.0; §AUDIT's absence was documented in `sota/rules/01` §5 (*"nothing catches this automatically"*), and a sentence saying a thing is unchecked is exactly as loud as no sentence | **yes** — a hash over a section delimited by two stable headings, the mechanism `ROUTER_BUILD_SHA` has used since v1.15.0 | **gated as invariant 20.** Placed in `check-invariants.sh`, not a runner: `run-repo-audit` pastes verbatim and cannot drift, so the drift that matters is **router-vs-rules** — §AUDIT states seven passes whose procedure lives in `sota/rules/01` and `rules/03`, and a pass contradicting the file it points at is worse than no pass, because the reader follows whichever they loaded. **What it does not check**: whether those files still *agree* with the new §AUDIT. A hash can only guarantee someone had to come and look |
| **Every CHANGELOG version below the top entry has a git tag** (2026-09-04, invariant 21) | **yes, twice, before anyone asked** — v1.30.0 (2026-08-29) and v1.31.2 (2026-09-02) each had a CHANGELOG section, a `VERSION` bump and a merge to `main`, and no tag and no release. Both found by enumerating the CHANGELOG against `git tag`, not by any gate | **yes** — invariant 5 checks a tag is never *ahead* of `VERSION` and nothing checked the other direction; an untagged version is unreachable by `git tag -l` while its CHANGELOG entry reads exactly like a published one | **yes** — `git rev-parse --verify refs/tags/vX.Y.Z` per heading below the top one | **gated as invariant 21.** The **top entry is exempt** and that is not a loophole — the tag is pushed *after* the squash-merge ([RELEASING.md](../RELEASING.md) §4 forbids chaining them), so on a release PR the current version legitimately has none yet. **Skips with a note** on a tagless shallow checkout rather than failing every version at once: a gate that cannot see its evidence must say so. Its probe was a **FALSE PASS on the first draft** — it inserted the untagged version *above* the top entry, so invariant 5 complained instead, and the harness refused to credit the catch |
| **No `- [ ]` checklist bullet is stranded inside a code fence in a skill file** (2026-09-05, invariant 22) | **yes** — PR #226 (2026-08-16) inserted two audit-checklist bullets at the wrong offset, inside the fenced example in `sota-code-security` rules/11 §2.2; they rendered as gate output for three weeks and never reached the checklist an auditor reads | **yes** — the line count does not change, the diff line is indistinguishable from another line of the sample, and Markdown renders it as one. Invariant 2 already tracks fence state but only to stop a fenced *heading* satisfying "ends with an Audit checklist"; invariant 10 checks a rules file is indexed, not that its contents reached anyone | **yes** — the same fence toggle check 2 already uses, plus a `- [ ]` match; found exactly 2 instances across 303 skill files | **earned a gate.** Watched to fail on a re-injection of the original defect and to pass once fixed, before being wired in. **Scope stops at skill files**: prose files legitimately show checklist syntax inside samples |
| **`AGENTS.md` stays under its own 200-line cap, and keeps its symlinks** (2026-09-06, invariant 24) | **yes, twice in two days** — 201 on 2026-09-05 and 202 on 2026-09-06, each time from adding an invariant's own table row, each time found only because a session happened to run `awk` by hand | **yes** — invariant 1 deliberately exempts this file, and the only symptom of a breach is that the file is longer. Nothing in any output changes | **yes**, once the word was settled. **Gating a *target* is a category error**, so ROADMAP 35 asked for the cap-vs-target decision *before* the check. It is a cap: the file already states it as an imperative with a named escape (move detail to `CONTRIBUTING.md` behind a pointer), which is exactly invariant 1's shape | **gated as invariant 24**, and it **caught its own author on the first run** — adding rows 24 and 25 to the table took the file to 201. The check also asserts `CLAUDE.md`/`GEMINI.md` are still symlinks: that is `sota-code-security` rules/10 §1's **proxy question** applied to a gate of ours, because the cap only *matters* while those symlinks make the file load every session. A cap enforced on a file nobody loads passes forever while its reason has quietly gone |
| **Undocumented eval flags do not grow** (2026-09-06, invariant 25) | **yes** — `--no-gate-arm` shipped in v1.33.0 documented in the root README's index and in the runner's `--help`, and **not** in `evals/README.md`, the file a person opens to learn what an instrument measures. It got there only because a follow-up sweep looked | **yes** — invariant 14 resolves a release's declared terms against `README.md` **or** `docs/INDEX.md`, and either satisfies it, so the harness's own front door is unguarded | **only in ratchet form, and measuring said so before it was written.** A strict "every flag is documented" rule opens red on **27** pre-existing (file, flag) pairs, nearly all generic plumbing — `--json`, `--report`, `--build-model`, `--judge-model`. A gate that opens red on 27 things it does not care about is one someone disables, which this file calls strictly worse than no gate. And *which* flags deserve documentation is judgement: the ones that matter change what the instrument **measures** | **gated as invariant 25** — the count may not *rise*. Two designs rejected on the way: the strict rule (above), and **adding `evals/README.md` to invariant 14's resolution set** — that was in ROADMAP 36's own text and reads plausible, but 14 accepts a term in README **or** INDEX, so a third accepted location makes it **looser**; it would have weakened the gate it was meant to reinforce. The ratchet **fails closed on an empty scan**, since a drifted regex would otherwise make it pass on every possible input (`sota-code-security` rules/11 §2.2a — this repo's own newest rule, applied to its own newest gate) |
| **Every CHANGELOG version heading has its own link reference** (2026-09-06, invariant 23) | **yes, four consecutive releases** — 1.31.2, 1.32.0, 1.32.1 and 1.32.2 all shipped with no `[X.Y.Z]:` ref, found by hand at the v1.32.3 cut while adding 1.32.3's own and backfilled in that commit | **yes** — a `## [1.32.0]` heading with no matching ref is **not a broken link**: Markdown renders it as literal text, brackets and all. No error, no 404, nothing to click. Invariant 8 cannot see it either — 8 resolves `[text](file.md)` inline links to files on disk, and this is a reference-style link to an external URL | **yes** — set-difference of `^## [X.Y.Z]` headings against `^[X.Y.Z]:` refs, **per file**, since [RELEASING.md](../RELEASING.md) §1 requires a heading and its ref to stay in the same file when archiving | **gated as invariant 23.** Sibling of 21, and the two fail independently — one asks for a tag, the other for a ref. **Compares sets, never counts**: when it was written all three files' heading and ref counts matched exactly, and a count check would have been just as green with two versions swapped. Checks **both directions** (a bare heading *and* an orphan ref, which is what moving a section without its ref produces — one edit, two defects, no count change) and that each ref ends in `/releases/tag/v<its own version>`, since all 75 already follow that single form, so a deviation is a typo rather than a style |

Two of its three assertions were added *because* the smoke check could not catch the class
itself: importing a module-level script **runs** it, which reads as "reached the network".
And the `.env` assertion was **vacuous on its first draft** — it matched `.env` inside the
`open()` call while the code builds the path first, so it passed the broken tree exactly as
happily as the healthy one. Watching it fail is the only reason that was caught, which is
the ledger's own standing point: a gate nobody has seen fail is not yet a gate.

It caught a defect on its **first CI run** — in code added the same day
(`run-router-length.py` opened `.env` unconditionally, so it raised on any machine
without one). No local run could have found that: a maintainer's tree has a `.env`, so
the failing branch is only reachable where the file is absent.

## The three filters

A convention earns a gate only if it passes **all three**:

1. **Has it already failed?** The repo records its own incidents. A convention with
   a real incident is *proven fallible*; one without is a hypothesis, and gating
   hypotheses is how a repo accumulates checks nobody trusts.
2. **Does it fail silently?** The discriminator that matters. A violation that
   breaks CI, fails a test, or annoys somebody already has feedback. A violation
   that produces a **plausible-looking result** — a green stamp, a `+0.00`, a scorer
   returning `1.0` — is the rules/10 class and cannot be caught by attention.
3. **Is it mechanically checkable?** Many are not, and pretending otherwise
   produces a gate that measures the wrong thing.

## The ledger

### Enforced (25) — invariants 1–25

Skill-file line cap · audit-checklist placement · internal-name denylist · description cap ·
version lockstep · count surfaces · router completeness · link resolution ·
single `[Unreleased]` · rules-file indexed by its SKILL.md · `LAST-VERIFIED` sweep
pairing · rendered asset no older than its source · scoreboard rows declare their sample size ·
**a release declares its front-door terms and they resolve** · **the router's library map
lists every `rules/NN` file, both directions** · **the hook `README.md` documents equals the
one `install.sh` writes** · **a document describing the checks agrees with them** ·
**every `§` section reference resolves** · **every check has a known-bad, and the
exempt set is pinned** · **the router's §AUDIT is pinned** · **every CHANGELOG version
below the top entry is tagged** · **no `- [ ]` checklist bullet is stranded inside a
code fence in a skill file** · **every CHANGELOG version heading has its own
link reference** · **`AGENTS.md` stays under its own 200-line cap and keeps its
symlinks** · **undocumented eval flags do not grow**.
Each is in `scripts/check-invariants.sh` and documented in
`AGENTS.md`. (Corrected 2026-08-19: this section read "(14) — invariants 1–14" and named
only thirteen, while 15 and 16 were already gated and described in the table below —
the ledger of what is enforced had itself drifted from what is enforced.)

### Enforced in code, outside the invariant script (9)

| Convention | Where enforced |
|---|---|
| Pin what you mirror | `ROUTER_BUILD_SHA` aborts `run-completeness.py` on drift |
| Assert the corpus is non-empty / a filter removed something | guards inside each runner |
| Guards abort, never warn | the runners' own abort paths |
| Don't trust the scrub | gitleaks is the backstop, in pre-commit and CI |
| **A 200 with empty content is not success** (added 2026-08-14) | every runner that calls a model: empty completion → retry → fail loudly with `finish_reason`; `finish_reason == "length"` warns, because a truncated artifact is a floor not a measurement |
| **A judge verdict must match the rubric it was asked about** (2026-08-16) | `run-completeness.judge()`, shared by all four judge-driven instruments: aborts on missing/extra ids or values outside present/absent, and normalises case — a well-formed reply of the wrong shape used to score 0.00 in silence |
| **Pin what you compare against** (2026-08-16) | `run-competitors.py` compares each clone's `git rev-parse HEAD` to the manifest SHA and refuses on mismatch; the artifact records models, manifest path and resolved SHAs |
| **An ablation arm must actually differ from its baseline** (2026-09-01) | `run-prompt-independence.py` diffs each case's `pre` and `post` bundles and **aborts** when none differ — otherwise the ablation arm is a duplicate of the treatment wearing a different label, and reports a delta of zero as a result. Cases that *do* match are kept and read as the run's sampling-noise control instead of being dropped |
| **A probe must assert its own mutation landed** (2026-08-16) | `check-negative-controls.sh probe()`: a stale hardcoded literal used to make the harness report the *gate* inert |

### Judgment — correctly ungateable (≈18)

*Verify every claim against a primary source* · *keep it generic* (the judgment half;
the denylist covers the mechanical half) · *watch the guard fail before trusting it* ·
*assert a scripted edit landed* · *wait on a terminal artifact* · *grow the set before
trusting a subgroup signal* · *adversarially re-verify* · the sweep runbook's steps ·
the live-agent A/B conventions (*a bare arm is not bare by default*, *never encode the
arm in a path*) — these govern work that happens **outside the repo**, in prompts and
scratch directories a gate cannot see.

For these the fix is never a fourth copy of the text. It is **proximity**: the
LAST-VERIFIED rule failed while written in three places, all far from the point of
use. One line *in* the file being edited would likely have outperformed all three.

**Applied 2026-07-31** to the three cases with an identifiable point of use:

| Convention | Moved to | Note |
|---|---|---|
| `LAST-VERIFIED` is a sweep stamp, don't bump it | **`LAST-VERIFIED` itself** | required teaching `check-freshness.sh` to strip comment lines — the strict `YYYY-MM-DD` parser was *why* the rule could not live where it was needed |
| Watch a guard fail · print the denominator · skip don't guess | **`scripts/check-invariants.sh` header**, as an "adding a check?" block | the file had **zero** guidance on adding a check |
| A bare arm is not bare · never encode the arm in a path | **all three live-agent runners' docstrings** | none of them carried it, though they are what the conventions govern |

The rest of the judgment list has no single point of use — *verify every claim* applies
everywhere, which is precisely why it cannot be relocated and must stay a principle.

### Gated after this ledger was derived (2)

| Candidate | Incident? | Silent? | Checkable? | Verdict |
|---|---|---|---|---|
| A rendered `assets/*.png` is never older than its `*.html` | **yes** — PR #173 (2026-08-01) fixed a stale line-cap claim in `how-it-works.html` and did not re-render the PNG; `main` served the old claim all day | **yes** — nobody reads the HTML, and the PNG looks fine, it just says the old thing | **yes** — commit times from `git log -1`, no rendering required | **gated same day** as invariant 12 |

This one is the ledger's most useful entry, because **it was not on the list.**
The ledger was derived by matching the repo's convention format across the five
agent-facing docs — and this convention was *nowhere in those docs to be matched*.
It was not an ungated convention; it was an **unwritten** one, and the extraction
method is structurally blind to that class. The finding below that "the gateable set
is small" is therefore a statement about *written* conventions only. A second source
of candidates exists and is not searchable: things this repo does by habit and has
never said out loud, which surface only when one of them fails.

### Gateable but not gated (0 candidates)

| Candidate | Incident? | Silent? | Checkable? | Verdict |
|---|---|---|---|---|
| Front-door capability grep (`RELEASING.md` §2b) | **yes** — five capabilities shipped with no README mention | **yes** — nothing errors | ~~**no**~~ → **yes** | **GATED 2026-08-02 as invariant 14** |
| **Router library map lists every `rules/*` file** | **yes** — `rules/11` was absent from the map (then in `skills/sota/SKILL.md`, since offloaded to `skills/sota/rules/04`) for two releases (found 2026-08-05) | **yes** — invariant 7 gates *skills* against the router and invariant 10 gates rules files against their *own* `SKILL.md`; the map itself is checked by neither, so drift there is silent | **yes** — diff `git ls-files 'skills/*/rules/*.md'` against the map's entries | **GATED 2026-08-05 as invariant 15** — both directions, watched to fail on the real defect and its inverse first |
| **A negative control for our own gates** | **partly** — no gate of ours has been caught inert, but two were caught *examining nothing* (2026-07-30) and the fix was to print the denominator, not to prove the check can reject | **yes** — an invariant that can no longer fail prints the same `ok` as one that can | **yes** — a fixture directory each invariant must reject, asserted non-zero | **GATED 2026-08-05 as `scripts/check-negative-controls.sh`**, its own CI job — 5/5 mutations caught by the intended check |
| **The documented hook matches the installed hook** | **yes** — three different texts existed at once (2026-08-05): `README.md`'s JSON block, `install.sh`'s `HOOK_CMD`, and what was actually in a user's `settings.json`; the README's was two revisions behind | **yes** — nothing reads the README, so a doc showing a hook we no longer install is indistinguishable from a correct one | **yes** — extract the `command` string from the README's fenced JSON and compare it to `HOOK_CMD` | **GATED 2026-08-05 as invariant 16** — parses the README's fenced JSON and compares to `HOOK_CMD`; watched to fail on both drift directions and both empty-scope cases |
| **A document that describes the checks agrees with them** | **yes** — twice in one week (2026-08-19): `CONTRIBUTING.md` listed part A's negative-control coverage as five invariants when the harness printed eleven, and this very file headed its enforced section "(14) — invariants 1–14" while 15 and 16 were gated *and described in the table below it* | **yes** — nothing reads these documents; a doc that under-describes the gates renders identically to a correct one, and both incidents were found by eye, after shipping | **yes** — the count is derivable from `check-invariants.sh`'s own `[k/N]` markers, and the coverage lists are printed verbatim by `check-negative-controls.sh` | **GATED 2026-08-19 as invariant 17** — with a deliberate carve-out: a number inside `"quotes"` is read as a quotation of old wording, not a claim, so a correction note can record what a document *used* to say. Scope stops where derivation does: the **probe count is not gated**, because a static count of call sites reads 13 against an actual 23 |
| **Every `§` section reference resolves** | **yes** — six live defects on the check's *first* run over an unmodified tree (2026-08-20): `rules/11 §6.7` cited from two files including across a skill boundary, `sota-golang` rules/07 §6 in a five-section file, and four cross-skill refs whose bare `rules/NN` resolved to the citing skill's own numbering | **yes** — a `§` reference is prose, so invariant 8's link resolver never saw one; a stale pointer is indistinguishable from a good one until a reader follows it, and ~1,300 of them exist | **yes** — headings and ordered-list items are both parseable, and the reference forms are regular | **GATED 2026-08-20 as invariant 18**, deliberately **fail-open on ambiguity**: a bare `rules/NN` is tried against every skill named on the line and the containing skill, and any hit passes. Two authoring conventions had to be modelled before it was precise — `## §N ` headings and `§N.M` meaning *item M of §N* — and its own first draft flagged nine correct references, which is rules/12 §2.1's "generalised from one sample" committed by the instrument itself |
| **Every check has a known-bad, and the exempt set is pinned** | **yes** — invariant 18 shipped **probe-less in the very commit that introduced it** (2026-08-20), and nothing complained; the gap surfaced only because a human re-read the harness output. Invariant 19 then caught *itself* the same way on introduction | **yes** — a check with no negative control is indistinguishable from a probed one in every output the suite produces; and the cheapest way to satisfy a coverage rule is to add your new check to the exempt list, which is also silent | **yes** — the `probe N` call sites and the harness's own *NOT COVERED* block are both parseable, and the exempt set is small enough to pin | **GATED 2026-08-20 as invariant 19**, and deliberately **not** behind `--self-test`: it costs ~50 ms (measured), and a check you must remember to run is a convention rather than a property — which is exactly how 18 shipped unprobed. The pin (`EXPECTED_UNPROBED`) is a **tripwire, not a cached count**: nothing derives it, everything compares against it, so growing it is a deliberate edit a reviewer sees. Scope stops at existence — it does **not** check the probe count (a static count reads 13 against an actual 26) nor whether a probe's assertion is meaningful |
| **The router's `§AUDIT` cannot move without someone re-reading the rules files that hold its procedure** | **yes, and it is the interesting kind** — not an incident in the code but in the *ledger*: ROADMAP 26 parked this gate on "no eval consumes §AUDIT", and that reason was false when re-read — `run-repo-audit.py:89` pastes the whole router, §AUDIT included. The trigger had been met for as long as that runner existed and nothing re-tested it | **yes** — §BUILD's pin has caught drift twice; §AUDIT's absence was documented in `sota/rules/01` §5 (*"nothing catches this automatically"*) and that sentence is exactly as loud as no sentence at all | **yes** — a hash over a section delimited by two stable headings; the same mechanism `ROUTER_BUILD_SHA` has used since v1.15.0 | **GATED 2026-09-01 as invariant 20.** Placed in `check-invariants.sh` rather than in a runner, because `run-repo-audit` pastes verbatim and therefore cannot drift — the drift that matters is router-vs-rules. **What it does not check**: whether `rules/01` and `rules/03` still *agree* with the new §AUDIT. It guarantees only that someone had to come and look, which is the most a hash can promise |
| **Every CI job that can fail is a required check** | **yes** — `Negative controls` and `Shell lint` have run on every PR since they were added and neither can block a merge (found 2026-08-05) | **yes** — a non-required job renders identically to a required one in the PR UI; only the protection API distinguishes them | **yes** — diff the workflow's job names against `required_status_checks.contexts` | **CLOSED 2026-08-05** — all four jobs made required. Not a script: the remedy was a protection change, so the "gate" here is GitHub's own. Verified the way this ledger demands — a PR with a deliberately failing negative control went from mergeable to refused |

**How the block came off.** This sat blocked on *"needs a machine-readable
capability list per release"* — true, and still true: **discovery cannot be
gated**, because "what counts as a capability" is judgement. What can be gated is
the **declaration**, which is the same move invariant 11 makes for `LAST-VERIFIED`:
the escape is a claim that must be *true*. A release states its front-door terms
and the gate proves each one resolves — in `README.md`/`docs/INDEX.md` **and** in
the release's own entry, so a filler word cannot buy a pass. The residual risk is a
deliberately gamed declaration, which is a different failure from the oversight
this fixes.

**The actionable set from written conventions is now empty.**

**Closed 2026-08-02: the Samples-column guard shipped as invariant 13.** It was
this ledger's one actionable candidate — *every scoreboard row declares its sample
size* — with its incident (a `+0.07` retracted when the set grew 15 → 49; a `+0.40`
corrected to `+0.39` by a second run), its silence (a number from one run is
typographically identical to one from ten), and its checkability (the `Samples`
column, populated in all 10 rows) all already argued above. The implementation
locates the table by its **header** rather than a column index, so renaming or
dropping the column fails closed instead of passing over zero rows.

That leaves **one** candidate, and it is blocked on a prerequisite this ledger
cannot supply. The actionable set from *written* conventions is now empty — which,
with finding 2b below, is the useful state to be in: the next gate will come from an
incident, not from re-reading the docs.

**And a third time, in a new way (2026-08-20, invariant 18).** The prediction holds —
nothing about `§` references was ever a *written* convention, so re-reading the docs
could not have surfaced it. What is new is the trigger: the gate was proposed because a
**planned change** (splitting two rules files) would create a hazard nothing checked,
and it was built *before* the change. Applying the three filters honestly at proposal
time, the first one — *has it already failed?* — read **no**. Running the check answered
it retroactively: **six live defects** already existed, one of them a cross-skill
citation. So the useful lesson is narrower than "gates come from incidents": a gate can
also come from asking **what would this refactor break that nothing would tell me
about**, and the answer is often that it is already broken. Cost of getting the order
right: 27 further references broke during the split, all caught.

**And it did, twice, within three days (2026-08-05).** The two rows added above came
out of ordinary work — a router map found stale while adding a rules file, and a rule
we wrote for everyone else and had not applied to ourselves. Neither was discoverable
by re-reading a convention, because neither was ever written down as one; both match
the "unwritten conventions" bucket this ledger says is not searchable. That is the
mechanism working as designed, and it is worth recording as evidence for it: **the
prediction was made on 2026-08-02 and paid out on 2026-08-05.** Note the asymmetry in
their evidence, and do not flatten it — the router-map candidate has a real incident
behind it, while the negative-control candidate is argued from doctrine and a
near-miss. The first is ready to build; the second should be built because we require
it of others, which is a weaker reason and should be stated as one.

**Both shipped the same day they were recorded (2026-08-05), and the weaker one
earned its keep immediately.** The negative-control harness was argued from doctrine
rather than from an incident — and on its **first run** it reported a FALSE PASS on
its own probe 15: `git clean` does not remove *staged* files, so a fixture added by
probe 10 leaked forward and the next mutation failed on the file-count check instead
of the check it targeted. A harness that accepted any non-zero exit would have printed
**5/5 caught** and been wrong about one of them. That is the `rules/12` §2.1
"instrument that cannot fail" mode, caught in our own instrument, by the one assertion
added specifically to catch it. The doctrine-only candidate is no longer
doctrine-only; **treat this as the incident.**

**A third payout, 2026-08-19 — and this one indicted the ledger itself.** Invariant 17
also came from an incident rather than from re-reading conventions, and the incident
was *this file*: its enforced section said "(14)" while sixteen were gated, with the
two missing ones written out in the table above. A ledger of what is enforced had
drifted from what is enforced, which is the exact class it exists to catalogue. Note
what that costs the "re-read the docs" strategy: this document was re-read at two
consecutive release cuts and the heading survived both, because a reader checking
*whether a convention is gated* looks at the rows, not at the count above them.

**Not gated: BUILD and AUDIT halves must correspond (measured 2026-08-21, twice).**
Invariant 2 checks a rules file *ends* with `## Audit checklist`; nothing checks the
checklist matches the guidance above it. Both directions fail silently — a checklist item
with no build rule marks a team down for following the library, and a build rule with no
item is this library's most frequently rediscovered gap. Through the three filters:
incident **yes**, silent **yes**, mechanically checkable **no** — and the third is a
measurement, not an opinion:

- **Attempt 1 — `§` anchors.** Only **14 of 1,802** checklist items (1%) cite a section
  anchor at all. The proxy measured a formatting habit that does not exist, not the
  property. Discarded.
- **Attempt 2 — lexical overlap.** 95% of audit items share terms with their own file's
  body; 60% of build sections have a footprint in their own checklist. Then the numbers
  were **sampled before being quoted**, and the sample discredited them: `§2 HTTP method
  semantics` reads as uncovered while the checklist says *"No GET/HEAD endpoint mutates
  state"* — synonymy — and *"Retries idempotent-only, budget-bounded…"* reads as
  ungrounded while being grounded in two **sibling** files. Both failure modes are
  intrinsic: correspondence is semantic and often cross-file.

- **Attempt 3 — read a sample, which is the only method that works.** 20 sections on a
  fixed stride from a population of **1,773**: **16 covered, 2 correctly exempt** (HATEOAS
  and TDD are advisory — you cannot audit "did you practise TDD"), **2 real gaps**.
- **Attempt 4 — n=60, and the rate collapsed.** A second systematic sample, screened on
  section-*body* terms against the file's own checklist **and its siblings'**, flagged 7.
  All 7 read: **5 were covered** (the screen over-flags on synonymy), 1 correctly exempt
  (a pure cross-reference section), **1 real gap**. Eleven `ok` calls were then read as a
  false-negative check — including the seven weakest — and **every apparent gap dissolved
  under correct checking**: one had been searched in the wrong file, one was covered by an
  item phrased as `cast()` rather than "narrowing".
  Pooled over the 80 sampled sections the confirmed rate is **~4%**, not the 10% n=20
  suggested. The honest caveat: 18 of the 60 were read in full, the rest screened, and the
  screen is known to err **both ways** — so 4% is a floor with a soft ceiling, not a
  measurement.
- **The finding that beat the percentage: gaps cluster by *file*, not by section**, and
  the worst cluster was **self-inflicted the same day**. Ranking files by weak-screen
  density put two `rules/02-design-api.md` files on top; reading the first showed the real
  cause — the in-band-sentinel row added to **nine language skills that morning** had
  shipped with an audit item in only **two** of them. Seven were fixed on discovery. The
  lesson is procedural, not statistical: **a fan-out across N skills is N chances to ship
  the build half alone**, and the author is the last person who will notice.

Both real gaps were fixed on discovery: `sota-c-cpp` rules/01 §7 *Error handling* had **no
probe anywhere in the skill** (one incidental hit across seven files), and
`sota-ml-engineering` advertised *train/serve skew* twice in its own description with
**zero** checklist items on skew, point-in-time correctness or feature stores across all
seven of its rules files.

So it is written as a convention in [CONTRIBUTING.md](../CONTRIBUTING.md) with its
exception (advisory sections, and checks owned by a sibling skill) and left ungated. Two
things the sample settled that the mechanical attempts could not: the asymmetry is real
but **modest and one-directional**, and **the feared direction did not appear at all** —
not one sampled checklist item demanded something the build half never asked for. Every
apparent instance of that was an artifact of the instrument.

**Where invariant 17 stops, stated with an instance (2026-08-19, the v1.22.14 cut).**
It asserts two things and no more: every stated count equals the script's own `[k/N]`,
and `AGENTS.md`/`CONTRIBUTING.md` each enumerate 1..N with no gaps. It does **not**
compare what a description *means* to what the check *does*. The first instance is
already on the board: `AGENTS.md`'s invariant 14 row read "a declared term resolves in
**neither** `README.md`/`docs/INDEX.md` **nor** the release's own entry" — an OR across
all three — while `check-invariants.sh:842` requires (README **or** INDEX) and `:848`
requires the release's own entry, an AND. `CONTRIBUTING.md` item 14 was already correct,
so two documents describing one gate agreed on the count and disagreed on the logic.
Through the three filters: incident **yes** (once), silent **yes**, mechanically
checkable **no** — matching the semantics of two restatements written at deliberately
different granularities is the judgement class this ledger exists to argue against
gating, and it is the same residual `CONTRIBUTING.md` item 17 already states for row 12
versus item 12. The remedy stays a habit: read the prose beside the script at each cut,
which is how this one surfaced.

## Findings

**1. The "never publish from n=1" convention contradicts itself.** The bolded
headline reads *"One run is a data point, not a number. Never publish from n=1."*
The very next sentence permits it: *"Report a mean across ≥2 runs, **or state the
sample size**."* A reader skimming bold sees a prohibition; a reader of the body
sees a disclosure requirement. The scoreboard follows the body — the audit row is
`1×`, declared — so it is **compliant, not a violation**. I checked expecting to
find a breach and found a wording defect instead, which is the more useful result.

**2. The gateable set is small — 2, and one is blocked.** Against a prediction of
2–4, the ledger yields **one actionable candidate**, and it is a regression guard
rather than a repair. That is the honest output: most conventions here either are
already enforced or govern judgment a gate cannot reach. *(That one candidate
shipped as invariant 13 on 2026-08-02; the remaining candidate is still blocked.)*

**2b. …but only among conventions that were written down (added 2026-08-01).**
One day after this ledger shipped, a real defect produced invariant 12 — a
convention that passed all three filters and appeared in *none* of the five source
documents, because nobody had ever written it. The extraction method cannot find
what was never stated, so finding 2 bounds the **documented** set, not the real one.
Practical consequence: re-deriving this ledger will not find the next invariant 12.
Only an incident will.

**3. Enforcement is not concentrated in the invariant script.** **Eight** conventions are
enforced outside it (four when this ledger was first derived). Every one added since
arrived the way this ledger predicts — **from an incident, never from re-reading the
docs**: three of them on 2026-08-16 from a scoped audit of the instruments themselves.
Anyone auditing "what does this repo actually enforce?" by reading `check-invariants.sh`
alone would undercount by a third.

## What this does not claim

No convention outside the two candidates was found to be both failure-prone and
checkable. This ledger is a snapshot: it should be re-derived after any batch of new
conventions, and the extraction is mechanical enough to repeat. It measures *what is
enforced*, not *whether the conventions are correct*.
