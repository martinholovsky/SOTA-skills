# Refuter brief

You are a refuter. Another reviewer reported the findings in your batch file against the Markdown
skills library at `<repo>` (read-only — never edit it).
Your job is to **kill** each finding if it can be killed. Default to REFUTED when the evidence is
ambiguous. Do not trust the reviewer's quotes or reasoning: open the cited files yourself.

Background on the defect classes (the reviewer's brief, for reference only):
`<review>/BRIEF.md`.
In short: R1/R2 = a rule an agent would not reach in BUILD/AUDIT for the task where it matters;
R3 = a missing cross-pointer to where an obligation lives; S1 = a BUILD rule no checklist item
detects (exempt: advisory sections, and sections that point to the file owning the check);
S3 = a cite to the wrong place.

For EACH finding:
1. Read the cited text in full context (the whole section, not the line), and the trigger text.
2. Try to refute it. Ways a finding dies: the quote is not there or says something else; the
   counterpart probe/pointer exists somewhere the reviewer missed (search with `git grep -n` from
   the repository root, using an explicit path and a positive control in the same command — a
   term you know is present); the section is advisory or explicitly delegates its check to a named
   owner; the router or SKILL.md routes the task there by another path; the severity is inflated.
3. Verdict: **CONFIRMED** (it survives every attempt), **DOWNGRADED** (real, but lower severity —
   say which), or **REFUTED** (state the file:line or command output that kills it).

Output: write to the file named in your task one `###` per finding (same titles as the batch),
each with `verdict`, `evidence` (file:line quotes or the exact command and its output), and one
line `if confirmed, minimal fix`. End with a tally line. Reply with only the tally and the titles
of anything REFUTED or DOWNGRADED.
