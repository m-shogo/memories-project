#!/usr/bin/env python3
"""Register the append-only rate-limit operation ledger without claiming control-plane readiness."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_REL = Path("contracts/operations/rate-limit-operation-evidence-contract.v1.json")
OPERATIONS_REL = Path("contracts/operations/rate-limit-operations-contract.v1.json")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
WRITER_REL = Path("scripts/create-memory-os-rate-limit-operation-evidence.py")
EVIDENCE_VALIDATOR_REL = Path("scripts/validate-memory-os-rate-limit-operation-evidence.py")
OPERATIONS_VALIDATOR_REL = Path("scripts/validate-memory-os-rate-limit-operations.py")
RATE_LIMIT_VALIDATOR_REL = Path("scripts/validate-memory-os-rate-limit.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
WORKFLOW_REL = Path(".github/workflows/rate-limit-operation-evidence.yml")
EVIDENCE_PATH = ROOT / EVIDENCE_REL
OPERATIONS_PATH = ROOT / OPERATIONS_REL
STATUS_PATH = ROOT / STATUS_REL
WRITER_PATH = ROOT / WRITER_REL
EVIDENCE_VALIDATOR = ROOT / EVIDENCE_VALIDATOR_REL
OPERATIONS_VALIDATOR = ROOT / OPERATIONS_VALIDATOR_REL
RATE_LIMIT_VALIDATOR = ROOT / RATE_LIMIT_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
WORKFLOW_PATH = ROOT / WORKFLOW_REL

OLD_GAP = (
    "production emergency control plane with automatic expiry and append-only operation evidence ledger"
)
NEW_EXISTING = (
    "append-only rate-limit emergency-operation evidence contract with closed modes, proxy modes, activation reasons and verification checks",
    "exclusive-create writer that rejects duplicate operation IDs before any overwrite",
    "privacy validator forbidding raw IP, network identity, tokens, account/session identifiers, URLs, credentials and free-form evidence text",
)
NEW_GAP = "production emergency control plane with automatic expiry"
NEW_REFS = (
    "contracts/operations/rate-limit-operation-evidence-contract.v1.json",
    "docs/evidence/rate-limit-operations/README.md",
    "docs/fixtures/memory-os-operability/rate-limit-operation-record.template.v1.json",
    "scripts/create-memory-os-rate-limit-operation-evidence.py",
    "scripts/validate-memory-os-rate-limit-operation-evidence.py",
    "scripts/reconcile-memory-os-rate-limit-operation-evidence.py",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ReconcileFailure(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, relative, field in (
        (EVIDENCE_PATH, EVIDENCE_REL, "rate-limit operation evidence contract"),
        (OPERATIONS_PATH, OPERATIONS_REL, "rate-limit operations contract"),
        (STATUS_PATH, STATUS_REL, "production operability status"),
        (WRITER_PATH, WRITER_REL, "rate-limit operation writer"),
        (EVIDENCE_VALIDATOR, EVIDENCE_VALIDATOR_REL, "rate-limit operation evidence validator"),
        (OPERATIONS_VALIDATOR, OPERATIONS_VALIDATOR_REL, "rate-limit operations validator"),
        (RATE_LIMIT_VALIDATOR, RATE_LIMIT_VALIDATOR_REL, "rate-limit validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (WORKFLOW_PATH, WORKFLOW_REL, "rate-limit operation workflow"),
    ):
        require_exact_repo_file(path, relative, field)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> Any:
    require_exact_repo_file(WRITER_PATH, WRITER_REL, "rate-limit operation writer")
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_operation_writer_reconcile", WRITER_PATH
    )
    require(spec is not None and spec.loader is not None,
            "unable to load rate-limit operation evidence writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def run_validator(path: Path, label: str) -> None:
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    require(completed.returncode == 0,
            f"{label} validation failed:\n{completed.stdout[-4000:]}")


def validate_evidence_authority(evidence: dict[str, Any]) -> None:
    enforce_runtime_authorities()
    try:
        load_writer().validate_contract_append_guards(evidence)
    except Exception as exc:
        raise ReconcileFailure(
            f"rate-limit operation evidence append authority invalid: {exc}"
        ) from exc
    run_validator(EVIDENCE_VALIDATOR, "rate-limit operation evidence")


def validate_written_authority() -> None:
    enforce_runtime_authorities()
    evidence = load(EVIDENCE_PATH)
    validate_evidence_authority(evidence)
    run_validator(OPERATIONS_VALIDATOR, "rate-limit operation evidence post-write")
    run_validator(RATE_LIMIT_VALIDATOR, "rate-limit aggregate post-write")
    run_validator(OPERABILITY_VALIDATOR, "operability aggregate post-write")


def transactional_write(operations: dict[str, Any], status: dict[str, Any]) -> None:
    originals = {
        OPERATIONS_PATH: OPERATIONS_PATH.read_bytes(),
        STATUS_PATH: STATUS_PATH.read_bytes(),
    }
    try:
        OPERATIONS_PATH.write_text(
            json.dumps(operations, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        STATUS_PATH.write_text(
            json.dumps(status, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        validate_written_authority()
    except Exception:
        for path, original in originals.items():
            path.write_bytes(original)
        raise


def main() -> int:
    enforce_runtime_authorities()
    evidence = load(EVIDENCE_PATH)
    validate_evidence_authority(evidence)
    evidence_readiness = evidence.get("readiness")
    require(isinstance(evidence_readiness, dict), "evidence readiness must be an object")
    for foundation in (
        "recordContractDefined", "exclusiveWriterImplemented",
        "ledgerValidatorImplemented", "duplicateOperationIdRejected",
        "privacyValidationImplemented",
    ):
        require(evidence_readiness.get(foundation) is True,
                f"evidence foundation not validated: {foundation}")
    for unproven in (
        "productionControlPlaneImplemented", "automaticModeExpiryImplemented",
        "productionEvidenceRecorded", "productionReady",
    ):
        require(evidence_readiness.get(unproven) is False,
                f"unproven evidence readiness cannot be true: {unproven}")

    operations = load(OPERATIONS_PATH)
    readiness = operations.get("readiness")
    require(isinstance(readiness, dict), "operations readiness must be an object")
    require(readiness.get("productionControlPlaneImplemented") is False,
            "production control plane remains unimplemented")
    require(readiness.get("automaticExpiryImplemented") is False,
            "automatic expiry remains unimplemented")
    require(readiness.get("sharedStoreImplemented") is False,
            "shared store remains unimplemented")
    changed = False
    if readiness.get("evidenceLedgerImplemented") is not True:
        readiness["evidenceLedgerImplemented"] = True
        changed = True
    refs = operations.get("evidenceRefs")
    require(isinstance(refs, list), "operations evidenceRefs must be a list")
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"operation ledger evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "ledger reconcile cannot change productionDecision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-005"]
    require(len(matches) == 1, "OPS-P0-005 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") == "PARTIAL",
            "ledger reconcile cannot alter a non-PARTIAL gate")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    status_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-005 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-005 missingEvidence must be a list")
    require(isinstance(status_refs, list), "OPS-P0-005 evidenceRefs must be a list")

    for item in NEW_EXISTING:
        changed = append_once(existing, item) or changed
    if OLD_GAP in missing:
        missing.remove(OLD_GAP)
        changed = True
    changed = append_once(missing, NEW_GAP) or changed
    for ref in NEW_REFS:
        changed = append_once(status_refs, ref) or changed

    for required_gap in (
        "production-equivalent distributed enforcement",
        "trusted-proxy configuration owned per deployment",
        "load-calibrated limits",
        "production emergency control plane with automatic expiry",
        "completed emergency-mode",
    ):
        require(any(required_gap in item for item in missing),
                f"required OPS-P0-005 gap disappeared: {required_gap}")
    require(gate.get("status") == "PARTIAL", "OPS-P0-005 readiness changed unexpectedly")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        print("Rate-limit operation evidence authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    transactional_write(operations, status)
    print("Registered append-only operation ledger; control plane and automatic expiry remain unimplemented")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"RATE-LIMIT OPERATION EVIDENCE RECONCILE FAILED: {exc}",
              file=sys.stderr)
        raise SystemExit(1)
