#!/usr/bin/env python3
"""Register the production-equivalent admission foundation without promoting execution evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/production-equivalent-dependency-contract.v1.json"
LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
DEPENDENCY_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-dependencies.py"
LOAD_INDEX_VALIDATOR = ROOT / "scripts/validate-memory-os-load-evidence-index.py"
LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"

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


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def append_unique(values: list[Any], value: Any) -> None:
    if value not in values:
        values.append(value)


def run_validator(path: Path, label: str) -> None:
    require(path.is_file(), f"canonical {label} validator missing")
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
    originals = {
        LOAD_PATH: LOAD_PATH.read_bytes(),
        STATUS_PATH: STATUS_PATH.read_bytes(),
    }
    try:
        write(LOAD_PATH, load_contract)
        write(STATUS_PATH, status)
        validate_current_authority()
    except Exception:
        for path, data in originals.items():
            path.write_bytes(data)
        raise


def main() -> int:
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
