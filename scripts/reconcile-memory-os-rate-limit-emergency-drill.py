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


def enforce_runtime_authorities(
    _root: Path = ROOT,
    _contract: Path = CANONICAL_CONTRACT_PATH,
    _result: Path = CANONICAL_RESULT_PATH,
    _operations: Path = CANONICAL_OPERATIONS_PATH,
    _status: Path = CANONICAL_STATUS_PATH,
    _validator: Path = CANONICAL_VALIDATOR_PATH,
    _operations_validator: Path = CANONICAL_OPERATIONS_VALIDATOR,
    _rate_limit_validator: Path = CANONICAL_RATE_LIMIT_VALIDATOR,
    _operability_validator: Path = CANONICAL_OPERABILITY_VALIDATOR,
    _subprocess_run: Callable[..., Any] = CANONICAL_SUBPROCESS_RUN,
    _os_replace: Callable[..., Any] = CANONICAL_OS_REPLACE,
) -> None:
    require(ROOT == _root and _root == Path(__file__).resolve().parents[1],
            "emergency drill repository authority drift")
    immutable_authorities = (
        (CONTRACT_PATH, CANONICAL_CONTRACT_PATH, _contract, "emergency drill contract"),
        (RESULT_PATH, CANONICAL_RESULT_PATH, _result, "emergency drill result"),
        (OPERATIONS_PATH, CANONICAL_OPERATIONS_PATH, _operations, "rate-limit operations contract"),
        (STATUS_PATH, CANONICAL_STATUS_PATH, _status, "production operability status"),
        (VALIDATOR_PATH, CANONICAL_VALIDATOR_PATH, _validator, "emergency drill validator"),
        (OPERATIONS_VALIDATOR, CANONICAL_OPERATIONS_VALIDATOR, _operations_validator, "rate-limit operations validator"),
        (RATE_LIMIT_VALIDATOR, CANONICAL_RATE_LIMIT_VALIDATOR, _rate_limit_validator, "rate-limit validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, _operability_validator, "operability validator"),
    )
    for path, canonical_global, immutable, label in immutable_authorities:
        require(canonical_global == immutable, f"canonical {label} identity drift")
        require_exact_authority(path, immutable, label)
    require(CANONICAL_SUBPROCESS_RUN is _subprocess_run and subprocess.run is _subprocess_run,
            "emergency drill subprocess execution authority drift")
    require(CANONICAL_OS_REPLACE is _os_replace and os.replace is _os_replace,
            "emergency drill atomic replacement transport authority drift")


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


def run_validator(
    path: Path,
    *args: str,
    _subprocess_run: Callable[..., Any] = CANONICAL_SUBPROCESS_RUN,
) -> None:
    enforce_runtime_authorities()
    require(CANONICAL_SUBPROCESS_RUN is _subprocess_run and subprocess.run is _subprocess_run,
            "emergency drill subprocess execution authority drift")
    completed = _subprocess_run(
        [sys.executable, str(path), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"post-write validation failed for {path.name}:\n{completed.stdout[-4000:]}")


def validate_written_authority(
    source_sha: str,
    _run_validator: Callable[..., None] = run_validator,
) -> None:
    enforce_runtime_authorities()
    require(run_validator is _run_validator,
            "emergency drill validator execution authority drift")
    _run_validator(
        VALIDATOR_PATH,
        "--expected-commit-sha", source_sha,
        "--require-result",
        "--require-reconciled",
    )
    _run_validator(OPERATIONS_VALIDATOR)
    _run_validator(RATE_LIMIT_VALIDATOR)
    _run_validator(OPERABILITY_VALIDATOR)


def atomic_write_bytes(
    path: Path,
    payload: bytes,
    *,
    _replace_fn: Callable[[str | bytes | os.PathLike[str] | os.PathLike[bytes], str | bytes | os.PathLike[str] | os.PathLike[bytes]], None] = CANONICAL_OS_REPLACE,
) -> None:
    require(CANONICAL_OS_REPLACE is _replace_fn and os.replace is _replace_fn,
            "emergency drill atomic replacement transport authority drift")
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
        _replace_fn(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(
    path: Path,
    value: dict[str, Any],
    _atomic_write_bytes: Callable[..., None] = atomic_write_bytes,
) -> None:
    require(atomic_write_bytes is _atomic_write_bytes,
            "emergency drill atomic writer authority drift")
    _atomic_write_bytes(
        path,
        (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )


def transactional_write(
    contract: dict[str, Any],
    status: dict[str, Any],
    source_sha: str,
    _atomic_write_json: Callable[..., None] = atomic_write_json,
    _atomic_write_bytes: Callable[..., None] = atomic_write_bytes,
    _validate_written_authority: Callable[[str], None] = validate_written_authority,
) -> None:
    enforce_runtime_authorities()
    require(atomic_write_json is _atomic_write_json,
            "emergency drill JSON writer authority drift")
    require(atomic_write_bytes is _atomic_write_bytes,
            "emergency drill atomic writer authority drift")
    require(validate_written_authority is _validate_written_authority,
            "emergency drill post-write validator authority drift")
    originals = {
        CONTRACT_PATH: CONTRACT_PATH.read_bytes(),
        STATUS_PATH: STATUS_PATH.read_bytes(),
    }
    try:
        _atomic_write_json(CONTRACT_PATH, contract)
        _atomic_write_json(STATUS_PATH, status)
        _validate_written_authority(source_sha)
    except BaseException:
        for path, original in originals.items():
            _atomic_write_bytes(path, original)
        raise


def main(
    _enforce_runtime_authorities: Callable[[], None] = enforce_runtime_authorities,
    _transactional_write: Callable[..., None] = transactional_write,
    _validate_written_authority: Callable[[str], None] = validate_written_authority,
) -> int:
    require(enforce_runtime_authorities is _enforce_runtime_authorities,
            "emergency drill runtime guard authority drift")
    require(transactional_write is _transactional_write,
            "emergency drill transaction execution authority drift")
    require(validate_written_authority is _validate_written_authority,
            "emergency drill post-write validator authority drift")
    _enforce_runtime_authorities()
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
        _validate_written_authority(source_sha)
        print("Rate-limit emergency decision drill authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    _transactional_write(contract, status, source_sha)
    print("Registered local rate-limit emergency decision drill; runtime/production gaps remain")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"RATE-LIMIT EMERGENCY DRILL RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
