# Reachability and BUILD/AUDIT sync review — shared brief

Repository (read-only, do NOT edit anything in it): `<repo>`.
It is a library of Markdown skills an AI agent loads to BUILD software and to AUDIT it. Each skill
is `skills/<skill>/SKILL.md` (BUILD steps, AUDIT steps, a rules index whose rows say "read this
when…") plus `skills/<skill>/rules/NN-*.md` files, each ending in `## Audit checklist` (probes an
auditor runs). The router is `skills/sota/SKILL.md`. An agent normally reaches a rules file only
through: the router → a skill's SKILL.md BUILD/AUDIT steps or rules-index row → the file; or a link
from another rules file.

## The defect that motivated this review (a worked example — find more like it)

`sota-rust` gained `rules/09-formal-verification.md` (Kani proofs). It was linked from SKILL.md's
BUILD step 1 only for tasks that say "prove …" or touch `#[kani::*]`, and AUDIT recon loaded it only
when `kani::` already appeared in the code. So: (1) an ordinary "build a parser for this network
protocol" task loads `rules/05` (untrusted input), and rules/05 never pointed to rules/09 — the
builder was never asked whether a security-critical parser deserves a proof; (2) the AUDIT probe
"security-critical crate with no fuzz target and no Kani harness" lived in rules/09, which is only
loaded when harnesses exist — so the probe could never run in the very crate it targets. The rule
existed; the path to it started from the wrong end.

## Defect classes to report

- **R1 — BUILD trigger miss.** A rule (file or section) matters for a task shape that the skill's
  BUILD steps and the rules-index row would NOT route to. Name the concrete task an agent would be
  given (in plain words, as a user would phrase it), the file it WOULD load, and why the rule is
  missed.
- **R2 — AUDIT trigger miss.** A checklist probe that can only run if its file is loaded, where the
  AUDIT steps / index row load that file only when the thing the probe checks for is PRESENT (so an
  absence probe never runs where it matters), or where nothing in the AUDIT steps or index row would
  select the file for the codebase the probe targets.
- **R3 — missing cross-pointer.** File A is the natural home for a task and states (or should state)
  an obligation whose detail lives in file B (same or another skill), and A does not point to B, so
  an agent who loaded A never learns of B. Only report when the obligation is substantive, not when
  the topic is merely related.
- **S1 — BUILD rule with no AUDIT probe.** A section that tells builders to do something checkable,
  with no checklist item (in that file, or in a file it explicitly points to as the owner) that
  would detect the violation. **Exempt, do not report:** advisory sections ("prefer X where it
  fits"), and sections that say their check lives in a named sibling file/skill.
- **S2 — AUDIT probe with no BUILD rule.** A checklist item that flags something no section of the
  file (or a file it points to) tells builders to do — an auditor would mark down a team that
  followed the library.
- **S3 — broken section cite.** A checklist item or pointer citing `§N` / `rules/NN` that does not
  exist or names the wrong section.
- **S4 — SKILL.md BUILD/AUDIT asymmetry.** SKILL.md's BUILD steps require something (wire a job,
  a lint, a test) that SKILL.md's AUDIT steps and every checklist leave unchecked, or AUDIT checks
  something BUILD never asks for.

## Rules for you

1. Read each assigned skill's SKILL.md in full and each of its rules files in full (use the Read
   tool; files are ≤500 lines). Do not sample. Count the files you read and report the count.
2. A finding is only a finding if you quote the exact text it rests on with `file:line`. For R1/R2
   also quote the trigger text (BUILD step / AUDIT step / index row) that fails to fire. For S1 quote
   the BUILD sentence and state which checklist items you checked (by line range).
3. Before reporting R3 or S1, search the rest of the library for the counterpart (`git grep -n` in the
   repository, with a positive control in the same command — e.g. a term you know exists — and an
   explicit path). An obligation covered elsewhere WITH a pointer is not a defect.
4. Severity: **High** = a security-relevant or data-loss-relevant rule that is unreachable in the task
   where it matters (R1/R2/R3), or a security-critical BUILD rule with no probe (S1). **Medium** =
   correctness/reliability rules in the same shapes. **Low** = hygiene, S2, S3. Mark anything you are
   not sure of `UNSURE` rather than inflating it.
5. Prefer few true findings over many speculative ones. Do NOT report style, wording, or missing
   topics the library simply does not cover — only reachability and BUILD/AUDIT correspondence.
6. Write your full findings to the output file named in your task, as Markdown: one `###` per
   finding with fields `class`, `severity`, `file:line`, `quote`, `trigger quote` (R1/R2), `why`,
   `proposed fix` (one or two sentences, naming the file and section to change), `confidence`. End
   with a `## Coverage` section: skills reviewed, files read (count, listed), and a count of findings
   per class. Then reply with a 10-line summary only.
