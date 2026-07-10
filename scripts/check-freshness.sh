#!/usr/bin/env bash
#
# check-freshness.sh — report the verification freshness of the library.
#
# The library promises that fast-moving claims are verified against primary
# sources. Since 2026-07 that promise is tracked with a SINGLE library-level
# stamp: the root `LAST-VERIFIED` file holds the date (YYYY-MM-DD) of the last
# full-library re-verification sweep (per-skill research against primary
# sources — see the runbook in docs/MAINTENANCE.md). Update it only after such
# a sweep, not on ordinary edits (git history already records those).
#
# This script:
#   - fails (exit 1) if the stamp is older than the re-verify window
#     (default 6 months — content drifts far faster than the old 12-month
#     window allowed, per the 2026-07-10 audit; 6mo stays clearable so a red
#     report stays meaningful rather than perpetually-ignored);
#   - warns about any stray per-file `<!-- last-verified: ... -->` line-1
#     markers (the pre-2026-07 convention; they should no longer exist).
#
# Usage: scripts/check-freshness.sh [--window-months N]
#
# Portable to macOS bash 3.2. Run by .github/workflows/freshness.yml monthly.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

WINDOW=6
while [ $# -gt 0 ]; do
  case "$1" in
    --window-months) shift; WINDOW="${1:?--window-months needs a number}" ;;
    --list-unstamped) ;; # accepted for compatibility with older callers; no-op
    *) printf 'error: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

if [ ! -f LAST-VERIFIED ]; then
  echo "error: LAST-VERIFIED file missing — the library has no verification stamp" >&2
  exit 1
fi

stamp=$(tr -d '[:space:]' < LAST-VERIFIED)
case "$stamp" in
  [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
  *) echo "error: LAST-VERIFIED must contain a YYYY-MM-DD date, got: '$stamp'" >&2; exit 1 ;;
esac

y=${stamp%%-*}
m=${stamp#*-}; m=${m%%-*}
now_y=$(date +%Y)
now_m=$(date +%m)
age=$(( (now_y * 12 + ${now_m#0}) - (y * 12 + ${m#0}) ))

total=$(git ls-files 'skills/*/rules/*.md' | wc -l | tr -d ' ')
echo "Freshness report (window: ${WINDOW} months) — ${total} rules files"
echo "  library last-verified: ${stamp}  (${age} months ago)"

# Stray per-file markers from the retired per-file convention.
stray=$(git grep -lE '^<!-- last-verified: [0-9]{4}-[0-9]{2}' -- 'skills/*/rules/*.md' || true)
if [ -n "$stray" ]; then
  echo
  echo "WARNING: stray per-file last-verified markers (retired convention — remove them):"
  printf '%s\n' "$stray" | sed 's/^/    /'
fi

if [ "$age" -gt "$WINDOW" ]; then
  echo
  echo "STALE: last full-library verification sweep was ${age} months ago (window ${WINDOW})."
  echo "Run a re-verification sweep against primary sources, apply fixes, then update LAST-VERIFIED."
  exit 1
fi
