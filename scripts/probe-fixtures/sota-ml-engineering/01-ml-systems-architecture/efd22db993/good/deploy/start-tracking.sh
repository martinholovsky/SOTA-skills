#!/usr/bin/env bash
set -euo pipefail
exec mlflow server --app-name basic-auth --host 0.0.0.0 --port 5000 --backend-store-uri "$DB_URI"
