# 05 — Constructs & Cleanup: arrays, IFS, traps, tests, globbing

Scope: the constructs a script is assembled from, and the way each of them fails. Split out
of `rules/01` at v1.36.4, which keeps the safety baseline — shebang, `set -e` semantics,
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
      genuine no-match (`rules/01` §3a). Every sweep read as an *absence* has been positive-controlled
      against a pattern known to be present.

## Audit checklist

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
