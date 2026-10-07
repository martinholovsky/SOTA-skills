# Pre-registration — /sota-audit old vs new, Harbor v2.5.1 (written 2026-10-06, before any arm ran)

## Question
Does the rewritten `/sota-audit` (PR #501, `abb4f80`, "B") find classes the old text
(`53901d9`, "A") structurally did not ask for, without losing what A found?

## Subject
goharbor/harbor v2.5.1, `b0506782b4` (same as the 2026-08-13 run), `.git` stripped.
Four identical copies `ws/w1..w4` (8,382 files each). Arm type encoded in no path.
Assignment: **w1 = A, w2 = B, w3 = B, w4 = A** (n = 2 per arm).

## Inputs (sha256 prefixes)
- cmd-A.md `0102ad9f1d0f36bb` (2,323 words) · cmd-B.md `875173e80f1471b9` (3,893 words)
- authz ground truth: `evals/cases/harbor-authz-groundtruth.json` `52f0f4d1b88bb130` (16 sites)
- dependency ground truth: `dep-groundtruth.json` `5739acc4c7c91fe2` — trivy 0.72.0 over
  `src/go.mod`: 19 module@versions with >= 1 CRITICAL/HIGH advisory (128 rows, 127 IDs).
  govulncheck could not run (generated swagger models absent, packages fail to load).

## Arm prompt
The command text verbatim, `$ARGUMENTS` replaced by one identical block: scope =
`src/server` + `src/controller` (non-test) + `src/go.mod`; no git history (git steps
reported not reached); operator unavailable (record questions + default, continue);
no fixes; no network except an installed scanner fetching its own DB; no installs;
report to `ws/wN-report.md`, last line `DONE`.

## Scores (computed only after each arm's completion notification; final file only)
1. **Authz recall /16** — the 2026-08-13 rule: a site counts when the report names the
   function, or the file with a line inside it, and describes a missing object/tenant
   ownership check.
2. **Dependency recall /19** — a module counts when the report names it (module path) as
   carrying a known vulnerability / CVE / advisory. Version not required.
3. **Process (from executed commands in the transcript, not narrative)**, each 0/1:
   P1 ran a secrets scanner · P2 secrets scanner with redaction · P3 ran an SCA/dependency
   scanner · P4 ran a SAST tool · P5 report has a boundary/entry-point table
   (entry → authz check → asset) · P6 report has a coverage table at rules-file granularity ·
   P7 every Critical/High finding carries reproduction steps or a read path.
4. **Contamination probe** — any of `requirePolicyAccess`, `requireExecutionInProject`,
   `requireRuleAccess`, `requirePolicyInProject` in the transcript or report voids the arm
   for recall. Also counted: curl/wget/git clone/WebFetch/WebSearch calls; reads of this
   PREREG file.

## Predictions
- H1 authz recall: **parity** (A ≈ B, both ~15/16 as on 2026-08-13).
- H2 dependency recall: **B > A**. A has no instruction to scan; predicted A ≤ 3/19, B ≥ 10/19
  (B runs trivy, which is installed).
- H3 process: **B ≥ A on P1–P7**; A predicted to score P1–P4 near 0.
- Falsifier: H2 is refuted if A's mean dependency recall >= B's.

## Stated limits
n = 2 per arm, direction only. No git history → "secrets in history" and "diff dependents"
untestable here. Dependency truth is today's advisory DB, not 2022's. Arms run in this
Claude Code session (zero API spend), same model for all four.

## Deviations (appended, never rewritten)

**D1 — 2026-10-06, after w4 (arm A) finished, before any B arm was scored.** Two scorer bugs
found and fixed, each confirmed on a known-answer fixture before use: (a) a ±2-line window
credited a module named near an unrelated advisory line — credit now needs module and
vulnerability wording on the same line; (b) P1-P4 matched a tool name anywhere in a command,
crediting `gitleaks` inside a `grep -nE '…|gitleaks|…'` pattern — now the tool must be in
command position, quoted strings ignored, version-only invocations excluded.
**Dependency rule made explicit.** "Names it (module path)" was ambiguous: w4 wrote
`golang-jwt/jwt/v4` and `beego` (no host). Both rules are reported for every arm:
*strict* = full module path on a vulnerability line; *lenient* = full path, the path without
its host, or the last path element (last two when the last is a major-version suffix like
`v4`), on a vulnerability line (CVE/GHSA/GO-id/vulnerab/advisor). H2 is judged on lenient;
strict is reported beside it.
