#!/usr/bin/env python3
"""Mark evidence-ownership validation infrastructure implemented after validation."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT = ROOT / "contracts/operations/operability-evidence-ownership-contract.v1.json"
CANONICAL_VALIDATOR = ROOT / "scripts/validate-memory-os-operability-evidence-ownership.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CANONICAL_WORKFLOW = ROOT / ".github/workflows/operability-evidence-ownership.yml"

CONTRACT = CANONICAL_CONTRACT
VALIDATOR = CANONICAL_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
WORKFLOW = CANONICAL_WORKFLOW


class ReconcileFailure(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconcileFailure(f"cannot read ownership authority: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReconcileFailure(f"root must be object: {path.relative_to(ROOT)}")
    return value


def require_runtime_authority(candidate: Path, expected: Path, label: str) -> None:
    root = ROOT.resolve(strict=True)
    if candidate != expected:
        raise ReconcileFailure(f"{label} authority drift: expected {expected.relative_to(ROOT)}, got {candidate}")
    if candidate.is_symlink():
        raise ReconcileFailure(f"{label} authority must not be a symlink: {candidate.relative_to(ROOT)}")
    try:
        resolved = candidate.resolve(strict=True)
        expected_resolved = expected.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ReconcileFailure(f"{label} authority missing or escapes repository: {candidate}") from exc
    if resolved != expected_resolved:
        raise ReconcileFailure(f"{label} authority drift after resolution: {candidate.relative_to(ROOT)}")


def enforce_runtime_authorities() -> None:
    require_runtime_authority(CONTRACT, CANONICAL_CONTRACT, "ownership contract")
    require_runtime_authority(VALIDATOR, CANONICAL_VALIDATOR, "ownership validator")
    require_runtime_authority(
        OPERABILITY_VALIDATOR,
        CANONICAL_OPERABILITY_VALIDATOR,
        "operability validator",
    )
    require_runtime_authority(WORKFLOW, CANONICAL_WORKFLOW, "ownership workflow")


def run_validator(path: Path, label: str) -> None:
    enforce_runtime_authorities()
    try:
        subprocess.run(["python", str(path)], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        raise ReconcileFailure(f"{label} rejected ownership authority") from exc


def validate_written_authority() -> None:
    enforce_runtime_authorities()
    run_validator(VALIDATOR, "ownership validator")
    run_validator(OPERABILITY_VALIDATOR, "aggregate operability validator")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def transactional_write(contract: dict[str, Any]) -> None:
    enforce_runtime_authorities()
    original = CONTRACT.read_bytes()
    proposed = (json.dumps(contract, indent=2) + "\n").encode("utf-8")
    try:
        atomic_write(CONTRACT, proposed)
        validate_written_authority()
    except Exception:
        atomic_write(CONTRACT, original)
        raise


def main() -> int:
    enforce_runtime_authorities()
    run_validator(VALIDATOR, "ownership validator")
    contract = load(CONTRACT)
    readiness = contract.get("readiness")
    if not isinstance(readiness, dict):
        raise ReconcileFailure("ownership readiness missing")
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["productionReady"] = False
    if contract.get("productionDecision") != "NO_GO":
        raise ReconcileFailure("ownership contract cannot change production decision")

    proposed = (json.dumps(contract, indent=2) + "\n").encode("utf-8")
    if CONTRACT.read_bytes() == proposed:
        validate_written_authority()
    else:
        transactional_write(contract)

    print("Memory OS operability evidence ownership readiness reconciliation PASS")
    print("validator implemented: true")
    print("automatic workflow implemented: true")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"OPERABILITY EVIDENCE OWNERSHIP RECONCILE FAILED: {exc}")
        raise SystemExit(1)
