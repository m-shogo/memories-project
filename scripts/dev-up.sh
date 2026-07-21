#!/usr/bin/env bash
# Start the local PostgreSQL + MinIO stack used by services/import-api's live
# test suites, and wait until both are healthy. Safe to re-run: it reuses any
# already-running containers instead of restarting them.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose -f infra/dev-compose.yml up -d
docker compose -f infra/dev-compose.yml up -d --wait
echo "postgres: postgres://postgres:postgres@127.0.0.1:55432/memory_os_security"
echo "minio:    http://127.0.0.1:59000 (minioadmin/minioadmin)"
