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
# Usage:
#   scripts/install.sh                 # link skills into ~/.claude/skills (all projects)
#   scripts/install.sh --project DIR   # link into DIR/.claude/skills (one project)
#   scripts/install.sh --update        # git pull --ff-only first, then re-link
#   scripts/install.sh --copy          # copy instead of symlink (pin a snapshot)
#   scripts/install.sh --routing       # also set up always-on routing (force)
#   scripts/install.sh --no-routing    # skip the routing offer
#   scripts/install.sh --yes           # assume the recommended answer to prompts
#   scripts/install.sh --help
#
set -euo pipefail

# Repo root = parent of this script's dir, so cwd does not matter.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd -- "$SCRIPT_DIR/.." && pwd)"; readonly REPO
readonly SKILLS_SRC="$REPO/skills"

TARGET="$HOME/.claude/skills"
DO_UPDATE=0
USE_COPY=0
DO_ROUTING=-1   # -1 = ask/auto, 0 = skip, 1 = force
ASSUME_YES=0

INTERACTIVE=0
{ [ -t 0 ] && [ -t 1 ]; } && INTERACTIVE=1

log()  { printf '  %s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

usage() { sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'; exit "${1:-0}"; }

# --- interactive / routing helpers -------------------------------------------
readonly RT_BEGIN="<!-- >>> sota-skills routing (managed by install.sh) >>> -->"
readonly RT_END="<!-- <<< sota-skills routing <<< -->"
# kept on one line; contains "sota" so re-runs detect it and never duplicate
readonly HOOK_SIG="sota standing rules:"   # stable marker identifying our own hook
readonly HOOK_CMD="echo 'sota standing rules: (1) validate every claim about code/system/config/versions/facts against a primary source before answering or proposing, and label anything unverified; (2) keep docs current in the same change. For code tasks, route through the sota skill and apply the matching sota-* skills; treat ~/.claude/profiles as the baseline.'"

ask_yn() {  # $1 prompt, $2 default(y|n); honors --yes and non-interactive
  local def="${2:-y}" ans
  if [ "$ASSUME_YES" -eq 1 ] || [ "$INTERACTIVE" -eq 0 ]; then
    [ "$def" = y ] && return 0 || return 1
  fi
  printf '%s [%s] ' "$1" "$([ "$def" = y ] && printf 'Y/n' || printf 'y/N')" >/dev/tty
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
    if [ "$(extract_block "$f")" = "$(emit_routing_block)" ]; then
      log "routing directive in ~/.claude/CLAUDE.md — up to date"; return
    fi
    if ask_yn "The managed SOTA routing directive in $where is out of date — refresh it in place?" y; then
      backup "$f"; refresh_block "$f"; log "refreshed routing directive in ~/.claude/CLAUDE.md"
    else
      log "left existing directive unchanged"
    fi
    return
  fi
  if [ -L "$f" ] && [ ! -e "$f" ]; then           # dangling symlink
    # shellcheck disable=SC2088  # ~ is display text in the prompt, not a path
    ask_yn "~/.claude/CLAUDE.md is a broken symlink — replace it with a real file holding the directive?" y \
      && { rm -f "$f"; emit_routing_block >"$f"; log "wrote ~/.claude/CLAUDE.md (real file)"; }
    return
  fi
  if [ -e "$f" ]; then
    if ask_yn "Append the SOTA routing directive to $where?" y; then
      backup "$f"; { printf '\n'; emit_routing_block; } >>"$f"; log "appended directive to ~/.claude/CLAUDE.md"
    else
      log "skipped — copy the block from README's 'Always-on routing' yourself"
    fi
  else
    ask_yn "Create ~/.claude/CLAUDE.md with the SOTA routing directive?" y \
      && { mkdir -p "$(dirname "$f")"; emit_routing_block >"$f"; log "created ~/.claude/CLAUDE.md"; }
  fi
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
        cat "$tmp" >"$s"; log "refreshed sota UserPromptSubmit hook to latest wording"
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
      log "added UserPromptSubmit hook to ~/.claude/settings.json"
    else
      warn "could not parse $s as JSON — left unchanged"
    fi
  else
    mkdir -p "$(dirname "$s")"
    jq -n --arg c "$HOOK_CMD" '{hooks:{UserPromptSubmit:[{hooks:[{type:"command",command:$c}]}]}}' >"$s"
    log "created ~/.claude/settings.json with the hook"
  fi
  rm -f "$tmp"
}

maybe_setup_routing() {
  # personal install only; never for --project or --copy snapshots
  [ "$TARGET" = "$HOME/.claude/skills" ] && [ "$USE_COPY" -eq 0 ] || return 0
  local go=0
  case "$DO_ROUTING" in
    1) go=1 ;;
    0) return 0 ;;
    *) if [ "$INTERACTIVE" -eq 1 ] || [ "$ASSUME_YES" -eq 1 ]; then
         ask_yn "Set up always-on routing (global directive + prompt hook) so skills apply without trigger words?" y && go=1
       fi ;;
  esac
  [ "$go" -eq 1 ] || return 0
  setup_claude_md
  setup_hook
}

while [ $# -gt 0 ]; do
  case "$1" in
    --update)     DO_UPDATE=1 ;;
    --copy)       USE_COPY=1 ;;
    --project)    shift; [ $# -gt 0 ] || die "--project needs a directory"; TARGET="$1/.claude/skills" ;;
    --routing)    DO_ROUTING=1 ;;
    --no-routing) DO_ROUTING=0 ;;
    --yes|-y)     ASSUME_YES=1 ;;
    -h|--help)    usage 0 ;;
    *)            die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

[ -d "$SKILLS_SRC" ] || die "no skills/ dir at $SKILLS_SRC — run from a SOTA-skills checkout"

# --- optional self-update ----------------------------------------------------
if [ "$DO_UPDATE" -eq 1 ]; then
  if git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log "updating $(basename "$REPO") (git pull --ff-only)…"
    git -C "$REPO" pull --ff-only || die "pull failed — resolve manually, then re-run"
  else
    warn "$REPO is not a git checkout — skipping --update"
  fi
fi

mkdir -p "$TARGET"

# --- link (or copy) every skill, idempotently --------------------------------
linked=0; created=0
for src in "$SKILLS_SRC"/*/; do
  name="$(basename "$src")"
  dest="$TARGET/$name"
  [ -e "$dest" ] || [ -L "$dest" ] || created=$((created + 1))
  if [ "$USE_COPY" -eq 1 ]; then
    rm -rf "$dest"
    cp -R "${src%/}" "$dest"
  else
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
      "$SKILLS_SRC"/*) [ -e "$tgt" ] || { rm -f "$dest"; pruned=$((pruned + 1)); log "pruned stale link: $(basename "$dest")"; } ;;
    esac
  done
fi

log "linked $linked skill(s) into $TARGET ($created new, $pruned pruned)$([ "$USE_COPY" -eq 1 ] && echo ' [copied]')"

# --- profile convenience (personal install only) -----------------------------
if [ "$TARGET" = "$HOME/.claude/skills" ] && [ "$USE_COPY" -eq 0 ]; then
  prof="$(find "$REPO/profiles" -maxdepth 1 -name '*.md' ! -name 'example.md.template' 2>/dev/null | head -n1 || true)"
  if [ -n "$prof" ]; then
    mkdir -p "$HOME/.claude/profiles"
    ln -sfn "$prof" "$HOME/.claude/profiles/$(basename "$prof")"
    log "linked profile: ~/.claude/profiles/$(basename "$prof")"
  else
    log "no profile yet — cp profiles/example.md.template profiles/<you>.md, then re-run"
  fi
fi

maybe_setup_routing

cat <<NEXT

Done. To update later:
  git -C "$REPO" pull   # existing skills update live (symlinks); then…
  "$REPO/scripts/install.sh"   # …re-link to pick up any new skills

Or in one step:  scripts/install.sh --update
NEXT
