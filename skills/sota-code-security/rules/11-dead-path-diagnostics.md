# Dead Paths — the diagnostics that expose a system reporting success while doing nothing

rules/10 asks, one control at a time, *"if this were a no-op, would anything look
different?"* This file is the **hunt**: the cheap signals that surface the family
across a whole codebase without reading every line, four classes rules/10 does
not cover (they are not security controls at all — they are correctness), and the
evidence bar a finding in this family has to clear.

Use it in AUDIT as the sweep that decides *where* to apply rules/10, and in BUILD
as the set of properties that make a stage falsifiable before you ship it.

Related: inert controls (the catalog) → rules/10; fail-open authz → rules/03;
truncation before inspection → rules/10 §2.7; mutation testing and watching a
test fail → `sota-testing` rules/06 and rules/09; degradation telemetry →
`sota-observability` rules/05; scale and cost → `sota-performance` rules/01;
shell/CI exit-code masking → `sota-shell-scripting` rules/01.

---

## 1. The governing observation: "zero" is a legitimate answer

A bug that produces a **wrong** answer gets caught, because someone compares it
to a right one. A bug that produces **no** answer — where "none" is a valid
result — is invisible by construction.

So the hunting ground is every place where:

    failure state == a valid success state

`0 results`, `nothing to do`, `all clean`, `no changes`, `exit 0`, an empty list,
`None`, `0.0`. **If you cannot distinguish "it ran and found nothing" from "it
never ran", that is a finding — whether or not it has fired yet.**

This is rules/10 §1 turned outward: there, per control; here, per pipeline stage,
gate, job, and query.

## 2. The diagnostics, highest yield first

### 2.1 Duration, not result

**The single highest-yield tell, and the only one that needs no code reading.**
Compare each step's wall time against the work it claims to have done. A stage
reporting "0 findings" in 5 s against a 300k-LOC target did not run. A test job
that finishes in 3 s, a migration that returns instantly, a backup that completes
suspiciously fast — same signal.

```
# Time every stage, then read the ratio, not the verdict.
$ time ./scan.sh corpus/          # claims: full AST scan, 40k files
real    0m2.104s                  # ← 40k files in 2s. It did not scan them.
```

What to record in a finding: the **measured** wall time, the input size, and the
order of magnitude the claimed work implies. "Fast" is not evidence; "2.1 s for
40k files, vs 6 min for the same corpus on the previous release" is.

Two refinements:

- **Constant duration across very different inputs** is the same tell without a
  baseline: if 100 files and 100k files take the same time, size is not reaching
  the work.
- **Duration that collapses after a change** is a regression signal. A scanner
  that got 30× faster and found the same number of issues did not get faster.

### 2.2 Scope of the check — print the denominator

**`0 checked, 0 failed, exit 0` is the signature of this entire family.** Every
gate must report *how many items it examined*, and must fail closed when that
number is unexpectedly zero. A gate whose file glob, pathspec, or selector
drifted keeps printing green forever.

This library shipped that exact defect and fixed it (2026-07-30). The gate
enumerated skill files via `git ls-files 'skills/*/rules/*.md'`; renaming the
`rules/` directory level made the pathspec match nothing:

```
# BEFORE — pathspec mutated to match nothing:
[2/10] Every skills/*/rules/*.md ends with an '## Audit checklist'
    ok
[10/10] Every skills/*/rules/*.md is referenced by its own SKILL.md
    ok
PASS: all repository invariants satisfied.        # exit 0, examined 0 files

# AFTER — the same mutation, once each check reported its denominator:
    SCOPE EMPTY: examined 0 rules files — pathspec drift? a gate that checks
    nothing passes silently
exit=1
```

A neighbouring check that recounted the tree did **not** catch it, because the
count it recounted (`SKILL.md` files) was unaffected — worth stating as its own
lesson: *one gate's green does not cover another gate's scope.*

The commonest instance ships inside the toolchains themselves: `go test ./...`
over a package with no test files prints `? x [no test files]` and **exits 0**
(verified 2026-08-04 on the installed Go). A test stage whose selector matches
nothing is therefore green by default in the place it matters most. Gate on a
floor for tests actually executed, never on the runner's exit code — and check
*your* runner's zero-collected behaviour rather than assuming it, they differ.

Rule for BUILD: a gate prints `ok (N items)`, and `N == 0` is a failure unless
zero is explicitly expected and asserted as such. Rule for AUDIT: for every gate,
ask what its denominator was on the last run, and whether anything would say so.

### 2.3 Cross-scale delta

Run the same stage on a small and a large input. **Output that does not grow with
input is suspect.** Findings, rows, log lines, bytes written, duration — pick a
quantity the work should move and compare the two runs. This is the cheap version
of §3.1: it catches a threshold-gated path without finding the threshold first.

### 2.4 Telemetry silence

A stage that emits no log lines cannot be distinguished from a stage that did
nothing. Silence is not evidence of health; it is absence of evidence. Any stage
on a data path emits at least a start/finish pair carrying its denominator
(§2.2). See rules/10 §4 for the degraded-control helper and the gauge that stays
1 while a control is degraded.

### 2.5 Did the changed code execute?

**After any fix, prove the new path ran.** A fix that is never reached is
indistinguishable from a fix that works — and both look like a green suite.

The cheap proof: make the new branch emit exactly once (a log line, a counter, a
one-shot `print`), run the real workload, and show the emission. The same trap
bites mutation testing: an editable install, a copied tree, a stale image, or
cached bytecode means the code you edited may not be the code that ran
(rules/10 §3). Assert the runtime effect before trusting any before/after result.

## 3. Four classes rules/10 does not cover

### 3.1 Scale-dependent silence — correct small, broken large

Code that is right on fixtures and pathological or wrong in production, where the
difference is a number nobody crossed in a test.

Shapes to look for:

- **Unbounded traversal**: recursion without a depth cap; variable-length graph
  queries with no bound (`[:AST*]` rather than `[:AST*1..12]`, Cypher
  variable-length patterns, SQL recursive CTEs without a depth column). Unbounded
  is not "thorough" — it is a query that times out and returns nothing on the
  inputs that matter most.
- **Whole-input reads**: loading a file, table, or response fully into memory.
- **Per-item queries inside a loop** over an unbounded set (N+1).
- **Budgets that truncate rather than fail** (time, size, row, token caps).
- **Paths gated behind a size threshold that fixtures never cross** — chunking,
  sharding, pagination, streaming, multi-part upload. The gated branch is
  effectively untested code that only ever runs in production.

The tell: **the threshold is a literal in the code and no fixture crosses it.**

**Budget exhaustion is the silent sub-case worth its own rule.** A stage that
logs `skipped 12 rules (budget exhausted)` at INFO and returns a normal-looking
result has reported *partial* coverage as *complete*. The consumer cannot tell
"clean" from "clean as far as we got". Rule: a truncating budget degrades loudly
(rules/10 §4) **and** the result carries the partiality in its own value —
`coverage: partial`, `skipped: 12`, a distinct status — never only in a log line.
An audit finding here is the missing field, not the budget.

Proof required: state the trigger **numerically** (threshold, node count, row
count) and show the fixtures never reach it. Measure at both scales where cheap.
Performance framing of the same code → `sota-performance` rules/01; the fixture
side → `sota-testing` rules/03.

### 3.2 Stale-artifact no-op — a key narrower than the behaviour

A cache, tag, fingerprint, or memo keyed on **fewer inputs than actually
determine the output**, so a real change is silently ignored and a stale artifact
is reused. Nothing errors; the pipeline is simply operating on last week's answer.

Ask of every key: **what input can change while the key stays constant?**

Where they hide: cache keys, memoization decorators, content hashes, image and
artifact tags, `if exists: skip`, lockfiles, generated code checked into the
repo, incremental-build stamps.

The usual omissions are not the source file — they are everything *around* it:
the tool or ruleset **version**, compiler/interpreter flags, the config that
selects behaviour, the environment or platform, and the schema the output is
shaped by. A scanner cache keyed on the target's hash but not on the ruleset
version keeps serving pre-rule-update results.

Proof required: change the omitted input, show the key is unchanged, and show the
stale artifact being reused (a cache-hit log, an unchanged output hash, a build
that skipped the step).

Rule for BUILD: the key covers every input that changes the output, tool versions
included; when unsure, add a version salt and take the cheap re-computation. See
`sota-devsecops` rules/04 for the security-relevant case (a cache key must also
carry the **trust context**, or a lower-trust build can poison a release).

### 3.3 Format assumption generalised from one sample

A parser built against one observed sample of an external interface, where a
sibling field, a newer version, or an edge case has another shape. Indexing into
external JSON/CSV (`x[0]`, chained `.get().get()`), assumed column counts, a
tagged union read as a flat record, an optional field treated as required.

**The silent sub-case: lenient parsers that accept malformed input and return a
plausible-but-wrong value** rather than raising. Verified 2026-07-30 on the
installed runtimes:

```js
parseInt("12abc")   // 12      — trailing garbage ignored
parseInt("")        // NaN     — which then propagates as a number
Number(" 12 ")      // 12      — surrounding whitespace accepted
```

```python
int(" 12 \n")       # 12       — whitespace accepted
float("1_0")        # 10.0     — underscore separators accepted: "1_0" is not 1.0
```

A corrupted or unexpected field therefore yields *a number*, not an error, and
every downstream stage treats it as data. This is a silent zero with a plausible
disguise.

Proof required: produce a **real sample from the installed version** that
violates the assumption — captured output, a recorded response, a fixture pulled
from the actual tool. Not a hypothetical.

Rule for BUILD: parse strictly at the boundary — reject trailing garbage, require
the declared type, validate against the interface's schema rather than against
the one response you saw — and record which interface **version** you validated
against, because that is the input §3.2 says your cache key is probably missing.

### 3.4 Contract drift by interaction — the seam nobody declared

Neither component is wrong. A change to a **producer** silently alters a layout
its **consumer** depends on: file name, directory shape, column order, separator,
units, encoding, per-label files where there was one combined file. Both sides
pass their own tests — each knows only its own side of the seam.

What separates this from §3.3 is *where the assumption lives*: §3.3 is a consumer
generalising from one sample of an external interface; this is an internal seam
**no schema describes**, so nothing exists for a registry or a compat check to
compare. Declared contracts are `sota-data-engineering` rules/04 and
`sota-testing` rules/04 — this class is what is left when none exists.

The high-yield trigger is a change that is not a code change: **selecting a
different backend, engine, driver, or frontend** for one class of input, where
the new one writes a different layout as a side effect. One config line moves,
the format change is undocumented, and the stage downstream reads zero rows and
reports "produced no output" — a silent zero (§1) with an innocent-looking cause.

Rule for BUILD: when you change a producer, **run the consumer on that
producer's real output** before merging; isolation tests pass on both sides while
the seam is broken. Rule for AUDIT: for every artifact handed between stages,
name its layout, its writer and its reader — where no schema pins them, the pair
is a finding awaiting its first change.

## 4. An assert is not a control in production

An assertion is a developer-facing invariant check. In three major runtimes it is
**removed or disabled** in the configuration production most often runs, so a
control implemented as an assert is a guaranteed no-op there. Verified
2026-07-30 by running each case:

| Runtime | Command | Result |
|---|---|---|
| Python | `python3 -O prog.py` / `PYTHONOPTIMIZE=1` | failing `assert` vanished; program printed `passed` |
| C/C++ | `cc -DNDEBUG` | `assert(x>0)` compiled out; program printed `passed` |
| Java | default `java` (no `-ea`) | assertions are **disabled by default** at runtime |

Java's own documentation states it plainly: *"By default, assertions are disabled
at runtime"*, and once disabled they are *"essentially equivalent to empty
statements in semantics and performance"*
([Oracle, Programming with Assertions](https://docs.oracle.com/javase/8/docs/technotes/guides/language/assert.html)).

Rules:

- **Never** implement validation, authorization, bounds, or any
  data-integrity check as an assert. Use an explicit conditional that raises,
  returns a denial, or exits — code that survives optimisation flags.
- Asserts are fine for *impossible* internal states you want loud in development.
- AUDIT: grep for assertions on validation, authz, size, and parsing paths, then
  check what flags the **deployment** actually uses (`-O`, `NDEBUG`,
  `PYTHONOPTIMIZE`, the absence of `-ea`). A control removed by a build flag is
  the purest form of this family: source code that reads correct and does not
  exist at runtime.

Language specifics: `sota-python` rules/05, `sota-c-cpp` rules/04, `sota-jvm`
rules/04.

## 5. Evidence — one discriminating proof per finding

Evidence must **distinguish broken from fine**. Reasoning is not evidence, and a
mechanism you did not trigger is not a confirmed finding.

| Class | The proof that discriminates |
|---|---|
| Vacuous control | **Mutation test.** Inject the exact failure the control claims to catch, run it, show it still reports green (rules/10 §3) |
| Silent zero | Show the failure return is **identical** to the success-but-empty return, and name **one consumer** that cannot distinguish them |
| Scale-dependent | State the trigger numerically; show fixtures never cross it; measure both scales where cheap |
| Stale artifact | Change the omitted input; show the key unchanged and the stale artifact reused |
| Format assumption | A **real** sample from the installed version that violates the assumption |

Label every finding exactly one of:

- **ACTIVE** — proven to have fired. Cite the log line, output, or measurement.
- **LATENT** — mechanism verified in the code; verified **not** to have fired,
  and you say how you checked. Report it; do not inflate it to ACTIVE.
- **REFUTED** — you suspected it and the evidence says no. **Report these too**:
  a refuted suspicion stops the next auditor re-raising it (`sota/rules/01` §7).

**Not findings** (disqualifiers):

- "This could fail if…" with no proof that it does, or that no guard exists.
- A control you called vacuous but never made fail.
- Any conclusion drawn from a name, comment, or docstring rather than the code.
  Comments are a **hypothesis** about behaviour and are themselves prime hunting
  ground — a comment describing a check the code does not implement is the
  canonical vacuous control.
- Anything you cannot tie to a `file:line`, a command's output, or a log line.

**Rank by blast radius × silence.** A loud partial failure outranks nothing; a
silent total failure outranks everything.

**Fix + risk — state whether the fix moves a decision boundary.** Making an inert
detector work changes what the system reports. If the fix alters a decision
boundary (a scanner that now fires, a validator that now rejects), it needs
validation against a **labelled corpus — known-bad and known-good — before
shipping**, or you trade a silent miss for a silent flood, and the flood gets the
control switched off. Say so in the finding rather than shipping the fix blind.

## 6. Where to hunt, in order

1. **Every gate**: CI jobs, pre-commit hooks, health and readiness checks,
   admission/validation webhooks, authz checks, quality gates. Mutation-test each
   one — a gate you have never seen reject anything is unverified (rules/10 §2.13).
2. **The tests *of* those gates**: does any test assert the gate **fails** on bad
   input? Happy-path-only tests are how vacuous controls survive review
   (`sota-testing` rules/09).
3. **Error handling on the main data path** — every catch/except between input
   and output (rules/10 §2.4).
4. **Fallback, retry, degrade, and "continue anyway" branches** — verify the
   fallback *actually engages*. A log line saying it will is not proof that it does.
5. **Shell and CI glue**: pipelines without `pipefail` mask a non-final failure;
   globs that match nothing; `find -exec` over an empty set; `|| true`; any
   command whose exit code is discarded (`sota-shell-scripting` rules/01).
6. **Caches, tags, fingerprints** (§3.2).
7. **Feature flags and config**: is the value **read** *and also* **applied**? A
   config field that parses, validates, and is never plumbed to the code path it
   names is a silent no-op — distinct from rules/10 §2.5, where the flag *is*
   applied, just more broadly than its name claims. Trace one flag end-to-end
   from file to the branch it is supposed to control.

Start by enumerating every gate, guard, and audit in the codebase. For each: read
the comment, read the code, then **make it fail on purpose**. The controls you
cannot make fail are the finding.

Do one thing before any of that reading: **run every script CI, a hook, or a
runbook references, and record which produce output and which do not.** A
measurement tool nobody has executed this quarter is presumed dead until it
prints something — the ones needing credentials, a daemon, a rules directory, a
model file, or a network fail in precisely the way a clean result looks, and one
environment change (auth switched on) kills them all at once.

## 7. The instrument that measures a control is itself a control

A scorer, a quality gate, a benchmark, a coverage threshold, a lint config, a
dashboard — anything whose output decides whether something is **OK** — is a
control, and every rule in this file applies to it. This is the most commonly
skipped application, because measurement code reads as scaffolding rather than as
production, and nobody threat-models scaffolding.

The asymmetry is what makes it dangerous. A broken feature produces a complaint.
**A broken instrument produces a number** — and numbers are believed, quoted, and
put in a README.

### 7.1 Four failure modes specific to instruments

- **Unbounded or unread scope.** §2.2 turned inward: an instrument must report
  what it examined, *and someone must read it*. A scorer that printed "851 files"
  for a ten-module service was reading a vendored virtualenv, third-party
  packages, and the project's own test assertions — `assert user.has(permission)`
  in a test file counted as an authorization control. The denominator was on
  screen and went unread, which is the failure §2.2 exists to prevent.
- **Generalised from one sample** (§3.3, applied to yourself). Patterns written
  against a single reference implementation flag every *other* correct spelling:
  a check keyed on the method name that reference happened to use; a rule that
  flagged the *correct* fix because the safe spelling shared a shape with the
  unsafe one; a matcher that could not follow a check extracted into a helper;
  a slice-detector that could not tell "scan a prefix" from "scan in chunks".
  Every one punished code **better** than the sample it was written against.
- **Errors run both ways, and only one direction gets investigated.** The same
  instrument that penalises a good implementation can excuse a real defect —
  flat text matching once credited an unprotected read path with the ownership
  check belonging to a sibling function. The excusing direction is the one nobody
  chases, because it agrees with the hoped-for result.
- **The guard that is an instance of what it guards.** Least intuitive, highest
  yield: the control existing to prevent class X is itself an example of it.
  Three real forms — a test asserting "*every* call site passes auth" that
  scanned one directory and accepted `auth=None`, its predicate being `"auth=" in
  line` (wrong **scope** *and* a predicate the defect satisfies); a tripwire
  nested inside another gate's success branch, so items failing the outer gate
  got neither; a coverage audit whose denominator counts only items that survived
  earlier filtering. Ask of every guard: **if the defect this exists for were
  present now, would it fail?** Then introduce it and check. §2.2 catches an
  *empty* scope; this catches one merely wrong, and a predicate merely weak.
- **The instrument that cannot fail.** A scorer returning a plausible number
  whatever it is handed. A mutation harness reporting **18/18 controls caught**
  while every run died before the test suite started — each non-zero exit read as
  "caught". Both look exactly like success.

### 7.2 The bar

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
- **Assert the mutation took** (§2.5). Editable installs, copied trees, stale
  caches and vendored environments all mean the code you changed may not be the
  code that ran.
- **Sample and read before you count.** Report a count only after reading a
  sample of what it matched. A regex over prose over-counts hard — one such
  sweep reported 50 unearned claims (rules/10 §2.10) where reading found 8.
- **Validate on inputs where failure is possible.** "No false positives on three
  clean libraries" establishes nothing if none of them contains the construct the
  control keys on: it could not have failed. Pick inputs that *can* fail.
- **When a wrapper reports an empty reason, go one layer down.** A CLI that
  swallows its child's log turns a named, fixable cause into "produced no
  output". The answer is usually one command deeper, not one hypothesis further.

### 7.3 Changing an instrument after you have seen results

Sometimes correct: a demonstrable false negative is a defect, not an
inconvenience. It is also exactly how a result gets massaged into the shape
someone wanted. So make it auditable — **say that you changed it, why, and the
before/after numbers; show the references still separate; and confirm no case's
ranking moved for any reason other than the fix.** An instrument quietly widened
after a disappointing run is indistinguishable from a fabricated one.

---

## Audit checklist

- [ ] **Duration recorded per stage** and compared against the work claimed —
      any stage returning "nothing found" far faster than its claimed work allows
      flagged, with the measured seconds and input size (§2.1)?
- [ ] **Every gate reports its denominator** (`ok (N items)`), and an unexpected
      **zero scope fails closed** — no `0 checked, 0 failed, exit 0` anywhere (§2.2)?
- [ ] Cross-scale delta run on at least the stages that gate on size: output
      that does not grow with input investigated (§2.3)?
- [ ] No stage on a data path is **silent** — start/finish with counts (§2.4)?
- [ ] After each fix, the **new path proven to have executed** (emission, counter,
      or asserted runtime effect), not just "tests pass" (§2.5)?
- [ ] Unbounded traversals/recursion/variable-length queries bounded, and every
      **size-gated path** exercised by a fixture that crosses the threshold (§3.1)?
- [ ] Truncating budgets degrade **loudly and in the returned value**
      (`coverage: partial`), never only in a log line (§3.1)?
- [ ] Every cache/tag/fingerprint key audited with "what input can change while
      the key stays constant?" — tool/ruleset **version** included (§3.2)?
- [ ] External-interface parsers validated against the **declared schema** and a
      real sample from the installed version, not one observed response; numeric
      parsing rejects trailing garbage (§3.3)?
- [ ] **No security, authz, bounds, or data-integrity check implemented as an
      `assert`**, and the deployment's flags (`-O`, `NDEBUG`, `PYTHONOPTIMIZE`,
      missing `-ea`) checked against any assert on a control path (§4)?
- [ ] Every finding carries a **discriminating proof** for its class, and is
      labelled **ACTIVE / LATENT / REFUTED** — refuted ones reported too (§5)?
- [ ] Findings ranked by **blast radius × silence**, and any fix that moves a
      decision boundary flagged as needing labelled known-bad/known-good
      validation before shipping (§5)?
- [ ] Config and feature flags traced **end-to-end**: read, validated, *and*
      applied to the branch they name (§6.7)?
- [ ] Every artifact handed **between stages** has its layout, writer and reader
      named, and any producer change validated by **running the consumer on real
      output** — not by each side's own tests (§3.4)?
- [ ] Every script CI, a hook or a runbook references **actually executed this
      pass**, the silent ones recorded as dead until proven otherwise (§6)?
- [ ] Each guard asked the recursive question — **if the defect it exists for
      were present now, would it fail?** — checking its *scope* and whether its
      *predicate* is satisfied by the defect itself (§7.1)?
- [ ] Counts reported only after **reading a sample** of what matched, and any
      clean-corpus validation done on inputs that **could** have failed (§7.2)?
- [ ] **Every instrument treated as a control** — each scorer, gate, benchmark and
      threshold has a known-bad reference it scores at the floor and a known-good
      one it scores at the ceiling, both wired into CI (§7.2)?
- [ ] Each instrument **reports what it examined**, and that denominator was
      actually read — no scanning of vendored environments, third-party packages,
      or the project's own tests as if they were product code (§7.1)?
- [ ] Classifying harnesses carry a **negative control**, and a run producing no
      parsable summary **aborts** rather than reading as "nothing found" (§7.2)?
- [ ] Any instrument changed **after** results were seen is disclosed with the
      before/after numbers and evidence that no ranking moved for another reason (§7.3)?
