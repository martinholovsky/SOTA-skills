#!/usr/bin/env bash
set -euo pipefail
if ! git push origin "HEAD:$branch"; then
  git fetch origin "$branch"
  git log --oneline -1 "origin/$branch" >&2
  echo "push failed; remote state printed above, not retrying" >&2
  exit 1
fi
