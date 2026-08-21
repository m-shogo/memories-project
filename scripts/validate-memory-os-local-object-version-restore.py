#!/usr/bin/env python3
"""Fail-closed validation for the local exact object-version restore drill."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROOT_REAL = ROOT.resolve()
CONTRACT_PATH = ROOT / "contracts/operations/local-object-version-restore-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/local-object-version-restore-results.sample.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_EVIDENCE = {
    "contracts/operations/local-object-version-restore-contract.v1.json",
    "scripts/run-memory-os-local-object-version-restore.py",
    "scripts/validate-memory-os-local-object-version-restore.py",
    "scripts/reconcile-memory-os-local-object-version-restore.py",
    ".github/workflows/local-object-version-restore.yml",
}


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def require_repo_regular_file(path: Path, label: str) -> None:
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise ValidationFailure(f"{label} escapes repository root") from exc
    require(relative != Path("."), f"{label} cannot resolve to repository root")
    current = ROOT
    for part in relative.parts:
        current = current / part
        require(not current.is_symlink(), f"{label} uses symlink component: {relative.as_posix()}")
    try:
        resolved = path.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError) as exc:
        raise ValidationFailure(f"{label} is missing or unreadable: {relative.as_posix()}") from exc
    try:
        resolved.relative_to(ROOT_REAL)
    except ValueError as exc:
        raise ValidationFailure(f"{label} resolves outside repository root: {relative.as_posix()}") from exc
    require(resolved.is_file(), f"{label} must be a regular file: {relative.as_posix()}")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def source_is_ancestor(value: Any) -> bool:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        return False
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", value, "HEAD"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def validate_result(result: dict[str, Any], expected_sha: str | None) -> None:
    require(result.get("schemaVersion") ==
            "memory-os-local-object-version-restore-results.v1",
            "object restore result schemaVersion drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "object restore result requires a full source SHA")
    require(source_is_ancestor(commit_sha),
            "object restore result source is not an ancestor of current HEAD")
    if expected_sha:
        require(commit_sha == expected_sha,
                f"object restore result SHA {commit_sha} != expected {expected_sha}")

    environment = result.get("environment")
    require(isinstance(environment, dict), "result environment must be an object")
    require(environment.get("objectStoreMode") ==
            "LOCAL_MINIO_VERSIONED_THREE_BUCKET_RECOVERY",
            "object-store mode drift")
    require(environment.get("productionEvidence") is False,
            "local object restore cannot be production evidence")
    require(environment.get("containsSecrets") is False,
            "result must state that it contains no secrets")
    for field in ("endpointIdentityDigest", "bucketSetIdentityDigest"):
        value = environment.get(field)
        require(isinstance(value, str) and DIGEST_RE.fullmatch(value) is not None,
                f"{field} must be a SHA-256 digest")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "result scenario must be an object")
    require(scenario.get("scenarioId") ==
            "exact-object-version-independent-bucket-restore-smoke",
            "scenario ID drift")
    require(scenario.get("result") == "PASS", "object restore result is not PASS")
    require(scenario.get("integrityResult") == "PASS",
            "object restore integrity is not PASS")
    require(scenario.get("sourceVersionsCreated") >= 3,
            "source version count is insufficient")
    require(scenario.get("sourceVersionsRemainingAfterLoss") == 0,
            "source versions remained after simulated loss")
    require(isinstance(scenario.get("durationSeconds"), int) and
            scenario["durationSeconds"] >= 0,
            "result duration is invalid")
    require(isinstance(scenario.get("contentLength"), int) and
            scenario["contentLength"] > 0,
            "content length is invalid")
    for field in (
        "selectedSourceVersionDigest", "backupVersionDigest",
        "restoreVersionDigest", "objectKeyDigest", "contentChecksumSha256",
    ):
        value = scenario.get(field)
        require(isinstance(value, str) and DIGEST_RE.fullmatch(value) is not None,
                f"{field} must be a SHA-256 digest")
    require(len({
        scenario["selectedSourceVersionDigest"],
        scenario["backupVersionDigest"],
        scenario["restoreVersionDigest"],
    }) == 3, "provider version identifier digests are not distinct")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "result assertions must be an object")
    expected_assertions = {
        "sourceVersionWasNonLatest",
        "sourceWasFullyPurgedBeforeRestore",
        "backupSourceVersionBindingMatched",
        "backupChecksumMatched",
        "restoredChecksumMatched",
        "restoredLengthMatched",
        "restoredSourceBindingMatched",
        "providerVersionIdentifiersWereDistinct",
    }
    require(set(assertions) == expected_assertions,
            f"object restore assertion set drift: {sorted(assertions)}")
    for field in expected_assertions:
        require(assertions.get(field) is True, f"object restore assertion failed: {field}")

    limitations = result.get("limitations")
    require(isinstance(limitations, list) and len(limitations) >= 6,
            "result limitations must remain explicit")
    joined = "\n".join(str(item) for item in limitations)
    for phrase in (
        "local MinIO", "not independent provider", "not production TLS",
        "not immutability", "not coherent PostgreSQL/object",
        "not approved RPO or RTO",
    ):
        require(phrase in joined, f"result limitation omitted: {phrase}")

    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "minioadmin", "aws_access_key_id", "aws_secret_access_key",
        '"access_key"', '"secret_key"', '"accesskeyid"', '"secretaccesskey"',
        "http://", "https://", "memory-os-source-", "memory-os-backup-",
        "memory-os-restore-", "synthetic/exact-version-recovery.json",
        '"versionid"', "fixture\":\"memory-os-object-restore",
    ):
        require(forbidden not in serialized,
                f"result contains forbidden raw evidence value: {forbidden}")


def main() -> int:
    for path, label in (
        (CONTRACT_PATH, "object restore contract"),
        (STATUS_PATH, "production operability status"),
    ):
        require_repo_regular_file(path, label)

    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") ==
            "memory-os-local-object-version-restore.v1",
            "object restore contract schemaVersion drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-local-object-version-restore-results.v1",
            "object restore results schemaVersion drift")
    expected_paths = {
        "runner": "scripts/run-memory-os-local-object-version-restore.py",
        "validator": "scripts/validate-memory-os-local-object-version-restore.py",
        "workflow": ".github/workflows/local-object-version-restore.yml",
        "reconcile": "scripts/reconcile-memory-os-local-object-version-restore.py",
        "resultPath": "docs/fixtures/memory-os-operability/local-object-version-restore-results.sample.v1.json",
        "diagnosticPath": "docs/fixtures/memory-os-operability/local-object-version-restore-diagnostic.last.json",
    }
    for field, expected in expected_paths.items():
        require(contract.get(field) == expected, f"{field} path drift")
    require(contract.get("dependencyMode") ==
            "LOCAL_MINIO_VERSIONED_THREE_BUCKET_RECOVERY",
            "dependency mode drift")

    scenario = contract.get("scenario")
    require(isinstance(scenario, dict), "scenario must be an object")
    require(scenario.get("scenarioId") ==
            "exact-object-version-independent-bucket-restore-smoke",
            "contract scenario ID drift")
    for field, minimum in (("requiredSteps", 13), ("successCriteria", 11),
                           ("abortCriteria", 8)):
        items = scenario.get(field)
        require(isinstance(items, list) and len(items) >= minimum,
                f"scenario.{field} is incomplete")
        require(len(items) == len(set(items)), f"scenario.{field} contains duplicates")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary must be an object")
    for field in (
        "productionEvidence", "independentProviderRetentionEvidence",
        "tlsEvidence", "credentialSeparationEvidence", "immutabilityEvidence",
        "lifecycleEvidence", "postgresObjectCoherenceEvidence",
        "rpoMeasured", "rtoMeasured",
    ):
        require(boundary.get(field) is False,
                f"local object restore cannot claim {field}")

    privacy = contract.get("privacy")
    require(isinstance(privacy, dict), "privacy must be an object")
    for field in (
        "syntheticDataOnly", "rawEndpointInEvidenceForbidden",
        "credentialInEvidenceForbidden", "rawBucketNameInEvidenceForbidden",
        "rawObjectKeyInEvidenceForbidden", "rawVersionIdInEvidenceForbidden",
        "payloadInEvidenceForbidden", "providerIdentifiersStoredAsSha256DigestOnly",
    ):
        require(privacy.get(field) is True, f"privacy.{field} must be true")

    runner_path = ROOT / contract["runner"]
    require_repo_regular_file(runner_path, "object restore runner")
    runner = runner_path.read_text(encoding="utf-8")
    for snippet in (
        "MEMORY_OS_ALLOW_EPHEMERAL_OBJECT_DELETE",
        'parsed.hostname in {"127.0.0.1", "localhost", "::1"}',
        'VersioningConfiguration={"Status": "Enabled"}',
        "VersionId=selected_source_version",
        '"source-version-sha256"',
        "purge_bucket(client, source_bucket)",
        "VersionId=backup_version",
        "len({selected_source_version, backup_version, restore_version}) == 3",
        '"productionEvidence": False',
        "unexpected {type(exc).__name__}",
    ):
        require(snippet in runner, f"runner missing safety/evidence boundary: {snippet}")
    for forbidden in (
        "print(access_key", "print(secret_key", "print(endpoint",
        "traceback.print_exc", "Body=payloads[-1]",
    ):
        require(forbidden not in runner, f"runner contains forbidden pattern: {forbidden}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for foundation in (
        "contractDefined", "runnerImplemented", "validatorImplemented",
        "automaticWorkflowImplemented", "exactSourcePassResultTrackedInStatus",
    ):
        require(readiness.get(foundation) is True,
                f"readiness.{foundation} must be true")
    for field in (
        "productionIndependentRetentionConfigured", "productionTlsConfigured",
        "productionCredentialSeparationConfigured", "productionLifecycleVerified",
        "coherentDatabaseObjectRestoreCompleted", "rpoRtoApprovedAndMeasured",
        "productionReady",
    ):
        require(readiness.get(field) is False,
                f"unproven object restore readiness cannot be true: {field}")

    refs = contract.get("evidenceRefs")
    require(isinstance(refs, list) and len(refs) == len(set(refs)),
            "object restore evidenceRefs invalid")
    require(set(refs) == EXPECTED_EVIDENCE, f"evidenceRefs drift: {refs}")
    for ref in refs:
        require_repo_regular_file(ROOT / ref, f"object restore evidence ref {ref}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA_RE.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be a full SHA")
        require(RESULT_PATH.is_file(), "exact-source object restore result is missing")
    if RESULT_PATH.is_file():
        require_repo_regular_file(RESULT_PATH, "object restore result")
        validate_result(load(RESULT_PATH), expected_sha)

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "local object restore cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-007"]
    require(len(matches) == 1, "OPS-P0-007 must exist exactly once")
    require(matches[0].get("status") != "READY",
            "local MinIO restore cannot make OPS-P0-007 READY")

    print("Memory OS local object-version restore validation PASS")
    print(f"result present: {RESULT_PATH.is_file()}")
    print(f"OPS-P0-007 status: {matches[0].get('status')}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"LOCAL OBJECT RESTORE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
