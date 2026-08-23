#!/usr/bin/env python3
"""Register the production-equivalent admission foundation without promoting execution evidence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/production-equivalent-dependency-contract.v1.json"
CANONICAL_LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_DEPENDENCY_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-dependencies.py"
CANONICAL_LOAD_INDEX_VALIDATOR = ROOT / "scripts/validate-memory-os-load-evidence-index.py"
CANONICAL_LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CANONICAL_WORKFLOW_PATH = ROOT / ".github/workflows/production-equivalent-dependency-contract.yml"

CONTRACT_PATH = CANONICAL_CONTRACT_PATH
LOAD_PATH = CANONICAL_LOAD_PATH
STATUS_PATH = CANONICAL_STATUS_PATH
DEPENDENCY_VALIDATOR = CANONICAL_DEPENDENCY_VALIDATOR
LOAD_INDEX_VALIDATOR = CANONICAL_LOAD_INDEX_VALIDATOR
LOAD_VALIDATOR = CANONICAL_LOAD_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
WORKFLOW_PATH = CANONICAL_WORKFLOW_PATH

FOUNDATION_REFS = (
    "contracts/operations/production-equivalent-dependency-contract.v1.json",
    "scripts/validate-memory-os-production-equivalent-dependencies.py",
    "scripts/reconcile-memory-os-production-equivalent-foundation.py",
    ".github/workflows/production-equivalent-dependency-contract.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_runtime_authority(candidate: Path, expected: Path, label: str) -> None:
    root = ROOT.resolve(strict=True)
    require(candidate == expected, f"{label} authority drift: expected {expected.relative_to(ROOT)}, got {candidate}")
    require(not candidate.is_symlink(), f"{label} authority must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
        expected_resolved = expected.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise Fail(f"{label} authority missing or escapes repository: {candidate}") from exc
    require(resolved == expected_resolved, f"{label} authority drift after resolution")


def enforce_runtime_authorities() -> None:
    for candidate, expected, label in (
        (CONTRACT_PATH, CANONICAL_CONTRACT_PATH, "dependency contract"),
        (LOAD_PATH, CANONICAL_LOAD_PATH, "load contract"),
        (STATUS_PATH, CANONICAL_STATUS_PATH, "production status"),
        (DEPENDENCY_VALIDATOR, CANONICAL_DEPENDENCY_VALIDATOR, "dependency validator"),
        (LOAD_INDEX_VALIDATOR, CANONICAL_LOAD_INDEX_VALIDATOR, "load index validator"),
        (LOAD_VALIDATOR, CANONICAL_LOAD_VALIDATOR, "load validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
        (WORKFLOW_PATH, CANONICAL_WORKFLOW_PATH, "foundation workflow"),
    ):
        require_runtime_authority(candidate, expected, label)


def load(path: Path) -> dict[str, Any]:
    enforce_runtime_authorities()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def atomic_write(path: Path, value: dict[str, Any] | bytes) -> None:
    data = value if isinstance(value, bytes) else (json.dumps(value, indent=2) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def append_unique(values: list[Any], value: Any) -> None:
    if value not in values:
        values.append(value)


def run_validator(path: Path, label: str) -> None:
    enforce_runtime_authorities()
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"canonical {label} validation failed: {completed.stdout[-2000:]}",
    )


def validate_current_authority() -> None:
    enforce_runtime_authorities()
    for path, label in (
        (DEPENDENCY_VALIDATOR, "production-equivalent dependency"),
        (LOAD_INDEX_VALIDATOR, "load evidence index"),
        (LOAD_VALIDATOR, "load"),
        (OPERABILITY_VALIDATOR, "operability"),
    ):
        run_validator(path, label)


def write_and_validate_transactionally(
    load_contract: dict[str, Any],
    status: dict[str, Any],
) -> None:
    enforce_runtime_authorities()
    originals = {
        LOAD_PATH: LOAD_PATH.read_bytes(),
        STATUS_PATH: STATUS_PATH.read_bytes(),
    }
    try:
        atomic_write(LOAD_PATH, load_contract)
        atomic_write(STATUS_PATH, status)
        validate_current_authority()
    except Exception:
        for path, data in originals.items():
            atomic_write(path, data)
        raise


def main() -> int:
    enforce_runtime_authorities()
    admission = load(CONTRACT_PATH)
    readiness = admission.get("readiness")
    require(isinstance(readiness, dict), "admission readiness missing")
    require(readiness.get("contractDefined") is True, "admission contract not defined")
    require(readiness.get("validatorImplemented") is True, "admission validator not implemented")
    require(readiness.get("automaticValidationImplemented") is True, "admission automatic validation not implemented")
    require(readiness.get("environmentProvisioned") is False, "foundation reconciliation refuses provisioned environment claims")
    require(readiness.get("productionEquivalentDependencies") is False, "foundation cannot be production-equivalent evidence")
    require(readiness.get("productionReady") is False, "foundation cannot be production ready")

    load_contract = load(LOAD_PATH)
    load_readiness = load_contract.get("readiness")
    load_refs = load_contract.get("evidenceRefs")
    require(isinstance(load_readiness, dict), "load readiness missing")
    require(isinstance(load_refs, list), "load evidenceRefs missing")
    require(load_readiness.get("productionEquivalentDependencies") is False, "load contract already overclaims production equivalence")
    load_readiness["productionEquivalentAdmissionContractDefined"] = True
    load_readiness["productionEquivalentEnvironmentProvisioned"] = False
    for ref in FOUNDATION_REFS:
        append_unique(load_refs, ref)

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO", "foundation reconciliation requires Production NO_GO")
    areas = status.get("areas")
    require(isinstance(areas, list), "operability areas missing")
    load_area = next((area for area in areas if isinstance(area, dict) and area.get("id") == "OPS-P0-006"), None)
    require(isinstance(load_area, dict), "OPS-P0-006 missing")
    require(load_area.get("status") == "PARTIAL", "foundation cannot change OPS-P0-006 status")
    existing = load_area.get("existingEvidence")
    missing = load_area.get("missingEvidence")
    refs = load_area.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-006 evidence structure invalid")
    append_unique(
        existing,
        "fail-closed production-equivalent dependency admission contract now requires TLS, scoped non-production credentials, PostgreSQL role/RLS and connection budgets, object lifecycle, queue/backpressure, failure behavior, restore linkage, a material-delta ledger and independent review before any environment can be called production-equivalent",
    )
    require(any("production-equivalent" in item for item in missing if isinstance(item, str)), "production-equivalent execution gap must remain explicit")
    for ref in FOUNDATION_REFS:
        append_unique(refs, ref)

    require(load_readiness.get("productionEquivalentDependencies") is False, "production-equivalent evidence drift")
    require(status.get("productionDecision") == "NO_GO", "production decision drift")
    require(load_area.get("status") == "PARTIAL", "OPS-P0-006 status drift")

    proposed_load = (json.dumps(load_contract, indent=2) + "\n").encode("utf-8")
    proposed_status = (json.dumps(status, indent=2) + "\n").encode("utf-8")
    if LOAD_PATH.read_bytes() == proposed_load and STATUS_PATH.read_bytes() == proposed_status:
        validate_current_authority()
    else:
        write_and_validate_transactionally(load_contract, status)
    print("Memory OS production-equivalent admission foundation reconciled")
    print("environment provisioned: false")
    print("production-equivalent dependencies: false")
    print("OPS-P0-006: PARTIAL")
    print("Production: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT FOUNDATION RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
