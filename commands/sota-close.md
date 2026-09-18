---
description: End-of-session closure pass — retract what proved wrong and correct it everywhere it reached, hand off open items where the next session will trip over them, update the docs this session made false, re-derive every number from its source, and commit the evidence. Run it at the END of a working session.
---

End-of-session closure pass. Work through these in order and report each one.

**Before step 1: your own summary is not a source.** By this point in a session the context
has usually been compacted at least once, so most of what you would "recall" is your own
earlier prose *about* the work rather than the work. Re-reading it re-runs the reasoning that
produced it, which is the weakest check available. Every step below is executed against
artifacts — `git diff`, `git log`, the file on disk, the command run again — never against
recollection. A verbatim file quoted into context earlier is not primary either: it may
predate an edit made since. Re-read the path.

**The order is load-bearing.** Steps 2–6 all *write*. Anything step 1 fails to catch gets
propagated by them into a doc, a commit message, a memory file, or a hand-off — where the
next session will read it as established.

## 1. Retract first

List every claim you made this session that later proved wrong, unverified, or was overtaken
by something you found afterwards. Include the ones only you noticed. **If there are none,
say so explicitly** — that is a valid answer, but it is also a claim, so it means you looked.

"What did I get wrong" is a bad recall query. Sweep the candidate shapes instead:

- anything you asserted *before* running the command that later confirmed it;
- any number produced by arithmetic on a remembered number rather than by counting;
- any absence — "nothing else uses this", "that isn't covered" — backed by a single search;
- anything the user corrected you on, including corrections you accepted in passing;
- any "should work", "that's fixed", "done" not followed by output.

**Then find where the claim went.** A wrong claim does not stay where you said it. It gets
written into a commit message, a doc sentence, a code comment, a ledger row, a memory file, a
PR description. Grep its distinctive words across the tree *and* across this session's commits
(`git log -S '<phrase>'`). Correcting the copy you remember and leaving three behind is worse
than not correcting at all: the retraction makes the survivors look reviewed.

**Delete or supersede — decide per line, this is where the pass goes wrong.**

- **Delete** when the line states *current state*: a README sentence, a rule's imperative, a
  count, a capability claim. A caveat beside a wrong line leaves both readings live and the
  reader picks one. Prefer deleting a wrong line to annotating it.
- **Supersede** — keep the original, add the correction and its date beside it — when the line
  is a *record*: a changelog entry, a measurement, a ledger verdict, a dated claim. Editing a
  record rewrites history and destroys the trail showing the number moved.

Cite the primary source for each correction: the command re-run and its output, the file at
the line, the doc or advisory fetched now. "I realised it was wrong" is not a source.

## 2. Record open items where a new session will trip over them

A backlog row is not a hand-off. The next session reads what its harness puts in front of it:
the worklist or resume file, the branch it lands on, `CLAUDE.md`/`AGENTS.md`, an open PR, a
failing check. An item filed anywhere else is a note to yourself.

Per open item, one line with three fields: **what it is · where it now lives · what a future
session would have to read to find it.** If the third answer is "search the repo", it is not
recorded. Prefer the artifact the next session is already forced to read — a failing gate, a
draft PR, a TODO at the line it applies to, the branch name itself.

**Status lives in exactly one place.** If an item's state is tracked in a ledger, every summary
above it is *derived* — update the summary in the same change, or it drifts within a day. (In
this library's own roadmap that drift happened three times in one session, and the summary is
always the stale half and the half people read; it took invariant 26 to stop it.)

**A pushed branch with no PR is checked by nothing** — every gate runs on the PR — and it reads
as finished. Name every branch you pushed and say whether a PR exists:

```sh
git branch -r --contains HEAD
gh pr list --head "$(git rev-parse --abbrev-ref HEAD)" --state all
```

## 3. Update documentation, memory and agent files

Same change as the work, not a follow-up. Then remove what this session made false: **prefer
deleting a line to adding a caveat beside it.** Two contradicting lines cost a reader more
than one missing line.

Agent files — `CLAUDE.md`, `AGENTS.md`, skills, memory entries — are **instructions, not
notes.** They load into sessions that know nothing about today, so a stale line there is
*executed*, not merely read, and a line that is merely noise still spends the budget that
makes the rest adhere. Cheapest test before writing one: *would I want this injected into an
unrelated task next week?* If not, it belongs in the worklist from step 2.

Write the mechanism, not the episode. "X silently returns empty when Y, so control it with Z"
survives; "we hit something odd on Tuesday" does not. Deleting is half the update — stale
instructions do not decay quietly, they get followed.

## 4. Validate by execution, not recall

Every number you write in this pass is re-derived **now**, with the command shown next to it.
A number carried forward from earlier in the session is recall, and recall is the thing this
pass exists to compensate for.

- **Count, do not compute.** "43 files, so 41 after the two deletions" is arithmetic on a
  remembered 43.
- **Two derivations that disagree are a finding, not rounding.** Reconcile to a named cause
  before reporting either number — and note that the fix for one can silently change the
  population the other counted. (Measured here: 330 vs 339 merged PRs reconciled to a wrong
  predicate, `state=closed` including closed-unmerged — `sota-shell-scripting` rules/09 §5.)
- **Every absence needs a positive control in the same invocation** — search for something you
  have already seen in that scope. If the control comes back empty, the instrument is broken
  and the absence is worth nothing. "Independent" means a different failure mode, not a
  different phrasing: two searches of a symlink tree agreed on zero and both were wrong
  (`sota-shell-scripting` rules/06 §2).
- **Two tells worth a second look.** A result whose size equals a round number you or the tool
  chose is a page, not a total (`sota-shell-scripting` rules/09 §5). An implausibly *large*
  result is usually an empty value that removed a filter rather than matching nothing
  (`sota-shell-scripting` rules/06 §2b).

## 5. State plainly what is not done

Three separate lists, not one:

- **Not done** — scope you did not cover. Say it in the sentence the user would use, not in a
  softened one.
- **Blocked, and on whom** — a person, a credential, an upstream fix, a decision the user has
  not made. Name the unblocking event. "Blocked" with no owner is "not done".
- **Uncertain** — claims you are shipping that could still be wrong, at the granularity of
  their evidence. One observation licenses "this happened once"; *always*, *every*, *by design*
  assert a mechanism, and a mechanism is established by reading the code that implements it,
  never by an artifact however clean.

If a check was **skipped** rather than passed, say skipped. A gate whose environment cannot
reach the defect is green and proves nothing — report the depth it actually reached.

## 6. Commit the evidence, then confirm it landed

Three guards before anything is written:

- **Is this repo yours to commit to?** On an upstream you do not own, a diff against a tracked
  file rides on every branch cut from it, into every later PR. Ask first, and keep agent
  scaffolding in `.git/info/exclude` rather than the tracked `.gitignore`.
- **Check the branch before the first commit, not at push time.** `git rev-parse
  --abbrev-ref HEAD` — if it is the default branch, branch now. The trigger is the moment
  right after a merge, when the checkout returns to `main` and work simply continues.
- **Do not commit private files.** Read `git status --porcelain` and the staged list by eye;
  never `git add -A` blind. Reports, transcripts, `*.local.*`, anything carrying a hostname,
  a customer, or a credential stays out.

The message carries the **evidence**, not a description of the change — the diff already
describes the change:

- what was retracted, and every file the correction landed in;
- the command and its result for any number the message states;
- what is still open, in one line.

Then confirm the push landed, which is a different fact from "the push command ran":

```sh
git push -u origin "$(git rev-parse --abbrev-ref HEAD)" && git rev-parse HEAD '@{u}'
```

`&&`, never `;` — `;` ignores exit status, and a gate-then-act chain written with it will
report success after a printed FAIL. Do not pipe the push through `tail`/`head` and read the
result either: `$?` after a pipeline is the *last stage's* status. The two SHAs must match. If
the branch needs a PR, open it or say plainly that it is unlanded.

## Finally

Print the six answers in order, short, with the commands beside the numbers. **If a step
produced nothing, say so in one line rather than omitting it** — an omitted step is
indistinguishable from a completed one, and this pass is read by someone who was not here.

$ARGUMENTS
