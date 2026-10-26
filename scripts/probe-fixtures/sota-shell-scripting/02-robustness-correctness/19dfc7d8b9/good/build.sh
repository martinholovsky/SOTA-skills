#!/usr/bin/env bash
if ! make build > build.log 2>&1; then
  echo "build failed" >&2
  exit 1
fi
