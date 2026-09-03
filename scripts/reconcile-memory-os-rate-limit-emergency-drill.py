#!/usr/bin/env python3
"""Register a validated local rate-limit decision drill without production promotion."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/rate-limit-emergency-drill-contract.v1.json"
CANONICAL_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/rate-limit-emergency-drill-results.sample.v1.json"
CANONICAL_OPERATIONS_PATH = ROOT / "contracts/operations/rate-limit-operations-contract.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-rate-limit-emergency-drill.py"
CANONICAL_OPERATIONS_VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-operations.py"
CANONICAL_RATE_LIMIT_VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CANONICAL_SUBPROCESS_RUN = subprocess.run
CANONICAL_OS_REPLACE = os.replace
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
OPERATIONS_PATH = CANONICAL_OPERATIONS_PATH
STATUS_PATH = CANONICAL_STATUS_PATH
VALIDATOR_PATH = CANONICAL_VALIDATOR_PATH
OPERATIONS_VALIDATOR = CANONICAL_OPERATIONS_VALIDATOR
RATE_LIMIT_VALIDATOR = CANONICAL_RATE_LIMIT_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
WORKFLOW_PATH = ".github/workflows/rate-limit-emergency-drill.yml"
NEW_REFS = (
    "contracts/operations/rate-limit-emergency-drill-contract.v1.json",
    "scripts/run-memory-os-rate-limit-emergency-drill.py",
    "scripts/validate-memory-os-rate-limit-emergency-drill.py",
    "scripts/reconcile-memory-os-rate-limit-emergency-drill.py",
    "scripts/evaluate-memory-os-rate-limit-emergency-state.py",
    "docs/fixtures/memory-os-operability/rate-limit-emergency-drill-results.sample.v1.json",
    WORKFLOW_PATH,
)
STATUS_EVIDENCE = (
    "exact-source local/CI emergency decision-model drill proves the canonical append-only writer rejects duplicate operation IDs and the canonical read-only evaluator classifies an ACTIVE emergency record as expired fail-closed after the 60-minute boundary; restoration to NORMAL is modeled as eligible only after every required recovery check passes, without mutating runtime traffic or claiming automatic production expiry",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")
    try:
        resolved = canonical.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError) as exc:
        raise ReconcileFailure(f"canonical {label} cannot be resolved") from exc
    require(resolved == canonical, f"canonical {label} escaped repository path")


def enforce_runtime_authorities() -> None:
    for path, canonical, label in (
        (CONTRACT_PATH, CANONICAL_CONTRACT_PATH, "emergency drill contract"),
        (RESULT_PATH, CANONICAL_RESULT_PATH, "emergency drill result"),
        (OPERATIONS_PATH, CANONICAL_OPERATIONS_PATH, "rate-limit operations contract"),
        (STATUS_PATH, CANONICAL_STATUS_PATH, "production operability status"),
        (VALIDATOR_PATH, CANONICAL_VALIDATOR_PATH, "emergency drill validator"),
        (OPERATIONS_VALIDATOR, CANONICAL_OPERATIONS_VALIDATOR, "rate-limit operations validator"),
        (RATE_LIMIT_VALIDATOR, CANONICAL_RATE_LIMIT_VALIDATOR, "rate-limit validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
    ):
        require_exact_authority(path, canonical, label)
    require(subprocess.run is CANONICAL_SUBPROCESS_RUN,
            "emergency drill subprocess execution authority drift")
    require(os.replace is CANONICAL_OS_REPLACE,
            "emergency drill atomic replacement transport authority drift")
    require(run_validator is CANONICAL_RUN_VALIDATOR,
            "emergency drill validator execution authority drift")
    require(atomic_write_bytes is CANONICAL_ATOMIC_WRITE_BYTES,
            "emergency drill atomic writer authority drift")
    require(atomic_write_json is CANONICAL_ATOMIC_WRITE_JSON,
            "emergency drill JSON writer authority drift")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def run_validator(path: Path, *args: str) -> None:
    enforce_runtime_authorities()
    completed = CANONICAL_SUBPROCESS_RUN(
        [sys.executable, str(path), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"post-write validation failed for {path.name}:\n{completed.stdout[-4000:]}")


CANONICAL_RUN_VALIDATOR = run_validator


def validate_written_authority(source_sha: str) -> None:
    enforce_runtime_authorities()
    CANONICAL_RUN_VALIDATOR(
        VALIDATOR_PATH,
        "--expected-commit-sha", source_sha,
        "--require-result",
        "--require-reconciled",
    )
    CANONICAL_RUN_VALIDATOR(OPERATIONS_VALIDATOR)
    CANONICAL_RUN_VALIDATOR(RATE_LIMIT_VALIDATOR)
    CANONICAL_RUN_VALIDATOR(OPERABILITY_VALIDATOR)


def atomic_write_bytes(
    path: Path,
    payload: bytes,
    *,
    replace_fn: Callable[[str | bytes | os.PathLike[str] | os.PathLike[bytes], str | bytes | os.PathLike[str] | os.PathLike[bytes]], None] = CANONICAL_OS_REPLACE,
) -> None:
    existing_mode = path.stat().st_mode & 0o777 if path.exists() else None
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            if existing_mode is not None:
                os.fchmod(handle.fileno(), existing_mode)
            handle.flush()
            os.fsync(handle.fileno())
        replace_fn(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


CANONICAL_ATOMIC_WRITE_BYTES = atomic_write_bytes


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    CANONICAL_ATOMIC_WRITE_BYTES(
        path,
        (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )


CANONICAL_ATOMIC_WRITE_JSON = atomic_write_json


def transactional_write(contract: dict[str, Any], status: dict[str, Any], source_sha: str) -> None:
    enforce_runtime_authorities()
    originals = {
        CONTRACT_PATH: CONTRACT_PATH.read_bytes(),
        STATUS_PATH: STATUS_PATH.read_bytes(),
    }
    try:
        CANONICAL_ATOMIC_WRITE_JSON(CONTRACT_PATH, contract)
        CANONICAL_ATOMIC_WRITE_JSON(STATUS_PATH, status)
        validate_written_authority(source_sha)
    except BaseException:
        for path, original in originals.items():
            CANONICAL_ATOMIC_WRITE_BYTES(path, original)
        raise


def main() -> int:
    enforce_runtime_authorities()
    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)
    operations = load(OPERATIONS_PATH)
    status = load(STATUS_PATH)

    require(result.get("result") == "PASS" and result.get("integrityResult") == "PASS",
            "decision drill result must PASS before reconcile")
    require(result.get("classification") == "LOCAL_CI_DECISION_MODEL",
            "decision drill classification drift")
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and len(source_sha) == 40,
            "decision drill commitSha must be a full SHA")
    assertions = result.get("assertions")
    require(isinstance(assertions, dict), "result assertions must be object")
    require(assertions.get("productionEvidence") is False,
            "local decision drill cannot be production evidence")
    require(assertions.get("runtimeTrafficChanged") is False,
            "local decision drill cannot mutate runtime traffic")
    require(assertions.get("productionControlPlaneExercised") is False,
            "local decision drill cannot exercise production control plane")
    evaluator_states = result.get("canonicalEvaluatorStates")
    require(isinstance(evaluator_states, dict), "canonical evaluator states missing")
    require(evaluator_states.get("beforeExpiry") ==
            "ACTIVE_EVIDENCE_WINDOW_RUNTIME_UNVERIFIED",
            "pre-expiry evaluator state drift")
    require(evaluator_states.get("afterExpiry") ==
            "EXPIRED_FAIL_CLOSED_RUNTIME_REQUIRES_VERIFICATION",
            "post-expiry evaluator must fail closed")

    changed = False
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "drill readiness must be object")
    for flag in (
        "contractDefined", "runnerImplemented", "validatorImplemented",
        "automaticWorkflowImplemented", "exactSourceResultCommitted",
        "localDecisionModelDrillExecuted",
    ):
        if readiness.get(flag) is not True:
            readiness[flag] = True
            changed = True
    for flag in (
        "runtimeEmergencyModeDrillExecuted", "productionControlPlaneImplemented",
        "automaticProductionExpiryImplemented", "productionReady",
    ):
        require(readiness.get(flag) is False,
                f"unproven drill readiness cannot be true: {flag}")
    refs = contract.get("evidenceRefs")
    require(isinstance(refs, list), "drill evidenceRefs must be list")
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"drill evidence path missing: {ref}")
        changed = append_once(refs, ref) or changed

    operations_readiness = operations.get("readiness")
    require(isinstance(operations_readiness, dict), "operations readiness must be object")
    require(operations_readiness.get("evidenceLedgerImplemented") is True,
            "canonical append-only evidence ledger must be reconciled first")
    for flag in (
        "productionControlPlaneImplemented", "automaticExpiryImplemented",
        "sharedStoreImplemented", "trustedProxyDeploymentConfigured",
        "drillCompleted", "operatorReviewCompleted", "productionReady",
    ):
        require(operations_readiness.get(flag) is False,
                f"local decision drill cannot prove operations readiness: {flag}")

    require(status.get("productionDecision") == "NO_GO",
            "decision drill reconcile cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be list")
    matches = [row for row in areas if isinstance(row, dict) and row.get("id") == "OPS-P0-005"]
    require(len(matches) == 1, "OPS-P0-005 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") == "PARTIAL",
            "local decision drill cannot make OPS-P0-005 READY")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    gate_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-005 existingEvidence must be list")
    require(isinstance(missing, list), "OPS-P0-005 missingEvidence must be list")
    require(isinstance(gate_refs, list), "OPS-P0-005 evidenceRefs must be list")
    for item in STATUS_EVIDENCE:
        changed = append_once(existing, item) or changed
    for ref in NEW_REFS:
        changed = append_once(gate_refs, ref) or changed

    for required_gap in (
        "production-equivalent distributed enforcement",
        "trusted-proxy configuration owned per deployment",
        "load-calibrated limits",
        "production emergency control plane with automatic expiry",
        "completed emergency-mode",
    ):
        require(any(required_gap in str(item) for item in missing),
                f"required OPS-P0-005 gap disappeared: {required_gap}")

    if not changed:
        validate_written_authority(source_sha)
        print("Rate-limit emergency decision drill authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    transactional_write(contract, status, source_sha)
    print("Registered local rate-limit emergency decision drill; runtime/production gaps remain")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"RATE-LIMIT EMERGENCY DRILL RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
