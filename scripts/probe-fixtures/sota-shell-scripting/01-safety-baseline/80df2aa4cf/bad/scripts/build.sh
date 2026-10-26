#!/bin/sh
set -eu
if [[ -n "${CI:-}" ]]; then make ci; fi
