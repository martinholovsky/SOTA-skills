# Asking another session for a field report

This library has **no telemetry**. It learns nothing from being used unless the session that
used it says so — and the session that hit the problem is the only observer of it, at the only
moment it is visible.

Field reports are the highest-yield intake this project has. The ledger records **seven
field-report intakes** with near-total adoption — most `adopted with a correction` rather than
as written — against **~4 of 13** for commissioned research
([ROADMAP.md](ROADMAP.md), item 2 of the intake notes). The reason is not that the reporters
are better: a field report supplies a **reproducer**, a research report supplies a citation.

*(The seven is a count of `### … field report / brief` headings in
[ADOPTION-LOG.md](ADOPTION-LOG.md) — recount it rather than trusting this sentence, per
invariant 30's lesson about restated numbers.)*

Paste the prompt below at the **end** of a working session in another project, while its
history is still in context. Asked cold, a model reconstructs plausible-sounding failures it
never had.

---

## The prompt

```text
Write a SOTA-skills field report for this session.

You have been applying the sota-* skills (or should have been). I maintain that library and
have no telemetry: it learns nothing from use unless a session like this one says so. What I
need is not a summary of what you built — it is the places the guidance failed, was absent,
was wrong, or was right and did not fire.

## Write the file, don't print it

`FIELD-REPORT-<PROJECT>-<YYYY-MM-DD>.local.md` in the repo root. The `.local.md` suffix is
gitignored in SOTA-skills because that repo is public and yours may not be. Genericise as you
write: no company names, internal service names, private hostnames, or customer data.
Products appear only as neutral examples ("a Postgres instance", "an eBPF sensor").

## What is worth reporting, in descending order of value

1. A rule of the library's that CAUSED a defect. Followed literally, it produced the bug.
   This outranks everything else — an absence is a gap, a wrong rule is a liability.
2. A rule you had IN CONTEXT and broke anyway. Say so explicitly and separate these from
   coverage gaps. They are evidence about rule *shape* — placement, salience, wording — and
   they change how the library is written rather than what it contains.
3. Two loaded rules that contradicted each other. Name both, say which you followed, and why.
4. Real surface area with no owning skill — a routing gap. Say what the task was, and which
   skill should have triggered from its description alone.
5. A claim in the library refuted by a primary source you checked this session — a version, a
   flag, an API behaviour, a spec. Freshness rot.
6. Something that worked, if a control or a gate caught a defect that discipline would not
   have. I need to know which mechanisms pay for themselves.

## Per finding, this structure

    What happened        — the concrete sequence, with the command, error or diff
    Why it happened      — the mechanism, not the emotion. "I was careless" is not a mechanism
    Evidence             — a transcript, exit code, file:line, or measurement someone can re-run
    What caught it       — the control, the gate, the reader, or "nothing; the user did"
    Proposed change      — target skill + section, and the rule as you would write it
    Confidence           — and what would falsify it

## Four checks that decide whether I can act on it

A. Check coverage in the LIBRARY'S vocabulary, not yours. Before writing "nothing covers
this", search for the words the library would use, not the words you would. A real example: a
gap was declared after searching "one instance | a single observation" while the corpus said
"one sample" in six files, including a named failure mode. Run a positive control in the same
command (search a term you know is there); if the control returns nothing your instrument is
broken and the absence is worth nothing. A control proves the instrument works; it does not
prove your query asks the corpus's question.

B. Name the skill that would OWN the topic, and read its section headings. Twice, reports have
proposed rules for a file that does not cover the subject while the real owner covered it
under different words. Grep answers "does this string appear", never "is this idea covered".

C. Reproduce every falsifiable claim, and include the reproduction. If you assert a mechanism
— "X happens because Y" — build the smallest thing that shows it, and state the falsifier
before you run it. If it does not reproduce, that is an absence claim too: it needs a control
arm proving your harness can produce any outcome, or you have only shown that your instrument
reaches nothing. A null arriving instantly and identically on both runs is usually a harness
that never engaged. Report it as "did not reproduce here", not "refuted".

D. State a claim at the granularity of its evidence. One observation licenses "this happened
once". Words like always, every, by design, is truncated assert a MECHANISM, and a mechanism
is established by reading the code that implements it — never by an artifact, however clean.

## Three sections that make a report land

- "Considered and NOT proposed" — things you thought about and rejected, with the reason. This
  is where reviewer judgement adds the most, and items from it have been adopted more often
  than you would expect.
- Evidence strength per finding — grade them yourself. "This rests on one case", "this is a
  near-miss I caught before acting", "these two come from the same stack". A report that
  grades itself honestly is easier to adopt, not harder.
- An appendix with artifacts — transcripts, the relevant function, the log. Genericised. I
  cannot see your repo, and "trust me" is not evidence.

## What makes a report worthless

- A tally instead of per-item verification. "15 of 19 already covered" has been wrong twice.
- Proposals with no reproduction, where the mechanism is plausible and untested.
- Findings phrased as feelings about the guidance rather than as falsifiable claims.
- Praise. I cannot act on it.
- Padding to reach a count. Two real findings beat six thin ones; say if there is only one.

## Finally

If nothing failed this session, say that instead of inventing material — a clean session is
data too, particularly about which parts of the library are load-bearing under real work.
```

---

## Why each check is in there

Every one is a failure that has actually happened during intake, not a hypothetical:

| check | what it prevents | where it went wrong |
|---|---|---|
| **A — corpus vocabulary** | a gap declared against a working instrument | 2026-09-14: control returned four files, the search term was simply not the library's. Became a correction to operating principle 3 |
| **B — name the owning skill** | a rule adopted into the wrong file, or a duplicate | 2026-09-12: verified an absence *inside the file the report named*; the topic was owned, better, elsewhere. Had to be removed and replaced with a pointer |
| **C — control arm on a refutation** | "refuted" reported from a harness that reaches nothing | 2026-09-14: two confident refutations from harnesses that could not produce any outcome. The third attempt added a control arm and the mechanism reproduced immediately |
| **D — claim granularity** | a mechanism asserted from one artifact | 2026-09-14: "truncated in place" written into two tracked documents from timestamps alone. True by luck; the first grep had surfaced evidence for the opposite reading |

## After the report arrives

Run the intake the way [ADOPTION-LOG.md](ADOPTION-LOG.md) records it:

- **Reproduce every falsifiable claim before adopting** — the reporter's reasoning is usually
  sound and their *supporting* claims are where the errors live.
- **Verify each claimed gap against the library, per item.** A tally is not a verification.
- **Read the "considered and NOT proposed" section** — it has a high adoption rate.
- **Expect `adopted with a correction` to be the common verdict**, not the exception.
- **Write the ledger entry**, including placements that differ from what was proposed and why.
  Invariant 31 requires the entry; the reasoning is what makes it useful later.
