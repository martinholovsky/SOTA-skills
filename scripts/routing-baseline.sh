#!/usr/bin/env bash
#
# routing-baseline.sh — re-measure the description classifier, LOCALLY.
#
# WHY THIS EXISTS. Routing is the library's entry point: if a task does not reach the
# right skill, 100% of that skill's content is unreachable however good it is. It is
# also the one measurement that can regress with NO diff in this repo, because the
# classifier is a model evaluating 42 competing descriptions — when the model changes,
# the ranking can change and every invariant stays green. Invariant 29 only fires on a
# release whose own description map moved, so nothing here watches model drift.
#
# DELIBERATELY LOCAL, AND DELIBERATELY NOT A GATE.
#   - Local: this repo is public, and a scheduled Actions run would need
#     OPENROUTER_API_KEY as a repository secret. No API key is stored in this repo or in
#     CI. The run happens on a maintainer's machine; CI only checks that it happened
#     recently, which needs no credential (scripts/check-freshness.sh).
#   - Not a gate: a model-scored eval is not deterministic, and docs/CONVENTIONS-LEDGER.md
#     is explicit that a flaky gate gets disabled, leaving you worse off than none. So
#     this reports and stamps; it never blocks a merge.
#
# It writes two things:
#   evals/results/<date>/routing-baseline.json   the run itself
#   evals/ROUTING-BASELINE                       a one-line stamp CI can read
#
# WHICH SET. The default is the 10-case adversarially-confusable golden set
# (desc-routing.jsonl), because drift is what this watches and that set is built to
# discriminate. The 4-case desc-routing-regressions.jsonl is the *pinned mis-route* set
# invariant 29 asks a release to run; it sits at 1.00/1.00, so it can only ever report a
# DROP -- useful as an alarm, useless as a measurement, since a saturating instrument
# proves it cannot tell rather than that nothing changed. Run either with --cases.
#
# Usage: scripts/routing-baseline.sh [--samples N] [--model M] [--cases FILE]
#
# Portable to macOS bash 3.2.
set -euo pipefail

SAMPLES=3
MODEL="anthropic/claude-sonnet-4.6"
CASES="evals/cases/desc-routing.jsonl"

while [ $# -gt 0 ]; do
  case "$1" in
    --samples) shift; SAMPLES="${1:?--samples needs a number}" ;;
    --model)   shift; MODEL="${1:?--model needs a name}" ;;
    --cases)   shift; CASES="${1:?--cases needs a path}" ;;
    -h|--help) sed -n '2,28p' "$0"; exit 0 ;;
    *) printf 'error: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

cd "$(dirname "$0")/.."

[ -f "$CASES" ] || { printf 'error: case set not found: %s\n' "$CASES" >&2; exit 1; }

# The key is read by the runner itself from env or ./.env (which is git-ignored).
# Checked for PRESENCE here only, and never printed, so a missing key fails with a
# usable message instead of a stack trace 40 seconds in.
if [ -z "${OPENROUTER_API_KEY:-}" ] && ! grep -q '^OPENROUTER_API_KEY=' .env 2>/dev/null; then
  printf 'error: no OPENROUTER_API_KEY in env or ./.env — this run needs one.\n' >&2
  printf 'It is deliberately NOT in CI: see the header of this script.\n' >&2
  exit 1
fi

DATE=$(date +%F)
OUT="evals/results/${DATE}/routing-baseline.json"
mkdir -p "evals/results/${DATE}"

printf 'routing baseline: %s cases, %s samples, model %s\n' \
  "$(grep -c '^{' "$CASES" || true)" "$SAMPLES" "$MODEL"

python3 evals/run-desc-routing.py \
  --cases "$CASES" --samples "$SAMPLES" --model "$MODEL" --out "$OUT"

# The score is READ BACK from the artifact the run just wrote, not carried in a shell
# variable from before it: reading back is what proves the file on disk says what the
# run reported (sota-code-security rules/15 — read back the artifact this run produced).
SCORE=$(python3 - "$OUT" <<'SCOREPY'
import json, sys
# The number lives under summary[<arm>], not at the top level. The first draft guessed
# top-level keys, found none, and wrote the literal string "unparsed" into the stamp -- a
# stamp recording the READER failing rather than the thing measured. Read back what the run
# actually wrote (sota-code-security rules/15), and fail loudly rather than stamping a word.
d = json.load(open(sys.argv[1]))
summ = d.get("summary")
if not isinstance(summ, dict) or not summ:
    sys.exit("routing-baseline: no 'summary' in %s" % sys.argv[1])
arm = "with-xref" if "with-xref" in summ else sorted(summ)[0]
v = summ[arm]
if not isinstance(v, dict):
    print(v)
    raise SystemExit
for k in ("correct", "score", "accuracy", "recall"):
    if k in v:
        print("%.3f" % float(v[k]))
        break
else:
    sys.exit("routing-baseline: no score key in summary[%r]: %s" % (arm, sorted(v)))
SCOREPY
)

PREV=""
[ -f evals/ROUTING-BASELINE ] && PREV=$(grep -v '^#' evals/ROUTING-BASELINE | head -1 || true)

{
  printf '# Last LOCAL routing baseline. Written by scripts/routing-baseline.sh.\n'
  printf '# CI never runs the measurement (no API key in this repo); it only checks this\n'
  printf '# date is recent — scripts/check-freshness.sh. Format: DATE SCORE MODEL CASES\n'
  printf '%s %s %s %s\n' "$DATE" "$SCORE" "$MODEL" "$CASES"
} > evals/ROUTING-BASELINE

printf '\nbaseline written: %s\n' "$OUT"
printf 'stamp: %s %s %s\n' "$DATE" "$SCORE" "$MODEL"
[ -n "$PREV" ] && printf 'previous: %s\n' "$PREV"
printf '\nA drop against the previous line is the signal. It is not a gate — read it.\n'
