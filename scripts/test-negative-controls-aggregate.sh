#!/usr/bin/env bash
#
# Known-bads for check-negative-controls.sh --aggregate (2026-10-28).
#
# The aggregator is the verdict once CI shards the harness: a shard that did not report, a
# gap or an overlap in the probe ordinals, an aborted shard, a failed probe, shards that ran
# different harnesses, or coverage short of the COVERED line must each FAIL, and FAIL for
# its own reason, while a complete set of good manifests passes. Each case asserts the
# specific message, so a catch for the wrong reason is refused, as the harness does.
# Synthetic manifests only: no gate runs, a second or two.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
H=scripts/check-negative-controls.sh
A=$(mktemp -d)
trap 'rm -rf "$A"' EXIT

# The COVERED ids, read from the harness itself, so this test follows the declaration.
cov=$(sed -n 's/.*COVERED: \([0-9, ]*\) ([0-9]* of [0-9]*).*/\1/p' "$H" | head -1 | tr -d ',')
[ -n "$cov" ] || { echo "FAIL: could not read the COVERED ids from $H"; exit 1; }

m() {  # <case> <shard> <total> <tested> <failed> <ords> <probed> <complete y|n>
  mkdir -p "$A/$1"
  {
    echo "shards=2"; echo "shard=$2"; echo "total=$3"; echo "tested=$4"
    echo "caught=$(($4 - $5))"; echo "failed=$5"; echo "ords=$6"; echo "probed=$7"; echo "skipped="
    if [ "$8" = y ]; then echo "complete=yes"; fi
  } > "$A/$1/s$2.manifest"
}
m good       0 4 2 0 "1 3"   "$cov" y; m good       1 4 2 0 "2 4"   "" y
m missing    0 4 2 0 "1 3"   "$cov" y
m gap        0 4 2 0 "1 3"   "$cov" y; m gap        1 4 1 0 "2"     "" y
m dup        0 4 2 0 "1 3"   "$cov" y; m dup        1 4 3 0 "2 3 4" "" y
m incomplete 0 4 2 0 "1 3"   "$cov" y; m incomplete 1 4 2 0 "2 4"   "" n
m failed     0 4 2 1 "1 3"   "$cov" y; m failed     1 4 2 0 "2 4"   "" y
m totals     0 4 2 0 "1 3"   "$cov" y; m totals     1 5 2 0 "2 4"   "" y
m coverage   0 4 2 0 "1 3"   "1 2 3" y; m coverage  1 4 2 0 "2 4"   "" y
mkdir -p "$A/empty"

pass=0; bad=0
expect() {  # <case> <want rc> <substring>
  local out rc=0
  out=$(bash "$H" --aggregate "$A/$1" 2>&1) || rc=$?
  if [ "$rc" -eq "$2" ] && case "$out" in (*"$3"*) true ;; (*) false ;; esac; then
    echo "  [$1] ok"; pass=$((pass + 1))
  else
    echo "  [$1] WRONG: rc=$rc, expected rc=$2 and '$3'"
    printf '%s\n' "$out" | tail -3 | sed 's/^/        got: /'
    bad=$((bad + 1))
  fi
}
expect good       0 "PASS: 4/4 mutations caught"
expect missing    1 "a shard did not report"
expect gap        1 "the shards left a gap"
expect dup        1 "ran in more than one shard"
expect incomplete 1 "that shard aborted"
expect failed     1 "were not caught by the check they target"
expect totals     1 "shards disagree on the probe count"
expect coverage   1 "but the COVERED line declares"
expect empty      1 "nothing ran"

total=$((pass + bad))
[ "$total" -eq 9 ] || { echo "FAIL: ran $total of 9 cases"; exit 1; }
[ "$bad" -eq 0 ] || { echo "FAIL: $bad of $total aggregator cases wrong"; exit 1; }
echo "PASS: $pass/$total aggregator cases (1 good, 8 known-bad, each for its own reason)."
