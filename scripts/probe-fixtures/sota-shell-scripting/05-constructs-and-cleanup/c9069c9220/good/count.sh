#!/usr/bin/env bash
set -euo pipefail
n=0
for f in *.log; do n=$((n + 1)); done
