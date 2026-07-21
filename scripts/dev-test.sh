#!/usr/bin/env bash
# Run the services/import-api Go suite (including live PostgreSQL/MinIO
# tests) against the stack started by scripts/dev-up.sh. Runs in a golang
# container attached to the same Docker network as postgres/minio, so no
# host Go toolchain is required.
#
# Usage:
#   scripts/dev-up.sh
#   scripts/dev-test.sh                 # go test ./...
#   scripts/dev-test.sh -race ./...     # any extra `go test` arguments
#   GO_IMAGE=golang:1.23 scripts/dev-test.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "$#" -eq 0 ]; then
  set -- ./...
fi

docker run --rm \
  --network memory-os-dev \
  -v "$PWD:/src" \
  -w /src/services/import-api \
  -e MEMORY_OS_TEST_DATABASE_URL="postgres://postgres:postgres@postgres:5432/memory_os_security" \
  -e MEMORY_OS_TEST_S3_ENDPOINT="http://minio:9000" \
  -e MEMORY_OS_TEST_S3_ACCESS_KEY="minioadmin" \
  -e MEMORY_OS_TEST_S3_SECRET_KEY="minioadmin" \
  "${GO_IMAGE:-golang:1.23}" \
  go test "$@"
