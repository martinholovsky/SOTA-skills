#!/usr/bin/env bash
set -euo pipefail
for file in "$@"; do
  process "$file"
done
