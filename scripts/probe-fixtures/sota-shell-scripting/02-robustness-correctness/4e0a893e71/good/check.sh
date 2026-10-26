#!/usr/bin/env bash
count=$(git status --porcelain | wc -l)
[[ $count =~ ^[0-9]+$ ]] || { echo "bad count: $count" >&2; exit 2; }
if (( count != 0 )); then echo "dirty" >&2; exit 1; fi
