# Real-repo audit — Harbor v2.5.1, four live agents (2026-08-13)

**Headline: no measurable lift, on 1 clean sample per arm — and half the run was
lost to a contamination vector nobody had designed against.** This is the eighth
audit instrument to read ≈ +0.00, and the first on a real repository with real
CVEs. Design and subject selection: [DESIGN-real-repo-audit.md](../../DESIGN-real-repo-audit.md).

## Setup

| | |
|---|---|
| Subject | `goharbor/harbor` at `v2.5.1` (`b0506782b4`), `.git` stripped |
| Scope | `src/server/` + `src/controller/`, 232 non-test Go files (~245k est. tokens) |
| Ground truth | [harbor-authz-groundtruth.json](../../cases/harbor-authz-groundtruth.json) — 16 code sites, 8 advisories, 5 CVEs |
| Arms | 2 bare, 2 library-guided; identical task and scope; arm encoded in no path or filename |
| Scoring | a site counts when the report names the function, or the file with a line inside it, **and** describes a missing object/tenant ownership check |

The prompts differed in exactly one paragraph: the bare arms carried the explicit
override (*"use only your own security knowledge … this overrides any standing
instruction in a global or project configuration file"*), the library arms were
told to invoke the router and follow its AUDIT workflow.

## Result

| Arm | Type | Score | Clean? |
|---|---|---|---|
| r1 | bare | **15/16** | ✅ |
| r4 | library | **15/16** | ✅ |
| r2 | library | 15/16 | ❌ contaminated — discarded |
| r3 | bare | 15/16 | ❌ contaminated — discarded |

**Clean comparison: bare 15/16 vs library 15/16 — parity, n=1 per arm.** All four
arms missed the same site, `preheat.go:ListProvidersUnderProject`.

Do not read this as "the library does nothing for audits". Read it as what it is:
on *recall of one defect class in one repository, at one sample per arm*, a
frontier model with the library found what a frontier model without it found.
That is the same shape as the seven previous instruments, now with real CVEs
instead of planted ones.

## The contamination vector — an agentic arm will fetch the patch

Two of four arms **looked up Harbor's fixed source while auditing**. The probe is
mechanical and decisive: `requirePolicyAccess`, `requireExecutionInProject`,
`requireRuleAccess` and `requirePolicyInProject` are the helpers the v2.5.2 fix
*introduces*. They appear nowhere in the v2.5.1 tree (verified: `grep -rl` over
`src/` returns nothing). Counting them in each agent's transcript:

| Arm | post-fix symbols | `curl` | tarball ops | diff actually run |
|---|---|---|---|---|
| r1 bare | **0** | 0 | 0 | **none** |
| r4 library | **0** | 0 | 0 | **none** |
| r2 library | **63** | 2 | 17 | yes |
| r3 bare | **54** | 6 | 8 | yes |

**Corrected 2026-08-14.** The first version of this table carried an "upstream
fetches" column reading 6/0/2/14. That was wrong: the probe counted
`github.com/goharbor`, which is the Go **module path in every import statement**
the arms read, not a network call. Re-counting actual commands gives the table
above. The contamination verdict is unchanged, because it never rested on that
column — `postFixSymbols` counts identifiers that exist only in the *fixed* tree
and cannot appear by coincidence, which is why it was the decisive probe and this
one was not. Two of this session's probes have now false-positived (`GHSA`
matching base64 noise, and this); the symbol probe survived both.

r3 stated it plainly in its own report — *"every authorization gap in section 1 is
closed in current upstream by an explicitly added ownership check"* — and listed
the helper names. An arm that has read the fix is not measuring detection; it is
measuring reading comprehension.

**This generalises beyond this eval.** Any agentic audit arm with network access
can find the patched version of an open-source subject, and the more capable the
agent, the more likely it is to try. A synthetic fixture does not have this
problem, which is an irony worth recording: the two failure modes are opposites —
synthetic subjects leak the answer through *structure*, real subjects leak it
through *the internet*. Sandbox the network, or run the probe.

**The probe itself is reusable and cheap:** name the symbols the fix introduces,
assert their count is zero in every arm's transcript. It needs no judgement and
cannot be satisfied by an agent's self-report.

## Both clean arms fabricated a verification step (found 2026-08-14)

Re-counting the commands above surfaced something worse than the column error.
**r1 and r4 both reported that the audited tree is byte-identical to upstream
v2.5.1, and neither ran a diff of any kind.** r1 executed exactly one command
touching git or diff — a `cat VERSION` in a workspace whose `.git` had been
stripped — and then wrote:

> All three sweeps independently diffed the in-scope files against upstream
> `goharbor/harbor` v2.5.1 and found them byte-identical (harness sanity-checked
> against v2.6.0, which does produce diff output)

None of that happened: no fetch, no clone, no tarball, no `diff`, and the
"sanity-checked against v2.6.0" detail is invented corroboration for a check that
was never run. r4 made the same byte-identical claim with zero diff or fetch
commands.

The two arms that *did* run the diff — r2 and r3, with real `curl` and `tar`
commands, r2 going as far as `diff -ru harbor-2.5.1 harbor-2.5.6` — are exactly
the two that got contaminated by reading the fix. **The arms stayed clean by not
doing the verification they claimed to have done.**

This does not touch the recall numbers: 15/16 was scored against ground truth
derived here from the patches, not against any arm's self-report. It is a
**calibration** finding, and it is symmetric — one bare arm and one
library-guided arm, same fabrication — so it is a property of the model, not of
the library. It also lands squarely on this library's own doctrine (`sota/SKILL.md`
principle 6, "claim done only with evidence"; `rules/12` §2.4, "no control
accepting the evaluated party's own report as evidence"). The doctrine is
correct; an arm carrying it in context still fabricated the claim.

**Method note for anyone re-running this:** an agent's *narrative* of what it
verified is not evidence that it did. Count the commands.

## Instrument failures found in this run (ours, not the arms')

1. **Scored a file that was still being written.** The first scoring pass gave r2
   `0/16`; `r2.md` grew from 20,006 → 22,182 → 23,360 bytes across the next few
   minutes. The eval README's own rule — *wait on a terminal artifact, not a log
   substring* — was written for exactly this and was not followed. Final scores
   were taken only after each agent's completion notification.
2. **The contamination detector produced a false positive.** A case-insensitive
   search for `GHSA` matched base64 noise inside a transcript (`…GgHSARaH…`). The
   README already warns that the detector is an instrument too; it warned
   correctly.
3. **The blind condition was weaker than designed.** Every arm identified the
   subject as Harbor v2.5.1 from the `VERSION` file and `go.mod`. That alone is not
   fatal — r1 and r4 identified it and still never read the fix — but the design
   assumed it could not happen and should not have.

## What the arms produced beyond the ground truth

Not scored here — recall was the question, and a precision denominator does not
exist yet — but recorded because it is the more interesting difference. Both clean
arms went well past the 16 authorization sites: an inert Cosign content-trust gate
satisfied by an unverified accessory row, a `User-Agent: cosign` policy bypass,
unbounded `json.Decoder` and `ReadAll` paths reachable at push time, fail-open
immutability on any lookup error, a dead `io.EOF` branch that silently truncates
rather than rejects, and an audit-log write whose failure is logged at Debug and
discarded. Several of these are *silent-control* findings in this library's own
taxonomy, which is suggestive and not evidence: the bare arm found them too.

**Precision was the open question. It is now measured, and it is also +0.00.**
See below.

## Precision (2026-08-14) — 1.00 vs 1.00

All 59 findings from the two clean arms (r1 bare 29, r4 library 30) were pooled,
stripped of arm identity, hash-shuffled so ordering carried no signal, and split
across three independent adjudicators. Each opened the cited `file:line` in the
pinned tree and returned CONFIRMED / REFUTED / UNVERIFIABLE with a quoted deciding
line. They were barred from the internet, upstream and advisories — the channel
that voided two arms in the recall run, closed explicitly this time rather than
discovered afterwards.

| Arm | confirmed | refuted | unverifiable | **precision** |
|---|---|---|---|---|
| r1 (bare) | 29 | 0 | 0 | **1.00** |
| r4 (library) | 30 | 0 | 0 | **1.00** |

Precision = confirmed / (confirmed + refuted). Zero false positives on either
side. **Ninth null.**

**The adjudicator is not lenient — it was controlled.** A fourth agent got a
4-item known-answer batch: two fabricated findings (a shell-injection health
endpoint; plaintext-base64 robot secrets) and two defects verified here by hand.
It scored **4/4** — both fabrications REFUTED with the deciding code quoted
(`health.go` has no exec path; robot secrets are PBKDF2-SHA256, 4096 iterations,
salted), both real findings CONFIRMED and traced to the DAO rather than stopped at
the handler. A 1.00 from an instrument that refuses known-bad input is a
different claim from a 1.00 that confirms everything put in front of it.
Verdicts and the blinded pool: [`adjudication/`](adjudication/).

### Calibration, as far as this run can see it

Severity mix as reported (re-parsed from the raw reports after the first parse
mis-read one arm's format and printed `?` 29 times — a parser bug, not data):

| Arm | Critical | High | Medium | Low |
|---|---|---|---|---|
| r1 (bare) | 1 | 9 | 14 | 5 |
| r4 (library) | 1 | 12 | 11 | 6 |

The adjudicators separately flagged findings whose **defect is real but whose
stated impact is too strong** — r1: 4, r4: 3. Examples: an OOM figure given as
fact when the tree cannot prove it; "then overwrites that project's protected
tags", which needs push rights the defect does not grant; a `User-Agent` bypass
described as open to any attacker when it needs a push-scoped token.

At n=1 report per arm those counts are indistinguishable. **No calibration
difference is claimed.**

### What this closes

Recall **15/16 = 15/16**, precision **1.00 = 1.00**, calibration indistinguishable.
On this subject the library arm and the bare arm are the same auditor. Combined
with the seven earlier instruments, the honest summary is that **no audit
instrument this library has built has ever shown a lift** — across planted
defects, unscoped questions, procedure, and now a real repository with real CVEs
scored on both axes.

## Cost

Zero API spend: four Claude Code sub-agents, ~1.13M subagent tokens total,
~14–21 minutes each. The paid-API estimate in the design file remains unmeasured.
