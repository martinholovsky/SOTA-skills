---
description: Write a SOTA-skills field report for this session — where the guidance failed, was absent, was wrong, or was right and did not fire. Run it at the END of a working session, while the history is still in context.
---

Write a SOTA-skills field report for this session.

You have been applying the sota-* skills (or should have been). I maintain that library and
have no telemetry: it learns nothing from use unless a session like this one says so. What I
need is not a summary of what you built — it is the places the guidance failed, was absent,
was wrong, or was right and did not fire.

## First, record which version produced this

The evidence is bound to the version that produced it, so the report opens with:

    SOTA-skills version : <from the VERSION file next to the installed library>
    Install type        : symlink / --copy snapshot / plugin / unknown
    Date                : <today>

Resolve it without guessing: `readlink ~/.claude/skills/sota` gives the repo path for a
symlink install — `cat <that>/../../VERSION`. For a plugin install look under
`~/.claude/plugins`. **If you cannot resolve it, write `unknown` and say why.** A wrong
version stamp is worse than none: it is the field a maintainer trusts to decide whether your
finding still applies.

**Do not update the library and re-run this.** The session already happened under the
installed version; updating changes the skills but cannot re-run the work, so you would
produce a report about old behaviour stamped with a new version. Report against what you
actually used. Being months behind is fine — most of the library does not move, and triage
is one `git log` on the file you cite.

## Write the file, don't print it

`FIELD-REPORT-<PROJECT>-<YYYY-MM-DD>.local.md`. Genericise as you write: no company names,
internal service names, private hostnames, or customer data. Products appear only as neutral
examples ("a Postgres instance", "an eBPF sensor").

**Where to put it: outside the target repo's working tree, unless you have checked two things
there.** `.local.md` is gitignored *in SOTA-skills*; that is a fact about that repo, and it
does not travel with this instruction. In the repo you are reporting on, check (1) that the
pattern is actually ignored — `git check-ignore -v <file>` answers it, exit 0 naming the rule
that matched and exit 1 with no output when nothing does, and it reads `.git/info/exclude` as
well as `.gitignore`, which is where agent scaffolding usually lives — and (2) that no
**working-directory** scanner runs over the tree, because a directory scanner does not read
`.gitignore` at all (`sota-secrets-management` rules/04, verified on gitleaks 8.30.1). Writing
the report into the root of a repo mid-session otherwise dirties the tree and feeds an
unreviewed file to a secret gate, which then fails on your own report. When in doubt write it
outside and move it in afterwards — that is what a field session actually did on 2026-09-15,
after this instruction's literal form cost it a red gate.

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
prove your query asks the corpus's question, **nor that your scope contains the answer**: draw
it from where your search is least likely to reach (the router, `commands/`, a `SKILL.md`),
and print the file count beside the zero (`sota-shell-scripting` rules/06 §2).

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

## Then offer a publishable extract — but do not publish it

The file above is **private by default** and stays that way. After writing it, print (do not
write to disk, do not post) a short **extract** suitable for a public issue:

    What happened            generalised: "an eBPF sensor", not the real name
    Why — the mechanism
    Was the rule already loaded?     the highest-value field
    What caught it
    Proposed change          target skill, and the rule as you would write it
    Confidence + falsifier

**Rules for the extract, and they are not negotiable:**

- **Leave out transcripts, appendices, logs and real paths.** They carry most of the
  disclosure risk and are the least useful part to a maintainer who cannot run your repo.
- **Generalise every name** — repo, host, service, customer, branch, internal tool.
- 30–60 lines. If it is longer, you are pasting the report rather than extracting from it.
- **Never post it yourself.** No `gh issue create`, no API call, no browser. Print it and
  stop. The gap between "I generalised it" and "a human confirmed it is safe to publish" is
  where a leak lives, and a public issue is indexed and cached before anyone notices.

**Write the extract to `FIELD-REPORT-<PROJECT>-<DATE>-EXTRACT.local.md`** — also gitignored by
the same `*.local.md` rule — so the operator can read the exact bytes before anything is sent,
and so the submit command can reference a file rather than a paste buffer.

Then print both paths and stop:

    Read it first:  FIELD-REPORT-<PROJECT>-<DATE>-EXTRACT.local.md
    Submit it:      gh issue create --repo martinholovsky/SOTA-skills \
                      --title "[field-report] <one line>" \
                      --body-file FIELD-REPORT-<PROJECT>-<DATE>-EXTRACT.local.md \
                      --label field-report
    No gh?          https://github.com/martinholovsky/SOTA-skills/issues/new?template=3-field-report.yml

**Do not run that command.** Print it. The operator reads the file, then runs it if they are
satisfied there is nothing private in it.

**Only if the operator says they want to submit**, and only then, two best-effort checks —
both silent on failure, neither blocking:

- **Version delta.** If the library's git repo is reachable locally, compare the installed
  VERSION against the newest tag and add one line to the extract: *"reported against 1.38.2;
  latest at time of filing 1.41.2"*. Never fetch on the report itself — this library makes no
  network request unless a human asked for one.
- **Duplicate search.** `gh issue list --repo martinholovsky/SOTA-skills --search "<key
  phrase>" --state all --limit 5`. If something matches, show it and ask whether to comment on
  that issue instead of opening a new one.

If anything in the finding is **security-sensitive** — insecure guidance, an understated
severity, a real credential — say so and point at the private advisory form instead of the
issue tracker: https://github.com/martinholovsky/SOTA-skills/security/advisories/new

## Finally

If nothing failed this session, say that instead of inventing material — a clean session is
data too, particularly about which parts of the library are load-bearing under real work.

$ARGUMENTS
