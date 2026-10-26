#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "failed at line $LINENO" >&2' ERR
