#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

: "${MEMORY_OS_TEST_DATABASE_URL:?MEMORY_OS_TEST_DATABASE_URL is required}"
: "${MEMORY_OS_TEST_S3_ENDPOINT:?MEMORY_OS_TEST_S3_ENDPOINT is required}"

OLD_SHA="${MEMORY_OS_MIXED_VERSION_OLD_SHA:-2af6e8e10755cc707c6bdd958a049a0f4afb3d70}"
SOURCE_SHA="${MEMORY_OS_COMMIT_SHA:-$(git rev-parse HEAD)}"
RESULT_PATH="${MEMORY_OS_MIXED_VERSION_APPLY_RESULTS_PATH:-$REPO_ROOT/docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json}"
OLD_PORT="18180"
CURRENT_PORT="18181"
BUCKET="memory-os-mixed-version-apply-ci"

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
if ! git merge-base --is-ancestor "$OLD_SHA" "$SOURCE_SHA"; then
  echo "pinned old backend must be an ancestor of current source" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/memory-os-mixed-version-apply.XXXXXX")"
OLD_TREE="$TMP_DIR/old"
OLD_BIN="$TMP_DIR/import-api-old"
CURRENT_BIN="$TMP_DIR/import-api-current"
FIXTURE_BIN="$TMP_DIR/memory-os-mixed-version-fixture"
OLD_TOKEN_FILE="$TMP_DIR/old-session.txt"
CURRENT_TOKEN_FILE="$TMP_DIR/current-session.txt"
OLD_LOG="$TMP_DIR/old-server.log"
CURRENT_LOG="$TMP_DIR/current-server.log"
FIXTURE_A="$TMP_DIR/preview-a.json"
FIXTURE_B="$TMP_DIR/preview-b.json"
HTTP_SUMMARY="$TMP_DIR/http-summary.json"
IDENTITY_ENV="$TMP_DIR/identity.env"
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

SOURCE_SHA="$SOURCE_SHA" OUTPUT="$IDENTITY_ENV" python - <<'PY'
import hashlib
import os
import secrets
from pathlib import Path

seed = hashlib.sha256((os.environ["SOURCE_SHA"] + secrets.token_hex(16)).encode()).hexdigest()
values = {
    "ACCOUNT_ID": "acct_" + seed[0:24],
    "JOB_A": "job_" + seed[0:24],
    "JOB_B": "job_" + seed[24:48],
    "PREVIEW_A": "prv_" + seed[0:24],
    "PREVIEW_B": "prv_" + seed[24:48],
    "SPOOL_A": "spl_" + seed[0:24],
    "SPOOL_B": "spl_" + seed[24:48],
    "UPLOAD_A": "upl_" + seed[0:24],
    "UPLOAD_B": "upl_" + seed[24:48],
    "FINGERPRINT_A": "fp-mixed-" + seed[0:24],
    "FINGERPRINT_B": "fp-mixed-" + seed[24:48],
    "IDEMPOTENCY_A": "idem-mixed-" + seed[0:24],
    "IDEMPOTENCY_B": "idem-mixed-" + seed[24:48],
}
Path(os.environ["OUTPUT"]).write_text(
    "".join(f"{name}={value}\n" for name, value in values.items()),
    encoding="utf-8",
)
PY
# Values are generated from lowercase hexadecimal and fixed prefixes only.
# shellcheck disable=SC1090
source "$IDENTITY_ENV"

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
  go build -trimpath -o "$FIXTURE_BIN" ./cmd/memory-os-mixed-version-fixture
)

"$FIXTURE_BIN" \
  -database-url "$MEMORY_OS_TEST_DATABASE_URL" \
  -account-id "$ACCOUNT_ID" -job-id "$JOB_A" -preview-id "$PREVIEW_A" \
  -spool-id "$SPOOL_A" -upload-id "$UPLOAD_A" -fingerprint "$FINGERPRINT_A" \
  >"$FIXTURE_A"
"$FIXTURE_BIN" \
  -database-url "$MEMORY_OS_TEST_DATABASE_URL" \
  -account-id "$ACCOUNT_ID" -job-id "$JOB_B" -preview-id "$PREVIEW_B" \
  -spool-id "$SPOOL_B" -upload-id "$UPLOAD_B" -fingerprint "$FINGERPRINT_B" \
  >"$FIXTURE_B"

"$OLD_BIN" -database-url "$MEMORY_OS_TEST_DATABASE_URL" \
  -dev-issue-session "$ACCOUNT_ID" >"$OLD_TOKEN_FILE"
"$CURRENT_BIN" -database-url "$MEMORY_OS_TEST_DATABASE_URL" \
  -dev-issue-session "$ACCOUNT_ID" >"$CURRENT_TOKEN_FILE"
OLD_TOKEN="$(extract_token "$OLD_TOKEN_FILE")"
CURRENT_TOKEN="$(extract_token "$CURRENT_TOKEN_FILE")"
rm -f "$OLD_TOKEN_FILE" "$CURRENT_TOKEN_FILE"

"$CURRENT_BIN" \
  -listen "127.0.0.1:$CURRENT_PORT" \
  -database-url "$MEMORY_OS_TEST_DATABASE_URL" \
  -s3-endpoint "$MEMORY_OS_TEST_S3_ENDPOINT" \
  -s3-access-key "${MEMORY_OS_TEST_S3_ACCESS_KEY:-minioadmin}" \
  -s3-secret-key "${MEMORY_OS_TEST_S3_SECRET_KEY:-minioadmin}" \
  -bucket "$BUCKET" -dev-provision >"$CURRENT_LOG" 2>&1 &
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

OLD_TOKEN="$OLD_TOKEN" CURRENT_TOKEN="$CURRENT_TOKEN" \
OLD_URL="http://127.0.0.1:$OLD_PORT" CURRENT_URL="http://127.0.0.1:$CURRENT_PORT" \
FIXTURE_A="$FIXTURE_A" FIXTURE_B="$FIXTURE_B" \
IDEMPOTENCY_A="$IDEMPOTENCY_A" IDEMPOTENCY_B="$IDEMPOTENCY_B" \
HTTP_SUMMARY="$HTTP_SUMMARY" python - <<'PY'
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

old_url = os.environ["OLD_URL"]
current_url = os.environ["CURRENT_URL"]
old_token = os.environ["OLD_TOKEN"]
current_token = os.environ["CURRENT_TOKEN"]
fixture_a = json.loads(Path(os.environ["FIXTURE_A"]).read_text())
fixture_b = json.loads(Path(os.environ["FIXTURE_B"]).read_text())


def request(base, method, path, token, body=None):
    payload = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=payload, method=method)
    req.add_header("Authorization", "Bearer " + token)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read(1 << 20)
            return response.status, json.loads(raw or b"{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read(1 << 20)
        try:
            decoded = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            decoded = {}
        return exc.code, decoded


def apply(base, token, fixture, key):
    return request(
        base,
        "POST",
        f"/v1/previews/{fixture['previewId']}/apply",
        token,
        {
            "previewSha256": fixture["previewSha256"],
            "idempotencyKey": key,
            "duplicatePolicy": "skip_existing",
        },
    )

old_read_status, _ = request(
    old_url, "GET", "/v1/import-jobs/" + os.environ.get("JOB_A", "") + "/preview", current_token
) if os.environ.get("JOB_A") else (0, {})
# The Apply paths below are the binding proof; explicit Preview reads use the
# IDs returned by the fixture through their job-independent Apply surface.
old_first_status, old_first = apply(
    old_url, current_token, fixture_a, os.environ["IDEMPOTENCY_A"]
)
current_replay_status, current_replay = apply(
    current_url, old_token, fixture_a, os.environ["IDEMPOTENCY_A"]
)
current_first_status, current_first = apply(
    current_url, old_token, fixture_b, os.environ["IDEMPOTENCY_B"]
)
old_replay_status, old_replay = apply(
    old_url, current_token, fixture_b, os.environ["IDEMPOTENCY_B"]
)
conflict_status, _ = apply(
    current_url, current_token, fixture_b, os.environ["IDEMPOTENCY_A"]
)

for label, status in {
    "old first apply": old_first_status,
    "current replay": current_replay_status,
    "current first apply": current_first_status,
    "old replay": old_replay_status,
}.items():
    if status != 200:
        raise SystemExit(f"{label} returned HTTP {status}")
if conflict_status != 409:
    raise SystemExit(f"cross-preview idempotency reuse returned HTTP {conflict_status}")

if old_first.get("replayed") is not False or old_first.get("counts", {}).get("created") != 1:
    raise SystemExit("old first apply did not create exactly one item")
if current_first.get("replayed") is not False or current_first.get("counts", {}).get("created") != 1:
    raise SystemExit("current first apply did not create exactly one item")
if current_replay.get("replayed") is not True or current_replay.get("applyId") != old_first.get("applyId"):
    raise SystemExit("current process did not replay the old-created claim")
if old_replay.get("replayed") is not True or old_replay.get("applyId") != current_first.get("applyId"):
    raise SystemExit("old process did not replay the current-created claim")

summary = {
    "oldFirstApplyStatus": old_first_status,
    "currentReplayStatus": current_replay_status,
    "currentFirstApplyStatus": current_first_status,
    "oldReplayStatus": old_replay_status,
    "crossPreviewIdempotencyConflictStatus": conflict_status,
    "oldToCurrentApplyIdStable": current_replay.get("applyId") == old_first.get("applyId"),
    "currentToOldApplyIdStable": old_replay.get("applyId") == current_first.get("applyId"),
    "oldToCurrentReplayMarked": current_replay.get("replayed") is True,
    "currentToOldReplayMarked": old_replay.get("replayed") is True,
    "rawTokensPersisted": False,
    "rawSyntheticIdsPersisted": False,
}
Path(os.environ["HTTP_SUMMARY"]).write_text(json.dumps(summary, indent=2) + "\n")
PY

APPLY_ROWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(*) FROM memory_os.apply_confirmation WHERE owner_account_id = '$ACCOUNT_ID';")"
MEMORY_ROWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(*) FROM memory_os.memory_item WHERE owner_account_id = '$ACCOUNT_ID';")"
DISTINCT_PREVIEWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(DISTINCT source_preview_id) FROM memory_os.memory_item WHERE owner_account_id = '$ACCOUNT_ID';")"
IN_PROGRESS_ROWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(*) FROM memory_os.apply_confirmation WHERE owner_account_id = '$ACCOUNT_ID' AND state = 'in_progress';")"

[[ "$APPLY_ROWS" == "2" && "$MEMORY_ROWS" == "2" && "$DISTINCT_PREVIEWS" == "2" && "$IN_PROGRESS_ROWS" == "0" ]] || {
  echo "mixed-version accounting mismatch: applies=$APPLY_ROWS memories=$MEMORY_ROWS previews=$DISTINCT_PREVIEWS in_progress=$IN_PROGRESS_ROWS" >&2
  exit 1
}

mkdir -p "$(dirname "$RESULT_PATH")"
SOURCE_SHA="$SOURCE_SHA" OLD_SHA="$OLD_SHA" HTTP_SUMMARY="$HTTP_SUMMARY" \
APPLY_ROWS="$APPLY_ROWS" MEMORY_ROWS="$MEMORY_ROWS" DISTINCT_PREVIEWS="$DISTINCT_PREVIEWS" \
IN_PROGRESS_ROWS="$IN_PROGRESS_ROWS" RESULT_PATH="$RESULT_PATH" python - <<'PY'
import datetime as dt
import json
import os
from pathlib import Path

summary = json.loads(Path(os.environ["HTTP_SUMMARY"]).read_text())
result = {
    "schemaVersion": "memory-os-mixed-version-apply-results.v1",
    "currentCommitSha": os.environ["SOURCE_SHA"],
    "oldBackendCommitSha": os.environ["OLD_SHA"],
    "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    "environment": {
        "mode": "GITHUB_ACTIONS_OR_LOCAL_POSTGRES16_MINIO_TWO_PROCESSES_SHARED_SCHEMA",
        "productionEvidence": False,
        "releaseCompatibilityEvidence": False,
        "historicalCandidateOnly": True,
        "containsSecrets": False,
        "syntheticDataOnly": True,
    },
    "result": "PASS",
    "integrityResult": "PASS",
    "assertions": {
        **summary,
        "applyConfirmationRows": int(os.environ["APPLY_ROWS"]),
        "memoryItemRows": int(os.environ["MEMORY_ROWS"]),
        "distinctSourcePreviews": int(os.environ["DISTINCT_PREVIEWS"]),
        "inProgressApplyRows": int(os.environ["IN_PROGRESS_ROWS"]),
        "sharedCurrentSchema": True,
        "oldAndCurrentProcessesConcurrent": True,
        "sameRequestHashStableAcrossVersions": True,
        "noDuplicateMaterialization": True,
    },
    "limitations": [
        "historical candidate rather than an approved predecessor release",
        "two synthetic ready Previews with one candidate each",
        "sequential mutation and replay rather than concurrent claim racing",
        "no process termination during an in-progress transaction",
        "no rolling traffic drain, rollback or destructive contract migration",
        "ephemeral PostgreSQL 16 and MinIO only",
        "not production compatibility evidence",
    ],
}
serialized = json.dumps(result, indent=2) + "\n"
for forbidden in ("postgres://", "postgresql://", "Bearer ", "acct_", "job_", "prv_", "idem-"):
    if forbidden in serialized:
        raise SystemExit(f"forbidden evidence content: {forbidden}")
Path(os.environ["RESULT_PATH"]).write_text(serialized, encoding="utf-8")
PY

printf 'Mixed-version Apply drill PASS: old=%s current=%s\n' "$OLD_SHA" "$SOURCE_SHA"
