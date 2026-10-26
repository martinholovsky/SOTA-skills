#!/usr/bin/env bash
cd "$(dirname "$0")"
rsync -a build/ "$TARGET"/
