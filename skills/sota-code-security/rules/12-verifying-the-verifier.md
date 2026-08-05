# Verifying the Verifier — the mutation probe, and the things that do the checking

rules/10 catalogs controls that look enabled and do nothing. rules/11 is the
sweep that finds them at codebase scale. This file is the third move, and the one
most often skipped: **proving that a specific control works, and then turning the
same suspicion on everything that did the proving** — the tests, the gates, the
scorers, the guards, and the instrument you are auditing with right now.

The reason it earns its own file is an asymmetry. A broken feature produces a
complaint. **A broken verifier produces a green tick or a number**, and both are
believed, quoted, and put in a README. Nothing downstream distinguishes "we
checked and it was fine" from "the check could not have failed".

Use it in BUILD to decide whether a control you just wrote is actually held in
place by anything, and in AUDIT as the pass that runs *after* rules/10 and
rules/11 have produced findings — because a finding produced by an unvalidated
instrument is not yet a finding (§2, §3).

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

Related: the inert-control catalog → rules/10; the codebase-scale sweep →
rules/11; vacuous tests in general, mutation testing, and watching a security
test fail → `sota-testing` rules/02, rules/06 and rules/09; the audit-level
evidence and refutation standard → `sota/rules/01` §5 and §7.

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
- **The mutation did not take.** Editable installs, copied/rsync'd trees, stale
  bytecode, and cached images mean the original code may still be running.
  **Assert the mutation's runtime effect** — make the no-op print or raise once —
  before trusting a "zero failures" result.

Then build the **structural** test that catches the class: assert the loaded rule
count is non-zero, assert every reference-config key resolves, assert the
documented default equals the parsed default, assert the control's telemetry is
emitted. Instance tests catch today's bug; structural tests catch the next one.

## 2. Your instrument is a control

A scorer, a quality gate, a benchmark, a coverage threshold, a lint config, a
dashboard — anything whose output decides whether something is **OK** — is a
control, and every rule in rules/10 and rules/11 applies to it. This is the most
commonly skipped application, because measurement code reads as scaffolding
rather than as production, and nobody threat-models scaffolding.

### 2.1 Four failure modes specific to instruments

- **Unbounded or unread scope.** rules/11 §2.2 turned inward: an instrument must
  report what it examined, *and someone must read it*. A scorer that printed
  "851 files" for a ten-module service was reading a vendored virtualenv,
  third-party packages, and the project's own test assertions — `assert
  user.has(permission)` in a test file counted as an authorization control. The
  denominator was on screen and went unread, which is the failure rules/11 §2.2
  exists to prevent.
- **Generalised from one sample** (rules/11 §3.3, applied to yourself). Patterns
  written against a single reference implementation flag every *other* correct
  spelling: a check keyed on the method name that reference happened to use; a
  rule that flagged the *correct* fix because the safe spelling shared a shape
  with the unsafe one; a matcher that could not follow a check extracted into a
  helper; a slice-detector that could not tell "scan a prefix" from "scan in
  chunks". Every one punished code **better** than the sample it was written
  against.
- **Errors run both ways, and only one direction gets investigated.** The same
  instrument that penalises a good implementation can excuse a real defect —
  flat text matching once credited an unprotected read path with the ownership
  check belonging to a sibling function. The excusing direction is the one nobody
  chases, because it agrees with the hoped-for result.
- **The instrument that cannot fail.** A scorer returning a plausible number
  whatever it is handed. A mutation harness reporting **18/18 controls caught**
  while every run died before the test suite started — each non-zero exit read as
  "caught". Both look exactly like success.

### 2.2 The bar

**Never trust a number from an instrument you have not watched produce a *wrong*
answer on purpose.** Before its output is quoted anywhere:

- **Two references, both in CI.** A known-bad input it must score at the floor and
  a known-good input it must score at the ceiling. If they do not separate, there
  is no measurement — only output. Keep them as fixtures, not as memories.
- **A negative control** for anything that classifies: an item that must *not* be
  flagged. A detector that flags everything scores perfectly on a positives-only
  corpus, and that is the corpus everyone builds first.
- **Abort, never warn, on a missing result.** If a run produced no parsable
  summary, exit non-zero. "No output" must never be readable as "nothing found".
- **Assert the mutation took** (rules/11 §2.5). Editable installs, copied trees,
  stale caches and vendored environments all mean the code you changed may not be
  the code that ran.
- **Sample and read before you count.** Report a count only after reading a
  sample of what it matched. A regex over prose over-counts hard — one such
  sweep reported 50 unearned claims (rules/10 §2.10) where reading found 8.
- **Validate on inputs where failure is possible.** "No false positives on three
  clean libraries" establishes nothing if none of them contains the construct the
  control keys on: it could not have failed. Pick inputs that *can* fail.
- **When a wrapper reports an empty reason, go one layer down.** A CLI that
  swallows its child's log turns a named, fixable cause into "produced no
  output". The answer is usually one command deeper, not one hypothesis further.

### 2.3 Changing an instrument after you have seen results

Sometimes correct: a demonstrable false negative is a defect, not an
inconvenience. It is also exactly how a result gets massaged into the shape
someone wanted. So make it auditable — **say that you changed it, why, and the
before/after numbers; show the references still separate; and confirm no case's
ranking moved for any reason other than the fix.** An instrument quietly widened
after a disappointing run is indistinguishable from a fabricated one.

### 2.4 Evidence the subject supplies about itself

An instrument that accepts the evaluated party's own report of its result is not
measuring, it is transcribing. The failure mode is not that subjects lie — it is
that the cheapest passing artifact wins and nothing in the loop prefers a real
one.

The scale of it has now been measured. A study of the EvoMap agent-to-agent
network (1.5M assets, 128K agents) found that **"over 84% of approved assets
bypass quality checks using vacuous tests (e.g. `console.log()`)"** — the
platform asked agents to submit their own local execution logs as evidence of
correctness, and nothing independent re-ran them
([arXiv:2605.25815](https://arxiv.org/abs/2605.25815), 2026). Approval stayed
near-total and meant nothing.

Rule: **the party under evaluation never supplies the evidence of its own
evaluation.** Re-execute the check somewhere you control, or verify the artifact
against something the subject cannot author — a hash you computed, a count you
took, a log the harness emitted. This binds CI jobs that report their own status,
vendors self-attesting to a control, and any model asked to grade its own output
(`sota-llm-engineering` rules/01 on judges; `rules/08` §1 on same-class checkers).

## 3. The guard that is an instance of what it guards

The least intuitive shape in this whole family, and the highest-yield: **the
control that exists to prevent class X is itself an example of class X.** It is
not a variant of §2 — an instrument reports a number, a guard renders a verdict,
and a guard that cannot fail blocks nothing while appearing to block everything.

Three forms, all observed:

- **The predicate the defect satisfies.** A test asserting "*every* driver call
  site passes auth" that scanned only one directory **and** accepted `auth=None`
  as passing, because the predicate it used was `"auth=" in line`. Both halves
  are wrong independently: the **scope** missed the call sites that mattered
  (including the lint gate itself), and the **predicate** is satisfied by the
  exact defect it was written to catch.
- **The guard nested inside another gate's success branch.** A regression
  tripwire placed inside a frozen-evidence block, so the targets with missing
  evidence — the ones needing protection most — received neither check.
- **The denominator that counts only survivors.** A coverage audit computed over
  the items that made it past earlier filtering reports high coverage of a
  population it has already narrowed. rules/11 §2.2 catches an *empty* scope;
  this is a scope that is merely **wrong**, which prints a healthy number.

The question to ask of every guard, gate, coverage assertion and tripwire:

> If the defect this exists for were present right now, would this fail?

Then **introduce the defect and check** — the same discipline §1 applies to a
control, applied to the thing that checks the control. A guard you have not
watched reject something is a guard with an unverified predicate, and its scope
is unverified until you have seen what it enumerated (rules/11 §2.2).

**Verify per target, not once.** A guard protects a *population*: 20 call sites,
40 modules, every route. Watching it reject one member proves the predicate can
fire and says nothing about the other 19. Inject the defect into **each** member
and assert the guard trips for every one. The real shape this catches is a
tripwire that fired for 2 of 20 targets and stayed green for the remaining 18 —
indistinguishable from full coverage on any single-instance test. For a security
gate the acceptable kill rate is **100%**: unlike a code mutation score, where
surviving mutants are triaged and a number below 1.0 is normal
(`sota-testing` rules/06), a gate that misses its own target defect on a member
of its population is simply void for that member.

The oldest name for the underlying error is **vacuous satisfaction** — a
conditional that holds because its antecedent is never true. "Every call site
passes auth" is vacuously true over zero call sites, and the check reports the
same green it would report over a thousand correct ones. Ball and Kupferman's
*Vacuity in Testing* quotes the original hardware-verification result: "typically
20% of specifications pass vacuously during the first formal-verification runs of
a new hardware design, and vacuous passes always point to a real problem in
either the design or its specification or environment." Treat a green from an
unstated denominator as vacuous until you have seen the denominator.

One corollary worth stating on its own: **one gate's green does not cover another
gate's scope.** Two checks over what looks like the same tree can enumerate
different sets, and the one that still passes tells you nothing about the one
whose pathspec drifted.

---

## Audit checklist

- [ ] **Mutation probe run on security-critical paths** — control body replaced
      with the permissive no-op, with the dependency forced present and the
      mutation's **runtime effect asserted** before trusting a green run (§1)?
- [ ] Structural tests added alongside the instance test — non-zero loaded rule
      count, every reference-config key resolving, documented default equal to
      parsed default, control telemetry actually emitted (§1)?
- [ ] **Every instrument treated as a control** — each scorer, gate, benchmark and
      threshold has a known-bad reference it scores at the floor and a known-good
      one it scores at the ceiling, both wired into CI (§2.2)?
- [ ] Each instrument **reports what it examined**, and that denominator was
      actually read — no scanning of vendored environments, third-party packages,
      or the project's own tests as if they were product code (§2.1)?
- [ ] Classifying harnesses carry a **negative control**, and a run producing no
      parsable summary **aborts** rather than reading as "nothing found" (§2.2)?
- [ ] Counts reported only after **reading a sample** of what matched, and any
      clean-corpus validation done on inputs that **could** have failed (§2.2)?
- [ ] Any instrument changed **after** results were seen is disclosed with the
      before/after numbers and evidence that no ranking moved for another
      reason (§2.3)?
- [ ] Each guard, gate and coverage assertion asked the recursive question — **if
      the defect it exists for were present now, would it fail?** — with its
      *scope* enumerated and its *predicate* checked against the defect itself,
      not merely read (§3)?
- [ ] Guards verified **per target**, not once — the defect injected into every
      member of the protected population, kill rate **100%** for a security gate,
      and no "every X passes Y" green accepted without its denominator (§3)?
- [ ] No control accepting the **evaluated party's own report** as evidence —
      re-executed where you control it, or checked against an artifact the
      subject could not author (§2.4)?
- [ ] No guard nested inside another gate's success branch, and no coverage
      denominator computed over survivors of earlier filtering (§3)?
