# Audit Report & Tracking — Reproduction, Finding Lifecycle, Report Provenance

Scope: the fields that let a finding be **re-run by someone else** and **followed to closure**
after the report is delivered, the provenance a report needs so a reader can judge who
looked and against what, and the two rules that keep a verdict honest once the code moves —
a verdict expires with its commit (§4) and "fixed" needs three runs (§5). It extends two sections of `rules/03` without restating them: the
eight-field evidence block (`rules/03` §2) and the report order (`rules/03` §5). `rules/01`
owns how the audit is run; `rules/03` owns rating and evidence; this file owns what keeps a
delivered report usable once remediation starts.

---

## 1. Reproduction steps — a field of its own on every finding

Evidence (`rules/03` §2, field 4) shows *that* the defect exists; it does not tell the person
fixing it how to see it happen. Add a **Reproduction** field to every finding, after Evidence:

- **The shortest sequence that makes the defect observable**, written as numbered steps a
  developer who was not in the audit can follow: starting state (commit, config, seed data,
  account role), the action (request, command, input file), and the observable result that
  proves the defect — plus what the result should be once it is fixed.
- **Static-only findings still get one.** Where nothing can be executed, the steps are the
  read path: the entry point, each call that carries the tainted value, and the sink, as
  `file:line` hops. "See evidence" is not a reproduction.
- **Keep it safe to run.** Steps target a test environment, use placeholder credentials, and
  never contain a live secret or a payload aimed at production (`rules/01` §4).
- **It is what the re-audit re-runs.** The fix is confirmed when these steps stop producing
  the result *and* a fresh search cannot get round the fix (`rules/01` §4) — so write them
  to be re-executed, not narrated.

OWASP: Secure Code Review cheat sheet; Code Review Guide v2.

## 2. Tracking fields — optional, but all-or-nothing once used

A report that feeds a remediation programme needs each finding to carry its lifecycle. These
fields are optional for a one-off review; once any finding carries them, **every** finding
does, because a finding with no owner is the one that is silently dropped.

| Field | Content |
|---|---|
| **Status** | one of: open · in progress · fixed (verified at `<commit>`) · risk accepted · withdrawn |
| **Assignee** | a named person or team — not "dev team" |
| **Due date** | set from severity; an overdue Critical/High is itself reported at the next review |
| **Ticket** | a link to the issue tracker item that owns the work |

- **"Fixed" means verified, not merged.** It carries the commit at which the reproduction
  was re-run and failed to reproduce; a merged PR with no re-run stays *in progress*.
- **"Risk accepted" names who accepted it and until when.** An acceptance with no owner and
  no expiry is an unowned open finding with a nicer label; it belongs in the decision ledger
  (`rules/03` §3) where its expiry gets re-checked.
- **"Withdrawn" keeps the row** with the reason (false positive, out of scope, duplicate of
  another ID). Deleting it loses the record that it was examined and lets it be re-reported.
- **The ticket is the source of truth for status after delivery.** The report is a snapshot
  dated to its commit; do not edit its rows as work lands — issue a dated re-audit instead.

OWASP: Secure Code Review cheat sheet; Code Review Guide v2.

## 3. Report provenance — who reviewed, against which checklist

Add these to the **Scope & methodology** section (`rules/03` §5, item 2):

- **Author and reviewer names.** Who performed the review, and who checked the findings — for
  an agent-run audit, the model and the human who reviewed its output. A report with no named
  reviewer has had no second read, whatever it says.
- **The checklist actually used**, identified precisely enough to fetch again: the skill
  names and the commit or version of this library, or the organisation's own checklist and
  its revision. "Standard checklist" is not an identifier.
- **The review type and trigger** — baseline or diff, and why (`rules/01` §1) — and, where
  one exists, the ticket or change request that prompted the review.

OWASP: Code Review Guide v2.

## 4. A verdict is bound to the commit it was made at

Every terminal verdict — *false positive*, *withdrawn*, *fixed*, *risk accepted*, *dead code /
test-only* — is a claim about **specific code at a specific commit**. Record that commit beside
the verdict, and treat the verdict as **expired** once the code under it changes:

- **A dismissal lapses when its file changes.** A false positive, a test-only or dead-code
  classification, or an accepted risk on `auth.go` was true of `auth.go` at `<sha>`. If
  `auth.go` — or a file it depends on — has changed since, the finding is re-examined, not
  inherited. Carrying old verdicts forward unchanged steers the next pass away from exactly the
  code where a regression would sit.
- **A "fixed" finding that reappears is a possible regression, never a duplicate.** When a new
  finding matches one already marked fixed, but on code that changed since the fix was
  verified, keep it **open** and note the history. Filtering it as "already reported" hides a
  reverted or bypassed fix — the one outcome a re-audit exists to catch.
- **A finding inherited from another commit is re-located, not dropped.** `rules/01` §4b fails a
  citation that does not resolve; that rule assumes the finding and the reader are at the same
  commit. For a finding from an earlier report, ticket or wave, a moved or renamed file is
  drift, not hallucination: find the code again at the current commit, then apply the citation
  check to the new location. Drop it only if the code is genuinely gone.
- **Evidence from another commit cannot raise a rating.** A crash log, trace or PoC captured at
  an earlier commit supports *"this happened at `<old sha>`"*. It upgrades severity at the
  current commit only after it is re-run there.

Source: Google's Mantis toolkit (Apache-2.0) keys every carried-over verdict to the snapshot it
was made against and re-discovers it when the file changed; adopted 2026-10-02 (ADOPTION-LOG).

## 5. A fix is verified by three runs, not one

`rules/01` §4 makes the bar *"a fresh search cannot get round the fix"*. Three checks make
that bar mechanical, and each closes a known way to record a false "fixed":

1. **The unpatched baseline still fires on the current tree.** Re-run the reproduction against
   the *unpatched* code at today's commit before testing the patch. If it no longer fires
   there, something else changed; the verdict is **inconclusive**, never "fixed".
2. **Identical instrumentation for every run.** Baseline, patched and re-attack runs use the
   same build flags, sanitizers and configuration. Dropping a sanitizer between runs makes the
   crash disappear and reads exactly like a fix (`sota-c-cpp` rules/02).
3. **At least three same-class bypass attempts, all of which fail.** Vary the input along the
   axis the fix guards — off-by-one lengths, zero and maximum sizes, another entry point, an
   alternate encoding. A variant that triggers a *different* defect is a new finding, not a
   bypass. An empty or short attempt set is **verification incomplete**: "all attempts failed"
   is vacuously true of zero attempts (`sota-code-security` rules/11 §2.2).

The most common failed auto-repair blocks only the exact bytes of the reported PoC; check 3 is
what catches it.

Source: Google's Mantis toolkit (Apache-2.0) patch gate; adopted 2026-10-02 (ADOPTION-LOG).

---

## Audit checklist — quality gate on reproduction, tracking and provenance

- [ ] **Medium** — Every finding carries a **Reproduction** field with starting state,
      action, observed and expected result, or a `file:line` read path for static-only
      findings (§1)? Print finding headings that have no Reproduction line before the next
      finding or section:
      `awk '/^##+ [CHMLI]-[0-9]+/ || /^## /{if(id!=""&&!r)print FILENAME": "id; id=""; r=0} /^##+ [CHMLI]-[0-9]+/{id=$0} /^[*_]*Reproduction/{r=1} END{if(id!=""&&!r)print FILENAME": "id}' report.md`
      (assumes finding IDs like `H-3` in headings; adjust to the report's own ID format).
- [ ] **Medium** — If any finding has tracking fields, do all of them have status, assignee,
      due date and ticket; does every "fixed" name the verifying commit, and every "risk
      accepted" an owner and an expiry (§2)?
- [ ] **High** — Does every terminal verdict (false positive, withdrawn, fixed, risk
      accepted, dead code) carry the commit it was made at, and was each one re-examined when
      its file or a dependency changed since (§4)? List files changed since a verdict's commit:
      `git diff --name-only <verdict-sha>..HEAD -- <file>`. Any output means the verdict expired.
- [ ] **High** — Was a new finding matching an already-fixed one kept **open** as a possible
      regression rather than filtered as a duplicate (§4)?
- [ ] **High** — Does every "fixed" record all three runs: unpatched baseline firing at the
      current commit, identical instrumentation, and at least three failed same-class bypass
      attempts (§5)? Fewer than three is "verification incomplete", not "fixed".
- [ ] **Low** — Scope & methodology names the author, the reviewer and the checklist with
      its version (§3)? Expect three hits:
      `grep -iE '^[*_ -]*(Author|Reviewer|Checklist)[^:]*:' report.md`
