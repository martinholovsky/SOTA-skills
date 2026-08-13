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

| Arm | post-fix symbols | upstream fetches |
|---|---|---|
| r1 bare | **0** | 6 (v2.5.1 comparison only) |
| r4 library | **0** | 0 |
| r2 library | **63** | 2 |
| r3 bare | **54** | 14 |

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

Whether the library changes **precision, calibration or report structure** rather
than recall remains the open question — as it has since 2026-07-30. Nothing here
moves it.

## Cost

Zero API spend: four Claude Code sub-agents, ~1.13M subagent tokens total,
~14–21 minutes each. The paid-API estimate in the design file remains unmeasured.
