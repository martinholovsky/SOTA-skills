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

It ships as a slash command: **`/sota-report`**, installed by `scripts/install.sh` (and
therefore `scripts/update.sh`) into `~/.claude/commands/sota-report.md`. Run it at the **end**
of a working session in the project that hit the problems:

```text
/sota-report
/sota-report focus on the eBPF work and the two gate failures
```

Anything you add after the command is passed through, so you can point it at the part of the
session worth writing up.

**The prompt text lives in one place — [`commands/sota-report.md`](../commands/sota-report.md)
— and is not repeated here.** Two homes for one rule is how they drift; this file holds the
reasoning, that file holds the thing that ships. If you want to read it before installing, or
paste it into a tool that has no slash commands, open that file.

## Two ways a report reaches the library

`/sota-report` always writes a **private** `FIELD-REPORT-*.local.md`, then prints a short
**extract** — finding, mechanism, whether the rule was already loaded, what caught it,
proposed rule, confidence. It never posts anything.

- **Maintaining the library?** Keep the file. An issue is friction you do not need; the
  ledger entry is the record that matters.
- **Using the library on your own work?** Submit the extract via the
  [field report template](https://github.com/martinholovsky/SOTA-skills/issues/new?template=3-field-report.yml).
  This is how the library hears from anyone but its maintainer, and it has no other channel.

**The extract is not the report, and that is deliberate.** This repository is public and
issues are indexed, cached and mirrored — they cannot be truly deleted. Field reports are
written from real sessions and, per this repo's own `.gitignore`, *"routinely name private
repos, internal hosts and customer detail"*. The extract drops transcripts, appendices and
real paths: most of the disclosure risk lives there, and it is the part a maintainer who
cannot run your repo needs least.

**The command is forbidden from posting.** Not "discouraged" — the prompt says print and
stop. The gap between *"I generalised it"* and *"a human confirmed it is safe to publish"* is
where a leak lives, and no genericisation pass by the model that just wrote 400 lines of
private detail closes it. A human reads the extract, then submits it.

Anything security-sensitive goes to the
[private advisory form](https://github.com/martinholovsky/SOTA-skills/security/advisories/new),
never to an issue — see [SECURITY.md](../SECURITY.md).

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
