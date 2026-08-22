#!/usr/bin/env python3
"""Reconcile observability-stack deployment admission without inventing deployment evidence."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/observability-stack-deployment-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/observability-stack-deployment-registry.v1.json")
WRITER_REL = Path("scripts/register-memory-os-observability-stack-deployment.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-observability-stack-deployment.py")
OBSERVABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-observability.py")
ACCESS_VALIDATOR_REL = Path("scripts/validate-memory-os-observability-access.py")
METRICS_VALIDATOR_REL = Path("scripts/validate-memory-os-metrics.py")
METRICS_OPERATIONS_VALIDATOR_REL = Path("scripts/validate-memory-os-metrics-operations.py")
METRICS_ALERTING_VALIDATOR_REL = Path("scripts/validate-memory-os-metrics-alerting.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
WORKFLOW_REL = Path(".github/workflows/observability-stack-deployment.yml")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
WRITER = ROOT / WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL
OBSERVABILITY_VALIDATOR = ROOT / OBSERVABILITY_VALIDATOR_REL
ACCESS_VALIDATOR = ROOT / ACCESS_VALIDATOR_REL
METRICS_VALIDATOR = ROOT / METRICS_VALIDATOR_REL
METRICS_OPERATIONS_VALIDATOR = ROOT / METRICS_OPERATIONS_VALIDATOR_REL
METRICS_ALERTING_VALIDATOR = ROOT / METRICS_ALERTING_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
POST_WRITE_VALIDATORS = (
    VALIDATOR,
    OBSERVABILITY_VALIDATOR,
    ACCESS_VALIDATOR,
    METRICS_VALIDATOR,
    METRICS_OPERATIONS_VALIDATOR,
    METRICS_ALERTING_VALIDATOR,
    OPERABILITY_VALIDATOR,
)
WORKFLOW = ROOT / WORKFLOW_REL
STATUS = ROOT / STATUS_REL

EVIDENCE = (
    "integrated observability-stack deployment admission is fail-closed: a future record must jointly prove structured-log backend health and retention deletion, identity-group/access-audit controls, metrics scrape/backend/dashboard wiring, paging ownership/delivery/response drills and independent security/operability review; the registry is currently empty and creates no deployment claim"
)
REFS = (
    "contracts/operations/observability-stack-deployment-contract.v1.json",
    "contracts/operations/observability-stack-deployment-registry.v1.json",
    "scripts/register-memory-os-observability-stack-deployment.py",
    "scripts/validate-memory-os-observability-stack-deployment.py",
    "scripts/reconcile-memory-os-observability-stack-deployment.py",
    ".github/workflows/observability-stack-deployment.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, relative, field in (
        (CONTRACT, CONTRACT_REL, "observability stack contract"),
        (REGISTRY, REGISTRY_REL, "observability stack registry"),
        (WRITER, WRITER_REL, "observability stack writer"),
        (VALIDATOR, VALIDATOR_REL, "observability stack validator"),
        (OBSERVABILITY_VALIDATOR, OBSERVABILITY_VALIDATOR_REL, "observability validator"),
        (ACCESS_VALIDATOR, ACCESS_VALIDATOR_REL, "observability access validator"),
        (METRICS_VALIDATOR, METRICS_VALIDATOR_REL, "metrics validator"),
        (METRICS_OPERATIONS_VALIDATOR, METRICS_OPERATIONS_VALIDATOR_REL, "metrics operations validator"),
        (METRICS_ALERTING_VALIDATOR, METRICS_ALERTING_VALIDATOR_REL, "metrics alerting validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (WORKFLOW, WORKFLOW_REL, "observability stack workflow"),
        (STATUS, STATUS_REL, "production operability status"),
    ):
        require_exact_repo_file(path, relative, field)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def render(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def validate_current_authority() -> None:
    completed = subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=False)
    require(completed.returncode == 0,
            "canonical observability stack authority is invalid before reconcile")


def commit_validated_pair(contract: dict[str, Any], status: dict[str, Any]) -> None:
    original_contract = CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    try:
        CONTRACT.write_bytes(render(contract))
        STATUS.write_bytes(render(status))
        for validator in POST_WRITE_VALIDATORS:
            completed = subprocess.run(["python", str(validator)], cwd=ROOT, check=False)
            require(completed.returncode == 0,
                    f"reconciled observability stack authority failed validation: {validator.name}")
    except BaseException:
        CONTRACT.write_bytes(original_contract)
        STATUS.write_bytes(original_status)
        raise


def main() -> int:
    enforce_runtime_authorities()
    for path in (REGISTRY, WRITER, *POST_WRITE_VALIDATORS, WORKFLOW):
        require(path.is_file(), f"observability stack foundation missing: {path.relative_to(ROOT)}")
    validate_current_authority()
    registry = load(REGISTRY)
    stacks = registry.get("stacks")
    require(isinstance(stacks, list), "registry stacks missing")
    admitted = len(stacks)
    pe = sum(1 for item in stacks if isinstance(item, dict) and item.get("environmentClass") == "PRODUCTION_EQUIVALENT")
    prod = sum(1 for item in stacks if isinstance(item, dict) and item.get("environmentClass") == "PRODUCTION")

    contract = load(CONTRACT)
    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "contract authority missing")
    current["admittedStackCount"] = admitted
    current["productionEquivalentStackCount"] = pe
    current["productionStackCount"] = prod
    current["integratedStructuredLogBackendProven"] = admitted > 0
    current["integratedMetricsBackendProven"] = admitted > 0
    current["accessAuditAndReviewProven"] = admitted > 0
    current["pagingDeliveryAndResponseProven"] = admitted > 0
    current["retentionDeletionVerified"] = admitted > 0
    current["productionEvidence"] = prod > 0
    current["productionReady"] = False
    current["productionDecision"] = "NO_GO"
    readiness["registryImplemented"] = True
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["admittedStackCount"] = admitted
    readiness["productionEquivalentStackAvailable"] = pe > 0
    readiness["productionStackAvailable"] = prod > 0
    readiness["independentReviewCompleted"] = admitted > 0
    readiness["productionReady"] = False

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    for gate_id in ("OPS-P0-003", "OPS-P0-004"):
        gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == gate_id), None)
        require(isinstance(gate, dict), f"{gate_id} missing")
        require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, f"{gate_id} must remain blocking PARTIAL")
        existing = gate.get("existingEvidence")
        refs = gate.get("evidenceRefs")
        require(isinstance(existing, list) and isinstance(refs, list), f"{gate_id} authority arrays missing")
        append_once(existing, EVIDENCE)
        for ref in REFS:
            append_once(refs, ref)

    commit_validated_pair(contract, status)
    print("Memory OS observability stack admission reconciliation PASS")
    print(f"admitted stacks: {admitted}")
    print(f"production stacks: {prod}")
    print("OPS-P0-003/004: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OBSERVABILITY STACK RECONCILE FAILED: {exc}")
        raise SystemExit(1)
