# Audit Report & Tracking — Reproduction, Finding Lifecycle, Report Provenance

Scope: the fields that let a finding be **re-run by someone else** and **followed to closure**
after the report is delivered, and the provenance a report needs so a reader can judge who
looked and against what. It extends two sections of `rules/03` without restating them: the
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
- [ ] **Low** — Scope & methodology names the author, the reviewer and the checklist with
      its version (§3)? Expect three hits:
      `grep -iE '^[*_ -]*(Author|Reviewer|Checklist)[^:]*:' report.md`
