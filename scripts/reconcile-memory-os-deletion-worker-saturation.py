#!/usr/bin/env python3
"""Reconcile exact-source multi-account deletion-worker saturation evidence into its local-only contract."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-worker-saturation-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-saturation-results.sample.v1.json"
VALIDATOR_PATH = ROOT / "scripts" / "validate-memory-os-deletion-worker-saturation.py"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_validator():
    try:
        resolved = VALIDATOR_PATH.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail("canonical deletion-worker saturation validator missing or escapes repository") from exc
    require(
        resolved == Path("scripts") / VALIDATOR_PATH.name and VALIDATOR_PATH.is_file(),
        "canonical deletion-worker saturation validator path drift",
    )
    spec = importlib.util.spec_from_file_location("memory_os_deletion_worker_saturation_validator", VALIDATOR_PATH)
    require(spec is not None and spec.loader is not None, "cannot load canonical deletion-worker saturation validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(callable(getattr(module, "validate_contract", None)), "canonical deletion-worker saturation validator missing validate_contract")
    require(callable(getattr(module, "validate_result", None)), "canonical deletion-worker saturation validator missing validate_result")
    return module


def validate_canonical(validator, contract: dict[str, Any], expected: str) -> None:
    try:
        validator.validate_contract(contract)
        validator.validate_result(contract, expected)
    except RuntimeError as exc:
        if exc.__class__.__name__ == "Fail":
            raise Fail(f"canonical deletion-worker saturation authority invalid: {exc}") from exc
        raise


def main() -> int:
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

    try:
        CONTRACT_PATH.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
        validate_canonical(validator, load(CONTRACT_PATH), expected)
    except Exception:
        CONTRACT_PATH.write_bytes(original_contract)
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
