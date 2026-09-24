# 06 — Ad-hoc commands: the ones you type to check something

Scope: the commands nobody commits — a sweep, a probe, a one-liner pasted from a
checklist, a quick container copy. They are unlinted, unreviewed, and run against the
system under test, so when they go wrong they produce a false finding **about the
product**, or damage the thing they were inspecting. Split out of `rules/01` at v1.38.0 —
its zsh, sweep and blast-radius sections became §1, §2 and §3 here. The blast-radius and
process-table sections moved on to `rules/08` at v1.42.2, keeping their numbers,
and the listing and selection sections (§5, §5a) to `rules/09` (· v1.43.1) the same
way. Quoting itself stays in
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
| `cmd \| python3 - <<'PY'` (pipe **and** heredoc on fd 0) | heredoc wins, piped data **discarded** | `MULTIOS` **concatenates** them: the data runs as the program's first lines | bash **quietly** (script reads empty stdin); zsh **loudly but misleadingly** (below) |

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
- **Never pipe into an interpreter that reads its program from a heredoc** (row 4). zsh's
  `MULTIOS` is on by default, so `echo '{"a": false}' | python3 - <<'PY'` fails with
  `NameError: name 'false'` at `<stdin>` line 1 — an error naming *your data*, which reads as
  a data bug. Measured zsh 5.9, bash 3.2 and 5.3, `sh`. Write the script to a file and pipe
  into it, or save the input to a file the heredoc opens.

## 2. The sweep that never ran: `grep -r` over symlinks — and the positive control that catches ANY broken sweep

§1 is about a *quoting* bug stopping the command. This is the command running fine and
**traversing less than you think**.

**`-r` vs `-R` is not one rule — it depends on which `grep` you have.** Re-measured
2026-09-09 on macOS against a target reachable **only** through the link (the first
measurement of this table put the target inside the searched root as well, so every row
found it by walking the real directory and the distinction was invisible — a vacuous
fixture, `sota-testing` rules/06 §6.3):

| binary | symlinked dir **as the argument** | symlinked dir **met in traversal** |
|---|---|---|
| ugrep 7.8.4 **and** GNU grep 3.11, `-r` | followed | **skipped, silently** |
| ugrep 7.8.4 **and** GNU grep 3.11, `-R` | followed | followed |
| **BSD grep 2.6.0** (macOS `/usr/bin/grep`) **`-r` and `-R` alike** | **skipped** — unless the argument carries a **trailing slash** (`linked/`) | **skipped, silently** |
| `rg` (defaults) | followed | **skipped** — `--follow` follows |

```text
scan/plain.md          scan/linked -> ../outside   outside/target.md holds the needle
ugrep      -r → 1 of 2      -R → 2 of 2
/usr/bin/grep -r → 1 of 2   -R → 1 of 2      (find -L finds both; the file IS readable)
rg            → 1 of 2      --follow → 2 of 2
```

**So on macOS's default grep, `-R` is not the fix**, and "use `-R`" is GNU/ugrep advice wearing
a generic name. Re-measured 2026-09-13, GNU grep 3.11 matched ugrep cell for cell — the split is
**BSD versus everyone else**. Verify on the binary in front of you, with a positive control that
the file is readable through the link — else a permission error and a skipped symlink look alike.

So **a recursive search over any tree that may contain symlinked directories under-reports,
and the under-report is an empty or short result that reads as a clean answer.** It bites hardest
where the tree is *made* of links: a skills or plugin directory installed by symlink, a
monorepo with linked packages, `node_modules` with workspace links, a dotfiles checkout.
Use `-R` when you mean "follow", and say which you used when you report a count.

**Control the search in the SAME invocation — and this part is not about symlinks.** It is
the general remedy for every false absence in this file, and it sits here only because the
symlink case is where it was first measured. §1 says to positive-control a sweep; the
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

**A passing control proves the instrument, not the scope.** A control drawn from *inside* the
scope you searched passes whether or not that scope excludes the answer. Field-reported:
`rg -l 'positive control' skills/ --glob '**/rules/*.md'` returned 4 files, the real query
returned 0 and was reported as a gap, and the answer sat in `skills/sota/SKILL.md`, which that
glob never matches. **Draw the control from where your scope is least likely to reach**, and
print the file count beside the zero: a denominator that is implausibly small for the corpus
is the tell.

**Where you have nothing to control *with*, print a denominator instead.** A positive control
needs a term you already know is present — unavailable exactly where this fails most: an
**extraction** or **fetch** into a blob you have never opened. Field-reported, six empty
results in one session each read as a fact about the subject — `cpio -i` listed 0 files from
an RPM (it cannot read zstd payloads), `tar -tzf` found 0 members in a valid 39.8 MB archive,
a fetch returned an empty page (an anti-bot challenge), `apt-cache depends` printed nothing
(wrong query shape). Every one was the reader failing, and every one rendered as `0`.

The fix is mechanical and needs no prior knowledge of the target: make each extraction,
fetch or search emit **what it got** beside **what it found**, in the same invocation.

```bash
# BAD  — a fact about the subject, or a broken reader. Indistinguishable.
rpm2archive -n "$RPM" | tar -xO ./boot/config-* | grep -c CONFIG_BPF_LSM

# GOOD — the denominator localises the failure in one step
printf 'ARCHIVE_BYTES:%s  MEMBERS:%s  CONFIG_LINES:%s\n' \
  "$(stat -f%z "$TGZ")" "$(tar -tzf "$TGZ" | wc -l)" "$(grep -c '^CONFIG' "$CFG")"
```

`CONFIG_LINES:0` alone is a finding about the kernel. `CONFIG_LINES:0` beside
`ARCHIVE_BYTES:39802880 MEMBERS:0` is a finding about your `tar` invocation. Same rule for a
store rather than a file — an empty result carries the store's identity *and* its inventory:
`sota-code-security` rules/13 §6.

**And where a command *reports* what it did, read the result instead.** `cargo clean`
printed `Removed 740751 files, 75.8GiB total` — specific and authoritative — while `df`
showed nothing freed, a snapshot still holding the blocks. Two instruments caught it by
luck, not by design.

**Every searcher has silent-exclusion defaults, and they differ — so the fix is naming them,
not switching tool.** Measured on one tree holding four matches (plain, hidden, gitignored,
behind a symlinked dir):

| searcher | found | what it dropped, silently |
|---|---|---|
| `rg` (defaults) | **1 of 4** | gitignored, hidden, and symlinked-dir contents |
| `grep -R` (see below) | 3 of 4 | the gitignored file |
| `rg --no-ignore` alone | **2 of 4** | **still every hidden dir** — and it searched *more* files |
| `rg --hidden --no-ignore --follow` | **4 of 4** | — |

**`--no-ignore` is the trap inside the trap.** It is the flag that *sounds* like "stop
excluding things", so it is the one reached for — and it does not touch hidden directories
at all. Because it searches strictly more files than the default (measured on one repo:
**1042 vs 404**), the run reads as the more thorough one while missing the same matches. An
agent-rules tree is exactly what this hides: `rg PAT .` never enters `.claude/`, `.github/`
or `.githooks/`. Only `--hidden` reaches them (404 → 576 files, 2 → 4 matching files).

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

## 2a. `rg -r` is `--replace`, not "recursive" — the same trap inverted

§2's `grep -r` fabricates a false **absence**. Its twin fabricates false **content**, and
the reflex that produces it is the same muscle memory:

```
rg -rn --no-heading "events_dropped|queue_len" crates/
```

`rg` is recursive by default, so `-r` is free to mean `--replace`, and it consumes the next
argument as the replacement template. Every matching line prints with the match **rewritten**,
and it exits **0**. Field-measured: that command printed source reading `pub n: u64` and
`let mut n = 0_u64` — which reads exactly like a field that has been renamed. Three hours
later, in the same session, it happened again and produced a document containing the phrase
*"shared n test suite"*.

| | what it does | what the output looks like |
|---|---|---|
| `grep -r` over a symlinked dir | silently skips it | "no matches" — a clean absence |
| `rg -r PATTERN PATH` | rewrites every match to `PATTERN` | real lines, real paths, wrong content, exit 0 |

The absence at least *looks* like nothing. This one looks like evidence, and it is the
shape you then quote into a finding or a commit message.

**Fix:** `-n` alone for line numbers; `--replace` spelled out when you actually mean it. And
**`cat` one hit before building an argument on a surprising search result** — the tell here
was never the exit code, it was that the content was implausible (`sota-code-security`
rules/15 §2.1, sixth
bullet). Writing this trap into a personal rules file did **not** prevent the second
occurrence; noticing the implausible output did.

**A second tell, mechanical rather than judgemental.** `-rn` parses as `-r n`, so the
`-n` you typed is eaten as the replacement template and never applied. The output comes
back as `path:content` when you asked for `path:LINE:content` — **if you typed `-n` and
the line numbers are missing, the content has been rewritten.** Verified on ripgrep 15.2.0,
both arms, exit 0 each time:

```console
$ rg -n  'Missing .*gate for' .     $ rg -rn 'Missing .*gate for' .
./b.py:1:beta Missing auth gate...  ./b.py:beta n deletion
./a.py:1:alpha Missing auth gate... ./a.py:alpha n deletion
```

This matters because the plausibility tell is weakest exactly where you need it: an
unfamiliar tree, a language you do not write, a rewritten line that is merely odd rather
than absurd. The line-number test needs no knowledge of the file at all.

**Three independent reporters have now hit this with the rule installed, two with it
loaded in context.** That is the calibration: the lever is not stating it more loudly.
A reporter who had written the trap into their own rules file hit it again three hours
later; another read this section's one-line index entry and hit it fourteen tool calls
afterwards. Prefer a mechanical tell you can apply to output you already have.

## 2b. An empty command substitution removes the filter rather than matching nothing

§2 and §2a distrust a suspiciously *empty* result. This points the same discipline at an
implausibly *full* one:

```bash
git log --author="$(get_author)" --oneline | wc -l     # 373 of 373 commits, exit 0
```

The substitution expanded to `""` and the filter **matched everything**: asked *"what did this
person commit?"*, answered *"what is in this repo?"* Quoted, so this is not SC2086.

**Which flags do this, measured 2026-09-13 — the split is the useful part:**

| the flag filters by… | an empty value | measured |
|---|---|---|
| **pattern / substring** | **matches everything** | `git log --author=""` and `--grep=""` 373 of 373 · `grep -e ""` 3 of 3 |
| **identifier** | rejected, or matches nothing | `ps -p ""` exit **1** on BSD *and* procps-ng 4.0.4 · `find -name ""` 0 hits, exit 0 |

So a `--filter`-shaped flag is dangerous when it filters by *pattern*, merely useless when it
filters by *id*. (Separately: `ps -axo … -p "$pid"` lists **every** process even for a valid
pid — `-a`/`-x` override `-p` — so an implausibly large result there is the flags.)

Guard the substitution, not the command:

```bash
author="$(get_author)"
[[ -n ${author} ]] || { printf 'no author resolved\n' >&2; return 1; }
git log --author="${author}" --oneline
```

The tell is §2a's: the **result was implausible** before it was wrong — treat one far
*larger* than expected exactly as a clean zero (`sota-code-security` rules/15 §2.1).

## 2c. A search pattern that begins with `-` is parsed as a flag

§2a rewrites your output and §2b widens your filter. This one **destroys the query** and
hands back a clean zero. A pattern is *data*, but the tool sees argv:

```console
$ rg -c -F '- [ ]' . 2>/dev/null ; echo "exit=$?"
exit=2                                  # no output at all
$ rg -c -F '- [ ]' . 2>&1 | head -1
rg: unrecognized flag -                 # the evidence 2>/dev/null destroyed
$ rg -c -F -e '- [ ]' .
./t.md:2                                # the real answer
```

Field-reported: a tracker sweep reported **zero** unchecked boxes against a real **65**,
and the session nearly opened by announcing an empty backlog.

**Put the pattern after `-e`, or the argument list after `--`, whenever the pattern is
data** — not only when you notice it starts with a dash. You will not always notice: the
same trap bit a `printf` while its victim was building the fixture to demonstrate it.

**And it is shell-dependent, which is why "I tested it" is not an answer.** The identical
command is correct in one shell and broken in another — measured on one machine:

| | `printf "- [ ] box\n"` | exit |
|---|---|---|
| bash 5.3 builtin | `invalid option` | 2 |
| zsh 5.9 builtin | prints correctly | 0 |
| `/usr/bin/printf` (BSD) | `illegal option` | 1 |
| `/bin/sh` | `invalid option` | 2 |

A contributor who checks this in zsh concludes the trap is imaginary. Three different
exit codes across four implementations, and only one of them is success.

**The combination never to write** is a `-`-leading pattern **+** `2>/dev/null` **+**
`$?` read after a pipe: the first manufactures the wrong answer, the second hides the
reason, and the third certifies it (`rules/01` §3 for why `$?` after a pipeline is the
last stage's status).

## 2d. `cmd 2>/dev/null || echo "missing X"` reports your broken sweep as their defect

The `||` arm is meant to mean *"the pattern was absent."* It fires on **every** non-zero
exit, and `2>/dev/null` has already destroyed the evidence of which one. `grep` exits `1`
for no-match and `2` for an unreadable or missing path — `||` cannot tell them apart:

```console
# one path in the list does not exist
$ grep -rnE 'Werror|/WX' CMakeLists.txt cmake/ Makefile_absent 2>/dev/null || echo "no -Werror"
CMakeLists.txt:1:add_compile_options(-Werror)
no -Werror          <- it printed the match AND the verdict that contradicts it

$ grep -rnE 'Werror' CMakeLists.txt Makefile_absent >/dev/null 2>&1 ; echo $?   # 2, path missing
$ grep -rnE 'ZZZ'    CMakeLists.txt                 >/dev/null 2>&1 ; echo $?   # 1, truly absent
```

The failure is **directional**: it manufactures findings rather than hiding them, so an
auditor sees plausible output and files it against someone's codebase. In zsh an unquoted
`Makefile*` that matches nothing raises NOMATCH and aborts the whole command, so neither
the `grep` nor the `|| echo` runs and the item silently yields nothing at all (§1).

**Never suppress stderr on a sweep whose *absence* you intend to report.** Branch on the
exit code you actually mean, and print the captured stderr beside the verdict:

```sh
err=$(grep -rnE "$pat" $paths 2>&1 >/dev/null); rc=$?
case $rc in
  0) echo "FOUND" ;;
  1) echo "ABSENT" ;;
  *) echo "SWEEP FAILED (rc=$rc): $err" ;;   # never the same branch as ABSENT
esac
```

This library shipped the broken form in **11 files** of its own audit checklists until
v1.42.2 — found by a reporter, not by any gate. A checklist line is a control, and a
control that cannot distinguish "clean" from "did not run" is the silent-control-failure
shape (`sota-code-security` rules/10).

## 2e. A label that states the verdict is not evidence of the verdict

§2d's `|| echo` fires on any non-zero exit. This is its **unconditional** twin, and it is
worse, because it fires always:

```bash
ps -axo pid=,command= | grep -c "[m]y-job"; echo "^ 0 = nothing running"   # printed 1
```

The label is typed **before** the command runs, so it records what you expected rather than
what happened — and it renders in the same block as the real output, where prediction and
measurement are typographically identical on re-reading. `;` cannot propagate a
contradiction, and a literal string cannot be falsified by the line above it.

Measured 2026-09-18: four instances in one session, each contradicted by the output directly
beneath it. The costly one asserted a rule was **absent from a corpus** one line above output
proving it was present — the next step would have been adding a rule that already existed.

**Print the value, not your reading of it.** Where a verdict is genuinely needed, derive it
from the same variable the command produced:

```bash
n=$(ps -axo command= | grep -c "[m]y-job")
[ "$n" -eq 0 ] && echo "none running" || echo "$n still running"
```

That is `sota-code-security` rules/14 §1 applied to your own scrollback: a claim is sited in
the **consumer**, derived from the value it actually received. **The tell on review** is a
line beginning `^`, `(` or `<-` that asserts a *state* rather than naming a *quantity*. Read
the output above it before believing it — including your own.

## 2f. A word-boundary escape is a property of the machine, not of the tool

`\b` and `\<` are not portable, and failing them is **silent**: no match, exit 1,
indistinguishable from a true absence. The same pattern, the same git and the same repository
**answer differently on different machines** — that part is measured below, on four builds.

The *mechanism* is verified on one of them and is stated at that width: on the macOS build,
`nm -u` shows `_regcomp` **imported** with only git's own `_git_regcomp` wrapper defined, so
that git inherits the platform's regex rather than carrying its own. Do not assume the same
linkage elsewhere — the equivalent check on an Alpine build returned neither an imported nor a
defined `regcomp` while `nm -D` still listed 252 symbols, which is a fact about that
instrument, not about the binary. **You do not need the mechanism to act on this**: the
behaviour is the rule, and the control below is what makes it visible.

Measured 2026-09-18 over a file containing `53`, control (`53` alone) matching in every row:

| platform | git | `\b` / `\<` | `[[:<:]]` |
|---|---|---|---|
| macOS, system BSD regex | 2.55.0 | **no match** | matches |
| Debian, glibc | 2.39.5 and 2.47.3 | matches | **no match** |
| Alpine, musl | 2.45.4 | matches | — |

**There is no version to pin** — three older gits match `\b` and the newest does not. The GNU
and BSD forms are **mutually exclusive**, so neither is portable. Use `-P` where PCRE is
compiled in, or drop the boundary and filter afterwards.

This cost two false absences in one session: a count search over an agent file that plainly
contained the number, and a reference sweep that reported zero while five references existed.
Both were caught only because a second, differently-shaped measurement disagreed. **Run §2's
positive control on the search itself.**

**The placement defect this paragraph predicted, then repeated.** It used to end: *§2 states
that control under a heading about symlinked directories … and that placement is why it was
skipped here.* It happened **again on 2026-09-21**, to a different reader on a different
stack — a field report whose `git grep -cE '\b(TODO|FIXME)\b'` returned 0 files on macOS with
its control returning 0 too, exactly this section, three days after it was written. Two
independent readers, one cause, so the heading was the defect and not the readers: §2 now
names the control in its own title. **A rule filed under where it was first measured is
filed under the wrong thing** — index it by what it is *for*.


## Audit checklist

- [ ] **Command substitutions that supply a filter are guarded for empty** (§2b) — an empty
      value makes a **pattern** flag match everything (`git log --author=""` returned 373 of
      373); an identifier flag rejects it instead. An implausibly LARGE result is the tell

- [ ] **No `rg -r` used to mean "recursive"** (§2a) — it is `--replace`, it rewrites every
      match to the next argument and exits 0, so the output is false *content* rather than a
      false absence. `grep -rn 'rg -r' ` your own scripts and scrollback before quoting a
      surprising search result

- [ ] **Is any search pattern passed as a bare argument when it could begin with `-`?** (§2c)
      It is parsed as a flag, the error goes to stderr, and you get a clean zero. Use `-e
      PATTERN` or `--` whenever the pattern is *data*. The unforgivable combination is
      `-`-leading pattern + `2>/dev/null` + `$?` after a pipe. Shell-dependent: the same
      `printf` succeeds in zsh and fails in bash, so one green run proves nothing.
- [ ] **Does any check report an absence through `|| echo` with stderr suppressed?** (§2d)
      `cmd 2>/dev/null || echo "missing X"` fires on *every* non-zero exit — grep's `2`
      (unreadable path) is indistinguishable from `1` (absent) once stderr is gone, and it
      manufactures findings about someone else's code. Branch on the exit code and print the
      captured stderr. Sweep your own checklists for the shape: `grep -rn '2>/dev/null ||'`.

- [ ] **Does any command carry a hardcoded label asserting its own result?** (§2e) — a
      trailing `; echo "^ 0 = ..."` is a prediction typed before the run, and `;` cannot
      propagate a contradiction. Sweep your own scripts and scrollback for `; *echo` beside
      a counting command; print the value and derive any verdict from the variable the
      command produced
- [ ] **Does any search rely on `\b` or `\<`?** (§2f) — absent from BSD/macOS regex, and
      `git grep` inherits the platform's, so the same pattern silently returns zero on one
      machine and matches on another. There is no version to pin. Use `-P`, the POSIX
      bracket form, or no boundary at all — and control the search
- [ ] **Sweeps: is the searcher's traversal and exclusion set stated with the count?** (§2)
      `-r` skips symlinked dirs met in traversal and `-R` follows **only on ugrep/GNU** —
      on BSD grep (macOS `/usr/bin/grep`) neither does; `rg` skips gitignored and hidden by
      default; `type grep` may reveal a wrapper. Control the sweep with a known-present term
      **in the same invocation**, drawn from where the scope is least likely to reach: a
      control from inside a too-narrow glob passes while the answer sits outside it.
- [ ] **Every extraction or fetch printed a denominator** (§2) — bytes retrieved, members
      listed, total files — in the **same invocation** as the result read from it. `LINES:0`
      alone is a fact about the subject; `LINES:0` beside `MEMBERS:0 BYTES:39802880`
      localises it to the reader. Required wherever a positive control is unavailable
      because nothing is known to be present in the target yet.
- [ ] **zsh joining bugs** (the inverse of SC2086, and unlinted): in any zsh script or
      snippet, `grep -nE '\$\{[a-zA-Z_]+:\+[^}]*\$' -e '[a-z] \$[a-zA-Z_]+$'` for
      `${var:+--flag $var}` and bare `cmd $args`. Each passes **one** argument in zsh
      where bash passes several. Confirm by running it: `printf "[%s]" $args` prints one
      bracket group, `${=args}` prints several. Symptom to recognise in a bug report — a
      **usage error (exit 2) from the callee**, which looks like the tool is broken.
- [ ] **Does any command pipe into `interpreter - <<EOF`?** (§1) Both claim fd 0: bash drops
      the pipe, zsh prepends it to the program. Sweep with `grep -nE '\| *[a-z0-9]+ +- *<<'`.
