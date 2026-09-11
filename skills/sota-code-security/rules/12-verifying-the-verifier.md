# Verifying the Verifier — the mutation probe

rules/10 catalogs controls that look enabled and do nothing. rules/11 is the sweep
that finds them at codebase scale. This file is the third move, and the one most
often skipped: **proving that a specific control works** — by making it fail on
purpose, and by putting that known-bad somewhere it will survive.

Turning the same suspicion on **everything that did the proving** — the scorers,
gates, benchmarks, watchers and guards, and the instrument you are auditing with
right now — is `rules/15`, split out of this file on 2026-09-06 at the seam its own
subtitle used to name. Section numbers did not change in the move: `rules/15` §2 and
`rules/15` §3 mean there exactly what they meant here.

The reason it earns its own file is an asymmetry. A broken feature produces a
complaint. **A broken verifier produces a green tick or a number**, and both are
believed, quoted, and put in a README. Nothing downstream distinguishes "we
checked and it was fine" from "the check could not have failed".

Use it in BUILD to decide whether a control you just wrote is actually held in
place by anything, and in AUDIT as the pass that runs *after* rules/10 and
rules/11 have produced findings — because a finding produced by an unvalidated
instrument is not yet a finding (`rules/15` §2, §3).

**Outside software this is settled practice, under four different names.** Every
discipline that has to trust a detector tests it with something it *must* catch:
a **proof test**, which exists because a safety function's dangerous failures
stay hidden until the moment of demand (IEC 61508's framing); a **positive
control** in an assay, where a run whose known-positive comes back negative is
void rather than clean; **built-in test** on aircraft systems; and adversary
emulation in detection engineering, where `sota-detection-engineering` rules/06
already requires proving a detection fires against the real technique. Software
CI tests the code with the tests and almost never tests the tests, gates and
scanners with a known-bad. Closing that asymmetry is what this file is for. The
design-level generalisation is **poka-yoke**: prefer making the inert state
impossible or self-announcing over making it detectable.

Related: the instruments and guards that do the checking → `rules/15`; the
inert-control catalog → rules/10; the codebase-scale sweep → rules/11; vacuous tests in general, mutation testing, and watching a security
test fail → `sota-testing` rules/02, rules/06 and rules/09; the audit-level
evidence and refutation standard → `sota/rules/03` §2 and §4.

---

## 1. The mutation probe — make the control fail on purpose

A test that passes against broken code is worse than no test: it manufactures
false safety. `sota-testing` rules/02 (assertion-free, tautological), rules/06
(mutation testing), and rules/09 (security regression tests must be watched to
fail) own the general doctrine. What this file adds is the targeted procedure
for a **security control**:

1. Replace the control's body with the permissive no-op — `return []`,
   `return True`, `pass`.
2. Run the suite.
3. **Nothing fails ⇒ that control is untested**, regardless of how many tests
   name it. Report it as a finding, not as a coverage note.

Two traps that make step 3 lie:

- **Masked by a missing dependency.** The assertion passes because the feature
  was disabled for an *unrelated* reason (rules/10 §2.2) — the real path never
  ran. Force the dependency present (monkeypatch the availability check) so the
  control is actually exercised.
- **The mutation did not take.** Commonest cause first, because it is not an environment
  fault at all: **the substitution matched nothing.** A regex that does not match, a `sed`
  delimiter colliding with a character in the pattern (`s|…|…|` against a pattern
  containing `|`), an edit tool that no-ops. Then the environmental ones — editable
  installs, copied/rsync'd trees, stale bytecode, cached images — and a **formatter
  reflow**, where a multi-line revert silently matches nothing because
  `ruff format`/`black`/`prettier` folded the target onto one line.

  Two fixes, and the cheaper one is stronger. **Assert the pattern is present before you
  write**, which fails at *mutation* time:

  ```python
  assert old in text, f"mutation {n} did not match -- harness bug, not a result"
  ```

  and **assert the mutation's runtime effect** — make the no-op print or raise once —
  which fails at *interpretation* time. Field-measured: a three-mutation harness where one
  `sed` died loudly on a delimiter collision and another matched nothing in silence; the
  silent one made the self-test **pass**, and was read for half a minute as a real gap in
  the control being built. Only the loud sibling made the harness suspect at all
  (`rules/15` §2.1, sixth bullet — the harness is the newer artifact).

A **third probe** costs one edit: leave code and fixture alone and point the
assertion at a plausible **wrong expected value** — still passing means it is keyed
to something true that is not evidence (`sota-testing` rules/06 §6.3).

Then build the **structural** test that catches the class: assert the loaded rule
count is non-zero, assert every reference-config key resolves, assert the
documented default equals the parsed default, assert the control's telemetry is
emitted. Instance tests catch today's bug; structural tests catch the next one.

## 1a. The other direction — the control that blocks everything

§1's probe is **directional**. It installs the *permissive* no-op and asks what
fails, which finds the control that does nothing. Nothing in it can find the
opposite defect: an **enforcement** control — a cap, quota, limit, filter,
allowlist, sandbox policy — set so tight that it refuses the legitimate case too.
Both defects pass the same test, because a security suite asserts *refusal*
(`sota-testing` rules/09 §1) and refusal is exactly what an over-tight control
produces.

The asymmetry is why only one of the two ever gets found. An inert control fails
toward the attacker and nothing observable changes. An over-tight one fails toward
the user and is loud — *in production*, weeks later, on the input nobody tested.

**Every enforcement control needs two arms, and the deny arm is the one everybody
writes:**

1. **Deny arm** — the abusive case is refused. (The one you already have.)
2. **Allow arm** — a *representative legitimate* case completes unchanged under the
   same policy. Not a reduced case, not a synthetic one: the real workload's
   ordinary input.

**A negative control on the environment is not a negative control on the control.**
Proving the machine can allocate a gigabyte says nothing about whether *your cap*
permits legitimate work — an arm like that exercises the environment and passes
whether or not the control exists at all. The allow arm has to run **through** the
control.

Worked instance, both arms measured (Go 1.26, linux/amd64, container, 2026-08-18):

| memory cap | deny arm — over-budget allocation refused | allow arm — 200 MiB legitimate run completes |
|---|---|---|
| `ulimit -v` (`RLIMIT_AS`) | yes — **vacuously**: the process never starts | **no** — `fatal error: failed to reserve page summary memory` at `-v 512M` |
| `ulimit -d` (`RLIMIT_DATA`) | yes — 400 MiB refused at `-d 128M` | yes — completes at `-d 512M` |

Deny-only, the two configurations are indistinguishable and both read as "the cap
works" — and the `RLIMIT_AS` row passes its deny arm **vacuously** (`rules/15` §3), for the
same reason it fails the allow arm: nothing ever runs (`sota-sandboxing` rules/02
R7.2a). The allow arm is the only thing that separates a working budget from a
control that refuses everything — and it is precisely the arm the deny-only habit
drops. The same gap applies to a WAF ruleset, an egress allowlist, an input
validator, an admission policy, and a rate limiter keyed too narrowly.

## 1b. Where the probe lives decides whether it survives

§1 and §1a describe probes as things you *run*. In any suite that keeps them they
are also things somebody *maintains*, and the two usual homes both leak:

- **Beside the checks** — a separate harness or CI job that injects a known-bad per
  check. It proves today's checks can fail. It says nothing about the check added
  next week, because joining the harness is a **convention**, enforced by a sentence
  in a contributing guide and by whoever happens to review the PR.
- **In a reviewer's memory** — "we watched it fail once". Unrecorded, and gone with
  the person.

Prefer a third home: **a mode of the tool itself** — `--self-test`, a `doctor`
subcommand — that walks the same registry of checks the ordinary run walks, injects
each check's declared known-bad, and asserts that *that check, by name* is the one
that reports. "Every check can go red" then stops being a property of who last
edited the suite and becomes a property of the suite:

- a check with **no declared known-bad fails the self-test** instead of being
  silently exempt, so the probe cannot be forgotten at the moment a check is added
  — which is the only moment it is ever forgotten;
- the probe **ships with the tool**, so it runs against the operator's own
  installation — exactly where §1's stale-install and missing-dependency traps bite
  (rules/11 §2.5), and where a harness that only ever runs in your CI cannot look;
- the known-bad sits **next to the check's definition**, where the reviewer of a new
  check is already reading.

**The self-test is itself an instrument** (`rules/15` §2) and inherits every rule there. Three
that decide whether its output means anything:

- **Attribute the catch.** Requiring "the run failed" accepts a non-zero exit for an
  unrelated reason as proof — a **false pass**, not a catch. Assert the intended
  check is the one that complains.
- **Assert the mutation took** (§1). A probe whose hardcoded known-bad has drifted
  out of sync with the check reports `NOT CAUGHT` and accuses a healthy check.
- **Report the denominator**: checks probed over checks registered. The gap is the
  interesting number, and it is invisible in a pass/fail line.

Two things a self-test does **not** establish, and both belong in its output rather
than in a reader's assumption: checks whose known-bad needs state it cannot
fabricate (a tag, a merge base, an mtime, a live upstream) are **skipped**, and a
skip must print its reason instead of folding into the pass count; and a check that
can fail may still have stopped covering the code that matters — scope drift is a
separate failure with no diff to the check (`sota-devsecops` rules/09 §2).

### 1b.1 A planned change is a legitimate source of a gate

Gates are usually said to come from incidents — something failed, so now it is checked.
That under-counts one case badly. **Before a rename, a move, a renumber or a split, ask
what class of reference or assumption it invalidates and whether anything would report
it.** Where the answer is *nothing would*, build that check first: the refactor then
becomes its own negative control, because you can watch the check go red on damage you
caused deliberately.

The usual "has this already failed?" filter reads **no** at proposal time here, and that
reading is unreliable — a class nothing reports has no incident history *by
construction*. Running the check is what answers it. Worked case: a documentation tree
carried ~1,300 prose section references (`rules/15 §2.4`, `rules/13 §5`) that no link checker
could see, because a link checker resolves `[text](file.md)` and a `§` reference is
prose. The check was written to protect a planned file split; on its **first run against
the unmodified tree** it found six live breakages, then caught 27 more the split itself
caused. Both sets were invisible the day before, and the second would have shipped.

Two cautions from the same case, because a check like this is an instrument (`rules/15` §2). **Read
the findings before believing the count** — successive drafts reported 46, 29, 17, 13 and
finally 6, and the shrinkage was not tuning but discovering two authoring conventions the
first draft had not modelled, one of which made it flag *correct* references (`rules/15` §2.1's
"generalised from one sample", committed by the instrument itself). And **fail open on
ambiguity**: where a reference could plausibly resolve more than one way, accept it. A
gate that flags correct work gets switched off, which leaves you worse off than no gate.

## 1c. The control that was correct, and then edited

§1 probes a control that is **wrong**, §1a one that blocks **everything**, `rules/14`
a control **not in force**. All three ask a correctness question about a control
somebody else wrote. None of them asks the integrity question: *this control is
correct today — who can change it?*

**Detection is bounded by the integrity of the detector.** A control that a rewrite can
delete provides exactly as much protection as the write permissions on its own source
file, whatever its logic says.

Field-reported. A policy gate protected two artifacts it had enumerated — its decision
engine and its rule pack — staging both read-only outside the writable tree and recording
both in an integrity manifest. It was correct about both, and short by one: **the gate's
own module was an editable install**, so the import resolved *inside* the directory the
gate permitted writes to. Replacing that module with a no-op allowed every subsequent
call. The write was permitted by every rule pack tested, **including the fail-closed
one** — because that pack constrained shell commands, and the write arrived through an
editor tool the pack did not model.

Three things that generalises to:

- **Derive the protected set from what the decision depends on, not from what was
  obvious when the manifest was written.** The artifact most often missing from a
  control's own integrity list is the code doing the protecting. Enumerating inputs and
  policy files while omitting the evaluator is the normal shape of this, not an unusual
  one.
- **Manifesting the verifier is worth doing and is not sufficient.** Whoever rewrites the
  entry module deletes the verification call *in the same edit*, so a manifest checked by
  the thing being manifested closes tampering with every module except the one that
  matters most. The fix has to be **location**: execute the control from a copy the
  constrained principal cannot write to, with the manifest and detection as the layer
  that catches the rest.
- **Enumerate the writers by capability, not by the mechanism you modelled.** A policy
  that constrains shell commands does not constrain a file-writing tool, an editor
  integration, a language server, or a package manager doing an editable reinstall. Ask
  which *principals* can write the path, then which tools each of them has —
  `sota-skill-security` rules/02 §2 makes the same argument for instruction files, and
  this is the executable case of it.

**Not the same as `rules/14` §8.** There, a *benign* neighbouring process overwrites what
a control produced, and the fix is a predicate the innocent state fails. Here the actor is
the principal the control constrains, the target is the control's own code, and no
predicate on the output helps — the output is whatever the replacement chooses to say.

### 1c.1 Some residuals are protocol-level, and the obvious fix costs more than it buys

Where **"allow" is expressed as silence**, a control replaced by a no-op is byte-identical
to a permitted call. Nothing downstream can tell them apart, and a `|| deny` wrapper does
not fire — that wrapper exists for a *crash*, and this is not a crash.

The tempting fix is to make silence anomalous by emitting an explicit allow. Price it
first: an explicit allow can **override a separate permission layer** that was relying on
the same silence, trading a real defence for a tamper signal. That is a worse trade than
the residual.

So: **price a fix against the layer it disables.** Writing the residual down — as a named
test that documents what would not be detected, and an entry in whatever ledger records
accepted risk — and leaving it open can be the correct call. What is not correct is
leaving it undescribed, because the next reader cannot distinguish an accepted residual
from an oversight (`rules/15` §2).

## Audit checklist

- [ ] **Mutation probe run on security-critical paths** — control body replaced
      with the permissive no-op, with the dependency forced present and the
      mutation's **runtime effect asserted** before trusting a green run (§1)?
- [ ] Negative controls run as a **mode of the tool** (`--self-test`, `doctor`), not
      only as a harness beside it — a check with no declared known-bad fails the
      self-test, each probe asserts the **named** check caught it rather than
      accepting any non-zero exit, skips print their reason, and the run reports
      checks-probed over checks-registered (§1b)?
- [ ] Every **enforcement** control (cap, quota, filter, allowlist, sandbox
      policy) carries an **allow arm** as well as a deny arm — a representative
      legitimate case completing *through* the control, not against the bare
      environment — so "blocks everything" cannot read as "works" (§1a)?
- [ ] Structural tests added alongside the instance test — non-zero loaded rule
      count, every reference-config key resolving, documented default equal to
      parsed default, control telemetry actually emitted (§1)?
- [ ] Is the control's **own executable or source** on the list of things something
      protects, and is that list derived from what the decision **depends on** rather
      than from what was obvious when it was written (§1c)?
- [ ] Can the principal the control constrains **write to the control's own code**, by
      any tool — including tools the control does not model (an editor integration, a
      package manager, an editable reinstall), not just the mechanism its policy
      describes (§1c)?
- [ ] If the control were replaced by a **no-op**, could anything downstream tell? Where
      "allow" is silence the answer is **no** — say so explicitly, and record the
      residual rather than reaching for an explicit-allow signal that may override a
      separate permission layer (§1c.1).
