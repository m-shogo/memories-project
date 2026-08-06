#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CONTRACT="$ROOT/contracts/operations/postgresql-major-upgrade-contract.v1.json"
MIGRATION_CONTRACT="$ROOT/contracts/operations/migration-lifecycle-contract.v1.json"
MIGRATION_DIR="$ROOT/infra/postgresql/security"
RESULT_PATH="${MEMORY_OS_POSTGRESQL_MAJOR_UPGRADE_RESULTS_PATH:-$ROOT/docs/fixtures/memory-os-operability/postgresql-major-upgrade-results.sample.v1.json}"
SOURCE_SHA="${MEMORY_OS_COMMIT_SHA:-$(git rev-parse HEAD)}"
START_EPOCH="$(date +%s)"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SUFFIX="${GITHUB_RUN_ID:-$$}-${GITHUB_RUN_ATTEMPT:-1}"
SUFFIX="$(printf '%s' "$SUFFIX" | tr -cd 'a-zA-Z0-9-' | cut -c1-30)"
NETWORK="memory-os-pg-upgrade-$SUFFIX"
SOURCE_CONTAINER="memory-os-pg16-$SUFFIX"
TARGET_CONTAINER="memory-os-pg17-$SUFFIX"
SOURCE_DB="memory_os_upgrade_source"
TARGET_DB="memory_os_upgrade_target"
DUMP_PATH="/tmp/memory-os-upgrade-data.dump"
FINGERPRINT_SQL="$(mktemp "${TMPDIR:-/tmp}/memory-os-schema-authority.XXXXXX.sql")"

fail() {
  printf 'POSTGRESQL MAJOR UPGRADE FAILED: %s\n' "$*" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "docker is required"
command -v python >/dev/null 2>&1 || fail "python is required"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required"
[[ -f "$CONTRACT" ]] || fail "missing PostgreSQL upgrade contract"
[[ -f "$MIGRATION_CONTRACT" ]] || fail "missing migration lifecycle contract"
[[ -d "$MIGRATION_DIR" ]] || fail "missing migration directory"
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "source SHA must be a full lowercase commit SHA"

cleanup() {
  set +e
  docker rm -f "$SOURCE_CONTAINER" "$TARGET_CONTAINER" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -f "$FINGERPRINT_SQL"
}
trap cleanup EXIT

wait_postgres() {
  local container="$1"
  for _ in $(seq 1 90); do
    if docker exec "$container" pg_isready -U postgres -d postgres >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  docker logs "$container" >&2 || true
  fail "PostgreSQL container did not become ready"
}

container_psql() {
  local container="$1"
  local database="$2"
  docker exec -i -e PGPASSWORD=postgres "$container" \
    psql -X -U postgres -d "$database" --set=ON_ERROR_STOP=1 "$@"
}

query_scalar() {
  local container="$1"
  local database="$2"
  local sql="$3"
  docker exec -e PGPASSWORD=postgres "$container" \
    psql -X -U postgres -d "$database" --tuples-only --no-align \
    --set=ON_ERROR_STOP=1 --command "$sql"
}

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
  migration_path="$MIGRATION_DIR/$migration"
  [[ -f "$migration_path" ]] || fail "missing migration: $migration"
  test_path="$MIGRATION_DIR/test_${migration#*_}"
  [[ -f "$test_path" ]] || fail "missing SQL integration test for migration: $migration"
  SQL_TESTS+=("$test_path")
done
[[ "${#SQL_TESTS[@]}" -eq "${#MIGRATIONS[@]}" ]] || \
  fail "SQL integration test count does not match migration count"

cat >"$FINGERPRINT_SQL" <<'SQL'
WITH authority AS (
  SELECT
    'relation'::text AS kind,
    namespace.nspname || '.' || relation.relname AS identity,
    concat_ws(':', relation.relkind::text, relation.relrowsecurity::text,
              relation.relforcerowsecurity::text) AS detail
  FROM pg_class AS relation
  JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
  WHERE namespace.nspname = 'memory_os'
    AND relation.relkind IN ('r', 'p', 'v', 'm', 'S')

  UNION ALL

  SELECT
    'column',
    namespace.nspname || '.' || relation.relname || '.' || attribute.attname,
    concat_ws(':', attribute.attnum::text,
              pg_catalog.format_type(attribute.atttypid, attribute.atttypmod),
              attribute.attnotnull::text, attribute.attidentity::text,
              attribute.attgenerated::text,
              (default_value.adbin IS NOT NULL)::text)
  FROM pg_attribute AS attribute
  JOIN pg_class AS relation ON relation.oid = attribute.attrelid
  JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
  LEFT JOIN pg_attrdef AS default_value
    ON default_value.adrelid = attribute.attrelid
   AND default_value.adnum = attribute.attnum
  WHERE namespace.nspname = 'memory_os'
    AND relation.relkind IN ('r', 'p', 'v', 'm')
    AND attribute.attnum > 0
    AND NOT attribute.attisdropped

  UNION ALL

  SELECT
    'constraint',
    namespace.nspname || '.' || relation.relname || '.' || constraint_row.conname,
    concat_ws(':', constraint_row.contype::text,
              constraint_row.condeferrable::text,
              constraint_row.condeferred::text,
              constraint_row.convalidated::text,
              coalesce(constraint_row.conkey::text, ''),
              coalesce(constraint_row.confkey::text, ''),
              coalesce(referenced_namespace.nspname || '.' || referenced.relname, ''))
  FROM pg_constraint AS constraint_row
  JOIN pg_class AS relation ON relation.oid = constraint_row.conrelid
  JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
  LEFT JOIN pg_class AS referenced ON referenced.oid = constraint_row.confrelid
  LEFT JOIN pg_namespace AS referenced_namespace ON referenced_namespace.oid = referenced.relnamespace
  WHERE namespace.nspname = 'memory_os'

  UNION ALL

  SELECT
    'policy',
    schemaname || '.' || tablename || '.' || policyname,
    concat_ws(':', permissive, cmd, roles::text,
              coalesce(qual, ''), coalesce(with_check, ''))
  FROM pg_policies
  WHERE schemaname = 'memory_os'

  UNION ALL

  SELECT
    'function',
    namespace.nspname || '.' || procedure.proname || '(' ||
      pg_get_function_identity_arguments(procedure.oid) || ')',
    concat_ws(':', pg_get_function_result(procedure.oid),
              procedure.prosecdef::text, procedure.provolatile::text,
              procedure.proparallel::text)
  FROM pg_proc AS procedure
  JOIN pg_namespace AS namespace ON namespace.oid = procedure.pronamespace
  WHERE namespace.nspname = 'memory_os'
)
SELECT kind || '|' || identity || '|' || detail
FROM authority
ORDER BY kind, identity, detail;
SQL

printf 'POSTGRESQL UPGRADE STAGE: start-isolated-majors\n'
docker network create "$NETWORK" >/dev/null
docker run -d --name "$SOURCE_CONTAINER" --network "$NETWORK" \
  -e POSTGRES_PASSWORD=postgres postgres:16-alpine >/dev/null
docker run -d --name "$TARGET_CONTAINER" --network "$NETWORK" \
  -e POSTGRES_PASSWORD=postgres postgres:17-alpine >/dev/null
wait_postgres "$SOURCE_CONTAINER"
wait_postgres "$TARGET_CONTAINER"

SOURCE_MAJOR="$(query_scalar "$SOURCE_CONTAINER" postgres "SHOW server_version_num;" | cut -c1-2)"
TARGET_MAJOR="$(query_scalar "$TARGET_CONTAINER" postgres "SHOW server_version_num;" | cut -c1-2)"
[[ "$SOURCE_MAJOR" == "16" && "$TARGET_MAJOR" == "17" ]] || \
  fail "unexpected PostgreSQL majors: source=$SOURCE_MAJOR target=$TARGET_MAJOR"

container_psql "$SOURCE_CONTAINER" postgres --quiet <<SQL >/dev/null
CREATE DATABASE "$SOURCE_DB";
SQL
container_psql "$TARGET_CONTAINER" postgres --quiet <<SQL >/dev/null
CREATE DATABASE "$TARGET_DB";
SQL

printf 'POSTGRESQL UPGRADE STAGE: apply-current-migrations-to-both-majors\n'
for migration in "${MIGRATIONS[@]}"; do
  PGOPTIONS='-c client_min_messages=warning' \
    container_psql "$SOURCE_CONTAINER" "$SOURCE_DB" --file=- \
    <"$MIGRATION_DIR/$migration" >/dev/null
  PGOPTIONS='-c client_min_messages=warning' \
    container_psql "$TARGET_CONTAINER" "$TARGET_DB" --file=- \
    <"$MIGRATION_DIR/$migration" >/dev/null
done

printf 'POSTGRESQL UPGRADE STAGE: seed-active-and-deleted-authority\n'
container_psql "$SOURCE_CONTAINER" "$SOURCE_DB" --quiet <<'SQL' >/dev/null
INSERT INTO memory_os.account_control
  (account_id, account_epoch, state, created_at, updated_at)
VALUES
  ('acct_upgrade_active_0001', 1, 'active', now(), now()),
  ('acct_upgrade_deleted_0001', 1, 'active', now(), now());

INSERT INTO memory_os.account_session
  (id, token_digest, owner_account_id, account_epoch, authority, state, created_at, expires_at)
VALUES
  ('ses_upgrade_active_0001',
   'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
   'acct_upgrade_active_0001', 1, 'ios_device_session', 'active', now(), now() + interval '1 hour'),
  ('ses_upgrade_deleted_0001',
   'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
   'acct_upgrade_deleted_0001', 1, 'ios_device_session', 'active', now(), now() + interval '1 hour');

DELETE FROM memory_os.account_session WHERE id = 'ses_upgrade_deleted_0001';
DELETE FROM memory_os.account_control WHERE account_id = 'acct_upgrade_deleted_0001';
SQL

SOURCE_ACTIVE_ACCOUNT_COUNT="$(query_scalar "$SOURCE_CONTAINER" "$SOURCE_DB" \
  "SELECT count(*) FROM memory_os.account_control WHERE account_id = 'acct_upgrade_active_0001';")"
SOURCE_ACTIVE_SESSION_COUNT="$(query_scalar "$SOURCE_CONTAINER" "$SOURCE_DB" \
  "SELECT count(*) FROM memory_os.account_session WHERE token_digest = 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee';")"
SOURCE_DELETED_ACCOUNT_COUNT="$(query_scalar "$SOURCE_CONTAINER" "$SOURCE_DB" \
  "SELECT count(*) FROM memory_os.account_control WHERE account_id = 'acct_upgrade_deleted_0001';")"
SOURCE_DELETED_SESSION_COUNT="$(query_scalar "$SOURCE_CONTAINER" "$SOURCE_DB" \
  "SELECT count(*) FROM memory_os.account_session WHERE token_digest = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff';")"
[[ "$SOURCE_ACTIVE_ACCOUNT_COUNT" == "1" && "$SOURCE_ACTIVE_SESSION_COUNT" == "1" && \
   "$SOURCE_DELETED_ACCOUNT_COUNT" == "0" && "$SOURCE_DELETED_SESSION_COUNT" == "0" ]] || \
  fail "source synthetic authority state is invalid"

printf 'POSTGRESQL UPGRADE STAGE: compare-schema-authority\n'
SOURCE_FINGERPRINT="$(container_psql "$SOURCE_CONTAINER" "$SOURCE_DB" \
  --tuples-only --no-align --file=- <"$FINGERPRINT_SQL" | sha256sum | awk '{print $1}')"
TARGET_FINGERPRINT="$(container_psql "$TARGET_CONTAINER" "$TARGET_DB" \
  --tuples-only --no-align --file=- <"$FINGERPRINT_SQL" | sha256sum | awk '{print $1}')"
[[ "$SOURCE_FINGERPRINT" == "$TARGET_FINGERPRINT" ]] || \
  fail "schema authority fingerprints differ across PostgreSQL majors"

printf 'POSTGRESQL UPGRADE STAGE: dump-source-with-target-client\n'
docker exec -e PGPASSWORD=postgres "$TARGET_CONTAINER" \
  pg_dump --host "$SOURCE_CONTAINER" --username postgres --dbname "$SOURCE_DB" \
  --format=custom --compress=6 --data-only --no-owner --no-privileges \
  --file "$DUMP_PATH"
DUMP_BYTES="$(docker exec "$TARGET_CONTAINER" stat -c '%s' "$DUMP_PATH")"
[[ "$DUMP_BYTES" =~ ^[0-9]+$ && "$DUMP_BYTES" -gt 0 ]] || fail "upgrade dump is empty"

printf 'POSTGRESQL UPGRADE STAGE: restore-data-into-fresh-target\n'
docker exec -e PGPASSWORD=postgres "$TARGET_CONTAINER" \
  pg_restore --username postgres --dbname "$TARGET_DB" --exit-on-error \
  --data-only --no-owner --no-privileges "$DUMP_PATH" >/dev/null

ROLE_COUNT="$(query_scalar "$TARGET_CONTAINER" "$TARGET_DB" \
  "SELECT count(*) FROM pg_roles WHERE rolname IN ('memory_api_runtime','memory_worker_runtime','memory_deletion_runtime','memory_auth_runtime') AND rolbypassrls = false;")"
FORCE_RLS_COUNT="$(query_scalar "$TARGET_CONTAINER" "$TARGET_DB" \
  "SELECT count(*) FROM pg_class AS relation JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace WHERE namespace.nspname = 'memory_os' AND relation.relkind = 'r' AND relation.relforcerowsecurity;")"
ACTIVE_ACCOUNT_COUNT="$(query_scalar "$TARGET_CONTAINER" "$TARGET_DB" \
  "SELECT count(*) FROM memory_os.account_control WHERE account_id = 'acct_upgrade_active_0001';")"
ACTIVE_SESSION_COUNT="$(query_scalar "$TARGET_CONTAINER" "$TARGET_DB" \
  "SELECT count(*) FROM memory_os.account_session WHERE token_digest = 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee';")"
DELETED_ACCOUNT_COUNT="$(query_scalar "$TARGET_CONTAINER" "$TARGET_DB" \
  "SELECT count(*) FROM memory_os.account_control WHERE account_id = 'acct_upgrade_deleted_0001';")"
DELETED_SESSION_COUNT="$(query_scalar "$TARGET_CONTAINER" "$TARGET_DB" \
  "SELECT count(*) FROM memory_os.account_session WHERE token_digest = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff';")"
ACTIVE_RESOLVED_OUTPUT="$(container_psql "$TARGET_CONTAINER" "$TARGET_DB" --tuples-only --no-align --quiet <<'SQL'
SET ROLE memory_auth_runtime;
SELECT count(*) FROM memory_os.resolve_account_session(
  'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
);
RESET ROLE;
SQL
)"
DELETED_RESOLVED_OUTPUT="$(container_psql "$TARGET_CONTAINER" "$TARGET_DB" --tuples-only --no-align --quiet <<'SQL'
SET ROLE memory_auth_runtime;
SELECT count(*) FROM memory_os.resolve_account_session(
  'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'
);
RESET ROLE;
SQL
)"
ACTIVE_RESOLVED_COUNT="$(printf '%s\n' "$ACTIVE_RESOLVED_OUTPUT" | grep -E '^[0-9]+$' | tail -n 1)"
DELETED_RESOLVED_COUNT="$(printf '%s\n' "$DELETED_RESOLVED_OUTPUT" | grep -E '^[0-9]+$' | tail -n 1)"

[[ "$ROLE_COUNT" == "4" ]] || fail "runtime role verification failed: $ROLE_COUNT"
[[ "$FORCE_RLS_COUNT" =~ ^[0-9]+$ && "$FORCE_RLS_COUNT" -gt 0 ]] || \
  fail "FORCE RLS verification failed: $FORCE_RLS_COUNT"
[[ "$ACTIVE_ACCOUNT_COUNT" == "1" && "$ACTIVE_SESSION_COUNT" == "1" && \
   "$ACTIVE_RESOLVED_COUNT" == "1" ]] || fail "active authority did not survive upgrade"
[[ "$DELETED_ACCOUNT_COUNT" == "0" && "$DELETED_SESSION_COUNT" == "0" && \
   "$DELETED_RESOLVED_COUNT" == "0" ]] || fail "deleted authority resurrected after upgrade"

printf 'POSTGRESQL UPGRADE STAGE: run-canonical-sql-tests-on-target\n'
for test_file in "${SQL_TESTS[@]}"; do
  PGOPTIONS='-c client_min_messages=warning' \
    container_psql "$TARGET_CONTAINER" "$TARGET_DB" --file=- <"$test_file" >/dev/null
done

END_EPOCH="$(date +%s)"
DURATION_SECONDS="$((END_EPOCH - START_EPOCH))"
COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
mkdir -p "$(dirname "$RESULT_PATH")"

SOURCE_SHA="$SOURCE_SHA" STARTED_AT="$STARTED_AT" COMPLETED_AT="$COMPLETED_AT" \
DURATION_SECONDS="$DURATION_SECONDS" SOURCE_MAJOR="$SOURCE_MAJOR" TARGET_MAJOR="$TARGET_MAJOR" \
MIGRATION_COUNT="${#MIGRATIONS[@]}" SQL_TEST_COUNT="${#SQL_TESTS[@]}" \
DUMP_BYTES="$DUMP_BYTES" SCHEMA_FINGERPRINT="$SOURCE_FINGERPRINT" \
ROLE_COUNT="$ROLE_COUNT" FORCE_RLS_COUNT="$FORCE_RLS_COUNT" \
ACTIVE_ACCOUNT_COUNT="$ACTIVE_ACCOUNT_COUNT" ACTIVE_SESSION_COUNT="$ACTIVE_SESSION_COUNT" \
ACTIVE_RESOLVED_COUNT="$ACTIVE_RESOLVED_COUNT" DELETED_ACCOUNT_COUNT="$DELETED_ACCOUNT_COUNT" \
DELETED_SESSION_COUNT="$DELETED_SESSION_COUNT" DELETED_RESOLVED_COUNT="$DELETED_RESOLVED_COUNT" \
RESULT_PATH="$RESULT_PATH" python - <<'PY'
import datetime as dt
import json
import os
from pathlib import Path

result = {
    "schemaVersion": "memory-os-postgresql-major-upgrade-results.v1",
    "commitSha": os.environ["SOURCE_SHA"],
    "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    "environment": {
        "mode": "EPHEMERAL_DOCKER_POSTGRESQL_16_TO_17_LOGICAL_FORWARD_RESTORE",
        "productionEvidence": False,
        "productionTraffic": False,
        "productionCredentials": False,
        "containsSecrets": False,
        "syntheticDataOnly": True,
    },
    "scenario": {
        "scenarioId": "postgresql-16-to-17-logical-forward-upgrade",
        "startedAt": os.environ["STARTED_AT"],
        "completedAt": os.environ["COMPLETED_AT"],
        "durationSeconds": int(os.environ["DURATION_SECONDS"]),
        "sourceMajor": int(os.environ["SOURCE_MAJOR"]),
        "targetMajor": int(os.environ["TARGET_MAJOR"]),
        "migrationFilesAppliedPerDatabase": int(os.environ["MIGRATION_COUNT"]),
        "sqlIntegrationTestsExecutedOnTarget": int(os.environ["SQL_TEST_COUNT"]),
        "dumpBytes": int(os.environ["DUMP_BYTES"]),
        "schemaAuthorityFingerprintSha256": os.environ["SCHEMA_FINGERPRINT"],
        "assertions": {
            "sourceMajor": int(os.environ["SOURCE_MAJOR"]),
            "targetMajor": int(os.environ["TARGET_MAJOR"]),
            "allCurrentMigrationsAppliedToSource": True,
            "allCurrentMigrationsAppliedToTarget": True,
            "dataOnlyDumpCreated": True,
            "dataOnlyRestoreCompleted": True,
            "schemaAuthorityFingerprintEqual": True,
            "runtimeRolesWithoutBypassRls": int(os.environ["ROLE_COUNT"]),
            "forceRlsTables": int(os.environ["FORCE_RLS_COUNT"]),
            "activeSyntheticAccountsAfterUpgrade": int(os.environ["ACTIVE_ACCOUNT_COUNT"]),
            "activeSyntheticSessionsAfterUpgrade": int(os.environ["ACTIVE_SESSION_COUNT"]),
            "activeSyntheticSessionsResolvedAfterUpgrade": int(os.environ["ACTIVE_RESOLVED_COUNT"]),
            "deletedSyntheticAccountsAfterUpgrade": int(os.environ["DELETED_ACCOUNT_COUNT"]),
            "deletedSyntheticSessionDigestsAfterUpgrade": int(os.environ["DELETED_SESSION_COUNT"]),
            "deletedSyntheticSessionsResolvedAfterUpgrade": int(os.environ["DELETED_RESOLVED_COUNT"]),
            "allCanonicalSqlTestsPassedOnTarget": True,
            "integrityResult": "PASS",
            "result": "PASS",
        },
        "integrityResult": "PASS",
        "result": "PASS",
    },
    "limitations": [
        "ephemeral single-node PostgreSQL 16 and PostgreSQL 17 Docker containers",
        "logical data-only dump and restore rather than in-place pg_upgrade",
        "no extensions, replication slots, WAL, failover or connection-pool migration",
        "synthetic authority and deletion state only",
        "no production traffic, credentials or operator promotion",
        "no downgrade or destructive contract migration",
        "not production database upgrade evidence",
    ],
}
serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
for forbidden in (
    "postgres://", "postgresql://", "password=", "acct_upgrade_",
    "ses_upgrade_", "eeeeeeee", "ffffffff", "memory-os-pg16-", "memory-os-pg17-",
):
    if forbidden in serialized.lower():
        raise SystemExit(f"forbidden evidence content: {forbidden}")
Path(os.environ["RESULT_PATH"]).write_text(serialized, encoding="utf-8")
PY

printf 'Memory OS PostgreSQL 16 to 17 logical upgrade PASS\n'
printf 'migrations per database: %s  target SQL tests: %s  FORCE RLS tables: %s\n' \
  "${#MIGRATIONS[@]}" "${#SQL_TESTS[@]}" "$FORCE_RLS_COUNT"
printf 'result: %s\n' "$RESULT_PATH"
