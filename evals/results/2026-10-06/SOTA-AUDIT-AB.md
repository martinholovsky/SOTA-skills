# `/sota-audit` old vs new — Harbor v2.5.1, four live agents (2026-10-06)

**Headline: the rewrite (#501) changed how the audit is run, reliably, and did not change what
it reports about dependencies.** Both new-text arms ran a redacted secrets scan, built the
trust-boundary map and kept coverage per rules file; neither old-text arm did any of the three.
Authorization recall is at parity (15, 15 vs 15, 13 of 16). The one pre-registered *directional*
prediction — that the new text finds more vulnerable dependencies — is **refuted**: old 5.5, new
3.0 of 19 (lenient rule). Every arm ran trivy and saw the same 128 advisories; every arm then
reported them as a count plus a few examples. The new text says to run the scanner; it does not
say to report each Critical/High advisory as a finding, and that is the step that was missing.
Follow-up: ROADMAP item 67. **Followed up 2026-10-07:** with that rule added, dependency recall went to 19, 19 of 19 ([SOTA-AUDIT-AB-C](../2026-10-07/SOTA-AUDIT-AB-C.md)).

Pre-registration, frozen before any arm ran: [sota-audit-ab/PREREG.md](sota-audit-ab/PREREG.md)
(sha256 of the frozen part `9aa6fe5c1c5fcab4`; one dated deviation appended, D1, below).

## Setup

| | |
|---|---|
| Subject | `goharbor/harbor` at `v2.5.1` (`b0506782b4`) — the 2026-08-13 subject — `.git` stripped, four identical copies |
| Scope | `src/server` + `src/controller` (232 non-test Go files) + `src/go.mod` |
| Arms | **A** = `/sota-audit` at `53901d9` (2,323 words): w1, w4 · **B** = at `abb4f80` (3,893 words): w2, w3 |
| Prompt | the command text verbatim; `$ARGUMENTS` replaced by one identical block (scope agreed, no git history, operator unavailable — record questions and continue, no fixes, no network except a scanner's own DB, no installs) |
| Runner | Claude Code background agents in one session, same model, zero API spend |
| Authz truth | [harbor-authz-groundtruth.json](../../cases/harbor-authz-groundtruth.json) — 16 sites; credit = function named or a line inside it, **and** a missing ownership check described |
| Dependency truth | [sota-audit-ab/dep-groundtruth.json](sota-audit-ab/dep-groundtruth.json) — trivy 0.72.0 over `go.mod`: 19 module@versions with ≥ 1 Critical/High advisory (128 rows, 127 IDs). govulncheck could not build the tree (generated swagger models absent) |
| Scorers | [score.py](sota-audit-ab/score.py) (dependency recall, P1–P4 from executed commands, contamination) and [authz.py](sota-audit-ab/authz.py) (location → function span); every judgement half read by hand |

## Result

| | A — w1 | A — w4 | B — w2 | B — w3 |
|---|---|---|---|---|
| Clean (0 fix symbols, 0 network, 0 cross-arm reads) | yes¹ | yes | yes | yes¹ |
| **Authz recall /16** | 15 | 13 | 15 | 15 |
| **Dependency recall /19**, lenient (strict) | 6 (0) | 5 (0) | 2 (0) | 4 (0) |
| P1 secrets scanner ran · P2 with redaction | 0 · 0¹ | 0 · 0 | 1 · 1 | 1 · 1 |
| P3 SCA ran · P4 SAST ran | 1 · 1 | 1 · 1 | 1 · 1 | 1 · 1 |
| P5 boundary map (entry → authz check → asset) | 0 | 0 | 1 | 1 |
| P6 coverage table per rules file | 0 | 0 | 1 | 1 |
| P7 reproduction / read path on every High | 0 | 0 | 1 | 0 (4 of 7) |
| tool calls · minutes · subagent tokens | 53 (+4 agents) · 28.0 · 259k | 77 · 16.1 · 238k | 120 · 24.2 · 355k | 87 (+1 agent) · 19.7 · 307k |

¹ w1 launched three partition agents and a refuter, w3 a refuter. Their transcripts are not in
the arm's file, so the contamination probe and P1–P4 see the top-level agent only. Both reports
are clean of every fix-only symbol.

Every arm missed the same authz site, `preheat.go:ListProvidersUnderProject` — the site all four
arms missed on 2026-08-13. w4's other two misses: `UpdatePolicy`, `updateV2Robot`.

## Addendum 2026-10-07 — nested agents probed (supersedes footnote ¹)

The limit above was closed after the fact. `score.py` now takes an arm's nested transcripts as
extra arguments: the `subagents/agent-<id>.jsonl` files whose `.meta.json` names the arm in
`parentAgentId`. Contamination reads all of them; P1–P4 stay top-level only, as pre-registered.
Positive control: passing PREREG.md as a fake nested transcript counted all four symbols.

| arm | nested agents read | fix-only symbols | network / cross-arm / PREREG reads |
|---|---|---|---|
| w1 | 4 (partitions A, B, C, refuter) | **`requirePolicyAccess` × 2, both in partition B** | 0 |
| w3 | 1 (refuter) | 0 | 0 |

**The w1 hit is ambiguous, and it is recorded rather than resolved.** Partition B typed the
symbol once, as one of about twenty guessed guard names in an awk/grep alternation, beside
`requireRetention` and `requireNotificationPolicy`. The symbol is absent from v2.5.1, so the
search matched nothing, and it appears in no report. That is consistent with recalling the fixed
Harbor code, and also with guessing names. Read literally, PREREG item 4 ("in the transcript …
voids the arm for recall") voids w1. **With w1 voided, no conclusion changes:**
- **H1:** A authz is 13/16 (n = 1, w4) against B's 15, still not claimed as a lift.
- **H2:** stays refuted, since A's 5 ≥ B's 3.0.
- **ROADMAP 67's C arms:** their 19/19 never compared against w1 alone.

## Against the predictions

- **H1 — authz parity: held.** Means 14.0 (A) vs 15.0 (B); the gap is one sample (w4's 13).
  Not claimed as a lift.
- **H2 — B > A on dependency recall: refuted** by its own pre-registered falsifier (A 5.5 ≥ B 3.0).
  Both halves of the forecast were wrong: A was predicted ≤ 3/19 and ran trivy unprompted in
  both arms; B was predicted ≥ 10/19 and reported a count instead of rows. Strict recall (full
  module path) is 0 in every arm: no report wrote `github.com/…`.
- **H3 — B ≥ A on process: held, with the prediction partly wrong.** A was predicted near zero
  on P1–P4 and scored 2/2 on P3 and P4 — a frontier agent runs an SCA and a SAST tool without
  being told. What the new text added is what the model does *not* do on its own: a secrets
  scan, with redaction (2/2 vs 0/2), the boundary map (2/2 vs 0/2), per-rules-file coverage
  (2/2 vs 0/2) and, in one arm, a reproduction for every High.

## What it means

The rewrite is doing what a procedure can do — making the expensive-to-skip steps happen — and
on this subject it cost nothing in authz recall. It does not yet turn scanner output into
findings. The fix is one sentence in step 4: every Critical/High advisory becomes its own
finding, by module@version, with the reachability that was checked. That is **ROADMAP 67**,
and the measurement to close it is this run again on that text.

## Deviation D1 (recorded before any B arm was scored)

Four instrument defects, each confirmed on a known-answer fixture before it was trusted:
1. the dependency matcher credited a module named within two lines of an unrelated advisory;
2. P1–P4 credited a tool named inside a `grep` pattern (`gitleaks` in a CI-config search gave
   w4 a false P1) — now command position only, quoted strings and version checks ignored;
3. "names it (module path)" was ambiguous once w4 wrote `jwt/v4` and `beego` — both a strict and
   a lenient rule are reported, H2 judged on lenient;
4. the authz matcher missed continuation references (`` `:143` `` after a named file): w4 read
   10/16 before the fix and 13/16 after, the extra three read by hand as ownership findings.

## Limits

- n = 2 per arm: direction, not significance.
- No git history: "secrets in history" and "a diff's callers" — two of the classes #501 added —
  were untestable on this subject.
- Nested agents (w1, w3) were not probed for contamination or scanner runs.
- osv-scanner sat in `~/go/bin`, off PATH; the pre-run inventory checked PATH only and missed
  it. All arms had the same access; w3 found and used it.
- Dependency truth is today's advisory database, not what was known at the v2.5.1 release.
- The arms' reports are committed as produced, with one redaction: the stack profile's file
  name is replaced by `<owner>.md`.

## Files

[PREREG.md](sota-audit-ab/PREREG.md) · [arm-w1.md](sota-audit-ab/arm-w1.md) ·
[arm-w2.md](sota-audit-ab/arm-w2.md) · [arm-w3.md](sota-audit-ab/arm-w3.md) ·
[arm-w4.md](sota-audit-ab/arm-w4.md) · [score.py](sota-audit-ab/score.py) ·
[authz.py](sota-audit-ab/authz.py) · [dep-groundtruth.json](sota-audit-ab/dep-groundtruth.json)

## Cost

Zero API spend: four Claude Code agents, 1.16M subagent tokens in total (238k–355k each, excluding
their own nested agents), 16–28 minutes each.
