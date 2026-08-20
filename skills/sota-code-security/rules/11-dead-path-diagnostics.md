# Dead Paths — the diagnostics that expose a system reporting success while doing nothing

rules/10 asks, one control at a time, *"if this were a no-op, would anything look
different?"* This file is the **hunt**: the cheap signals that surface the family
across a whole codebase without reading every line, five classes rules/10 does
not cover (they are not security controls at all — they are correctness), and the
evidence bar a finding in this family has to clear.

Use it in AUDIT as the sweep that decides *where* to apply rules/10, and in BUILD
as the set of properties that make a stage falsifiable before you ship it.

Related: inert controls (the catalog) → rules/10; **proving a control works, and
validating the instrument or guard that reported it → rules/12**; fail-open authz
→ rules/03; truncation before inspection → rules/10 §2.7; mutation testing and
watching a test fail → `sota-testing` rules/06 and rules/09; degradation telemetry →
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
- [ ] **Environment-dependent predicates**: any filter tested against an absolute
      path, hostname, username, env var or locale — `grep -rn "\.parts\|os.environ\|
      gethostname" ` near a comprehension. Run the suite from a `mktemp -d` clone, not
      the working tree; on macOS that path resolves under `/private`, which is exactly
      the component such filters tend to exclude.
- [ ] **Every collection a suite iterates has a non-empty assertion** — without one an
      empty parameter set reports SKIPPED and the suite passes vacuously.
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

The commonest instance ships inside the toolchains themselves, **and they do not
agree with each other** — which is the whole point. Both verified by running them:
`go test ./...` over a package with no test files prints `? x [no test files]` and
**exits 0**; `pytest` on the same empty scope prints `no tests ran` and **exits 5**,
as it does for a file with no test functions and for a `-k` selector that deselects
everything (pytest 9.1.1). One fails closed, one fails green. So a test stage whose
selector drifts is silently green on one toolchain and loud on the next, and no
amount of folklore about "runners exit 0 when they find nothing" tells you which
you have. Gate on a floor for tests **actually executed**, never on the exit code,
and confirm your own runner's zero-collected behaviour by running it — an exit 5
that CI discards is worth exactly as much as an exit 0.

Rule for BUILD: a gate prints `ok (N items)`, and `N == 0` is a failure unless
zero is explicitly expected and asserted as such. Rule for AUDIT: for every gate,
ask what its denominator was on the last run, and whether anything would say so.

**The same arithmetic on the output side: a produced size that lands exactly on
its limit is a truncation report.** The cheapest tell in this family, and it
needs no cooperation from the producer — compare what came back against the cap
that bounded it (`output_tokens == max_tokens`, rows == `LIMIT`, bytes == the
buffer) and treat equality as truncated until shown otherwise. Field-reported
and reproduced 2026-08-19: a recon call left `max_tokens` unset, inherited a
4096 default, and a 4,843-character JSON fragment reached `json.loads` as a
plain string — no exception from the provider, no flag, and a swallowing
`except` (rules/10 §2.4) then published it as an empty profile. Corollary: **a
parse-error offset is uninterpretable without the document length.** "Failed at
char 3,023" argues *against* truncation while you assume 4,096 tokens yield
12–16k characters, and *for* it the moment you learn 3,023 was the last
character — so log the size beside the offset. Class and fix: rules/10 §2.7.

### 2.3 Cross-scale delta

Run the same stage on a small and a large input. **Output that does not grow with
input is suspect.** Findings, rows, log lines, bytes written, duration — pick a
quantity the work should move and compare the two runs. This is the cheap version
of `rules/13` §1: it catches a threshold-gated path without finding the threshold first.

### 2.4 Telemetry silence

A stage that emits no log lines cannot be distinguished from a stage that did
nothing. Silence is not evidence of health; it is absence of evidence. Any stage
on a data path emits at least a start/finish pair carrying its denominator
(§2.2). See rules/10 §3 for the degraded-control helper and the gauge that stays
1 while a control is degraded.

**The inverse also holds, and it is the harder half: speech is not evidence of health
either**, when the claim is sited *upstream* of the effect it describes. A line reading
`1 adjudicated` proves a count was computed there, not that the count survived the rest
of the function. Site the claim in the consumer, derived from the value received —
`rules/14` §1.

### 2.5 Did the changed code execute?

**After any fix, prove the new path ran.** A fix that is never reached is
indistinguishable from a fix that works — and both look like a green suite.

The cheap proof: make the new branch emit exactly once (a log line, a counter, a
one-shot `print`), run the real workload, and show the emission. **Placement is a
precondition of that proof**: an emission establishes that the line it sits on ran, not
that its result survived the suffix of the function — the filter, early return or
reassignment that comes after it. Put the emission where the value is *consumed*, or it
answers a weaker question than the one you asked (`rules/14` §1). The same trap
bites mutation testing: an editable install, a copied tree, a stale image, or
cached bytecode means the code you edited may not be the code that ran
(rules/12 §1). Assert the runtime effect before trusting any before/after result.

### 2.6 When you cannot state the right answer, state how it must change

The reason a tool emitting nothing survives review is that nobody holds an oracle
for its output. That difficulty has a name — the **test oracle problem** (Barr,
Harman, McMinn, Shahbaz & Yoo, *IEEE TSE* 41(5):507–525, 2015,
doi:10.1109/TSE.2014.2372785). You cannot write "the analyser should find 1,283
functions" for an arbitrary repository, so nothing in the pipeline contradicts
"it found 0", and §1's silent zero ships.

A **metamorphic relation** gets you an oracle anyway: you cannot state the
output, but you can state how it must *change*. Commit a fixture with N known
functions and assert the extracted count is N; add one and assert the count
rises; remove half and assert it falls. `sota-testing` rules/06 §4 owns the
technique for application code — the use here is different and cheaper. It is a
**liveness oracle for a tool whose correct output you do not know**, and it is
the one diagnostic in this file that catches an analyser emitting an
empty-but-well-formed artifact while exiting 0.

§2.3's cross-scale delta is the same idea without a fixture; the fixture buys you
an absolute assertion instead of a relative one, and it belongs in CI rather than
in an audit.

## 3. Five classes rules/10 does not cover

Moved to [`rules/13`](13-context-dependent-silence.md) — scale-dependent silence,
stale-artifact no-ops, format assumptions generalised from one sample, contract
drift at an undeclared seam, and location-dependent silence. §2's diagnostics are
how you notice one; `rules/13` is what you are looking at once you do.

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
| Vacuous control | **Mutation test.** Inject the exact failure the control claims to catch, run it, show it still reports green (rules/12 §1) |
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
   one — a gate you have never seen reject anything is unverified (rules/14 §4).
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
6. **Caches, tags, fingerprints** (`rules/13` §2).
7. **Feature flags and config**: is the value **read** *and also* **applied**? A
   config field that parses, validates, and is never plumbed to the code path it
   names is a silent no-op — distinct from rules/10 §2.5, where the flag *is*
   applied, just more broadly than its name claims. Trace one flag end-to-end
   from file to the branch it is supposed to control.
8. **In-band sentinels on a compared value** — a number whose domain includes an
   "absent/unknown/error" marker (`-1`, `0`, `""`, `9999-12-31`). It defeats a
   presence check (`-1` is truthy), and because it has an **ordering** it loses
   every `<` and wins every `>`, so a guard silently skips one way and fires
   spuriously the other. Grep the *producer* — one function returning the same
   constant from a not-found branch and an error branch — then look for the
   **asymmetric guard**: a comparison with one operand filtered against the
   sentinel and the other not. That asymmetry, not the constant, is the finding
   (`sota-architecture` rules/02 §8a).

Start by enumerating every gate, guard, and audit in the codebase. For each: read
the comment, read the code, then **make it fail on purpose**. The controls you
cannot make fail are the finding.

Do one thing before any of that reading: **run every script CI, a hook, or a
runbook references, and record which produce output and which do not.** A
measurement tool nobody has executed this quarter is presumed dead until it
prints something — the ones needing credentials, a daemon, a rules directory, a
model file, or a network fail in precisely the way a clean result looks, and one
environment change (auth switched on) kills them all at once.

## 7. Then turn the lens around

Every diagnostic above is run *by* something — a script, a gate, a scorer, a
grep. Each of those is a control by the definition in §1, and the sweep is not
finished until they have been held to the same standard: **rules/12** carries the
mutation probe, the bar an instrument must clear before its number is quoted, and
the guard that is an instance of what it guards. A finding produced by an
unvalidated instrument is not yet a finding.

---

## Audit checklist

- [ ] **Duration recorded per stage** and compared against the work claimed —
      any stage returning "nothing found" far faster than its claimed work allows
      flagged, with the measured seconds and input size (§2.1)?
- [ ] **Every gate reports its denominator** (`ok (N items)`), and an unexpected
      **zero scope fails closed** — no `0 checked, 0 failed, exit 0` anywhere (§2.2)?
- [ ] Every **generated** result checked against the cap that bounded it before
      parsing (`output_tokens == max_tokens`, rows == `LIMIT`), and parse-error
      offsets logged beside the document size (§2.2)?
- [ ] Cross-scale delta run on at least the stages that gate on size: output
      that does not grow with input investigated (§2.3)?
- [ ] No stage on a data path is **silent** — start/finish with counts (§2.4)?
- [ ] Any tool whose correct output cannot be stated carries a **metamorphic
      liveness check** in CI — a fixture with a known count, and an assertion
      that the count moves when the input does (§2.6)?
- [ ] After each fix, the **new path proven to have executed** (emission, counter,
      or asserted runtime effect), not just "tests pass" (§2.5)?
- [ ] Unbounded traversals/recursion/variable-length queries bounded, and every
      **size-gated path** exercised by a fixture that crosses the threshold (`rules/13` §1)?
- [ ] Truncating budgets degrade **loudly and in the returned value**
      (`coverage: partial`), never only in a log line (`rules/13` §1)?
- [ ] Every cache/tag/fingerprint key audited with "what input can change while
      the key stays constant?" — tool/ruleset **version** included (`rules/13` §2)?
- [ ] External-interface parsers validated against the **declared schema** and a
      real sample from the installed version, not one observed response; numeric
      parsing rejects trailing garbage (`rules/13` §3)?
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
      output** — not by each side's own tests (`rules/13` §4)?
- [ ] Every script CI, a hook or a runbook references **actually executed this
      pass**, the silent ones recorded as dead until proven otherwise (§6)?
- [ ] The tools that produced these findings held to the same standard —
      mutation probe, instrument bar, guard recursion (§7 → **rules/12**)?
