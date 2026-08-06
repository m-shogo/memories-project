#!/usr/bin/env python3
"""Fail-closed validation for parser restart recovery matrix evidence."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/parser-restart-matrix-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/parser-restart-matrix-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_CLASSES = {
    "protocol_truncation": ("ErrFrameProtocolViolation", True, False),
    "wall_clock_timeout": ("ErrParseTimeout", True, False),
    "cpu_limit_kill": ("ErrWorkerFailed", True, True),
    "memory_limit_kill": ("ErrWorkerFailed", True, True),
    "pre_start_cancellation": ("context.Canceled", False, False),
}


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def strings(value: Any, field: str, minimum: int = 0) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(len(value) >= minimum, f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def validate_result(result: dict[str, Any], expected_sha: str | None) -> None:
    require(result.get("schemaVersion") == "memory-os-parser-restart-matrix-results.v1",
            "matrix result schemaVersion drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "matrix result commitSha must be a full SHA")
    if expected_sha:
        require(commit_sha == expected_sha,
                f"matrix result SHA {commit_sha} != expected {expected_sha}")
    environment = result.get("environment")
    require(isinstance(environment, dict), "matrix result environment missing")
    require(environment.get("mode") == "GITHUB_ACTIONS_UBUNTU_LINUX_NON_RACE",
            "matrix result environment mode drift")
    require(environment.get("productionEvidence") is False,
            "matrix result cannot claim production evidence")
    require(environment.get("syntheticDataOnly") is True,
            "matrix result must use synthetic data only")
    require(environment.get("containsSecrets") is False,
            "matrix result must state containsSecrets false")

    cases = result.get("failureClasses")
    require(isinstance(cases, list), "matrix failureClasses must be a list")
    by_id = {item.get("id"): item for item in cases if isinstance(item, dict)}
    require(set(by_id) == set(EXPECTED_CLASSES),
            f"matrix result class set drift: {sorted(by_id)}")
    require(len(cases) == len(by_id), "matrix result classes contain duplicates")
    for class_id in EXPECTED_CLASSES:
        item = by_id[class_id]
        require(item.get("result") == "PASS", f"matrix class is not PASS: {class_id}")
        for assertion in (
            "expectedErrorMatched", "spoolResidueAbsent", "sameSpoolReusable",
            "replacementSealValid", "independentVerificationMatched",
        ):
            require(item.get(assertion) is True,
                    f"matrix assertion failed for {class_id}: {assertion}")
    require(result.get("overallResult") == "PASS",
            "complete five-class matrix result must be PASS")
    limitations = strings(result.get("limitations"), "matrix result limitations", 6)
    joined = "\n".join(limitations)
    for phrase in (
        "in-flight cancellation latency not proven",
        "child-process reaping not independently measured",
        "host restart not executed",
        "production artifact not exercised",
        "not production chaos evidence",
    ):
        require(phrase in joined, f"matrix result limitation omitted: {phrase}")
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "password=", "postgres://", "authorization: bearer", "workerpath",
        "spoolpath", "secretaccesskey", "user content",
    ):
        require(forbidden not in serialized,
                f"matrix result contains forbidden evidence value: {forbidden}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-parser-restart-matrix.v1",
            "matrix contract schemaVersion drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-parser-restart-matrix-results.v1",
            "matrix results schemaVersion drift")
    require(contract.get("runnerCommand") ==
            "go test ./internal/parsersup -run ^TestSupervisorRestartRecoveryMatrix$ -count=1",
            "matrix runner command drift")
    require(contract.get("workingDirectory") == "services/import-api",
            "matrix workingDirectory drift")
    require(contract.get("validator") ==
            "scripts/validate-memory-os-parser-restart-matrix.py",
            "matrix validator path drift")
    require(contract.get("resultPath") ==
            "docs/fixtures/memory-os-operability/parser-restart-matrix-results.sample.v1.json",
            "matrix result path drift")

    classes = contract.get("failureClasses")
    require(isinstance(classes, list), "failureClasses must be a list")
    by_id = {item.get("id"): item for item in classes if isinstance(item, dict)}
    require(set(by_id) == set(EXPECTED_CLASSES),
            f"matrix contract class set drift: {sorted(by_id)}")
    require(len(classes) == len(by_id), "matrix contract classes contain duplicates")
    for class_id, expected in EXPECTED_CLASSES.items():
        item = by_id[class_id]
        error_class, worker_started, kernel_driven = expected
        require(item.get("expectedErrorClass") == error_class,
                f"matrix expected error drift: {class_id}")
        require(item.get("workerStarted") is worker_started,
                f"matrix workerStarted drift: {class_id}")
        require(item.get("kernelLimitDriven") is kernel_driven,
                f"matrix kernelLimitDriven drift: {class_id}")

    assertions = strings(contract.get("requiredRecoveryAssertions"),
                         "requiredRecoveryAssertions", 5)
    require(any("same manager" in value for value in assertions),
            "matrix must require same manager/spool reuse")
    privacy = contract.get("privacy")
    require(isinstance(privacy, dict), "matrix privacy must be an object")
    require(privacy.get("productionEvidence") is False,
            "matrix privacy cannot claim production evidence")
    for flag in (
        "syntheticDataOnly", "secretsInEvidenceForbidden",
        "workerPathInEvidenceForbidden", "rawSpoolPathInEvidenceForbidden",
        "userContentInEvidenceForbidden",
    ):
        require(privacy.get(flag) is True, f"matrix privacy.{flag} must be true")
    strings(contract.get("limitations"), "matrix limitations", 6)

    test_path = ROOT / "services/import-api/internal/parsersup/restart_matrix_drill_linux_test.go"
    require(test_path.is_file(), "matrix Go test is missing")
    source = test_path.read_text(encoding="utf-8")
    for snippet in (
        "protocol_truncation", "wall_clock_timeout", "cpu_limit_kill",
        "memory_limit_kill", "pre_start_cancellation", "assertRootEmpty",
        "replacementSupervisor.Parse", "verifier.Verify",
    ):
        require(snippet in source, f"matrix Go test missing boundary: {snippet}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "matrix readiness must be an object")
    for foundation in ("contractDefined", "testImplemented", "validatorImplemented"):
        require(readiness.get(foundation) is True,
                f"matrix readiness.{foundation} must be true")
    for unproven in (
        "exactSourcePassResultCommitted", "inFlightCancellationProven",
        "childProcessReapingProven", "hostRestartProven",
        "productionArtifactRestartProven", "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven matrix readiness cannot be true: {unproven}")

    refs = strings(contract.get("evidenceRefs"), "matrix evidenceRefs", 5)
    for ref in refs:
        require((ROOT / ref).is_file(), f"matrix evidence path missing: {ref}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA_RE.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be a full SHA")
        require(RESULT_PATH.is_file(), "exact-source matrix result is missing")
    if RESULT_PATH.is_file():
        validate_result(load(RESULT_PATH), expected_sha)

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "matrix CI evidence cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    gate = next((item for item in areas
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict), "OPS-P0-009 missing")
    require(gate.get("status") != "READY",
            "local parser matrix cannot make OPS-P0-009 READY")

    print("Memory OS parser restart matrix validation PASS")
    print(f"failure classes: {len(EXPECTED_CLASSES)}")
    print(f"result present: {RESULT_PATH.is_file()}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"PARSER RESTART MATRIX VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
