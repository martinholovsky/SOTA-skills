#!/usr/bin/env bash
grep -q pattern "$f"; rc=$?
[ "$rc" -eq 1 ] && echo "missing pattern in $f"
# a near miss the probe must not match: a plain `||` with no stderr redirect
[ -n "$f" ] || echo "no file given"
