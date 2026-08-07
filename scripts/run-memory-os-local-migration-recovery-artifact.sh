#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACT="$ROOT/contracts/operations/local-migration-recovery-artifact-contract.v1.json"
LIFECYCLE="$ROOT/contracts/operations/migration-lifecycle-contract.v1.json"
MIGRATION_DIR="$ROOT/infra/postgresql/security"
SOURCE_SHA="${MEMORY_OS_COMMIT_SHA:-}"
RUN_ID="${MEMORY_OS_MIGRATION_RUN_ID:-}"
RESULT_PATH="${MEMORY_OS_MIGRATION_RECOVERY_RESULT_PATH:-}"
SOURCE_DB="${MEMORY_OS_MIGRATION_SOURCE_DB:-memory_os_migration_recovery_source}"
RECOVERY_DB="${MEMORY_OS_MIGRATION_RECOVERY_DB:-memory_os_migration_recovery_target}"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_EPOCH="$(date +%s)"

fail() {
  printf 'LOCAL MIGRATION RECOVERY ARTIFACT FAILED: %s\n' "$*" >&2
  exit 1
}

now_ms() {
  python - <<'PY'
import time
print(time.time_ns() // 1_000_000)
PY
}

for command in psql pg_dump pg_restore python sha256sum; do
  command -v "$command" >/dev/null 2>&1 || fail "$command is required"
done
[[ -f "$CONTRACT" && -f "$LIFECYCLE" ]] || fail "migration contracts are missing"
[[ -d "$MIGRATION_DIR" ]] || fail "migration directory is missing"
[[ "${MEMORY_OS_ALLOW_EPHEMERAL_DATABASE_DROP:-}" == "1" ]] || fail "MEMORY_OS_ALLOW_EPHEMERAL_DATABASE_DROP=1 is required"
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "MEMORY_OS_COMMIT_SHA must be a full commit SHA"
[[ "$RUN_ID" =~ ^mig_[0-9]{8}_[a-z0-9][a-z0-9._-]{2,63}$ ]] || fail "MEMORY_OS_MIGRATION_RUN_ID format invalid"
[[ -n "$RESULT_PATH" ]] || fail "MEMORY_OS_MIGRATION_RECOVERY_RESULT_PATH is required"

PGHOST="${PGHOST:-127.0.0.1}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
export PGHOST PGPORT PGUSER
case "$PGHOST" in
  127.0.0.1|localhost|::1) ;;
  *) fail "runner is restricted to a local PostgreSQL host" ;;
esac
[[ "$SOURCE_DB" =~ ^[a-z][a-z0-9_]{2,62}$ ]] || fail "invalid source database name"
[[ "$RECOVERY_DB" =~ ^[a-z][a-z0-9_]{2,62}$ ]] || fail "invalid recovery database name"
[[ "$SOURCE_DB" != "$RECOVERY_DB" ]] || fail "source and recovery database must differ"
[[ "$SOURCE_DB" != "postgres" && "$RECOVERY_DB" != "postgres" ]] || fail "postgres database is protected"
DATABASE_IDENTITY_DIGEST="$(printf '%s' "LOCAL_POSTGRES_REHEARSAL:$SOURCE_DB:$RECOVERY_DB:$SOURCE_SHA" | sha256sum | awk '{print $1}')"
[[ "$DATABASE_IDENTITY_DIGEST" =~ ^[0-9a-f]{64}$ ]] || fail "database identity digest invalid"

mapfile -t MIGRATIONS < <(
  python - "$LIFECYCLE" <<'PY'
import json, sys
from pathlib import Path
value = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
for item in value['migrationSequence']:
    print(item)
PY
)
[[ "${#MIGRATIONS[@]}" -ge 2 ]] || fail "canonical migration sequence is too short"
UNDER_TEST="${MIGRATIONS[$(( ${#MIGRATIONS[@]} - 1 ))]}"
EXPECTED_UNDER_TEST="$(python - "$CONTRACT" <<'PY'
import json, sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))['migrationUnderTest'])
PY
)"
[[ "$UNDER_TEST" == "$EXPECTED_UNDER_TEST" ]] || fail "contract migrationUnderTest is stale: $UNDER_TEST"
BASELINE=("${MIGRATIONS[@]:0:${#MIGRATIONS[@]}-1}")
[[ "${#BASELINE[@]}" -eq "$(( ${#MIGRATIONS[@]} - 1 ))" ]] || fail "baseline sequence calculation failed"

SQL_TESTS=()
for migration in "${MIGRATIONS[@]}"; do
  test_path="$MIGRATION_DIR/test_${migration#*_}"
  [[ -f "$test_path" ]] || fail "missing SQL test for $migration"
  SQL_TESTS+=("$test_path")
done
UNDER_TEST_SPECIFIC_TEST="$MIGRATION_DIR/test_${UNDER_TEST#*_}"
TEST_HELPER_BOOTSTRAP="${SQL_TESTS[0]}"

DUMP_FILE="$(mktemp "${TMPDIR:-/tmp}/memory-os-migration-recovery.XXXXXX.dump")"
cleanup() {
  rm -f "$DUMP_FILE"
  if [[ "${MEMORY_OS_KEEP_MIGRATION_RECOVERY_DATABASES:-0}" != "1" ]]; then
    psql --dbname postgres --set=ON_ERROR_STOP=1 --quiet <<SQL >/dev/null 2>&1 || true
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname IN ('$SOURCE_DB', '$RECOVERY_DB') AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$SOURCE_DB";
DROP DATABASE IF EXISTS "$RECOVERY_DB";
SQL
  fi
}
trap cleanup EXIT

psql --dbname postgres --set=ON_ERROR_STOP=1 --quiet <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname IN ('$SOURCE_DB', '$RECOVERY_DB') AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$SOURCE_DB";
DROP DATABASE IF EXISTS "$RECOVERY_DB";
CREATE DATABASE "$SOURCE_DB";
CREATE DATABASE "$RECOVERY_DB";
SQL

for migration in "${BASELINE[@]}"; do
  psql --dbname "$SOURCE_DB" --set=ON_ERROR_STOP=1 --file "$MIGRATION_DIR/$migration" >/dev/null
done

PRE_SOURCE_APPLE_IDENTITY="$(psql --dbname "$SOURCE_DB" --tuples-only --no-align --command \
  "SELECT CASE WHEN to_regclass('memory_os.apple_identity') IS NULL THEN 0 ELSE 1 END;")"
PRE_SOURCE_APPLE_REPLAY="$(psql --dbname "$SOURCE_DB" --tuples-only --no-align --command \
  "SELECT CASE WHEN to_regclass('memory_os.apple_replay') IS NULL THEN 0 ELSE 1 END;")"
[[ "$PRE_SOURCE_APPLE_IDENTITY" == "0" && "$PRE_SOURCE_APPLE_REPLAY" == "0" ]] || \
  fail "pre-migration source already contains migration-under-test surface"

pg_dump --format=custom --compress=6 --no-comments --file "$DUMP_FILE" "$SOURCE_DB"
[[ -s "$DUMP_FILE" ]] || fail "recovery artifact dump is empty"
ARTIFACT_DIGEST="$(sha256sum "$DUMP_FILE" | awk '{print $1}')"
ARTIFACT_BYTES="$(wc -c < "$DUMP_FILE" | tr -d ' ')"
[[ "$ARTIFACT_DIGEST" =~ ^[0-9a-f]{64}$ ]] || fail "recovery artifact digest invalid"
[[ "$ARTIFACT_BYTES" =~ ^[0-9]+$ && "$ARTIFACT_BYTES" -gt 0 ]] || fail "recovery artifact byte count invalid"

APPLY_STARTED_MS="$(now_ms)"
psql --dbname "$SOURCE_DB" --set=ON_ERROR_STOP=1 --file "$MIGRATION_DIR/$UNDER_TEST" >/dev/null
APPLY_COMPLETED_MS="$(now_ms)"
APPLY_DURATION_MS="$((APPLY_COMPLETED_MS - APPLY_STARTED_MS))"
[[ "$APPLY_DURATION_MS" -ge 0 ]] || fail "migration apply duration invalid"
# The security SQL suites share the memory_os_test assertion helpers created by
# the first suite. Bootstrap those helpers before executing the migration-under-
# test suite in isolation; the recovery database below still runs the complete
# canonical suite in order.
psql --dbname "$SOURCE_DB" --set=ON_ERROR_STOP=1 --file "$TEST_HELPER_BOOTSTRAP" >/dev/null
psql --dbname "$SOURCE_DB" --set=ON_ERROR_STOP=1 --file "$UNDER_TEST_SPECIFIC_TEST" >/dev/null
POST_SOURCE_APPLE_IDENTITY="$(psql --dbname "$SOURCE_DB" --tuples-only --no-align --command \
  "SELECT CASE WHEN to_regclass('memory_os.apple_identity') IS NULL THEN 0 ELSE 1 END;")"
[[ "$POST_SOURCE_APPLE_IDENTITY" == "1" ]] || fail "migration-under-test surface missing after source apply"

pg_restore --exit-on-error --dbname "$RECOVERY_DB" "$DUMP_FILE" >/dev/null
PRE_RECOVERY_APPLE_IDENTITY="$(psql --dbname "$RECOVERY_DB" --tuples-only --no-align --command \
  "SELECT CASE WHEN to_regclass('memory_os.apple_identity') IS NULL THEN 0 ELSE 1 END;")"
PRE_RECOVERY_APPLE_REPLAY="$(psql --dbname "$RECOVERY_DB" --tuples-only --no-align --command \
  "SELECT CASE WHEN to_regclass('memory_os.apple_replay') IS NULL THEN 0 ELSE 1 END;")"
[[ "$PRE_RECOVERY_APPLE_IDENTITY" == "0" && "$PRE_RECOVERY_APPLE_REPLAY" == "0" ]] || \
  fail "restored artifact did not recover pre-migration surface"

psql --dbname "$RECOVERY_DB" --set=ON_ERROR_STOP=1 --file "$MIGRATION_DIR/$UNDER_TEST" >/dev/null
for test_file in "${SQL_TESTS[@]}"; do
  psql --dbname "$RECOVERY_DB" --set=ON_ERROR_STOP=1 --file "$test_file" >/dev/null
done
POST_RECOVERY_APPLE_IDENTITY="$(psql --dbname "$RECOVERY_DB" --tuples-only --no-align --command \
  "SELECT CASE WHEN to_regclass('memory_os.apple_identity') IS NULL THEN 0 ELSE 1 END;")"
POST_RECOVERY_APPLE_REPLAY="$(psql --dbname "$RECOVERY_DB" --tuples-only --noalign --command \
  "SELECT CASE WHEN to_regclass('memory_os.apple_replay') IS NULL THEN 0 ELSE 1 END;")"
[[ "$POST_RECOVERY_APPLE_IDENTITY" == "1" && "$POST_RECOVERY_APPLE_REPLAY" == "1" ]] || \
  fail "migration reapply after recovery did not restore current surface"

COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
END_EPOCH="$(date +%s)"
DURATION_SECONDS="$((END_EPOCH - START_EPOCH))"
mkdir -p "$(dirname "$RESULT_PATH")"

SOURCE_SHA="$SOURCE_SHA" RUN_ID="$RUN_ID" STARTED_AT="$STARTED_AT" COMPLETED_AT="$COMPLETED_AT" \
DURATION_SECONDS="$DURATION_SECONDS" APPLY_DURATION_MS="$APPLY_DURATION_MS" \
DATABASE_IDENTITY_DIGEST="$DATABASE_IDENTITY_DIGEST" UNDER_TEST="$UNDER_TEST" \
BASELINE_COUNT="${#BASELINE[@]}" FINAL_COUNT="${#MIGRATIONS[@]}" SQL_TEST_COUNT="${#SQL_TESTS[@]}" \
ARTIFACT_DIGEST="$ARTIFACT_DIGEST" ARTIFACT_BYTES="$ARTIFACT_BYTES" RESULT_PATH="$RESULT_PATH" \
python - <<'PY'
import datetime as dt
import json
import os
from pathlib import Path

assertions = {
    'sourceBaselineApplied': True,
    'recoveryArtifactDigestRecorded': True,
    'migrationAppliedOnSource': True,
    'migrationSpecificSourceTestPassed': True,
    'exactRecoveryArtifactRestored': True,
    'preMigrationSurfaceRecovered': True,
    'migrationReappliedAfterRestore': True,
    'canonicalSqlSuitePassedAfterRecovery': True,
    'actualRecoveryArtifactRestored': True,
    'containsSecrets': False,
    'productionTraffic': False,
    'productionCredentials': False,
    'productionEvidence': False,
}
result = {
    'schemaVersion': 'memory-os-local-migration-recovery-artifact.v1',
    'migrationRunId': os.environ['RUN_ID'],
    'commitSha': os.environ['SOURCE_SHA'],
    'generatedAt': dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z'),
    'environmentClass': 'LOCAL_POSTGRES_REHEARSAL',
    'databaseMode': 'EPHEMERAL_POSTGRESQL_16_SAME_CLUSTER_PREMIGRATION_LOGICAL_RECOVERY',
    'databaseIdentityDigest': os.environ['DATABASE_IDENTITY_DIGEST'],
    'migrationUnderTest': os.environ['UNDER_TEST'],
    'startedAt': os.environ['STARTED_AT'],
    'completedAt': os.environ['COMPLETED_AT'],
    'durationSeconds': int(os.environ['DURATION_SECONDS']),
    'migrationApplyDurationMs': int(os.environ['APPLY_DURATION_MS']),
    'baselineMigrationCount': int(os.environ['BASELINE_COUNT']),
    'finalMigrationCount': int(os.environ['FINAL_COUNT']),
    'sqlIntegrationTestsExecutedAfterRecovery': int(os.environ['SQL_TEST_COUNT']),
    'recoveryArtifact': {
        'reference': 'sha256:' + os.environ['ARTIFACT_DIGEST'],
        'sha256': os.environ['ARTIFACT_DIGEST'],
        'bytes': int(os.environ['ARTIFACT_BYTES']),
        'rawArtifactCommitted': False,
    },
    'assertions': assertions,
    'result': 'PASS',
    'integrityResult': 'PASS',
    'limitations': [
        'same PostgreSQL cluster logical dump and restore',
        'not PITR, WAL archive, physical backup or replication evidence',
        'not production-equivalent infrastructure or credentials',
        'not proof that a production migration may be automatically rolled back',
        'does not exercise application traffic during migration',
        'clean isolated database has no competing sessions by construction and therefore does not provide production lock-wait telemetry',
        'does not satisfy destructive-contract isolated restore approval',
    ],
}
Path(os.environ['RESULT_PATH']).write_text(
    json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
)
PY

printf 'Memory OS local migration recovery artifact rehearsal PASS\n'
printf 'migration: %s  apply ms: %s  artifact sha256: %s  bytes: %s\n' \
  "$UNDER_TEST" "$APPLY_DURATION_MS" "$ARTIFACT_DIGEST" "$ARTIFACT_BYTES"
printf 'result: %s\n' "$RESULT_PATH"
