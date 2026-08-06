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
FIXTURE_C="$TMP_DIR/preview-c.json"
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
    "JOB_C": "job_" + seed[8:32],
    "PREVIEW_A": "prv_" + seed[0:24],
    "PREVIEW_B": "prv_" + seed[24:48],
    "PREVIEW_C": "prv_" + seed[8:32],
    "SPOOL_A": "spl_" + seed[0:24],
    "SPOOL_B": "spl_" + seed[24:48],
    "SPOOL_C": "spl_" + seed[8:32],
    "UPLOAD_A": "upl_" + seed[0:24],
    "UPLOAD_B": "upl_" + seed[24:48],
    "UPLOAD_C": "upl_" + seed[8:32],
    "FINGERPRINT_A": "fp-mixed-" + seed[0:24],
    "FINGERPRINT_B": "fp-mixed-" + seed[24:48],
    "FINGERPRINT_C": "fp-mixed-" + seed[8:32],
    "IDEMPOTENCY_A": "idem-mixed-" + seed[0:24],
    "IDEMPOTENCY_B": "idem-mixed-" + seed[24:48],
    "IDEMPOTENCY_C": "idem-mixed-" + seed[8:32],
}
if len(set(values.values())) != len(values):
    raise SystemExit("synthetic fixture identifiers are not unique")
Path(os.environ["OUTPUT"]).write_text(
    "".join(f"{name}={value}\n" for name, value in values.items()),
    encoding="utf-8",
)
PY
# Values are generated from lowercase hexadecimal and fixed prefixes only.
# shellcheck disable=SC1090
source "$IDENTITY_ENV"

printf 'MIXED-VERSION APPLY STAGE: apply-current-migrations\n'
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
  PGOPTIONS='-c client_min_messages=warning' \
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

printf 'MIXED-VERSION APPLY STAGE: build-old-current-and-fixture\n'
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

printf 'MIXED-VERSION APPLY STAGE: commit-three-synthetic-previews\n'
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
"$FIXTURE_BIN" \
  -database-url "$MEMORY_OS_TEST_DATABASE_URL" \
  -account-id "$ACCOUNT_ID" -job-id "$JOB_C" -preview-id "$PREVIEW_C" \
  -spool-id "$SPOOL_C" -upload-id "$UPLOAD_C" -fingerprint "$FINGERPRINT_C" \
  >"$FIXTURE_C"

"$OLD_BIN" -database-url "$MEMORY_OS_TEST_DATABASE_URL" \
  -dev-issue-session "$ACCOUNT_ID" >"$OLD_TOKEN_FILE"
"$CURRENT_BIN" -database-url "$MEMORY_OS_TEST_DATABASE_URL" \
  -dev-issue-session "$ACCOUNT_ID" >"$CURRENT_TOKEN_FILE"
OLD_TOKEN="$(extract_token "$OLD_TOKEN_FILE")"
CURRENT_TOKEN="$(extract_token "$CURRENT_TOKEN_FILE")"
rm -f "$OLD_TOKEN_FILE" "$CURRENT_TOKEN_FILE"

printf 'MIXED-VERSION APPLY STAGE: start-two-processes\n'
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

printf 'MIXED-VERSION APPLY STAGE: execute-bidirectional-apply-replay\n'
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


def created_count(response):
    counts = response.get("counts", {})
    return counts.get("created", counts.get("Created"))


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

if old_first.get("replayed") is not False or created_count(old_first) != 1:
    raise SystemExit("old first apply did not create exactly one item")
if current_first.get("replayed") is not False or created_count(current_first) != 1:
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

printf 'MIXED-VERSION APPLY STAGE: verify-sequential-accounting\n'
APPLY_ROWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(*) FROM memory_os.apply_confirmation WHERE owner_account_id = '$ACCOUNT_ID';")"
MEMORY_ROWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(*) FROM memory_os.memory_item WHERE owner_account_id = '$ACCOUNT_ID';")"
DISTINCT_PREVIEWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(DISTINCT source_preview_id) FROM memory_os.memory_item WHERE owner_account_id = '$ACCOUNT_ID';")"
IN_PROGRESS_ROWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(*) FROM memory_os.apply_confirmation WHERE owner_account_id = '$ACCOUNT_ID' AND state = 'in_progress';")"

[[ "$APPLY_ROWS" == "2" && "$MEMORY_ROWS" == "2" && "$DISTINCT_PREVIEWS" == "2" && "$IN_PROGRESS_ROWS" == "0" ]] || {
  echo "sequential accounting mismatch: applies=$APPLY_ROWS memories=$MEMORY_ROWS previews=$DISTINCT_PREVIEWS in_progress=$IN_PROGRESS_ROWS" >&2
  exit 1
}

printf 'MIXED-VERSION APPLY STAGE: execute-concurrent-old-current-claim-race\n'
OLD_TOKEN="$OLD_TOKEN" CURRENT_TOKEN="$CURRENT_TOKEN" \
OLD_URL="http://127.0.0.1:$OLD_PORT" CURRENT_URL="http://127.0.0.1:$CURRENT_PORT" \
FIXTURE_C="$FIXTURE_C" IDEMPOTENCY_C="$IDEMPOTENCY_C" \
HTTP_SUMMARY="$HTTP_SUMMARY" python - <<'PY'
import concurrent.futures
import json
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path

old_url = os.environ["OLD_URL"]
current_url = os.environ["CURRENT_URL"]
old_token = os.environ["OLD_TOKEN"]
current_token = os.environ["CURRENT_TOKEN"]
fixture = json.loads(Path(os.environ["FIXTURE_C"]).read_text())
key = os.environ["IDEMPOTENCY_C"]
barrier = threading.Barrier(3)


def apply(base, token):
    barrier.wait(timeout=10)
    payload = json.dumps({
        "previewSha256": fixture["previewSha256"],
        "idempotencyKey": key,
        "duplicatePolicy": "skip_existing",
    }).encode()
    request = urllib.request.Request(
        base + f"/v1/previews/{fixture['previewId']}/apply",
        data=payload,
        method="POST",
    )
    request.add_header("Authorization", "Bearer " + token)
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(1 << 20)
            return response.status, json.loads(raw or b"{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read(1 << 20)
        try:
            decoded = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            decoded = {}
        return exc.code, decoded


with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    old_future = executor.submit(apply, old_url, current_token)
    current_future = executor.submit(apply, current_url, old_token)
    barrier.wait(timeout=10)
    results = [old_future.result(timeout=30), current_future.result(timeout=30)]

statuses = sorted(status for status, _ in results)
responses = [body for _, body in results]
replayed = sorted(body.get("replayed") for body in responses)
apply_ids = {body.get("applyId") for body in responses}
if statuses != [200, 200]:
    raise SystemExit(f"concurrent old/current Apply statuses were {statuses}")
if replayed != [False, True]:
    raise SystemExit(f"concurrent old/current replay split was {replayed}")
if len(apply_ids) != 1 or None in apply_ids:
    raise SystemExit("concurrent old/current requests did not converge on one Apply ID")

summary_path = Path(os.environ["HTTP_SUMMARY"])
summary = json.loads(summary_path.read_text())
summary.update({
    "concurrentOldCurrentClaimRaceStatuses": statuses,
    "concurrentOldCurrentClaimRaceReplaySplit": True,
    "concurrentOldCurrentClaimRaceApplyIdStable": True,
    "concurrentOldCurrentClaimRacePassed": True,
})
summary_path.write_text(json.dumps(summary, indent=2) + "\n")
PY

printf 'MIXED-VERSION APPLY STAGE: verify-final-race-accounting\n'
FINAL_APPLY_ROWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(*) FROM memory_os.apply_confirmation WHERE owner_account_id = '$ACCOUNT_ID';")"
FINAL_MEMORY_ROWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(*) FROM memory_os.memory_item WHERE owner_account_id = '$ACCOUNT_ID';")"
FINAL_DISTINCT_PREVIEWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(DISTINCT source_preview_id) FROM memory_os.memory_item WHERE owner_account_id = '$ACCOUNT_ID';")"
FINAL_IN_PROGRESS_ROWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(*) FROM memory_os.apply_confirmation WHERE owner_account_id = '$ACCOUNT_ID' AND state = 'in_progress';")"
RACE_APPLY_ROWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(*) FROM memory_os.apply_confirmation WHERE owner_account_id = '$ACCOUNT_ID' AND preview_id = '$PREVIEW_C';")"
RACE_MEMORY_ROWS="$(psql "$MEMORY_OS_TEST_DATABASE_URL" --tuples-only --no-align --set=ON_ERROR_STOP=1 \
  --command "SELECT count(*) FROM memory_os.memory_item WHERE owner_account_id = '$ACCOUNT_ID' AND source_preview_id = '$PREVIEW_C';")"

[[ "$FINAL_APPLY_ROWS" == "3" && "$FINAL_MEMORY_ROWS" == "3" && \
   "$FINAL_DISTINCT_PREVIEWS" == "3" && "$FINAL_IN_PROGRESS_ROWS" == "0" && \
   "$RACE_APPLY_ROWS" == "1" && "$RACE_MEMORY_ROWS" == "1" ]] || {
  echo "race accounting mismatch: applies=$FINAL_APPLY_ROWS memories=$FINAL_MEMORY_ROWS previews=$FINAL_DISTINCT_PREVIEWS in_progress=$FINAL_IN_PROGRESS_ROWS race_applies=$RACE_APPLY_ROWS race_memories=$RACE_MEMORY_ROWS" >&2
  exit 1
}

mkdir -p "$(dirname "$RESULT_PATH")"
SOURCE_SHA="$SOURCE_SHA" OLD_SHA="$OLD_SHA" HTTP_SUMMARY="$HTTP_SUMMARY" \
APPLY_ROWS="$APPLY_ROWS" MEMORY_ROWS="$MEMORY_ROWS" DISTINCT_PREVIEWS="$DISTINCT_PREVIEWS" \
IN_PROGRESS_ROWS="$IN_PROGRESS_ROWS" FINAL_APPLY_ROWS="$FINAL_APPLY_ROWS" \
FINAL_MEMORY_ROWS="$FINAL_MEMORY_ROWS" FINAL_DISTINCT_PREVIEWS="$FINAL_DISTINCT_PREVIEWS" \
FINAL_IN_PROGRESS_ROWS="$FINAL_IN_PROGRESS_ROWS" RACE_APPLY_ROWS="$RACE_APPLY_ROWS" \
RACE_MEMORY_ROWS="$RACE_MEMORY_ROWS" RESULT_PATH="$RESULT_PATH" python - <<'PY'
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
        "finalApplyConfirmationRows": int(os.environ["FINAL_APPLY_ROWS"]),
        "finalMemoryItemRows": int(os.environ["FINAL_MEMORY_ROWS"]),
        "finalDistinctSourcePreviews": int(os.environ["FINAL_DISTINCT_PREVIEWS"]),
        "finalInProgressApplyRows": int(os.environ["FINAL_IN_PROGRESS_ROWS"]),
        "racedPreviewApplyConfirmationRows": int(os.environ["RACE_APPLY_ROWS"]),
        "racedPreviewMemoryItemRows": int(os.environ["RACE_MEMORY_ROWS"]),
        "sharedCurrentSchema": True,
        "oldAndCurrentProcessesConcurrent": True,
        "sameRequestHashStableAcrossVersions": True,
        "noDuplicateMaterialization": True,
    },
    "limitations": [
        "historical candidate rather than an approved predecessor release",
        "three synthetic ready Previews with one candidate each",
        "one simultaneous old/current claim race without process termination",
        "no host or process failure during an in-progress transaction",
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

printf 'Mixed-version Apply drill PASS: old=%s current=%s concurrent-race=true\n' "$OLD_SHA" "$SOURCE_SHA"
