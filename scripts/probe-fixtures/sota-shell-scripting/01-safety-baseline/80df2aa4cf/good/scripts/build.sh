#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${CI:-}" ]]; then make ci; fi
