#!/usr/bin/env bash
#
# statusline.sh — a Claude Code status line that shows which skills you've
# actually used this session (not just how many are installed).
#
#   model │ ctx NN% │ <dir> ⎇ <branch>
#   skills▸ code-security, testing (2)
#
# How it works: Claude Code's status-line JSON doesn't expose loaded skills, but
# it does pass `transcript_path`. Each skill invocation is recorded there as a
# Skill tool call (`"name":"Skill" … "skill":"<name>"`), so we read them back.
# When nothing's been invoked yet, it falls back to the count of available skills.
#
# Wire it up — point settings.json at this script:
#   "statusLine": { "type": "command", "command": "/path/to/scripts/statusline.sh" }
#
# Requires: jq.
#
set -euo pipefail

input="$(cat)"

if ! command -v jq >/dev/null 2>&1; then
  printf 'statusline: jq not found — install it (e.g. brew install jq)\n'
  exit 0
fi

# one jq pass extracts every field, joined by a unit separator (0x1F) — a
# non-whitespace delimiter so `read` preserves empty fields (e.g. absent ctx)
IFS=$'\037' read -r model ctx cwd transcript <<EOF
$(printf '%s' "$input" | jq -r '[
  (.model.display_name // .model.id // "?"),
  (if .context_window.used_percentage then (.context_window.used_percentage | floor | tostring) else "" end),
  (.workspace.current_dir // .cwd // ""),
  (.transcript_path // "")
] | join("")' 2>/dev/null)
EOF
[ -n "$model" ] || model="?"

# current branch (best-effort; never fail the line on it)
branch=""
if [ -n "$cwd" ] && [ -d "$cwd" ]; then
  branch="$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
fi

# skills used this session = distinct Skill tool invocations in the transcript
skills=""
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
  used="$(grep '"name":"Skill"' "$transcript" 2>/dev/null \
    | grep -o '"skill":"[^"]*"' \
    | sed 's/.*:"//; s/"$//' \
    | awk 'NF && !seen[$0]++' || true)"
  if [ -n "$used" ]; then
    n="$(printf '%s\n' "$used" | grep -c .)"
    list="$(printf '%s' "$used" | paste -sd, - | sed 's/,/, /g')"
    skills="skills▸ ${list} (${n})"
  fi
fi
# fallback: count of installed skills
if [ -z "$skills" ]; then
  for d in "$cwd/.claude/skills" "$HOME/.claude/skills"; do
    if [ -d "$d" ]; then
      # -L so symlinked skill dirs (how install.sh links them) are followed
      avail="$(find -L "$d" -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')"
      [ "$avail" -gt 0 ] && { skills="skills▸ ${avail} available"; break; }
    fi
  done
fi

sep=" │ "
out="$model"
[ -n "$ctx" ]    && out="${out}${sep}ctx ${ctx}%"
[ -n "$cwd" ]    && out="${out}${sep}$(basename "$cwd")"
[ -n "$branch" ] && out="${out} ⎇ ${branch}"
printf '%s\n' "$out"
# skills on their own row so the list gets the full terminal width
# (Claude Code renders each output line as a separate status row)
[ -n "$skills" ] && printf '%s\n' "$skills"
