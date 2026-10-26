#!/usr/bin/env bash
set -euo pipefail
for file in "$@"; do
  bash -c "process $file"
done
