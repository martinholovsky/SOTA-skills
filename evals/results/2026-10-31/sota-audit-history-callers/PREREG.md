# Pre-registration — `/sota-audit` on a diff with real history: secrets in history, a caller-held defect (ROADMAP 70)

Written 2026-10-31, before either arm ran. Frozen by the commit that adds this file; anything
learned later goes under **Deviations**, appended, never rewritten.

## Question

The command text has two steps that the 2026-10-06 A/B could not exercise, because its subject
had no `.git`: scan the **full git history** for secrets, and, for a **diff** scope, read the
diff's **callers and importers**, which are part of the scope. Given a diff scope on a repository
whose history is intact, does the current `/sota-audit`:

1. find a secret that was committed and later removed, so it exists only in history; and
2. find a defect that lives in a **caller** of the changed function, outside the diff?

## Subject

`asterinas/asterinas`, history up to `b563fb639fb08749b20daaaf9afdf3e103fcbdfb` only
(1,667 commits), then three commits on a local `main`:

| commit | content |
|---|---|
| `499003f3` "Add CI deploy settings" | a **fake** GitHub token (`github-pat` shape) in `tools/deploy/ci.env`; random, never valid, never pushed; its value appears nowhere here (sha256 prefix `ccea9f25d87b0fda`) |
| `e35bb96f` "Remove CI deploy settings" | deletes that file — **BASE** |
| `20e56ec7` "Make `pause_timeout` return `EINTR`" | upstream `6421fd0b3` (2024-11-05), cherry-picked unchanged — **HEAD** |

Diff scope: `git diff e35bb96f...HEAD` = one file, `kernel/src/process/signal/pause.rs`. No remote;
upstream's later revert (`0c114e911`) and reapply (`2411ba671`) are absent from the object store
(checked with `git cat-file -e`). Built by a script that never prints the token.

Positive control, run 2026-10-31 before this file was written: `gitleaks git --redact` (8.30.1)
over all 1,670 commits reports **exactly one** finding, `github-pat` in `tools/deploy/ci.env` at
`499003f3` line 3; `gitleaks dir` over the working tree reports none. The secret is detectable,
and only by scanning history.

Arm workspaces: two `cp -R` copies, `eval-r70-ws/w1` and `w2` (HEAD `20e56ec7`, clean tree,
1,317 tracked files each), in a directory that holds no truth file.

## Ground truth

**T1 — the secret.** The GitHub token committed in `499003f3` and removed in `e35bb96f`.

**T2 — the caller-held defect.** The diff changes `Pause::pause_timeout`'s contract: it now returns
`EINTR` whenever the thread has a pending signal after the wait, **even when the wait ended
because the condition was met** (a futex wake). At HEAD it has exactly one caller,
`futex_wait_bitset` in `kernel/src/process/posix_thread/futex.rs`, which returns that result
unchanged to userspace. So a futex that is woken while a signal arrives fails with `EINTR`
although the wake happened. Upstream evidence: the change was reverted four days later
(`0c114e911`), and the reapply (`2411ba671`, 2025-02-20) added caller-side handling in
`futex.rs` whose own comment marks it FIXME and links asterinas PR #1577. The defect is in a file
the diff does not touch.

## Arms

n = 2, **both on the current command text**: `commands/sota-audit.md` at `b10feffc`, sha256 prefix
`72d93d5d9ff6e6f8`, 4,188 words. Each arm is a fresh subagent in this Claude Code session (zero API
spend, the session's model), started with the command text verbatim, `$ARGUMENTS` replaced by one
identical block:

- the repository is the workspace path; scope is **the diff `e35bb96f...HEAD`** (BASE given as
  that SHA);
- the operator is unavailable: record each question with the default taken, and continue;
- no fixes; no network (no fetch, clone, curl, web search or web fetch) except a scanner already
  installed fetching its own rule or advisory database; no installs;
- **do not build or run the target** (no `cargo` build, test, clippy or any build script);
- write the report to `report.md` in the workspace; last line `DONE`.

## Scores

Computed by `score.py` (committed with this file) only after an arm's completion notification,
from its final `report.md` and its transcript plus every nested transcript it spawned.

- **S1 (T1 found), 0/1:** a report paragraph names the planted credential: `tools/deploy/ci.env`,
  commit `499003f3`, or "CI deploy settings", together with token/secret/credential wording.
- **S2 lenient (T2 located), 0/1:** a report paragraph names `futex_wait_bitset` or `futex.rs`
  together with `EINTR` or `pause_timeout`.
- **S2 strict (T2 explained), 0/1:** S2 lenient, and the same paragraph says the `EINTR` comes
  although the wait was woken or satisfied, i.e. a wake racing a signal.
- **Process, from executed commands, not narrative, counted across the arm's transcript and every
  nested one (the command text tells the auditor to partition the work across agents, so a scan a
  partition agent ran counts), each 0/1:** P1 ran a secrets scanner over git
  history (`gitleaks git`, or `gitleaks detect` without `--no-git`, or `trufflehog git`); P2
  searched the tree for callers of `pause_timeout`; P3 checked
  `git rev-parse --is-shallow-repository`.
- **Contamination probe:** any of `#1577`, `pull/1577`, `gvisor`, `Reapply`, `0c114e9`,
  `2411ba6`, `7a017faa` in a transcript or the report **voids S2** for that arm. Any read of a
  path under `/Volumes/speedy/Github/asterinas`, `asterinas-audit`, `eval-r70/` (the truth
  directory: `planted-token`, `control-gitleaks`), or this file **voids the arm**. Network tool
  calls (`curl`, `wget`, `git fetch`, `git clone`, `WebFetch`, `WebSearch`) are counted; one
  that could reach upstream history voids S2.

## Predictions

- **H1:** S1 = 1 in **both** arms. The command explicitly requires a full-history secrets scan
  and checks for a shallow clone, and gitleaks is installed. **Falsifier:** S1 = 0 in both arms,
  i.e. the step does not run or does not report in practice.
- **H2:** S2 lenient = 1 in **at least one** arm. The command puts callers in the diff scope,
  and `pause_timeout` has exactly one, a single search away. **Falsifier:** S2 lenient = 0 in both.
- **H3:** S2 strict is the hard half; predicted 0 or 1 of 2, with no falsifier claimed. Locating
  the caller is what the command asks for; seeing the wake-versus-signal race takes reasoning
  about `futex` semantics the command does not prompt.

## Stated limits

- n = 2 and one defect of each kind: direction, not a rate.
- The subject is public and was audited in this session at a much later commit (findings held
  privately); the arms are fresh subagents with no access to that context, but the model may know
  asterinas or PR #1577 from training. The contamination probe catches only what is written down.
- The planted secret is real-shaped but synthetic; the caller-held defect is real.
- **Publication:** arm reports are **not** committed verbatim. They audit kernel code and could
  restate defects that are still unfixed upstream (see ROADMAP 70's 2026-10-30 note). Only the
  scores, the process flags, the probe results and the exact report paragraphs that earned S1/S2
  are published; full reports stay local in `eval-r70-ws/`.

## Deviations (appended, never rewritten)
