#!/usr/bin/env bash
#
# check-freshness.sh — report the verification freshness of every rules file.
#
# The library promises that fast-moving claims are verified against primary
# sources. This makes that promise auditable: a rules file whose claims have
# been (re-)verified carries, as its FIRST line, the marker
#
#   <!-- last-verified: YYYY-MM -->
#
# and this script reports every skills/*/rules/*.md that is either
#   - STALE:     marker older than the re-verify window (default 12 months), or
#   - UNSTAMPED: no marker — the file's claims have never been dated.
#
# Exit code: 1 if any STAMPED file is past the window (a red scheduled run is
# the re-verify signal), 0 otherwise. Unstamped files are reported as debt but
# do not fail the run — they would keep it red forever and train everyone to
# ignore it; the count trending to zero is the goal.
#
# Usage: scripts/check-freshness.sh [--window-months N] [--list-unstamped]
#
# Portable to macOS bash 3.2. Run by .github/workflows/freshness.yml monthly.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

WINDOW=12
LIST_UNSTAMPED=0
while [ $# -gt 0 ]; do
  case "$1" in
    --window-months) shift; WINDOW="${1:?--window-months needs a number}" ;;
    --list-unstamped) LIST_UNSTAMPED=1 ;;
    *) printf 'error: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

now_y=$(date +%Y)
now_m=$(date +%m)
now_idx=$((now_y * 12 + ${now_m#0}))

total=0 fresh=0 stale=0 unstamped=0
stale_list="" unstamped_list=""

while IFS= read -r f; do
  [ -f "$f" ] || continue
  total=$((total + 1))
  first=$(head -n 1 "$f")
  case "$first" in
    '<!-- last-verified: '[0-9][0-9][0-9][0-9]-[0-9][0-9]' -->')
      ym=${first#'<!-- last-verified: '}
      ym=${ym%' -->'}
      y=${ym%-*}; m=${ym#*-}
      idx=$((y * 12 + ${m#0}))
      age=$((now_idx - idx))
      if [ "$age" -gt "$WINDOW" ]; then
        stale=$((stale + 1))
        stale_list="${stale_list}    ${f}  (last-verified ${ym}, ${age} months ago)
"
      else
        fresh=$((fresh + 1))
      fi
      ;;
    *)
      unstamped=$((unstamped + 1))
      unstamped_list="${unstamped_list}    ${f}
"
      ;;
  esac
done < <(git ls-files 'skills/*/rules/*.md')

echo "Freshness report (window: ${WINDOW} months) — ${total} rules files"
echo "  fresh:     ${fresh}"
echo "  stale:     ${stale}"
echo "  unstamped: ${unstamped}  (never dated — verification debt)"
if [ "$stale" -gt 0 ]; then
  echo
  echo "STALE — re-verify against primary sources, then update the marker:"
  printf '%s' "$stale_list"
fi
if [ "$LIST_UNSTAMPED" -eq 1 ] && [ "$unstamped" -gt 0 ]; then
  echo
  echo "UNSTAMPED:"
  printf '%s' "$unstamped_list"
fi

[ "$stale" -eq 0 ] || exit 1
