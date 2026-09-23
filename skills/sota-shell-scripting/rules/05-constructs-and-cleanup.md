# 05 — Constructs & Cleanup: arrays, IFS, traps, tests, globbing

Scope: the constructs a script is assembled from, and the way each of them fails. Split out
of `rules/01` at v1.37.0, which keeps the safety baseline — shebang, `set -e` semantics,
quoting, and the zsh deviations that bite pasted commands. Quoting is `rules/01` §3; this
file is what you reach for once the expansion itself is correct.

## 1. Arrays for command building (SC2089/SC2090/SC2086)

```bash
# BAD — flags in a string; quoting inside the string does NOT survive expansion
opts="-v --exclude '*.log'"
rsync $opts src/ dst/

# GOOD — array; conditional construction is natural
rsync_opts=(-a --delete)
[[ ${VERBOSE:-} ]] && rsync_opts+=(-v)
[[ ${EXCLUDE:-} ]] && rsync_opts+=(--exclude "$EXCLUDE")
rsync "${rsync_opts[@]}" -- "$src/" "$dst/"
```

Empty-array expansion under `set -u` errors on bash < 4.4; if you must support old bash,
use `${arr[@]+"${arr[@]}"}`. On bash ≥ 4.4 `"${arr[@]}"` on an empty array expands to
zero words, which is what you want.

## 2. IFS handling

- Never set `IFS` globally to "fix" splitting — fix the quoting instead. A global
  `IFS=$'\n'` changes behavior of every subsequent `read`, `$*`, and unquoted expansion.
- Scope IFS to the single command that needs it:

```bash
# GOOD — IFS scoped to read; -r stops backslash mangling
while IFS= read -r line; do
  process "$line"
done < "$input"

# GOOD — split a known-delimited string into an array, scoped
IFS=, read -r -a fields <<< "$csv_line"
```

- `read` without `-r` is almost always a bug (SC2162). `IFS=` before `read` preserves
  leading/trailing whitespace.

## 3. trap-based cleanup and mktemp

Every script that creates temp files, locks, background jobs, or partial state gets:

```bash
tmpdir=""
cleanup() {
  local status=$?
  # idempotent: safe to run twice, guards every action
  [[ -n $tmpdir && -d $tmpdir ]] && rm -rf -- "$tmpdir"
  return "$status"   # don't mask the real exit code
}
trap cleanup EXIT

tmpdir=$(mktemp -d)   # never $$-based or hardcoded /tmp names (race + symlink attack)
```

- `trap ... EXIT` covers normal exit, `set -e` exits, and (in bash) signal-initiated exits
  *if* the signal traps re-raise. Standard pattern when you need signal-specific behavior:

```bash
trap cleanup EXIT
trap 'trap - TERM; kill -TERM -- -$$' INT TERM   # forward to process group, then EXIT trap runs
```

- Cleanup must be **idempotent** (EXIT can follow INT) and must not assume variables are
  set (it can run before initialization completes — hence `tmpdir=""` first, guards inside).
- Don't put logic after `exit` relying on the trap having "finished": the trap *is* the end.
- `mktemp -d` for dirs, `mktemp` for files; honor `TMPDIR`. GNU vs BSD `mktemp` differ on
  templates — `mktemp -d "${TMPDIR:-/tmp}/myscript.XXXXXX"` is portable enough; plain
  `mktemp -d` works on both modern GNU and macOS.

## 3a. Sourcing a script to test one function relocates the script

"Run one function from a large script" is how shell gets tested at all, and both obvious
moves fail — the second one **silently**:

```bash
# attempt 1 — strip the entry point and eval the rest
eval "$(sed '$d' scripts/ci-local.sh)"
#   -> BASH_SOURCE[0]: unbound variable
#   the script derives REPO_ROOT from BASH_SOURCE, which eval never sets

# attempt 2 — strip it into a temp file and source THAT
sed '$d' scripts/ci-local.sh > /tmp/lib.sh && source /tmp/lib.sh
#   -> no error at all. REPO_ROOT is now /tmp, because BASH_SOURCE points at the COPY,
#      and the script's own `cd -- "$REPO_ROOT"` has moved you out of the repository
```

Attempt 2 is the dangerous one: it succeeds. Every `git` call in every function under test
then fails, and the harness emits a **correct, well-written diagnostic about healthy code** —
field-measured as `the compiled-in scan found 0 path(s); it has stopped working`, from a scan
that was fine. That is `sota-code-security` rules/15 §2.1's sixth failure mode: the harness is
newer than the subject, so it owns the prior.

**The better fix is in the script, not the test.** Guard the entry point so the file can be
sourced as a library:

```bash
[[ ${BASH_SOURCE[0]} == "$0" ]] && main "$@"
```

Failing that, source the copy and `cd` back before calling anything:

```bash
bash -c 'source "$SCRATCH/lib.sh"; cd "$REAL_REPO_ROOT"; the_function_under_test'
```

Any script that resolves its own root from `BASH_SOURCE`/`$0` — which is the correct way to
do it — carries this hazard for anyone who sources it.

## 3b. In-place edit on a symlink — and why `sed -i` is the trap, not the fix

`sed -i` and `perl -pi` are treated as interchangeable spellings of "edit this file in
place". They are not — and the difference is **per implementation, not per tool**, which is
the part that bites: the safe behaviour exists only on the platform you develop on.

Measured 2026-09-13, editing a symlink that points at a regular file:

| implementation | `-i` on a symlink | exit | the link afterwards |
|---|---|---|---|
| **BSD sed** (macOS `/usr/bin/sed`) | refuses: `in-place editing only works for regular files` | **1** | intact |
| **GNU sed 4.9** (Debian) | **silently replaces the link with a regular file** | **0** | gone |
| **BusyBox sed 1.37.0** (Alpine) | **silently replaces the link with a regular file** | **0** | gone |
| **perl -pi** (5.34.1) | **silently replaces the link with a regular file** | **0** | gone |
| GNU sed `-i --follow-symlinks` | edits the **target**, link preserved | 0 | intact |

In every silent case the **target is never modified**, so the two paths diverge without a
word: the former target still holds the old content, and what was a view of it is now an
independent copy.

**The dangerous shape is the platform split, and it runs the wrong way.** A developer on
macOS types `sed -i`, sees it refuse on a symlink, and concludes the idiom is safe. The same
script in CI — Debian, Alpine, any Linux image — destroys the link silently and exits 0. The
machine where you *test* the safety is the only machine that has it.

- **Do not rely on `sed -i` refusing.** That is BSD behaviour, not `sed` behaviour. The only
  portable assumption is that an in-place edit **replaces** a symlink.
- **Enumerate regular files when you sweep**, rather than paths:
  `git ls-files -s '*.md' | awk '$1=="100644"{print $4}'` — mode `120000` is a symlink.
  `find . -type f` excludes them for the same reason; `find . -type l` finds them.
- **`--follow-symlinks` is GNU-only**, so a script that needs it is a script that has just
  become non-portable — say so in a comment rather than discovering it on a BSD runner.
- **`git status` shows this as `T` (typechange), not `M`** — one character apart in a list
  you are skimming, and the only signal you get.

Why it is worth a rule rather than a footnote: **a repository's symlinks are usually load
bearing, and a sweep is exactly what destroys them.** Field-reported the same day:
`git ls-files '*.md' | xargs perl -pi -e …`, run to hand-test a probe, converted a repo's
tracked `CLAUDE.md` and `GEMINI.md` into regular files, and `git add -A` staged the type
change before anyone noticed.

## 3c. A hard link does not survive the way tools actually update files

§3b is an in-place edit destroying a **symlink**. This is the mirror: reaching for a **hard**
link to avoid that, and getting a failure mode that is strictly worse because nothing breaks.

Measured 2026-09-13:

```console
$ ln real.txt hard.txt      # same inode: 51720584 51720584, contents agree
$ printf 'v2\n' > .tmp && mv -f .tmp real.txt      # how an atomic writer updates
$ cat real.txt; cat hard.txt
v2
v1                          # inodes now 51720587 vs 51720584
$ ln somedir somedir2
ln: somedir: Is a directory
```

**Nothing errors and no link is broken** — `hard.txt` is simply a stale file that looks
correct. Compare a symlink, whose failure mode is loud and obvious.

- **Almost nothing edits a file in place.** git never does; nor does any "atomic write"
  (`mktemp` + `mv`), which is most config-writing tools, most editors, and most formatters.
  Each one writes a new inode and renames over the old name, and every hard link to the old
  inode silently keeps the old content.
- **You cannot hard-link a directory at all**, so any design that links *directories* into
  place is out before you start — a symlink to a directory also picks up new files inside it
  for free, which a per-file link can never do.
- **Prefer the symlink and accept its loud failure.** "Broken link" is an error message;
  "stale content that looks correct" is a bug report six weeks later.

## 3d. Rewriting a script that is still running changes what it runs

§3b and §3c are what an edit does to *other names* for a file. This is what it does to a
**process** that is executing the file. bash reads a script as it runs rather than loading
it all up front, so how the new content is written decides what the running process
executes next:

- **Truncate and write the same file** (`>`, `cat >`, an editor's save-in-place, Python's
  `write_text`): the running process keeps its byte offset into the **new** content, and
  executes whatever now sits there.
- **Write a new file and rename it over the old one** (`mv`, `sed -i`, `perl -pi`): the
  running process keeps the old inode and finishes the **original** script.

Measured on macOS bash with the falsifier stated first ("if the running script prints only
its original lines, this is wrong"). A 4-line script echoed line 1 and slept, then was
rewritten mid-run. After truncate-and-write it printed `EDITED line 3`; after write-and-rename
it printed the original line 3. Field case in this library: a 27-minute run died with
`$1: unbound variable` and a syntax error at a line that was valid in both versions, after the
script was rewritten beneath it. **Never rewrite a script while it runs**: write a new file and
rename it over the old one, or wait for the run to end. Other shells are not measured here.

## 4. Test constructs, printf, declarations

- `[[ ]]` over `[ ]` in bash: no word splitting of unquoted vars, `&&`/`||` inside,
  `=~` regex, `<`/`>` string comparison without escaping. Use `[ ]` only in POSIX `sh`.
- Arithmetic: `(( count > 3 ))`, not `[ $count -gt 3 ]`. But beware `(( x ))` returns
  nonzero when x=0 — under `set -e`, `(( count++ ))` with count=0 kills the script;
  write `(( ++count ))` or `count=$((count + 1))`.
- `printf` over `echo` for any variable data: `echo` behavior with `-n`, `-e`, and
  backslashes is implementation-defined (dash interprets escapes by default; a variable
  that *is* `-n` vanishes). `printf '%s\n' "$var"` is exact (SC2028 hints at this).
- `local` for every function variable (SC2034 finds unused leaks); remember the SC2155
  split-declaration rule from `rules/01` §2.
- `readonly` (or `declare -r`) for constants and config resolved at startup — catches
  accidental reassignment at the point of the bug:

```bash
readonly SCRIPT_NAME=${0##*/}
readonly DEFAULT_REGION=${REGION:-eu-central-1}
```

## 5. Globbing pitfalls and never parsing ls

- A glob that matches nothing stays **literal**: `rm ./*.tmp` with no matches tries to
  remove the file `./*.tmp`. Choose explicitly:
  - `shopt -s nullglob` — no match → zero words (right for loops over files; beware: makes
    `ls *.tmp` become bare `ls`).
  - `shopt -s failglob` — no match → error (right for "these files must exist" scripts).
- `for f in ./*` not `for f in *` — a file named `-rf` becomes an option otherwise; same
  reason as `--` separators.
- Dotfiles are excluded from `*` unless `shopt -s dotglob`.
- **Never parse `ls`** (SC2012/SC2045): output is for humans, mangles non-ASCII/newline
  names, and splits on whitespace.

```bash
# BAD
for f in $(ls /data); do ...
count=$(ls | wc -l)

# GOOD
for f in /data/*; do
  [[ -e $f ]] || continue   # or rely on nullglob
  ...
done
count=$(find /data -mindepth 1 -maxdepth 1 -printf '.' | wc -c)   # GNU; or a glob-into-array
files=(/data/*); count=${#files[@]}                               # with nullglob
```

- [ ] Any command **pasted into an interactive shell** that passes a glob as a flag value
      (`--include`, `--exclude`, `-name`) has it **quoted** — unquoted, zsh's `NOMATCH`
      aborts the command and, under `2>/dev/null`, the result is indistinguishable from a
      genuine no-match (`rules/06` §1). Every sweep read as an *absence* has been positive-controlled
      against a pattern known to be present.

## Audit checklist

- [ ] **Is any long-running script rewritten while it may be executing?** (§3d) A deploy that
      writes over `run.sh` with `cat >` while a cron job is mid-run, or an agent editing a
      harness it just started, makes the running process execute a splice of old and new.
      Write elsewhere and `mv` it into place.
- [ ] **Any hard link used to keep two paths in sync?** (§3c) It survives nothing that
      writes-and-renames — git, `mktemp`+`mv`, most editors and formatters — and the stale
      copy is a valid file with no broken link and no error. Directories cannot be hard-linked
      at all. Prefer a symlink: its failure is loud.
- [ ] **Any in-place sweep (`perl -pi`, `sed -i`) over a path list that could contain a
      symlink?** (§3b) Measured: **GNU sed, BusyBox sed and `perl -pi` all replace the link
      with a regular file at exit 0**, target untouched, the two copies then diverging. Only
      **BSD** sed refuses — so a macOS developer sees the safe behaviour and CI does not.
      Never rely on the refusal; enumerate regular files instead
      (`git ls-files -s | awk '$1=="100644"{print $4}'`, or `find -type f`), and remember
      `git status` reports this as `T`, not `M`.

- [ ] **Scripts that resolve their own root guard their entry point** (§3a) —
      `[[ ${BASH_SOURCE[0]} == "$0" ]] && main "$@"` — so a caller can source them to test one
      function without the script `cd`-ing itself somewhere else and failing every `git` call

- [ ] SC2046 (unquoted `$(...)`), SC2068 (unquoted `$@`/array), SC2048 (`$*`).
- [ ] SC2012/SC2045 — `grep -rn 'in \$(ls\|ls .*| *wc\|ls .*| *grep' --include='*.sh'`
- [ ] SC2162 — `grep -rn 'read [^-]' --include='*.sh'` (missing `-r`).
- [ ] Temp files: `grep -rn '/tmp/[a-zA-Z]\|\$\$' --include='*.sh'` — predictable names,
      `$$`-suffixed paths → HIGH (race), must be `mktemp`.
- [ ] Cleanup: every `mktemp` has a reachable `trap ... EXIT`; cleanup function is
      idempotent and preserves `$?`.
- [ ] `grep -rn 'echo .*\$' --include='*.sh'` — variable data through `echo` (SC2028 area);
      MEDIUM unless value is constrained.
- [ ] Glob loops without nullglob/failglob or `[[ -e $f ]]` guard.
