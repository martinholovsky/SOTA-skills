# 06 — Ad-hoc commands: the ones you type to check something

Scope: the commands nobody commits — a sweep, a probe, a one-liner pasted from a
checklist, a quick container copy. They are unlinted, unreviewed, and run against the
system under test, so when they go wrong they produce a false finding **about the
product**, or damage the thing they were inspecting. Split out of `rules/01` at v1.38.0 —
its zsh, sweep and blast-radius sections became §1, §2 and §3 here. Quoting itself stays in
`rules/01` §3, which this file assumes you have read.

## 1. zsh is not bash — the deviations that bite *pasted* commands

Committed scripts are immune: every one carries a `#!/usr/bin/env bash` shebang, so bash
runs them whatever your login shell is. The exposure is **interactive, pasted, and
agent-issued commands** — including the audit checklists in this library, which are
written to be pasted, and **macOS's interactive shell is zsh**. Check the operator's shell
rather than assuming; then treat the table below as live.

| | bash | zsh | how it fails |
|---|---|---|---|
| unquoted `$var` with spaces **or newlines** — incl. any `$(…)` file list | splits into words | **joins** into one argument (`rules/01` §3) | **loudly** — a usage error, exit 2, from the callee — but a *file-list* command then searches **nothing**, and empty output reads as a clean tree |
| `$?` after a pipeline | last stage (`${PIPESTATUS[0]}` for the first) | same, but `${pipestatus[1]}` (`rules/01` §3) | **quietly** — a wrong status, read as truth |
| unquoted glob in a flag value | passed through **literally**, command runs | `NOMATCH` **aborts the command** | **silently** — and it fakes a clean result |

**The third is the dangerous one: a failed glob means the command never runs at all.**
zsh's `NOMATCH` is on by default, so a glob matching nothing is a hard error rather than a
literal word. Verified on zsh 5.9 / bash 5.3.15 / Darwin 25.6.0:

```zsh
grep -rn --include=*.md TODO .     # zsh: "no matches found: --include=*.md" — grep NEVER RAN
                                   # bash: works, because the word is passed through
grep -rn --include='*.md' TODO .   # correct in both
```

**Why it earns a rule of its own: with `2>/dev/null` it is byte-identical to a real
no-match.** That redirect is the standard idiom for hiding `Permission denied` noise in a
recursive search, and it also hides the one line that would have told you:

```zsh
out=$(grep -rn --include=*.md   hello . 2>/dev/null)   # BROKEN:  stdout empty, exit 1
out=$(grep -rn --include='*.md' ABSENT . 2>/dev/null)  # GENUINE: stdout empty, exit 1
```

Same stdout, same exit code. **An audit sweep written this way cannot distinguish "the
codebase is clean" from "my search never executed"** — a false-clean produced by the tool
these checklists are pasted into — `sota-code-security` rules/15's instrument
failure arriving through the shell.

Rules:

- **Quote every glob you intend the *callee* to interpret** — `--include`, `--exclude`,
  `find -name`, `rsync --filter`, and any flag taking a pattern as its value. This is the
  opposite of `rules/01` §3's advice for filenames: there you quote so *your* shell does not split;
  here you quote so your shell does not *expand* at all.
- **`setopt nonomatch` is the wrong fix.** It changes global shell behaviour to hide a
  quoting bug and would mask genuine typos in real filename globs.
- **Positive-control any sweep whose output you will read as an absence** (rules/04): run
  it once against a pattern you know is present, and see the hit. A sweep that has never
  been shown capable of producing a hit is not evidence of a clean tree — the same
  known-good/known-bad discipline `sota-code-security` rules/11 §7 asks of any instrument.
- Do not rely on the exit status reaching you. Measured: whether the *rest* of the command
  list still runs depends on the failing command — `grep --include=*.md x . ; echo hi`
  prints `hi`, while the same glob passed to a **builtin** (`echo`, `true`) aborts the
  whole list, so the follow-up never runs either. Either way the intended command did not.

## 2. The sweep that never ran, part two: `grep -r` and symlinked directories

§1 is about a *quoting* bug stopping the command. This is the command running fine and
**traversing less than you think**. Measured on ugrep 7.8.4 / macOS, and it is POSIX
behaviour rather than a quirk:

| form | a symlinked dir **given as the argument** | a symlinked dir **met during traversal** |
|---|---|---|
| `grep -r` | followed | **skipped, silently** |
| `grep -R` | followed | followed |

```text
tree/direct.md:NEEDLE          # grep -r  — found 1 of 2
tree/sub/linked/hidden.md:…    # grep -R  — found 2 of 2
```

So **`grep -r` over any tree that may contain symlinked directories under-reports, and the
under-report is an empty or short result that reads as a clean answer.** It bites hardest
where the tree is *made* of links: a skills or plugin directory installed by symlink, a
monorepo with linked packages, `node_modules` with workspace links, a dotfiles checkout.
Use `-R` when you mean "follow", and say which you used when you report a count.

**Control the search in the SAME invocation.** §1 says to positive-control a sweep; the
sharpening is *where*. A control run separately is a different command against a possibly
different tree, and it is the one people skip when the result looks plausible. Put a term
you know is present into the same run and read both numbers:

```bash
files=("${(@f)$(git ls-files '*.md')}")            # zsh; see `rules/01` §3
printf 'control=%s  hits=%s\n' \
  "$(grep -lF 'KNOWN_PRESENT' $files | wc -l)" "$(grep -lF "$TERM" $files | wc -l)"
```

A control of **0** means the sweep is broken and the `hits=0` beside it means nothing. This
is `sota-code-security` rules/15 §2.2's known-good, at one-liner scale.

**Every searcher has silent-exclusion defaults, and they differ — so the fix is naming them,
not switching tool.** Measured on one tree holding four matches (plain, hidden, gitignored,
behind a symlinked dir):

| searcher | found | what it dropped, silently |
|---|---|---|
| `rg` (defaults) | **1 of 4** | gitignored, hidden, and symlinked-dir contents |
| `grep -R` (see below) | 3 of 4 | the gitignored file |
| `rg --hidden --no-ignore --follow` | **4 of 4** | — |

**And check what your `grep` actually is** (`type grep`): agent and IDE environments
routinely alias it. In one measured case it was a shell *function* running `ugrep -G
--ignore-files --hidden -I --exclude-dir=.git …` — so it honoured `.gitignore` (which GNU
grep does not) and skipped binaries, neither of which appears in any manual the reader would
consult. **An absence measured through an unexamined wrapper is not an absence.**

**Two tools can answer to the same name.** Measured in one agent environment: `grep` was a
shell *function* running **ugrep 7.8.4**, except that any `-z`/`-Z` argument was routed to
`command grep` — **BSD grep 2.6.0**, where `-z` means null-data rather than *search inside
archives*. So `grep --version` and `command grep --version` named different programs, and one
flag decided which one ran. Call the binary you mean (`ugrep …`, `rg …`) when the semantics
matter, and check `type grep` before trusting a sweep's flags.

Worth knowing rather than mandating, since availability varies: **ugrep** carries the
features an audit sweep actually wants — `--bool` for `A AND B NOT C` queries (verified
working), `-z` to search inside archives and compressed files, `-Z` fuzzy, `-Q` interactive;
**ripgrep** is fastest and gitignore-aware by default (which is an exclusion, see the table
above); **ast-grep** answers construct questions regex cannot. Use what is installed, and
say which.

Choose by the question, not by fashion: a regex tool answers *"does this string appear"*;
answering *"is this construct used"* wants an AST matcher (`ast-grep`, a language's own
query API), because a regex generalises from whichever spelling you thought of and cannot
follow a value into a helper (`sota-code-security` rules/15 §2.1). Use whichever is
installed — and **report the tool, its flags and its exclusions in the same sentence as the
count.**

## 3. An ad-hoc command can destroy the thing it was checking

The failure modes above are about *wrong answers*. A verification command can also do
**damage**, and nothing about "I am only checking something" bounds its blast radius.
Field-reported: a command whose entire purpose was to check a claim copied a 40 GB build
directory into a container on a host already at 99% full, which corrupted the container
runtime's storage and cost ~64 GB of images. The check was never run.

Before an ad-hoc command that **writes at scale** — a container copy or build, an image
export, a bulk archive, a recursive `cp`/`rsync`, anything with `--output` on a big tree:

- **Look at headroom first** (`df -h` on the target filesystem, and on the runtime's own
  storage, which is often a different one). A verification step is not exempt from capacity
  planning; it is just unbudgeted.
- **Prefer read-only**: mount the source `:ro`, and send output **outside the source tree**
  to a path you chose. A check that cannot write to its subject cannot corrupt it.
- **Bound it before running it** — `du -sh` the thing you are about to copy. "It is only the
  repo" is a guess about size, and the number is one command away.
- **Build output is the trap, and it is never in your mental model of the repo.** `target/`,
  `node_modules/`, `.venv/`, `vendor/`, `build/` and `dist/` reach tens of gigabytes and are
  exactly what a naive recursive copy takes. Exclude them, or better, do not copy: point the
  tool's output elsewhere (`CARGO_TARGET_DIR=/build`, `--target-dir`, `-o`) and leave the
  source read-only.
- **A full disk is not a clean failure.** On a VM-backed container runtime the guest's disk is
  a sparse file on the host's, so exhausting the host surfaces *inside* the VM as I/O errors
  and can corrupt the filesystem and image store — minutes later, in an unrelated command,
  long after the one that caused it.
- Cleanup on a shared runtime is not housekeeping: see `sota-devsecops` rules/07 §7.7.

## Audit checklist

- [ ] **Sweeps: is the searcher's traversal and exclusion set stated with the count?** (§2)
      `-r` skips symlinked dirs met in traversal where `-R` follows; `rg` skips gitignored and
      hidden by default; `type grep` may reveal a wrapper. Control the sweep with a
      known-present term **in the same invocation**.
- [ ] **Ad-hoc commands that write at scale** (§3): headroom checked (`df -h` on the target
      *and* the runtime's own filesystem), source mounted read-only, output outside the source
      tree, size bounded with `du -sh` before the copy, and build output (`target/`,
      `node_modules/`, `.venv/`, `vendor/`) excluded or redirected rather than copied.
- [ ] **zsh joining bugs** (the inverse of SC2086, and unlinted): in any zsh script or
      snippet, `grep -nE '\$\{[a-zA-Z_]+:\+[^}]*\$' -e '[a-z] \$[a-zA-Z_]+$'` for
      `${var:+--flag $var}` and bare `cmd $args`. Each passes **one** argument in zsh
      where bash passes several. Confirm by running it: `printf "[%s]" $args` prints one
      bracket group, `${=args}` prints several. Symptom to recognise in a bug report — a
      **usage error (exit 2) from the callee**, which looks like the tool is broken.
