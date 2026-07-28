# Verifying a repo's setup — the read-only check

`scripts/init-gates.sh` and `scripts/gen-agents-md.sh` **set things up**.
Nothing checks the result. This is that check: a prompt you paste into a coding
agent that reports whether the library, this repo's own context, and its gates
are actually in place — and changes nothing.

It exists because "configured" and "working" are different states that render
identically. A `.pre-commit-config.yaml` with no installed hook is a file, not a
control. A CI workflow whose every run is *skipped* is a gate on paper. An
`AGENTS.md` whose commands all resolve can still assert a toolchain seven months
stale. Each of those passes an existence check and fails the job.

## When to run it

- On a repo you just scaffolded, before trusting the scaffolding.
- On a repo you inherited, before assuming its green CI means anything.
- Periodically on your own, because agent files decay
  ([`sota-docs-workflow` rules/01](../skills/sota-docs-workflow/rules/01-documentation-architecture.md) §7).

## The prompt

Paste this verbatim.

```text
SOTA setup verification — READ-ONLY. Do not build, scaffold, install, or fix
anything. Do not create, modify, or delete a single file. If a check fails, say
so and move on; the output is a report, not a repair.

Verify by OBSERVATION, never inference. Run the command, read the file. Any
check you cannot actually run gets reported as UNVERIFIED with the reason —
never as a pass. Probe for capabilities, not for one implementation's name: a
check for `docker` misses podman, `LICENSE` misses `LICENSE-MPL`,
`.pre-commit-config.yaml` misses husky/lefthook/a CI job.

## A. Is the library reaching this directory?

1. List the sota-* skills you can actually load right now, and count them.
   Compare against `ls -d ~/.claude/skills/sota*/ | wc -l` (or the plugin's
   skills dir). PASS = the counts agree and the `sota` router is among them.
2. Always-on routing: does `~/.claude/CLAUDE.md` contain a sota routing
   directive, and does `~/.claude/settings.json` define a `UserPromptSubmit`
   hook whose command mentions sota? PASS = both. If only the CLAUDE.md
   directive exists, say so — routing then depends on the model reading it
   rather than on a per-prompt injection.
3. Stack profile: does `~/.claude/profiles/*.md` exist and resolve (not a
   dangling symlink)? Report the filename only, not its contents.

## B. Is this repo's own context in place?

4. Agent file: `AGENTS.md` and/or `CLAUDE.md`. PASS is not existence — it is
   CONTENT. Read it and state whether it carries (a) exact build/test/lint
   commands, (b) deviations from the language default, (c) traps. A file that
   only restates generic best practice, or that points at tooling a fresh
   contributor would not have, is a FAIL with the reason.
   If `CLAUDE.md` is a symlink, check it resolves; if it is a one-line pointer
   to `AGENTS.md`, that is fine and preferred.
5. Verify the agent file is TRUE, in two passes:
   5a. Every build/test/lint command it names exists (Makefile target, script in
       package.json, task in pyproject/justfile). Name the file:line of each.
   5b. Every factual CLAIM it makes is still accurate — pinned versions,
       toolchains, image tags, what a given target actually does. Open the file
       it describes and compare. This is where agent files rot: the command
       still exists, the claim about it went stale months ago, and nothing
       checks it.
6. Day-zero artifacts: a licence file (`LICENSE*`/`COPYING*`/`COPYRIGHT`),
   `.gitignore`, README. Report each present/absent.

## C. Are the gates real, or just configured?

7. Find every gate mechanism, not just one: `.pre-commit-config.yaml`, husky,
   lefthook, `.git/hooks/*` (non-sample), and CI workflows. For each, list what
   it actually runs.
8. Secret scanning specifically: is any gate running gitleaks/trufflehog/
   detect-secrets, at commit time or in CI? Confirm with a repo-wide search, not
   by assuming from a filename.
9. Are the gates INSTALLED, not merely configured? Check `.git/hooks/` for
   non-sample hooks and `core.hooksPath`. Distinguish three states: installed /
   configured-but-not-installed (a file, not a control) / nothing configured at
   all (N/A, not a failure).
10. For each gate, establish TWO things from observable history — use
    `gh run list --limit 60` (or the CI provider's equivalent) and read real
    conclusions:
    (a) Has it ever EXECUTED? A workflow whose runs are all "skipped" has a
        trigger condition that never fires — that is a control on paper only.
    (b) Has it ever REJECTED anything? A gate with only successes has never
        been observed doing its job.
    Mark each UNVERIFIED where history doesn't show it, and state your sample
    size — "not in the last 60 runs" is not "never".

## D. Routing dry-run (no code)

11. Without writing any code, state which sota-* skills and which specific
    rules files you WOULD load for: "add an authenticated file-upload endpoint
    backed by Postgres". List them, then stop. This tests that routing resolves;
    it is not permission to implement anything.

## E. Can the findings be acted on?

12. Report `git remote -v` and whether this repo is yours, a fork, or an
    upstream clone. A fix list you cannot land is a different deliverable from
    one you can.

## Output

A table: check | PASS / FAIL / PARTIAL / UNVERIFIED / N/A | evidence observed.
PARTIAL and N/A each require a one-line reason. UNVERIFIED must state what
prevented verification and your sample size where relevant.
Then a short ordered list of what to fix — described, not done — each marked
[local] or [upstream] per check 12.
Do not apply any fix. Do not offer to start building. End after the report.
```

## The one check it cannot do read-only

Proving the secret gate *rejects* something needs a real commit attempt. Run it
yourself — three lines, reversible:

```sh
printf 'aws_secret_access_key = "AKIAIOSFODNN7EXAMPLE"\n' > leak-test.txt
git add leak-test.txt && git commit -m "gate test"   # MUST be rejected
git reset -q && rm -f leak-test.txt
```

If that commit succeeds, check 8 was a false pass — you have a scanner in the
config and no control on the commit path.

## Reading the report

- **FAIL on check 5b with PASS on 5a** is the common and dangerous shape: the
  commands work, the claims lie. Fix by replacing the assertion with a link to
  the file that owns the fact.
- **All-skipped run history** is
  [`sota-code-security` rules/10](../skills/sota-code-security/rules/10-silent-control-failure.md)
  §2.13 — the trigger is the finding, not the gate's logic.
- **UNVERIFIED is not a soft PASS.** It means nobody has watched the thing work.
  Treat it as unknown, and say so when reporting upward.

## Provenance

Derived from two live runs against a real 4300-commit repository (2026-07-28).
The first run's own limitations produced checks 5b, 9's three-state
distinction, 10's execute/reject split, and 12 — each was a gap the run exposed
rather than something reasoned in advance. See
[ADOPTION-LOG.md](ADOPTION-LOG.md).
