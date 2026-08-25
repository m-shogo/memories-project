#!/usr/bin/env python3
"""Reconcile exact-source multi-account deletion-worker saturation evidence into its local-only contract."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/deletion-worker-saturation-contract.v1.json"
CANONICAL_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-saturation-results.sample.v1.json"
CANONICAL_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-deletion-worker-saturation.py"
CANONICAL_SPEC_FROM_FILE_LOCATION = importlib.util.spec_from_file_location
CANONICAL_MODULE_FROM_SPEC = importlib.util.module_from_spec
CANONICAL_OS_REPLACE = os.replace
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
VALIDATOR_PATH = CANONICAL_VALIDATOR_PATH
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_authority(path: Path, canonical: Path, label: str, *, must_exist: bool = True) -> None:
    require(path == canonical, f"{label} authority drift")
    require(not canonical.is_symlink(), f"canonical {label} must not be a symlink")
    if not canonical.exists():
        require(not must_exist, f"canonical {label} missing")
        return
    try:
        resolved = canonical.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"canonical {label} missing or escapes repository") from exc
    require(resolved == canonical.relative_to(ROOT), f"canonical {label} path drift")
    require(canonical.is_file(), f"canonical {label} must be regular file")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


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


CANONICAL_ATOMIC_WRITE_BYTES = atomic_write_bytes


def load_validator():
    enforce_runtime_authorities()
    spec = importlib.util.spec_from_file_location("memory_os_deletion_worker_saturation_validator", VALIDATOR_PATH)
    require(spec is not None and spec.loader is not None, "cannot load canonical deletion-worker saturation validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(callable(getattr(module, "validate_contract", None)), "canonical deletion-worker saturation validator missing validate_contract")
    require(callable(getattr(module, "validate_result", None)), "canonical deletion-worker saturation validator missing validate_result")
    return module


CANONICAL_LOAD_VALIDATOR = load_validator


def validate_canonical(validator, contract: dict[str, Any], expected: str) -> None:
    try:
        validator.validate_contract(contract)
        validator.validate_result(contract, expected)
    except RuntimeError as exc:
        if exc.__class__.__name__ == "Fail":
            raise Fail(f"canonical deletion-worker saturation authority invalid: {exc}") from exc
        raise


CANONICAL_VALIDATE_CANONICAL = validate_canonical


def enforce_runtime_authorities() -> None:
    require_exact_authority(CONTRACT_PATH, CANONICAL_CONTRACT_PATH, "deletion-worker saturation contract")
    require_exact_authority(
        RESULT_PATH,
        CANONICAL_RESULT_PATH,
        "deletion-worker saturation result",
        must_exist=False,
    )
    require_exact_authority(VALIDATOR_PATH, CANONICAL_VALIDATOR_PATH, "deletion-worker saturation validator")
    require(importlib.util.spec_from_file_location is CANONICAL_SPEC_FROM_FILE_LOCATION, "validator spec loader transport is not canonical")
    require(importlib.util.module_from_spec is CANONICAL_MODULE_FROM_SPEC, "validator module loader transport is not canonical")
    require(os.replace is CANONICAL_OS_REPLACE, "atomic replacement transport is not canonical")
    require(atomic_write_bytes is CANONICAL_ATOMIC_WRITE_BYTES, "atomic writer authority is not canonical")
    require(load_validator is CANONICAL_LOAD_VALIDATOR, "validator loader authority is not canonical")
    require(validate_canonical is CANONICAL_VALIDATE_CANONICAL, "validator execution authority is not canonical")


def main() -> int:
    enforce_runtime_authorities()
    expected = os.getenv("EXPECTED_COMMIT_SHA", "")
    require(SHA_RE.fullmatch(expected) is not None, "EXPECTED_COMMIT_SHA must be full SHA")
    validator = load_validator()
    contract = load(CONTRACT_PATH)
    validate_canonical(validator, contract, expected)

    original_contract = CONTRACT_PATH.read_bytes()
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["exactSourceResultCommitted"] = True
    readiness["multiAccountWorkerSaturationProven"] = True
    readiness["productionDependenciesTested"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    for key in (
        "productionEvidence",
        "productionEquivalentDependencies",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "hostFailureCovered",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"local proof cannot enable {key}")

    payload = (json.dumps(contract, indent=2) + "\n").encode("utf-8")
    try:
        enforce_runtime_authorities()
        atomic_write_bytes(CONTRACT_PATH, payload)
        enforce_runtime_authorities()
        validate_canonical(validator, load(CONTRACT_PATH), expected)
    except Exception:
        atomic_write_bytes(CONTRACT_PATH, original_contract)
        raise

    print("Memory OS deletion-worker saturation authority reconciled")
    print("multi-account worker saturation proven: true")
    print("capacity boundary established: false")
    print("production dependencies tested: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"DELETION WORKER SATURATION RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
