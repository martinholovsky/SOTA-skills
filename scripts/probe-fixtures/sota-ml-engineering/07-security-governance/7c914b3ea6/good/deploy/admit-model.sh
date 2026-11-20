#!/usr/bin/env bash
set -euo pipefail
model_signing verify sigstore models/ranker --signature models/ranker.sig --identity ci@example.org --identity_provider https://token.example.org
