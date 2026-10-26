#!/usr/bin/env bash
count=$(git status --porcelain | wc -l)
if [ "$count" != "0" ]; then echo "dirty" >&2; exit 1; fi
