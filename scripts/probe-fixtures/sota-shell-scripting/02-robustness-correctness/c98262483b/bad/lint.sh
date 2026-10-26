#!/usr/bin/env bash
set -euo pipefail
files=$(git ls-files | grep '\.sh$')
shellcheck $files
