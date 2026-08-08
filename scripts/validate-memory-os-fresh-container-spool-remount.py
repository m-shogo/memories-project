#!/usr/bin/env python3
"""Fail-closed validation for fresh-container sealed-spool remount evidence."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/fresh-container-spool-remount-contract.v1.json"
RESULT = ROOT / "docs/fixtures/memory-os-operability/fresh-container-spool-remount-results.sample.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def strings(value: Any, field: str, minimum: int = 0) -> list[str]:
    require(isinstance(value, list), f"{field} must be list")
    require(len(value) >= minimum, f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains empty/non-string entry")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def validate_result(result: dict[str, Any], expected_sha: str | None) -> None:
    require(result.get("schemaVersion") == "memory-os-fresh-container-spool-remount-results.v1",
            "fresh-container result schema drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA40.fullmatch(commit_sha),
            "fresh-container result commitSha invalid")
    if expected_sha:
        require(commit_sha == expected_sha,
                f"fresh-container result SHA {commit_sha} != expected {expected_sha}")
    environment = result.get("environment")
    require(isinstance(environment, dict), "fresh-container environment missing")
    require(environment.get("mode") == "GITHUB_ACTIONS_UBUNTU_POSTGRES16_MINIO_FRESH_DOCKER",
            "fresh-container environment mode drift")
    require(environment.get("productionEvidence") is False and
            environment.get("syntheticDataOnly") is True and
            environment.get("containsSecrets") is False,
            "fresh-container evidence boundary drift")
    require(result.get("result") == "PASS" and result.get("integrityResult") == "PASS" and
            result.get("exitCode") == 0,
            "fresh-container result is not PASS")
    assertions = result.get("assertions")
    require(isinstance(assertions, dict), "fresh-container assertions missing")
    for flag in (
        "sealedSpoolPreservedAfterCommitFailure",
        "originalSpoolManagerClosed",
        "freshContainerStarted",
        "sameSpoolDirectoryBindMounted",
        "sameSpoolIdReused",
        "resumeWithoutObjectStore",
        "resumeWithoutParser",
        "firstSuccessfulRecoveryNotReplay",
    ):
        require(assertions.get(flag) is True, f"fresh-container assertion failed: {flag}")
    require(assertions.get("previewRowsAfterRecovery") == 1,
            "fresh-container preview row count drift")
    require(assertions.get("candidateRowsAfterRecovery") == 2,
            "fresh-container candidate row count drift")
    require(assertions.get("rejectionRowsAfterRecovery") == 1,
            "fresh-container rejection row count drift")
    require(assertions.get("producerRestartExecuted") is False,
            "consumer-only fresh-container drill cannot claim producer restart")
    limitations = strings(result.get("limitations"), "result.limitations", 6)
    joined = "\n".join(limitations)
    for phrase in (
        "producer remains the host test process",
        "producer restart not executed",
        "not a reviewed production parser artifact",
        "not production-equivalent",
        "not production chaos evidence",
    ):
        require(phrase in joined, f"fresh-container limitation omitted: {phrase}")
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "authorization: bearer",
        "minioadmin", "access_key", "secret_key", "/tmp/", "/home/runner/",
    ):
        require(forbidden not in serialized,
                f"fresh-container result contains forbidden material: {forbidden}")


def main() -> int:
    contract = load(CONTRACT)
    require(contract.get("schemaVersion") == "memory-os-fresh-container-spool-remount.v1",
            "fresh-container contract schema drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-fresh-container-spool-remount-results.v1",
            "fresh-container results schema drift")
    require(contract.get("runnerCommand") ==
            "MEMORY_OS_RUN_DOCKER_SPOOL_REMOUNT=1 CGO_ENABLED=0 go test ./internal/importflow -run ^TestFlowResumesSealedSpoolInFreshContainer$ -count=1",
            "fresh-container runner command drift")
    require(contract.get("workingDirectory") == "services/import-api",
            "fresh-container workingDirectory drift")
    strings(contract.get("requiredAssertions"), "requiredAssertions", 10)
    strings(contract.get("implementationGuards"), "implementationGuards", 6)
    strings(contract.get("limitations"), "limitations", 7)
    privacy = contract.get("privacy")
    require(isinstance(privacy, dict), "fresh-container privacy missing")
    require(privacy.get("productionEvidence") is False and
            privacy.get("productionCredentials") is False,
            "fresh-container privacy production boundary drift")
    for flag in (
        "syntheticDataOnly", "databaseUrlInEvidenceForbidden",
        "objectStoreCredentialsInEvidenceForbidden", "hostPathInEvidenceForbidden",
        "userContentInEvidenceForbidden",
    ):
        require(privacy.get(flag) is True, f"fresh-container privacy.{flag} must be true")

    source = (ROOT / "services/import-api/internal/importflow/docker_spool_remount_drill_linux_test.go").read_text(encoding="utf-8")
    for snippet in (
        "env.flow.Spool.Close()",
        '"-v", env.root+":/recovery-spool"',
        'dockerResumeHelperGate+"=1"',
        'Flow{Spool: manager, Committer: committer}',
        "ResumeCommit(context.Background()",
        "MEMORY_OS_FRESH_CONTAINER_SPOOL_REMOUNT=PASS",
        "sanitizeDockerResumeOutput",
    ):
        require(snippet in source, f"fresh-container test missing boundary: {snippet}")
    resume = (ROOT / "services/import-api/internal/importflow/resume.go").read_text(encoding="utf-8")
    require("f.Objects" not in resume and "f.Supervisor" not in resume,
            "ResumeCommit unexpectedly gained object-store/parser dependency")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "fresh-container readiness missing")
    for flag in ("contractDefined", "testImplemented", "validatorImplemented", "automaticWorkflowImplemented"):
        require(readiness.get(flag) is True, f"fresh-container readiness.{flag} must be true")
    require(readiness.get("producerRestartExecuted") is False and readiness.get("productionReady") is False,
            "fresh-container foundation cannot claim producer restart or production readiness")
    if readiness.get("freshContainerRemountCompleted") is True:
        require(readiness.get("exactSourcePassResultCommitted") is True and
                readiness.get("originalSpoolManagerClosed") is True and
                readiness.get("resumeWithoutObjectStoreOrParser") is True,
                "fresh-container completed readiness dependencies missing")
        require(RESULT.is_file(), "completed fresh-container readiness requires result")

    refs = strings(contract.get("evidenceRefs"), "evidenceRefs", 6)
    for ref in refs:
        require((ROOT / ref).is_file(), f"fresh-container evidence ref missing: {ref}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA40.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be full SHA")
        require(RESULT.is_file(), "exact-source fresh-container result missing")
    if RESULT.is_file():
        validate_result(load(RESULT), expected_sha)

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO",
            "fresh-container evidence cannot change production decision")
    gate = next((row for row in status.get("areas", [])
                 if isinstance(row, dict) and row.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict) and gate.get("status") != "READY",
            "fresh-container local drill cannot make OPS-P0-009 READY")

    print("Memory OS fresh-container spool remount validation PASS")
    print(f"result present: {RESULT.is_file()}")
    print("producer restart executed: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FRESH-CONTAINER SPOOL REMOUNT VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
