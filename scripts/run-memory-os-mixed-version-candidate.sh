#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACT="$ROOT/contracts/operations/mixed-version-candidate-contract.v1.json"
CURRENT_MIGRATION_CONTRACT="$ROOT/contracts/operations/migration-lifecycle-contract.v1.json"
CURRENT_MIGRATION_DIR="$ROOT/infra/postgresql/security"
RESULT_PATH="${MEMORY_OS_MIXED_VERSION_RESULTS_PATH:-$ROOT/docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json}"
CURRENT_SHA="${MEMORY_OS_COMMIT_SHA:-}"
BASELINE_DB="${MEMORY_OS_MIXED_BASELINE_DB:-memory_os_mixed_baseline}"
CURRENT_DB="${MEMORY_OS_MIXED_CURRENT_DB:-memory_os_mixed_current}"
START_EPOCH="$(date +%s)"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

fail() {
  printf 'MIXED-VERSION CANDIDATE FAILED: %s\n' "$*" >&2
  exit 1
}

stage() {
  printf 'MIXED-VERSION STAGE: %s\n' "$1" >&2
}

for command in git psql pg_dump python sha256sum; do
  command -v "$command" >/dev/null 2>&1 || fail "$command is required"
done
[[ -f "$CONTRACT" ]] || fail "missing mixed-version contract"
[[ -f "$CURRENT_MIGRATION_CONTRACT" ]] || fail "missing current migration contract"
[[ -d "$CURRENT_MIGRATION_DIR" ]] || fail "missing current migration directory"
[[ "${MEMORY_OS_ALLOW_EPHEMERAL_DATABASE_DROP:-}" == "1" ]] || \
  fail "MEMORY_OS_ALLOW_EPHEMERAL_DATABASE_DROP=1 is required"
[[ "$CURRENT_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "MEMORY_OS_COMMIT_SHA must be a full SHA"

PGHOST="${PGHOST:-127.0.0.1}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
export PGHOST PGPORT PGUSER
case "$PGHOST" in
  127.0.0.1|localhost|::1) ;;
  *) fail "runner is restricted to a local PostgreSQL host" ;;
esac
for database in "$BASELINE_DB" "$CURRENT_DB"; do
  [[ "$database" =~ ^[a-z][a-z0-9_]{2,62}$ ]] || fail "invalid database name"
  [[ "$database" != "postgres" ]] || fail "postgres database is protected"
done
[[ "$BASELINE_DB" != "$CURRENT_DB" ]] || fail "baseline and current databases must differ"

BASELINE_SHA="$(python - "$CONTRACT" <<'PY'
import json
import sys
from pathlib import Path
value = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
print(value['candidateBaseline']['commitSha'])
PY
)"
[[ "$BASELINE_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "contract baseline SHA is invalid"
git -C "$ROOT" cat-file -e "$CURRENT_SHA^{commit}" || fail "current SHA is not available"
git -C "$ROOT" cat-file -e "$BASELINE_SHA^{commit}" || fail "baseline SHA is not available"
git -C "$ROOT" merge-base --is-ancestor "$BASELINE_SHA" "$CURRENT_SHA" || \
  fail "candidate baseline is not an ancestor of current source"
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$CURRENT_SHA" ]] || \
  fail "working tree HEAD does not equal MEMORY_OS_COMMIT_SHA"
[[ -z "$(git -C "$ROOT" status --porcelain)" ]] || fail "current working tree must be clean"

WORKTREE="$(mktemp -d "${TMPDIR:-/tmp}/memory-os-mixed-version.XXXXXX")"
BASELINE_WORKTREE="$WORKTREE/baseline"
CURRENT_SCHEMA_BEFORE="$WORKTREE/current-schema-before.sql"
CURRENT_SCHEMA_AFTER="$WORKTREE/current-schema-after.sql"

cleanup() {
  set +e
  git -C "$ROOT" worktree remove --force "$BASELINE_WORKTREE" >/dev/null 2>&1 || true
  rm -rf "$WORKTREE"
  if [[ "${MEMORY_OS_KEEP_MIXED_VERSION_DATABASES:-0}" != "1" ]]; then
    psql --dbname postgres --set=ON_ERROR_STOP=1 --quiet <<SQL >/dev/null 2>&1 || true
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname IN ('$BASELINE_DB', '$CURRENT_DB') AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$BASELINE_DB";
DROP DATABASE IF EXISTS "$CURRENT_DB";
SQL
  fi
}
trap cleanup EXIT

stage "checkout-pinned-baseline"
git -C "$ROOT" worktree add --detach "$BASELINE_WORKTREE" "$BASELINE_SHA" >/dev/null
[[ -z "$(git -C "$BASELINE_WORKTREE" status --porcelain)" ]] || \
  fail "baseline worktree is not clean"
[[ "$(git -C "$BASELINE_WORKTREE" rev-parse HEAD)" == "$BASELINE_SHA" ]] || \
  fail "baseline worktree SHA drift"

mapfile -t CURRENT_MIGRATIONS < <(
  python - "$CURRENT_MIGRATION_CONTRACT" <<'PY'
import json
import sys
from pathlib import Path
value = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
for item in value['migrationSequence']:
    print(item)
PY
)
[[ "${#CURRENT_MIGRATIONS[@]}" -gt 0 ]] || fail "current migration sequence is empty"

CURRENT_SQL_TESTS=()
for migration in "${CURRENT_MIGRATIONS[@]}"; do
  migration_path="$CURRENT_MIGRATION_DIR/$migration"
  test_path="$CURRENT_MIGRATION_DIR/test_${migration#*_}"
  [[ -f "$migration_path" ]] || fail "missing current migration: $migration"
  [[ -f "$test_path" ]] || fail "missing current SQL test: ${test_path##*/}"
  CURRENT_SQL_TESTS+=("$test_path")
done

BASELINE_MIGRATION_CONTRACT="$BASELINE_WORKTREE/contracts/operations/migration-lifecycle-contract.v1.json"
BASELINE_SQL_ORDER_SOURCE=""
BASELINE_SQL_TESTS=()
if [[ -f "$BASELINE_MIGRATION_CONTRACT" ]]; then
  mapfile -t BASELINE_MIGRATIONS < <(
    python - "$BASELINE_MIGRATION_CONTRACT" <<'PY'
import json
import sys
from pathlib import Path
value = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
for item in value['migrationSequence']:
    print(item)
PY
  )
  [[ "${#BASELINE_MIGRATIONS[@]}" -gt 0 ]] || fail "baseline migration sequence is empty"
  for migration in "${BASELINE_MIGRATIONS[@]}"; do
    test_path="$BASELINE_WORKTREE/infra/postgresql/security/test_${migration#*_}"
    [[ -f "$test_path" ]] || fail "missing baseline SQL test: ${test_path##*/}"
    BASELINE_SQL_TESTS+=("$test_path")
  done
  BASELINE_SQL_ORDER_SOURCE="BASELINE_MIGRATION_REGISTRY"
else
  BASELINE_SECURITY_WORKFLOW="$BASELINE_WORKTREE/.github/workflows/security-contracts.yml"
  [[ -f "$BASELINE_SECURITY_WORKFLOW" ]] || \
    fail "baseline has neither migration registry nor Security Contracts workflow"
  mapfile -t BASELINE_TEST_NAMES < <(
    python - "$BASELINE_SECURITY_WORKFLOW" <<'PY'
import re
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding='utf-8')
pattern = re.compile(r"--file\s+infra/postgresql/security/(test_memory_os_[A-Za-z0-9_]+\.sql)")
seen = set()
for name in pattern.findall(text):
    if name not in seen:
        seen.add(name)
        print(name)
PY
  )
  [[ "${#BASELINE_TEST_NAMES[@]}" -gt 0 ]] || \
    fail "baseline Security Contracts workflow contains no ordered SQL tests"
  for name in "${BASELINE_TEST_NAMES[@]}"; do
    test_path="$BASELINE_WORKTREE/infra/postgresql/security/$name"
    [[ -f "$test_path" ]] || fail "baseline workflow references missing SQL test: $name"
    BASELINE_SQL_TESTS+=("$test_path")
  done
  BASELINE_SQL_ORDER_SOURCE="BASELINE_SECURITY_CONTRACTS_WORKFLOW"
fi

GO_PACKAGE_CANDIDATES=(
  ./internal/authstore
  ./internal/httpserver
  ./internal/previewcommit
  ./internal/importflow
)
GO_PACKAGES=()
for package in "${GO_PACKAGE_CANDIDATES[@]}"; do
  relative="${package#./}"
  if [[ -d "$BASELINE_WORKTREE/services/import-api/$relative" && -d "$ROOT/services/import-api/$relative" ]]; then
    GO_PACKAGES+=("$package")
  fi
done
[[ "${#GO_PACKAGES[@]}" -ge 3 ]] || \
  fail "fewer than three reviewed Go package surfaces exist in both source trees"
for required in ./internal/httpserver ./internal/previewcommit ./internal/importflow; do
  found=0
  for package in "${GO_PACKAGES[@]}"; do
    [[ "$package" == "$required" ]] && found=1
  done
  [[ "$found" == "1" ]] || fail "required common Go package is missing: $required"
done

stage "create-ephemeral-databases"
psql --dbname postgres --set=ON_ERROR_STOP=1 --quiet <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname IN ('$BASELINE_DB', '$CURRENT_DB') AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$BASELINE_DB";
DROP DATABASE IF EXISTS "$CURRENT_DB";
CREATE DATABASE "$BASELINE_DB";
CREATE DATABASE "$CURRENT_DB";
SQL

stage "apply-current-migrations-to-both-databases"
for database in "$BASELINE_DB" "$CURRENT_DB"; do
  for migration in "${CURRENT_MIGRATIONS[@]}"; do
    psql --dbname "$database" --set=ON_ERROR_STOP=1 \
      --file "$CURRENT_MIGRATION_DIR/$migration" >/dev/null
  done
done

stage "capture-pre-baseline-schema-fingerprint"
pg_dump --dbname "$BASELINE_DB" --schema-only --no-owner --no-privileges \
  --schema memory_os > "$CURRENT_SCHEMA_BEFORE"
SCHEMA_BEFORE_SHA="$(sha256sum "$CURRENT_SCHEMA_BEFORE" | awk '{print $1}')"

stage "run-baseline-sql-tests"
for test_file in "${BASELINE_SQL_TESTS[@]}"; do
  psql --dbname "$BASELINE_DB" --set=ON_ERROR_STOP=1 --file "$test_file" >/dev/null
done

BASELINE_DATABASE_URL="postgres://$PGUSER:${PGPASSWORD:-}@${PGHOST}:$PGPORT/$BASELINE_DB?sslmode=disable"
CURRENT_DATABASE_URL="postgres://$PGUSER:${PGPASSWORD:-}@${PGHOST}:$PGPORT/$CURRENT_DB?sslmode=disable"
stage "run-baseline-go-tests"
(
  cd "$BASELINE_WORKTREE/services/import-api"
  MEMORY_OS_TEST_DATABASE_URL="$BASELINE_DATABASE_URL" \
  MEMORY_OS_TEST_S3_ENDPOINT="${MEMORY_OS_TEST_S3_ENDPOINT:-http://127.0.0.1:9000}" \
  go test "${GO_PACKAGES[@]}" -count=1
)

stage "verify-baseline-did-not-change-schema"
pg_dump --dbname "$BASELINE_DB" --schema-only --no-owner --no-privileges \
  --schema memory_os > "$CURRENT_SCHEMA_AFTER"
SCHEMA_AFTER_SHA="$(sha256sum "$CURRENT_SCHEMA_AFTER" | awk '{print $1}')"
[[ "$SCHEMA_BEFORE_SHA" == "$SCHEMA_AFTER_SHA" ]] || \
  fail "baseline execution changed the current memory_os schema fingerprint"

stage "run-current-sql-tests"
for test_file in "${CURRENT_SQL_TESTS[@]}"; do
  psql --dbname "$CURRENT_DB" --set=ON_ERROR_STOP=1 --file "$test_file" >/dev/null
done
stage "run-current-go-tests"
(
  cd "$ROOT/services/import-api"
  MEMORY_OS_TEST_DATABASE_URL="$CURRENT_DATABASE_URL" \
  MEMORY_OS_TEST_S3_ENDPOINT="${MEMORY_OS_TEST_S3_ENDPOINT:-http://127.0.0.1:9000}" \
  go test "${GO_PACKAGES[@]}" -count=1
)

END_EPOCH="$(date +%s)"
DURATION_SECONDS="$((END_EPOCH - START_EPOCH))"
COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DATABASE_IDENTITY_DIGEST="$(printf '%s' "$PGHOST:$PGPORT:$BASELINE_DB:$CURRENT_DB" | sha256sum | awk '{print $1}')"
mkdir -p "$(dirname "$RESULT_PATH")"

CURRENT_SHA="$CURRENT_SHA" \
BASELINE_SHA="$BASELINE_SHA" \
STARTED_AT="$STARTED_AT" \
COMPLETED_AT="$COMPLETED_AT" \
DURATION_SECONDS="$DURATION_SECONDS" \
DATABASE_IDENTITY_DIGEST="$DATABASE_IDENTITY_DIGEST" \
CURRENT_MIGRATION_COUNT="${#CURRENT_MIGRATIONS[@]}" \
BASELINE_SQL_TEST_COUNT="${#BASELINE_SQL_TESTS[@]}" \
CURRENT_SQL_TEST_COUNT="${#CURRENT_SQL_TESTS[@]}" \
GO_PACKAGE_COUNT="${#GO_PACKAGES[@]}" \
BASELINE_SQL_ORDER_SOURCE="$BASELINE_SQL_ORDER_SOURCE" \
SCHEMA_SHA="$SCHEMA_AFTER_SHA" \
RESULT_PATH="$RESULT_PATH" \
python - <<'PY'
import datetime as dt
import json
import os
from pathlib import Path

result = {
    'schemaVersion': 'memory-os-mixed-version-candidate-results.v1',
    'currentCommitSha': os.environ['CURRENT_SHA'],
    'candidateBaselineCommitSha': os.environ['BASELINE_SHA'],
    'generatedAt': dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z'),
    'environment': {
        'mode': 'EPHEMERAL_POSTGRESQL_16_MINIO_TWO_DATABASE_CANDIDATE_BASELINE',
        'productionEvidence': False,
        'releaseCompatibilityEvidence': False,
        'candidateBaselineOnly': True,
        'containsSecrets': False,
        'syntheticDataOnly': True,
        'databaseIdentityDigest': os.environ['DATABASE_IDENTITY_DIGEST'],
    },
    'scenario': {
        'scenarioId': 'historical-candidate-on-current-expanded-schema',
        'startedAt': os.environ['STARTED_AT'],
        'completedAt': os.environ['COMPLETED_AT'],
        'durationSeconds': int(os.environ['DURATION_SECONDS']),
        'currentMigrationsAppliedPerDatabase': int(os.environ['CURRENT_MIGRATION_COUNT']),
        'candidateBaselineSqlTestsExecuted': int(os.environ['BASELINE_SQL_TEST_COUNT']),
        'currentSqlTestsExecuted': int(os.environ['CURRENT_SQL_TEST_COUNT']),
        'candidateBaselineGoPackagesExecuted': int(os.environ['GO_PACKAGE_COUNT']),
        'currentGoPackagesExecuted': int(os.environ['GO_PACKAGE_COUNT']),
        'baselineSqlOrderSource': os.environ['BASELINE_SQL_ORDER_SOURCE'],
        'memoryOsSchemaFingerprintSha256': os.environ['SCHEMA_SHA'],
        'assertions': {
            'baselineIsAncestorOfCurrent': True,
            'currentExpandedSchemaAppliedToBothDatabases': True,
            'candidateBaselineSqlTestsPassed': True,
            'candidateBaselineGoTestsPassed': True,
            'candidateExecutionPreservedSchemaFingerprint': True,
            'currentSqlTestsPassed': True,
            'currentGoTestsPassed': True,
        },
        'result': 'PASS',
        'integrityResult': 'PASS',
    },
    'limitations': [
        'candidate baseline is not an approved release',
        'single PostgreSQL 16 major version',
        'separate databases rather than simultaneous old/current traffic',
        'local MinIO rather than production object storage',
        'no rolling deployment order or connection-drain failure injection',
        'no downgrade or destructive contract migration',
        'not production mixed-version evidence',
    ],
}
Path(os.environ['RESULT_PATH']).write_text(
    json.dumps(result, indent=2, ensure_ascii=False) + '\n',
    encoding='utf-8',
)
PY

printf 'Memory OS mixed-version candidate PASS\n'
printf 'baseline SQL tests: %s  current SQL tests: %s  Go packages per side: %s\n' \
  "${#BASELINE_SQL_TESTS[@]}" "${#CURRENT_SQL_TESTS[@]}" "${#GO_PACKAGES[@]}"
printf 'result: %s\n' "$RESULT_PATH"
