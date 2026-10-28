#!/usr/bin/env bash
#
# Pre-push mirror of two CI steps that pass locally only if someone remembers them.
#
# WHY. Field-reported three times (2026-10-25 twice, 2026-10-28 once): a branch passed every
# local gate and went red in CI on (1) a stale docs/skill-map.* and (2) shellcheck, run here at a
# lower severity than CI's `-S style`. A memory note naming the gap did not prevent the third
# occurrence, so the step is mechanical now. The commands below are CI's own (ci.yml, "Skill map
# is current" and "shellcheck scripts/ and tracked *.sh"); keep them identical.
#
# LIMIT, stated so a green here is not over-read: a local shellcheck may be older than CI's, and
# CI's reported SC2015 where a local one did not (2026-10-28). This narrows the gap; CI decides.
#
# A missing shellcheck FAILS with the install command rather than skipping (router principle 6:
# a tool the check needs is a question, not a skip). To push without it on purpose:
# SKIP=ci-mirror git push   (pre-commit's documented per-hook skip), and CI still runs it.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
fail=0

# --- 1. skill map is current (ci.yml, "Skill map is current") -------------------------------
python3 scripts/gen-skill-map.py >/dev/null
if ! git diff --quiet -- docs/skill-map.drawio docs/skill-map.json; then
  echo "FAIL: docs/skill-map.* is stale. Run: python3 scripts/gen-skill-map.py && git add docs/skill-map.* && git commit"
  git diff --stat -- docs/skill-map.drawio docs/skill-map.json
  fail=1
else
  echo "ok: skill map is current"
fi

# --- 2. shellcheck at CI's severity (ci.yml, "shellcheck scripts/ and tracked *.sh") --------
if ! command -v shellcheck >/dev/null; then
  echo "FAIL: shellcheck is not installed; CI runs it at -S style. Install it (macOS: brew install shellcheck; Debian: apt-get install shellcheck), or push with SKIP=ci-mirror."
  exit 1
fi
files=$(git ls-files '*.sh' ':!scripts/probe-fixtures/')
[ -n "$files" ] || { echo "FAIL: no shell files matched — pathspec drift"; exit 1; }
n=$(printf '%s\n' "$files" | wc -l | tr -d ' ')
# shellcheck disable=SC2086  # word splitting is intended: a file list, as in ci.yml
if shellcheck -S style --enable=check-unassigned-uppercase $files; then
  echo "ok: shellcheck -S style over $n tracked shell files ($(shellcheck --version | sed -n 's/^version: //p'))"
else
  echo "FAIL: shellcheck -S style over $n tracked shell files"
  fail=1
fi

exit "$fail"
