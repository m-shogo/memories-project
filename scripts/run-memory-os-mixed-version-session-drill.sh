#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

: "${MEMORY_OS_TEST_DATABASE_URL:?MEMORY_OS_TEST_DATABASE_URL is required}"
: "${MEMORY_OS_TEST_S3_ENDPOINT:?MEMORY_OS_TEST_S3_ENDPOINT is required}"

OLD_SHA="${MEMORY_OS_MIXED_VERSION_OLD_SHA:-2af6e8e10755cc707c6bdd958a049a0f4afb3d70}"
SOURCE_SHA="${MEMORY_OS_COMMIT_SHA:-$(git rev-parse HEAD)}"
RESULT_PATH="${MEMORY_OS_MIXED_VERSION_RESULTS_PATH:-$REPO_ROOT/docs/fixtures/memory-os-operability/mixed-version-session-results.sample.v1.json}"
ACCOUNT_ID="acct_01J00000000000000000000000"
JOB_ID="job_01J000000000000000000000000"
OLD_PORT="18080"
CURRENT_PORT="18081"
BUCKET="memory-os-mixed-version-ci"

if ! [[ "$OLD_SHA" =~ ^[a-f0-9]{40}$ && "$SOURCE_SHA" =~ ^[a-f0-9]{40}$ ]]; then
  echo "source and old commit SHA must be full lowercase SHA-1 values" >&2
  exit 1
fi
if [[ "$OLD_SHA" == "$SOURCE_SHA" ]]; then
  echo "old and current source SHA must differ" >&2
  exit 1
fi
if [[ "$(git cat-file -t "$OLD_SHA" 2>/dev/null || true)" != "commit" ]]; then
  echo "pinned old backend commit is unavailable: $OLD_SHA" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/memory-os-mixed-version.XXXXXX")"
OLD_TREE="$TMP_DIR/old"
OLD_BIN="$TMP_DIR/import-api-old"
CURRENT_BIN="$TMP_DIR/import-api-current"
OLD_TOKEN_FILE="$TMP_DIR/old-session.txt"
CURRENT_TOKEN_FILE="$TMP_DIR/current-session.txt"
OLD_LOG="$TMP_DIR/old-server.log"
CURRENT_LOG="$TMP_DIR/current-server.log"
OLD_PID=""
CURRENT_PID=""

cleanup() {
  set +e
  if [[ -n "$OLD_PID" ]]; then kill "$OLD_PID" 2>/dev/null || true; fi
  if [[ -n "$CURRENT_PID" ]]; then kill "$CURRENT_PID" 2>/dev/null || true; fi
  if [[ -n "$OLD_PID" ]]; then wait "$OLD_PID" 2>/dev/null || true; fi
  if [[ -n "$CURRENT_PID" ]]; then wait "$CURRENT_PID" 2>/dev/null || true; fi
  git worktree remove --force "$OLD_TREE" >/dev/null 2>&1 || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

wait_http() {
  local url="$1"
  local log_file="$2"
  for _ in $(seq 1 60); do
    if curl --fail --silent --show-error "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "server did not become healthy: $url" >&2
  tail -n 80 "$log_file" >&2 || true
  return 1
}

extract_token() {
  local path="$1"
  local token
  token="$(tail -n 1 "$path" | tr -d '\r\n')"
  if [[ -z "$token" || ${#token} -gt 512 ]]; then
    echo "session issuer did not produce a bounded token" >&2
    return 1
  fi
  printf '%s' "$token"
}

mapfile -t MIGRATIONS < <(python - <<'PY'
import json
from pathlib import Path
contract = json.loads(Path("contracts/operations/migration-lifecycle-contract.v1.json").read_text())
for name in contract["migrationSequence"]:
    print(name)
PY
)
[[ "${#MIGRATIONS[@]}" -gt 0 ]] || { echo "migration registry is empty" >&2; exit 1; }
for migration in "${MIGRATIONS[@]}"; do
  psql "$MEMORY_OS_TEST_DATABASE_URL" --set=ON_ERROR_STOP=1 \
    --file "$REPO_ROOT/infra/postgresql/security/$migration" >/dev/null
done

psql "$MEMORY_OS_TEST_DATABASE_URL" --set=ON_ERROR_STOP=1 >/dev/null <<SQL
INSERT INTO memory_os.account_control
  (account_id, account_epoch, state)
VALUES
  ('$ACCOUNT_ID', 1, 'active')
ON CONFLICT (account_id) DO UPDATE
SET account_epoch = EXCLUDED.account_epoch,
    state = EXCLUDED.state,
    deletion_started_at = NULL,
    deletion_completed_at = NULL,
    updated_at = now();
DELETE FROM memory_os.account_session WHERE owner_account_id = '$ACCOUNT_ID';
SQL

for _ in $(seq 1 60); do
  if curl --fail --silent --show-error "$MEMORY_OS_TEST_S3_ENDPOINT/minio/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl --fail --silent --show-error "$MEMORY_OS_TEST_S3_ENDPOINT/minio/health/live" >/dev/null

git worktree add --detach "$OLD_TREE" "$OLD_SHA" >/dev/null
(
  cd "$OLD_TREE/services/import-api"
  go build -trimpath -o "$OLD_BIN" ./cmd/import-api-server
)
(
  cd "$REPO_ROOT/services/import-api"
  go build -trimpath -o "$CURRENT_BIN" ./cmd/import-api-server
)

"$OLD_BIN" \
  -database-url "$MEMORY_OS_TEST_DATABASE_URL" \
  -dev-issue-session "$ACCOUNT_ID" >"$OLD_TOKEN_FILE"
"$CURRENT_BIN" \
  -database-url "$MEMORY_OS_TEST_DATABASE_URL" \
  -dev-issue-session "$ACCOUNT_ID" >"$CURRENT_TOKEN_FILE"

OLD_TOKEN="$(extract_token "$OLD_TOKEN_FILE")"
CURRENT_TOKEN="$(extract_token "$CURRENT_TOKEN_FILE")"
# Token-bearing files are no longer needed after extraction.
rm -f "$OLD_TOKEN_FILE" "$CURRENT_TOKEN_FILE"

"$CURRENT_BIN" \
  -listen "127.0.0.1:$CURRENT_PORT" \
  -database-url "$MEMORY_OS_TEST_DATABASE_URL" \
  -s3-endpoint "$MEMORY_OS_TEST_S3_ENDPOINT" \
  -s3-access-key "${MEMORY_OS_TEST_S3_ACCESS_KEY:-minioadmin}" \
  -s3-secret-key "${MEMORY_OS_TEST_S3_SECRET_KEY:-minioadmin}" \
  -bucket "$BUCKET" \
  -dev-provision >"$CURRENT_LOG" 2>&1 &
CURRENT_PID="$!"
wait_http "http://127.0.0.1:$CURRENT_PORT/healthz" "$CURRENT_LOG"

"$OLD_BIN" \
  -listen "127.0.0.1:$OLD_PORT" \
  -database-url "$MEMORY_OS_TEST_DATABASE_URL" \
  -s3-endpoint "$MEMORY_OS_TEST_S3_ENDPOINT" \
  -s3-access-key "${MEMORY_OS_TEST_S3_ACCESS_KEY:-minioadmin}" \
  -s3-secret-key "${MEMORY_OS_TEST_S3_SECRET_KEY:-minioadmin}" \
  -bucket "$BUCKET" >"$OLD_LOG" 2>&1 &
OLD_PID="$!"
wait_http "http://127.0.0.1:$OLD_PORT/healthz" "$OLD_LOG"

CURRENT_HEALTH="$(curl --silent --output /dev/null --write-out '%{http_code}' "http://127.0.0.1:$CURRENT_PORT/healthz")"
OLD_HEALTH="$(curl --silent --output /dev/null --write-out '%{http_code}' "http://127.0.0.1:$OLD_PORT/healthz")"

# A nonexistent Preview is deliberate: authentication and account fencing must
# succeed, then the resource lookup may return a bounded 4xx. A 401, 403, 5xx or
# transport failure means the cross-version session boundary is not compatible.
CURRENT_ACCEPTS_OLD="$(curl --silent --output "$TMP_DIR/current-accepts-old.json" --write-out '%{http_code}' \
  -H "Authorization: Bearer $OLD_TOKEN" \
  "http://127.0.0.1:$CURRENT_PORT/v1/import-jobs/$JOB_ID/preview")"
OLD_ACCEPTS_CURRENT="$(curl --silent --output "$TMP_DIR/old-accepts-current.json" --write-out '%{http_code}' \
  -H "Authorization: Bearer $CURRENT_TOKEN" \
  "http://127.0.0.1:$OLD_PORT/v1/import-jobs/$JOB_ID/preview")"

for value in "$CURRENT_ACCEPTS_OLD" "$OLD_ACCEPTS_CURRENT"; do
  if [[ "$value" == "000" || "$value" == "401" || "$value" == "403" || "$value" =~ ^5 ]]; then
    echo "cross-version authenticated request failed with HTTP $value" >&2
    exit 1
  fi
done
[[ "$CURRENT_HEALTH" == "200" && "$OLD_HEALTH" == "200" ]] || {
  echo "mixed-version health check failed: old=$OLD_HEALTH current=$CURRENT_HEALTH" >&2
  exit 1
}

SESSION_ROWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(*) FROM memory_os.account_session WHERE owner_account_id = '$ACCOUNT_ID' AND state = 'active';")"
[[ "$SESSION_ROWS" == "2" ]] || {
  echo "expected two active cross-version sessions, got $SESSION_ROWS" >&2
  exit 1
}

mkdir -p "$(dirname "$RESULT_PATH")"
SOURCE_SHA="$SOURCE_SHA" OLD_SHA="$OLD_SHA" RESULT_PATH="$RESULT_PATH" \
CURRENT_HEALTH="$CURRENT_HEALTH" OLD_HEALTH="$OLD_HEALTH" \
CURRENT_ACCEPTS_OLD="$CURRENT_ACCEPTS_OLD" OLD_ACCEPTS_CURRENT="$OLD_ACCEPTS_CURRENT" \
SESSION_ROWS="$SESSION_ROWS" python - <<'PY'
import datetime as dt
import json
import os
from pathlib import Path

result = {
    "schemaVersion": "memory-os-mixed-version-session-results.v1",
    "commitSha": os.environ["SOURCE_SHA"],
    "oldBackendCommitSha": os.environ["OLD_SHA"],
    "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    "environment": {
        "mode": "GITHUB_ACTIONS_OR_LOCAL_POSTGRES16_MINIO_TWO_PROCESSES",
        "productionEvidence": False,
        "containsSecrets": False,
        "syntheticDataOnly": True,
    },
    "result": "PASS",
    "integrityResult": "PASS",
    "assertions": {
        "oldHealthStatus": int(os.environ["OLD_HEALTH"]),
        "currentHealthStatus": int(os.environ["CURRENT_HEALTH"]),
        "currentAcceptsOldIssuedSessionStatus": int(os.environ["CURRENT_ACCEPTS_OLD"]),
        "oldAcceptsCurrentIssuedSessionStatus": int(os.environ["OLD_ACCEPTS_CURRENT"]),
        "activeSessionRows": int(os.environ["SESSION_ROWS"]),
        "sharedCurrentSchema": True,
        "oldAndCurrentProcessesConcurrent": True,
        "rawTokensPersisted": False,
    },
    "limitations": [
        "session issuance, session resolution, account fencing and read-route entry only",
        "not full rolling-deployment route coverage",
        "not mixed persisted Preview or parser artifact coverage",
        "not a rollback-under-live-traffic drill",
        "ephemeral PostgreSQL 16 and MinIO only",
        "not production compatibility evidence",
    ],
}
Path(os.environ["RESULT_PATH"]).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
PY

printf 'Mixed-version session drill PASS: old=%s current=%s\n' "$OLD_SHA" "$SOURCE_SHA"
