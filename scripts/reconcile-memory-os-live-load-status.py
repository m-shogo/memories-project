#!/usr/bin/env python3
"""Register validated live dependency load results without changing readiness.

This script is intentionally narrow. It may replace the single pending-results
open gap only after both exact-source live result documents pass their canonical
validators for the same source commit. It must never mark OPS-P0-006 READY or
change the production decision from NO_GO.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
LOAD_CONTRACT_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
POSTGRES_VALIDATOR = ROOT / "scripts/validate-memory-os-live-load.py"
OBJECT_VALIDATOR = ROOT / "scripts/validate-memory-os-live-object-load.py"
LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
POSTGRES_RESULT = (
    ROOT
    / "docs/fixtures/memory-os-operability/live-postgres-load-results.sample.v1.json"
)
OBJECT_RESULT = (
    ROOT
    / "docs/fixtures/memory-os-operability/live-object-load-results.sample.v1.json"
)
PENDING_TEXT = (
    "exact-HEAD committed PASS results from the live PostgreSQL and MinIO "
    "checkpoint (automatic generation pending)"
)
POSTGRES_EVIDENCE = (
    "exact-HEAD committed PASS result from the local PostgreSQL Preview read "
    "and concurrent idempotent Apply checkpoint"
)
OBJECT_EVIDENCE = (
    "exact-HEAD committed PASS result from the local MinIO signed-upload, "
    "exact-version completion and scan-enqueue checkpoint"
)
POSTGRES_RESULT_REF = POSTGRES_RESULT.relative_to(ROOT).as_posix()
OBJECT_RESULT_REF = OBJECT_RESULT.relative_to(ROOT).as_posix()


class ReconcileFailure(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing required file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReconcileFailure(f"top-level JSON must be an object: {path.relative_to(ROOT)}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def canonical_root() -> Path:
    return Path(__file__).resolve().parents[1]


def require_exact_authority(actual: Path, relative: str, label: str) -> None:
    root = canonical_root()
    expected = root / relative
    require(actual == expected, f"canonical {label} authority drift")
    require(expected.is_file(), f"canonical {label} authority missing")
    current = expected
    while current != root:
        require(not current.is_symlink(), f"canonical {label} authority must be symlink-free")
        current = current.parent


def validate_authority_identity() -> None:
    require(ROOT == canonical_root(), "canonical live-load repository root authority drift")
    for actual, relative, label in (
        (
            STATUS_PATH,
            "contracts/operations/production-operability-status.json",
            "production status",
        ),
        (
            LOAD_CONTRACT_PATH,
            "contracts/operations/load-test-scenario-contract.v1.json",
            "load contract",
        ),
        (
            POSTGRES_RESULT,
            "docs/fixtures/memory-os-operability/live-postgres-load-results.sample.v1.json",
            "PostgreSQL live-load result",
        ),
        (
            OBJECT_RESULT,
            "docs/fixtures/memory-os-operability/live-object-load-results.sample.v1.json",
            "MinIO live-object-load result",
        ),
        (
            POSTGRES_VALIDATOR,
            "scripts/validate-memory-os-live-load.py",
            "PostgreSQL live-load validator",
        ),
        (
            OBJECT_VALIDATOR,
            "scripts/validate-memory-os-live-object-load.py",
            "MinIO live-object-load validator",
        ),
        (
            LOAD_VALIDATOR,
            "scripts/validate-memory-os-load.py",
            "load validator",
        ),
        (
            OPERABILITY_VALIDATOR,
            "scripts/validate-memory-os-operability.py",
            "operability validator",
        ),
    ):
        require_exact_authority(actual, relative, label)


def run_validator(validator: Path, label: str, env: dict[str, str] | None = None) -> None:
    require(validator.is_file(), f"canonical {label} validator missing")
    completed = subprocess.run(
        [sys.executable, str(validator)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"canonical {label} validation failed: {completed.stdout[-2000:]}",
    )


def validate_live_authorities(expected_sha: str) -> None:
    env = dict(os.environ)
    env["EXPECTED_COMMIT_SHA"] = expected_sha
    for validator, label in (
        (POSTGRES_VALIDATOR, "PostgreSQL live-load"),
        (OBJECT_VALIDATOR, "MinIO live-object-load"),
    ):
        run_validator(validator, label, env)


def validate_derived_authorities() -> None:
    run_validator(LOAD_VALIDATOR, "load")
    run_validator(OPERABILITY_VALIDATOR, "operability")


def result_is_pass(document: dict[str, Any], expected_sha: str) -> bool:
    if document.get("commitSha") != expected_sha:
        return False
    scenarios = document.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return False
    return all(
        isinstance(item, dict)
        and item.get("result") == "PASS"
        and item.get("integrityResult") == "PASS"
        for item in scenarios
    )


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def json_bytes(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main() -> int:
    validate_authority_identity()

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA", "")
    require(len(expected_sha) == 40, "EXPECTED_COMMIT_SHA must be a full commit SHA")

    # Standalone execution must be as strict as the workflow. Do not rely on a
    # caller having run these validators before invoking this reconciler.
    validate_live_authorities(expected_sha)

    postgres = load(POSTGRES_RESULT)
    object_result = load(OBJECT_RESULT)
    require(result_is_pass(postgres, expected_sha), "PostgreSQL result is not an exact-source PASS")
    require(result_is_pass(object_result, expected_sha), "MinIO result is not an exact-source PASS")

    status = load(STATUS_PATH)
    load_contract = load(LOAD_CONTRACT_PATH)
    require(status.get("productionDecision") == "NO_GO", "reconcile requires productionDecision NO_GO")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    load_areas = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-006"]
    require(len(load_areas) == 1, "OPS-P0-006 must exist exactly once")
    area = load_areas[0]
    require(area.get("status") == "PARTIAL", "reconcile cannot alter a non-PARTIAL load gate")

    existing = area.get("existingEvidence")
    missing = area.get("missingEvidence")
    refs = area.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-006 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-006 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-006 evidenceRefs must be a list")

    changed = False
    for evidence in (POSTGRES_EVIDENCE, OBJECT_EVIDENCE):
        if evidence not in existing:
            existing.append(evidence)
            changed = True
    for ref in (POSTGRES_RESULT_REF, OBJECT_RESULT_REF):
        if ref not in refs:
            refs.append(ref)
            changed = True
    if PENDING_TEXT in missing:
        missing.remove(PENDING_TEXT)
        changed = True

    readiness = load_contract.get("readiness")
    require(isinstance(readiness, dict), "load contract readiness must be an object")
    if readiness.get("exactHeadLiveResultsCommitted") is not True:
        readiness["exactHeadLiveResultsCommitted"] = True
        changed = True

    required_open_phrases = (
        "capacity boundary",
        "sustained soak",
        "production-equivalent",
        "production object-store TLS",
    )
    for phrase in required_open_phrases:
        require(any(phrase in item for item in missing), f"required open gap disappeared: {phrase}")

    for readiness_key in (
        "productionShapedWorkload",
        "capacityBoundaryEstablished",
        "sustainedSoakEvidence",
        "operationalThresholds",
        "productionEquivalentDependencies",
    ):
        require(readiness.get(readiness_key) is False, f"local results cannot enable {readiness_key}")

    require(area.get("status") == "PARTIAL", "OPS-P0-006 readiness changed unexpectedly")
    require(status.get("productionDecision") == "NO_GO", "production decision changed unexpectedly")

    if not changed:
        validate_derived_authorities()
        print("Live load evidence metadata already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    original_status = STATUS_PATH.read_bytes()
    original_load_contract = LOAD_CONTRACT_PATH.read_bytes()
    try:
        atomic_write_bytes(STATUS_PATH, json_bytes(status))
        atomic_write_bytes(LOAD_CONTRACT_PATH, json_bytes(load_contract))
        validate_derived_authorities()
    except Exception:
        atomic_write_bytes(STATUS_PATH, original_status)
        atomic_write_bytes(LOAD_CONTRACT_PATH, original_load_contract)
        raise

    print("Registered exact-source live PostgreSQL and MinIO PASS results; OPS-P0-006 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
