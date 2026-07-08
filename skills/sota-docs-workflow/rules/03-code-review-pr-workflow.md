# 03 — Code Review & PR Workflow

Pull request sizing and description, reviewer and author conduct, review SLAs,
stacked/draft PRs, automation boundaries, and reviewing AI-generated code.

## §1 Small PRs are the highest-leverage practice

Review effectiveness degrades sharply with size: defect-detection rate falls as
diff size grows, and large PRs converge on "LGTM" because nobody can hold 2,000
lines in their head. Everything else in this file is downstream of size.

- **Target ≤ ~400 changed lines of substantive diff; treat ~1,000 as a hard
  ceiling** requiring justification (generated code, lockfiles, and mechanical
  renames don't count — but call them out so reviewers can skip them).
- **One logical change per PR.** "Implements X *and* refactors Y" is two PRs.
  The refactor goes first, separately — it's the one that can be approved in
  minutes because behavior is unchanged and tests prove it.
- **Slicing strategies** for big features: vertical slices behind a feature
  flag; preparatory refactors first; interface/contract PR before
  implementation; data-model migration separate from the code that uses it;
  stacked PRs (§5).
- A PR that *can't* be made small (large migration, vendored code) gets a
  reviewing map in the description: read order, where the decisions are, what's
  mechanical.

## §2 PR description discipline

The description is documentation with a deadline: it's how the reviewer loads
context, and how `git log` archaeology works in two years.

Required content — **what / why / how-tested**:

- **What**: the observable change, one or two sentences.
- **Why**: the problem/motivation and the linked issue (`Fixes #123` to
  auto-close). The diff shows what changed; only the description can say why.
- **How tested**: specific — which tests added/updated, what was exercised
  manually, what wasn't and why that's acceptable.
- **UI changes**: before/after screenshots or a clip. Reviewers can't render
  JSX in their heads.
- **Risk & rollout** when relevant: feature flag, migration ordering, rollback
  plan, blast radius.
- State what's deliberately out of scope to pre-empt scope-creep review.

Use a PR template (`.github/pull_request_template.md`) to make the structure
the default. Keep it short enough that people fill it instead of deleting it.

**Bad**: title `fix bug`, body empty, 23 files changed.
**Good**:

```markdown
## What
Reject payout previews for creators with frozen accounts (422 + code
`account_frozen`).

## Why
Frozen accounts could see previews that would never execute, generating
support tickets (#892). Execution was already blocked; preview wasn't.

## How tested
- New: `test_preview_frozen_account_422`
- Manual: froze demo creator in staging, verified 422 body + UI message
- Not covered: bulk-preview path — frozen filter happens upstream
  (see `BulkPreviewService:88`), existing tests cover it.

Out of scope: unfreezing flow cleanup → #901.
```

## §3 Reviewer behavior

- **Review SLA: first response within one business day** (same-day for small
  PRs as an aspiration). Review latency is the dominant term in cycle time, and
  slow review is what teaches people to make giant batched PRs. Reviewing
  others' code outranks writing your own in the daily priority order.
- **WIP limits**: when your review queue is full, finish reviews before
  starting new work. Ten open PRs awaiting review is a team-level incident, not
  ten individual delays.
- **Label every comment as blocking or non-blocking.** Conventional prefixes
  (`blocking:`, `nit:`, `question:`, `suggestion:`, `praise:` — the
  "conventional comments" style) remove the guess about what must be resolved
  before merge.
- **Suggest, don't command; ask, don't assert.** "What happens if `items` is
  empty here?" beats "this is broken" — it's both kinder and more often
  correct, because sometimes the answer is "it can't be, see the validator."
  Comment on the code, never the author.
- **Approve with nits.** If everything remaining is non-blocking, approve and
  trust the author to address nits before merge. Holding approval hostage to
  trivia trains people to argue instead of fix.
- **Review for what automation can't catch**: design fit, correctness under
  concurrency/failure, missing tests, naming, security, API contract, "should
  this exist." If you're commenting on formatting, the CI config is the bug (§6).
- **Know when to take it offline.** Three back-and-forth rounds on one thread
  means the medium failed: call/pair, then record the conclusion in the thread
  for the archaeologists.
- An approval means "I understood this and stake my name on it," not "the
  author seems confident." If you didn't understand it, say so — that's a
  finding about the PR, usually.

## §4 Author behavior

- **Self-review first.** Read your own diff in the review UI before requesting
  review; you'll catch the debug print, the stray file, the TODO. Annotate the
  diff with PR comments where the reviewer will need context ("this rename is
  mechanical, the real change is in `scheduler.py`").
- **Respond to every comment** — fix, push back with reasoning, or file a
  follow-up issue. Silently ignoring a comment, or marking it resolved without
  action, destroys reviewer trust permanently.
- **Don't force-push during active review**: it orphans comment anchors and
  destroys the reviewer's "what changed since my last pass" diff. Push
  fixup/appended commits during review; clean up history (squash/autosquash) at
  merge time. (Pre-review and stacked-PR rebases are fine.)
- The author merges (where the platform allows) — they own the timing against
  deploys and freezes.
- Don't request review on red CI. Reviewer attention is the scarce resource;
  spend it on code that at least compiles and passes tests.

## §5 Draft and stacked PRs

- **Draft PRs for direction checks**: open as draft with a specific question
  ("is this the right seam?") before investing in polish. Cheap course
  correction beats a finished PR built on the wrong design. Mark ready only
  when it meets the full bar (§2, green CI).
- **Stacked PRs for large changes**: a sequence of dependent, individually
  reviewable PRs (each targeting the previous branch), reviewed and merged in
  order. This is how you keep §1's size discipline on multi-thousand-line
  features. GitHub now ships native stacked PRs (private preview as of
  mid-2026: `gh stack` CLI, a stack map in the PR UI, branch protection and CI
  evaluated against the final target branch, auto-rebase of the remaining
  stack after each merge) — prefer it where enabled, since reviewers need no
  third-party account. Until then, tooling (Graphite, `gh`/`git` stacking
  workflows, `git-spice`, jj-based flows) automates the rebase cascade;
  without tooling, keep stacks ≤3 deep or the rebase tax exceeds the review
  benefit.
- Each PR in a stack must stand alone: green CI, coherent description, no
  forward references that make it unreviewable without reading the whole stack.

## §6 Automation does the robot work

- **Lint, formatting, type errors, import order, coverage thresholds, secret
  scanning, license checks are CI's job.** A human pointing out a formatting
  issue is a process failure: add the rule to CI and it never recurs. Reviewer
  attention is for judgment (§3).
- Format-on-save + pre-commit hooks catch locally; CI enforces. Nobody debates
  style in review because style isn't an opinion anymore — it's a config file.
- Bot-noise budget: auto-comments (coverage deltas, preview links, size labels)
  must collapse/update in place. A PR where human comments drown in bot spam
  gets worse review.
- CI status gates merge: required checks, no `--no-verify` culture, branch
  protection on the default branch (supply-chain side: `sota-devsecops`).

## §7 Reviewing AI-generated code

AI assistance raises PR volume; the review bar does not move.

- **Same bar, same process.** "An agent wrote it" is not a provenance excuse —
  the human who opens the PR owns every line of it, including understanding it.
  If the author can't explain a hunk, it isn't ready for review.
- **No rubber-stamping volume.** The failure mode of 2025–26 is plausible,
  confident, subtly-wrong code reviewed at "looks idiomatic" depth. Spot-check
  the parts AI gets wrong most: edge cases, error paths, concurrency,
  off-by-one boundaries, invented APIs, tests that assert the implementation
  rather than the requirement.
- **AI-generated tests deserve the most suspicion**: verify they fail without
  the change (mutation thinking), not just that they pass with it.
- Disclose substantial AI generation in the PR when team policy asks; either
  way, size limits (§1) apply with extra force — generated code is cheap to
  produce and expensive to review, so the queue saturates from the author side.
- AI *reviewers* (CI-integrated review bots) are a pre-filter on the author's
  side, like a linter with opinions — they reduce trivial findings reaching
  humans, they don't replace the human approval (§3's "stake my name on it").

## Audit checklist

- [ ] Median merged-PR size is small (≲400 substantive lines); large PRs are exceptions with stated justification or a reviewing map.
- [ ] PRs are one logical change; refactors land separately from behavior changes.
- [ ] PR template exists; sampled recent PRs have what/why/how-tested, linked issues, screenshots for UI changes.
- [ ] Review first-response time is ~1 business day or better; no PRs silently aging past the SLA.
- [ ] Blocking vs non-blocking comments are distinguishable (prefixes/labels); approve-with-nits happens in practice.
- [ ] Authors self-review (look for author-annotated diffs), respond to all comments, and don't force-push mid-review.
- [ ] Draft PRs used for early direction; oversized features arrive as stacks of independently green PRs.
- [ ] CI owns lint/format/type/coverage; sampled reviews contain zero human style comments; required checks gate merge.
- [ ] Review depth on AI-heavy PRs matches human-written ones: comments engage with logic, tests proven to fail without the change, no volume rubber-stamps.
- [ ] Merged PR descriptions are useful in `git log` archaeology (pick 5 from six months ago and try to reconstruct the why).
