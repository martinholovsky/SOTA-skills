#!/usr/bin/env bash
build_a &
build_b &
wait
echo "both done"
