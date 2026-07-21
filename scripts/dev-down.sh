#!/usr/bin/env bash
# Stop and remove the local dev stack started by scripts/dev-up.sh.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose -f infra/dev-compose.yml down --volumes
