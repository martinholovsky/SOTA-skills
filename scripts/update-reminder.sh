#!/usr/bin/env bash
#
# update-reminder.sh — an occasional nudge to check for a newer SOTA-skills.
#
# THIS SCRIPT MAKES NO NETWORK REQUEST. It does not contact GitHub, this repo, or
# anything else; it cannot know whether a new version exists. All it knows is how
# long it has been since it last said anything, and which version is installed
# locally (read from the VERSION file next to it).
#
# That is a deliberate design choice, not a limitation to fix later. A real
# version check has to phone home from every session start, which turns a
# documentation library into something that reports when and how often you work.
# The whole benefit here — reminding you that updates exist — needs none of that.
# If you want the actual check, YOU run it, and it is one command:
#
#     scripts/update.sh                # pulls, then prints the version delta
#
# Behaviour: silent on first run (a fresh install is current by definition, and
# the plugin's first-run notice is already speaking), then at most one line every
# SOTA_UPDATE_REMINDER_DAYS days (default 14).
#
# Opt out completely:
#     export SOTA_UPDATE_REMINDER_DAYS=0
#
# FAILS OPEN, ALWAYS. This runs on SessionStart; a hook that errors degrades the
# session it is attached to. Every step is guarded and the script exits 0 no
# matter what — an un-writable data dir, a missing VERSION, a read-only home.
# The worst outcome is silence, which is also the correct outcome most days.
set -uo pipefail

# --- opt-out and interval -------------------------------------------------
days="${SOTA_UPDATE_REMINDER_DAYS:-14}"
case "$days" in
  ''|*[!0-9]*) days=14 ;;   # garbage in the env must not break a session
esac
[ "$days" -eq 0 ] && exit 0

# --- a COPIED install that the checkout has moved past --------------------
# install.sh --copy (or its forced fallback where symlinks are unavailable, e.g. Git
# Bash without Developer Mode) stamps each copied skills dir with the release and
# commit it came from. `git pull` moves the checkout and never the copy, so the copy
# silently serves old guidance. This is not a timer: it compares two local facts,
# and says so on every session while they differ — a stale copy is a defect, not news.
repo=$(unset CDPATH; cd -- "$(dirname -- "$0")/.." 2>/dev/null && pwd) || repo=""
if [ -n "$repo" ]; then
  now_v=""; now_c=""
  [ -r "$repo/VERSION" ] && now_v=$(tr -d '[:space:]' < "$repo/VERSION" 2>/dev/null)
  now_c=$(git -C "$repo" rev-parse HEAD 2>/dev/null) || now_c=""
  for d in "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills" "$HOME/.agents/skills" \
           "$HOME/.gemini/config/skills" "$HOME/.gemini/antigravity-cli/skills"; do
    f="$d/.sota-install"
    [ -r "$f" ] || continue
    was_v=$(sed -n 's/^version=//p' "$f" 2>/dev/null | head -n 1)
    was_c=$(sed -n 's/^commit=//p' "$f" 2>/dev/null | head -n 1)
    stale=0
    [ -n "$now_v" ] && [ -n "$was_v" ] && [ "$was_v" != "$now_v" ] && stale=1
    [ -n "$now_c" ] && [ -n "$was_c" ] && [ "$was_c" != "unknown" ] && [ "$was_c" != "$now_c" ] && stale=1
    if [ "$stale" -eq 1 ]; then
      printf '[sota-skills: stale copied install. Relay this to the user in one line, then continue with their request.]\n'
      printf 'The skills in %s are a COPY of SOTA-skills %s (commit %.7s), but the checkout at %s is now %s (commit %.7s). A copy does not update on git pull: re-run %s/scripts/install.sh to refresh it.\n' \
        "$d" "${was_v:-unknown}" "${was_c:-unknown}" "$repo" "${now_v:-unknown}" "${now_c:-unknown}" "$repo"
    fi
  done
fi

# --- where we remember the last nudge -------------------------------------
data="${CLAUDE_PLUGIN_DATA:-${HOME}/.claude/sota-skills-data}"
stamp="${data}/.update-reminder-last"

mkdir -p "$data" 2>/dev/null || exit 0

# First run: record the moment and say nothing. A just-installed copy is current,
# and the plugin's first-run notice is already using this turn.
if [ ! -e "$stamp" ]; then
  : > "$stamp" 2>/dev/null || true
  exit 0
fi

# Older than the interval? `find -mtime` rather than date arithmetic: `date -d`
# (GNU) and `date -v` (BSD/macOS) disagree, and this has to run on both.
due=$(find "$stamp" -maxdepth 0 -mtime +"$days" 2>/dev/null) || exit 0
[ -n "$due" ] || exit 0

# --- what we can say without asking anyone --------------------------------
here=$(unset CDPATH; cd -- "$(dirname -- "$0")/.." 2>/dev/null && pwd) || exit 0
version=""
[ -r "$here/VERSION" ] && version=$(tr -d '[:space:]' < "$here/VERSION" 2>/dev/null)

: > "$stamp" 2>/dev/null || true   # reset the clock even if the message is thin

printf '[sota-skills: occasional update reminder. Relay this to the user in one line, then continue with their request.]\n'
if [ -n "$version" ]; then
  printf 'SOTA-skills %s has been installed here for over %s days. No update check was made (this library never phones home).\n' "$version" "$days"
else
  printf 'SOTA-skills has been installed here for over %s days. No update check was made (this library never phones home).\n' "$days"
fi
# shellcheck disable=SC2016  # literal backticks/text for the user to read, not an expansion
printf 'If they want to check for a newer release: run `scripts/update.sh`, or browse https://github.com/martinholovsky/SOTA-skills/releases\n'
printf 'To silence this: export SOTA_UPDATE_REMINDER_DAYS=0 (or set it to a different number of days).\n'
exit 0
