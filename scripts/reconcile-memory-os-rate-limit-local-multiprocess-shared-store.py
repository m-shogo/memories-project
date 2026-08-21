#!/usr/bin/env python3
"""Reconcile local multi-process shared-store rehearsal without promoting distributed runtime admission."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/rate-limit-local-multiprocess-shared-store-contract.v1.json"
RESULT = ROOT / "docs/fixtures/memory-os-operability/rate-limit-local-multiprocess-shared-store-results.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store.py"
RATE_LIMIT_OPERATIONS_VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-operations.py"
RATE_LIMIT_VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
REFS = (
    "contracts/operations/rate-limit-local-multiprocess-shared-store-contract.v1.json",
    "services/import-api/internal/ratelimit/shared_store_multiprocess_test.go",
    "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store.py",
    "scripts/reconcile-memory-os-rate-limit-local-multiprocess-shared-store.py",
    ".github/workflows/rate-limit-local-multiprocess-shared-store.yml",
)
EVIDENCE_PREFIX = "exact-source local multi-process rate-limit shared-store rehearsal"


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


def validate_runtime_authority() -> None:
    for path, expected, label in (
        (VALIDATOR, ROOT / "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store.py", "local shared-store validator"),
        (RATE_LIMIT_OPERATIONS_VALIDATOR, ROOT / "scripts/validate-memory-os-rate-limit-operations.py", "rate-limit operations validator"),
        (RATE_LIMIT_VALIDATOR, ROOT / "scripts/validate-memory-os-rate-limit.py", "rate-limit validator"),
        (OPERABILITY_VALIDATOR, ROOT / "scripts/validate-memory-os-operability.py", "operability validator"),
    ):
        require(path == expected, f"canonical {label} identity drift")
        require(path.is_file(), f"canonical {label} missing")
        require(not path.is_symlink(), f"canonical {label} must not be a symlink")
        try:
            require(path.resolve(strict=True) == expected, f"canonical {label} path drift")
        except OSError as exc:
            raise Fail(f"cannot resolve canonical {label}") from exc


def run_validator(path: Path) -> None:
    completed = subprocess.run([sys.executable, str(path)], cwd=ROOT, check=False)
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"canonical validator rejected local shared-store authority: {path.name}")


def normalized_contract(current: dict[str, Any], result_present: bool) -> dict[str, Any]:
    contract = copy.deepcopy(current)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    runner = contract.get("runner")
    workflow = contract.get("workflow")
    require(isinstance(runner, str) and runner, "runner authority missing")
    require(isinstance(workflow, str) and workflow, "workflow authority missing")
    readiness["contractDefined"] = True
    readiness["runnerImplemented"] = (ROOT / runner).is_file()
    readiness["validatorImplemented"] = VALIDATOR.is_file()
    readiness["automaticWorkflowImplemented"] = (ROOT / workflow).is_file()
    readiness["exactSourcePassCommitted"] = result_present
    readiness["localCrossProcessStoreSemanticsProven"] = result_present
    readiness["distributedSharedStoreImplemented"] = False
    readiness["productionEquivalentRuntimeEvidence"] = False
    readiness["productionReady"] = False
    return contract


def normalized_status(current: dict[str, Any], result_present: bool) -> dict[str, Any]:
    status = copy.deepcopy(current)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-005"), None)
    require(isinstance(gate, dict), "OPS-P0-005 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True,
            "OPS-P0-005 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list),
            "OPS-P0-005 authority arrays missing")
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    if result_present:
        append_once(existing, (
            EVIDENCE_PREFIX + " proves two independent OS test clients consume one atomic shared budget through the canonical Store interface, a fresh client process cannot reset exhausted backend state, and a loopback shared-store outage maps to fail-closed store_unavailable; the broker is test-only MemoryStore-backed HTTP, so this is not a distributed production store, runtime-host restart, TLS/trusted-proxy deployment or production-equivalent evidence"
        ))
    else:
        append_once(existing, (
            EVIDENCE_PREFIX + " foundation is implemented but no exact-source PASS result is committed yet; no distributed-runtime claim is created"
        ))
    for ref in REFS:
        require((ROOT / ref).is_file(), f"local shared-store evidence ref missing: {ref}")
        append_once(refs, ref)
    if result_present:
        append_once(refs, str(RESULT.relative_to(ROOT)))

    joined = "\n".join(str(item).lower() for item in missing)
    for phrase in (
        "production-equivalent distributed enforcement",
        "trusted-proxy configuration",
        "load-calibrated limits",
        "completed emergency-mode",
        "production emergency control plane",
    ):
        require(phrase in joined, f"OPS-P0-005 production blocker must remain: {phrase}")
    require(status.get("productionDecision") == "NO_GO", "productionDecision changed unexpectedly")
    return status


def main() -> int:
    validate_runtime_authority()
    result_present = RESULT.is_file()
    contract = normalized_contract(load(CONTRACT), result_present)
    status = normalized_status(load(STATUS), result_present)

    original_contract = CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        for validator in (
            VALIDATOR,
            RATE_LIMIT_OPERATIONS_VALIDATOR,
            RATE_LIMIT_VALIDATOR,
            OPERABILITY_VALIDATOR,
        ):
            run_validator(validator)
    except Exception:
        CONTRACT.write_bytes(original_contract)
        STATUS.write_bytes(original_status)
        raise

    print("Memory OS local multi-process shared-store reconciliation PASS")
    print(f"exact-source result committed: {str(result_present).lower()}")
    print(f"local cross-process store semantics proven: {str(result_present).lower()}")
    print("distributed shared store implemented: false")
    print("production-equivalent runtime evidence: false")
    print("OPS-P0-005: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RATE LIMIT LOCAL MULTIPROCESS SHARED STORE RECONCILE FAILED: {exc}")
        raise SystemExit(1)
