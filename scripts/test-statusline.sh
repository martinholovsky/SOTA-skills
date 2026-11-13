#!/usr/bin/env bash
#
# Fixture tests for scripts/statusline.sh (2026-11-10).
#
# The script is in maintenance mode (docs/ROADMAP.md: bug-fix only), so these pin the
# fixes and the unchanged output format:
#   - the line is byte-identical to the previous script on ordinary payloads;
#   - untrusted text (directory, branch, model, transcript) cannot emit a terminal escape
#     (CWE-150): control characters are shown escaped, bidi / zero-width replaced;
#   - a wrongly typed or non-JSON payload prints a line and exits 0, and cannot shift the
#     extracted fields;
#   - a host that sends `product` (Antigravity CLI) never writes Claude Code's
#     context-window file;
#   - skill names outside [A-Za-z0-9:._-] are refused; relative paths are ignored.
# Hostile characters are built at run time (printf octal, jq implode), never typed into
# this file, which stays ASCII apart from the status line's own separators.
#
# Usage: scripts/test-statusline.sh                          (bash from PATH)
#        STATUSLINE_BASH=/bin/bash scripts/test-statusline.sh (macOS's bash 3.2)
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
SL="$PWD/scripts/statusline.sh"
SH="${STATUSLINE_BASH:-bash}"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
ESC=$(printf '\033')
BEL=$(printf '\007')
RLO=$(printf '\342\200\256')

pass=0 fail=0
ok() { pass=$((pass + 1)); }
bad() {
  fail=$((fail + 1))
  printf 'FAIL: %s\n' "$1"
  [ $# -gt 1 ] && printf '      got: %q\n' "$2"
  return 0
}
run() { # run <payload> [VAR=value ...] — fresh HOME and config per call
  local payload="$1"
  shift
  printf '%s' "$payload" | env -i PATH="$PATH" HOME="$T/home" CLAUDE_CONFIG_DIR="$T/home/.claude" "$@" "$SH" "$SL"
}
eq() { if [ "$2" = "$3" ]; then ok; else bad "$1 — want: $3" "$2"; fi; }
has() { case "$2" in *"$3"*) ok ;; *) bad "$1 — missing: $3" "$2" ;; esac }
hasnt() { case "$2" in *"$3"*) bad "$1 — must not contain: $3" "$2" ;; *) ok ;; esac }

mkdir -p "$T/home"
git init -q -b main "$T/proj"
git -C "$T/proj" -c user.email=t@example.invalid -c user.name=t commit -q --allow-empty -m init

base() { # base <cwd> [transcript]
  jq -n --arg cwd "$1" --arg tr "${2:-}" '{model: {display_name: "Opus 5.5"},
    workspace: {current_dir: $cwd}, transcript_path: $tr,
    context_window: {context_window_size: 1000000, used_percentage: 42}}'
}
FULL="$(base "$T/proj")"

# 1. The format is unchanged, and the context window is recorded for Claude Code.
eq "ordinary payload" "$(run "$FULL")" "Opus 5.5 │ ctx 42% │ proj ⎇ main"
eq "context-window file written" "$(cut -d' ' -f1 "$T/home/.claude/sota-skills-data/context-window")" "1000000"

# 2. Differential against the script as it was before these fixes (the merge base), on
#    ordinary payloads: the output must be byte-identical.
base_ref="$(git merge-base HEAD origin/main 2>/dev/null || true)"
if [ -n "$base_ref" ] && git show "$base_ref:scripts/statusline.sh" >"$T/old.sh" 2>/dev/null; then
  tr="$T/t.jsonl"
  printf '%s\n' '{"message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"sota-testing"}}]}}' >"$tr"
  for p in "$FULL" "$(base "$T/proj" "$tr")" '{"model":{"id":"m"}}' "$(base "$T/proj" | jq 'del(.context_window)')"; do
    new="$(run "$p")"
    old="$(printf '%s' "$p" | env -i PATH="$PATH" HOME="$T/home" CLAUDE_CONFIG_DIR="$T/home/.claude" "$SH" "$T/old.sh")"
    eq "same as before on: $(printf '%s' "$p" | jq -c 'keys')" "$new" "$old"
  done
else
  bad "no base commit to diff against (fetch origin/main)"
fi

# 3. Terminal-escape injection (CWE-150) through the directory and the model name:
#    nothing hostile is emitted raw; it is shown escaped.
evil="$T/evil${ESC}[2J${ESC}]52;c;ZXZpbA==${BEL}x"
git init -q -b main "$evil"
p="$(base "$evil" | jq '.model.display_name = "M" + ([27] | implode) + "]0;pwned" + ([7, 8238, 127] | implode) + "X"')"
out="$(run "$p")"
hasnt "no ESC byte at all (the script prints no styling)" "$out" "$ESC"
hasnt "no raw RLO" "$out" "$RLO"
has "directory shown escaped" "$out" "evil^[[2J^[]52;c;ZXZpbA==^Gx"
has "model: controls escaped, bidi replaced, DEL shown" "$out" "M^[]0;pwned^G?^?X"

# 4. Wrongly typed and non-JSON payloads: a line, exit 0, never a blank.
eq "empty object" "$(run '{}')" "?"
eq "array payload" "$(run '[1,2]')" "?"
out="$(run 'garbage')" && rc=0 || rc=$?
eq "non-JSON exits 0" "$rc" "0"
eq "non-JSON prints a line" "$out" "?"
eq "wrong types everywhere" "$(run '{"model":"x","context_window":"y","workspace":"w","cwd":5,"transcript_path":[1]}')" "?"
# A wrongly typed context_window must not shift the directory into the ctx slot.
eq "wrong-typed field does not shift the others" "$(run "$(base "$T/proj" | jq '.context_window = "x"')")" "Opus 5.5 │ proj ⎇ main"
eq "percentage out of range dropped" "$(run "$(printf '%s' "$FULL" | jq '.context_window.used_percentage = 1e308')")" "Opus 5.5 │ proj ⎇ main"

# 5. The context-window guard: a host that sends `product` never writes Claude Code's file,
#    including when a wrongly typed field precedes `product` (a field shift would have
#    moved "antigravity" out of its slot and let the write through).
rm -rf "$T/home/.claude"
run '{"product":"antigravity","context_window":{"context_window_size":2000000}}' >/dev/null
run '{"context_window":"x","product":"antigravity"}' >/dev/null
run '{"model":3,"context_window":{"context_window_size":2000000,"used_percentage":"x"},"product":"antigravity"}' >/dev/null
if [ -e "$T/home/.claude/sota-skills-data/context-window" ]; then bad "a product-bearing host wrote Claude Code's context-window file"; else ok; fi

# 6. Skill names from the transcript: the allow-list refuses anything else.
tr="$T/hostile.jsonl"
{
  printf '%s\n' '{"name":"Skill","input":{"skill":"sota-skills:sota-rust"}}'
  printf '%s\n' '{"name":"Skill","input":{"skill":"x;rm -rf ~"}}'
  printf '{"name":"Skill","input":{"skill":"bad%sname"}}\n' "$ESC"
} >"$tr"
out="$(run "$(base "$T/proj" "$tr")")"
has "allowed skill listed" "$out" "skills▸ sota-skills:sota-rust (1)"
hasnt "shell metacharacters refused" "$out" "rm -rf"
hasnt "escape-bearing name refused" "$out" "bad"

# 7. Relative paths are ignored (each names a path that DOES exist from the repository
#    root, so only the guard can hide it).
eq "relative cwd ignored" "$(run '{"workspace":{"current_dir":"scripts"}}')" "?"
out="$(run "$(base "$T/proj" "scripts/test-statusline.sh")")"
hasnt "relative transcript ignored" "$out" "skills▸"

total=$((pass + fail))
# shellcheck disable=SC2016  # $BASH_VERSION is meant to expand in the bash under test
printf 'statusline: %d/%d passed under %s (%s)\n' "$pass" "$total" "$SH" "$("$SH" -c 'echo "$BASH_VERSION"')"
[ "$fail" -eq 0 ]
