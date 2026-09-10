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
**traversing less than you think**.

**`-r` vs `-R` is not one rule — it depends on which `grep` you have.** Re-measured
2026-09-09 on macOS against a target reachable **only** through the link (the first
measurement of this table put the target inside the searched root as well, so every row
found it by walking the real directory and the distinction was invisible — a vacuous
fixture, `sota-testing` rules/06 §6.3):

| binary | symlinked dir **as the argument** | symlinked dir **met in traversal** |
|---|---|---|
| ugrep 7.8.4 `-r` | followed | **skipped, silently** |
| ugrep 7.8.4 `-R` | followed | followed |
| **BSD grep 2.6.0** (macOS `/usr/bin/grep`) **`-r` and `-R` alike** | **skipped** — unless the argument carries a **trailing slash** (`linked/`) | **skipped, silently** |
| `rg` (defaults) | followed | **skipped** — `--follow` follows |

```text
scan/plain.md          scan/linked -> ../outside   outside/target.md holds the needle
ugrep      -r → 1 of 2      -R → 2 of 2
/usr/bin/grep -r → 1 of 2   -R → 1 of 2      (find -L finds both; the file IS readable)
rg            → 1 of 2      --follow → 2 of 2
```

**So on macOS's default grep, `-R` is not the fix**, and advice that says "use `-R`" is
GNU/ugrep advice wearing a generic name. Verify on the binary in front of you, with a
positive control that the file is readable through the link at all — otherwise a
permission error and a skipped symlink are the same empty result.

So **a recursive search over any tree that may contain symlinked directories under-reports,
and the under-report is an empty or short result that reads as a clean answer.** It bites hardest
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

## 4. The loop you left running exhausts the process table — and takes cleanup with it

§3 is about a command that writes too much. This is the same idea aimed at a resource
nobody budgets: **processes**. It is the more dangerous of the two, because running out
of disk still lets you run `rm`, and running out of processes does not let you run
anything at all.

**The shape.** A wait loop, backgrounded, with no bound on its iterations:

```bash
# WRONG — nothing here ever stops, and each tick spawns
while ! pgrep -f "run-eval.py" >/dev/null; do sleep 60; done &
```

Every iteration forks (`pgrep`, `grep`, `ps`, the subshells in a `$(…)`), and a
backgrounded loop outlives the command that started it — often the whole session. §1's
`pgrep -f` self-match is what makes it never stop: the loop's own argv contains the
pattern, so it matches itself forever. §1 frames that cost as *a burned timeout*. The
larger cost is that it never stops **spawning**.

**How big it gets, measured — and read the attribution note.** At failure on the machine
below, `ps -A | wc -l` read **11,463** against a `kern.maxprocperuid` of **11,136**: the
per-user table was full, with **≈10,700 `/bin/sh`** in it.

**Correction (2026-09-10): those figures are the *signature*, not evidence for this
section's cause.** When this section was first written the numbers were attributed to
backgrounded wait loops, which had indeed been running that hour — but parentage had not
been checked, and the section said so. It was checked afterwards, and the `/bin/sh`
processes belonged to a **self-recursive `PATH` shim** (`rules/03` §3a); deleting one file
took the count to **691**. The tell was in the evidence all along: a `zsh` wait loop spawns
`zsh`, `sleep` and `pgrep` — never **10,700 `/bin/sh`**.

**Two unrelated causes produce this identical signature** — an unbounded backgrounded loop
(this section) and a wrapper that shadows a command it calls (`rules/03` §3a) — and **only a
parentage check distinguishes them**: `ps -axo pid=,ppid=,command=`, grouped by ppid.
Sequential PIDs with one child each is a recursion; many children under one parent is a pool
or a loop. Fixing the wrong one leaves the machine exactly as exposed, so **do not pick
between them from whichever you happen to have been doing that hour.**

The mechanism and the remedies below are unchanged and independently sound: an unbounded
backgrounded wait *is* a real way to fill the process table, whether or not it was this
incident's cause.

**Recognise the signature, because it is not the one you expect:**

- It does **not** degrade gradually. It hits a ceiling and *every* tool fails at once.
- The error is `fork failed: resource temporarily unavailable`, and it appears in the
  agent's shell and the operator's interactive shell **simultaneously** — which reads
  like the machine broke, not like a script did something.
- **The cleanup tools are inside the blast radius.** `ps -o ppid`, `killall`, `pkill`,
  even `echo` in a fresh shell, all need to fork. So does the diagnosis: you cannot
  learn which process leaked because listing parents requires a process.
- `kill` being a **shell builtin does not rescue you** if each command runs in a newly
  spawned shell — that spawn is the thing failing, before any builtin executes.
- What is left is a GUI process manager (already running, kills internally) or a
  reboot. Plan for that before you background anything.

**So:**

- **Do not poll work that something else already reports.** Where a harness, CI or job
  runner notifies on completion, waiting for that notification costs nothing; a polling
  loop costs a process per tick and buys the same answer later.
- **Never background an unbounded wait.** Before writing any repeating loop, ask what
  makes it *stop* — and if the answer is a `pgrep` on a pattern the loop's own argv
  contains, the answer is **nothing** (§1).
- **Bound the iterations, not just the sleep**: `for i in $(seq 1 60)`, never a bare
  `while true` / `until`. A loop that gives up is a loop that cannot leak forever.
- **Keep it in the foreground** so it dies with the command that started it, and **watch
  an artifact rather than a process** — `until grep -q DONE run.log` forks less and
  cannot match itself.
- **Check headroom for the resource you are about to spend**, exactly as §3 asks for
  `df -h`: `ps -A | wc -l` against `sysctl -n kern.maxprocperuid` (macOS) or `ulimit -u`.
  A loop that ticks every 60s for a day is 1,440 spawns *if each one exits* — and a
  leaked-process count that climbs while you watch it is the cheapest early warning
  there is, because at the ceiling you can no longer run the command that would tell you.

Blast radius is not only disk (§3). It is whatever finite resource the command consumes
without anyone counting — and the process table is the one whose exhaustion disables the
tools you would use to recover.

## 5. The listing tool answered your question about *one page*

§2 is a searcher that traverses less than you think. This is a lister that returns less
than you think — and it is worse, because the shortfall is **policy, not a bug**: the tool
did exactly what it was asked, exited `0`, and wrote nothing to stderr.

Measured 2026-09-10 against a repository with 330 merged pull requests:

```text
gh pr list --state merged --json number | wc -l        →   30    ← no flag: a DEFAULT cap
gh pr list --state merged --limit 20 ...               →   20    ← the cap you typed
gh pr list --state merged --limit 1000 ...             →  330    ← the population
exit status 0, stderr empty, in all three
```

The no-flag answer is off by an order of magnitude. Nothing in the output distinguishes
"there are 30" from "here are the first 30 of 330", and `wc -l` turns either into a number
that looks like a measurement. The same default sits under `gh issue list`, `gh run list`,
`aws ... --max-items`, `kubectl get --chunk-size`, `docker ps -n`, and every REST `GET`
that pages at 30 or 100 — **a client library that iterates pages for you is the exception,
not the rule, and `curl` never does.**

Two distinct ways to get this wrong, and the second is the one that repeats:

- **The cap you never set.** You reach for a lister to *look* at recent items, the default
  page is the right size for looking, and later the same command gets used to *count*.
- **The cap you set yourself, for a different question.** `--limit 20` was correct when the
  question was "show me the recent ones". It silently became the answer when the question
  changed to "how many are there" — the flag is still in the scrollback, and the number it
  produced looks like a finding. Read the flags in your own command before quoting its
  output as a total.

**A count and a sample need different commands.** When the number is the deliverable, ask
the API for the number rather than for the rows, or make the tool prove it reached the end:

```bash
# GOOD — the server counts; no page size can shorten a total
gh api -X GET search/issues --raw-field q='repo:OWNER/REPO is:pr is:merged' -q .total_count

# GOOD — page until short, and say so; --paginate exists precisely for this.
# NOTE the predicate: `state=closed` is merged AND closed-unmerged. Filter, don't assume.
gh api --paginate '/repos/OWNER/REPO/pulls?state=closed&per_page=100' \
  -q '.[] | select(.merged_at != null) | .number' | wc -l

# CONTROL — a cap you can see: if the count equals the limit exactly, assume truncation
n=$(gh pr list --state merged --limit 100 --json number -q '.[].number' | wc -l)
[ "$n" -eq 100 ] && echo "AT THE CAP — this is a page, not a total" >&2
```

**Then check the two methods against each other — and read the disagreement.** Writing
this section, the server count said **330** and the paginated read said **339**. The
pagination was right; the *predicate* was wrong — `state=closed` includes the 9 PRs that
were closed without merging, so the fixed command had quietly started answering a different
question than the one it replaced. A second method exists to have a **different failure
mode** (`sota-code-security` rules/11 §7), and the whole return on that is the moment the
two numbers differ. Had they agreed, nothing would have been learned; had I run only the
fixed one, `339` would have shipped as the merged total. Reconcile the gap to a named cause
(`330 + 9 unmerged = 339`) before reporting either number — an unexplained delta between two
methods is a finding, not a rounding difference.

That last line generalises past `gh`: **a result whose size equals a round number you or the
tool chose is a page until proven otherwise.** 30, 50, 100, 1000. It costs one comparison
and it is the only signal the tool gives you, because it does not give one.

The reporting rule follows §2's: **say which bound produced the number.** "330 merged PRs
(`--limit 1000`, no truncation — the run returned fewer rows than the cap)" is a
measurement. "330 PRs" is a claim whose evidence has been thrown away, and "30" was too.


## Audit checklist

- [ ] **Sweeps: is the searcher's traversal and exclusion set stated with the count?** (§2)
      `-r` skips symlinked dirs met in traversal and `-R` follows **only on ugrep/GNU** —
      on BSD grep (macOS `/usr/bin/grep`) neither does; `rg` skips gitignored and hidden by
      default; `type grep` may reveal a wrapper. Control the sweep with a known-present term
      **in the same invocation**.
- [ ] **Ad-hoc commands that write at scale** (§3): headroom checked (`df -h` on the target
      *and* the runtime's own filesystem), source mounted read-only, output outside the source
      tree, size bounded with `du -sh` before the copy, and build output (`target/`,
      `node_modules/`, `.venv/`, `vendor/`) excluded or redirected rather than copied.
- [ ] **Backgrounded wait loops** (§4): does any `&`-ed loop lack a bound on its
      iterations, and does anything make it stop other than a `pgrep` that matches the
      loop's own argv? Grep for the shape — `grep -nE '(while|until).*(true|pgrep|ps ).*&\s*$'`
      — and for polling of work a harness already reports. Headroom for the resource
      being spent is checked (`ps -A | wc -l` vs `ulimit -u`), not just `df -h`. If the
      table is already full, **establish parentage before assigning blame** — a
      self-recursive wrapper (`rules/03` §3a) produces the same signature, and only
      `ps -axo pid=,ppid=,command=` tells the two apart.
- [ ] **Counts taken from a listing tool** (§5): does the command carry a `--limit`/
      `per_page`/`--max-items`, or rely on the tool's **default** page (30 for `gh`, 100 for
      most REST)? A total must come from a server-side count (`total_count`) or a paginated
      read (`gh api --paginate`), never from the first page. Treat a result whose size equals
      the cap exactly as truncated, and quote the bound alongside the number. Where a second
      method was run, is the delta between the two reconciled to a named cause — or was the
      un-truncated command also given a **different predicate** (`state=closed` vs merged)?
- [ ] **zsh joining bugs** (the inverse of SC2086, and unlinted): in any zsh script or
      snippet, `grep -nE '\$\{[a-zA-Z_]+:\+[^}]*\$' -e '[a-z] \$[a-zA-Z_]+$'` for
      `${var:+--flag $var}` and bare `cmd $args`. Each passes **one** argument in zsh
      where bash passes several. Confirm by running it: `printf "[%s]" $args` prints one
      bracket group, `${=args}` prints several. Symptom to recognise in a bug report — a
      **usage error (exit 2) from the callee**, which looks like the tool is broken.
