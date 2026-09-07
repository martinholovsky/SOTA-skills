# Gates That Hold — a gate that can fail, still covers you, and says why

`rules/05` covers the scanners: what to run, where, and how to read what they emit.
This file covers the harder question — **whether any of it actually gates**, which is
a property of the pipeline around the scanner rather than of the scanner.

Split out of `rules/05` on 2026-09-06, from the subsection *"Gates that don't get
bypassed"*, which had reached 284 lines — more than half that file. Its five subsections
were unnumbered and gained numbers in the move (§1–§5 here), so an older citation of that
subsection means this file as a whole.

Five distinct ways a gate stops gating, in the order they are usually discovered:

| § | The gate… | and the tell is |
|---|---|---|
| **1** | is not *required*, or is bypassed | a green compliance answer that no framework asks to be falsifiable |
| **2** | can no longer **fail** | the known-bad still gets rejected, but from a scope that shrank |
| **3** | ran, failed, and the artifact **shipped anyway** | a verification error at the consumer, three steps from the cause |
| **4** | failed for a reason nobody can **recover** | `Error (exit code 1)`, and the pod is gone |
| **5** | is clean when *you* run it, red when **CI** does | "all gates pass" said before the push |

§1 and §2 are about the gate's *authority and scope*. §3 and §4 come from one incident
and are two halves of the same failure — the artifact escaped, and then the error message
sent the operator to the wrong subsystem. §5 is the inverse of §2: the code is in scope,
the gate sees it, and the human's local re-run asks a different question.

**The thread through all five** is `sota-code-security` rules/15's: a gate is an
instrument, and an instrument that cannot produce a wrong answer on demand has not been
verified. What this file adds is that a gate can be perfectly capable of failing and still
gate nothing — because of *when* it runs, *what* it can still see, or *whether anyone can
read its verdict afterwards*.

Related: probing a control → `sota-code-security` rules/12; instruments and guards →
`sota-code-security` rules/15; the scanners themselves → `rules/05`; pipeline identity,
permissions and provenance → `rules/01` and `rules/02`.

---


## 1. What the standards ask for — and the one thing none of them ask

Worth knowing precisely, because it bounds what a green compliance answer is
worth. Two frameworks require **evidence the scan ran**:

- **NIST SSDF (SP 800-218 v1.1)** — **PW.8.2**: "Scope the testing, design the
  tests, perform the testing, and document the results, including recording and
  triaging all discovered issues and recommended remediations…". **PO.3.3**:
  "Configure tools to generate artifacts of their support of secure software
  development practices as defined by the organization" — where the document's
  own footnote defines an artifact as "a piece of evidence".
- **EU CRA (Regulation (EU) 2024/2847)** — Annex VII requires the technical
  documentation to contain "reports of the tests carried out to verify the
  conformity of the product with digital elements and of the vulnerability
  handling processes with the applicable essential cybersecurity requirements".

One does not even require that. **OpenSSF Scorecard's SAST check detects tool
*presence*** — it "looks for known GitHub apps such as CodeQL
(github-code-scanning) or SonarCloud … or the use of 'github/codeql-action' in a
GitHub workflow". Its Dependency-Update-Tool check says so outright: it "can
determine only whether the dependency update tool is enabled; it does not ensure
that the tool is run". Only CI-Tests reads an outcome, and it "only considers
tests which run successfully".

**None of them require evidence that the gate is capable of failing.** A scanner
misconfigured to scan zero files satisfies every clause above and yields a
documented, attestable record of having found nothing — SLSA will even sign
provenance proving that the scan executed, because provenance covers *how the
artifact was built*, never whether the scan was semantically capable of a
finding. So treat a passing compliance check as evidence of process, not of
protection. The missing evidence is a **negative control** — a committed
known-bad the gate must reject on every run — and it is not asked for by any
mainstream framework, which is exactly why it has to be a house rule
(`sota-code-security` rules/12 §1 and `rules/15` §3).

*(SSDF and Scorecard wording verified against the primary documents 2026-08-05;
the CRA sentence verified against published copies of the regulation text rather
than EUR-Lex directly — confirm the Annex VII point number before quoting it in
a filing.)*

The mechanics that make everything above real:

- **Required status checks, by exact job name**, in branch protection/rulesets. A check
  that isn't required is a suggestion. Gotchas:
  - A *skipped* job satisfies "required" on GitHub if path-filtered — when using
    `paths:`/conditional jobs, required gates need a fallback (a no-op job with the same
    name on the excluded paths, or no path filter on gates).
  - Renaming a job silently un-requires it (the protection references the old name) —
    review ruleset config when workflows change; alert on required-check list drift.
- **No `continue-on-error: true`, `|| true`, `set +e`, or `exit 0` tails on gate steps.**
  Audit grep across workflows; every hit on a security/test job is a finding (Medium-High).
  Same for tools invoked with their own "don't fail" flags (`--exit-code 0`, `--soft-fail`,
  `npm audit || true`).
- **Rulesets apply to admins**; bypass lists are empty or break-glass-only with audit
  (rules/07 §7.5). `[skip ci]` must not be honored on protected branches' required gates
  (merge queue or push-triggered verification covers post-merge).
- **Merge queue** for busy repos: re-runs required checks on the actual merge result —
  closes the "green on stale base, broken on main" hole and the approve-then-push race
  (pairs with dismiss-stale-approvals, rules/01 §1.7).
- Gate jobs must not be modifiable by the change they gate, where the threat model demands
  it: reusable workflows from a protected repo (rules/01 §1.8) — otherwise a PR can edit
  the workflow to neuter the gate that judges the PR. (CODEOWNERS on workflows + required
  review mitigates; required *workflows* / org rulesets solve it properly.)

Audit greps for bypass patterns (run across `.github/workflows/`, CI config, Makefiles):

```
continue-on-error: true        # on gate jobs/steps
|| true     || exit 0     ; true
set +e                         # without a matching set -e re-arm
--soft-fail   --exit-code 0   --no-fail   --exit-zero
npm audit || …    audit-level  none
allow_failure: true            # GitLab equivalent
failFast: false                # fine for matrices; check what consumes the result
if: always()                   # on steps that should be conditional on success
```

Each hit needs a justification or a finding. Also diff the branch-protection/ruleset
required-checks list against the actual workflow job names — orphaned required checks
(job renamed/deleted) either block everything (visible, gets fixed) or, with
"required check expected but not run" semantics misconfigured, silently stop gating.

## 2. The negative control proves the gate *can* fail — not that it still covers you

A committed known-bad answers "can this gate fail?". It never answers "does this
gate still see the code that matters?", and the two come apart the moment somebody
refactors.

**Where the known-bad lives decides whether it survives.** A fixture beside the gate
proves *today's* gate can fail and says nothing about the gate added next sprint,
because joining the fixture set is a convention — enforced by a line in a contributing
guide and by whoever reviews the PR. Prefer a **`--self-test` mode of the gate runner**
that walks the same registry of checks the normal run walks, injects each check's
declared known-bad, and asserts *that check, by name*, is the one that complains. A
check with no declared known-bad then **fails the self-test** instead of being silently
exempt, and the probe ships to the operator rather than living only in your CI. Full
procedure, including why a non-zero exit for an unrelated reason is a false pass:
`sota-code-security` rules/12 §1b. A gate's scope is a path or module expression, and ordinary,
well-motivated containment moves code out from under it with **no diff to the
workflow file and no change in risk**:

- `govulncheck ./...` analyses **the current module only** — it uses "the same
  package path syntax that the go command uses", and `go list ./...` in a module
  containing a nested `go.mod` silently omits that nested module (verified by
  execution, 2026-08-18). Extract the risky parser into its own module and a
  blocking finding becomes an invisible one.
- Same shape elsewhere: a second `package.json` outside the lockfile the SCA reads,
  a git submodule, a directory added to `.semgrepignore`, a vendored tree, code
  moved into a sidecar image the scanner never pulls.

Through all of it the known-bad sits in the main module, the gate keeps rejecting
it, and the gate keeps proving it *can* fail. This is the temporal form of
`sota-code-security` rules/11 §2.2: **the same gate's green today does not cover
the scope it had yesterday.** The check is mechanical — have every gate print the
number of units it enumerated (modules, packages, files) and fail the build when
that number **drops**, exactly as you would treat a coverage drop; a refactor that
legitimately shrinks the tree then costs one deliberate baseline update. Containment
is good engineering. Containment without repointing the scanner is just a smaller
blind spot.

## 3. A gate only gates if failing it makes the artifact unconsumable

Everything above is about a gate being **skipped**. This is the case where the gate
**ran, failed, and the artifact shipped anyway** — because the publish came first.

**If the build publishes to an identifier a deploy watcher can already consume**
(an image-updater, Flux image automation, a `latest`-following chart, a release
channel), then the gates that run *after* that publish do not gate anything. They
only decide whether the artifact ends up *annotated*. The deploy then fails at the
**consumer**, with a verification error — *"no signatures found"*, *"unverified
image"*, *"missing attestation"* — whose cause is three steps upstream in a different
subsystem. Operators triage the message they are given, so a vulnerability, dependency
or test failure reliably sends them to the signing path.

**Build to a candidate identifier; promote after the last gate.**

```
build(:candidate) → scan(:candidate) → sign(:candidate) → promote(:candidate → :release)
```

Three requirements, ordered by how often they are got wrong:

1. **The candidate must be structurally invisible to the watcher, not merely
   different.** Check it against the watcher's own allow-pattern and assert it does
   not match. *"It is a different string"* is not a control; *"it cannot satisfy
   `allowTags`/`filterTags`/the semver constraint"* is.
2. **Promote by retag/copy of the same digest, never by rebuild.** Signatures and
   attestations are digest-keyed, so a same-digest promotion carries them for free —
   and a promotion that re-encodes the manifest silently moves the digest and leaves
   the release tag unsigned. Read the digest back and assert it is unchanged.
3. **Promotion fails closed and is all-or-nothing.** Verify the candidate is present
   everywhere the consumer might read it *before* creating any release identifier;
   with a per-node registry or a multi-region mirror, a partial promotion makes
   admission a coin-flip. If one artifact of a coupled set cannot be promoted, promote
   none.

**The state-advance trap that makes this self-amplifying.** If the step recording
"last built commit" also sits behind the failing gate, the marker never advances, so
the scheduler rebuilds the same commit forever — each cycle publishing another
unverified artifact. Whatever records build state must depend on the **last** gate.
Depend on too early a step instead and a later failure is never retried; both
directions are bugs, and the dependency belongs on the final promotion.

Distinct from *build once, promote many* (`rules/06` §6.6), which is about **environment**
promotion — the staging digest is the prod digest. This is ordering **within a single
build**, and the failure it produces is an error message pointing at the wrong subsystem.

**Audit grep:** for each pipeline, find the step that publishes and the steps that
scan/sign/test, and confirm the publish of the *consumable* identifier is topologically
after all of them. A `docker push` / `ko build` / `kaniko --destination` naming the
release tag directly is the finding.

## 4. A verdict that lives only in a garbage-collected log does not exist

The other half of the same incident. §1 and §2 ask whether a gate *can* fail; the
negative-control material asks whether it can still go red. Neither asks whether a human
can find out **why** it went red once the executor is reaped.

**A gate that classifies its own failure must publish that classification somewhere that
outlives the process.** CI executors are ephemeral by design — pods are garbage-collected,
runners are torn down, log retention is shorter than the time it takes anyone to notice. A
step that carefully separates *"policy violation"* from *"infrastructure error"* and then
`echo`s the distinction to stdout has produced a diagnostic with the lifetime of a pod.
What survives is the exit code, and every failure looks identical: `Error (exit code 1)`.

On Kubernetes the durable surface is the **container termination message**. The default
`terminationMessagePolicy: File` reads `/dev/termination-log` and the orchestrator copies
it into an object that outlives the pod. Writing to it needs no pod-spec change:

```sh
if <gate failed>; then
  if <it was a policy violation>; then
    MSG="GATE FAILED - <POLICY> (NOT a <downstream subsystem> problem). <artifact> | <summary> | <offending items> | <what was skipped> | <the fix>"
  else
    MSG="GATE INFRA ERROR - NOT a <policy> failure. <artifact> | <what to check>"
  fi
  echo "$MSG"
  printf '%s\n' "$MSG" > /dev/termination-log 2>/dev/null || true
  exit 1
fi
```

Rules for the message:

- **Name the cause and explicitly deny the plausible wrong one.** Where the failure has a
  known downstream symptom in another subsystem, say so — that sentence is what stops the
  next hour of investigation.
- **State the consequence**, not just the fact: which later steps were skipped, and
  therefore what will not deploy.
- **Include the identifying detail a fix needs** (CVE IDs, the rule ID, the offending
  dependency). The log that had it is gone.
- **Budget for the cap, and know it is not per-container-generous.** The kubelet truncates
  a termination message at **4096 bytes** — but the *total across all containers is limited
  to 12KiB, divided equally*, so a 12-container pod gets **1024 bytes each** (Kubernetes
  docs, verified 2026-09-06). Init containers and sidecars count, which is exactly the
  shape a CI pod has, so budget from the container count rather than from 4096.
- `2>/dev/null || true` on the write: a read-only rootfs must not turn a clean policy
  failure into a confusing write error.

`terminationMessagePolicy: FallbackToLogsOnError` is the cheaper option when you do not
control the step's script — it uses the tail of the container log when the file is empty
*and* the container errored, capped at **2048 bytes or 80 lines, whichever is smaller**.
It is a fallback, not a substitute: the log tail is whatever happened to be last, not a
verdict you composed.

**Verified on Kubernetes.** The equivalent durable surface elsewhere — GitHub Actions job
summaries, step outputs, annotations — is the same idea and is **not verified here**;
phrase the requirement as *"the durable surface your orchestrator preserves"* and name the
one you actually checked.

**Apply it to every instance of the gate, not just the one that broke.** Gate steps are
routinely copy-pasted across per-service pipelines, and fixing one leaves the rest mute
(`rules/01` §1.11a).

**The alert is the other half.** An alert whose description enumerates possible causes
(*"could indicate X, or Y, or an actual policy failure"*) is the same defect one layer up:
it hands the operator the guesswork the step already resolved. Point the alert at the
durable verdict and give the exact command that prints it.

## 5. The scoped gate is not the gate — reproduce the invocation, not an equivalent

Everything above is about the *pipeline's* scope drifting away from the code. This
is the inverse, and it is what makes people report "all gates clean" before they
push: the code is in scope, the gate sees it, and the **human's local re-run uses
a different invocation** and therefore answers a different question.

Reproduced here at mypy 2.3.1, same tool, same tree, same moment — the error lives
in a file the developer did not change:

```
$ mypy src/pkg/                                      # what you type to "check it"
src/pkg/b.py:2: error: Incompatible return value type ...        exit=1
$ mypy --ignore-missing-imports --no-error-summary \
       --follow-imports=silent src/pkg/a.py          # what the pre-commit hook runs
                                                                 exit=0
```

It runs both ways. Field-reported 2026-09-05 in the opposite direction: a
whole-package run printed `Success: no issues found in 378 source files` while the
hook's changed-file invocation returned three genuine errors (a narrowed `Optional`
reassigned). **Neither verdict is authoritative for the other.** At least three
independent levers produce the divergence, and you rarely know which one you are
looking at: **file selection** (with `--follow-imports=silent`, errors in modules
outside the named set are followed but suppressed), **flags** (`--ignore-missing-imports`
turns absent third-party stubs into `Any`, and inference changes with them), and a
**stale incremental cache** (`.mypy_cache`) on the run that looked clean.

The same trap sits under `ruff`/`eslint` (config discovery depends on the invocation
directory), `pytest` (markers, `-p` plugins, `--import-mode`, `-k` selection), and
every tool whose answer is a function of flags *plus* file selection.

**The rule.** To verify a gate locally, reproduce **its exact invocation** — flags and
file selection — read out of the hook or workflow config, not a convenient equivalent.
Better, run the hook manager itself: `pre-commit run --all-files`, `act`, the CI script.
Where a tool's answer depends on its file selection, say so at the gate definition so
the next person does not re-derive it. And read **each gate's exit code on its own**: an
`&&` chain reports only the last command's status, a trailing `echo` makes the shell's
status 0 whatever the tool did, and a pipe reports the last stage
(`sota-shell-scripting` rules/01 §3). A locally clean run of "the same" linter is not
evidence the gate is clean — it is evidence that a different question has a different
answer.

## 6. A bespoke watcher inherits the publishing conventions of what it watches

Some things you pin cannot be seen by an update bot at all (`rules/03` §3.7.1), so you
write the watcher yourself. It is then an instrument and fails the way instruments fail
(`sota-code-security` rules/15 §2) — with one twist that makes it worse: **silence is a
watcher's normal state**, so an entry that can *never* report is indistinguishable from an
entry with nothing to report. Two field-reported failures, both producing a green that
meant nothing:

- **The source may not publish in the form you query.** A watcher asking
  `GET /repos/<owner>/<repo>/releases/latest` gets a **404** from a project that publishes
  git tags and zero GitHub releases — the entry is skipped silently, every run, forever,
  while the list still reads as complete. That is worse than the entry being absent, because
  completeness is what stops anyone looking. Reproduced 2026-09-07: `mholt/caddy-ratelimit`
  has **0** releases and the single tag `v0.1.0`, and `releases/latest` answers
  `404 Not Found`. Fall back to `/tags` filtered to semver, and do the ordering yourself.
- **The threshold may be coarser than the event class you pinned for.** Alerting only at
  "more than one minor behind" is reasonable for images rebuilt on a schedule and wrong for
  a *pinned*, internet-facing TLS terminator, where `v2.11.4 → v2.11.5` is precisely the
  event the pin exists to catch. It reported **OK**. Derive the threshold from the event
  class you are pinning against; never inherit a default and discover the class later.

**Audit a watcher on four axes**, all cheap, all answerable before you trust a run:

1. **Does the source publish in the form I query?** Ask once per entry and read the answer
   per entry — an aggregate "N checked" hides the entries that can never answer.
2. **Is my threshold finer than the event class I care about?** A patch-level pin needs a
   patch-level threshold, or the watcher excludes its own reason for existing.
3. **Can I make it fire on demand?** A watcher with no forced-alarm path has never been
   observed working (§2; `sota-code-security` rules/15 §2.2 — never trust a number from an
   instrument you have not watched produce a *wrong* answer on purpose).
4. **Does the comparator behave in the environment the watcher runs in, not in my shell?**
   Version comparison is the classic: a lexical sort ranks `v2.9.1` above `v2.11.4` and
   inverts every verdict (verified 2026-09-07 — `sort` returns `v2.9.1`, `sort -V` returns
   `v2.11.4`), and `-V` is not in POSIX. Check it *in the image*: measured the same day,
   BusyBox 1.37.0 in `alpine:latest` does support `-V` — the assumption was wrong in the
   safe direction that time, which is exactly why it is worth one command rather than a
   guess. A shell-less base has no `sort` at all.

An entry that has never reported anything is `sota-code-security` rules/15 §2.2a's
four-state problem in a slower loop: **UNKNOWN** rendered as **NOT DONE**, indefinitely.
Count the runs in which an entry produced no comparison at all, and alert on that count —
"I have not been able to read this for six weeks" is a different fact from "up to date".

## Audit checklist

- [ ] **Does failing a gate make the artifact unconsumable, or merely unannotated?** For each
      pipeline, confirm the *consumable* identifier is published only after every gate: the
      pre-gate identifier **provably fails the deploy watcher's allow-pattern**, promotion is a
      same-digest retag with the digest read back, and build-state advance depends on the final
      promotion — not an intermediate step (§3, §4). A verification error at the consumer for a
      scan/test cause is the symptom.
- [ ] **Does every gate that classifies its own failure write that verdict somewhere durable?**
      A classification `echo`ed to stdout dies with the executor and the operator gets
      `exit code 1`. On Kubernetes: `/dev/termination-log`, budgeted from the pod's container
      count (12KiB total, divided equally — not 4096 each). The message names the cause,
      **denies the plausible wrong one**, states what was skipped, and carries the identifying
      detail a fix needs. Applied to every copy of the gate, not just the one that broke (§3, §4).

- [ ] **Is every "gates are clean" claim backed by the gate's own invocation?**
      A local whole-package run of the same tool answers a different question than the
      hook's flags-plus-file-selection run — verified both ways at mypy 2.3.1 (§3, §4).
      Prefer `pre-commit run --all-files` / `act` / the CI script over re-typing the tool.

- [ ] **Can each entry in a hand-rolled watcher report at all?** (§6) Per entry, not in
      aggregate: the source publishes in the form queried (a tag-only repo 404s
      `releases/latest` forever), the threshold is finer than the event class the pin exists
      for, the alarm can be forced on demand, and the version comparator was verified **in
      the image it runs in** — a lexical sort inverts `v2.9.1` vs `v2.11.4`. Runs where an
      entry produced no comparison are counted and alerted on, not read as "up to date".

- [ ] Every security gate ships a **negative control** — a committed known-bad it must reject on every run, and it is reachable as a **mode of the runner** (`--self-test`) rather than only as a fixture beside it, so a newly added check with no known-bad fails rather than passing unprobed (`sota-code-security` rules/12 §1b). No framework (SSDF, CRA, Scorecard, SLSA) requires this; a passing compliance check is evidence of process, not protection (`sota-code-security` rules/12)
- [ ] Every gate prints the **number of units it enumerated** and the build fails when that number drops — a refactor that moves code into a nested module, a second manifest, a submodule or a sidecar image silently shrinks the gate's scope while the negative control keeps passing (§3, §4)
