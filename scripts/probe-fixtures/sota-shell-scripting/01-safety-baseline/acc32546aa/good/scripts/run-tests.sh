#!/usr/bin/env bash
make test
rc=$?
echo "EXIT=$rc"
exit "$rc"
