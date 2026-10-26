#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rsync -a build/ "$TARGET"/
