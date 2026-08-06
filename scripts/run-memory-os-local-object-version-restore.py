#!/usr/bin/env python3
"""Run a synthetic, local-only exact object-version backup/restore drill."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
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
    print("LOCAL OBJECT RESTORE FAILED: boto3 is required", file=sys.stderr)
    raise SystemExit(1) from exc

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = Path(os.environ.get(
    "MEMORY_OS_LOCAL_OBJECT_RESTORE_RESULTS_PATH",
    ROOT / "docs/fixtures/memory-os-operability/local-object-version-restore-results.sample.v1.json",
))
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class DrillFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DrillFailure(message)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def list_all_versions(client: Any, bucket: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    versions: list[dict[str, str]] = []
    markers: list[dict[str, str]] = []
    paginator = client.get_paginator("list_object_versions")
    for page in paginator.paginate(Bucket=bucket):
        for item in page.get("Versions", []):
            versions.append({"Key": item["Key"], "VersionId": item["VersionId"]})
        for item in page.get("DeleteMarkers", []):
            markers.append({"Key": item["Key"], "VersionId": item["VersionId"]})
    return versions, markers


def purge_bucket(client: Any, bucket: str) -> None:
    versions, markers = list_all_versions(client, bucket)
    objects = versions + markers
    for offset in range(0, len(objects), 1000):
        response = client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": objects[offset:offset + 1000], "Quiet": True},
        )
        require(not response.get("Errors"), "version purge returned object errors")
    remaining_versions, remaining_markers = list_all_versions(client, bucket)
    require(not remaining_versions and not remaining_markers,
            "object versions or delete markers remain after purge")


def safe_client_error(exc: ClientError) -> str:
    response = exc.response if isinstance(exc.response, dict) else {}
    error = response.get("Error", {}) if isinstance(response, dict) else {}
    code = error.get("Code", "ClientError") if isinstance(error, dict) else "ClientError"
    return str(code)[:80]


def main() -> int:
    endpoint = os.environ.get("MEMORY_OS_TEST_S3_ENDPOINT", "")
    access_key = os.environ.get("MEMORY_OS_TEST_S3_ACCESS_KEY", "")
    secret_key = os.environ.get("MEMORY_OS_TEST_S3_SECRET_KEY", "")
    source_sha = os.environ.get("MEMORY_OS_COMMIT_SHA", "")
    allow_delete = os.environ.get("MEMORY_OS_ALLOW_EPHEMERAL_OBJECT_DELETE", "")
    keep_buckets = os.environ.get("MEMORY_OS_KEEP_OBJECT_RESTORE_BUCKETS", "0") == "1"

    parsed = urlparse(endpoint)
    require(parsed.scheme in {"http", "https"}, "local S3 endpoint scheme is invalid")
    require(parsed.hostname in {"127.0.0.1", "localhost", "::1"},
            "runner is restricted to a local object-store endpoint")
    require(access_key and secret_key, "local object-store credentials are required")
    require(allow_delete == "1", "MEMORY_OS_ALLOW_EPHEMERAL_OBJECT_DELETE=1 is required")
    require(SHA_RE.fullmatch(source_sha) is not None,
            "MEMORY_OS_COMMIT_SHA must be a full commit SHA")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )

    suffix = hashlib.sha256(f"{source_sha}:{uuid.uuid4().hex}".encode()).hexdigest()[:16]
    source_bucket = f"memory-os-source-{suffix}"
    backup_bucket = f"memory-os-backup-{suffix}"
    restore_bucket = f"memory-os-restore-{suffix}"
    buckets = (source_bucket, backup_bucket, restore_bucket)
    object_key = "synthetic/exact-version-recovery.json"
    started_at = dt.datetime.now(dt.timezone.utc)
    started_monotonic = time.monotonic()

    try:
        for bucket in buckets:
            client.create_bucket(Bucket=bucket)
            client.put_bucket_versioning(
                Bucket=bucket,
                VersioningConfiguration={"Status": "Enabled"},
            )
            versioning = client.get_bucket_versioning(Bucket=bucket)
            require(versioning.get("Status") == "Enabled",
                    "bucket versioning did not become enabled")

        payloads = [
            json.dumps({"fixture": "memory-os-object-restore", "revision": revision},
                       separators=(",", ":")).encode("utf-8")
            for revision in (1, 2, 3)
        ]
        source_versions: list[str] = []
        for payload in payloads:
            response = client.put_object(
                Bucket=source_bucket,
                Key=object_key,
                Body=payload,
                ContentType="application/json",
                Metadata={"fixture-class": "synthetic-operational"},
            )
            version_id = response.get("VersionId")
            require(isinstance(version_id, str) and version_id,
                    "source put did not return a VersionId")
            source_versions.append(version_id)
        require(len(set(source_versions)) == 3,
                "source did not produce three distinct versions")

        selected_source_version = source_versions[1]
        require(selected_source_version != source_versions[-1],
                "selected source version must be non-latest")
        selected = client.get_object(
            Bucket=source_bucket,
            Key=object_key,
            VersionId=selected_source_version,
        )
        selected_body = selected["Body"].read()
        selected_checksum = sha256_bytes(selected_body)
        selected_length = len(selected_body)
        require(selected_body == payloads[1], "explicit source version returned wrong bytes")

        source_version_digest = sha256_text(selected_source_version)
        source_key_digest = sha256_text(object_key)
        backup_response = client.put_object(
            Bucket=backup_bucket,
            Key=object_key,
            Body=selected_body,
            ContentType="application/json",
            Metadata={
                "source-version-sha256": source_version_digest,
                "source-key-sha256": source_key_digest,
                "checksum-sha256": selected_checksum,
                "content-length-decimal": str(selected_length),
                "fixture-class": "synthetic-operational",
            },
        )
        backup_version = backup_response.get("VersionId")
        require(isinstance(backup_version, str) and backup_version,
                "backup put did not return a VersionId")
        backup_head = client.head_object(
            Bucket=backup_bucket,
            Key=object_key,
            VersionId=backup_version,
        )
        backup_metadata = backup_head.get("Metadata", {})
        require(backup_metadata.get("source-version-sha256") == source_version_digest,
                "backup metadata lost source-version binding")
        require(backup_metadata.get("source-key-sha256") == source_key_digest,
                "backup metadata lost source-key binding")
        require(backup_metadata.get("checksum-sha256") == selected_checksum,
                "backup metadata checksum mismatch")
        require(backup_metadata.get("content-length-decimal") == str(selected_length),
                "backup metadata content length mismatch")

        purge_bucket(client, source_bucket)
        try:
            client.get_object(Bucket=source_bucket, Key=object_key)
        except ClientError as exc:
            require(safe_client_error(exc) in {
                "NoSuchKey", "NoSuchVersion", "404", "NotFound"
            }, "source get failed for an unexpected reason")
        else:
            raise DrillFailure("source object remained available after complete purge")

        backup_object = client.get_object(
            Bucket=backup_bucket,
            Key=object_key,
            VersionId=backup_version,
        )
        backup_body = backup_object["Body"].read()
        require(sha256_bytes(backup_body) == selected_checksum,
                "explicit backup version checksum mismatch")
        require(len(backup_body) == selected_length,
                "explicit backup version length mismatch")

        restore_response = client.put_object(
            Bucket=restore_bucket,
            Key=object_key,
            Body=backup_body,
            ContentType="application/json",
            Metadata={
                "backup-version-sha256": sha256_text(backup_version),
                "source-version-sha256": source_version_digest,
                "source-key-sha256": source_key_digest,
                "checksum-sha256": selected_checksum,
                "content-length-decimal": str(selected_length),
                "fixture-class": "synthetic-operational",
            },
        )
        restore_version = restore_response.get("VersionId")
        require(isinstance(restore_version, str) and restore_version,
                "restore put did not return a VersionId")
        restored = client.get_object(
            Bucket=restore_bucket,
            Key=object_key,
            VersionId=restore_version,
        )
        restored_body = restored["Body"].read()
        restored_metadata = restored.get("Metadata", {})
        require(sha256_bytes(restored_body) == selected_checksum,
                "restored checksum mismatch")
        require(len(restored_body) == selected_length,
                "restored content length mismatch")
        require(restored_metadata.get("source-version-sha256") == source_version_digest,
                "restore lost source-version binding")
        require(restored_metadata.get("backup-version-sha256") == sha256_text(backup_version),
                "restore lost backup-version binding")
        require(restored_metadata.get("source-key-sha256") == source_key_digest,
                "restore lost source-key binding")
        require(len({selected_source_version, backup_version, restore_version}) == 3,
                "source backup and restore VersionIds are not distinct")

        completed_at = dt.datetime.now(dt.timezone.utc)
        duration_seconds = max(0, int(time.monotonic() - started_monotonic))
        result = {
            "schemaVersion": "memory-os-local-object-version-restore-results.v1",
            "commitSha": source_sha,
            "generatedAt": completed_at.isoformat().replace("+00:00", "Z"),
            "environment": {
                "objectStoreMode": "LOCAL_MINIO_VERSIONED_THREE_BUCKET_RECOVERY",
                "productionEvidence": False,
                "endpointIdentityDigest": sha256_text(
                    f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 80}"
                ),
                "bucketSetIdentityDigest": sha256_text(":".join(buckets)),
                "containsSecrets": False,
            },
            "scenario": {
                "scenarioId": "exact-object-version-independent-bucket-restore-smoke",
                "startedAt": started_at.isoformat().replace("+00:00", "Z"),
                "completedAt": completed_at.isoformat().replace("+00:00", "Z"),
                "durationSeconds": duration_seconds,
                "sourceVersionsCreated": len(source_versions),
                "sourceVersionsRemainingAfterLoss": 0,
                "selectedSourceVersionDigest": source_version_digest,
                "backupVersionDigest": sha256_text(backup_version),
                "restoreVersionDigest": sha256_text(restore_version),
                "objectKeyDigest": source_key_digest,
                "contentChecksumSha256": selected_checksum,
                "contentLength": selected_length,
                "assertions": {
                    "sourceVersionWasNonLatest": True,
                    "sourceWasFullyPurgedBeforeRestore": True,
                    "backupSourceVersionBindingMatched": True,
                    "backupChecksumMatched": True,
                    "restoredChecksumMatched": True,
                    "restoredLengthMatched": True,
                    "restoredSourceBindingMatched": True,
                    "providerVersionIdentifiersWereDistinct": True,
                },
                "integrityResult": "PASS",
                "result": "PASS",
            },
            "limitations": [
                "local MinIO three-bucket recovery only",
                "not independent provider retention evidence",
                "not production TLS or credential-separation evidence",
                "not immutability or lifecycle evidence",
                "not coherent PostgreSQL/object recovery evidence",
                "not approved RPO or RTO evidence",
            ],
        }
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("Memory OS local exact object-version restore PASS")
        print("source versions: 3  source remaining: 0  restored checksum: PASS")
        print(f"result: {RESULT_PATH}")
        return 0
    finally:
        if not keep_buckets:
            for bucket in reversed(buckets):
                try:
                    purge_bucket(client, bucket)
                    client.delete_bucket(Bucket=bucket)
                except Exception:
                    # Cleanup must not hide the primary result or leak provider
                    # details. Workflow isolation destroys the local MinIO
                    # container even when this best-effort cleanup fails.
                    pass


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DrillFailure as exc:
        print(f"LOCAL OBJECT RESTORE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except ClientError as exc:
        print(f"LOCAL OBJECT RESTORE FAILED: object-store error {safe_client_error(exc)}",
              file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"LOCAL OBJECT RESTORE FAILED: unexpected {type(exc).__name__}",
              file=sys.stderr)
        raise SystemExit(2)
