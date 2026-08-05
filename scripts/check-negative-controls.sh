#!/usr/bin/env bash
#
# Negative controls for check-invariants.sh — proof the gate can still FAIL.
#
# WHY THIS EXISTS. check-invariants.sh prints "ok" fifteen times on a clean tree.
# So does a check whose pathspec drifted, whose predicate stopped matching, or
# that was quietly disabled. Those states are typographically identical, and this
# repo's own library calls that an inert control: `sota-code-security` rules/12 §1
# (mutation-probe every control), §2.2 (an instrument needs a known-bad it must
# reject and a known-good it must pass), and `sota-devsecops` rules/05 §5.6, which
# says outright that no mainstream framework requires evidence a gate CAN fail.
# We required that of everyone else and did not do it here. This closes that.
#
# WHAT IT DOES. For each mutation below: apply a known-bad to a disposable copy of
# the tree, run the gate, and require BOTH
#   (a) a non-zero exit, and
#   (b) the EXPECTED check to be the one that complained.
# (b) is not pedantry. A harness that accepts any non-zero exit reports "18/18
# controls caught" while every run dies before the thing under test (rules/12
# §2.1, "the instrument that cannot fail"). A mutation caught for the wrong reason
# is a FALSE PASS and is reported as one.
#
# POSITIVE CONTROL FIRST. The unmutated copy must exit 0. If it does not, the
# harness is measuring nothing and aborts rather than reporting results — a
# known-bad that "fails" in a tree that already fails proves nothing.
#
# ASSERT THE MUTATION TOOK. The copy is a git worktree at HEAD, so it would carry
# the COMMITTED gate, not the one being edited. The working-tree gate is copied in
# and byte-compared, because "the code you changed may not be the code that ran"
# is the trap rules/12 §2.2 names explicitly.
#
# Scope: invariants 1, 2, 6, 10 and 15 — the five with a cheap, unambiguous
# known-bad. The others are diff-, history- or release-shaped and need a fixture
# with real commits; they are NOT covered, and this script says so rather than
# implying whole-gate coverage.
#
# Portable to macOS bash 3.2 (no associative arrays).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
REPO=$(pwd)
GATE=scripts/check-invariants.sh
[ -f "$GATE" ] || { echo "FAIL: $GATE not found"; exit 1; }

WT=$(mktemp -d)/wt
cleanup() { git worktree remove --force "$WT" >/dev/null 2>&1 || true; rm -rf "$(dirname "$WT")"; }
trap cleanup EXIT

echo "Negative controls for $GATE"
echo "  disposable worktree: $WT"
git worktree add --detach "$WT" HEAD >/dev/null 2>&1 || {
  echo "FAIL: could not create a worktree (need a clean git repo)"; exit 1; }

# The worktree is at HEAD; test the gate we HAVE, not the gate we shipped.
cp "$REPO/$GATE" "$WT/$GATE"
cmp -s "$REPO/$GATE" "$WT/$GATE" || { echo "FAIL: gate copy did not take"; exit 1; }

# One gate run per probe: capture output AND status together. Running it twice
# doubles a ~10s check and invites the two runs to disagree.
GATE_OUT=""
GATE_RC=0
run_gate() {
  GATE_RC=0
  GATE_OUT=$( cd "$WT" && bash "./$GATE" 2>&1 ) || GATE_RC=$?
}

# --- positive control -----------------------------------------------------
printf '  [positive control] clean copy must PASS ... '
run_gate
if [ "$GATE_RC" -eq 0 ]; then
  echo "ok"
else
  echo "FAIL"
  echo
  echo "The unmutated copy does not pass. Every result below would be meaningless,"
  echo "so nothing was run. Fix the tree (or the gate) first:"
  printf '%s\n' "$GATE_OUT" | tail -20
  exit 1
fi

# --- mutations ------------------------------------------------------------
# Each entry: id | human name | mutate fn | expected substring in the gate output.
tested=0
caught=0
failed=0

# `git checkout -- .` + `git clean -fd` is NOT enough: git clean leaves files that
# have been `git add`-ed, so probe 10's staged file leaked into probe 15, which
# then failed on check 6 (file count 299) instead of check 15. The (b) assertion
# reported that as a FALSE PASS on the first run of this harness — which is the
# whole reason (b) is there. `git reset --hard` clears the index too; it also
# reverts the gate we deliberately copied in, so the copy is redone and re-verified.
restore() {
  ( cd "$WT" && git reset -q --hard HEAD && git clean -fdq ) >/dev/null 2>&1 || true
  cp "$REPO/$GATE" "$WT/$GATE"
  cmp -s "$REPO/$GATE" "$WT/$GATE" || { echo "FAIL: gate copy did not survive restore"; exit 1; }
}

probe() {  # <id> <name> <expected substring>   — mutation already applied
  local id="$1" name="$2" want="$3"
  tested=$((tested + 1))
  run_gate
  if [ "$GATE_RC" -eq 0 ]; then
    echo "  [$id] $name — NOT CAUGHT: the gate still passed. This check is INERT."
    failed=$((failed + 1))
  elif printf '%s\n' "$GATE_OUT" | grep -qF -- "$want"; then
    echo "  [$id] $name — caught"
    caught=$((caught + 1))
  else
    echo "  [$id] $name — FALSE PASS: gate failed, but not for this reason."
    echo "        expected to see: $want"
    printf '%s\n' "$GATE_OUT" | grep -E '^ +[A-Z]' | head -3 | sed 's/^ */        got: /'
    failed=$((failed + 1))
  fi
  restore
}

# 1 — line budget: a rules file over the 500-line cap.
target="skills/sota-code-security/rules/12-verifying-the-verifier.md"
( cd "$WT" && awk 'BEGIN{for(i=0;i<600;i++) print "padding line to breach the cap"}' >> "$target" )
probe 1 "line budget (rules file over 500 lines)" "OVER 500"

# 2 — every rules file ends with an Audit checklist.
( cd "$WT" && perl -0pi -e 's/^## Audit checklist$/## Not A Checklist/m' "$target" )
probe 2 "audit checklist missing from a rules file" "MISSING/NOT-LAST '## Audit checklist'"

# 6 — count-bearing surfaces match the tree.
( cd "$WT" && perl -0pi -e 's/\*\*41 skills \(298 files/**41 skills (999 files/' README.md )
probe 6 "README file count drifted from the tree" "README hero file count"

# 10 — a rules file its own SKILL.md never indexes.
( cd "$WT" && cp "$target" "skills/sota-code-security/rules/99-unindexed-probe.md" \
    && git add -A >/dev/null 2>&1 )
probe 10 "rules file not referenced by its own SKILL.md" "not referenced in"

# 15 — the router's library map omits a rules file that exists.
( cd "$WT" && perl -0pi -e 's/10 silent control failure, 11 dead-path diagnostics, /10 silent control failure, /' skills/sota/SKILL.md )
probe 15 "router library map omits an existing rules file" "map missing:"

# --- result ---------------------------------------------------------------
echo
if [ "$tested" -eq 0 ]; then
  echo "FAIL: 0 mutations tested — an empty negative-control run proves nothing."
  exit 1
fi
if [ "$failed" -ne 0 ]; then
  printf 'FAIL: %d of %d mutations were not caught by the check they target.\n' "$failed" "$tested"
  exit 1
fi
printf 'PASS: %d/%d mutations caught by the intended check.\n' "$caught" "$tested"
echo "      Covers invariants 1, 2, 6, 10, 15. The diff-, history- and"
echo "      release-shaped checks (5, 8, 9, 11, 12, 13, 14) are NOT covered."
