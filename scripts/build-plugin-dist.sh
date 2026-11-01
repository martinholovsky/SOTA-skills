#!/usr/bin/env bash
#
# build-plugin-dist.sh — build the slim plugin tree the Claude plugin directory tracks.
#
#   scripts/build-plugin-dist.sh OUT [REF]     # REF defaults to HEAD
#
# WHY. The directory validates the repository archive of the branch it follows, and refuses
# one holding 10,000 files and folders or more ("Repository too large to validate",
# claude.com/docs/plugins/pre-submission-checklist). main holds about 17,000, almost all of
# them probe fixtures, so the directory follows a generated branch, plugin-dist, holding only
# what the plugin loads. RELEASING.md §4b has the release flow; plugin-dist.yml runs it.
#
# AN ALLOWLIST, READ FROM GIT. Every shipped path is named below, and the tree comes from
# `git archive REF`, so an untracked or ignored file in the caller's checkout can never ship
# and a path added to the repo ships only when someone adds it here. A named path missing at
# REF fails the build: a silent drop would ship a plugin whose hook points at nothing.
#
# WHAT SHIPS, and why each script is here:
#   - the six hook targets in hooks/hooks.json;
#   - scripts/skill-listing-sources.sh, which plugin-budget-check.sh runs;
#   - scripts/install.sh, read as TEXT by plugin-routing-hook.sh (it greps HOOK_CMD out of it,
#     so the reminder has one source). It is not an installer here: it names files that do not
#     ship (update.sh, verify-setup.sh), and plugin/README.md says so;
#   - the three extras plugin-notice.sh tells the user "ship with the plugin":
#     statusline.sh, init-gates.sh and gen-agents-md.sh.
# plugin/README.md becomes the tree's README.md (the listing text), and SOURCE_COMMIT records
# the commit the tree was built from. .claude-plugin/marketplace.json does not ship: the
# directory is the marketplace for this tree.
#
# OUT must not exist yet, or be an empty directory, so a rebuild cannot keep a stale file.
# Exit: 0 built, 1 a named path is missing or the extracted tree disagrees with git, 2 usage.
set -euo pipefail

usage() { sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'; exit "${1:-0}"; }
die() { printf 'build-plugin-dist: %s\n' "$*" >&2; exit 1; }

case "${1:-}" in -h | --help) usage 0 ;; '') usage 2 >&2 ;; esac
out=$1
ref=${2:-HEAD}

readonly ALLOW=(
  .claude-plugin/plugin.json
  .claude-plugin/icon.png
  VERSION
  LICENSE
  LICENSE-APACHE
  SECURITY.md
  plugin/README.md
  skills
  commands
  hooks
  scripts/plugin-budget-check.sh
  scripts/plugin-notice.sh
  scripts/update-reminder.sh
  scripts/plugin-routing-hook.sh
  scripts/code-rules-hook.py
  scripts/zsh-equals-hook.py
  scripts/skill-listing-sources.sh
  scripts/install.sh
  scripts/statusline.sh
  scripts/init-gates.sh
  scripts/gen-agents-md.sh
)

repo=$(git rev-parse --show-toplevel 2>/dev/null) || die "not inside a git repository"
cd -- "$repo"
sha=$(git rev-parse --verify --quiet "${ref}^{commit}") || die "no commit named '$ref'"

if [ -e "$out" ]; then
  [ -d "$out" ] || die "$out exists and is not a directory"
  [ -z "$(ls -A -- "$out")" ] || die "$out is not empty: give a new or empty directory"
else
  mkdir -p -- "$out"
fi
out=$(cd -- "$out" && pwd -P)

for p in "${ALLOW[@]}"; do
  git cat-file -e "${sha}:${p}" 2>/dev/null || die "allowlisted path '$p' does not exist at $ref (${sha:0:12})"
done

# The denominator: how many files git holds under the allowlist, to compare with what landed.
want=$(git ls-tree -r --name-only "$sha" -- "${ALLOW[@]}" | wc -l | tr -d ' ')
[ "$want" -gt 0 ] || die "the allowlist matched 0 files at $ref"

git archive --format=tar "$sha" -- "${ALLOW[@]}" | tar -xf - -C "$out"
# A tracked symlink extracts as a link, and a later entry written through it lands outside OUT
# (the tar-slip shape, sota-code-security rules/09 §2). The directory also blocks a symlink the
# plugin loads, so refuse every one here, before anything is moved or counted.
links=$(find "$out" -type l | wc -l | tr -d ' ')
[ "$links" -eq 0 ] || die "$links symlink(s) arrived from $ref: $(find "$out" -type l | head -3 | tr '\n' ' ')"
got=$(find "$out" -type f | wc -l | tr -d ' ')
# A mismatch means .gitattributes export-ignore/export-subst touched the archive, which the
# directory itself refuses (pre-submission checklist), or tar dropped something.
[ "$got" -eq "$want" ] || die "git holds $want files under the allowlist, the tree has $got"

[ -e "$out/README.md" ] && die "a root README.md arrived through the allowlist; the listing text is plugin/README.md"
mv -- "$out/plugin/README.md" "$out/README.md"
rmdir -- "$out/plugin"
printf '%s\n' "$sha" > "$out/SOURCE_COMMIT"

entries=$(find "$out" -mindepth 1 | wc -l | tr -d ' ')
files=$(find "$out" -type f | wc -l | tr -d ' ')
printf 'built %s from %s (%s): %s files, %s entries\n' "$out" "$ref" "${sha:0:12}" "$files" "$entries"
