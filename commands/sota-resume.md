---
description: Find and finish the open work in this project — inventory every tracker, checkbox and marker with a controlled search, classify what is actually actionable, agree the list, then execute one item at a time against the project's own verification. Run it at the START of a session.
---

Find and finish the open work in this project.

This is the other end of `/sota-close`: that command records open items where a new session
will trip over them, this one picks them up. Neither assumes the other ran — most projects
scatter their open work across files written by people who are not here.

## 1. Inventory — and prove the search works before trusting it

Search widely before concluding anything:

- files named `TODO*`, `BACKLOG*`, `ROADMAP*`, `NEXT*`, `next-steps*`, `PLAN*`, `*.local.md`;
- unchecked `- [ ]` boxes in docs;
- `TODO|FIXME|XXX|HACK` markers in tracked source;
- `Unreleased`, "planned", "not yet", "for now" in the CHANGELOG and README;
- deferred items in ADRs and design docs — an ADR that says "we defer X" *is* a tracker row;
- open issues and PRs, if a remote is configured.

**A clean "nothing found" is the result you were hoping for, which is exactly when to distrust
it.** Four failure modes produce a confident zero, and none of them prints an error:

- **The searcher skipped the tree.** `grep -r` does not follow symlinked directories, and
  package dirs, dotfile checkouts and installed-plugin trees are symlink farms. Which flag
  rescues you depends on the *binary*: on BSD grep neither `-r` nor `-R` traverses one. Say
  which tool and which binary you used — `command -v grep` — and reach for `find -L`,
  `rg --follow` or `ugrep -R` (`sota-shell-scripting` rules/06 §2).
- **The flag meant something else.** `rg -r` is `--replace`, not "recursive"; it silently
  rewrites every match to the next token and the output looks like content
  (`sota-shell-scripting` rules/06 §2a).
- **The lister answered about one page.** `gh issue list` and friends cap at 30 by default,
  exit 0, empty stderr. A result whose size equals a round number you or the tool chose is a
  page until proven otherwise (`sota-shell-scripting` rules/06 §5).
- **The query asked your question, not the project's.** `grep` answers "does this string
  appear", never "is this idea covered". A project that writes "parked" will not match "TODO".

**Run one query whose answer you already know, in the same invocation as the real one.** If the
control returns nothing, the instrument is broken and the absence is worth nothing. Then
report the **denominator** — how many files you actually scanned — beside the finding count.
`0 found over 0 files` and `0 found over 900 files` are different answers.

## 2. Classify — show me this table before changing anything

| Class | What it means |
|---|---|
| **READY** | Unambiguous, self-contained, finishable now. |
| **NEEDS A DECISION** | Depends on a choice only the operator can make — naming, scope, priority, cost, anything security-, privacy- or money-relevant. State the question and your recommendation. |
| **DELIBERATELY DEFERRED** | The doc gives a reason to wait. Leave it, and say what the reason was. If the deferral names **no revisit trigger**, that is a finding: a deferral with no condition attached is a silent drop wearing a tracker row. |
| **NOT AN ITEM** | Template checkboxes, worked examples, a `- [ ]` inside a code fence (it renders as sample output and no one was ever meant to tick it), completed rows still phrased as open. Say so rather than "doing" them. |
| **ALREADY DONE** | Implemented, tracker never updated. The fix is a **doc correction, not code**. |

**ALREADY DONE is usually the largest class and the easiest to get wrong in the other
direction.** The summary is always the stale half, and it is the half people read — a
priorities table pointing at work its own ledger closed. Check the *ledger row*, the code, or
the commit, never the header that summarises them.

Order READY by value against risk. Estimate **blast radius and uncertainty**, not minutes: how
many files it touches, whether anything else depends on it, and what you would have to know
that you do not.

## 3. Stop and let me steer

Do not execute until the operator confirms the list. The one exception is *every* item being
READY **and** small — where small means: inside one file or one obvious unit, no interface,
schema, dependency or security posture touched, and verification already exists for it. Say
you are taking the exception and which bar it met, then carry on. An exception invoked without
naming its bar swallows the rule.

## 4. Execute — one at a time, smallest blast radius first

For each agreed item:

1. Make the change.
2. **Run this project's own verification** — find its entry point, do not assume one.
   `Makefile`, `package.json` scripts, `justfile`, `tox.ini`, `noxfile.py`, `.pre-commit-config.yaml`,
   and above all `.github/workflows/*` — CI is the definition of "passing" that actually
   gates this repo. Run what CI runs.
3. **Watch it fail before trusting it to pass.** If you did not see the check reject something,
   you do not know it ran — a suite that silently matched zero files exits 0 and prints `ok`.
   A green check whose environment cannot reach the defect is green and proves nothing; say
   what depth it reached (`sota-devsecops` rules/09 §2a).
4. **Update the tracker in the same change.** Status lives in one place; everything above it is
   derived. Grep the summary for the item's own identifier in the same commit that closes it,
   or the summary is stale before you finish reading this.

## 5. When you find a better way mid-execution

Do not silently take it, and do not silently ignore it. The threshold:

- **Just do it, and note it in the final report** — choices *inside* the item's stated scope:
  which helper to reuse, naming, test layout, ordering.
- **Pause and ask** when the better way would change the item's **shape**: its scope, a public
  interface or schema, a dependency, the security or privacy posture, the data model, or
  anything contradicting a written decision (an ADR, a spec, an explicit "we chose X because
  Y"). Also pause if the prescribed way would knowingly leave a defect, or if the item rests on
  a **false premise** — a stated blocker that is simply no longer true is common, and doing the
  work anyway is worse than saying so.

When you pause, give: what the item asked for; the alternatives; the concrete trade-off of each
(cost, risk, what it forecloses); your recommendation **and why**; and what you need to
proceed. Two or three options, not a survey. **Batch related questions into one interruption**
rather than asking serially, and keep working on any agreed item that does not depend on the
answer.

Once the operator decides, **record the decision where this project keeps them** — an ADR, the
tracker row, a comment at the site. A recorded decision is what stops the same idea being
re-litigated in three months, and that includes recorded *rejections*. If the operator chose
against your recommendation, **write down their reasoning, not just the outcome**: an outcome
with no reasoning gets re-argued by the next person who finds it surprising.

## 6. If an item is bigger than it looked

Stop and say so rather than half-finishing it. The tell is concrete: you are several files
deep in something the item never named, or you are about to change an interface to make a
"small" fix land. A half-finished item is worse than an untouched one — it looks done in the
tracker and behaves like neither.

## 7. Report honestly

- What is **done and verified**, with the command and its result.
- What you **skipped**, and why.
- What is **still open**, including anything you downgraded from READY once you looked.
- Every **judgement call** you took under rule 5, including the ones you decided were inside
  scope and did not ask about.

**Never mark something complete that you did not observe working.** If you could not test it,
name the part that is unverified rather than the whole thing being "done". If verification
failed for an environmental reason, fix the environment or say plainly that you could not —
a red run described as green is the single most expensive thing in this list.

## Constraints

- **Don't invent work no file asked for.** If you see a genuine improvement outside every
  item, collect it and summarise it at the end — do not fold it into an item.
- **Don't widen scope past what an item says**, even when the adjacent fix is obvious.
- **Prefer correcting a stale document over writing new prose.** A wrong line deleted is worth
  more than a right paragraph added beside it.

$ARGUMENTS
