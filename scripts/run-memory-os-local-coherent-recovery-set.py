#!/usr/bin/env python3
"""Run a local-only coherent PostgreSQL + exact object-version recovery-set drill."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError as exc:  # pragma: no cover - workflow installs boto3
    print("LOCAL COHERENT RECOVERY SET FAILED: boto3 is required", file=sys.stderr)
    raise SystemExit(1) from exc

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_CONTRACT = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
MIGRATION_DIR = ROOT / "infra/postgresql/security"
RESULT_PATH = Path(os.environ.get(
    "MEMORY_OS_LOCAL_COHERENT_RECOVERY_RESULTS_PATH",
    ROOT / "docs/fixtures/memory-os-operability/local-coherent-recovery-set-results.sample.v1.json",
))
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class DrillFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DrillFailure(message)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run(command: list[str], *, capture: bool = False, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, f"command failed: {command[0]}")
    return completed.stdout.strip() if capture else ""


def psql(db: str, sql: str, env: dict[str, str], *, capture: bool = False) -> str:
    command = ["psql", "--dbname", db, "--set", "ON_ERROR_STOP=1", "--quiet"]
    if capture:
        command.extend(["--tuples-only", "--no-align"])
    command.extend(["--command", sql])
    return run(command, capture=capture, env=env)


def list_all_versions(client: Any, bucket: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    versions: list[dict[str, str]] = []
    markers: list[dict[str, str]] = []
    paginator = client.get_paginator("list_object_versions")
    for page in paginator.paginate(Bucket=bucket):
        versions.extend({"Key": item["Key"], "VersionId": item["VersionId"]} for item in page.get("Versions", []))
        markers.extend({"Key": item["Key"], "VersionId": item["VersionId"]} for item in page.get("DeleteMarkers", []))
    return versions, markers


def purge_bucket(client: Any, bucket: str) -> None:
    versions, markers = list_all_versions(client, bucket)
    objects = versions + markers
    for offset in range(0, len(objects), 1000):
        response = client.delete_objects(Bucket=bucket, Delete={"Objects": objects[offset:offset + 1000], "Quiet": True})
        require(not response.get("Errors"), "object purge returned errors")
    versions, markers = list_all_versions(client, bucket)
    require(not versions and not markers, "object versions remain after purge")


def main() -> int:
    source_sha = os.environ.get("MEMORY_OS_COMMIT_SHA", "")
    require(SHA40.fullmatch(source_sha) is not None, "MEMORY_OS_COMMIT_SHA must be a full SHA")
    require(os.environ.get("MEMORY_OS_ALLOW_EPHEMERAL_DATABASE_DROP") == "1", "ephemeral database drop permission required")
    require(os.environ.get("MEMORY_OS_ALLOW_EPHEMERAL_OBJECT_DELETE") == "1", "ephemeral object delete permission required")

    pg_host = os.environ.get("PGHOST", "127.0.0.1")
    pg_port = os.environ.get("PGPORT", "5432")
    pg_user = os.environ.get("PGUSER", "postgres")
    require(pg_host in {"127.0.0.1", "localhost", "::1"}, "PostgreSQL host must be local")
    pg_env = os.environ.copy()
    pg_env.update({"PGHOST": pg_host, "PGPORT": pg_port, "PGUSER": pg_user})

    endpoint = os.environ.get("MEMORY_OS_TEST_S3_ENDPOINT", "")
    parsed = urlparse(endpoint)
    require(parsed.scheme in {"http", "https"} and parsed.hostname in {"127.0.0.1", "localhost", "::1"}, "object endpoint must be local")
    access_key = os.environ.get("MEMORY_OS_TEST_S3_ACCESS_KEY", "")
    secret_key = os.environ.get("MEMORY_OS_TEST_S3_SECRET_KEY", "")
    require(access_key and secret_key, "local object credentials required")

    contract = json.loads(MIGRATION_CONTRACT.read_text(encoding="utf-8"))
    migrations = contract.get("migrationSequence")
    require(isinstance(migrations, list) and migrations, "canonical migration sequence missing")
    for migration in migrations:
        require((MIGRATION_DIR / migration).is_file(), f"migration missing: {migration}")

    recovery_digest = sha256_text(f"{source_sha}:{uuid.uuid4().hex}")
    marker_account = f"acct_recovery_{recovery_digest}"
    suffix = recovery_digest[:16]
    source_db = f"memory_os_coherent_source_{suffix[:8]}"
    target_db = f"memory_os_coherent_target_{suffix[:8]}"
    source_bucket = f"memory-os-coherent-source-{suffix}"
    backup_bucket = f"memory-os-coherent-backup-{suffix}"
    restore_bucket = f"memory-os-coherent-restore-{suffix}"
    object_key = "synthetic/coherent-recovery-set.json"
    dump_file = Path(tempfile.mkstemp(prefix="memory-os-coherent-", suffix=".dump")[1])
    started_at = dt.datetime.now(dt.timezone.utc)
    started_monotonic = time.monotonic()

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    buckets = (source_bucket, backup_bucket, restore_bucket)

    try:
        psql("postgres", f'DROP DATABASE IF EXISTS "{source_db}";', pg_env)
        psql("postgres", f'DROP DATABASE IF EXISTS "{target_db}";', pg_env)
        psql("postgres", f'CREATE DATABASE "{source_db}";', pg_env)
        psql("postgres", f'CREATE DATABASE "{target_db}";', pg_env)
        for migration in migrations:
            run(["psql", "--dbname", source_db, "--set", "ON_ERROR_STOP=1", "--file", str(MIGRATION_DIR / migration)], env=pg_env)

        psql(
            source_db,
            "INSERT INTO memory_os.account_control (account_id, account_epoch, state, created_at, updated_at) "
            f"VALUES ('{marker_account}', 1, 'active', now(), now());",
            pg_env,
        )
        source_marker_count = int(psql(source_db, f"SELECT count(*) FROM memory_os.account_control WHERE account_id = '{marker_account}';", pg_env, capture=True))
        require(source_marker_count == 1, "database recovery-set marker setup failed")

        for bucket in buckets:
            client.create_bucket(Bucket=bucket)
            client.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
            require(client.get_bucket_versioning(Bucket=bucket).get("Status") == "Enabled", "bucket versioning not enabled")

        payload = json.dumps({"fixture": "coherent-recovery-set", "revision": 1}, separators=(",", ":")).encode("utf-8")
        source_response = client.put_object(
            Bucket=source_bucket,
            Key=object_key,
            Body=payload,
            Metadata={"recovery-set-sha256": recovery_digest, "fixture-class": "synthetic-operational"},
        )
        source_version = source_response.get("VersionId")
        require(isinstance(source_version, str) and source_version, "source object VersionId missing")
        source_obj = client.get_object(Bucket=source_bucket, Key=object_key, VersionId=source_version)
        source_body = source_obj["Body"].read()
        object_checksum = sha256_bytes(source_body)
        require(source_obj.get("Metadata", {}).get("recovery-set-sha256") == recovery_digest, "source object recovery-set binding missing")

        backup_response = client.put_object(
            Bucket=backup_bucket,
            Key=object_key,
            Body=source_body,
            Metadata={
                "recovery-set-sha256": recovery_digest,
                "source-version-sha256": sha256_text(source_version),
                "checksum-sha256": object_checksum,
            },
        )
        backup_version = backup_response.get("VersionId")
        require(isinstance(backup_version, str) and backup_version, "backup object VersionId missing")

        run(["pg_dump", "--format=custom", "--compress=6", "--no-comments", "--file", str(dump_file), source_db], env=pg_env)
        require(dump_file.stat().st_size > 0, "database dump is empty")

        # Destroy source-side evidence before recovery.
        psql("postgres", f'DROP DATABASE "{source_db}";', pg_env)
        purge_bucket(client, source_bucket)

        run(["pg_restore", "--exit-on-error", "--dbname", target_db, str(dump_file)], env=pg_env)
        restored_marker = psql(
            target_db,
            "SELECT account_id FROM memory_os.account_control WHERE account_id LIKE 'acct_recovery_%' ORDER BY account_id LIMIT 1;",
            pg_env,
            capture=True,
        )
        require(restored_marker.startswith("acct_recovery_"), "restored database recovery-set marker missing")
        db_recovery_digest = restored_marker.removeprefix("acct_recovery_")
        require(db_recovery_digest == recovery_digest, "restored database recovery-set digest mismatch")

        backup_obj = client.get_object(Bucket=backup_bucket, Key=object_key, VersionId=backup_version)
        backup_body = backup_obj["Body"].read()
        require(sha256_bytes(backup_body) == object_checksum, "backup object checksum mismatch")
        backup_metadata = backup_obj.get("Metadata", {})
        require(backup_metadata.get("recovery-set-sha256") == recovery_digest, "backup recovery-set binding mismatch")
        restore_response = client.put_object(
            Bucket=restore_bucket,
            Key=object_key,
            Body=backup_body,
            Metadata=backup_metadata,
        )
        restore_version = restore_response.get("VersionId")
        require(isinstance(restore_version, str) and restore_version, "restore object VersionId missing")
        restored_obj = client.get_object(Bucket=restore_bucket, Key=object_key, VersionId=restore_version)
        restored_body = restored_obj["Body"].read()
        restored_metadata = restored_obj.get("Metadata", {})
        object_recovery_digest = restored_metadata.get("recovery-set-sha256")
        require(object_recovery_digest == recovery_digest, "restored object recovery-set digest mismatch")
        require(sha256_bytes(restored_body) == object_checksum, "restored object checksum mismatch")

        require(db_recovery_digest == object_recovery_digest, "database/object coherent recovery-set comparison failed")
        deliberately_skewed = ("0" if recovery_digest[0] != "0" else "1") + recovery_digest[1:]
        deliberate_skew_rejected = db_recovery_digest != deliberately_skewed
        require(deliberate_skew_rejected, "deliberate one-sided recovery-set skew was accepted")

        completed_at = dt.datetime.now(dt.timezone.utc)
        result = {
            "schemaVersion": "memory-os-local-coherent-recovery-set-results.v1",
            "commitSha": source_sha,
            "generatedAt": completed_at.isoformat().replace("+00:00", "Z"),
            "environment": {
                "dependencyMode": "EPHEMERAL_POSTGRESQL_16_PLUS_LOCAL_MINIO_COHERENT_RECOVERY_SET",
                "databaseEndpointDigest": sha256_text(f"{pg_host}:{pg_port}"),
                "objectEndpointDigest": sha256_text(f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 80}"),
                "productionTraffic": False,
                "productionCredentials": False,
                "productionEvidence": False,
                "containsSecrets": False,
            },
            "scenario": {
                "scenarioId": "postgres-object-shared-recovery-set-local",
                "startedAt": started_at.isoformat().replace("+00:00", "Z"),
                "completedAt": completed_at.isoformat().replace("+00:00", "Z"),
                "durationSeconds": max(0, int(time.monotonic() - started_monotonic)),
                "migrationFilesApplied": len(migrations),
                "databaseDumpBytes": dump_file.stat().st_size,
                "recoverySetDigest": recovery_digest,
                "databaseRecoverySetDigest": db_recovery_digest,
                "objectRecoverySetDigest": object_recovery_digest,
                "objectChecksumSha256": object_checksum,
                "sourceObjectVersionDigest": sha256_text(source_version),
                "backupObjectVersionDigest": sha256_text(backup_version),
                "restoreObjectVersionDigest": sha256_text(restore_version),
                "assertions": {
                    "sourceDatabaseDestroyedBeforeRestore": True,
                    "sourceObjectVersionsDestroyedBeforeRestore": True,
                    "databaseRecoverySetBindingMatched": True,
                    "objectRecoverySetBindingMatched": True,
                    "databaseObjectRecoverySetMatched": True,
                    "exactBackupObjectChecksumMatched": True,
                    "deliberateOneSidedSkewRejected": deliberate_skew_rejected,
                },
                "integrityResult": "PASS",
                "result": "PASS",
            },
            "limitations": [
                "same local PostgreSQL instance and local MinIO process",
                "logical dump rather than PostgreSQL WAL/PITR",
                "shared digest proves recovery-set binding but does not measure temporal recovery-point skew",
                "not independent provider retention TLS credential separation or durability evidence",
                "not production or production-equivalent recovery evidence",
            ],
        }
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Memory OS local coherent recovery-set PASS")
        print(f"migrations: {len(migrations)}  database/object binding: PASS  deliberate skew rejected: true")
        print(f"result: {RESULT_PATH}")
        return 0
    finally:
        try:
            dump_file.unlink()
        except FileNotFoundError:
            pass
        if os.environ.get("MEMORY_OS_KEEP_COHERENT_RECOVERY_FIXTURE", "0") != "1":
            for db in (source_db, target_db):
                try:
                    psql("postgres", f'DROP DATABASE IF EXISTS "{db}";', pg_env)
                except Exception:
                    pass
            for bucket in reversed(buckets):
                try:
                    purge_bucket(client, bucket)
                    client.delete_bucket(Bucket=bucket)
                except Exception:
                    pass


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DrillFailure as exc:
        print(f"LOCAL COHERENT RECOVERY SET FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "ClientError") if isinstance(exc.response, dict) else "ClientError"
        print(f"LOCAL COHERENT RECOVERY SET FAILED: object-store error {str(code)[:80]}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"LOCAL COHERENT RECOVERY SET FAILED: unexpected {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(2)
