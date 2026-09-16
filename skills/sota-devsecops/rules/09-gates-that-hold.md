# Gates That Hold — a gate that can fail, still covers you, and says why

`rules/05` covers the scanners: what to run, where, and how to read what they emit.
This file covers the harder question — **whether any of it actually gates**, which is
a property of the pipeline around the scanner rather than of the scanner.

Split out of `rules/05` on 2026-09-06, from the subsection *"Gates that don't get
bypassed"*, which had reached 284 lines — more than half that file. Its five subsections
were unnumbered and gained numbers in the move (§1–§3 here, §4–§6 in `rules/11`), so an older citation of that
subsection means this file as a whole.

Five distinct ways a gate stops gating, in the order they are usually discovered:

| § | The gate… | and the tell is |
|---|---|---|
| **1** | is not *required*, or is bypassed | a green compliance answer that no framework asks to be falsifiable |
| **2** | can no longer **fail** | the known-bad still gets rejected, but from a scope that shrank |
| **3** | ran, failed, and the artifact **shipped anyway** | a verification error at the consumer, three steps from the cause |
| **4** | failed for a reason nobody can **recover** | `Error (exit code 1)`, and the pod is gone |
| **5** | is clean when *you* run it, red when **CI** does | "all gates pass" said before the push |

§1 and §2 are about the gate's *authority and scope*. §3 and `rules/11` §4 come from one incident
and are two halves of the same failure — the artifact escaped, and then the error message
sent the operator to the wrong subsystem. `rules/11` §5 is the inverse of §2: the code is in scope,
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


**§4, §5 and §6 moved to [`rules/11`](11-after-the-gate-fails.md)** (· unreleased) when this file
reached its cap — that half asks what happens *after* a gate goes red (a verdict that outlives
the executor, reproducing the gate's own invocation, a bespoke watcher's blind spots, and
preserving a failed run's log before re-running it destroys the cause). They keep their section
numbers there.

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

### 2a. A gate that stops at the artifact cannot see a defect that starts at load

§2's blind spot is *lateral* — code moved out from under a gate's path expression. This
one is **depth**, and no scope count reveals it: every gate ran over every file and the
whole class of defect lives past the last line any of them executes.

Formatters, linters, type checkers and most SAST stop at the **compiled artifact**. A
loader, a verifier, a dynamic linker, a runtime capability check, a policy engine and a
kernel all run *after* it. Field-reported: four gates — `fmt`, `clippy` and two
domain-specific lint passes — were green on an eBPF object that the kernel verifier then
refused to load, because the defect was a stack-budget overrun measured at load time
(`sota-rust` rules/07 §1a). Nothing was misconfigured; the artifact was simply the end of
their reach. The same boundary sits under a container that builds and crashes on start, a
WASM module that compiles and fails instantiation, a plugin that links and fails its
capability check, a Terraform plan that renders and is refused by admission.

- **Name every gate's terminal artifact**, and ask what happens to it next. If the answer
  is "something loads, verifies or admits it", that step is unprobed.
- **One gate per pipeline must execute the artifact on a representative target** — load
  it, start it, instantiate it, `--dry-run` it against the real admission controller.
  Where the target is expensive or exotic (a specific kernel, a device), it is still the
  only gate with reach, so its cost is the price of the class, not a reason to drop it.
- **Green from the artifact-level gates is not evidence about load**, and should not be
  quoted as if it were. This is `sota-code-security` rules/15's *"state the traversed
  path beside the probe"* applied to a whole pipeline: say where the gates stop.
- The mirror-image trap is a gate whose reach is bounded by what the **subject** checks
  first — a runner that exits at a credential check in CI never reaches the code under
  test. Injecting a **dummy** credential makes CI and a laptop measure the same depth.

### 2b. The gate ran — but which binary, and over what?

§2 is a gate whose **scope** drifted sideways; §2a is one whose **reach** stops at the
artifact. This is the third axis and the cheapest to get wrong: **the identity of the tool
that produced the verdict, and the extent it was pointed at.** Both are invisible in a green
tick, and neither leaves a diff.

**Which binary.** `PATH` order decides which `cargo`, `python` or `node` actually ran, and a
version manager's shim loses to anything earlier. Field-measured: a Homebrew `cargo` at
`/usr/local/bin` shadowed the rustup shim while `rustup show active-toolchain` still correctly
reported the pinned nightly — **the pin was fine and the binary was wrong.** The two failure
modes are not equally visible: a nightly-only `-Z` flag died loudly, but **`cargo fmt --check`
exited 0 while silently ignoring every nightly-only key in `rustfmt.toml`**, printing
`Warning: can't set imports_granularity …` and then reporting success. A green format check
from the wrong binary is the kind of green nobody looks at again.

**Over what.** A scoping flag narrows coverage without changing the verdict's shape.
Field-measured: `cargo fmt --check --manifest-path kernel/Cargo.toml` exited 0 on a tree that
`cargo fmt --check` from the repo root reported two diffs on, because the narrower manifest
excluded the workspace member holding most of the code. CI rejected what local had passed.

- **Print the binary and the version in the same invocation as the verdict** — `command -v
  cargo`, `cargo --version` — rather than trusting the version manager's idea of what is
  active. For a pinned toolchain the ground truth is `rustup run <channel> cargo --version`,
  which execs the real binary and is immune to shadowing; `rustup show active-toolchain`
  reports the *pin*, which is never the thing that breaks.
- **Prefer the project's own check script to an ad-hoc invocation** — it encodes the intended
  scope. Where you must go ad-hoc, establish coverage: count the files, or change one
  deliberately and confirm the check goes red.
- **A check's exit code tells you it ran, never what it ran over.** Treat "passed locally,
  failed in CI" as a scope or binary question first, and a code question second.

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

## Audit checklist

- [ ] **Does each gate print the binary and the scope that produced its verdict?** (§2b)
      `PATH` order decides which toolchain ran — a shadowing binary made `cargo fmt --check`
      exit 0 while ignoring every nightly-only config key — and a scoping flag
      (`--manifest-path`, a path arg, an ignore file) narrows coverage without changing how
      the green looks. `command -v` + `--version` beside the result; for a pin, compare
      against `rustup run <channel> …`, not `rustup show active-toolchain`.
- [ ] **Where do the gates stop, and what runs after?** (§2a) Name each gate's terminal
      artifact. If a loader, verifier, dynamic linker, capability check, admission
      controller or kernel runs after it, at least one gate must **execute** the artifact
      on a representative target — otherwise that whole depth is unprobed while every gate
      is green. Conversely, a gate whose subject exits early (a credential check in CI)
      reaches nothing past that point: inject a **dummy** credential so CI and a developer
      machine measure the same depth.
- [ ] **Does failing a gate make the artifact unconsumable, or merely unannotated?** For each
      pipeline, confirm the *consumable* identifier is published only after every gate: the
      pre-gate identifier **provably fails the deploy watcher's allow-pattern**, promotion is a
      same-digest retag with the digest read back, and build-state advance depends on the final
      promotion — not an intermediate step (§3, `rules/11` §4). A verification error at the consumer for a
      scan/test cause is the symptom.
- [ ] Every security gate ships a **negative control** — a committed known-bad it must reject on every run, and it is reachable as a **mode of the runner** (`--self-test`) rather than only as a fixture beside it, so a newly added check with no known-bad fails rather than passing unprobed (`sota-code-security` rules/12 §1b). No framework (SSDF, CRA, Scorecard, SLSA) requires this; a passing compliance check is evidence of process, not protection (`sota-code-security` rules/12)
- [ ] Every gate prints the **number of units it enumerated** and the build fails when that number drops — a refactor that moves code into a nested module, a second manifest, a submodule or a sidecar image silently shrinks the gate's scope while the negative control keeps passing (§3, `rules/11` §5)
