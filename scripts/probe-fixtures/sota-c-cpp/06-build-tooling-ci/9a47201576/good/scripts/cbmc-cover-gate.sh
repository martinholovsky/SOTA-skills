#!/usr/bin/env bash
set -uo pipefail
out=$(cbmc --cover cover "$@" 2>&1); rc=$?
if (( rc != 0 )); then exit "$rc"; fi
