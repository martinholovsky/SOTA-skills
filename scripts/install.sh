#!/usr/bin/env bash
#
# install.sh — link the SOTA skills into Claude Code, and update them later.
#
# Installation is symlink-based, so this script is also the updater: re-run it
# after `git pull` and it links any newly-added skills and prunes links to
# skills that were removed/renamed. Existing skills update with no action at all
# (the symlinks already point at the live files).
#
# Usage:
#   scripts/install.sh                 # link skills into ~/.claude/skills (all projects)
#   scripts/install.sh --project DIR   # link into DIR/.claude/skills (one project)
#   scripts/install.sh --update        # git pull --ff-only first, then re-link
#   scripts/install.sh --copy          # copy instead of symlink (pin a snapshot)
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

log()  { printf '  %s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

usage() { sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --update)  DO_UPDATE=1 ;;
    --copy)    USE_COPY=1 ;;
    --project) shift; [ $# -gt 0 ] || die "--project needs a directory"; TARGET="$1/.claude/skills" ;;
    -h|--help) usage 0 ;;
    *)         die "unknown argument: $1 (try --help)" ;;
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

cat <<NEXT

Done. To update later:
  git -C "$REPO" pull   # existing skills update live (symlinks); then…
  "$REPO/scripts/install.sh"   # …re-link to pick up any new skills

Or in one step:  scripts/install.sh --update
NEXT
