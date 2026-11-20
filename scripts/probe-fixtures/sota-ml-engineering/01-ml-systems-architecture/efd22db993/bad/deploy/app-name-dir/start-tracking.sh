#!/usr/bin/env bash
set -euo pipefail
exec mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri "$DB_URI"
