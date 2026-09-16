# 11 — After the gate fails: can anyone find out why

Scope: the sibling of `rules/09`. That file asks whether a gate *can* fail and whether failing
it *matters*; this one starts one step later — the gate went red, and someone has to find out
why. Split out of `rules/09` (· unreleased — the cut fills this in) when that file reached its 500-line cap; §4, §5 and §6
keep their numbers so every existing citation still names the right section.

**The unifying property:** a failure's cause lives in output that is *more perishable than the
failure itself*. An executor is reaped, a log is truncated, a re-run overwrites its
predecessor — and what survives is an exit code, which looks identical for every cause.

## 4. A verdict that lives only in a garbage-collected log does not exist

The other half of the same incident. `rules/09` §1 and §2 ask whether a gate *can* fail; the
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

**A warning on a *passing* run needs its transport verified, not just its existence.**
Everything above is about failure diagnostics dying with an ephemeral executor. The
systematically worse case is the opposite: **every wrapper that suppresses output suppresses
it on success** — and a warning is by definition emitted on a run that otherwise passed, so
warnings are the class of message most likely to be structurally unreachable, on the one
outcome nobody investigates afterwards.

Verified against the installed **pre-commit 4.6.0**, not from documentation:
`pre_commit/commands/run.py` emits a hook's output only when

```python
if verbose or hook.verbose or retcode or files_modified:
```

so a seventeen-minute, twenty-three-gate run reaches the terminal as the single word
`Passed`, and a warning written inside it cannot arrive. Remedy there is `verbose: true` on
that hook. The same shape elsewhere: a GitHub Actions `::group::` collapses output out of a
skimmer's view, a `@`-prefixed Makefile recipe hides the command, `| tail` keeps the summary
and drops the warning above it.

Ask **"what does this look like on a green run, to someone not looking?"** Where no path
exists, the warning must become a **durable artifact** — a file, a record, a check a later
command performs — rather than a line of stdout. Field-measured: the problem above was found
by exactly that, a ledger query reporting `1 of 2 commit(s) in HEAD~2..HEAD carry a gate
record`, after the stdout warning had been invisible.

## 4a. Re-running a failed check destroys the evidence of why it failed

§4 is about a verdict the gate **composed** — it knew why it failed and had to publish that
durably. This is the harder case: the gate did **not** know. The line that explains the failure
is incidental output nobody designed as a diagnostic, and the natural next action — run it
again — is what deletes it.

**The mechanism is ordinary and that is the problem.** A runner that writes its log with `>`
truncates the previous run's; one that writes to a fixed path overwrites it; CI keeps only the
latest attempt for a re-run of the same job. None of that is a bug, and all of it means the
*first* red run is the only one that saw the cause.

Field-reported 2026-09-16: a gate suite failed, and a second run started concurrently by a
pre-push hook collided with it over a shared test binary. The surviving evidence was one line —
`cp: cannot create regular file '/tmp/<bin>': Text file busy` — in an **archived** copy of the
first run's log. The visible symptom was a kernel conformance test failing to observe an event
it had caused: **indistinguishable from a product race**, in a suite already tracking four
unexplained intermittent failures. Re-running to green and reporting the green would have added
a fifth.

**So: copy the log before you re-run, not after you decide you need it.**

```sh
# the re-run is the destructive step; archive first, unconditionally
run_gate() {
  local stamp; stamp=$(date +%Y%m%dT%H%M%S)
  ./ci-local.sh > "runs/$stamp.log" 2>&1        # per-run path, never a fixed one
  local rc=$?
  [ "$rc" -eq 0 ] || echo "FAILED: runs/$stamp.log (rc=$rc)" >&2
  return "$rc"
}
```

- **Capture stderr into the same stream** (`2>&1`). The `ETXTBSY` above arrived on stderr; a
  runner that keeps only stdout discards exactly the class of line that explains an
  infrastructure failure.
- **Never a fixed log path** for a check you will run repeatedly. `> gate.log` is a
  single-slot buffer that the next invocation empties.
- **Record wall-clock duration beside the verdict.** It is often the only signal separating an
  environment problem from a product one: the same suite at 1599s against a 757s baseline for
  identical code is the tell that two runs were contending, not that the code changed
  (`sota-performance` rules/01 §9a — a suspiciously *slow* run indicts the measurement first).
- **A flake you cannot explain is not a flake, it is an unread log.** Before adding a failure
  to a known-intermittent list, check whether its first occurrence was ever preserved. A list
  of "unexplained intermittent failures" is frequently a list of runs whose evidence was
  overwritten.

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

- [ ] **Warnings emitted on a PASSING run have a verified path to a human** (§4) — the
      wrapper's success-path output handling checked, not assumed (pre-commit discards it
      by default), and a ledger query proving the record exists rather than the stdout line.
- [ ] **Does every gate that classifies its own failure write that verdict somewhere durable?**
      (§4) On Kubernetes, `/dev/termination-log`; elsewhere, the surface your orchestrator
      actually preserves — named, and checked rather than assumed. Budget the message from the
      **container count**, not from 4096 bytes.
- [ ] **Is a failed run's log preserved before anything re-runs?** (§4a) Per-run paths, not a
      fixed one; stderr folded in; duration recorded beside the verdict. Ask specifically:
      **could the cause of the last red run still be read today?** If the answer is "it was
      re-run", the evidence is gone — and any "unexplained intermittent failure" list built
      that way is a list of unread logs, not of flakes.
- [ ] **Is every "gates are clean" claim backed by the gate's own invocation?** (§5) Reproduce
      the pipeline's command, not an equivalent — a different scope is a different question.
- [ ] **Can each entry in a hand-rolled watcher report at all?** (§6) Per entry, not in
      aggregate: count the runs in which an entry produced no comparison, and alert on it.
      "I have not been able to read this for six weeks" is not "up to date".
