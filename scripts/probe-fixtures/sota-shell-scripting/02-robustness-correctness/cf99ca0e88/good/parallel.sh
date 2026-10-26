#!/usr/bin/env bash
build_a & pa=$!
build_b & pb=$!
wait "$pa" || exit 1
wait "$pb" || exit 1
echo "both done"
