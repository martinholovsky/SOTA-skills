#!/usr/bin/env bash
grep -q pattern "$f" 2>/dev/null || echo "missing pattern in $f"
