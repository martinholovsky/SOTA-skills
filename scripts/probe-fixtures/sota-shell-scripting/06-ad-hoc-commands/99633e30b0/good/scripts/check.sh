#!/usr/bin/env bash
grep -q pattern "$f"; rc=$?
[ "$rc" -eq 1 ] && echo "missing pattern in $f"
