#!/usr/bin/env bash
make build > build.log 2>&1
echo "build finished"; rc=$?
exit "$rc"
