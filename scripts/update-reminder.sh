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

# --- a symlinked install whose checkout is on a feature branch, or dirty -------
# With a symlink install the checkout IS the live library: a maintainer's `git checkout -b`
# there changes what every session on the machine loads. Measured 2026-10-22: ~5.5 h of
# feature branches across five PRs (reflog), noticed only by another session's field report.
# The maintainer's session cannot see who else is loading, so the consuming session says it.
# Local facts only. Silent for a plugin or a --copy install, which do not load this checkout.
if [ -n "$repo" ]; then
  conf="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  link=$(readlink "$conf/skills/sota" 2>/dev/null) || link=""
  if [ -n "$link" ]; then
    real_link=$(unset CDPATH; cd -- "$conf/skills/sota" 2>/dev/null && pwd -P) || real_link=""
    real_repo=$(unset CDPATH; cd -- "$repo" 2>/dev/null && pwd -P) || real_repo=""
    # Only a git work tree has a branch to report: a tarball install is not a checkout, and an
    # empty branch there would read as "a detached HEAD" (caught by its own test case, 2026-10-23).
    in_git=$(git -C "$repo" rev-parse --is-inside-work-tree 2>/dev/null) || in_git=""
    [ "$in_git" = true ] || real_link=""
    case "$real_link" in
      "$real_repo"/skills/*)
        branch=$(git -C "$repo" symbolic-ref --short -q HEAD 2>/dev/null) || branch=""
        default=$(git -C "$repo" symbolic-ref --short -q refs/remotes/origin/HEAD 2>/dev/null) || default=""
        default=${default#origin/}; [ -n "$default" ] || default=main
        dirty=$(git -C "$repo" status --porcelain --untracked-files=no 2>/dev/null | wc -l | tr -d ' ') || dirty=0
        what=""
        [ "$branch" = "$default" ] || what="checked out on ${branch:-a detached HEAD}, not $default"
        [ "${dirty:-0}" -gt 0 ] 2>/dev/null && what="${what:+$what, and }carrying $dirty uncommitted change(s)"
        if [ -n "$what" ]; then
          printf '[sota-skills: this session loads an unreleased library. Relay this to the user in one line, then continue with their request.]\n'
          printf 'The installed skills link into %s, which is %s, so this session runs that text and hook code, not a release. Maintainers: work in a git worktree instead (AGENTS.md "Landing a change", step 1).\n' \
            "$repo" "$what"
        fi
        ;;
    esac
  fi
fi

# --- where we remember the last nudge -------------------------------------
data="${CLAUDE_PLUGIN_DATA:-${HOME}/.claude/sota-skills-data}"
stamp="${data}/.update-reminder-last"

mkdir -p "$data" 2>/dev/null || exit 0

# --- a default-on hook that a pull brought and nothing registered -----------
# A `git pull` on a symlink install brings a new hook SCRIPT and registers nothing: only
# `install.sh --routing` / `--update` writes settings.json. Field-reported twice on 2026-10-22
# (a zsh EQUALS cut recurring with the hook shipped "on by default" and unwired), and true on
# the machine that took the reports in.
# The plugin registers its own hooks, so this is for installs WITHOUT it. Local facts only:
# the checkout's scripts and the settings files. Each missing hook is named ONCE (recorded in
# $notified), so a user who declined it at install is told once, not every session. A fresh
# install (no update stamp yet) records the current state silently: it was just offered them.
if [ -n "$repo" ] && [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  conf="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  notified="${data}/.hooks-notified"
  first=0; [ -e "$stamp" ] || first=1   # no update stamp yet = a fresh install, which was just offered every hook
  agent_shell=""
  case "${CLAUDE_CODE_SHELL:-}" in */zsh | */bash) [ -x "$CLAUDE_CODE_SHELL" ] && agent_shell=${CLAUDE_CODE_SHELL##*/} ;; esac
  [ -n "$agent_shell" ] || { agent_shell=${SHELL:-}; agent_shell=${agent_shell##*/}; }
  missing=""
  for h in code-rules-hook.py zsh-equals-hook.py; do
    [ -f "$repo/scripts/$h" ] || continue
    case "$h" in
      code-rules-hook.py) case "${SOTA_CODE_RULES_HOOK:-}" in off | OFF | 0 | false | FALSE | no) continue ;; esac ;;
      zsh-equals-hook.py)
        [ "$agent_shell" = zsh ] || continue
        case "${SOTA_ZSH_EQUALS_HOOK:-}" in off | OFF | 0 | false | FALSE | no) continue ;; esac ;;
    esac
    grep -qF "$h" "$conf/settings.json" "$conf/settings.local.json" 2>/dev/null && continue
    grep -qxF "$h" "$notified" 2>/dev/null && continue
    missing="${missing:+$missing }$h"
    printf '%s\n' "$h" >> "$notified" 2>/dev/null || true
  done
  [ "$first" -eq 1 ] && { : >> "$notified" 2>/dev/null || true; missing=""; }
  if [ -n "$missing" ]; then
    printf '[sota-skills: a default hook is not registered. Relay this to the user in one line, then continue with their request.]\n'
    printf 'Shipped on by default by the checkout at %s, but not registered in %s/settings.json: %s (a git pull does not register hooks). Run %s/scripts/install.sh --routing to add them, or set their opt-out variables. This is said once.\n' \
      "$repo" "$conf" "$missing" "$repo"
  fi
fi

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
