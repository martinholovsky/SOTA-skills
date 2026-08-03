#!/usr/bin/env bash
#
# update.sh — pull the latest SOTA-skills and re-link the skills.
#
# This is a thin alias for `install.sh --update`, and deliberately nothing more.
# Installation is symlink-based, so the installer *is* the updater — but that is
# a design detail, and nobody browsing `scripts/` should have to know a flag to
# find the update path. Discoverability is the entire reason this file exists.
#
# Every install.sh flag works here and is forwarded untouched:
#
#   scripts/update.sh                    # git pull --ff-only, then re-link
#   scripts/update.sh --yes              # take the recommended answer to prompts
#   scripts/update.sh --project DIR      # update a project-local install
#   scripts/update.sh --no-color         # plain output (see install.sh --help)
#   scripts/update.sh --help             # install.sh's help — it owns every flag
#
# It holds NO logic of its own on purpose: a wrapper carrying its own copy of
# the update rules is a wrapper that silently drifts from them. If you came here
# to change update behaviour, change install.sh instead.
set -euo pipefail

dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$dir/install.sh" --update "$@"
