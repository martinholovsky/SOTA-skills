---
description: Audit this codebase against the library — agree and pin the scope, map the trust boundaries, run the scanners, route from the surfaces rather than from whatever happened to get loaded, walk every applicable rules file's Audit checklist item by item, ask the questions that need a decision, then fix what you agree to. Run it when a piece of work is finished, or on arriving in a codebase you did not write.
---

Audit this codebase against the library's rules — how far they were applied, not how good
the code feels.

It is the third position in a session: `/sota-resume` opens one, `/sota-close` shuts one
down, this one checks the work in between against the standard it was supposed to meet. It
is also the first useful thing to run in a codebase you did not write.

**What separates it from a defect hunt.** A generic review asks *is this code wrong?* This
asks *which of the library's rules own this surface, and does the code satisfy them?* So the
dominant finding is not a bug. It is a rule that owns real surface area and was never
applied — and behind it, a control that is present and enforces nothing.

**What separates it from `/sota-deep-audit`.** Not *what* is checked — both commands look
for the same classes of defect against the same standard, the `sota` router's AUDIT workflow
and its `rules/01`, `rules/03` and `rules/05`. The deep audit buys things one context cannot
supply: refuters that did not find the finding, partitions on separate agents, decisions
re-measured this session, a forward look at the plan, and the *full* threat-model
reconstruction. Where this command says "point at a rules section", that section is the
procedure; this file is the order to run it in.

## 0. The work is the subject. Your memory of it is not

If this session wrote the code, you are auditing yourself, and re-reading your own summary
re-runs the reasoning that produced it — the weakest check available. Every claim below is
made against an artifact: `git diff`, the file on disk, the command run a second time. **A
file quoted verbatim into context earlier is not primary either** — it may predate an edit
made since. Re-read the path.

Self-audit fails in one direction: **false negatives**. You will agree with yourself, because
the reasoning that produced the code is still loaded. The only counter that works is to walk
the checklists rather than to recall the work — an item you cannot remember deciding is an
item you did not decide.

## 1. Agree the scope, and pin it, before reading anything

Scope decides the answer, and the wrong scope does not error — it returns **clean**.
Enumerate the candidates that actually exist here, size each one, and stop:

```sh
git rev-parse HEAD                              # the commit every finding is pinned to
git status --porcelain | wc -l                  # uncommitted work (non-zero: pin HEAD + "dirty")
git ls-files | wc -l                            # the whole repo

# Resolve the base into a variable and GUARD IT before using it. Keep stderr:
# git says why it failed, and that reason is the thing you report.
BASE="$(git merge-base HEAD origin/HEAD)"
if [ -n "$BASE" ]; then
  git diff --name-status -M "$BASE" | wc -l     # this branch vs its base, renames kept
else
  printf 'base did not resolve — ask which branch to compare against\n' >&2
fi
```

**That guard is the whole lesson of this step, so it is written out rather than assumed.**
Unguarded, `git diff --name-only "$BASE"` with `$BASE` unset and stderr dropped prints **`0`,
exit `0`** — a clean denominator for a branch carrying five commits, offered to me as a scope I
might pick. An empty comparand does not fail, it silently answers a different question
(`sota-shell-scripting` rules/06 §2b). `--name-status -M` rather than `--name-only` because a
rename has two paths and the old one can still be referenced.

Offer only what you could size, plus any subtree this session actually touched. If a command
failed, name it and say why rather than dropping the option silently — an absent scope and an
unsizeable one look identical in a list. **Print the denominator beside every candidate.**
`0 findings over 0 files` and `0 findings over 900 files` are the same sentence and different
answers (`sota-code-security` rules/11 §2.2).

Then, before reading code:

- **Pin it.** Record the SHA from the first command, plus a dirty flag or a hash of the
  uncommitted diff. Every finding *and every dismissal* is bound to it — a "false positive" or
  "dead code" verdict with no commit never expires when a caller changes (`sota` router
  `rules/05` §4).
- **A diff scope includes its dependents.** The callers and importers of every changed file,
  and both paths of a rename, two hops out — found by symbol reference, not by guessing. A
  changed contract breaks code that is not in the diff. A diff that turns up a serious concern
  **escalates** to a baseline of that component (`sota` router `rules/01` §1).
- **Name the yardstick** the findings assert against — ASVS with its level, the OWASP Top 10
  lists, CWE; the LLM and agent lists where that surface exists (`sota` router `rules/01` §1).

Then say what the chosen scope *excludes*, and do not quietly widen it later. A scope that
grew mid-pass makes every count in the report unreconcilable.

**If what I pick is larger than you can hold at once, partition it and say how** — by
subsystem, by entry point, by directory — **crown jewels first** (authentication and
sessions, secrets, money and sensitive-data flows, internet-facing entry points, untrusted LLM
input reaching a tool), and finish each partition before opening the next. Skimming a large
scope returns a clean result for the same reason the wrong scope does, and nothing in the
output distinguishes the two (`sota` router `rules/01` §1, §1a).

## 2. Map the trust boundaries — the light threat model

A Critical or High must name the chain that makes it one, and a chain crosses a trust boundary
(`sota` router `rules/03` §1). Rated without a boundary map, every severity is a guess. So
before any domain pass, build one table from the **code**, not the docs:

| entry point (route, consumer, cron, webhook, CLI, agent tool) | authn / authz checkpoint, `file:line` | asset or store reached | privilege it runs with |

Then write down the **assumptions** the code implies — *services trust the gateway's headers*,
*that bucket is private*, *only the worker reaches the queue* — and check each against the
code or config that would make it true. One with no evidence is not *probably fine*; it is a
broken assumption, and those are usually the Criticals. One you cannot check is marked
**unverified**, never assumed.

For a **diff** scope, do this for the diff and its dependents only: which boundaries does the
change touch, and what does each one now let through (`sota-threat-modeling` SKILL.md, the
continuous / incremental mode).

This is deliberately the *light* model — entry points, boundaries, assets, assumptions — sized
to prioritise and to rate. The full reconstruction (the DFD, the component threat catalogs,
the control-presence matrix with its sampling rule) is `/sota-deep-audit`'s, and
`sota-threat-modeling` rules/06 is its procedure. Say in the report which one you ran.

## 3. Route from the surfaces, not from what happened to be loaded

**This is the step that decides whether the audit can find anything at all.** A session that
never routed will look perfectly compliant, because nothing was being compared against.

So rebuild the list from the tree, not from context: languages with versions, entry points,
data stores, CI config, Dockerfiles, IaC, shell scripts, **personal data** wherever it is
stored, logged or exported, **untrusted data** the system ingests (feeds, uploads, scraped
pages, webhooks, RAG corpora), and anything an agent loads as instructions. Map each onto its
owning skills with the `sota` router's routing table — **then walk the router's cross-cutting
routing rules against the same list**, because the table maps one surface to one skill and
those rules are where the second and third skill come from: a language skill stacks on every
domain skill, untrusted ingestion adds `sota-code-security` rules/09, personal data adds
`sota-privacy-compliance` even when nothing is "about" privacy, every audit adds a
`sota-testing` suite-health pass, and a script that produces evidence is a security control.

Print the coverage table **per rules file**, not per skill, before reading any of them:

| surface found | owning skill | rules file | walked? | if not, why |

A skill marked "covered" because one of its files was opened is the hole this table exists to
expose: the file you did not open is the checklist nobody walked. Take each applicable skill's
rules index ("read this when…") and mark every file **walked** or **not applicable, because…**.

**An unexamined domain is not a clean one.** A domain with no matching surface is a legitimate
skip and says so in the table; a domain nobody opened is a hole in the audit and must be
reported as one, not omitted.

<!-- count-check: ^- \*\* -->
Three things join the standard beside the skills:

- **The stack profile.** `~/.claude/profiles/*.md`, if one exists, is the expected baseline
  in AUDIT mode (router principle 4) — a deviation from it is a finding even when the
  generic rule is satisfied. It can raise a finding's *default* severity, never skip chain
  closure: a profile's "Critical by default" still walks the legs of `sota/rules/03` §1 rule 3,
  and the report states both ratings when they differ.
- **The project's own written conventions.** `CLAUDE.md`/`AGENTS.md`, `CONTRIBUTING`, ADRs,
  the invariants a repo enforces on itself. Inside its own tree a project's stated convention
  outranks a general default. Where the two genuinely conflict, **say which you followed and
  why** — do not pick silently, and report the collision.
- **Day zero.** No secret scan in any hook or CI job, no licence file, no agent file, and a
  short history together mean nothing enforces any of this, and that is the first finding —
  above whatever the code does. Offer `scripts/init-gates.sh`; never run it unasked.

## 4. Run the scanners — tools find what reading misses

Checklists are read; a leaked key in a deleted commit, a lockfile pinning a package with a
published CVE, and a workflow with a template injection are *found*. The router's standard is
"Tools find the mechanical 60%; manual review finds the design flaws. Run both, never just
one" (`sota` router `rules/01` §3). For each ecosystem step 3 found, run one row of that file's
tool matrix at the pinned commit: **secrets over the full git history**, dependency/SCA, SAST,
and IaC and CI-workflow scanners where those surfaces exist.

- **Run what is installed; never install a tool, and never run one against a live system,
  unasked.** Live credential verification and scanners pointed at deployed endpoints are
  stop-and-ask actions (`sota` router `rules/01` §1). A scanner that is not present is reported
  under **not reached** — never counted as a clean result.
- **Record the tool, its version and the exact command line**, so the result can be re-run.
- **Triage before anything becomes a finding.** Tool severity is an input: re-rate it in
  context; "dead" and "test-only" are claims with evidence bars that fail closed; existing
  suppressions and deprecated APIs are findings in their own right (`sota` router `rules/01` §3).
  Never paste a raw dump into the report.
- **No secret value leaves the scanner.** A found secret is reported by location, type and
  commit, redacted, with rotation first in the fix (`sota` router `rules/01` §4).

## 5. Walk the checklists — silence is not a verdict

For every rules file the coverage table marks applicable, take its `## Audit checklist` item by
item and mark each **met · not met · not applicable, with the reason**. Not "reviewed". Then
the skill-level half the per-file checklists do not carry: each applicable skill's **AUDIT
mode** workflow and its **top-10 non-negotiables**, checked the same way.

An item you skip because it obviously holds is exactly the item that goes missing: the
cross-cutting ones — abuse control, transport enforcement, tests for the logic, structured
logs without secrets — get dropped under a long, dense task as an attention effect rather than
a knowledge gap. That is why the router re-checks them **last** (principle 5, BUILD step 4),
and why they are re-checked here even when no rules file raised them.

Checklists and scanners share a blind spot, so budget **explicit manual passes** for what
neither sees, ordered by the boundary map: business logic and state machines, authorization
**per object** (BOLA/IDOR), whether validation happens *at* each boundary or three layers
later, races and TOCTOU, crypto misuse, and injection or excessive-agency paths in LLM and
agent code (`sota` router `rules/01` §3, manual review).

## 6. Present is not applied

The passes above ask whether a control is there. This one asks whether it does anything.

For every control the audit just credited, ask the **falsification question**: *if this were
silently a no-op, would anything observable differ?* No log, no metric, no failing test —
then it is not a control (`sota-code-security` rules/10 §1). Where it emits an artifact, read
back **the one this run produced**, not an example of one.

Then two counts, because presence and reach are different claims:

- **Population.** A real control applied to part of what it is credited with is the finding —
  count the sites it guards against the sites the prose claims (`sota-code-security`
  rules/14 §6).
- **Enforcement.** A rule written in prose with nothing mechanical behind it is the same
  defect one level up: an instruction standing in for a control (`sota-code-security`
  rules/14 §3). Where a gate exists, say how deep it reaches — a gate that stops at the
  artifact cannot see a defect that starts at load, and green proves only what it could
  reach (`sota-devsecops` rules/09 §2a, §2b).

**Your own sweeps are controls too, and they fail the same way.** Every absence you report
needs a positive control in the same invocation — search for something you have already seen,
drawn from where your scope is least likely to reach (a control from inside a too-narrow scope
passes anyway); if the control returns nothing, the instrument is broken and the absence is
worth nothing (`sota-shell-scripting` rules/06 §2). A positive control proves the instrument;
an absence you report as a *finding* also needs a **second, independent method** — a different
failure mode, not a different phrasing (`sota` router `rules/03` §2). Two more tells: an
implausibly *large* result is usually an empty value that removed a filter rather than one
that matched everything (`sota-shell-scripting` rules/06 §2b), and a result whose size equals
a round number you or the tool chose is a page, not a total (`sota-shell-scripting` rules/09
§5).

## 7. Audit the decisions and the history, not just the code

Everything above asks whether the code meets the rules. None of it can see the defect where
the code **faithfully implements a choice that stopped being right** — a store picked for a
scale that never arrived, a constraint that has expired, a benchmark that justified a design
and no longer reproduces. No rule is violated, so no checklist fires.

Reconstruct the decisions that are expensive to reverse — ADRs, design docs, the CHANGELOG,
the PRs behind each major component — and classify each **JUSTIFIED · STALE · UNJUSTIFIED ·
UNVERIFIABLE**. Where a decision rests on a number, **re-measure it this session** if it is
cheap to; where it is not, mark the verdict UNVERIFIABLE and name the measurement — re-measuring
the expensive ones is what `/sota-deep-audit` is for. Full procedure — `sota` router `rules/03`
§3.

**Read the history for where to look.** Past incidents, earlier findings and commits that
quietly fixed a security bug mark the components that failed once; complexity × churn orders
the reading inside the crown jewels (`sota` router `rules/01` §2).

**Then ask where else this project's knowledge lives.** An agent's private memory store, an
IDE's notes, a chat log. Anything there that is a *fact about the repository* with no home in
the repository is a finding: invisible to review, absent from a fresh clone, gone when the
store is cleared. It is an absence claim, and the naive search for it lies — `sota` router
`rules/01` §4a.

## 8. Ask — batched, once, in decision form

Ask when the answer changes the finding: an intended trade-off you cannot distinguish from an
oversight, a convention that contradicts a library default, a severity that turns on whether
something is internet-facing, a rule that plainly does not fit and states no exception.
**Anything that materially moves security posture is always a question, never a silent pick**
(router principle 2).

Each one gets: the question, **two or three options with what each costs and forecloses**, and
your recommendation **with its reasoning**. A bare recommendation is ratification, not a
decision handed over. **Batch them into one interruption** and keep auditing everything that
does not depend on the answer. Do not ask what the tree already answers — that is a read, not
a question.

## 9. Report

One table, canonical format, deduplicated across domains:

`file:line | rule violated | severity | effort | fix`

That row is the **working** format. Severity resolves on the `sota` router's `rules/03` §1 — a
Critical or High names the chain that makes it one, using the boundary map from step 2, and a
diff is rated against the code it replaced, not against perfection. A finding you could not
confirm is marked **needs verification**; it is never asserted and never dropped. Borderline
severities state the deciding assumption.

Every surviving Critical, High and Medium then expands to the full evidence block — location
at the pinned commit, minimal evidence, CWE/OWASP mapping, the impact in the sentence an
attacker would use, a diff-level remediation, effort (`sota` router `rules/03` §2) — plus a
**reproduction**: the steps or command that show it (`sota` router `rules/05` §1). Lead with a
one-line posture verdict capped by the worst standing blocker (`sota` router `rules/03` §5).
**Before anything ships, resolve every `file:line` and every rules citation against the tree
as it is now** — positions drift while an audit runs (`sota` router `rules/01` §4b).

<!-- count-check: ^- \*\* -->
Then three things a findings table cannot carry, and which are the point of this command:

- **Coverage** — the per-rules-file table from step 3, as it ended: what was walked, what was
  skipped, why; which threat model ran (step 2); which scanners ran, at which versions (step 4).
- **Depth reached** — for anything you checked by running something, what the check could
  actually see.
- **Not reached** — scope you did not cover, scanners that were not installed, assumptions
  left unverified, in the sentence I would use for it, not a softened one. An omitted step and
  a completed one are indistinguishable in a report.

Before a Critical or High ships, try to kill it: re-read the code at the pinned commit rather
than your own write-up, default to REFUTED where the evidence is ambiguous, and **sweep the
pattern elsewhere either way** — a refuted finding routinely closes somewhere else, and that
sweep is where the strongest finding usually comes from (`sota` router `rules/03` §4).

**Say in the report that this was the weaker form of that pass, because it is.** The standard
is an *independent* refuter — a separate agent or a fresh context, prompted to kill the finding
and handed the code rather than your write-up, with what it receives bounded and its verdict
returned as a number (`sota` router `rules/03` §4a). One context refuting itself still holds
the reasoning that produced the finding. Where a Critical or High is load-bearing, escalate to
[`/sota-deep-audit`](sota-deep-audit.md), which fans that refutation out; short of that, name
which findings got only a self-refutation.

## 10. Fix what I agree to

Nothing is edited before I pick the set. Then, one finding at a time, smallest blast radius
first:

1. Make the change.
2. **Run this project's own verification** — find its entry point rather than assuming one:
   `Makefile`, `package.json` scripts, `justfile`, `noxfile.py`, `.pre-commit-config.yaml`,
   and above all `.github/workflows/*`, which is the definition of passing that gates this
   repo.
3. **Watch it fail before trusting it to pass.** A suite that matched zero files exits 0 and
   prints `ok`. If you never saw the check reject anything, you do not know it ran.
4. **Verify the finding, not just the suite.** A green suite says nothing about whether the
   class is closed. Run the reproduction against the fix *and* with the fix reverted — the
   baseline must still fire — then try at least three same-class variants, all of which must
   fail (`sota` router `rules/05` §5). A fix is verified when a fresh search cannot get around
   it, not when the reported input stops working (`sota` router `rules/01` §4). A leaked
   secret is fixed by rotating and revoking it, not by deleting the line.
5. **Update the docs the fix makes false in the same change** — README, comments, runbooks,
   the agent file, the ledger row. A stale line is executed, not merely read.

## Constraints

- **Report in the session; write no file unless I ask for one.** Most repos this runs in are
  not mine to leave artifacts in.
- **Audit what is here — do not design what should have been here.** A better architecture
  you would have chosen is not a finding. A rule with surface area and no application is.
- **Never report a fix working that you did not observe working.** If verification failed for
  an environmental reason, fix the environment or say plainly that you could not.
- **A rule that let this codebase down is worth one line at the end**, pointing me at
  `/sota-report` — that is the only way the library learns anything from this pass.

$ARGUMENTS
