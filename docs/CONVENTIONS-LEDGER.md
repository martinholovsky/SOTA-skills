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
positives, and rules/11 §7 is explicit that a flaky gate gets disabled, which leaves
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
| Already enforced as invariants | 13 (11 when this ledger was derived) |

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

### Enforced (13) — invariants 1–13

Skill-file line cap · audit-checklist placement · internal-name denylist · description cap ·
version lockstep · count surfaces · router completeness · link resolution ·
single `[Unreleased]` · rules-file indexed by its SKILL.md · `LAST-VERIFIED` sweep
pairing · rendered asset no older than its source · scoreboard rows declare their sample size. Each is in
`scripts/check-invariants.sh` and documented in `AGENTS.md`.

### Enforced in code, outside the invariant script (4)

| Convention | Where enforced |
|---|---|
| Pin what you mirror | `ROUTER_BUILD_SHA` aborts `run-completeness.py` on drift |
| Assert the corpus is non-empty / a filter removed something | guards inside each runner |
| Guards abort, never warn | the runners' own abort paths |
| Don't trust the scrub | gitleaks is the backstop, in pre-commit and CI |

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

### Gateable but not gated (1 candidate)

| Candidate | Incident? | Silent? | Checkable? | Verdict |
|---|---|---|---|---|
| Front-door capability grep (`RELEASING.md` §2b) | **yes** — five capabilities shipped with no README mention | **yes** — nothing errors | **no** — needs a machine-readable capability list per release | **blocked**, recorded in ROADMAP |

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

**3. Enforcement is not concentrated in the invariant script.** Four conventions are
enforced inside the eval runners. Anyone auditing "what does this repo actually
enforce?" by reading `check-invariants.sh` alone would undercount by a third.

## What this does not claim

No convention outside the two candidates was found to be both failure-prone and
checkable. This ledger is a snapshot: it should be re-derived after any batch of new
conventions, and the extraction is mechanical enough to repeat. It measures *what is
enforced*, not *whether the conventions are correct*.
