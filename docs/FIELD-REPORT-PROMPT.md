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

**Its sibling is [`/sota-close`](../commands/sota-close.md)**, which runs at the same moment
and points the other way: `/sota-report` tells the *library* what went wrong, `/sota-close`
closes the *session* down — retract, hand off, re-derive, commit. Running both at the end of a
session is the intended shape, and neither needs the other.
[`/sota-resume`](../commands/sota-resume.md) is the third: it opens a session by finding the
open work, where `/sota-close` ended one by recording it. The fourth,
[`/sota-audit`](../commands/sota-audit.md), asks the question in between — whether the rules
that own this surface were applied to what the session actually built. It feeds this one: a
rule it finds missing, wrong or absent is exactly what a field report is for. Its escalation,
[`/sota-deep-audit`](../commands/sota-deep-audit.md), is the same question asked with
independence and scale behind it, and feeds this one the same way.

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

## Known gap: the plugin install's version stamp is unverified

`/sota-report` resolves the version it stamps by reading `VERSION` next to the installed
library. **Only the symlink install has been exercised** — `readlink ~/.claude/skills/sota`
→ repo → `cat …/VERSION`, verified on a real machine at the v1.42.0 cut. The `--copy` and
**plugin** paths are written but untested: no plugin-only install was available. The prompt
tells the model to look under `~/.claude/plugins` and to write `unknown` rather than guess,
so the failure mode is a missing stamp and not a wrong one — but a wrong stamp is exactly
what triage trusts, so this is the first thing to check if a plugin user's report arrives
with an implausible version. **Unblocking it needs a plugin-only install to test against.**

## A report from an old version is still evidence

Reports arrive from whatever version the reporter had. **Do not reject one for being stale,
and never ask the reporter to update and resubmit** — the session happened under the installed
version, updating cannot re-run the work, and a fresh stamp on old behaviour is worse than an
honest old one. The channel is the scarce thing: a stale report costs one `git log`, a report
never sent costs everything in it.

**Most of the library does not move.** Measured 2026-09-14 over a genuine month
(`v1.22.5`, 2026-08-14 → `HEAD`): **93 of 271 rules files changed — 66% untouched.** A
month-old report is more often than not about text that still ships verbatim.

**The triage is one command**, because the extract names the file it is about:

```sh
git fetch -q origin
git cat-file -t <their-commit>     # "commit", or the stamp names nothing you have
git log --oneline <their-commit>..origin/main -- <every-file-the-report-cites>
```

Range from the **commit**, not `v<their-version>`: a symlink install moves with every pull
while `VERSION` stays put, so one version stamp can cover many content commits. Fall back to
the version tag only when the report has no commit, and say so in the ledger entry. Compare
against **`origin/main`**, not your local `HEAD`, which may itself be stale.

Empty output means the text the reporter ran is the text that ships now. It does **not**
mean the finding is true: that is what the next section is for.

When it *did* change, three outcomes — and all three are worth a ledger line:

| what changed | verdict |
|---|---|
| the change already fixed it | **close, and record it** — this is the only signal the library gets that a fix actually reached a user |
| changed for unrelated reasons, the defect survives in new words | **adopt, restated** against current text; the mechanism outlived the wording |
| the section was removed or replaced | **historical** — close with a pointer, but log it: "reported after it was fixed" says whether fixes land |

**Classify by finding type, not by age.** Version-sensitivity varies more than recency does,
and the template's fields already tell you which you have:

- *"A rule I had in context and broke anyway"* — nearly version-independent. It is about
  placement and salience, which survive rewording. A year-old one is still good.
- *"A rule of yours caused the defect"* — low sensitivity; mechanisms outlive edits.
- *A coverage gap* — medium. Check the skill that would **own** it, not only the cited file.
- *A stale version or CVE claim* — high. Recheck against latest first; most likely fixed.

## After the report arrives

**A report is a set of claims, not findings. Nothing in it is trusted as written — not
its version stamp, not its quotes of our text, not its counts, not its measurements, not its
proposed wording.** It was written by a model at the end of a long session, possibly against an
older library, with instruments you never saw. Every claim gets one of four labels in the
ledger entry, with the command that produced the label: **verified** (reproduced here),
**corrected** (reproduced, but the claim or the proposal needed changing), **refuted**, or
**not reproducible here** (and why). An item with no label has not been taken in.

1. **The stamp is a claim.** Run the triage above. If the stamp resolves to nothing, or the
   install type is `unknown`, treat every claim about library text as unverified until
   re-checked against `origin/main`.
2. **A claim about our text is re-checked against current `origin/main`, even when the stamp is
   current.** "rules/NN says X", "file F contains none of Y" and "the checklist has no item for
   Z" are searches the reporter ran with an instrument you cannot inspect. Re-run each with a
   positive control in the same invocation, and check the skill that would **own** the topic
   as well as the file the report names.
3. **A behaviour claim is reproduced by you**, in a disposable repo, a scratch directory or a
   container, on both sides of any platform split the claim implies. The report's own
   reproduction counts as a lead, not as evidence.
4. **The proposed wording is a claim too, and it is where most corrections land.** Check every
   flag, command and number in it against your reproduction before it goes into a rules file.
   2026-10-24, one report: its proposed fix `rg --no-ignore` still missed a tracked file in a
   hidden directory (it needed `--hidden` as well), its "`git check-ignore` does not reveal it"
   was false with `--no-index`, and its unexplained macOS non-reproduction had a documented cause
   (BSD `pgrep` excludes ancestors by default). All three were caught only by re-running.

Then run the intake the way [ADOPTION-LOG.md](ADOPTION-LOG.md) records it:

- **Reproduce every falsifiable claim before adopting** — the reporter's reasoning is usually
  sound and their *supporting* claims are where the errors live.
- **Verify each claimed gap against the library, per item.** A tally is not a verification.
- **Read the "considered and NOT proposed" section** — it has a high adoption rate.
- **Expect `adopted with a correction` to be the common verdict**, not the exception.
- **Write the ledger entry**, including placements that differ from what was proposed and why.
  Invariant 31 requires the entry; the reasoning is what makes it useful later.
