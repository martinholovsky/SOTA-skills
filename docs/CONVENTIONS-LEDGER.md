# Conventions ledger — which rules are enforced, which are prose, and why

A rule written in prose is a **hypothesis that people will read it**. This repo has
one measured counter-example: `LAST-VERIFIED` was documented in three separate
places, mentioned across nine files, and **two separate sessions still proposed
bumping it wrongly**, catching themselves only on verification. That is
`sota-code-security` rules/10 §2.12 — *a natural-language instruction standing in
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
| Already enforced as invariants | 17 (11 when this ledger was derived) |

An earlier estimate of "~122" came from a loose regex that matched any bold line or
any line containing *must/never/always*. It was an over-count by ~3×, and is
recorded here so the number is not repeated.

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

### Enforced (17) — invariants 1–17

Skill-file line cap · audit-checklist placement · internal-name denylist · description cap ·
version lockstep · count surfaces · router completeness · link resolution ·
single `[Unreleased]` · rules-file indexed by its SKILL.md · `LAST-VERIFIED` sweep
pairing · rendered asset no older than its source · scoreboard rows declare their sample size ·
**a release declares its front-door terms and they resolve** · **the router's library map
lists every `rules/NN` file, both directions** · **the hook `README.md` documents equals the
one `install.sh` writes** · **a document describing the checks agrees with them**.
Each is in `scripts/check-invariants.sh` and documented in
`AGENTS.md`. (Corrected 2026-08-19: this section read "(14) — invariants 1–14" and named
only thirteen, while 15 and 16 were already gated and described in the table below —
the ledger of what is enforced had itself drifted from what is enforced.)

### Enforced in code, outside the invariant script (8)

| Convention | Where enforced |
|---|---|
| Pin what you mirror | `ROUTER_BUILD_SHA` aborts `run-completeness.py` on drift |
| Assert the corpus is non-empty / a filter removed something | guards inside each runner |
| Guards abort, never warn | the runners' own abort paths |
| Don't trust the scrub | gitleaks is the backstop, in pre-commit and CI |
| **A 200 with empty content is not success** (added 2026-08-14) | every runner that calls a model: empty completion → retry → fail loudly with `finish_reason`; `finish_reason == "length"` warns, because a truncated artifact is a floor not a measurement |
| **A judge verdict must match the rubric it was asked about** (2026-08-16) | `run-completeness.judge()`, shared by all four judge-driven instruments: aborts on missing/extra ids or values outside present/absent, and normalises case — a well-formed reply of the wrong shape used to score 0.00 in silence |
| **Pin what you compare against** (2026-08-16) | `run-competitors.py` compares each clone's `git rev-parse HEAD` to the manifest SHA and refuses on mismatch; the artifact records models, manifest path and resolved SHAs |
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

### Gated after this ledger was derived (1)

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
| **Router library map lists every `rules/*` file** | **yes** — `rules/11` was absent from the map in `skills/sota/SKILL.md` for two releases (found 2026-08-05) | **yes** — invariant 7 gates *skills* against the router and invariant 10 gates rules files against their *own* `SKILL.md`; the map itself is checked by neither, so drift there is silent | **yes** — diff `git ls-files 'skills/*/rules/*.md'` against the map's entries | **GATED 2026-08-05 as invariant 15** — both directions, watched to fail on the real defect and its inverse first |
| **A negative control for our own gates** | **partly** — no gate of ours has been caught inert, but two were caught *examining nothing* (2026-07-30) and the fix was to print the denominator, not to prove the check can reject | **yes** — an invariant that can no longer fail prints the same `ok` as one that can | **yes** — a fixture directory each invariant must reject, asserted non-zero | **GATED 2026-08-05 as `scripts/check-negative-controls.sh`**, its own CI job — 5/5 mutations caught by the intended check |
| **The documented hook matches the installed hook** | **yes** — three different texts existed at once (2026-08-05): `README.md`'s JSON block, `install.sh`'s `HOOK_CMD`, and what was actually in a user's `settings.json`; the README's was two revisions behind | **yes** — nothing reads the README, so a doc showing a hook we no longer install is indistinguishable from a correct one | **yes** — extract the `command` string from the README's fenced JSON and compare it to `HOOK_CMD` | **GATED 2026-08-05 as invariant 16** — parses the README's fenced JSON and compares to `HOOK_CMD`; watched to fail on both drift directions and both empty-scope cases |
| **A document that describes the checks agrees with them** | **yes** — twice in one week (2026-08-19): `CONTRIBUTING.md` listed part A's negative-control coverage as five invariants when the harness printed eleven, and this very file headed its enforced section "(14) — invariants 1–14" while 15 and 16 were gated *and described in the table below it* | **yes** — nothing reads these documents; a doc that under-describes the gates renders identically to a correct one, and both incidents were found by eye, after shipping | **yes** — the count is derivable from `check-invariants.sh`'s own `[k/N]` markers, and the coverage lists are printed verbatim by `check-negative-controls.sh` | **GATED 2026-08-19 as invariant 17** — with a deliberate carve-out: a number inside `"quotes"` is read as a quotation of old wording, not a claim, so a correction note can record what a document *used* to say. Scope stops where derivation does: the **probe count is not gated**, because a static count of call sites reads 13 against an actual 23 |
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
