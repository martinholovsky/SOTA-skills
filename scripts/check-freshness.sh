#!/usr/bin/env bash
#
# check-freshness.sh — report the verification freshness of the library.
#
# The library promises that fast-moving claims are verified against primary
# sources. Since 2026-07 that promise is tracked with a SINGLE library-level
# stamp: the root `LAST-VERIFIED` file holds the date (YYYY-MM-DD) of the last
# full-library re-verification sweep (per-skill research against primary
# sources — see the runbook in docs/MAINTENANCE.md). Update it only after such
# a sweep, not on ordinary edits (git history already records those) — now
# enforced by invariant 11, which compares the parsed DATE and requires either a
# sweep-shaped diff or a CHANGELOG entry naming LAST-VERIFIED.
# The file may carry '#' comment lines, which this script strips: it holds the
# rule that governs it, at the point of use (docs/CONVENTIONS-LEDGER.md).
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
RWINDOW=3
routing_stale=0
while [ $# -gt 0 ]; do
  case "$1" in
    --window-months) shift; WINDOW="${1:?--window-months needs a number}" ;;
    --routing-window-months) shift; RWINDOW="${1:?--routing-window-months needs a number}" ;;
    --list-unstamped) ;; # accepted for compatibility with older callers; no-op
    *) printf 'error: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

if [ ! -f LAST-VERIFIED ]; then
  echo "error: LAST-VERIFIED file missing — the library has no verification stamp" >&2
  exit 1
fi

# Comment lines are stripped so the stamp file can carry the rule that governs it
# AT THE POINT OF USE. The rule was previously written only in AGENTS.md,
# docs/MAINTENANCE.md and this script's header — three copies, all far from the
# file — and two sessions still proposed bumping it wrongly (see
# docs/CONVENTIONS-LEDGER.md). Proximity beats repetition.
stamp=$(grep -v '^[[:space:]]*#' LAST-VERIFIED | tr -d '[:space:]')
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
# Fail closed on an empty scope. This report already printed its denominator, but
# printing "0 rules files" and continuing is the same silent pass that
# check-invariants.sh shipped until 2026-07-30: a drifted pathspec makes the run
# green while it examines nothing (sota-code-security rules/11 §2.2).
if [ "$total" -eq 0 ]; then
  echo "error: examined 0 rules files — pathspec drift? refusing to report freshness" >&2
  exit 1
fi
echo "Freshness report (window: ${WINDOW} months) — ${total} rules files"
echo "  library last-verified: ${stamp}  (${age} months ago)"

# Stray per-file markers from the retired per-file convention.
stray=$(git grep -lE '^<!-- last-verified: [0-9]{4}-[0-9]{2}' -- 'skills/*/rules/*.md' || true)
if [ -n "$stray" ]; then
  echo
  echo "WARNING: stray per-file last-verified markers (retired convention — remove them):"
  printf '%s\n' "$stray" | sed 's/^/    /'
fi

# --- Freshness CASE SETS age too, and that is a different decay -------------
# A fixed set of "current facts" measures LESS lift every model generation as its
# questions age INSIDE the model's training cutoff — measured 2026-08-25: the same
# 32-case set fell +0.53 -> +0.30 with the library UNCHANGED (its with-arm rose).
# So the instrument needs re-authoring on a cadence, not just once.
#
# The window is BORROWED from the LAST-VERIFIED window above, not derived from decay
# data: one before/after pair is not a decay rate, and guessing one would be inventing
# a number (roadmap item 24). It WARNS rather than fails — an ageing set still measures
# a real floor, and a perpetually-red job trains people to ignore it.
newest_set=""
newest_date=""
while IFS= read -r f; do
  d=$(sed -n 's/^#[[:space:]]*AUTHORED:[[:space:]]*\([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]\).*/\1/p' "$f" | head -1)
  [ -n "$d" ] || continue
  if [ -z "$newest_date" ] || [ "$d" \> "$newest_date" ]; then newest_date="$d"; newest_set="$f"; fi
done <<EOF
$(git ls-files 'evals/cases/freshness*.jsonl')
EOF

if [ -z "$newest_date" ]; then
  # Fail closed: no marker means this check silently verified nothing.
  echo "error: no '# AUTHORED: YYYY-MM-DD' marker in any evals/cases/freshness*.jsonl" >&2
  exit 1
fi
sy=${newest_date%%-*}; sm=${newest_date#*-}; sm=${sm%%-*}
set_age=$(( (now_y * 12 + ${now_m#0}) - (sy * 12 + ${sm#0}) ))
echo "  newest freshness case set: ${newest_set##*/} authored ${newest_date} (${set_age} months ago)"
if [ "$set_age" -gt "$WINDOW" ]; then
  echo
  echo "WARNING: the newest freshness case set is ${set_age} months old (window ${WINDOW})."
  echo "Its questions are ageing into the models' training cutoffs, so it now UNDER-reads"
  echo "the freshness claim. Re-author it (roadmap item 21 is the worked example) and quote"
  echo "the old number as a floor until you do."
fi

# --- The ROUTING baseline ages on a different clock, and nothing else watches it ---
# Routing is the library's entry point: a task that does not reach a skill gets none of
# its content. It is also the only measurement that can regress with NO diff here, because
# the classifier is a MODEL ranking 42 competing descriptions — when the model changes the
# ranking can change and every invariant stays green. Invariant 29 fires only on a release
# whose own description map moved, so model drift is unwatched by construction.
#
# THE MEASUREMENT IS LOCAL AND STAYS LOCAL. This repo is public and holds no API key; a
# scheduled Actions run would need OPENROUTER_API_KEY as a repository secret. So CI checks
# only that a maintainer ran it recently — a date comparison, needing no credential — while
# scripts/routing-baseline.sh does the run. The window is SHORTER than the content window
# above (3 vs 6 months) because the decay driver is model releases, not fact rot.
#
# Fails rather than warns: a stamp nobody must refresh is a stamp nobody refreshes, and
# this job is monthly, so it never blocks a PR.
if [ ! -f evals/ROUTING-BASELINE ]; then
  echo
  echo "MISSING: evals/ROUTING-BASELINE — no routing measurement has ever been stamped."
  echo "Run: scripts/routing-baseline.sh   (local; needs OPENROUTER_API_KEY in env or ./.env)"
  routing_stale=1
else
  rstamp=$(grep -v '^[[:space:]]*#' evals/ROUTING-BASELINE | head -1 | awk '{print $1}')
  case "$rstamp" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
    *) echo "error: evals/ROUTING-BASELINE must start with YYYY-MM-DD, got: '$rstamp'" >&2; exit 1 ;;
  esac
  ry=${rstamp%%-*}; rm_=${rstamp#*-}; rm_=${rm_%%-*}
  r_age=$(( (now_y * 12 + ${now_m#0}) - (ry * 12 + ${rm_#0}) ))
  echo "  routing baseline: ${rstamp}  (${r_age} months ago, window ${RWINDOW})"
  if [ "$r_age" -gt "$RWINDOW" ]; then
    echo
    echo "STALE: the routing baseline is ${r_age} months old (window ${RWINDOW})."
    echo "The description classifier may have re-ranked under a newer model with no diff"
    echo "in this repo. Re-run locally: scripts/routing-baseline.sh"
    routing_stale=1
  fi
fi

if [ "$age" -gt "$WINDOW" ]; then
  echo
  echo "STALE: last full-library verification sweep was ${age} months ago (window ${WINDOW})."
  echo "Run a re-verification sweep against primary sources, apply fixes, then update LAST-VERIFIED."
  exit 1
fi

if [ "$routing_stale" -ne 0 ]; then
  exit 1
fi
