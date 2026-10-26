#!/usr/bin/env bash
set -euo pipefail
pytest -q tests/ > pytest.log 2>&1
tail -20 pytest.log
