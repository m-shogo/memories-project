#!/usr/bin/env python3
"""Fail-closed validator for the pinned old/current session compatibility drill."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path("contracts/operations/mixed-version-session-contract.v1.json")
RESULT_PATH = Path("docs/fixtures/memory-os-operability/mixed-version-session-results.sample.v1.json")
VERSION_PATH = Path("contracts/operations/version-compatibility-contract.v1.json")
STATUS_PATH = Path("contracts/operations/production-operability-status.json")
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
FORBIDDEN_TEXT = (
    "bearer ",
    "authorization:",
    "token_digest",
    "session token",
    "postgres://",
    "password=",
    "secretaccesskey",
)


class ValidationFailure(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationFailure(f"root must be an object: {path}")
    return value


def string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValidationFailure(f"{name} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValidationFailure(f"{name} contains an empty or non-string value")
    if len(value) != len(set(value)):
        raise ValidationFailure(f"{name} contains duplicates")
    return value


def validate_contract(root: Path) -> dict[str, Any]:
    contract = load_json(root / CONTRACT_PATH)
    if contract.get("schemaVersion") != "memory-os-mixed-version-session.v1":
        raise ValidationFailure("unsupported contract schemaVersion")
    if contract.get("resultsSchemaVersion") != "memory-os-mixed-version-session-results.v1":
        raise ValidationFailure("unexpected results schemaVersion")
    old_sha = contract.get("oldBackendCommitSha")
    if not isinstance(old_sha, str) or not SHA_RE.fullmatch(old_sha):
        raise ValidationFailure("oldBackendCommitSha must be a full lowercase SHA")
    if contract.get("currentBackendRef") != "so":
        raise ValidationFailure("currentBackendRef must remain so")
    if contract.get("dependencyMode") != "EPHEMERAL_POSTGRES16_MINIO_TWO_PROCESSES":
        raise ValidationFailure("dependencyMode changed")
    if contract.get("productionEvidence") is not False:
        raise ValidationFailure("local mixed-version evidence cannot claim production")

    required = string_list(contract.get("requiredAssertions"), "requiredAssertions")
    joined = "\n".join(required).lower()
    for phrase in (
        "old-backend-issued session",
        "current-backend-issued session",
        "same current postgresql schema",
        "raw tokens",
    ):
        if phrase not in joined:
            raise ValidationFailure(f"required assertion omitted: {phrase}")

    forbidden = string_list(contract.get("forbiddenClaims"), "forbiddenClaims")
    forbidden_joined = "\n".join(forbidden).lower()
    for phrase in (
        "full old backend new schema compatibility",
        "full rolling backend compatibility",
        "production readiness",
    ):
        if phrase not in forbidden_joined:
            raise ValidationFailure(f"forbidden claim omitted: {phrase}")

    limitations = string_list(contract.get("limitations"), "limitations")
    if "not production compatibility evidence" not in limitations:
        raise ValidationFailure("production limitation is required")

    readiness = contract.get("readiness")
    if not isinstance(readiness, dict):
        raise ValidationFailure("readiness must be an object")
    for key in (
        "oldBackendNewSchemaFullyProven",
        "rollingBackendMixFullyProven",
        "productionReady",
    ):
        if readiness.get(key) is not False:
            raise ValidationFailure(f"{key} must remain false")

    refs = string_list(contract.get("evidenceRefs"), "evidenceRefs")
    for ref in refs:
        if not (root / ref).is_file():
            raise ValidationFailure(f"missing evidenceRef: {ref}")
    return contract


def validate_result(root: Path, contract: dict[str, Any], expected_sha: str | None) -> bool:
    path = root / RESULT_PATH
    if not path.exists():
        return False
    raw = path.read_text(encoding="utf-8")
    lower = raw.lower()
    for marker in FORBIDDEN_TEXT:
        if marker in lower:
            raise ValidationFailure(f"result contains forbidden sensitive marker: {marker}")
    result = load_json(path)
    if result.get("schemaVersion") != contract["resultsSchemaVersion"]:
        raise ValidationFailure("result schemaVersion mismatch")
    commit_sha = result.get("commitSha")
    if not isinstance(commit_sha, str) or not SHA_RE.fullmatch(commit_sha):
        raise ValidationFailure("result commitSha must be a full lowercase SHA")
    if expected_sha and commit_sha != expected_sha:
        raise ValidationFailure(
            f"result commitSha {commit_sha} does not match expected {expected_sha}"
        )
    if result.get("oldBackendCommitSha") != contract["oldBackendCommitSha"]:
        raise ValidationFailure("result old backend SHA does not match contract")
    if result.get("result") != "PASS" or result.get("integrityResult") != "PASS":
        raise ValidationFailure("mixed-version result must be PASS/PASS")

    environment = result.get("environment")
    if not isinstance(environment, dict):
        raise ValidationFailure("environment must be an object")
    if environment.get("productionEvidence") is not False:
        raise ValidationFailure("result cannot claim production evidence")
    if environment.get("containsSecrets") is not False:
        raise ValidationFailure("result must declare containsSecrets=false")
    if environment.get("syntheticDataOnly") is not True:
        raise ValidationFailure("result must use synthetic data only")

    assertions = result.get("assertions")
    if not isinstance(assertions, dict):
        raise ValidationFailure("assertions must be an object")
    if assertions.get("oldHealthStatus") != 200 or assertions.get("currentHealthStatus") != 200:
        raise ValidationFailure("both old and current health checks must be 200")
    for key in (
        "currentAcceptsOldIssuedSessionStatus",
        "oldAcceptsCurrentIssuedSessionStatus",
    ):
        status = assertions.get(key)
        if not isinstance(status, int) or status == 0 or status in {401, 403} or status >= 500:
            raise ValidationFailure(f"cross-version authentication failed: {key}={status!r}")
    if assertions.get("activeSessionRows") != 2:
        raise ValidationFailure("exactly two active synthetic sessions are required")
    for key in (
        "sharedCurrentSchema",
        "oldAndCurrentProcessesConcurrent",
    ):
        if assertions.get(key) is not True:
            raise ValidationFailure(f"assertion must be true: {key}")
    if assertions.get("rawTokensPersisted") is not False:
        raise ValidationFailure("rawTokensPersisted must be false")

    limitations = string_list(result.get("limitations"), "result.limitations")
    if set(limitations) != set(contract["limitations"]):
        raise ValidationFailure("result limitations must exactly match contract limitations")
    return True


def validate_authorities(root: Path) -> None:
    version = load_json(root / VERSION_PATH)
    if version.get("productionDecision") != "NO_GO":
        raise ValidationFailure("version compatibility decision must remain NO_GO")
    readiness = version.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("ready") is not False:
        raise ValidationFailure("version compatibility must remain not ready")
    status = load_json(root / STATUS_PATH)
    if status.get("productionDecision") != "NO_GO":
        raise ValidationFailure("production status must remain NO_GO")
    areas = status.get("areas")
    if not isinstance(areas, list):
        raise ValidationFailure("operability areas must be a list")
    area = next((item for item in areas if item.get("id") == "OPS-P0-008"), None)
    if not isinstance(area, dict) or area.get("status") == "READY":
        raise ValidationFailure("OPS-P0-008 cannot be READY from this slice")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expected-commit-sha", default=os.getenv("EXPECTED_COMMIT_SHA"))
    args = parser.parse_args()
    try:
        root = args.repo_root.resolve()
        contract = validate_contract(root)
        result_present = validate_result(root, contract, args.expected_commit_sha)
        validate_authorities(root)
    except ValidationFailure as exc:
        print(f"MIXED-VERSION SESSION VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"MIXED-VERSION SESSION VALIDATION FAILED WITH UNEXPECTED ERROR: {exc}", file=sys.stderr)
        return 2

    print("Memory OS mixed-version session validation PASS")
    print(f"exact-source result present: {str(result_present).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
