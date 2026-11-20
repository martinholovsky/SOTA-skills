---
description: Work through the open items unattended — inventory and classify as /sota-resume does, then decide what is reversible, queue what is not, never wait on the operator, and end with a report of every decision taken on their behalf. Run it when no one will be there to answer prompts.
---

Work through this project's open items **without asking the operator anything**, and end with a
report of every decision you took on their behalf.

The operator has pre-authorised the list by running this command, so `/sota-resume`'s "stop and
let me steer" does not apply. What replaces it is a policy: decide what can be undone, **queue**
what cannot, and keep moving. Nothing here waits for an answer, because no one is there to give one.

**What this command cannot do: suppress Claude Code's own permission prompts.** If a tool call
needs approval in the permission mode the session runs in, the session waits until someone
answers. For an unattended run, the operator starts it in a mode that does not prompt (auto mode,
or an allowlist). In that mode a denial comes back as a refused call, and step 4 handles it.

## Arguments

Read them from `$ARGUMENTS`; each is optional.

- `budget=$N` (or `budget=$N-$M`): the most you may spend on paid APIs, cloud resources or any
  metered service. **With no budget, spend nothing**: a paid item goes to AWAITING YOU (step 3).
  A range means aim for the low end and never pass the high end.
- `items=N`: stop after N items. `hours=N`: stop starting new items after N hours.
- Anything else is a scope hint: only items matching it.

## 0. Load the rules before the first command

Invoke the `sota-shell-scripting` skill and read its `rules/06` (ad-hoc commands) and `rules/08`
(ad-hoc side effects) in full now. An unattended run has no one to notice a sweep that found
nothing because it searched nothing, or a check that filled a disk.

## 1. Inventory and classify, as `/sota-resume` does

Read `commands/sota-resume.md` (or the installed `/sota-resume`) and follow its steps 1 and 2
exactly: the controlled sweep with a positive control and a denominator, then the five classes.
Do not skip the ALREADY DONE and fired-trigger checks: unattended, a stale tracker row costs a
whole night of work on something already finished.

Then **skip its step 3**, and sort each item into one of these instead:

| Class | What happens |
|---|---|
| **DO** | READY, and every action it needs is allowed by step 2. Execute it. |
| **DO, THEN QUEUE** | The work is allowed, but its last step is not (a merge, a release, a publish). Do everything up to that step, verify it, and queue the final step. |
| **DECIDE AND DO** | NEEDS A DECISION, and step 2 lets you make it. Make it, log it, execute. |
| **QUEUE** | NEEDS A DECISION that step 2 reserves for the operator, or an item that is all one queued action. Write the question, the options and your recommendation, and move on. |
| **LEAVE** | DELIBERATELY DEFERRED, NOT AN ITEM, ALREADY DONE: as `/sota-resume` says. A tracker correction for ALREADY DONE is a DO item. |

## 2. The decision policy

**Decide** when the choice is reversible inside this repository: a design choice within an item's
scope, naming, test layout, which helper to reuse, a fix's approach, opening a pull request on a
repository the operator owns. Record each one (step 6).

**Queue, never do**, anything irreversible or outward-facing:

- merging to the default branch, unless the operator's own instructions (a `CLAUDE.md` or
  `AGENTS.md` rule) already grant it for this repository; if they do, follow that grant exactly,
  conditions included, and log each merge;
- force-pushing, rebasing a shared branch, deleting a branch, a tag, a file outside the item, or data;
- tagging, releasing or publishing anything;
- anything that speaks for the operator outside this repository: an issue, a PR or a comment on a
  repository they do not own, an email, a chat message, a post;
- changing permissions, settings, hooks, agent files (`CLAUDE.md`, `AGENTS.md`, skills) or credentials;
- spending beyond the budget argument, or spending at all without one.

Leave each queued action **ready to run**: the branch pushed, the PR open and green, the exact
command written out, so the operator's part is a single, checked step.

**Security decisions** (an authentication or authorisation model, a crypto primitive, a trust
boundary, secrets handling, network exposure) are where the library's standing rule is "stop and
ask". Unattended, decide one only when **both** hold:

1. the option you take is the more secure one by the library's own rules (fail closed, least
   privilege, deny by default; cite the rules file), **and**
2. it costs nothing the operator owns: no breaking change for callers, no dropped feature, no
   model of who-may-do-what chosen on someone else's behalf.

Otherwise queue it, with the options and your recommendation. Every security decision you do
take goes in its own section at the top of the report.

**Spend**, with a budget: before each paid step, state its expected cost and the running total,
set the tool's own hard cap where it has one, and stop starting paid work once the next step
could cross the budget. Report what the provider's own counter says, not your estimate alone.

## 3. Execute, one item at a time

Follow `/sota-resume` steps 4 to 6 for each item: the project's own verification (what CI runs),
watching a check fail before trusting it to pass, the tracker updated in the same change, and the
same threshold for a better way found mid-item. Where those steps say to pause and ask, **queue
the question instead**, and carry on with any item that does not depend on the answer.

An item that turns out bigger than it looked: stop it at a clean point (nothing half-applied),
record where it stopped and why, and move on. A half-finished item is worse than an untouched one.

## 4. When a command is refused

Work out what the refusal protects before you react to it.

- **The form was refused** (a hook or check that names a fix: quote the glob, use `&&` instead of
  `;`, an option the tool rejects): apply the fix and retry. That is the check doing its job.
- **A classifier misread a harmless command** (a search whose quoted text contains a dangerous
  word, a read-only command flagged as a write): retry once in a form that says plainly what it
  does. A different method that reaches the same result **by a safe operation** is allowed (regenerate
  a file rather than discard edits with a refused `git checkout --`), if it is no riskier than the
  original.
- **The action was refused** (a push, a delete, a merge, a write outside the repository): do not
  achieve it another way. Re-encoding the same action to get past a refusal (`rm` refused, so
  `python -c "os.remove(...)"`) is evading the operator's control, not working around an
  oversensitive one. Queue it.

Log every refusal and every retry or workaround, with the original command and the reason, so the
operator can judge whether the block was oversensitive.

## 5. Stop conditions

Stop starting new items when any of these holds, and go to step 6:

- the `items=` or `hours=` limit is reached;
- **three items in a row fail** for a reason outside the item (a broken toolchain, a network
  outage, a full disk): an environment problem does not fix itself overnight, and retrying burns
  the budget;
- the budget cannot cover the next paid step;
- nothing classified DO or DECIDE AND DO is left.

## 6. Close and report

Run `/sota-close`'s steps (retract, hand off, docs, re-derive numbers, commit the evidence). Then
write the report below as your final message, and save the same text to
`$(git rev-parse --git-dir)/sota-auto/<UTC timestamp>.md`, which sits inside the git directory, never
the working tree, so the next session can find it without it being committed.

The report, in this order. Write a section heading even when it is empty, followed by "none", so
an omitted section cannot read as an empty one:

1. **Security decisions made on your behalf**: the decision, the alternatives, the rules file
   that makes yours the more secure one, how to reverse it (commit, PR or file:line).
2. **Awaiting you**: every queued action, ready to run: what, why it was queued, the exact
   command, and what you verified before leaving it.
3. **Decisions made on your behalf**: one row each, as `# · item · decision · options considered ·
   why · how to reverse`. Include the small ones: the operator reads this to change course.
4. **Refused, retried or worked around**: the original command, what refused it, what you did instead.
5. **Done and verified**: each item with the command and its result.
6. **Not done**: skipped, stopped part-way, or still open, and why.
7. **Spend**: per paid step and total, from the provider's own counter, against the budget.

**Never mark something complete that you did not observe working**, and never describe a queued
step as done. The operator will act on this report in the morning without the context you had.

$ARGUMENTS
