#!/usr/bin/env python3
"""Register physical host/node deletion-failure admission without claiming execution."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CANONICAL_ROOT = Path(__file__).resolve().parents[1]
ROOT = CANONICAL_ROOT
CANONICAL_CONTRACT = CANONICAL_ROOT / "contracts/operations/deletion-worker-host-failure-contract.v1.json"
CANONICAL_HOST_VALIDATOR = CANONICAL_ROOT / "scripts/validate-memory-os-deletion-worker-host-failure.py"
CANONICAL_LOAD_VALIDATOR = CANONICAL_ROOT / "scripts/validate-memory-os-load.py"
CANONICAL_OPERABILITY_VALIDATOR = CANONICAL_ROOT / "scripts/validate-memory-os-operability.py"
CANONICAL_WORKFLOW = CANONICAL_ROOT / ".github/workflows/deletion-worker-host-failure-admission.yml"
CANONICAL_STATUS = CANONICAL_ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_LOAD = CANONICAL_ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CANONICAL_SUBPROCESS_RUN = subprocess.run
CANONICAL_OS_REPLACE = os.replace
CANONICAL_SPEC_FROM_FILE_LOCATION = importlib.util.spec_from_file_location
CANONICAL_MODULE_FROM_SPEC = importlib.util.module_from_spec
CONTRACT = CANONICAL_CONTRACT
VALIDATOR = CANONICAL_HOST_VALIDATOR
LOAD_VALIDATOR = CANONICAL_LOAD_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
WORKFLOW = CANONICAL_WORKFLOW
STATUS = CANONICAL_STATUS
LOAD = CANONICAL_LOAD

EVIDENCE = (
    "physical host/node deletion-worker failure admission is now fail-closed: actual process SIGKILL and Docker container kill remain local evidence only; "
    "host/node proof requires a registered production-equivalent environment generation, an external failure controller outside the target node, a replacement "
    "worker on a distinct node, lease exclusion until expiry, attempt-2 reclaim, dependency reconnect, zero-row/object convergence and independent review"
)
REFS = (
    "contracts/operations/deletion-worker-host-failure-contract.v1.json",
    "scripts/validate-memory-os-deletion-worker-host-failure.py",
    "scripts/reconcile-memory-os-deletion-worker-host-failure.py",
    ".github/workflows/deletion-worker-host-failure-admission.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")
    require(canonical.resolve(strict=True) == canonical, f"canonical {label} resolved path drift")


def validate_data_authorities(
    _root: Path = CANONICAL_ROOT,
    _contract: Path = CANONICAL_CONTRACT,
    _workflow: Path = CANONICAL_WORKFLOW,
    _status: Path = CANONICAL_STATUS,
    _load: Path = CANONICAL_LOAD,
) -> None:
    require(CANONICAL_ROOT == _root and ROOT == _root, "repository root authority drift")
    require(Path(__file__).resolve().parents[1] == _root, "canonical repository root drift")
    for path, canonical, expected, label in (
        (CONTRACT, CANONICAL_CONTRACT, _contract, "host-failure contract"),
        (WORKFLOW, CANONICAL_WORKFLOW, _workflow, "host-failure workflow"),
        (STATUS, CANONICAL_STATUS, _status, "production status"),
        (LOAD, CANONICAL_LOAD, _load, "load contract"),
    ):
        require(canonical == expected, f"canonical {label} constant drift")
        require_exact_authority(path, expected, label)


def validate_executable_authorities(
    _host_validator: Path = CANONICAL_HOST_VALIDATOR,
    _load_validator: Path = CANONICAL_LOAD_VALIDATOR,
    _operability_validator: Path = CANONICAL_OPERABILITY_VALIDATOR,
    _subprocess_run: Any = CANONICAL_SUBPROCESS_RUN,
    _os_replace: Any = CANONICAL_OS_REPLACE,
    _spec_from_file_location: Any = CANONICAL_SPEC_FROM_FILE_LOCATION,
    _module_from_spec: Any = CANONICAL_MODULE_FROM_SPEC,
) -> None:
    validate_data_authorities()
    for path, canonical, expected, label in (
        (VALIDATOR, CANONICAL_HOST_VALIDATOR, _host_validator, "host-failure validator"),
        (LOAD_VALIDATOR, CANONICAL_LOAD_VALIDATOR, _load_validator, "load validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, _operability_validator, "operability validator"),
    ):
        require(canonical == expected, f"canonical {label} constant drift")
        require_exact_authority(path, expected, label)
    require(CANONICAL_SUBPROCESS_RUN is _subprocess_run and subprocess.run is _subprocess_run,
            "host-failure subprocess transport is not canonical")
    require(CANONICAL_OS_REPLACE is _os_replace and os.replace is _os_replace,
            "host-failure atomic replacement transport is not canonical")
    require(CANONICAL_SPEC_FROM_FILE_LOCATION is _spec_from_file_location and
            importlib.util.spec_from_file_location is _spec_from_file_location,
            "host-failure module spec loader is not canonical")
    require(CANONICAL_MODULE_FROM_SPEC is _module_from_spec and
            importlib.util.module_from_spec is _module_from_spec,
            "host-failure module loader is not canonical")


def load_host_validator(
    _spec_from_file_location: Any = CANONICAL_SPEC_FROM_FILE_LOCATION,
    _module_from_spec: Any = CANONICAL_MODULE_FROM_SPEC,
):
    validate_executable_authorities()
    try:
        resolved = VALIDATOR.resolve(strict=True).relative_to(CANONICAL_ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail("canonical host-failure validator missing or escapes repository") from exc
    require(resolved == CANONICAL_HOST_VALIDATOR.relative_to(CANONICAL_ROOT), "host-failure validator authority drift")
    require(importlib.util.spec_from_file_location is _spec_from_file_location,
            "host-failure module spec loader is not canonical")
    require(importlib.util.module_from_spec is _module_from_spec,
            "host-failure module loader is not canonical")
    spec = _spec_from_file_location("memory_os_host_failure_validator_for_reconcile", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load canonical host-failure validator")
    module = _module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - convert dependency failures into domain failure
        raise Fail(f"cannot load canonical host-failure validator: {exc}") from exc
    require(callable(getattr(module, "canonical_generation_count", None)), "host-failure generation authority helper missing")
    require(callable(getattr(module, "validate_generation_projection", None)), "host-failure generation projection validator missing")
    require(isinstance(getattr(module, "NO_GENERATION_LIMITATION", None), str), "host-failure generation limitation authority missing")
    return module


def reconcile_generation_projection(contract: dict[str, Any]) -> int:
    host_validator = load_host_validator()
    try:
        registered = host_validator.canonical_generation_count()
    except Exception as exc:  # noqa: BLE001 - shared authority must fail closed
        raise Fail(f"canonical generation authority validation failed: {exc}") from exc

    generation_available = registered > 0
    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    limitations = contract.get("limitations")
    require(isinstance(boundary, dict), "host-failure currentBoundary missing")
    require(isinstance(readiness, dict), "host-failure readiness missing")
    require(isinstance(limitations, list) and all(isinstance(item, str) for item in limitations), "host-failure limitations missing")

    boundary["environmentGenerationAvailable"] = generation_available
    readiness["environmentGenerationAvailable"] = generation_available
    no_generation_limitation = host_validator.NO_GENERATION_LIMITATION
    if generation_available:
        contract["limitations"] = [item for item in limitations if item != no_generation_limitation]
    elif no_generation_limitation not in limitations:
        limitations.insert(0, no_generation_limitation)

    try:
        host_validator.validate_generation_projection(contract, registered)
    except Exception as exc:  # noqa: BLE001 - projection must match shared validator
        raise Fail(f"host-failure generation projection invalid: {exc}") from exc
    return registered


def validate_load_authority() -> None:
    validate_executable_authorities()
    try:
        CANONICAL_SUBPROCESS_RUN([sys.executable, str(LOAD_VALIDATOR)], cwd=CANONICAL_ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        raise Fail(f"canonical load authority validation failed: {exc}") from exc


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    existing_mode = (path.stat().st_mode & 0o777) if path.exists() else None
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if existing_mode is not None:
            os.chmod(temporary_path, existing_mode)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


CANONICAL_ATOMIC_WRITE_BYTES = atomic_write_bytes


def validate_atomic_writer_authority(_writer: Any = atomic_write_bytes) -> None:
    require(CANONICAL_ATOMIC_WRITE_BYTES is _writer and atomic_write_bytes is _writer,
            "host-failure atomic writer is not canonical")


def write_transactionally(contract: dict[str, Any], status: dict[str, Any]) -> None:
    validate_executable_authorities()
    validate_atomic_writer_authority()
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    try:
        CANONICAL_ATOMIC_WRITE_BYTES(CONTRACT, (json.dumps(contract, indent=2) + "\n").encode("utf-8"))
        CANONICAL_ATOMIC_WRITE_BYTES(STATUS, (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        validate_executable_authorities()
        validate_atomic_writer_authority()
        CANONICAL_SUBPROCESS_RUN([sys.executable, str(VALIDATOR)], cwd=CANONICAL_ROOT, check=True)
        CANONICAL_SUBPROCESS_RUN([sys.executable, str(LOAD_VALIDATOR)], cwd=CANONICAL_ROOT, check=True)
        CANONICAL_SUBPROCESS_RUN([sys.executable, str(OPERABILITY_VALIDATOR)], cwd=CANONICAL_ROOT, check=True)
    except Exception as exc:
        CANONICAL_ATOMIC_WRITE_BYTES(CONTRACT, contract_bytes)
        CANONICAL_ATOMIC_WRITE_BYTES(STATUS, status_bytes)
        if isinstance(exc, Fail):
            raise
        raise Fail(f"host-failure post-write authority validation failed: {exc}") from exc


def main() -> int:
    validate_executable_authorities()
    validate_atomic_writer_authority()
    validate_load_authority()

    contract = load(CONTRACT)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "host-failure readiness missing")
    require(readiness.get("contractDefined") is True and readiness.get("validatorImplemented") is True, "host-failure foundation incomplete")
    if WORKFLOW.is_file():
        readiness["automaticWorkflowImplemented"] = True
    registered = reconcile_generation_projection(contract)

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    for gate_id in ("OPS-P0-006", "OPS-P0-009"):
        gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == gate_id), None)
        require(isinstance(gate, dict), f"{gate_id} missing")
        require(str(gate.get("status")).startswith("PARTIAL"), f"{gate_id} must remain PARTIAL")
        existing = gate.get("existingEvidence")
        missing = gate.get("missingEvidence")
        refs = gate.get("evidenceRefs")
        require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), f"{gate_id} authority arrays missing")
        append_once(existing, EVIDENCE)
        for ref in REFS:
            require((CANONICAL_ROOT / ref).is_file(), f"host-failure evidence ref missing: {ref}")
            append_once(refs, ref)
        joined = "\n".join(str(item).lower() for item in missing)
        require("host" in joined or "node" in joined, f"{gate_id} must retain physical host/node blocker")

    load_contract = load(LOAD)
    readiness_load = load_contract.get("readiness")
    require(isinstance(readiness_load, dict), "load readiness missing")
    require(readiness_load.get("deletionContainerKillRecoveryProven") is True, "container recovery must remain proven")
    require(readiness_load.get("deletionHostFailureRecoveryProven") is False, "host recovery cannot be promoted by admission foundation")

    write_transactionally(contract, status)
    print("Memory OS deletion-worker host-failure admission reconciliation PASS")
    print("container recovery: proven locally")
    print(f"registered production-equivalent generations: {registered}")
    print("physical host/node recovery: unexecuted")
    print("OPS-P0-006/009: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION HOST FAILURE RECONCILE FAILED: {exc}")
        raise SystemExit(1)
