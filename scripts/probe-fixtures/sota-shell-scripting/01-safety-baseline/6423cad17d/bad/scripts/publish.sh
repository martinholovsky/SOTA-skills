#!/usr/bin/env bash
set -euo pipefail
git push origin "HEAD:$branch" || git push --force origin "HEAD:$branch"
