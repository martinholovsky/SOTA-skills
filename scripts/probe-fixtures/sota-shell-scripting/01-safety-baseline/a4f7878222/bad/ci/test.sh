#!/usr/bin/env bash
set -euo pipefail
pytest -q tests/ | tail -20
