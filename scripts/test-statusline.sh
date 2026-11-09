#!/usr/bin/env bash
#
# Fixture tests for scripts/statusline.sh (2026-11-09).
#
# Synthetic payloads only — a captured real payload holds paths, session names and, on
# Antigravity, an email address, and this repository is public. Each case asserts the exact
# line or one specific property, so a regression fails for its own reason:
#   field mapping (Claude Code and Antigravity), plan-usage window choice and the ↑ rule,
#   cache countdown thresholds, hostile and wrongly typed payloads, terminal-escape
#   neutralisation (CWE-150), OSC 8 link encoding, width fitting, the worktree fallback,
#   the incremental skills cache, the context-window file guard, and the dump mode.
#
# Usage: scripts/test-statusline.sh            (uses `bash` from PATH)
#        STATUSLINE_BASH=/bin/bash scripts/test-statusline.sh   (macOS's bash 3.2)
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
SL="$PWD/scripts/statusline.sh"
SH="${STATUSLINE_BASH:-bash}"
NOW=1800000000
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
ESC=$'\033'
BEL=$'\007'

pass=0 fail=0
ok() { pass=$((pass + 1)); }
bad() {
  fail=$((fail + 1))
  printf 'FAIL: %s\n' "$1"
  [ $# -gt 1 ] && printf '      got: %q\n' "$2"
  return 0
}
# run <payload-json> [VAR=value ...] — fresh HOME, config and cache dirs per call
run() {
  local payload="$1"
  shift
  printf '%s' "$payload" | env -i PATH="$PATH" HOME="$T/home" CLAUDE_CONFIG_DIR="$T/home/.claude" \
    XDG_CACHE_HOME="$T/cache" SOTA_STATUSLINE_NOW="$NOW" "$@" "$SH" "$SL"
}
eq() { if [ "$2" = "$3" ]; then ok; else bad "$1 — want: $3" "$2"; fi; }
has() { case "$2" in *"$3"*) ok ;; *) bad "$1 — missing: $3" "$2" ;; esac; }
hasnt() { case "$2" in *"$3"*) bad "$1 — must not contain: $3" "$2" ;; *) ok ;; esac; }

mkdir -p "$T/home"
# A git repository named proj on branch main, with one linked worktree.
git init -q -b main "$T/proj"
git -C "$T/proj" -c user.email=t@example.invalid -c user.name=t commit -q --allow-empty -m init
git -C "$T/proj" worktree add -q -b feat "$T/proj-wt-feat"

base() { # base <cwd> — the full Claude Code shape
  jq -n --arg cwd "$1" --argjson now "$NOW" '{
    model: {id: "claude-opus-5-5", display_name: "Opus 5.5"},
    workspace: {current_dir: $cwd, project_dir: $cwd},
    context_window: {context_window_size: 1000000, used_percentage: 42},
    prompt_cache: {warm: true, ttl: "1h", expires_at: ($now + 720), recache_tokens_if_cold: 100000},
    rate_limits: {five_hour: {used_percentage: 73, resets_at: ($now + 6480)},
                  seven_day: {used_percentage: 41, resets_at: ($now + 300000)}}}'
}
FULL="$(base "$T/proj")"

# 1. Full Claude Code payload: every segment, the 5h window (closest to its limit) with ↑
#    (73% used, 64% of the window elapsed), 1h48m to reset, the cache at 12m.
out="$(run "$FULL" SOTA_STATUSLINE_PLAIN=1)"
eq "full payload" "$out" "Opus 5.5 │ ████░░░░░░ 42% │ cache 12m │ 5h 73%↑ 1h48m │ proj ⎇ main"
eq "context-window file written for Claude Code" "$(cut -d' ' -f1 "$T/home/.claude/sota-skills-data/context-window" 2>/dev/null)" "1000000"

# 2. An API-key user: no rate_limits, no prompt_cache. Nothing renders as null or ?.
out="$(run "$(printf '%s' "$FULL" | jq 'del(.rate_limits, .prompt_cache)')" SOTA_STATUSLINE_PLAIN=1)"
eq "no plan, no cache" "$out" "Opus 5.5 │ ████░░░░░░ 42% │ proj ⎇ main"

# 3. Only seven_day, used slower than the window elapses: no ↑ (the shape observed live).
out="$(run "$(printf '%s' "$FULL" | jq --argjson now "$NOW" '.rate_limits = {seven_day: {used_percentage: 27, resets_at: ($now + 147600)}}')" SOTA_STATUSLINE_PLAIN=1)"
has "seven_day only" "$out" "7d 27% 1d17h"
hasnt "seven_day only, no arrow" "$out" "↑"

# 4. Cache hidden when little is at stake, when expired, and when cold.
for mut in '.prompt_cache.recache_tokens_if_cold = 1000' '.prompt_cache.expires_at = (.prompt_cache.expires_at - 10000)' '.prompt_cache.warm = false'; do
  out="$(run "$(printf '%s' "$FULL" | jq "$mut")" SOTA_STATUSLINE_PLAIN=1)"
  hasnt "cache hidden ($mut)" "$out" "cache"
done
out="$(run "$(printf '%s' "$FULL" | jq '.prompt_cache.recache_tokens_if_cold = 1000')" SOTA_STATUSLINE_PLAIN=1 SOTA_STATUSLINE_CACHE_MIN_TOKENS=500)"
has "cache threshold is configurable" "$out" "cache 12m"

# 5. Empty, non-JSON and wrongly typed payloads: a line, exit 0, never a blank.
eq "empty object" "$(run '{}' SOTA_STATUSLINE_PLAIN=1)" "?"
out="$(run 'garbage' SOTA_STATUSLINE_PLAIN=1)" && rc=0 || rc=$?
eq "non-JSON exits 0" "$rc" "0"
has "non-JSON says so" "$out" "could not read"
eq "array payload" "$(run '[1,2]' SOTA_STATUSLINE_PLAIN=1)" "?"
out="$(run '{"model":"x","context_window":"y","prompt_cache":3,"rate_limits":[1],"quota":"q","worktree":7,"workspace":"w","cwd":5}' SOTA_STATUSLINE_PLAIN=1)"
eq "wrong types everywhere" "$out" "?"
out="$(run "$(printf '%s' "$FULL" | jq '.context_window.used_percentage = 1e308 | .rate_limits.five_hour.used_percentage = -5')" SOTA_STATUSLINE_PLAIN=1)"
has "percentages clamped high" "$out" "██████████ 100%"
has "percentages clamped low" "$out" "7d 41%"

# 6. Antigravity: quota buckets, and its window never recorded as Claude Code's.
rm -rf "$T/home/.claude"
AG="$(jq -n --arg cwd "$T/proj" '{product: "antigravity", model: {display_name: "Gemini"},
  workspace: {current_dir: $cwd}, context_window: {context_window_size: 2000000, used_percentage: 10},
  quota: {a: {remaining_fraction: 0.9, reset_in_seconds: 100}, b: {remaining_fraction: 0.25, reset_in_seconds: 3600},
          c: {remaining_fraction: 0.0, disabled: true}}}')"
out="$(run "$AG" SOTA_STATUSLINE_PLAIN=1)"
eq "antigravity" "$out" "Gemini │ █░░░░░░░░░ 10% │ quota 75% 1h0m │ proj ⎇ main"
if [ -e "$T/home/.claude/sota-skills-data/context-window" ]; then bad "antigravity wrote Claude Code's context-window file"; else ok; fi

# 7. Terminal-escape injection (CWE-150) through a repo name, the model name and a bidi
#    override, in colour mode: the hostile sequences are shown escaped, never emitted.
evil="$T/evil${ESC}[2J${ESC}]52;c;ZXZpbA==${BEL}x"
git init -q -b main "$evil"
p="$(base "$evil" | jq '.model.display_name = "M\u001b]0;pwned\u0007\u202eX\u007f"')"
out="$(run "$p")"
hasnt "no raw clear-screen" "$out" "${ESC}[2J"
hasnt "no raw OSC 52 clipboard write" "$out" "${ESC}]52"
hasnt "no raw title change" "$out" "${ESC}]0;"
has "clear-screen shown escaped" "$out" "^[[2J"
has "model control chars escaped, bidi replaced, DEL shown" "$out" "M^[]0;pwned^G?X^?"
has "link target percent-encoded" "$out" "%1B%5B2J"

# 8. Links and colour switches.
mkdir -p "$T/my proj"
out="$(run "$(base "$T/my proj")")"
has "OSC 8 link, encoded path" "$out" "${ESC}]8;;file://$(printf '%s' "$T" | jq -Rr 'split("/") | map(@uri) | join("/")')/my%20proj${BEL}my proj${ESC}]8;;${BEL}"
has "colour on by default" "$out" "${ESC}[33m"
out="$(run "$(base "$T/my proj")" SOTA_STATUSLINE_LINKS=0)"
hasnt "links off" "$out" "${ESC}]8"
out="$(run "$(base "$T/my proj")" NO_COLOR=1)"
hasnt "NO_COLOR: no colour" "$out" "${ESC}["
has "NO_COLOR: links kept" "$out" "${ESC}]8"
out="$(run "$(base "$T/my proj")" SOTA_STATUSLINE_PLAIN=1)"
hasnt "plain: no escape at all" "$out" "$ESC"

# 9. Width: drop from the lowest priority up; the model always stays.
out="$(run "$FULL" SOTA_STATUSLINE_PLAIN=1 COLUMNS=41)"
eq "COLUMNS=41 (exactly the three top segments)" "$out" "Opus 5.5 │ ████░░░░░░ 42% │ 5h 73%↑ 1h48m"
eq "COLUMNS=40 drops one more" "$(run "$FULL" SOTA_STATUSLINE_PLAIN=1 COLUMNS=40)" "Opus 5.5 │ ████░░░░░░ 42%"
eq "COLUMNS=5" "$(run "$FULL" SOTA_STATUSLINE_PLAIN=1 COLUMNS=5)" "Opus 5.5"
w="$(run "$FULL" SOTA_STATUSLINE_PLAIN=1 COLUMNS=60 | jq -Rr length)"
if [ "$w" -le 60 ]; then ok; else bad "COLUMNS=60 width" "$w"; fi
out="$(run "$(printf '%s' "$FULL" | jq '.terminal_width = 41')" SOTA_STATUSLINE_PLAIN=1)"
eq "terminal_width when COLUMNS unset" "$out" "Opus 5.5 │ ████░░░░░░ 42% │ 5h 73%↑ 1h48m"

# 10. Worktree: the git fallback names a linked worktree, the main checkout shows none,
#     and a host-sent name wins.
out="$(run "$(base "$T/proj-wt-feat")" SOTA_STATUSLINE_PLAIN=1)"
has "linked worktree" "$out" "proj ⎇ feat │ wt proj-wt-feat"
hasnt "main checkout: no worktree" "$(run "$FULL" SOTA_STATUSLINE_PLAIN=1)" "wt "
has "host worktree name" "$(run "$(printf '%s' "$FULL" | jq '.worktree = {name: "my-feature"}')" SOTA_STATUSLINE_PLAIN=1)" "wt my-feature"

# 11. Skills from the transcript: incremental, deduplicated, hostile names refused, and a
#     rewritten (shorter) transcript rescanned.
tr="$T/transcript.jsonl"
line() { printf '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"%s"}}]}}\n' "$1"; }
{ line sota-testing; line sota-testing; } >"$tr"
P="$(printf '%s' "$FULL" | jq --arg t "$tr" '.transcript_path = $t')"
has "skills from transcript" "$(run "$P" SOTA_STATUSLINE_PLAIN=1)" "skills▸ sota-testing (1)"
{ line 'sota-skills:sota-rust'; line 'x;rm -rf ~'; printf '%s\n' '{"name":"Skill","skill":"bad\u001bname"}'; } >>"$tr"
out="$(run "$P" SOTA_STATUSLINE_PLAIN=1)"
has "incremental scan adds the new skill" "$out" "skills▸ sota-testing, sota-skills:sota-rust (2)"
hasnt "hostile skill name refused" "$out" "rm -rf"
hasnt "escaped skill name refused" "$out" "bad"
cache_file="$(find "$T/cache/sota-skills-statusline" -type f ! -name '.tmp.*' | head -n 1)"
eq "cache records the bytes read" "$(sed -n 1p "$cache_file")" "$(wc -c <"$tr" | tr -d ' ')"
eq "cache dir is private" "$(find "$T/cache/sota-skills-statusline" -maxdepth 0 -perm 0700)" "$T/cache/sota-skills-statusline"
line sota-python >"$tr"
has "rewritten transcript rescanned" "$(run "$P" SOTA_STATUSLINE_PLAIN=1)" "skills▸ sota-python (1)"
echo garbage >"$cache_file"
has "corrupt cache ignored" "$(run "$P" SOTA_STATUSLINE_PLAIN=1)" "skills▸ sota-python (1)"
out="$(run "$P" SOTA_STATUSLINE_PLAIN=1 COLUMNS=85)"
has "narrow: skills shortened before dropped" "$out" "skills▸ 1 used"

# 12. Dump mode: private files, a visible indicator, and no write through a symlink.
mkdir -p "$T/dump"
out="$(run "$FULL" SOTA_STATUSLINE_PLAIN=1 SOTA_STATUSLINE_DUMP="$T/dump")"
has "dump indicator" "$out" "dump on"
f="$(find "$T/dump" -type f -name 'payload-*.json' | head -n 1)"
if [ -n "$f" ] && [ -n "$(find "$f" -maxdepth 0 -perm 0600)" ]; then ok; else bad "dump file missing or not 600" "$f"; fi
ln -s "$T/dump" "$T/dumplink"
before="$(find "$T/dump" -type f | wc -l | tr -d ' ')"
run "$FULL" SOTA_STATUSLINE_PLAIN=1 SOTA_STATUSLINE_DUMP="$T/dumplink" >/dev/null
eq "no dump through a symlinked dir" "$(find "$T/dump" -type f | wc -l | tr -d ' ')" "$before"

# 13. Scratchpad: shown when non-empty, hidden when empty, missing or relative.
mkdir -p "$T/scratch"
has_scr() { run "$(printf '%s' "$FULL" | jq --arg s "$1" '.scratchpad_dir = $s')" SOTA_STATUSLINE_PLAIN=1; }
hasnt "empty scratchpad hidden" "$(has_scr "$T/scratch")" "scratch"
touch "$T/scratch/notes.md"
has "non-empty scratchpad shown" "$(has_scr "$T/scratch")" "│ scratch"
# relative paths name directories that DO exist from the test's working directory (the
# repository root), so only the absolute-path guard can hide them
hasnt "relative scratchpad refused" "$(has_scr "scripts")" "scratch"
eq "relative cwd refused" "$(run '{"workspace":{"current_dir":"scripts"}}' SOTA_STATUSLINE_PLAIN=1)" "?"

# 14. Interactive use prints help instead of waiting on stdin; --help works.
has "--help" "$("$SH" "$SL" --help)" "SOTA_STATUSLINE_PLAIN"

total=$((pass + fail))
# shellcheck disable=SC2016  # $BASH_VERSION is meant to expand in the bash under test
printf 'statusline: %d/%d passed under %s (%s)\n' "$pass" "$total" "$SH" "$("$SH" -c 'echo "$BASH_VERSION"')"
[ "$fail" -eq 0 ]
