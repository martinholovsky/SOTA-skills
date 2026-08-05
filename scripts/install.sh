#!/usr/bin/env bash
#
# install.sh — link the SOTA skills into Claude Code, and update them later.
#
# Installation is symlink-based, so this script is also the updater: re-run it
# after `git pull` and it links any newly-added skills and prunes links to
# skills that were removed/renamed. Existing skills update with no action at all
# (the symlinks already point at the live files).
#
# After linking, on a personal install it offers to set up "always-on routing"
# (a global CLAUDE.md directive + a prompt hook) so the skills apply without
# trigger words. It is dotfiles-aware: it detects existing/symlinked config and
# ASKS before touching anything, backing up first and using managed markers so
# re-runs are idempotent and your own content is preserved. When the directive or
# hook wording changes in a newer release, re-running (e.g. --update) offers to
# refresh the managed block in place — only the content between the markers, and
# only a hook it recognizes as its own; hand edits outside the block are kept.
#
# Contributor hygiene: when run from a git checkout it also checks that the
# repo's pre-commit hook (gitleaks + invariants) is installed — offering to
# install it if the pre-commit tool is available, or printing a tip if not.
#
# Usage:
#   scripts/install.sh                 # link skills into ~/.claude/skills (all projects)
#   scripts/install.sh --project DIR   # link into DIR/.claude/skills (one project)
#   scripts/install.sh --update        # git pull --ff-only first, then re-link
#                                      #   (scripts/update.sh is an alias for it)
#   scripts/install.sh --version       # report which release is installed, and where
#   scripts/install.sh --copy          # copy instead of symlink (pin a snapshot)
#   scripts/install.sh --routing       # also set up always-on routing (force)
#   scripts/install.sh --no-routing    # skip the routing offer
#   scripts/install.sh --yes           # assume the recommended answer to prompts
#   scripts/install.sh --color=WHEN    # always | never | auto (default; --no-color = never)
#   scripts/install.sh --help
#
# Output: colour and emoji are decorative only — every line still says what it
# means in words. They turn themselves off when the stream is not a terminal, on
# a non-UTF-8 locale, on TERM=dumb, or when NO_COLOR is set; FORCE_COLOR (or
# CLICOLOR_FORCE) turns them back on, and --color/--no-color beats both.
#
set -euo pipefail

# Repo root = parent of this script's dir, so cwd does not matter.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd -- "$SCRIPT_DIR/.." && pwd)"; readonly REPO
readonly SKILLS_SRC="$REPO/skills"

TARGET="$HOME/.claude/skills"
DO_UPDATE=0
DO_VERSION=0
USE_COPY=0
DO_ROUTING=-1   # -1 = ask/auto, 0 = skip, 1 = force
ASSUME_YES=0
COLOR_MODE=auto # auto | always | never  (--color=WHEN / --no-color)

INTERACTIVE=0
{ [ -t 0 ] && [ -t 1 ]; } && INTERACTIVE=1

# --- output style ------------------------------------------------------------
# Colour/emoji policy, in precedence order: --color flag → FORCE_COLOR /
# CLICOLOR_FORCE (non-empty) → NO_COLOR (non-empty) → auto, meaning "the stream
# is a terminal and TERM is set and not dumb". Detection is PER STREAM because
# status goes to stdout and warnings/errors to stderr, and only one of the two
# may be a pipe (`install.sh > log.txt` must still colour its errors).
#
# Decoration never carries meaning on its own: "warning:"/"error:" stay in the
# text for colourblind and NO_COLOR readers, and the status glyphs degrade to
# ASCII (+ - ~ ! x) whenever emoji are off — so a CI log or a C-locale box gets
# readable markers instead of mojibake.
supports_color() {  # $1 = fd number, or "tty" for a stream that is one by definition
  case "$COLOR_MODE" in never) return 1 ;; always) return 0 ;; esac
  [ -n "${FORCE_COLOR:-}${CLICOLOR_FORCE:-}" ] && return 0
  [ -n "${NO_COLOR:-}" ] && return 1
  case "${TERM:-}" in ''|dumb) return 1 ;; esac
  [ "$1" = tty ] || [ -t "$1" ] || return 1
  return 0
}

utf8_locale() {
  case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in
    *UTF-8*|*utf-8*|*UTF8*|*utf8*) return 0 ;;
    *) return 1 ;;
  esac
}

init_style() {
  if supports_color 1; then
    C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'
    C_GREEN=$'\033[32m'; C_CYAN=$'\033[36m'
  else
    C_RESET=''; C_BOLD=''; C_DIM=''; C_GREEN=''; C_CYAN=''
  fi
  if supports_color 2; then
    E_RESET=$'\033[0m'; E_YELLOW=$'\033[33m'; E_RED=$'\033[31m'
  else
    E_RESET=''; E_YELLOW=''; E_RED=''
  fi
  # The prompt is written to /dev/tty, which is a terminal by definition — the
  # stream test cannot apply, but the flag/env policy still does.
  if [ "$INTERACTIVE" -eq 1 ] && supports_color tty; then
    P_RESET=$'\033[0m'; P_BOLD=$'\033[1m'; P_CYAN=$'\033[36m'
  else
    P_RESET=''; P_BOLD=''; P_CYAN=''
  fi
  # Emoji ride along with colour, and additionally need a UTF-8 locale.
  EMOJI=0
  if [ "$COLOR_MODE" != never ] && utf8_locale && supports_color 1; then EMOJI=1; fi
  if [ "$EMOJI" -eq 1 ]; then
    G_OK='✓'; G_CHG='↻'; G_INFO='·'; G_WARN='⚠'; G_ERR='✗'; G_ASK='?'
  else
    G_OK='+'; G_CHG='~'; G_INFO='-'; G_WARN='!'; G_ERR='x'; G_ASK='?'
  fi
}
init_style   # provisional, so an early die() is styled; re-run after flag parsing

ok()   { printf '  %s%s%s %s\n' "$C_GREEN" "$G_OK"   "$C_RESET" "$*"; }   # did something
chg()  { printf '  %s%s%s %s\n' "$C_CYAN"  "$G_CHG"  "$C_RESET" "$*"; }   # changed / act on this
log()  { printf '  %s%s %s%s\n' "$C_DIM"   "$G_INFO" "$*" "$C_RESET"; }   # no-op / context
warn() { printf '  %s%s warning:%s %s\n' "$E_YELLOW" "$G_WARN" "$E_RESET" "$*" >&2; }
die()  { printf '  %s%s error:%s %s\n'   "$E_RED"    "$G_ERR"  "$E_RESET" "$*" >&2; exit 1; }

section() {  # $1 = emoji, $2 = title
  local mark=""
  if [ "$EMOJI" -eq 1 ]; then mark="$1  "; fi
  printf '\n%s%s%s%s\n' "$C_BOLD" "$mark" "$2" "$C_RESET"
}

usage() { sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'; exit "${1:-0}"; }

# --- version reporting -------------------------------------------------------
# Nothing in the library reported which release was in use, so a bug report
# ("the day-zero check fired wrongly") could not name the version that produced
# it. VERSION is the single source of truth (invariant 5 keeps it in lockstep
# with plugin.json and the CHANGELOG top entry), so read it rather than
# hardcoding a number anywhere.
read_version() {  # <repo> — prints the release string, or "unknown"
  local f="$1/VERSION"
  [ -r "$f" ] && tr -d '[:space:]' <"$f" || printf 'unknown'
}

report_version() {
  local v git_desc="" head="" behind=""
  v="$(read_version "$REPO")"
  section '🧩' "SOTA-skills $v"
  if git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    # --dirty marks uncommitted local edits, so no separate dirty check is needed.
    git_desc="$(git -C "$REPO" describe --tags --always --dirty 2>/dev/null || true)"
    head="$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || true)"
    log "checkout: ${git_desc:-?} (HEAD $head)"
    # Is a newer release already fetched? Report it without touching the network.
    if git -C "$REPO" rev-parse --verify -q '@{upstream}' >/dev/null 2>&1; then
      behind="$(git -C "$REPO" rev-list --count 'HEAD..@{upstream}' 2>/dev/null || printf '0')"
      if [ "${behind:-0}" -gt 0 ]; then
        chg "upstream: $behind commit(s) ahead — run scripts/update.sh"
      else
        log "upstream: level as of the last fetch (a fetch is not implied)"
      fi
    fi
  else
    log "checkout: not a git repository (snapshot or plugin cache)"
  fi
  # Where the skills actually resolve from — a --copy snapshot does NOT track VERSION.
  local probe="$TARGET/sota"
  if [ -L "$probe" ]; then
    log "install:  symlinked → $(readlink "$probe") (updates live on git pull)"
  elif [ -d "$probe" ]; then
    log "install:  copied snapshot at $probe — pinned, will NOT update; re-run with --copy to refresh"
  else
    log "install:  not linked into $TARGET"
  fi
}

# --- interactive / routing helpers -------------------------------------------
readonly RT_BEGIN="<!-- >>> sota-skills routing (managed by install.sh) >>> -->"
readonly RT_END="<!-- <<< sota-skills routing <<< -->"
# kept on one line; contains "sota" so re-runs detect it and never duplicate
# Match on a phrase that survives rewording, not on the opening words. The old
# marker was "sota standing rules:" — the first three words of the message — so a
# user who reworded the opening (the natural thing to do) silently un-managed
# their own hook: --update then ADDED A SECOND one instead of refreshing it.
# Observed on a real install 2026-08-05. "sota-* skills" appears in every version
# of this hook we have ever shipped and in hand-edited variants of it.
readonly HOOK_SIG="sota-* skills"          # stable marker identifying our own hook
readonly HOOK_CMD="echo 'sota standing rules (every answer): (1) VALIDATE — check any claim about code, system state, config, versions or facts against a primary source before asserting it, and label anything unverified. (2) KEEP DOCS CURRENT — update affected docs in the same change. (3) ROUTE BEFORE YOU ACT — if the turn touches code, a diff, a config or a build/CI file, invoke the sota skill FIRST and apply the matching sota-* skills. Reading a file counts. If you have already read code this session without routing, route now. Treat ~/.claude/profiles as the stack baseline; stop and ask on security-relevant choices.'"

ask_yn() {  # $1 prompt, $2 default(y|n); honors --yes and non-interactive
  local def="${2:-y}" ans
  if [ "$ASSUME_YES" -eq 1 ] || [ "$INTERACTIVE" -eq 0 ]; then
    [ "$def" = y ] && return 0 || return 1
  fi
  local choices
  choices="$([ "$def" = y ] && printf 'Y/n' || printf 'y/N')"
  printf '  %s%s%s %s [%s%s%s] ' \
    "$P_CYAN" "$G_ASK" "$P_RESET" "$1" "$P_BOLD" "$choices" "$P_RESET" >/dev/tty
  read -r ans </dev/tty || ans=""
  [ -z "$ans" ] && ans="$def"
  case "$ans" in [Yy]*) return 0 ;; *) return 1 ;; esac
}

backup() { [ -e "$1" ] && cp -L "$1" "$1.bak" && log "backed up $1 → $1.bak"; }

emit_routing_block() {
  cat <<'MD'
<!-- >>> sota-skills routing (managed by install.sh) >>> -->
## Engineering standing rules

Apply to every answer, regardless of phrasing:

1. **Validate before you assert** — verify any claim about code, system state,
   config, versions, or facts against a primary source (read the file / run the
   command / fetch official docs) before answering or proposing; label anything
   unverified as such.
2. **Keep docs current** — when you change code/behavior/config, update the
   affected docs (README, CHANGELOG, comments, runbooks, AGENTS.md) in the same
   change, unprompted.

For any task that builds, designs, refactors, debugs, reviews, or audits code:
consult the `sota` router skill first, load the matching `sota-*` skills, and
apply their rules before acting — even when "SOTA" or "audit" is never said. If a
stack profile exists (`~/.claude/profiles/*.md`), treat it as the BUILD default
and AUDIT baseline; stop and ask on security-relevant decisions.
<!-- <<< sota-skills routing <<< -->
MD
}

# Print the managed routing block (markers inclusive) currently in a file.
extract_block() {  # $1 file
  awk -v b="$RT_BEGIN" -v e="$RT_END" '
    $0 == b { inblk = 1 }
    inblk   { print; if ($0 == e) exit }
  ' "$1"
}

# Replace the managed block in place with the current one, preserving everything
# outside the markers. Writes through the path (cat, not mv) so a symlinked
# target keeps its link.
refresh_block() {  # $1 file
  local f="$1" blk tmp
  blk="$(mktemp)"; tmp="$(mktemp)"
  emit_routing_block >"$blk"
  awk -v b="$RT_BEGIN" -v e="$RT_END" -v blk="$blk" '
    $0 == b { while ((getline l < blk) > 0) print l; close(blk); inblk = 1; next }
    inblk && $0 == e { inblk = 0; next }
    inblk { next }
    { print }
  ' "$f" >"$tmp"
  cat "$tmp" >"$f"
  rm -f "$blk" "$tmp"
}

setup_claude_md() {
  # shellcheck disable=SC2088  # ~ here is display text shown to the user, not a path
  local f="$HOME/.claude/CLAUDE.md" tgt="" where="~/.claude/CLAUDE.md"
  [ -L "$f" ] && tgt="$(readlink "$f")"
  [ -n "$tgt" ] && where="$where (symlink → $tgt; likely managed by your dotfiles — commit it there)"

  if [ -f "$f" ] && grep -qF "$RT_BEGIN" "$f" 2>/dev/null; then
    if ! grep -qF "$RT_END" "$f" 2>/dev/null; then
      # shellcheck disable=SC2088  # ~ is display text in the message, not a path
      warn "~/.claude/CLAUDE.md has the start marker but no end marker — leaving it untouched; fix by hand or delete the block and re-run"
      return
    fi
    if [ -z "$(extract_block "$f")" ]; then
      # Markers found by substring, but extract_block (exact whole-line match)
      # sees nothing: they were re-indented/altered. A refresh would be a
      # silent no-op loop — refuse instead.
      # shellcheck disable=SC2088  # ~ is display text in the message, not a path
      warn "~/.claude/CLAUDE.md has sota routing markers that are altered (indented?) — leaving it untouched; restore the exact marker lines or delete the block and re-run"
      return
    fi
    if [ "$(extract_block "$f")" = "$(emit_routing_block)" ]; then
      log "routing directive in ~/.claude/CLAUDE.md — up to date"; return
    fi
    if ask_yn "The managed SOTA routing directive in $where is out of date — refresh it in place?" y; then
      backup "$f"; refresh_block "$f"; ok "refreshed routing directive in ~/.claude/CLAUDE.md"
    else
      log "left existing directive unchanged"
    fi
    return
  fi
  if [ -L "$f" ] && [ ! -e "$f" ]; then           # dangling symlink
    # shellcheck disable=SC2088  # ~ is display text in the prompt, not a path
    ask_yn "~/.claude/CLAUDE.md is a broken symlink — replace it with a real file holding the directive?" y \
      && { rm -f "$f"; emit_routing_block >"$f"; ok "wrote ~/.claude/CLAUDE.md (real file)"; }
    return 0
  fi
  if [ -e "$f" ]; then
    if ask_yn "Append the SOTA routing directive to $where?" y; then
      backup "$f"; { printf '\n'; emit_routing_block; } >>"$f"; ok "appended directive to ~/.claude/CLAUDE.md"
    else
      log "skipped — copy the block from README's 'Always-on routing' yourself"
    fi
  else
    ask_yn "Create ~/.claude/CLAUDE.md with the SOTA routing directive?" y \
      && { mkdir -p "$(dirname "$f")"; emit_routing_block >"$f"; ok "created ~/.claude/CLAUDE.md"; }
  fi
  # Declining any prompt above is a valid outcome, not an error — return
  # success so `set -e` doesn't abort the installer before pre-commit setup
  # and the final instructions (2026-07-10 audit Q-MED-4).
  return 0
}

# A SessionStart hook that occasionally reminds the user updates exist. It makes
# NO network request — see scripts/update-reminder.sh for why that is a design
# choice and not a gap. This is the clone-install half of the update story:
# symlinked skills update the moment you `git pull`, but nothing ever told you to
# pull, and the plugin's first-run notice fires once ever so it is onboarding,
# not a version channel.
setup_update_reminder() {
  local s="$HOME/.claude/settings.json" tmp cmd
  cmd="\"$REPO/scripts/update-reminder.sh\""
  if ! command -v jq >/dev/null 2>&1; then
    warn "jq not found — skipping update-reminder hook"; return
  fi
  if [ -f "$s" ] && jq -e --arg sig "update-reminder.sh" \
      '[.hooks.SessionStart[]?.hooks[]?.command // ""] | any(contains($sig))' "$s" >/dev/null 2>&1; then
    log "sota update-reminder hook already present — up to date"; return
  fi
  ask_yn "Add a SessionStart hook that reminds you to check for updates every ~14 days (no network calls)?" y || return
  tmp="$(mktemp)"
  if [ -e "$s" ]; then
    backup "$s"
    if jq --arg c "$cmd" '.hooks.SessionStart = ((.hooks.SessionStart // []) + [{hooks:[{type:"command",command:$c}]}])' "$s" >"$tmp" 2>/dev/null; then
      cat "$tmp" >"$s"   # cat (not mv) so a symlinked settings.json keeps its link
      ok "added SessionStart update-reminder hook (silence it with SOTA_UPDATE_REMINDER_DAYS=0)"
    else
      warn "could not parse $s as JSON — left unchanged"
    fi
  else
    mkdir -p "$(dirname "$s")"
    jq -n --arg c "$cmd" '{hooks:{SessionStart:[{hooks:[{type:"command",command:$c}]}]}}' >"$s"
    ok "created ~/.claude/settings.json with the update-reminder hook"
  fi
  rm -f "$tmp"
}

setup_hook() {
  local s="$HOME/.claude/settings.json" tmp
  if ! command -v jq >/dev/null 2>&1; then
    warn "jq not found — skipping hook setup (add the UserPromptSubmit hook manually, or install jq and re-run)"; return
  fi
  if [ -f "$s" ]; then
    # A hook we manage (identified by a stable signature) already present?
    if jq -e --arg sig "$HOOK_SIG" '[.hooks.UserPromptSubmit[]?.hooks[]?.command // ""] | any(contains($sig))' "$s" >/dev/null 2>&1; then
      if jq -e --arg c "$HOOK_CMD" '[.hooks.UserPromptSubmit[]?.hooks[]?.command // ""] | any(. == $c)' "$s" >/dev/null 2>&1; then
        log "sota UserPromptSubmit hook already current — up to date"; return
      fi
      ask_yn "The sota UserPromptSubmit reminder hook is out of date — refresh its wording?" y \
        || { log "left existing hook unchanged"; return; }
      tmp="$(mktemp)"; backup "$s"
      if jq --arg c "$HOOK_CMD" --arg sig "$HOOK_SIG" \
          '.hooks.UserPromptSubmit |= map(.hooks |= map(if ((.command // "") | contains($sig)) then .command = $c else . end))' \
          "$s" >"$tmp" 2>/dev/null; then
        cat "$tmp" >"$s"; ok "refreshed sota UserPromptSubmit hook to latest wording"
      else
        warn "could not parse $s as JSON — left unchanged"
      fi
      rm -f "$tmp"; return
    fi
    # An unrecognized sota-mentioning hook — could be user-authored; do not touch.
    if jq -e '[.hooks.UserPromptSubmit[]?.hooks[]?.command // ""] | any(test("sota";"i"))' "$s" >/dev/null 2>&1; then
      log "a sota UserPromptSubmit hook already exists (custom wording) — left unchanged"; return
    fi
  fi
  ask_yn "Add a UserPromptSubmit hook that re-injects the standing rules each prompt?" y || return
  tmp="$(mktemp)"
  if [ -e "$s" ]; then
    backup "$s"
    if jq --arg c "$HOOK_CMD" '.hooks.UserPromptSubmit = ((.hooks.UserPromptSubmit // []) + [{hooks:[{type:"command",command:$c}]}])' "$s" >"$tmp" 2>/dev/null; then
      cat "$tmp" >"$s"   # cat (not mv) so a symlinked settings.json keeps its link
      ok "added UserPromptSubmit hook to ~/.claude/settings.json"
    else
      warn "could not parse $s as JSON — left unchanged"
    fi
  else
    mkdir -p "$(dirname "$s")"
    jq -n --arg c "$HOOK_CMD" '{hooks:{UserPromptSubmit:[{hooks:[{type:"command",command:$c}]}]}}' >"$s"
    ok "created ~/.claude/settings.json with the hook"
  fi
  rm -f "$tmp"
}

# --- contributor hygiene: the repo's own pre-commit hook ---------------------
# Non-fatal in every branch: end users who never commit to this checkout just
# get a one-line tip at most; CI enforces the same checks regardless.
maybe_setup_precommit() {
  [ -f "$REPO/.pre-commit-config.yaml" ] || return 0
  git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
  section '🔒' 'Contributor hygiene'
  local hook
  hook="$(git -C "$REPO" rev-parse --git-path hooks/pre-commit 2>/dev/null || true)"
  case "$hook" in /*) ;; *) hook="$REPO/$hook" ;; esac
  if [ -n "$hook" ] && [ -f "$hook" ] && grep -q 'pre-commit' "$hook" 2>/dev/null; then
    log "pre-commit hook in this checkout — already installed"
    return 0
  fi
  if ! command -v pre-commit >/dev/null 2>&1; then
    chg "contributor tip: 'pipx install pre-commit' (or 'brew install pre-commit'), then 'pre-commit install' — runs the gitleaks + invariants gate on each commit (CI enforces it regardless)"
    return 0
  fi
  ask_yn "Install the repo's pre-commit hook (gitleaks + invariants on every commit)?" y || return 0
  if (cd "$REPO" && pre-commit install >/dev/null); then
    ok "pre-commit hook installed in this checkout"
  else
    warn "pre-commit install failed — run 'pre-commit install' in $REPO manually"
  fi
}

maybe_setup_routing() {
  # personal install only; never for --project or --copy snapshots
  [ "$TARGET" = "$HOME/.claude/skills" ] && [ "$USE_COPY" -eq 0 ] || return 0
  local go=0
  case "$DO_ROUTING" in
    1) section '🧭' 'Always-on routing'; go=1 ;;
    0) return 0 ;;
    *) if [ "$INTERACTIVE" -eq 1 ] || [ "$ASSUME_YES" -eq 1 ]; then
         # Header first: the question and everything it prints belong under it.
         section '🧭' 'Always-on routing'
         ask_yn "Set up always-on routing (global directive + prompt hook) so skills apply without trigger words?" y && go=1
       fi ;;
  esac
  [ "$go" -eq 1 ] || return 0
  # Best-effort routing setup: declining a prompt inside either function is a
  # valid outcome, so never let it abort the installer before pre-commit setup
  # and the final instructions (2026-07-10 audit Q-MED-4).
  setup_claude_md || true
  setup_hook || true
  setup_update_reminder || true
  return 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --update)     DO_UPDATE=1 ;;
    --version)    DO_VERSION=1 ;;
    --copy)       USE_COPY=1 ;;
    --project)    shift; [ $# -gt 0 ] || die "--project needs a directory"; TARGET="$1/.claude/skills" ;;
    --routing)    DO_ROUTING=1 ;;
    --no-routing) DO_ROUTING=0 ;;
    --yes|-y)     ASSUME_YES=1 ;;
    --color)      shift; [ $# -gt 0 ] || die "--color needs always|never|auto"; COLOR_MODE="$1" ;;
    --color=*)    COLOR_MODE="${1#*=}" ;;
    --no-color)   COLOR_MODE=never ;;
    -h|--help)    usage 0 ;;
    *)            die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

case "$COLOR_MODE" in
  auto|always|never) ;;
  *) die "--color takes always|never|auto (got: $COLOR_MODE)" ;;
esac
init_style   # now with the flags applied

[ -d "$SKILLS_SRC" ] || die "no skills/ dir at $SKILLS_SRC — run from a SOTA-skills checkout"

# --version is a read-only report: print and exit before touching anything.
if [ "$DO_VERSION" -eq 1 ]; then
  report_version
  exit 0
fi

# --- optional self-update ----------------------------------------------------
if [ "$DO_UPDATE" -eq 1 ]; then
  section '📥' 'Update'
  if git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    was="$(read_version "$REPO")"
    chg "updating $(basename "$REPO") (git pull --ff-only)…"
    git -C "$REPO" pull --ff-only || die "pull failed — resolve manually, then re-run"
    now="$(read_version "$REPO")"
    # Report the delta explicitly: symlinked skills change under you on a pull,
    # so "nothing to do" and "you just moved three releases" looked identical.
    if [ "$was" != "$now" ]; then
      ok "version:  $was → $now — see CHANGELOG.md for what changed"
    else
      log "version:  $now (unchanged)"
    fi
  else
    warn "$REPO is not a git checkout — skipping --update"
  fi
fi

mkdir -p "$TARGET"

# --- link (or copy) every skill, idempotently --------------------------------
section '🔗' 'Skills'
linked=0; created=0
for src in "$SKILLS_SRC"/*/; do
  name="$(basename "$src")"
  dest="$TARGET/$name"
  [ -e "$dest" ] || [ -L "$dest" ] || created=$((created + 1))
  if [ "$USE_COPY" -eq 1 ]; then
    rm -rf "$dest"
    cp -R "${src%/}" "$dest"
  else
    if [ -e "$dest" ] && [ ! -L "$dest" ]; then
      # ln -sfn cannot replace a real directory — it would nest the link
      # INSIDE it and leave the stale copy in place while we report success
      # (the --copy → default-install switch). Ask, then replace for real.
      if ask_yn "$name at $dest is a real directory (previous --copy install?) — replace it with a symlink?" y; then
        rm -rf "$dest"
      else
        warn "kept $dest as-is — it is a snapshot and will NOT update; re-run with --copy to refresh it"
        continue
      fi
    fi
    ln -sfn "${src%/}" "$dest"
  fi
  linked=$((linked + 1))
done

# --- prune stale links: ours (point into this repo) but source now gone -------
pruned=0
if [ "$USE_COPY" -eq 0 ] && [ -d "$TARGET" ]; then
  for dest in "$TARGET"/*; do
    [ -L "$dest" ] || continue
    tgt="$(readlink "$dest")"
    case "$tgt" in
      "$SKILLS_SRC"/*) [ -e "$tgt" ] || { rm -f "$dest"; pruned=$((pruned + 1)); chg "pruned stale link: $(basename "$dest")"; } ;;
    esac
  done
fi

ok "linked $linked skill(s) into $TARGET ($created new, $pruned pruned)$([ "$USE_COPY" -eq 1 ] && echo ' [copied]')"

# --- profile convenience (personal install only) -----------------------------
if [ "$TARGET" = "$HOME/.claude/skills" ] && [ "$USE_COPY" -eq 0 ]; then
  prof="$(find "$REPO/profiles" -maxdepth 1 -name '*.md' ! -name 'example.md.template' 2>/dev/null | head -n1 || true)"
  if [ -n "$prof" ]; then
    mkdir -p "$HOME/.claude/profiles"
    dst="$HOME/.claude/profiles/$(basename "$prof")"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
      # A real file (not our symlink) already lives there — never clobber it
      # silently; back up + ask, matching setup_claude_md's contract
      # (2026-07-10 audit Q-MED-5). Non-interactive default is 'n' (keep it).
      if ask_yn "$dst is a real file — back it up and replace with a link to the repo profile?" n; then
        backup "$dst"; ln -sfn "$prof" "$dst"; ok "linked profile: ~/.claude/profiles/$(basename "$prof")"
      else
        log "left existing ~/.claude/profiles/$(basename "$prof") untouched"
      fi
    else
      ln -sfn "$prof" "$dst"
      ok "linked profile: ~/.claude/profiles/$(basename "$prof")"
    fi
  else
    chg "no profile yet — cp profiles/example.md.template profiles/<you>.md, then re-run"
  fi
fi

maybe_setup_routing
maybe_setup_precommit

section '✅' 'Done'
printf '  %sTo update later:%s\n' "$C_DIM" "$C_RESET"
printf '    git -C "%s" pull   %s# existing skills update live (symlinks); then…%s\n' \
  "$REPO" "$C_DIM" "$C_RESET"
printf '    "%s/scripts/install.sh"   %s# …re-link to pick up any new skills%s\n' \
  "$REPO" "$C_DIM" "$C_RESET"
printf '  %sOr in one step:%s  %s"%s/scripts/update.sh"%s\n' \
  "$C_DIM" "$C_RESET" "$C_CYAN" "$REPO" "$C_RESET"
