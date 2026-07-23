#!/usr/bin/env bash
# Run one visible end-to-end import against the local dev stack: build the
# digest-pinned parser-worker and the importctl harness inside a golang
# container on the dev network, upload the CSV through the real presigned
# binding, parse under supervision, verify, commit, and print the Preview.
#
# Usage:
#   scripts/dev-up.sh
#   scripts/dev-import.sh                              # sample CSV
#   scripts/dev-import.sh path/to/your.csv             # your CSV
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

CSV="${1:-services/import-api/testdata/sample-import.csv}"
if [ ! -f "$CSV" ]; then
  echo "dev-import: CSV not found: $CSV" >&2
  exit 2
fi

docker run --rm \
  --network memory-os-dev \
  -v "$PWD:/src" \
  -w /src/services/import-api \
  "${GO_IMAGE:-golang:1.23}" \
  bash -c "
    set -euo pipefail
    go build -o /tmp/parser-worker ./cmd/parser-worker
    go build -o /tmp/importctl ./cmd/importctl
    exec /tmp/importctl \
      -database-url 'postgres://postgres:postgres@postgres:5432/memory_os_security' \
      -s3-endpoint 'http://minio:9000' \
      -worker /tmp/parser-worker \
      -migrations /src/infra/postgresql/security \
      -csv '/src/$CSV'
  "
