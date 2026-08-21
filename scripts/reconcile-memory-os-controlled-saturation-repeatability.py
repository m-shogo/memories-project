#!/usr/bin/env python3
"""Reconcile repeatable local degradation evidence without approving capacity thresholds."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT = ROOT / "contracts/operations/controlled-saturation-repeatability-contract.v1.json"
CANONICAL_RESULT = ROOT / "docs/fixtures/memory-os-operability/controlled-saturation-repeatability-results.v1.json"
CANONICAL_VALIDATOR = ROOT / "scripts/validate-memory-os-controlled-saturation-repeatability.py"
CANONICAL_LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CANONICAL_LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CANONICAL_STATUS = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_WORKFLOW = ROOT / ".github/workflows/controlled-saturation-repeatability.yml"
CONTRACT = CANONICAL_CONTRACT
RESULT = CANONICAL_RESULT
VALIDATOR = CANONICAL_VALIDATOR
LOAD_VALIDATOR = CANONICAL_LOAD_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
LOAD = CANONICAL_LOAD
STATUS = CANONICAL_STATUS
WORKFLOW = CANONICAL_WORKFLOW
TRANSACTION_PATHS = (CONTRACT, LOAD, STATUS)

EVIDENCE = (
    "two-run local controlled-saturation repeatability authority classifies a throughput/latency degradation knee or actual failure signal on independent PostgreSQL+MinIO runners; even a repeatable local signal remains non-production and cannot itself establish a capacity boundary or approve an operating threshold"
)
REFS = (
    "contracts/operations/controlled-saturation-repeatability-contract.v1.json",
    "scripts/analyze-memory-os-controlled-saturation-repeatability.py",
    "scripts/validate-memory-os-controlled-saturation-repeatability.py",
    "scripts/reconcile-memory-os-controlled-saturation-repeatability.py",
    ".github/workflows/controlled-saturation-repeatability.yml",
    "docs/fixtures/memory-os-operability/controlled-saturation-repeatability-results.v1.json",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")


def enforce_runtime_authorities() -> None:
    for path, canonical, label in (
        (CONTRACT, CANONICAL_CONTRACT, "repeatability contract"),
        (RESULT, CANONICAL_RESULT, "repeatability result"),
        (VALIDATOR, CANONICAL_VALIDATOR, "repeatability validator"),
        (LOAD_VALIDATOR, CANONICAL_LOAD_VALIDATOR, "load validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
        (LOAD, CANONICAL_LOAD, "load contract"),
        (STATUS, CANONICAL_STATUS, "production status"),
        (WORKFLOW, CANONICAL_WORKFLOW, "repeatability workflow"),
    ):
        require_exact_authority(path, canonical, label)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def run_post_write_validators() -> None:
    enforce_runtime_authorities()
    for validator in (VALIDATOR, LOAD_VALIDATOR, OPERABILITY_VALIDATOR):
        subprocess.run([sys.executable, str(validator)], cwd=ROOT, check=True)


def write_transactionally(contract: dict[str, Any], load_contract: dict[str, Any], status: dict[str, Any]) -> None:
    enforce_runtime_authorities()
    originals = {path: path.read_bytes() for path in TRANSACTION_PATHS}
    try:
        write(CONTRACT, contract)
        write(LOAD, load_contract)
        write(STATUS, status)
        run_post_write_validators()
    except BaseException:
        for path, content in originals.items():
            path.write_bytes(content)
        raise


def main() -> int:
    enforce_runtime_authorities()
    subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, check=True)
    result = load(RESULT)
    repeatable = result.get("repeatableLocalDegradationSignalObserved") is True

    contract = load(CONTRACT)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "repeatability readiness missing")
    readiness["analyzerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = WORKFLOW.is_file()
    readiness["independentRunCount"] = 2
    readiness["repeatableLocalDegradationSignalObserved"] = repeatable
    readiness["capacityBoundaryEstablished"] = False
    readiness["operationalThresholdApproved"] = False
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    load_contract = load(LOAD)
    load_readiness = load_contract.get("readiness")
    require(isinstance(load_readiness, dict), "load readiness missing")
    load_readiness["repeatableLocalDegradationSignalObserved"] = repeatable
    load_readiness["capacityBoundaryEstablished"] = False
    load_readiness["operationalThresholds"] = False
    refs = load_contract.get("evidenceRefs")
    require(isinstance(refs, list), "load evidenceRefs missing")
    for ref in REFS:
        append_once(refs, ref)

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-006"), None)
    require(isinstance(gate, dict), "OPS-P0-006 missing")
    require(str(gate.get("status")).startswith("PARTIAL"), "OPS-P0-006 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    gate_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(gate_refs, list), "OPS-P0-006 arrays missing")
    append_once(existing, EVIDENCE)
    for ref in REFS:
        append_once(gate_refs, ref)
    if repeatable:
        rewritten: list[Any] = []
        for item in missing:
            text = str(item)
            if "repeatable saturation transition" in text.lower():
                replacement = "production-shaped capacity boundary plus independently reviewed safe operating thresholds derived from admitted repeated evidence"
                if replacement not in rewritten:
                    rewritten.append(replacement)
            elif item not in rewritten:
                rewritten.append(item)
        gate["missingEvidence"] = rewritten

    write_transactionally(contract, load_contract, status)

    print("Memory OS controlled saturation repeatability reconciliation PASS")
    print(f"repeatable local degradation signal: {repeatable}")
    print("capacity boundary established: false")
    print("operational threshold approved: false")
    print("OPS-P0-006: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"CONTROLLED SATURATION REPEATABILITY RECONCILE FAILED: {exc}")
        raise SystemExit(1)
