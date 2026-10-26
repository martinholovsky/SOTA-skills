#!/usr/bin/env bash
set -euo pipefail
python3 -m verifier.cc_admin --allow_hold_cert --user_mode
