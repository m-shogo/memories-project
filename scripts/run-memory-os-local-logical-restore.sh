#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACT="$ROOT/contracts/operations/local-logical-restore-contract.v1.json"
MIGRATION_CONTRACT="$ROOT/contracts/operations/migration-lifecycle-contract.v1.json"
MIGRATION_DIR="$ROOT/infra/postgresql/security"
RESULT_PATH="${MEMORY_OS_LOCAL_LOGICAL_RESTORE_RESULTS_PATH:-$ROOT/docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json}"
SOURCE_DB="${MEMORY_OS_RESTORE_SOURCE_DB:-memory_os_restore_source}"
TARGET_DB="${MEMORY_OS_RESTORE_TARGET_DB:-memory_os_restore_target}"
SOURCE_SHA="${MEMORY_OS_COMMIT_SHA:-}"
START_EPOCH="$(date +%s)"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

fail() {
  printf 'LOCAL LOGICAL RESTORE FAILED: %s\n' "$*" >&2
  exit 1
}

command -v psql >/dev/null 2>&1 || fail "psql is required"
command -v pg_dump >/dev/null 2>&1 || fail "pg_dump is required"
command -v pg_restore >/dev/null 2>&1 || fail "pg_restore is required"
command -v python >/dev/null 2>&1 || fail "python is required"
[[ -f "$CONTRACT" ]] || fail "missing logical restore contract"
[[ -f "$MIGRATION_CONTRACT" ]] || fail "missing migration lifecycle contract"
[[ -d "$MIGRATION_DIR" ]] || fail "missing migration directory"
[[ "${MEMORY_OS_ALLOW_EPHEMERAL_DATABASE_DROP:-}" == "1" ]] || \
  fail "MEMORY_OS_ALLOW_EPHEMERAL_DATABASE_DROP=1 is required"

PGHOST="${PGHOST:-127.0.0.1}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
export PGHOST PGPORT PGUSER
case "$PGHOST" in
  127.0.0.1|localhost|::1) ;;
  *) fail "runner is restricted to a local PostgreSQL host" ;;
esac
[[ "$SOURCE_DB" =~ ^[a-z][a-z0-9_]{2,62}$ ]] || fail "invalid source database name"
[[ "$TARGET_DB" =~ ^[a-z][a-z0-9_]{2,62}$ ]] || fail "invalid target database name"
[[ "$SOURCE_DB" != "$TARGET_DB" ]] || fail "source and target database must differ"
[[ "$SOURCE_DB" != "postgres" && "$TARGET_DB" != "postgres" ]] || fail "postgres database is protected"
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "MEMORY_OS_COMMIT_SHA must be a full commit SHA"

mapfile -t MIGRATIONS < <(
  python - "$MIGRATION_CONTRACT" <<'PY'
import json
import sys
from pathlib import Path
value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for item in value["migrationSequence"]:
    print(item)
PY
)
[[ "${#MIGRATIONS[@]}" -gt 0 ]] || fail "canonical migration sequence is empty"

SQL_TESTS=()
for migration in "${MIGRATIONS[@]}"; do
  test_name="test_${migration#*_}"
  test_path="$MIGRATION_DIR/$test_name"
  [[ -f "$test_path" ]] || fail "missing SQL integration test for migration: $migration"
  SQL_TESTS+=("$test_path")
done
[[ "${#SQL_TESTS[@]}" -eq "${#MIGRATIONS[@]}" ]] || \
  fail "SQL integration test count does not match migration count"

DUMP_FILE="$(mktemp "${TMPDIR:-/tmp}/memory-os-logical-restore.XXXXXX.dump")"
cleanup() {
  rm -f "$DUMP_FILE"
  if [[ "${MEMORY_OS_KEEP_RESTORE_DATABASES:-0}" != "1" ]]; then
    psql --dbname postgres --set=ON_ERROR_STOP=1 --quiet <<SQL >/dev/null 2>&1 || true
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname IN ('$SOURCE_DB', '$TARGET_DB') AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$SOURCE_DB";
DROP DATABASE IF EXISTS "$TARGET_DB";
SQL
  fi
}
trap cleanup EXIT

psql --dbname postgres --set=ON_ERROR_STOP=1 --quiet <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname IN ('$SOURCE_DB', '$TARGET_DB') AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$SOURCE_DB";
DROP DATABASE IF EXISTS "$TARGET_DB";
CREATE DATABASE "$SOURCE_DB";
CREATE DATABASE "$TARGET_DB";
SQL

for migration in "${MIGRATIONS[@]}"; do
  [[ -f "$MIGRATION_DIR/$migration" ]] || fail "missing migration: $migration"
  psql --dbname "$SOURCE_DB" --set=ON_ERROR_STOP=1 --file "$MIGRATION_DIR/$migration" >/dev/null
done

SYNTHETIC_ACCOUNT="acct_restore_deleted_0001"
SYNTHETIC_SESSION="ses_restore_deleted_0001"
SYNTHETIC_DIGEST="dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
SESSION_OWNER="acct_restore_session_owner_0001"
EXPIRED_SESSION="ses_restore_expired_0001"
EXPIRED_DIGEST="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
REVOKED_SESSION="ses_restore_revoked_0001"
REVOKED_DIGEST="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

psql --dbname "$SOURCE_DB" --set=ON_ERROR_STOP=1 --quiet <<SQL
INSERT INTO memory_os.account_control
  (account_id, account_epoch, state, created_at, updated_at)
VALUES
  ('$SYNTHETIC_ACCOUNT', 1, 'active', now(), now()),
  ('$SESSION_OWNER', 1, 'active', now(), now());
INSERT INTO memory_os.account_session
  (id, token_digest, owner_account_id, account_epoch, authority, state, created_at, expires_at)
VALUES
  ('$SYNTHETIC_SESSION', '$SYNTHETIC_DIGEST', '$SYNTHETIC_ACCOUNT', 1,
   'ios_device_session', 'active', now(), now() + interval '1 hour'),
  ('$EXPIRED_SESSION', '$EXPIRED_DIGEST', '$SESSION_OWNER', 1,
   'ios_device_session', 'active', now() - interval '2 hours', now() - interval '1 hour'),
  ('$REVOKED_SESSION', '$REVOKED_DIGEST', '$SESSION_OWNER', 1,
   'ios_device_session', 'revoked', now() - interval '10 minutes', now() + interval '1 hour');
DELETE FROM memory_os.account_session WHERE id = '$SYNTHETIC_SESSION';
DELETE FROM memory_os.account_control WHERE account_id = '$SYNTHETIC_ACCOUNT';
SQL

SOURCE_ACCOUNT_COUNT="$(psql --dbname "$SOURCE_DB" --tuples-only --no-align --command \
  "SELECT count(*) FROM memory_os.account_control WHERE account_id = '$SYNTHETIC_ACCOUNT';")"
SOURCE_SESSION_COUNT="$(psql --dbname "$SOURCE_DB" --tuples-only --no-align --command \
  "SELECT count(*) FROM memory_os.account_session WHERE token_digest = '$SYNTHETIC_DIGEST';")"
SOURCE_EXPIRED_COUNT="$(psql --dbname "$SOURCE_DB" --tuples-only --no-align --command \
  "SELECT count(*) FROM memory_os.account_session WHERE token_digest = '$EXPIRED_DIGEST' AND state = 'active' AND expires_at <= now();")"
SOURCE_REVOKED_COUNT="$(psql --dbname "$SOURCE_DB" --tuples-only --no-align --command \
  "SELECT count(*) FROM memory_os.account_session WHERE token_digest = '$REVOKED_DIGEST' AND state = 'revoked';")"
[[ "$SOURCE_ACCOUNT_COUNT" == "0" && "$SOURCE_SESSION_COUNT" == "0" ]] || \
  fail "synthetic deletion did not complete before dump"
[[ "$SOURCE_EXPIRED_COUNT" == "1" && "$SOURCE_REVOKED_COUNT" == "1" ]] || \
  fail "expired/revoked synthetic session setup is invalid before dump"

pg_dump --format=custom --compress=6 --no-comments --file "$DUMP_FILE" "$SOURCE_DB"
[[ -s "$DUMP_FILE" ]] || fail "logical dump is empty"
pg_restore --exit-on-error --dbname "$TARGET_DB" "$DUMP_FILE" >/dev/null

ROLE_COUNT="$(psql --dbname "$TARGET_DB" --tuples-only --no-align <<'SQL'
SELECT count(*)
FROM pg_roles
WHERE rolname IN (
  'memory_api_runtime',
  'memory_worker_runtime',
  'memory_deletion_runtime',
  'memory_auth_runtime'
)
AND rolbypassrls = false;
SQL
)"
FORCE_RLS_COUNT="$(psql --dbname "$TARGET_DB" --tuples-only --no-align <<'SQL'
SELECT count(*)
FROM pg_class AS relation
JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
WHERE namespace.nspname = 'memory_os'
  AND relation.relkind = 'r'
  AND relation.relforcerowsecurity = true;
SQL
)"
TARGET_ACCOUNT_COUNT="$(psql --dbname "$TARGET_DB" --tuples-only --no-align --command \
  "SELECT count(*) FROM memory_os.account_control WHERE account_id = '$SYNTHETIC_ACCOUNT';")"
TARGET_SESSION_COUNT="$(psql --dbname "$TARGET_DB" --tuples-only --no-align --command \
  "SELECT count(*) FROM memory_os.account_session WHERE token_digest = '$SYNTHETIC_DIGEST';")"
TARGET_EXPIRED_COUNT="$(psql --dbname "$TARGET_DB" --tuples-only --no-align --command \
  "SELECT count(*) FROM memory_os.account_session WHERE token_digest = '$EXPIRED_DIGEST' AND state = 'active' AND expires_at <= now();")"
TARGET_REVOKED_COUNT="$(psql --dbname "$TARGET_DB" --tuples-only --no-align --command \
  "SELECT count(*) FROM memory_os.account_session WHERE token_digest = '$REVOKED_DIGEST' AND state = 'revoked';")"
RESOLVED_SESSION_OUTPUT="$(psql --dbname "$TARGET_DB" --tuples-only --no-align --quiet <<SQL
SET ROLE memory_auth_runtime;
SELECT count(*) FROM memory_os.resolve_account_session('$SYNTHETIC_DIGEST');
RESET ROLE;
SQL
)"
RESOLVED_SESSION_COUNT="$(printf '%s\n' "$RESOLVED_SESSION_OUTPUT" | grep -E '^[0-9]+$' | tail -n 1)"
RESOLVED_EXPIRED_OUTPUT="$(psql --dbname "$TARGET_DB" --tuples-only --no-align --quiet <<SQL
SET ROLE memory_auth_runtime;
SELECT count(*) FROM memory_os.resolve_account_session('$EXPIRED_DIGEST');
RESET ROLE;
SQL
)"
RESOLVED_EXPIRED_COUNT="$(printf '%s\n' "$RESOLVED_EXPIRED_OUTPUT" | grep -E '^[0-9]+$' | tail -n 1)"
RESOLVED_REVOKED_OUTPUT="$(psql --dbname "$TARGET_DB" --tuples-only --no-align --quiet <<SQL
SET ROLE memory_auth_runtime;
SELECT count(*) FROM memory_os.resolve_account_session('$REVOKED_DIGEST');
RESET ROLE;
SQL
)"
RESOLVED_REVOKED_COUNT="$(printf '%s\n' "$RESOLVED_REVOKED_OUTPUT" | grep -E '^[0-9]+$' | tail -n 1)"
[[ -n "$RESOLVED_SESSION_COUNT" && -n "$RESOLVED_EXPIRED_COUNT" && -n "$RESOLVED_REVOKED_COUNT" ]] || \
  fail "synthetic session resolution count was not numeric"

[[ "$ROLE_COUNT" == "4" ]] || fail "runtime role verification failed: $ROLE_COUNT"
[[ "$FORCE_RLS_COUNT" =~ ^[0-9]+$ && "$FORCE_RLS_COUNT" -gt 0 ]] || \
  fail "FORCE RLS verification failed: $FORCE_RLS_COUNT"
[[ "$TARGET_ACCOUNT_COUNT" == "0" ]] || fail "deleted synthetic account resurrected"
[[ "$TARGET_SESSION_COUNT" == "0" ]] || fail "deleted synthetic session digest resurrected"
[[ "$RESOLVED_SESSION_COUNT" == "0" ]] || fail "deleted synthetic token resolved after restore"
[[ "$TARGET_EXPIRED_COUNT" == "1" ]] || fail "expired synthetic session state was lost or changed during restore"
[[ "$TARGET_REVOKED_COUNT" == "1" ]] || fail "revoked synthetic session state was lost or changed during restore"
[[ "$RESOLVED_EXPIRED_COUNT" == "0" ]] || fail "expired synthetic token resolved after restore"
[[ "$RESOLVED_REVOKED_COUNT" == "0" ]] || fail "revoked synthetic token resolved after restore"

for test_file in "${SQL_TESTS[@]}"; do
  psql --dbname "$TARGET_DB" --set=ON_ERROR_STOP=1 --file "$test_file" >/dev/null
done

DUMP_BYTES="$(wc -c < "$DUMP_FILE" | tr -d ' ')"
END_EPOCH="$(date +%s)"
DURATION_SECONDS="$((END_EPOCH - START_EPOCH))"
COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DATABASE_IDENTITY_DIGEST="$(printf '%s' "$PGHOST:$PGPORT:$SOURCE_DB:$TARGET_DB" | sha256sum | awk '{print $1}')"
mkdir -p "$(dirname "$RESULT_PATH")"

SOURCE_SHA="$SOURCE_SHA" \
STARTED_AT="$STARTED_AT" \
COMPLETED_AT="$COMPLETED_AT" \
DURATION_SECONDS="$DURATION_SECONDS" \
DATABASE_IDENTITY_DIGEST="$DATABASE_IDENTITY_DIGEST" \
MIGRATION_COUNT="${#MIGRATIONS[@]}" \
SQL_TEST_COUNT="${#SQL_TESTS[@]}" \
DUMP_BYTES="$DUMP_BYTES" \
ROLE_COUNT="$ROLE_COUNT" \
FORCE_RLS_COUNT="$FORCE_RLS_COUNT" \
TARGET_ACCOUNT_COUNT="$TARGET_ACCOUNT_COUNT" \
TARGET_SESSION_COUNT="$TARGET_SESSION_COUNT" \
RESOLVED_SESSION_COUNT="$RESOLVED_SESSION_COUNT" \
TARGET_EXPIRED_COUNT="$TARGET_EXPIRED_COUNT" \
TARGET_REVOKED_COUNT="$TARGET_REVOKED_COUNT" \
RESOLVED_EXPIRED_COUNT="$RESOLVED_EXPIRED_COUNT" \
RESOLVED_REVOKED_COUNT="$RESOLVED_REVOKED_COUNT" \
RESULT_PATH="$RESULT_PATH" \
python - <<'PY'
import datetime as dt
import json
import os
from pathlib import Path

result = {
    "schemaVersion": "memory-os-local-logical-restore-results.v1",
    "commitSha": os.environ["SOURCE_SHA"],
    "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    "environment": {
        "databaseMode": "EPHEMERAL_POSTGRESQL_16_SAME_CLUSTER_LOGICAL_RESTORE",
        "productionEvidence": False,
        "databaseIdentityDigest": os.environ["DATABASE_IDENTITY_DIGEST"],
        "containsSecrets": False,
    },
    "scenario": {
        "scenarioId": "postgresql-logical-dump-isolated-restore-smoke",
        "startedAt": os.environ["STARTED_AT"],
        "completedAt": os.environ["COMPLETED_AT"],
        "durationSeconds": int(os.environ["DURATION_SECONDS"]),
        "migrationFilesApplied": int(os.environ["MIGRATION_COUNT"]),
        "sqlIntegrationTestsExecuted": int(os.environ["SQL_TEST_COUNT"]),
        "dumpBytes": int(os.environ["DUMP_BYTES"]),
        "assertions": {
            "runtimeRolesWithoutBypassRls": int(os.environ["ROLE_COUNT"]),
            "forceRlsTables": int(os.environ["FORCE_RLS_COUNT"]),
            "deletedSyntheticAccountsAfterRestore": int(os.environ["TARGET_ACCOUNT_COUNT"]),
            "deletedSyntheticSessionDigestsAfterRestore": int(os.environ["TARGET_SESSION_COUNT"]),
            "deletedSyntheticSessionsResolvedAfterRestore": int(os.environ["RESOLVED_SESSION_COUNT"]),
            "expiredSyntheticSessionRowsAfterRestore": int(os.environ["TARGET_EXPIRED_COUNT"]),
            "revokedSyntheticSessionRowsAfterRestore": int(os.environ["TARGET_REVOKED_COUNT"]),
            "expiredSyntheticSessionsResolvedAfterRestore": int(os.environ["RESOLVED_EXPIRED_COUNT"]),
            "revokedSyntheticSessionsResolvedAfterRestore": int(os.environ["RESOLVED_REVOKED_COUNT"]),
        },
        "integrityResult": "PASS",
        "result": "PASS",
    },
    "limitations": [
        "same PostgreSQL cluster logical dump and restore",
        "not PITR or physical backup evidence",
        "not object-store restore evidence",
        "not approved RPO or RTO evidence",
        "synthetic deletion and expired/revoked session non-resurrection scope only",
    ],
}
Path(os.environ["RESULT_PATH"]).write_text(
    json.dumps(result, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
PY

printf 'Memory OS local logical restore PASS\n'
printf 'migrations: %s  SQL tests: %s  FORCE RLS tables: %s\n' \
  "${#MIGRATIONS[@]}" "${#SQL_TESTS[@]}" "$FORCE_RLS_COUNT"
printf 'expired/revoked session resolution after restore: %s/%s\n' \
  "$RESOLVED_EXPIRED_COUNT" "$RESOLVED_REVOKED_COUNT"
printf 'result: %s\n' "$RESULT_PATH"
