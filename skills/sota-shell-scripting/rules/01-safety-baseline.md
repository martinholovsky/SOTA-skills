# 01 — Safety Baseline

The preamble, quoting, and cleanup discipline every bash script gets before any logic.

## 1. Shebang discipline

- Use `#!/usr/bin/env bash` for bash scripts. `/bin/bash` is absent on NixOS/some BSDs, and
  on macOS `/bin/bash` is frozen at 3.2 (GPLv2) while users install modern bash (5.x) via
  Homebrew on PATH — `env` finds it. macOS's *default interactive shell* is zsh; scripts
  must not assume the login shell.
- Use `#!/bin/sh` **only** when you commit to strict POSIX (and verify with
  `shellcheck -s sh`). `sh` is dash on Debian/Ubuntu and busybox ash in minimal containers:
  no arrays, no `[[ ]]`, no `local` guarantees beyond common practice, no `pipefail`
  (until very recent POSIX-2024-aligned shells), no `${var//pat/rep}`.
- Never mix: a `#!/bin/sh` script containing bashisms is a time bomb that detonates on the
  first dash/busybox host. SC2039/SC3xxx-series catch these.
- If the script needs bash ≥4 features (associative arrays, `mapfile`, `${var,,}`), guard:

```bash
(( BASH_VERSINFO[0] >= 4 )) || { printf '%s: requires bash >= 4\n' "${0##*/}" >&2; exit 1; }
```

## 2. The preamble and what `set -e` actually does

```bash
#!/usr/bin/env bash
set -euo pipefail
```

- `-e` exit on command failure, `-u` error on unset variable expansion, `-o pipefail` a
  pipeline fails if any element fails (not just the last).
- Optionally `shopt -s inherit_errexit` (bash ≥4.4): makes command substitutions inherit
  `-e`; without it, `var=$(false; echo ok)` succeeds silently.
- bash ≥5.3 adds `${ cmd; }` — command substitution run *in the current shell* (no
  subshell/fork): assignments, `cd`, and `shopt` changes inside **persist** in the parent,
  unlike `$(cmd)`. The `-e`-masking rules here apply to it unchanged (`inherit_errexit`
  covers both forms). Guard it as a bash ≥5.3-only feature (§1).

**Where `set -e` does NOT fire — memorize this list; each is a real bug class:**

| Context | Behavior |
|---|---|
| Command tested by `if`/`while`/`until` | `-e` suspended for the whole command, including functions it calls |
| Left of `&&` / `||` | suspended — `cmd && other` swallows `cmd` failure |
| Any command in a function *called from* a condition | `-e` is off inside the entire call tree |
| `local var=$(cmd)` / `export var=$(cmd)` | exit status of `cmd` is masked by `local`/`export` (SC2155) |
| Pipeline without `pipefail` | only last element's status counts |
| Command substitution in a larger command | `echo "$(false)"` succeeds |
| Subshell `(exit 1) || true` patterns, `! cmd` | negation makes failure "expected" |

Consequences:

```bash
# BAD — set -e is OFF inside check_all because it's in an if-condition;
# every failure inside it is silently ignored
if check_all; then deploy; fi

# BAD — SC2155: rev is always assigned, git failure masked
local rev=$(git rev-parse HEAD)

# GOOD — separate declaration from command substitution
local rev
rev=$(git rev-parse HEAD)

# GOOD — when you need a command's status without -e killing the script:
status=0
risky_command || status=$?
if (( status != 0 )); then
  printf '%s: risky_command failed with %d\n' "${0##*/}" "$status" >&2
  exit "$status"
fi
```

Rule: treat `set -e` as a backstop, not error handling. Critical steps get explicit
`|| { err "..."; exit 1; }` or status capture.

## 3. Quoting: quote every expansion (SC2086)

Unquoted expansions undergo word splitting (on `$IFS`) **and** glob expansion. This is the
single largest shell bug class.

```bash
# BAD — splits on spaces, expands *, ?, [ in the value
rm -rf $build_dir/$target      # build_dir="my project" → rm -rf my project/...
cp $files $dest                # files="a b" is two args; files="*" globs

# GOOD
rm -rf -- "$build_dir/$target"
cp -- "$files" "$dest"
```

Word-splitting bug catalog — all are bugs, not style:

```bash
[ -f $path ]                 # path with space → "[: too many arguments"
for f in $(ls); do ...       # splits on whitespace, globs results (SC2045/SC2012)
echo $(<file)                # collapses runs of whitespace, expands globs in content
ssh host rm $file            # double expansion: once locally, once remotely
args="--opt val"; cmd $args  # works until val has a space — use an array
return $?                    # fine — but `exit $code` with code="" under -u errors; quote anyway
curl -H $auth_header ...     # header with space splits into garbage args
```

- `"$@"` not `$*` and not `"$*"` to forward arguments — `"$@"` preserves each argument as
  one word. `"$*"` joins into a single word (legit only for display strings).
- `"${arr[@]}"` for arrays, same logic.
- The only sanctioned unquoted expansions: inside `[[ ]]` (no splitting there — but quote
  the *right-hand side* of `==`/`=~` deliberately: unquoted RHS is a pattern, quoted is
  literal), and arithmetic `$(( ))`.

## 4. Arrays for command building (SC2089/SC2090/SC2086)

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

## 5. IFS handling

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

## 6. trap-based cleanup and mktemp

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

## 7. Test constructs, printf, declarations

- `[[ ]]` over `[ ]` in bash: no word splitting of unquoted vars, `&&`/`||` inside,
  `=~` regex, `<`/`>` string comparison without escaping. Use `[ ]` only in POSIX `sh`.
- Arithmetic: `(( count > 3 ))`, not `[ $count -gt 3 ]`. But beware `(( x ))` returns
  nonzero when x=0 — under `set -e`, `(( count++ ))` with count=0 kills the script;
  write `(( ++count ))` or `count=$((count + 1))`.
- `printf` over `echo` for any variable data: `echo` behavior with `-n`, `-e`, and
  backslashes is implementation-defined (dash interprets escapes by default; a variable
  that *is* `-n` vanishes). `printf '%s\n' "$var"` is exact (SC2028 hints at this).
- `local` for every function variable (SC2034 finds unused leaks); remember the SC2155
  split-declaration rule from §2.
- `readonly` (or `declare -r`) for constants and config resolved at startup — catches
  accidental reassignment at the point of the bug:

```bash
readonly SCRIPT_NAME=${0##*/}
readonly DEFAULT_REGION=${REGION:-eu-central-1}
```

## 8. Globbing pitfalls and never parsing ls

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

## Audit checklist

Run `shellcheck -S style` first; then hunt manually:

- [ ] `grep -rn '^#!/bin/sh' scripts/` then scan those files for `[[`, arrays, `local -`,
      `${var//`, `pipefail` → bashism-in-sh (SC3xxx series).
- [ ] Missing preamble: `grep -rLn 'set -euo pipefail\|set -eu' --include='*.sh' .`
- [ ] SC2086 (unquoted expansion) — treat every instance in a destructive command
      (`rm`, `mv`, `cp`, `chmod`, `chown`, `ssh`, `kill`) as HIGH.
- [ ] SC2155 — `grep -rn 'local [a-zA-Z_]*=\$(' --include='*.sh'` (masked exit status).
- [ ] `set -e` false confidence: grep for `if .*&&\|if [a-z_]*;` over functions with
      critical side effects; check `$(...)` in assignments without `inherit_errexit`.
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
