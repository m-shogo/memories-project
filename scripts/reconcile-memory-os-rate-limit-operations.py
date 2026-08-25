#!/usr/bin/env python3
"""Register rate-limit operations policy without claiming control-plane readiness."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_REL = Path("contracts/operations/rate-limit-policy-contract.v1.json")
OPERATIONS_REL = Path("contracts/operations/rate-limit-operations-contract.v1.json")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
OPERATIONS_VALIDATOR_REL = Path("scripts/validate-memory-os-rate-limit-operations.py")
RATE_LIMIT_VALIDATOR_REL = Path("scripts/validate-memory-os-rate-limit.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
ENTRY_DOCS_VALIDATOR_REL = Path("scripts/validate-memory-os-entry-docs.py")
WORKFLOW_REL = Path(".github/workflows/reconcile-rate-limit-operations.yml")
POLICY_PATH = ROOT / POLICY_REL
OPERATIONS_PATH = ROOT / OPERATIONS_REL
STATUS_PATH = ROOT / STATUS_REL
OPERATIONS_VALIDATOR_PATH = ROOT / OPERATIONS_VALIDATOR_REL
RATE_LIMIT_VALIDATOR_PATH = ROOT / RATE_LIMIT_VALIDATOR_REL
OPERABILITY_VALIDATOR_PATH = ROOT / OPERABILITY_VALIDATOR_REL
ENTRY_DOCS_VALIDATOR_PATH = ROOT / ENTRY_DOCS_VALIDATOR_REL
WORKFLOW_PATH = ROOT / WORKFLOW_REL

OLD_GAP = "operational disable/rollback runbook"
STALE_LEDGER_GAP = "production emergency control plane with automatic expiry and append-only operation evidence ledger"
NEW_EXISTING = (
    "binding emergency-operation policy that forbids unlimited/fail-open public traffic and permits only normal bounded, strict local emergency or route fail-closed modes",
    "trusted-proxy disablement procedure for uncertain deployment ownership",
    "canonical activation, rollback, shared-store recovery and no-business-mutation verification runbook",
)
NEW_GAPS = (
    "production emergency control plane with automatic expiry",
    "completed emergency-mode, shared-store recovery and trusted-proxy disablement drills",
)
NEW_REFS = (
    "contracts/operations/rate-limit-operations-contract.v1.json",
    "docs/runbooks/memory-os-rate-limit-operations.md",
    "scripts/validate-memory-os-rate-limit-operations.py",
    "scripts/reconcile-memory-os-rate-limit-operations.py",
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
        (POLICY_PATH, POLICY_REL, "rate-limit policy contract"),
        (OPERATIONS_PATH, OPERATIONS_REL, "rate-limit operations contract"),
        (STATUS_PATH, STATUS_REL, "production operability status"),
        (OPERATIONS_VALIDATOR_PATH, OPERATIONS_VALIDATOR_REL, "rate-limit operations validator"),
        (RATE_LIMIT_VALIDATOR_PATH, RATE_LIMIT_VALIDATOR_REL, "rate-limit validator"),
        (OPERABILITY_VALIDATOR_PATH, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (ENTRY_DOCS_VALIDATOR_PATH, ENTRY_DOCS_VALIDATOR_REL, "entry docs validator"),
        (WORKFLOW_PATH, WORKFLOW_REL, "rate-limit operations workflow"),
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


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def run_validator(path: Path, label: str) -> None:
    enforce_runtime_authorities()
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"{label} validation failed:\n{completed.stdout[-4000:]}",
    )


def validate_source_authority() -> None:
    enforce_runtime_authorities()
    run_validator(OPERATIONS_VALIDATOR_PATH, "rate-limit operations source")


def validate_written_authority() -> None:
    enforce_runtime_authorities()
    for validator, label in (
        (OPERATIONS_VALIDATOR_PATH, "rate-limit operations post-write"),
        (RATE_LIMIT_VALIDATOR_PATH, "rate-limit aggregate post-write"),
        (OPERABILITY_VALIDATOR_PATH, "operability aggregate post-write"),
        (ENTRY_DOCS_VALIDATOR_PATH, "entry docs post-write"),
    ):
        run_validator(validator, label)


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write_bytes(
        path,
        (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )


def transactional_write(policy: dict[str, Any], status: dict[str, Any]) -> None:
    originals = {
        POLICY_PATH: POLICY_PATH.read_bytes(),
        STATUS_PATH: STATUS_PATH.read_bytes(),
    }
    try:
        atomic_write_json(POLICY_PATH, policy)
        atomic_write_json(STATUS_PATH, status)
        validate_written_authority()
    except Exception:
        for path, original in originals.items():
            atomic_write_bytes(path, original)
        raise


_CANONICAL_ROOT = ROOT
_CANONICAL_REQUIRE = require
_CANONICAL_REQUIRE_EXACT_REPO_FILE = require_exact_repo_file
_CANONICAL_ENFORCE_RUNTIME_AUTHORITIES = enforce_runtime_authorities
_CANONICAL_LOAD = load
_CANONICAL_APPEND_ONCE = append_once
_CANONICAL_RUN_VALIDATOR = run_validator
_CANONICAL_VALIDATE_SOURCE_AUTHORITY = validate_source_authority
_CANONICAL_VALIDATE_WRITTEN_AUTHORITY = validate_written_authority
_CANONICAL_ATOMIC_WRITE_BYTES = atomic_write_bytes
_CANONICAL_ATOMIC_WRITE_JSON = atomic_write_json
_CANONICAL_TRANSACTIONAL_WRITE = transactional_write
_CANONICAL_SUBPROCESS_RUN = subprocess.run


def enforce_execution_authorities() -> None:
    if ROOT != _CANONICAL_ROOT:
        raise ReconcileFailure("rate-limit operations repository execution authority drift")
    helpers = (
        (require, _CANONICAL_REQUIRE, "require"),
        (require_exact_repo_file, _CANONICAL_REQUIRE_EXACT_REPO_FILE, "path checker"),
        (enforce_runtime_authorities, _CANONICAL_ENFORCE_RUNTIME_AUTHORITIES, "runtime guard"),
        (load, _CANONICAL_LOAD, "loader"),
        (append_once, _CANONICAL_APPEND_ONCE, "append helper"),
        (run_validator, _CANONICAL_RUN_VALIDATOR, "validator runner"),
        (validate_source_authority, _CANONICAL_VALIDATE_SOURCE_AUTHORITY, "source validator"),
        (validate_written_authority, _CANONICAL_VALIDATE_WRITTEN_AUTHORITY, "post-write validator"),
        (atomic_write_bytes, _CANONICAL_ATOMIC_WRITE_BYTES, "atomic byte writer"),
        (atomic_write_json, _CANONICAL_ATOMIC_WRITE_JSON, "atomic JSON writer"),
        (transactional_write, _CANONICAL_TRANSACTIONAL_WRITE, "transaction writer"),
        (subprocess.run, _CANONICAL_SUBPROCESS_RUN, "subprocess transport"),
    )
    for current, canonical, label in helpers:
        if current is not canonical:
            raise ReconcileFailure(f"rate-limit operations {label} execution authority drift")
    enforce_runtime_authorities()


_CANONICAL_ENFORCE_EXECUTION_AUTHORITIES = enforce_execution_authorities


def main() -> int:
    if enforce_execution_authorities is not _CANONICAL_ENFORCE_EXECUTION_AUTHORITIES:
        raise ReconcileFailure("rate-limit operations execution guard authority drift")
    enforce_execution_authorities()
    validate_source_authority()
    policy = load(POLICY_PATH)
    operations = load(OPERATIONS_PATH)
    readiness = operations.get("readiness")
    require(isinstance(readiness, dict), "operations readiness must be an object")
    for foundation in (
        "policyDefined", "runbookDefined", "safeModesDefined",
        "transitionGuardsDefined", "recoveryVerificationDefined",
        "evidenceLedgerImplemented",
    ):
        require(readiness.get(foundation) is True,
                f"operations foundation not validated: {foundation}")
    for unproven in (
        "productionControlPlaneImplemented", "automaticExpiryImplemented",
        "sharedStoreImplemented", "trustedProxyDeploymentConfigured",
        "drillCompleted", "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven operations readiness cannot be true: {unproven}")

    changed = False
    expected_operations = {
        "policyDefined": True,
        "policyContract": "contracts/operations/rate-limit-operations-contract.v1.json",
        "productionControlPlaneImplemented": False,
        "automaticExpiryImplemented": False,
        "evidenceLedgerImplemented": True,
        "drillCompleted": False,
    }
    if policy.get("operations") != expected_operations:
        policy["operations"] = expected_operations
        changed = True

    refs = policy.get("evidenceRefs")
    require(isinstance(refs, list), "primary rate-limit evidenceRefs must be a list")
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"rate-limit operations evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    store = policy.get("store")
    require(isinstance(store, dict), "primary store contract must be an object")
    require(store.get("distributedEnforcementImplemented") is False,
            "distributed shared store remains unimplemented")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "operations policy cannot change productionDecision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-005"]
    require(len(matches) == 1, "OPS-P0-005 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") == "PARTIAL",
            "operations policy cannot alter a non-PARTIAL gate")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    status_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-005 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-005 missingEvidence must be a list")
    require(isinstance(status_refs, list), "OPS-P0-005 evidenceRefs must be a list")

    for item in NEW_EXISTING:
        changed = append_once(existing, item) or changed
    for stale_gap in (OLD_GAP, STALE_LEDGER_GAP):
        if stale_gap in missing:
            missing.remove(stale_gap)
            changed = True
    for item in NEW_GAPS:
        changed = append_once(missing, item) or changed
    for ref in NEW_REFS:
        changed = append_once(status_refs, ref) or changed

    for required_gap in (
        "production-equivalent distributed enforcement",
        "trusted-proxy configuration owned per deployment",
        "load-calibrated limits",
        "production emergency control plane",
        "completed emergency-mode",
    ):
        require(any(required_gap in item for item in missing),
                f"required OPS-P0-005 gap disappeared: {required_gap}")
    require(not any("append-only operation evidence ledger" in item for item in missing),
            "implemented operation ledger cannot remain a missing-evidence blocker")
    require(gate.get("status") == "PARTIAL", "OPS-P0-005 readiness changed unexpectedly")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        validate_written_authority()
        print("Rate-limit operations authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    transactional_write(policy, status)
    print("Registered rate-limit operations policy; OPS-P0-005 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"RATE-LIMIT OPERATIONS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
