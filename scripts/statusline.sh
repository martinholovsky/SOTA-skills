#!/usr/bin/env bash
#
# statusline.sh — a Claude Code status line that shows which skills you've
# actually used this session (not just how many are installed).
#
#   model │ ctx NN% │ <dir> ⎇ <branch> │ skills▸ code-security, testing (2)
#
# How it works: Claude Code's status-line JSON doesn't expose loaded skills, but
# it does pass `transcript_path`. Each skill invocation is recorded there as a
# Skill tool call (`"name":"Skill" … "skill":"<name>"`), so we read them back.
# When nothing's been invoked yet, it falls back to the count of available skills.
#
# Cost: the transcript grows for the whole session (33 MB, 13,400 lines measured
# 2026-11-20), and re-reading it on every render cost 415 ms per render with BSD grep, which
# `cat` reads in 9 ms. So the scan is incremental: a per-transcript cache under
# $CLAUDE_CONFIG_DIR/sota-skills-data/statusline/ holds the byte offset already scanned and
# the skills found, and each render reads only the bytes appended since. Forks are kept
# down too (about 4 ms each on macOS): stdin and the cache are read with builtins.
#
# Untrusted input: the directory and branch names, the model name and the
# transcript can carry terminal control sequences (a cloned repository picks its
# own directory name). Every string is printed with C0/DEL/C1 control characters
# shown escaped (`^[`) and bidi / zero-width characters replaced (CWE-150,
# sota-cli-ux rules/02 §4); skill names must match [A-Za-z0-9:._-]; paths are used
# only when absolute; a wrongly typed payload still prints a line and exits 0.
#
# Wire it up — point settings.json at this script:
#   "statusLine": { "type": "command", "command": "/path/to/scripts/statusline.sh" }
#
# Requires: jq.
#
set -euo pipefail

# A builtin read: `$(</dev/stdin)` is reported to read empty under Claude Code's stdin
# pipe, `read -d ''` does not (it returns 1 at end of input, hence `|| true`).
input=""
IFS= read -r -d '' input || true

if ! command -v jq >/dev/null 2>&1; then
  printf 'statusline: jq not found — install it (e.g. brew install jq)\n'
  exit 0
fi

# One jq pass extracts every field, joined by a unit separator (0x1F) so `read` keeps
# empty fields. A 0x1F or newline inside a value is removed first, so a hostile value
# cannot shift the fields after it, and every optional access has a `// fallback`: on a
# wrong type `x?` yields nothing, which would drop its slot and shift the rest
# (measured on jq 1.7.1 and 1.8.2). A non-object payload makes jq fail outright, and the
# line falls back to "?".
IFS=$'\037' read -r model ctx cwd transcript ctxsize product <<EOF || true
$(printf '%s' "$input" | jq -r '
  def f: if type == "string" then gsub("[\\x{001f}\\n\\r]"; "") else "" end;
  [ (.model.display_name? // .model.id? // "?" | f),
      (.context_window.used_percentage? // null | if type == "number" and . >= 0 and . <= 100 then floor | tostring else "" end),
      (.workspace.current_dir? // .cwd | f),
      (.transcript_path | f),
      (.context_window.context_window_size? // null | if type == "number" and . > 0 and . < 1e9 then floor | tostring else "" end),
      (.product | f)
    ] | join([31] | implode)' 2>/dev/null || true)
EOF
[ -n "$model" ] || model="?"

# Paths are used only when absolute: a relative or option-shaped value never reaches
# git, find or a file test.
case "$cwd" in /*) ;; *) cwd="" ;; esac
case "$transcript" in /*) ;; *) transcript="" ;; esac

# Remember the context window this machine actually runs. Nothing outside a live
# session can know it: the SessionStart hook gets a model id at most, the installer and
# verify-setup get nothing, and a model string cannot rule 1M OUT (Sonnet 5+, Opus 4.7+
# and Fable run 1M natively with no `[1m]` suffix — code.claude.com/docs/en/model-config).
# The status line is the one place Claude Code hands over the exact number, so the
# skill-listing budget checks read it back from here. Written only when it changes, and
# never allowed to fail the line. Claude Code sends no `product` field; another host
# that does (Antigravity CLI sends "antigravity") must not have its window recorded as
# Claude Code's.
if [ -z "$product" ]; then
  case "$ctxsize" in
    '' | *[!0-9]*) ;;
    *)
      cw_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sota-skills-data"
      cw_file="$cw_dir/context-window"
      cw_have=""
      if [ -f "$cw_file" ]; then read -r cw_have _ <"$cw_file" 2>/dev/null || true; fi
      if [ "$cw_have" != "$ctxsize" ]; then
        { mkdir -p "$cw_dir" && printf '%s %s\n' "$ctxsize" "$(date +%s)" >"$cw_file"; } 2>/dev/null || true
      fi
      ;;
  esac
fi

# current branch (best-effort; never fail the line on it)
branch=""
if [ -n "$cwd" ] && [ -d "$cwd" ]; then
  branch="$(GIT_OPTIONAL_LOCKS=0 git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
fi

# skills used this session = distinct Skill tool invocations in the transcript. The
# transcript holds model and tool output, so a name is accepted only if it matches the
# skill-name alphabet, both when it is read from the transcript and from the cache.
skills=""
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
  sc_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sota-skills-data/statusline"
  sc_key="${transcript//[!A-Za-z0-9._-]/_}"
  [ "${#sc_key}" -le 200 ] || sc_key="${sc_key:$((${#sc_key} - 200))}"
  sc_file="$sc_dir/$sc_key"
  off=0 used=""
  if [ -f "$sc_file" ]; then
    { read -r off && read -r used; } <"$sc_file" 2>/dev/null || true
  fi
  # A cache that is not exactly "<digits>" then "<name>,<name>…" is discarded: rescan.
  case "$off" in '' | *[!0-9]*) off=0 used="" ;; esac
  case "$used" in *[!A-Za-z0-9:._,-]*) off=0 used="" ;; esac
  size="$(wc -c <"$transcript" 2>/dev/null || true)"
  size="${size//[!0-9]/}"
  [ -n "$size" ] || size=0
  # Smaller than the offset: the file was replaced or truncated, so start again.
  if [ "$size" -lt "$off" ]; then off=0 used=""; fi
  # Scan from off, and only when byte size-1 is a newline: the writer may be in the middle
  # of a line, and a Skill record split across two renders would be lost. Bytes are
  # skipped with a seek on the shared descriptor (dd skip, count=0), not `tail -c +N`,
  # which BSD tail ran in 2.2 s on the 33 MB transcript against 16 ms for the seek. Bytes
  # appended after `size` was read are scanned now and again next time: names are
  # de-duplicated, so a re-read is harmless and only a skipped byte would not be.
  if [ "$size" -gt "$off" ] &&
    [ -z "$({ dd bs=1 skip="$((size - 1))" count=0 2>/dev/null && head -c 1; } <"$transcript" 2>/dev/null)" ]; then
    new="$({ dd bs=1 skip="$off" count=0 2>/dev/null && cat; } <"$transcript" 2>/dev/null |
      LC_ALL=C grep -F '"name":"Skill"' |
      LC_ALL=C grep -o '"skill":"[A-Za-z0-9:._-]\{1,64\}"' |
      sed 's/.*:"//; s/"$//' || true)"
    for s in $new; do
      case ",$used," in *",$s,"*) ;; *) used="${used:+$used,}$s" ;; esac
    done
    off="$size"
    { [ -d "$sc_dir" ] || mkdir -p "$sc_dir"; } 2>/dev/null || true
    { printf '%s\n%s\n' "$off" "$used" >"$sc_file.$$" && mv -f "$sc_file.$$" "$sc_file"; } 2>/dev/null || true
  fi
  if [ -n "$used" ]; then
    n=0 list=""
    old_ifs="$IFS"
    IFS=,
    for s in $used; do
      n=$((n + 1))
      list="${list:+$list, }$s"
    done
    IFS="$old_ifs"
    skills="skills▸ ${list} (${n})"
  fi
fi
# fallback: count of installed skills
if [ -z "$skills" ]; then
  for d in "${cwd:-/nonexistent}/.claude/skills" "$HOME/.claude/skills"; do
    if [ -d "$d" ]; then
      # -L so symlinked skill dirs (how install.sh links them) are followed
      avail="$(find -L "$d" -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')"
      [ "$avail" -gt 0 ] && {
        skills="skills▸ ${avail} available"
        break
      }
    fi
  done
fi

# Assemble in jq so every untrusted string passes through one neutraliser; data reaches
# jq only through --arg. Oniguruma reads code points in a pattern as \x{HHHH}, never as
# backslash-u escapes, which it reads as other text (measured on jq 1.7.1 and 1.8.2).
jq -nr --arg model "$model" --arg ctx "$ctx" --arg dir "${cwd##*/}" --arg branch "$branch" \
  --arg skills "$skills" '
  def clean:
    gsub("\\x{007f}"; "^?")
    | gsub("(?<c>[\\x{0000}-\\x{001f}])"; "^" + ([(.c | explode[0]) + 64] | implode))
    | gsub("[\\x{0080}-\\x{009f}\\x{200b}-\\x{200f}\\x{2028}-\\x{202e}\\x{2060}-\\x{2069}\\x{feff}]"; "?");
  [ ($model | clean),
    (if $ctx != "" then "ctx \($ctx)%" else empty end),
    (if $dir != "" then ($dir | clean) + (if $branch != "" then " ⎇ " + ($branch | clean) else "" end) else empty end),
    (if $skills != "" then ($skills | clean) else empty end)
  ] | join(" │ ")' 2>/dev/null || printf '%s\n' "?"
