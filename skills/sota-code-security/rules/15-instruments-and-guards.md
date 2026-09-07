# The Things That Do The Checking — instruments, guards, and the tools you audit with

`rules/12` proves that a **specific control** works. This file turns the same
suspicion on **everything that did the proving**: the scorers, gates, benchmarks,
thresholds, watchers and guards — and the instrument you are auditing with right
now, including the command you just typed.

Split out of `rules/12` on 2026-09-06, at the seam that file's own subtitle named
(*"the mutation probe, **and** the things that do the checking"*). Section numbers
are **unchanged** across the move — §2, §2.1, §2.2, §2.2a, §2.3, §2.4 and §3 mean
here exactly what they meant there — so a citation that named a section still names
the same content, and only the file part of the reference changes. Invariant 18
resolves every `§` reference in `skills/`, which is what makes that safe to assert.

The asymmetry that earns these their own file is the one `rules/12` opens with, one
level up. A broken feature produces a complaint; **a broken verifier produces a green
tick or a number**, and both are believed, quoted, and put in a README. An instrument
is worse still, because its output is *used to decide something else* — so a defect in
it does not announce itself as a defect, it announces itself as a **finding**, a
**score**, or a **release**.

Two distinct shapes live here, and §3 is not a variant of §2:

- **§2 — the instrument.** It reports a number or a verdict that something else acts
  on. It fails by being *unable to fail*, by measuring a scope nobody read, or by
  generalising from one sample.
- **§3 — the guard that is an instance of what it guards.** The control that exists to
  prevent class X is itself an example of class X. An instrument reports a number; a
  guard renders a verdict, and a guard that cannot fail blocks nothing while appearing
  to block everything.

Use it in AUDIT as the pass that runs **after** `rules/10` and `rules/11` have produced
findings — a finding produced by an unvalidated instrument is not yet a finding — and in
BUILD whenever you write something whose output decides whether something else is OK.

Related: the mutation probe and where it lives → `rules/12`; the inert-control catalog →
`rules/10`; the codebase-scale sweep → `rules/11`; vacuous tests, mutation testing and
watching a security test fail → `sota-testing` rules/02, rules/06 and rules/09; the
audit-level evidence and refutation standard → `sota/rules/03` §2 and §4.

---

## 2. Your instrument is a control

A scorer, a quality gate, a benchmark, a coverage threshold, a lint config, a
dashboard — anything whose output decides whether something is **OK** — is a
control, and every rule in rules/10 and rules/11 applies to it. This is the most
commonly skipped application, because measurement code reads as scaffolding
rather than as production, and nobody threat-models scaffolding.

**The smallest instrument is the command you just typed.** A verification one-liner
is unlinted, unreviewed code that runs against the system under test, and when it is
wrong it manufactures a finding *about the product*. Before reporting anything that
rests on one, re-run it in the plainest form available — no unquoted expansion, no
pipe, one command — and compare. Three tells that the harness is the bug, not the
subject: a **usage error (exit 2) from the callee**, a result that contradicts a
passing unit test, and a status read through a pipe (`cmd | tail -1; echo $?` reports
`tail`). Shell-specific mechanics — zsh joining, `${pipestatus[1]}` vs
`${PIPESTATUS[0]}` — are in `sota-shell-scripting` rules/01 §3, which nothing will
route you to when the task does not look shell-shaped. That is exactly when it bites.
**A fourth tell has no usage error at all: a quoting bug can be the reason a probe never
fires.** In zsh an unquoted glob in a flag value (`grep --include=*.md`) aborts the
command under the default `NOMATCH`, and with the customary `2>/dev/null` that is
byte-identical to a genuine no-match — empty output, exit 1. The sweep you read as *"the
tree is clean"* may never have run: `sota-shell-scripting` rules/01 §3a.

### 2.1 Five failure modes specific to instruments

- **Unbounded or unread scope.** rules/11 §2.2 turned inward: an instrument must
  report what it examined, *and someone must read it*. A scorer that printed
  "851 files" for a ten-module service was reading a vendored virtualenv,
  third-party packages, and the project's own test assertions — `assert
  user.has(permission)` in a test file counted as an authorization control. The
  denominator was on screen and went unread, which is the failure rules/11 §2.2
  exists to prevent.
- **Generalised from one sample** (rules/13 §3, applied to yourself). Patterns
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
- **A probe that exercises a neighbouring property.** The probe works, the gate
  fails on demand, and the green it produces covers code it never touched. Field-
  reported: a gate whose known-bad corrupts a committed **canonical-encoding
  vector** caught none of three defects living in the *composition*, the
  *predicate* and the *write path*. The gate was not weak — it was **precise about
  the wrong thing**, and its passing is what let the other defects survive review.
  The tell is a probe that mutates a **fixture** rather than the artifact the
  control produces at runtime: a fixture probe proves the validator reads, and
  proves nothing about whether the writer still emits what the validator expects.
  **State the traversed path beside the probe — or beside the scan** — *"exercises
  the encoder, not the writer"*; *"reads the first positional arg, so keyword callers
  are invisible"* — then ask what else claims coverage from this gate's green. Where the control emits an artifact,
  probe by corrupting **what the control just produced**, not a stored copy of what
  it should have produced.

### 2.2 The bar

**Never trust a number from an instrument you have not watched produce a *wrong*
answer on purpose.** Before its output is quoted anywhere:

- **Two references, both in CI.** A known-bad input it must score at the floor and
  a known-good input it must score at the ceiling. If they do not separate, there
  is no measurement — only output. Keep them as fixtures, not as memories.
- **A negative control** for anything that classifies: an item that must *not* be
  flagged. A detector that flags everything scores perfectly on a positives-only
  corpus, and that is the corpus everyone builds first.
  **And where the classifier has an "everything else" branch, that branch must be
  proven reachable.** An unreachable fallback is worse than no classification: the
  caller stops hearing "unknown" and starts hearing a specific, wrong cause. A CI
  scan step classified its own failure as *policy violation* vs *infrastructure
  error* with `grep -qE '(^Total:|Severity:|CVE-[0-9]+-|vulnerability)'` — and the
  scanner logs `Vulnerability scanning is enabled` on **every** run, so the bare
  `vulnerability` alternative always matched and the infrastructure branch was dead
  code. An image missing from the node was reported as a policy failure. Two rules
  follow, and they are about *order* and *default*, not about better patterns:
  **test the definitive signal first** (an infrastructure error is conclusive; a
  finding-shaped pattern is a heuristic, and putting the cheap certain check ahead of
  it is what makes the fallback reachable), and **default the unknown case to the
  safe classification** — *"I could not tell"* must never render as *"it was your
  code"*. The tell here was internal to the output: a **"found vulnerabilities"
  verdict that named no vulnerabilities**. Detect it as you would any dead branch —
  feed one input of each class and assert each verdict appears at least once; a class
  you cannot produce is a branch that is decoration. This matters most once the
  classifier has been wired into an operator-facing message, which is where a broken
  classifier is given a confident voice (`sota-devsecops` rules/09 §4).
- **Abort, never warn, on a missing result.** If a run produced no parsable
  summary, exit non-zero. "No output" must never be readable as "nothing found".
- **Assert the mutation took** (rules/11 §2.5). Editable installs, copied trees,
  stale caches and vendored environments all mean the code you changed may not be
  the code that ran.
- **Sample and read before you count.** Report a count only after reading a
  sample of what it matched. A regex over prose over-counts hard — one such
  sweep reported 50 unearned claims (rules/14 §1) where reading found 8.
- **Validate on inputs where failure is possible.** "No false positives on three
  clean libraries" establishes nothing if none of them contains the construct the
  control keys on: it could not have failed. Pick inputs that *can* fail.
- **Read what your scanner's default configuration excludes, before quoting a clean run.**
  A tool can ship a default severity threshold that is silent about its most valuable
  detector. Field-reported: a constant-time analyser reports division and weak RNG by
  default and keeps its *warning* tier — secret-dependent branches, early-exit comparison,
  secret-indexed table lookups, variable-time encoding — switched off, so a default run says
  least about early-exit MAC comparison, which is the most common real timing bug there is
  (Lucky Thirteen). This is **not** the threshold *you* chose being too coarse
  (`sota-devsecops` rules/09 §6): you chose nothing, and the silence is the vendor's. Print
  the tool's effective configuration alongside its verdict and name the detector families
  that did not run.
- **When a wrapper reports an empty reason, go one layer down.** A CLI that
  swallows its child's log turns a named, fixable cause into "produced no
  output". The answer is usually one command deeper, not one hypothesis further.

### 2.2a Instruments that run over time

§2.2's **principle** holds everywhere: an unreadable result must never be readable as a
terminal answer. Its **remedy** does not. "Abort on a missing result" is right for an
instrument that runs **once** — a scorer, a scan, a gate. Abort on the first unreadable
read in one that runs *until a condition holds* — a watcher, a poller, a readiness or
completion check — and it dies on any transient failure. Because silence is a watcher's
**normal state**, a dead watcher and a waiting one are indistinguishable, so the event is
lost with no signal at all. Both directions are live defects:

| resolution of an unreadable read | result | how visible |
|---|---|---|
| fail **open** — treat it as "done" | invents a success | none: looks like the happy path |
| fail **closed by aborting** | the watch dies | none: looks like "still waiting" |

A binary done/not-done cannot express "I could not tell", so either resolution is wrong
some of the time. Use **four** states:

- **DONE** — only on a positively validated terminal signal. **Assert the success
  condition, never its negation**: validate the value is digits, then `[ "$n" -ge 1 ]`.
  Never `[ "$n" != "0" ]` — *every* error string satisfies it (verified: `""`, `error`,
  `null` and a usage message all compare `!= "0"`).
- **NOT DONE** — keep waiting.
- **GONE** — the target no longer exists: a job reaped after completion, a pod GC'd, a
  file rotated away. **Terminal and knowable, not unknown.** Collapsing it into UNKNOWN
  trades a false success for a false alarm and the watch never ends. Distinguish the two
  **at the source** — a `NotFound` is not a transport error — and when the target is gone,
  **fail over to its parent** (the CronJob's `lastSuccessfulTime`, the deployment, the
  directory), which outlives the instance and carries the outcome.
  **GONE is the state people delete while fixing the other bug**: field-reported, a first
  attempt had an explicit "no longer exists" branch, and rewriting it fail-closed replaced
  that branch with the unknown-counter — which then reported *"cannot read for 20min —
  probe is blind"* about a job that had simply been garbage-collected, while the API was
  reachable in the same second. The blindness signal worked exactly as designed and was
  still wrong, because the state model was missing a row.
- **UNKNOWN** — the read itself failed. Keep waiting, but **count consecutive unknowns**
  and emit blindness as its own event past a threshold. "I have not been able to observe
  this for N minutes" is a different fact from "not yet", and only one of them means the
  watch is worthless.

Cross-check the terminal signal against an **independent** one — the job's status field
against the scheduler's last-success timestamp; a process exit against the artifact it
should have written. A single field cannot detect its own read failure; two disagreeing
fields announce it.

Observed: a completion watcher reported success on a job that was 89% done and still
running, because a transient API read returned empty and the check was `!= "0"`. What
exposed it was a contradiction **inside its own output** — success printed beside a
last-success timestamp a week stale. That is the design rule: **make a watcher print the
independent signal next to its verdict**, so a false verdict has something to disagree
with. Shell mechanics: `sota-shell-scripting` rules/02 §2. The scope-and-predicate
version of this question is §3.

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

Four forms, all observed:

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
- **The guard whose scope is continuous but whose state is not.** A verifier
  that walks a sequence in chunks — a hash chain by epoch, a log by rotated
  file, a reconciliation by day — and **resets its carried state at each
  boundary**. It rejects every defect *inside* a chunk and is blind to the
  removal of a whole one, which is the cheapest edit available to whoever wants
  the record gone. Predicate right, traversal right, scope nominally complete:
  the checking stops at the seam between iterations, and nothing in the output
  distinguishes "all chunks verified" from "verified each chunk in isolation".
  Worked instance: `rules/04` §8, chained partitions.

The question to ask of every guard, gate, coverage assertion and tripwire:

> If the defect this exists for were present right now, would this fail?

Then **introduce the defect and check** — the same discipline `rules/12` §1 applies to a
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

For a guard that walks a sequence, that population includes the **seams**. An
injected defect lands inside one chunk, exercises the predicate, and never
touches the carry-over between chunks — so boundary cases have to be enumerated
deliberately: first chunk, last chunk, a whole interior chunk removed, an empty
chunk. Three of those four survive any amount of single-record mutation.

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

- [ ] **Every probe states the path it traverses**, and that statement is narrower than
      the gate's reputation. For each green gate, name one code path it does *not*
      exercise; if you cannot, the probe's scope has not been established.
- [ ] **Probes on artifact-producing controls corrupt the produced artifact**, not a
      committed fixture of it. A fixture-only probe survives a writer that has stopped
      writing what the validator expects.

- [ ] Any instrument that runs **over time** (watcher, poller, readiness or completion
      check): does it distinguish **not-yet** from **cannot-tell** *and from
      **target-gone*** (a `NotFound` is not a transport error), assert the terminal
      condition positively rather than as `!= 0`, bound the unknown state so persistent
      blindness is reported, and print an **independent** signal beside its verdict
      (§2.2a)?
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
- [ ] For any verifier that walks a sequence in chunks (chained epochs, rotated
      logs, daily partitions), is the **seam** probed as well as the interior —
      first/last chunk, a whole interior chunk removed, an empty chunk — rather
      than only single-record mutations that never reach the carry-over (§3)?
