#!/usr/bin/env bash
#
# publish-plugin-dist.sh — commit a built plugin tree to the plugin-dist branch and push it.
#
#   scripts/publish-plugin-dist.sh DIST TAG [REMOTE]   # REMOTE defaults to origin
#   scripts/publish-plugin-dist.sh --selftest          # every refusal, against a local bare remote
#
# WHY. The Claude plugin directory follows plugin-dist and serves each new commit on it to
# everyone who has the plugin, so this push is a release to every user (RELEASING.md §4b).
# It is built to be boring: one commit per release, on top of the branch as the REMOTE has it,
# never forced. .github/workflows/plugin-dist.yml is the only caller that should run it.
#
# WHAT IT REFUSES (exit 1, nothing pushed):
#   - TAG not vX.Y.Z, or DIST's VERSION / plugin.json version not equal to TAG without the v;
#   - a version lower than the one plugin-dist already carries (a downgrade);
#   - the same version with a different tree (a release changed after it shipped: bump instead);
#   - a push the remote rejects, including one that is not a fast-forward because the branch
#     moved meanwhile. There is no --force anywhere in this file.
# An identical tree at the same version is a no-op (exit 0): re-running a release is safe.
#
# THE CALLER'S CHECKOUT IS NEVER TOUCHED: the tree is staged through a private GIT_INDEX_FILE
# and committed with commit-tree, so no branch is switched, no working file changes, and the
# repo's own index is not read. The commit message carries the tag and SOURCE_COMMIT.
#
# Exit: 0 pushed or nothing to do, 1 refused or failed, 2 usage.
set -euo pipefail

readonly BRANCH=plugin-dist
usage() { sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'; exit "${1:-0}"; }
die() { printf 'publish-plugin-dist: %s\n' "$*" >&2; exit 1; }

# vercmp A B -> prints -1, 0 or 1. X.Y.Z only; callers validate the shape first.
vercmp() {
  local IFS=. i
  # shellcheck disable=SC2206  # splitting on the dots is the point; the shape is validated
  local -a a=($1) b=($2)
  for i in 0 1 2; do
    if ((10#${a[i]} < 10#${b[i]})); then echo -1; return; fi
    if ((10#${a[i]} > 10#${b[i]})); then echo 1; return; fi
  done
  echo 0
}

publish() {
  local dist=$1 tag=$2 remote=${3:-origin}
  [[ "$tag" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]] || die "TAG '$tag' is not vX.Y.Z"
  local ver=${tag#v}
  [ -d "$dist" ] || die "DIST '$dist' is not a directory"
  dist=$(cd -- "$dist" && pwd -P)

  local dver pver
  dver=$(tr -d '[:space:]' < "$dist/VERSION" 2>/dev/null) || die "DIST has no VERSION"
  pver=$(sed -n 's/^[[:space:]]*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
           "$dist/.claude-plugin/plugin.json" 2>/dev/null | head -n 1)
  [ "$dver" = "$ver" ] || die "DIST VERSION is '$dver', the tag says $ver"
  [ "$pver" = "$ver" ] || die "DIST plugin.json version is '${pver:-absent}', the tag says $ver"
  local src
  src=$(tr -d '[:space:]' < "$dist/SOURCE_COMMIT" 2>/dev/null) || src=""
  [[ "$src" =~ ^[0-9a-f]{40}$ ]] || die "DIST has no SOURCE_COMMIT (build it with build-plugin-dist.sh)"

  git rev-parse --git-dir >/dev/null 2>&1 || die "not inside a git repository"

  # The remote's tip, asked of the remote itself: a local tracking ref can be stale.
  local tip="" line
  line=$(git ls-remote --heads "$remote" "refs/heads/$BRANCH") || die "cannot reach remote '$remote'"
  [ -z "$line" ] || tip=${line%%[[:space:]]*}

  local tmp
  tmp=$(mktemp -d)
  # shellcheck disable=SC2064  # expand now: the path is fixed for this run
  trap "rm -rf -- '$tmp'" RETURN

  if [ -n "$tip" ]; then
    git fetch --quiet --no-tags "$remote" "refs/heads/$BRANCH" || die "cannot fetch $BRANCH from '$remote'"
    [ "$(git rev-parse FETCH_HEAD)" = "$tip" ] || die "$BRANCH moved between ls-remote and fetch; re-run"
    local old
    old=$(git show "$tip:VERSION" 2>/dev/null | tr -d '[:space:]') || old=""
    [[ "$old" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "$BRANCH tip ${tip:0:12} has no readable VERSION ('$old')"
    case $(vercmp "$ver" "$old") in
      -1) die "refusing a downgrade: $BRANCH carries $old, this is $ver" ;;
    esac
  fi

  # Stage DIST through a private index. The settings pin what lands: no line-ending rewrite,
  # executable bits recorded from the files, and no ignore rule of this repo can drop a file.
  local tree
  tree=$(GIT_INDEX_FILE="$tmp/index" git -c core.autocrlf=false -c core.fileMode=true \
           -c core.safecrlf=false --work-tree="$dist" add --all --force -- . &&
         GIT_INDEX_FILE="$tmp/index" git write-tree) || die "could not stage $dist"
  local staged want
  staged=$(git ls-tree -r --name-only "$tree" | wc -l | tr -d ' ')
  want=$(cd -- "$dist" && find . -type f | wc -l | tr -d ' ')
  [ "$staged" -eq "$want" ] || die "staged $staged files, DIST holds $want"

  if [ -n "$tip" ]; then
    if [ "$(git rev-parse "$tip^{tree}")" = "$tree" ]; then
      printf 'publish-plugin-dist: %s already carries this tree (%s); nothing to do\n' "$BRANCH" "${tip:0:12}"
      return 0
    fi
    [ "$(vercmp "$ver" "$old")" -eq 1 ] ||
      die "$BRANCH already carries $ver with a different tree: bump the version instead"
  fi

  local commit
  commit=$(GIT_AUTHOR_NAME=${GIT_AUTHOR_NAME:-sota-skills release} \
           GIT_AUTHOR_EMAIL=${GIT_AUTHOR_EMAIL:-noreply@github.com} \
           GIT_COMMITTER_NAME=${GIT_COMMITTER_NAME:-sota-skills release} \
           GIT_COMMITTER_EMAIL=${GIT_COMMITTER_EMAIL:-noreply@github.com} \
           git commit-tree "$tree" ${tip:+-p "$tip"} \
             -m "plugin-dist $tag" -m "Built from $src by scripts/build-plugin-dist.sh; $staged files.") ||
    die "commit-tree failed"

  # A plain push: the remote rejects anything that is not a fast-forward of the tip it has.
  git push --quiet "$remote" "$commit:refs/heads/$BRANCH" || die "push to $remote $BRANCH was rejected"
  line=$(git ls-remote --heads "$remote" "refs/heads/$BRANCH")
  [ "${line%%[[:space:]]*}" = "$commit" ] || die "pushed, but $remote $BRANCH reads '${line%%[[:space:]]*}', not $commit"
  printf 'publish-plugin-dist: %s %s -> %s (%s files, from %s)\n' "$remote" "$BRANCH" "${commit:0:12}" "$staged" "${src:0:12}"
}

# ---------------------------------------------------------------- selftest
selftest() {
  local t pass=0 fail=0
  t=$(mktemp -d)
  # shellcheck disable=SC2064  # expand now: the path is fixed for this run
  trap "rm -rf -- '$t'" EXIT
  # A CI runner has no git identity, and git's hostname fallback refuses on some hosts.
  export GIT_AUTHOR_NAME=selftest GIT_AUTHOR_EMAIL=selftest@example.invalid
  export GIT_COMMITTER_NAME=selftest GIT_COMMITTER_EMAIL=selftest@example.invalid
  git init --quiet --bare "$t/remote.git"
  git init --quiet "$t/work"
  local self remote="$t/remote.git"
  self="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/$(basename -- "${BASH_SOURCE[0]}")"

  mk() {  # mk DIR VERSION BODY
    rm -rf -- "$1"; mkdir -p "$1/.claude-plugin" "$1/scripts"
    printf '%s\n' "$2" > "$1/VERSION"
    printf '{\n  "name": "fixture",\n  "version": "%s"\n}\n' "$2" > "$1/.claude-plugin/plugin.json"
    printf '%s\n' "$3" > "$1/README.md"
    printf '%040d\n' 0 > "$1/SOURCE_COMMIT"
    printf '#!/bin/sh\nexit 0\n' > "$1/scripts/hook.sh"; chmod +x "$1/scripts/hook.sh"
  }
  tip() { git -C "$remote" rev-parse --verify --quiet "refs/heads/$BRANCH" || true; }
  ok_if() {  # ok_if MESSAGE TEST...: a real if, so a failed echo cannot flip the verdict
    local msg=$1; shift
    if "$@"; then pass=$((pass + 1)); printf 'ok   %s\n' "$msg"
    else fail=$((fail + 1)); printf 'FAIL %s\n' "$msg"; fi
  }
  expect() {  # expect NAME WANT_RC WANT_TEXT [args...]: the rc AND the reason must both match
    local name=$1 want=$2 text=$3 rc=0 out; shift 3
    out=$(cd "$t/work" && "$self" "$@" 2>&1) || rc=$?
    if [ "$rc" -eq "$want" ] && printf '%s' "$out" | grep -qF -e "$text"; then
      pass=$((pass + 1)); printf 'ok   %s (rc %s)\n' "$name" "$rc"
    else fail=$((fail + 1)); printf 'FAIL %s: rc %s, wanted %s and "%s": %s\n' "$name" "$rc" "$want" "$text" "$out"; fi
  }

  mk "$t/d1" 1.0.0 "first"
  expect "create the branch at 1.0.0" 0 "plugin-dist ->" "$t/d1" v1.0.0 "$remote"
  local first nf
  first=$(tip)
  # --parents prints the commit then its parents, so a root commit is one field. (`cut -f2`
  # prints a line with no delimiter whole, so a root would read as its own parent.)
  nf=$(git -C "$remote" rev-list --parents -n 1 "${first:-HEAD}" 2>/dev/null | awk '{print NF}')
  ok_if "the first commit exists and has no parent" [ "${nf:-0}" = 1 ]   # empty $first -> nf 0
  ok_if "the executable bit survives" [ "$(git -C "$remote" ls-tree "$first" scripts/hook.sh | cut -c1-6)" = 100755 ]

  expect "same version, same tree: a no-op" 0 "nothing to do" "$t/d1" v1.0.0 "$remote"
  ok_if "the no-op pushed nothing" [ "$(tip)" = "$first" ]

  mk "$t/d2" 1.0.0 "changed after release"
  expect "same version, different tree: refused" 1 "bump the version" "$t/d2" v1.0.0 "$remote"
  mk "$t/d3" 0.9.0 "older"
  expect "a downgrade: refused" 1 "refusing a downgrade" "$t/d3" v0.9.0 "$remote"
  mk "$t/d4" 1.1.0 "next"
  expect "VERSION and tag disagree: refused" 1 "DIST VERSION is" "$t/d4" v1.2.0 "$remote"
  expect "a tag that is not vX.Y.Z: refused" 1 "is not vX.Y.Z" "$t/d4" 1.1.0 "$remote"
  sed -i.bak 's/"1.1.0"/"1.0.9"/' "$t/d4/.claude-plugin/plugin.json"; rm -f "$t/d4/.claude-plugin/plugin.json.bak"
  expect "plugin.json and tag disagree: refused" 1 "plugin.json version is" "$t/d4" v1.1.0 "$remote"
  ok_if "no refusal moved the branch" [ "$(tip)" = "$first" ]

  mk "$t/d5" 1.1.0 "next"
  expect "an upgrade: a fast-forward" 0 "plugin-dist ->" "$t/d5" v1.1.0 "$remote"
  ok_if "1.1.0's parent is 1.0.0" [ "$(git -C "$remote" rev-parse "$(tip)^")" = "$first" ]
  local second; second=$(tip)

  # A race: the branch moves to a history this run never saw, after the run read the tip and
  # before its push lands. A git shim moves the remote ref when `push` starts. The shim calls
  # the real git by absolute path, never `git`, or it would run itself (a fork bomb,
  # sota-shell-scripting rules/03 §3a). The push must be rejected as a non-fast-forward.
  local stray real_git before rc=0 out
  stray=$(git -C "$t/work" commit-tree "$(git -C "$t/work" mktree </dev/null)" -m stray)
  git -C "$t/work" push --quiet "$remote" "$stray:refs/heads/elsewhere"
  real_git=$(command -v git)
  mkdir -p "$t/shim"
  # shellcheck disable=SC2016  # $1 and $@ belong to the shim, not to this shell
  printf '#!/bin/sh\nif [ "$1" = push ]; then "%s" --git-dir="%s" update-ref refs/heads/%s %s; fi\nexec "%s" "$@"\n' \
    "$real_git" "$remote" "$BRANCH" "$stray" "$real_git" > "$t/shim/git"
  chmod +x "$t/shim/git"
  mk "$t/d6" 1.2.0 "raced"
  out=$(cd "$t/work" && PATH="$t/shim:$PATH" "$self" "$t/d6" v1.2.0 "$remote" 2>&1) || rc=$?
  if [ "$rc" -eq 1 ] && [ "$(tip)" = "$stray" ] && printf '%s' "$out" | grep -q 'rejected'; then
    pass=$((pass + 1)); echo "ok   a branch moved mid-run: the push is rejected, the moved tip stands"
  else
    fail=$((fail + 1)); echo "FAIL race: rc $rc, tip $(tip), wanted rc 1 and $stray: $out"
  fi
  # Put the branch back on the 1.1.0 history, then check the ordinary next release.
  git --git-dir="$remote" update-ref "refs/heads/$BRANCH" "$second"
  before=$(tip)
  expect "the next upgrade fast-forwards" 0 "plugin-dist ->" "$t/d6" v1.2.0 "$remote"
  ok_if "1.2.0's parent is 1.1.0" [ "$(git -C "$remote" rev-parse "$(tip)^")" = "$before" ]

  local verdict=PASS
  [ "$fail" -eq 0 ] || verdict=FAIL
  printf '%s: %s/%s publish cases\n' "$verdict" "$pass" "$((pass + fail))"
  [ "$fail" -eq 0 ]
}

case "${1:-}" in
  -h | --help) usage 0 ;;
  --selftest) selftest ;;
  '') usage 2 >&2 ;;
  *)
    if [ $# -lt 2 ] || [ $# -gt 3 ]; then usage 2 >&2; fi
    publish "$@"
    ;;
esac
