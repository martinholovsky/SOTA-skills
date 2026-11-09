#!/usr/bin/env bash
#
# statusline.sh — a status line for Claude Code and Antigravity CLI that shows the
# model, context, prompt-cache countdown, plan usage, project, worktree and which
# skills you have actually used this session.
#
#   Opus 5.5 │ ███░░░░░░░ 32% │ cache 12m │ 5h 73%↑ 1h48m │ my-service ⎇ main │ wt fix-x │ scratch │ skills▸ testing (1)
#
# Each segment appears only when its data is present, and segments are dropped from the
# lowest priority up when the line is wider than the terminal. Wire it up:
#
#   Claude Code    ~/.claude/settings.json
#     "statusLine": { "type": "command", "command": "/path/to/scripts/statusline.sh", "refreshInterval": 30 }
#   Antigravity    ~/.gemini/antigravity-cli/settings.json
#     "statusLine": { "type": "command", "command": "/path/to/scripts/statusline.sh" }
#
# refreshInterval is optional; without it the cache countdown only moves when Claude Code
# redraws on an event. Environment (all optional):
#   SOTA_STATUSLINE_PLAIN=1            no colour, no links (Terminal.app, tmux over SSH, odd fonts)
#   NO_COLOR=<anything>                no colour (https://no-color.org)
#   SOTA_STATUSLINE_LINKS=0            no OSC 8 links
#   SOTA_STATUSLINE_CACHE_MIN_TOKENS=N hide the cache countdown when a cold cache would
#                                      re-send fewer than N tokens (default 50000)
#   SOTA_STATUSLINE_DUMP=<dir>         write every payload received into <dir> (mode 600),
#                                      to map a new host's fields. The payloads hold paths,
#                                      session names and, on Antigravity, your email: never
#                                      commit them. The line shows "dump on" while it is set.
#
# Security: every string from the payload, git or the transcript is treated as untrusted.
# Control characters (C0, DEL, C1) are escaped visibly and bidi / zero-width characters
# replaced before anything is printed (CWE-150; sota-cli-ux rules/02 §4), our own colours
# and links are added afterwards, link targets are percent-encoded, numbers are
# type-checked and clamped, and data reaches jq only through --arg, never the program text.
#
# Requires: bash (3.2+), jq. Exit status is always 0: a non-zero exit blanks the line in
# Claude Code and, after 30 in a row, disables it in Antigravity.
set -euo pipefail

usage() {
  awk 'NR > 2 && /^set -euo/ { exit } NR > 2 { sub(/^# ?/, ""); print }' "$0"
}
case "${1:-}" in
  -h | --help)
    usage
    exit 0
    ;;
esac
if [ -t 0 ]; then
  usage
  exit 0
fi

input="$(cat)"

if ! command -v jq >/dev/null 2>&1; then
  printf 'statusline: jq not found — install it (e.g. brew install jq)\n'
  exit 0
fi

# Never let git take locks or prompt from a status line.
export GIT_OPTIONAL_LOCKS=0 GIT_TERMINAL_PROMPT=0

# Pass 1: the few fields bash needs to act on (paths, sizes). Joined by a unit separator
# (0x1F) so `read` keeps empty fields; any 0x1F or newline inside a value is stripped first,
# so a hostile value cannot shift the fields after it.
IFS=$'\037' read -r cwd transcript ctxsize product scratch <<EOF || true
$(printf '%s' "$input" | jq -r '
  def f: if type == "string" then gsub("[\\x{001f}\\n\\r]"; "") else "" end;
  (if type == "object" then . else {} end)
  | [ (.workspace.current_dir? // .cwd | f),
      (.transcript_path | f),
      (.context_window.context_window_size? // null | if type == "number" and . > 0 and . < 1e9 then floor | tostring else "" end),
      (.product | f),
      (.scratchpad_dir | f)
    ] | join("\u001f")' 2>/dev/null || true)
EOF

# Paths are only used when absolute: a relative or option-shaped value ("-x") never reaches
# git, find or a file test.
abs() { case "$1" in /*) printf '%s' "$1" ;; *) printf '' ;; esac }
cwd="$(abs "$cwd")"
transcript="$(abs "$transcript")"
scratch="$(abs "$scratch")"

# Remember the context window this machine actually runs. Nothing outside a live session
# can know it: the SessionStart hook gets a model id at most, the installer and verify-setup
# get nothing, and a model string cannot rule 1M OUT (Sonnet 5+, Opus 4.7+ and Fable run 1M
# natively with no `[1m]` suffix — code.claude.com/docs/en/model-config). The status line is
# the one place Claude Code hands over the exact number, so the skill-listing budget checks
# read it back from here. Claude Code sends no `product` field; Antigravity sends
# "antigravity", and its window must never be recorded as Claude Code's.
if [ -z "$product" ]; then
  case "$ctxsize" in
    '' | *[!0-9]*) ;;
    *)
      cw_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sota-skills-data"
      cw_file="$cw_dir/context-window"
      if [ "$(cut -d' ' -f1 "$cw_file" 2>/dev/null || true)" != "$ctxsize" ]; then
        { mkdir -p "$cw_dir" && printf '%s %s\n' "$ctxsize" "$(date +%s)" >"$cw_file"; } 2>/dev/null || true
      fi
      ;;
  esac
fi

# Opt-in payload capture, for mapping a host whose schema is not published.
dump=""
if [ -n "${SOTA_STATUSLINE_DUMP:-}" ]; then
  dump=1
  if [ -d "$SOTA_STATUSLINE_DUMP" ] && [ ! -L "$SOTA_STATUSLINE_DUMP" ]; then
    (
      umask 077
      set -C # never follow or overwrite an existing name
      printf '%s\n' "$input" >"$SOTA_STATUSLINE_DUMP/payload-$(date +%s)-$$.json"
    ) 2>/dev/null || true
  fi
fi

# Git: branch, the repository's name, and whether this is a linked worktree. One rev-parse,
# no `git status` (which can run a repository-configured fsmonitor hook).
branch="" project="" wt=""
if [ -n "$cwd" ] && [ -d "$cwd" ]; then
  project="${cwd##*/}"
  gitinfo="$(git -C "$cwd" rev-parse --path-format=absolute --git-dir --git-common-dir --show-toplevel 2>/dev/null || true)"
  if [ -n "$gitinfo" ]; then
    gitdir="$(printf '%s\n' "$gitinfo" | sed -n 1p)"
    common="$(printf '%s\n' "$gitinfo" | sed -n 2p)"
    top="$(printf '%s\n' "$gitinfo" | sed -n 3p)"
    branch="$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    case "$common" in
      */.git)
        main="${common%/.git}"
        project="${main##*/}"
        ;;
      *) [ -n "$top" ] && project="${top##*/}" ;;
    esac
    if [ -n "$gitdir" ] && [ "$gitdir" != "$common" ] && [ -n "$top" ]; then
      wt="${top##*/}"
    fi
  fi
fi

# Scratchpad: shown only when the directory exists and is not empty. `scratchpad_dir` is
# sent by Claude Code but not in its documented schema (observed 2026-11-09, v2.1.321), so
# the segment simply disappears if it stops arriving.
scratch_ok=""
if [ -n "$scratch" ] && [ -d "$scratch" ] && [ ! -L "$scratch" ]; then
  [ -n "$(find "$scratch" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null || true)" ] && scratch_ok=1
fi

# Skills used this session = distinct Skill tool invocations in the transcript. The scan is
# incremental: a per-transcript cache keeps the byte offset already read, so a 40 MB
# transcript (measured 0.46 s for a full scan) costs only its new tail on each refresh. The
# re-read starts 64 KiB early so a line that was half-written last time is seen whole.
# The transcript holds model and tool output, so each name is re-validated below and in jq.
skill_names() {
  LC_ALL=C grep -F '"name":"Skill"' |
    LC_ALL=C grep -o '"skill":"[A-Za-z0-9:._-]\{1,64\}"' |
    sed 's/^"skill":"//; s/"$//' || true
}
used=""
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
  size="$(wc -c <"$transcript" 2>/dev/null | tr -d ' ' || true)"
  case "$size" in '' | *[!0-9]*) size=0 ;; esac
  cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/sota-skills-statusline"
  key="$(printf '%s' "$transcript" | cksum | cut -d' ' -f1)"
  cache="$cache_dir/$key"
  off=0 prev=""
  if [ -f "$cache" ] && [ ! -L "$cache" ]; then
    off="$(sed -n 1p "$cache" 2>/dev/null || true)"
    prev="$(sed -n '2,$p' "$cache" 2>/dev/null | LC_ALL=C grep -x '[A-Za-z0-9:._-]\{1,64\}' || true)"
  fi
  case "$off" in '' | *[!0-9]*) off=0 prev="" ;; esac
  if [ "$size" -lt "$off" ]; then off=0 prev=""; fi # rewritten or truncated: rescan
  if [ "$size" -gt "$off" ] || [ ! -f "$cache" ]; then
    start=$((off > 65536 ? off - 65536 : 0))
    new="$(tail -c +"$((start + 1))" "$transcript" 2>/dev/null | skill_names)"
    used="$(printf '%s\n%s\n' "$prev" "$new" | awk 'NF && !seen[$0]++')"
    tmp=""
    trap 'rm -f "$tmp"' EXIT
    trap 'exit 143' TERM INT
    if (umask 077 && mkdir -p "$cache_dir") 2>/dev/null &&
      tmp="$(mktemp "$cache_dir/.tmp.XXXXXX" 2>/dev/null)"; then
      if {
        printf '%s\n' "$size"
        if [ -n "$used" ]; then printf '%s\n' "$used"; fi
      } >"$tmp" 2>/dev/null &&
        mv -f "$tmp" "$cache" 2>/dev/null; then
        tmp=""
      else
        rm -f "$tmp"
      fi
    fi
  else
    used="$prev"
  fi
fi
skills="" skills_short=""
if [ -n "$used" ]; then
  n="$(printf '%s\n' "$used" | grep -c . || true)"
  skills="$(printf '%s\n' "$used" | head -n 8 | paste -sd, - | sed 's/,/, /g')"
  [ "$n" -gt 8 ] && skills="$skills, …"
  skills="$skills ($n)"
  skills_short="$n used"
else
  # fallback: count of installed skills, in the directories this host reads
  if [ "$product" = antigravity ]; then
    set -- "$HOME/.gemini/antigravity-cli/skills" "$HOME/.gemini/config/skills" "$HOME/.agents/skills"
  else
    set -- "${cwd:-/nonexistent}/.claude/skills" "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills"
  fi
  for d in "$@"; do
    if [ -d "$d" ]; then
      # -L so symlinked skill dirs (how install.sh links them) are followed
      avail="$(find -L "$d" -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')"
      if [ "$avail" -gt 0 ]; then
        skills="$avail available"
        skills_short="$skills"
        break
      fi
    fi
  done
fi

scratch_arg=""
if [ -n "$scratch_ok" ]; then scratch_arg="$scratch"; fi

color=1 links=1
if [ -n "${NO_COLOR:-}" ]; then color=""; fi
if [ "${SOTA_STATUSLINE_LINKS:-1}" = 0 ]; then links=""; fi
if [ "${SOTA_STATUSLINE_PLAIN:-}" = 1 ]; then color="" links=""; fi

# Pass 2: everything else, rendered in one jq program. Data arrives only through --arg.
printf '%s' "$input" | jq -r \
  --arg cwd "$cwd" --arg branch "$branch" --arg project "$project" --arg wt "$wt" \
  --arg scratch "$scratch_arg" \
  --arg skills "$skills" --arg skills_short "$skills_short" --arg dump "$dump" \
  --arg color "$color" --arg links "$links" --arg cols "${COLUMNS:-}" \
  --arg cachemin "${SOTA_STATUSLINE_CACHE_MIN_TOKENS:-50000}" \
  --arg nowarg "${SOTA_STATUSLINE_NOW:-}" '
  # --- untrusted text: escape controls visibly, replace invisible/bidi, cap length ---
  def clean($max):
    if type == "string" or type == "number" then tostring else "" end
    # Oniguruma reads \x{HHHH} in a pattern, not \uHHHH (which silently matches other text)
    | gsub("\\x{007f}"; "^?")
    | gsub("(?<c>[\\x{0000}-\\x{001f}])"; "^" + ([(.c | explode[0]) + 64] | implode))
    | gsub("[\\x{0080}-\\x{009f}\\x{200b}-\\x{200f}\\x{2028}-\\x{202e}\\x{2060}-\\x{2069}\\x{feff}]"; "?")
    | if length > $max then .[0:$max - 1] + "…" else . end;
  def num: if type == "number" and isinfinite == false and isnan == false then . else null end;
  def pct: num | if . == null then null elif . < 0 then 0 elif . > 100 then 100 else . end;

  # --- our own styling, added after cleaning ---
  def paint($c; $s): if $color == "1" and $c != "" then "\u001b[\($c)m\($s)\u001b[0m" else $s end;
  def link($path; $s):
    if $links == "1" and ($path | startswith("/")) then
      "\u001b]8;;file://\($path | split("/") | map(@uri) | join("/"))\u0007\($s)\u001b]8;;\u0007"
    else $s end;
  def level($p): if $p < 50 then "32" elif $p < 80 then "33" else "31" end;
  def dur($s): ($s | floor) as $s
    | if $s >= 86400 then "\($s / 86400 | floor)d\(($s % 86400) / 3600 | floor)h"
      elif $s >= 3600 then "\($s / 3600 | floor)h\(($s % 3600) / 60 | floor)m"
      elif $s >= 60 then "\($s / 60 | floor)m"
      else "<1m" end;
  def seg($t; $s; $p): {t: $t, s: $s, p: $p};

  (($nowarg | tonumber?) // now) as $now
  | (if type == "object" then . else {} end) as $in

  # model (always kept)
  | ($in.model.display_name? // $in.model.id? // "?" | clean(32)) as $model

  # context window
  # every `x?` needs a `// fallback`: on a wrong type `?` yields nothing, and `nothing as $v`
  # silently ends the whole program, which blanks the line
  | ($in.context_window.used_percentage? // null | pct) as $ctx
  | (if $ctx == null then null else
      ([($ctx / 10 | round), 10] | min) as $f
      | ([range(0; $f) | "█"] + [range($f; 10) | "░"] | join("")) as $bar
      | seg("\($bar) \($ctx | floor)%"; paint(level($ctx); $bar) + " \($ctx | floor)%"; 90)
    end) as $ctxseg

  # prompt cache: only while warm, unexpired, and a rebuild would cost real tokens
  | ($in.prompt_cache // {}) as $pc
  | (($cachemin | tonumber?) // 50000) as $min
  | (if ($pc | type) == "object" and $pc.warm == true
        and ($pc.expires_at | num) != null and $pc.expires_at > $now
        and (($pc.recache_tokens_if_cold | num) // 0) >= $min
     then ($pc.expires_at - $now) as $left
       | seg("cache \(dur($left))";
             paint(if $left < 60 then "31" elif $left < 300 then "33" else "" end; "cache \(dur($left))"); 60)
     else null end) as $cacheseg

  # plan usage: the window closest to its limit. Claude Code: rate_limits.*; Antigravity:
  # quota.<bucket>.remaining_fraction. "↑" = used faster than the window has elapsed.
  | ([ ($in.rate_limits // {} | if type == "object" then . else {} end) as $rl
       | (["five_hour", "5h", 18000], ["seven_day", "7d", 604800], ["spend_limit", "spend", null]) as [$k, $label, $win]
       | ($rl[$k] // null) | select(type == "object")
       | {label: $label, used: (.used_percentage | pct), left: ((.resets_at | num) // null | if . == null then null else . - $now end), win: $win}
       | select(.used != null and (.left == null or .left > 0)) ]
     + [ ($in.quota // {} | if type == "object" then . else {} end) | to_entries[]
       | .value | select(type == "object" and .disabled != true and (.remaining_fraction | num) != null)
       | {label: "quota", used: ((1 - .remaining_fraction) * 100 | pct), left: (.reset_in_seconds | num), win: null}
       | select(.used != null) ]
    ) as $windows
  | (if ($windows | length) == 0 then null else
      ($windows | max_by(.used)) as $w
      | (if $w.win != null and $w.left != null and $w.left <= $w.win
           then ($w.used > (($w.win - $w.left) / $w.win * 100)) else false end) as $ahead
      | "\($w.label) \($w.used | floor)%\(if $ahead then "↑" else "" end)" as $u
      | (if $w.left != null then " \(dur($w.left))" else "" end) as $r
      | seg($u + $r; paint(level($w.used); $u) + $r; 80)
    end) as $useseg

  # project ⎇ branch, linked to the working directory
  | ($project | clean(40)) as $proj
  | ($branch | clean(48)) as $br
  | (if $proj == "" then null else
      ($proj + (if $br != "" then " ⎇ " + $br else "" end)) as $t
      | seg($t; link($cwd; $proj) + (if $br != "" then " ⎇ " + $br else "" end); 70)
    end) as $projseg

  # worktree: the host field when sent, else the linked-worktree check done in bash
  | ($in.worktree.name? // $in.workspace.git_worktree? // $wt | clean(40)) as $wtname
  | (if $wtname == "" then null else seg("wt " + $wtname; paint("36"; "wt " + $wtname); 55) end) as $wtseg

  | (if $scratch == "" then null else seg("scratch"; link($scratch; "scratch"); 30) end) as $scrseg
  | (if $skills == "" then null else
      seg("skills▸ " + ($skills | clean(160)); "skills▸ " + ($skills | clean(160)); 20)
      + {alt: ("skills▸ " + ($skills_short | clean(24)))}
    end) as $skillseg
  | (if $dump == "" then null else seg("dump on"; paint("31"; "dump on"); 95) end) as $dumpseg

  | [ seg($model; $model; 100), $dumpseg, $ctxseg, $cacheseg, $useseg, $projseg, $wtseg, $scrseg, $skillseg ]
  | map(select(. != null))

  # fit the width: shorten, then drop, the lowest-priority segment until it fits
  | ((($cols | tonumber?) // ($in.terminal_width | num) // 0) | floor) as $width
  | def width: (map(.t | length) | add) + 3 * (length - 1);
    def fit:
      if $width <= 0 or width <= $width or length <= 1 then .
      else (map(select(.p < 100)) | min_by(.p)) as $low
        | if $low.alt != null then map(if . == $low then .t = .alt | .s = .alt | del(.alt) else . end)
          else map(select(. != $low)) end
        | fit
      end;
    fit
  | map(.s) | join(" │ ")
' 2>/dev/null || printf 'statusline: could not read the status payload\n'
