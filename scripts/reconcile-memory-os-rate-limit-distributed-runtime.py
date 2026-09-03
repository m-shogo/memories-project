#!/usr/bin/env python3
"""Reconcile distributed rate-limit runtime admission without inventing deployment evidence."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json")
WRITER_REL = Path("scripts/register-memory-os-rate-limit-distributed-runtime.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-rate-limit-distributed-runtime.py")
RATE_LIMIT_OPERATIONS_VALIDATOR_REL = Path("scripts/validate-memory-os-rate-limit-operations.py")
RATE_LIMIT_VALIDATOR_REL = Path("scripts/validate-memory-os-rate-limit.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
WORKFLOW_REL = Path(".github/workflows/rate-limit-distributed-runtime-admission.yml")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
WRITER = ROOT / WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL
RATE_LIMIT_OPERATIONS_VALIDATOR = ROOT / RATE_LIMIT_OPERATIONS_VALIDATOR_REL
RATE_LIMIT_VALIDATOR = ROOT / RATE_LIMIT_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
POST_WRITE_VALIDATORS = (
    VALIDATOR,
    RATE_LIMIT_OPERATIONS_VALIDATOR,
    RATE_LIMIT_VALIDATOR,
    OPERABILITY_VALIDATOR,
)
WORKFLOW = ROOT / WORKFLOW_REL
STATUS = ROOT / STATUS_REL

EVIDENCE = (
    "generation-bound distributed rate-limit runtime admission is implemented: future evidence must bind the exact policy digest, at least two runtime instances, an atomic shared store, trusted-proxy deployment, restart continuity, fail-closed dependency behavior, runtime-observed emergency expiry/restoration, alert delivery and independent security/operability review; the registry is currently empty and creates no runtime deployment claim"
)
REFS = (
    "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json",
    "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json",
    "scripts/register-memory-os-rate-limit-distributed-runtime.py",
    "scripts/validate-memory-os-rate-limit-distributed-runtime.py",
    "scripts/reconcile-memory-os-rate-limit-distributed-runtime.py",
    ".github/workflows/rate-limit-distributed-runtime-admission.yml",
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
        (CONTRACT, CONTRACT_REL, "distributed runtime contract"),
        (REGISTRY, REGISTRY_REL, "distributed runtime registry"),
        (WRITER, WRITER_REL, "distributed runtime writer"),
        (VALIDATOR, VALIDATOR_REL, "distributed runtime validator"),
        (RATE_LIMIT_OPERATIONS_VALIDATOR, RATE_LIMIT_OPERATIONS_VALIDATOR_REL, "rate limit operations validator"),
        (RATE_LIMIT_VALIDATOR, RATE_LIMIT_VALIDATOR_REL, "rate limit validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (WORKFLOW, WORKFLOW_REL, "distributed runtime workflow"),
        (STATUS, STATUS_REL, "production operability status"),
    ):
        require_exact_repo_file(path, relative, field)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def atomic_write_bytes(path: Path, payload: bytes, *, _replace=os.replace) -> None:
    mode = path.stat().st_mode & 0o777 if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(tmp_name, mode)
        _replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def write(path: Path, value: dict[str, Any], *, _atomic_write=atomic_write_bytes) -> None:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _atomic_write(path, payload)


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def run_validator(*, _run=subprocess.run, _validator=VALIDATOR, _root=ROOT) -> None:
    completed = _run(
        ["python", str(_validator)],
        cwd=_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        completed.returncode == 0,
        "distributed runtime authority rejected before reconcile:\n"
        + completed.stdout[-4000:]
        + completed.stderr[-4000:],
    )


def commit_outputs_transactionally(
    outputs: dict[Path, dict[str, Any]],
    *,
    _write=write,
    _atomic_write=atomic_write_bytes,
    _enforce=enforce_runtime_authorities,
    _validators=POST_WRITE_VALIDATORS,
    _run=subprocess.run,
    _root=ROOT,
) -> None:
    _enforce()
    originals = {path: path.read_bytes() for path in outputs}
    try:
        for path, value in outputs.items():
            _write(path, value)
        _enforce()
        for validator in _validators:
            completed = _run(
                ["python", str(validator)],
                cwd=_root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            require(
                completed.returncode == 0,
                f"authority rejected after distributed runtime reconcile: {validator.name}\n"
                + completed.stdout[-4000:]
                + completed.stderr[-4000:],
            )
    except Exception as exc:
        for path, data in originals.items():
            _atomic_write(path, data)
        raise Fail(f"distributed runtime reconcile validation failed; restored prior authority: {exc}") from exc


def main(*, _enforce=enforce_runtime_authorities, _run_validator=run_validator) -> int:
    _enforce()
    for path in (REGISTRY, WRITER, *POST_WRITE_VALIDATORS, WORKFLOW):
        require(path.is_file(), f"distributed runtime admission missing: {path.relative_to(ROOT)}")
    _run_validator()
    registry = load(REGISTRY)
    runtimes = registry.get("runtimes")
    require(isinstance(runtimes, list), "distributed runtime registry missing")
    pe = sum(1 for row in runtimes if isinstance(row, dict) and row.get("environmentClass") == "PRODUCTION_EQUIVALENT")
    prod = sum(1 for row in runtimes if isinstance(row, dict) and row.get("environmentClass") == "PRODUCTION")

    contract = load(CONTRACT)
    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "distributed runtime authority missing")
    current["admittedRuntimeCount"] = len(runtimes)
    current["productionEquivalentRuntimeCount"] = pe
    current["productionRuntimeCount"] = prod
    current["distributedSharedStoreProven"] = len(runtimes) > 0
    current["trustedProxyDeploymentProven"] = len(runtimes) > 0
    current["restartContinuityProven"] = len(runtimes) > 0
    current["runtimeAutomaticExpiryProven"] = len(runtimes) > 0
    current["completedRequiredDrillClassCount"] = len(contract.get("requiredDrillClasses", [])) if runtimes else 0
    current["independentReviewCompleted"] = len(runtimes) > 0
    current["productionEvidence"] = prod > 0
    current["productionReady"] = False
    current["productionDecision"] = "NO_GO"
    readiness["registryImplemented"] = True
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["admittedRuntimeCount"] = len(runtimes)
    readiness["productionEquivalentRuntimeAvailable"] = pe > 0
    readiness["productionRuntimeAvailable"] = prod > 0
    readiness["productionReady"] = False

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-005"), None)
    require(isinstance(gate, dict), "OPS-P0-005 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-005 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(refs, list), "OPS-P0-005 authority arrays missing")
    append_once(existing, EVIDENCE)
    for ref in REFS:
        append_once(refs, ref)

    commit_outputs_transactionally({CONTRACT: contract, STATUS: status})

    print("Memory OS distributed rate-limit runtime reconciliation PASS")
    print(f"admitted runtimes: {len(runtimes)}")
    print("distributed shared store: false" if not runtimes else "distributed shared store: evidence admitted")
    print("runtime automatic expiry: false" if not runtimes else "runtime automatic expiry: evidence admitted")
    print("OPS-P0-005: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DISTRIBUTED RATE LIMIT RUNTIME RECONCILE FAILED: {exc}")
        raise SystemExit(1)
