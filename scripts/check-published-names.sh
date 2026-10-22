#!/usr/bin/env bash
# check-published-names.sh — run the internal-name denylist over what a push PUBLISHES besides the
# tree: the branch names and the commit messages, and on a pull request its title and body.
#
# WHY. Invariant 3 scans tracked CONTENTS (`git grep`) and tracked PATHS (`git ls-files`), and
# nothing else. On 2026-10-21 an intake branch was named after a source report whose filename
# carried an internal project name; the push published it, the PR opened from it, and a closed
# PR keeps its head-ref name, so the leak is permanent. In the same session invariant 3 caught the
# same name in a file before commit: the gate worked to the edge of its reach, and the leak sat
# past it (sota-devsecops rules/09 §2a, where a gate's reach stops).
#
# WHERE IT RUNS
#   pre-push, through pre-commit (.pre-commit-config.yaml): pre-commit hands the push over as
#     PRE_COMMIT_LOCAL_BRANCH / PRE_COMMIT_REMOTE_BRANCH / PRE_COMMIT_TO_REF / PRE_COMMIT_REMOTE_NAME.
#     It reads only the FIRST ref of a multi-ref push (pre-commit 4.6.0, hook_impl._pre_push_ns
#     returns inside its loop), so push one branch at a time.
#   CI on a pull_request (GITHUB_HEAD_REF set): the head branch name, the PR's commits
#     (HEAD^2 --not HEAD^1 on the merge checkout) and PR_TITLE / PR_BODY, passed through `env:`.
#     By then it is already public, so CI can only stop the merge; pre-push is the control.
#   by hand: the current branch and every commit not on any remote.
#
# THE LIST is invariant 3's, loaded the same way: its generic phrases read from the `DENY='…'`
# line of check-invariants.sh (as denylist-engine-parity.sh does), then $SOTA_DENYLIST, else
# .denylist.local. Matched with `grep -iE`, the engine invariant 3 uses for file names.
# Exit 0 clean, 1 a hit, 2 the check itself could not run (fails closed).
# Self-test: scripts/check-published-names.sh --self-test
set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)

load_deny() {
  DENY=$(sed -n "s/^DENY='\(.*\)'\$/\1/p" "$here/scripts/check-invariants.sh" | head -1)
  [ -n "$DENY" ] || { echo "FAIL: could not read the generic DENY phrases from check-invariants.sh"; exit 2; }
  if [ -n "${SOTA_DENYLIST:-}" ]; then
    DENY="$DENY|$SOTA_DENYLIST"; SRC="SOTA_DENYLIST"
  elif [ -f "$here/.denylist.local" ]; then
    local extra
    extra=$(grep -vE '^[[:space:]]*(#|$)' "$here/.denylist.local" | paste -sd'|' - || true)
    if [ -n "$extra" ]; then DENY="$DENY|$extra"; SRC=".denylist.local"
    else SRC="generic phrases only: .denylist.local is empty or unparseable"; fi
  else
    SRC="generic phrases only: no private denylist"
  fi
}

# hits <label> <text>: print a hit and return 1, or return 0; any grep error exits 2
hits() {
  local out rc
  set +e
  out=$(printf '%s\n' "$2" | grep -inE "$DENY")
  rc=$?
  set -e
  if [ "$rc" -gt 1 ]; then echo "FAIL: denylist grep failed (rc=$rc) on $1"; exit 2; fi
  if [ "$rc" -eq 0 ]; then
    # In CI the log is public on a public repo: name WHERE, never WHAT, or the check republishes
    # the name it exists to stop (GitHub masks the whole SOTA_DENYLIST secret, not one alternative
    # of it). Locally, at pre-push, the matched line is shown so it can be fixed.
    if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
      printf '  LEAK in %s (line %s; text withheld in CI logs)\n' "$1" "$(printf '%s\n' "$out" | cut -d: -f1 | paste -sd, -)"
    else
      printf '  LEAK in %s:\n' "$1"; printf '%s\n' "$out" | sed 's/^/      /'
    fi
    return 1
  fi
  return 0
}

main() {
  load_deny
  local names=() mode commits n_commits=0 found=0 sha
  if [ -n "${PRE_COMMIT_REMOTE_BRANCH:-}" ]; then
    mode="pre-push"
    names=("${PRE_COMMIT_LOCAL_BRANCH:-}" "$PRE_COMMIT_REMOTE_BRANCH")
    commits=$(git rev-list "${PRE_COMMIT_TO_REF:-HEAD}" --not "--remotes=${PRE_COMMIT_REMOTE_NAME:-origin}")
  elif [ -n "${GITHUB_HEAD_REF:-}" ]; then
    mode="pull request"
    names=("$GITHUB_HEAD_REF")
    if git rev-parse -q --verify 'HEAD^2' >/dev/null; then
      commits=$(git rev-list 'HEAD^2' --not 'HEAD^1')
    else
      echo "FAIL: CI checkout is not a merge commit, so the PR's commits cannot be listed"; exit 2
    fi
  else
    mode="local"
    names=("$(git rev-parse --abbrev-ref HEAD)")
    commits=$(git rev-list HEAD --not --remotes)
  fi
  [ -n "${names[0]}${names[1]:-}" ] || { echo "FAIL: no branch name to check"; exit 2; }

  echo "published-names ($mode; list: $SRC)"
  for n in "${names[@]}"; do
    [ -n "$n" ] || continue
    # the label must not carry the name either: in CI it would print what the text withholding hides
    if [ "${GITHUB_ACTIONS:-}" = "true" ]; then hits "branch name" "$n" || found=1
    else hits "branch name '$n'" "$n" || found=1; fi
  done
  while IFS= read -r sha; do
    [ -n "$sha" ] || continue
    n_commits=$((n_commits + 1))
    hits "commit ${sha:0:8} message" "$(git log -1 --format=%B "$sha")" || found=1
  done <<EOF
$commits
EOF
  local n_pr=0
  if [ -n "${PR_TITLE:-}" ]; then n_pr=$((n_pr + 1)); hits "PR title" "$PR_TITLE" || found=1; fi
  if [ -n "${PR_BODY:-}" ]; then n_pr=$((n_pr + 1)); hits "PR body" "$PR_BODY" || found=1; fi
  echo "    checked ${#names[@]} name(s), $n_commits commit message(s), $n_pr PR text(s)"
  if [ "$found" -ne 0 ]; then
    echo "FAIL: an internal name would be published. Rename the branch (git branch -m), reword the"
    echo "      commit (git commit --amend / rebase), or edit the PR text, BEFORE pushing."
    return 1
  fi
  echo "    ok"
}

self_test() {
  local t fails=0 out rc
  t=$(mktemp -d); trap 'rm -rf "$t"' RETURN
  git -C "$t" init -q -b main
  git -C "$t" -c user.email=t@example.invalid -c user.name=t commit -q --allow-empty -m "clean start"
  git -C "$t" checkout -q -b feature/zzleakzz-intake
  git -C "$t" -c user.email=t@example.invalid -c user.name=t commit -q --allow-empty -m "fix from zzleakzz report"
  git -C "$t" checkout -q -b feature/clean main
  git -C "$t" -c user.email=t@example.invalid -c user.name=t commit -q --allow-empty -m "a clean change"
  run() { (cd "$t" && env -u GITHUB_HEAD_REF -u PRE_COMMIT_REMOTE_BRANCH SOTA_DENYLIST=zzleakzz "$@" bash "$here/scripts/check-published-names.sh") >"$t.out" 2>&1; }
  expect() {  # expect <name> <want-rc> <want-text> -- <env...>
    local name=$1 want=$2 text=$3; shift 4
    set +e; run "$@"; rc=$?; set -e
    if [ "$rc" -ne "$want" ] || ! grep -qF -- "$text" "$t.out"; then
      echo "FAIL $name: rc=$rc (want $want), wanted '$text' in:"; sed 's/^/    /' "$t.out"; fails=$((fails + 1))
    fi
  }
  local leaky clean
  leaky=$(git -C "$t" rev-parse feature/zzleakzz-intake); clean=$(git -C "$t" rev-parse feature/clean)
  expect "leaky branch name"   1 "LEAK in branch name" -- PRE_COMMIT_REMOTE_BRANCH=refs/heads/feature/zzleakzz-intake PRE_COMMIT_LOCAL_BRANCH=refs/heads/feature/zzleakzz-intake PRE_COMMIT_TO_REF="$leaky"
  expect "leaky commit message" 1 "LEAK in commit" -- PRE_COMMIT_REMOTE_BRANCH=refs/heads/x PRE_COMMIT_LOCAL_BRANCH=refs/heads/x PRE_COMMIT_TO_REF="$leaky"
  expect "clean push"          0 "checked 2 name(s), 2 commit message(s)" -- PRE_COMMIT_REMOTE_BRANCH=refs/heads/feature/clean PRE_COMMIT_LOCAL_BRANCH=refs/heads/feature/clean PRE_COMMIT_TO_REF="$clean"
  expect "leaky PR title"      1 "LEAK in PR title" -- PRE_COMMIT_REMOTE_BRANCH=refs/heads/feature/clean PRE_COMMIT_LOCAL_BRANCH=refs/heads/feature/clean PRE_COMMIT_TO_REF="$clean" PR_TITLE="intake: the ZZLEAKZZ report"
  expect "CI withholds text"   1 "text withheld in CI logs" -- GITHUB_ACTIONS=true PRE_COMMIT_REMOTE_BRANCH=refs/heads/feature/zzleakzz-intake PRE_COMMIT_LOCAL_BRANCH=refs/heads/feature/zzleakzz-intake PRE_COMMIT_TO_REF="$leaky"
  if grep -qi 'zzleakzz' "$t.out"; then echo "FAIL CI mode printed the matched name"; fails=$((fails + 1)); fi
  expect "case-insensitive"    1 "LEAK in branch name" -- PRE_COMMIT_REMOTE_BRANCH=refs/heads/ZzLeakZz PRE_COMMIT_LOCAL_BRANCH=refs/heads/ZzLeakZz PRE_COMMIT_TO_REF="$clean"
  echo "self-test: $([ "$fails" -eq 0 ] && echo ok || echo "FAILED $fails") (6 cases)"
  rm -f "$t.out"
  [ "$fails" -eq 0 ]
}

if [ "${1:-}" = "--self-test" ]; then self_test; else main; fi
