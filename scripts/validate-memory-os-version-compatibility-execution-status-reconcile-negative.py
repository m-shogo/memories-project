#!/usr/bin/env python3
"""Pin monotonicity and rollback for compatibility execution status reconciliation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-version-compatibility-execution-status.py"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ops_gate(status: dict) -> dict:
    gate = next(
        (
            item for item in status.get("areas", [])
            if isinstance(item, dict) and item.get("id") == "OPS-P0-008"
        ),
        None,
    )
    require(isinstance(gate, dict), "OPS-P0-008 missing for execution-status negative")
    return gate


def expect_blocker_monotonicity(module) -> None:
    status = json.loads(module.STATUS.read_text(encoding="utf-8"))
    gate = ops_gate(status)
    before = list(gate.get("missingEvidence", []))
    require(before, "OPS-P0-008 blockers missing before execution projection")
    require(
        "approved predecessor and successor release pair despite candidate-only mixed-version evidence" in before,
        "current canonical release-pair blocker missing before monotonicity probe",
    )
    reconciled = module.reconcile_execution_projection(status)
    after = ops_gate(reconciled).get("missingEvidence")
    require(after == before, "candidate/local execution projection rewrote production blockers")
    require(reconciled.get("productionDecision") == "NO_GO",
            "candidate/local execution projection changed productionDecision")


def expect_post_write_rollback(module) -> None:
    original = module.STATUS.read_bytes()
    status = json.loads(original.decode("utf-8"))
    gate = ops_gate(status)
    existing = gate.get("existingEvidence")
    require(isinstance(existing, list), "OPS-P0-008 existingEvidence missing for rollback probe")
    existing.append("synthetic execution-status rollback probe")

    def fail_post_write() -> None:
        raise RuntimeError("synthetic execution status aggregate validator failure")

    try:
        module.commit_status_transaction(status, validator_runner=fail_post_write)
    except RuntimeError as exc:
        require(
            "synthetic execution status aggregate validator failure" in str(exc),
            f"unexpected rollback failure reason: {exc}",
        )
    else:
        raise NegativeFailure("execution status reconcile accepted synthetic post-write failure")

    require(
        module.STATUS.read_bytes() == original,
        "execution status reconcile left partial production authority after validator failure",
    )


def expect_validator_order(module) -> None:
    expected = [
        module.CANONICAL_VALIDATOR,
        module.FOUNDATION_VALIDATOR,
        module.OPERABILITY_VALIDATOR,
    ]
    observed: list[Path] = []
    original = module.run_validator

    def fake_run(path: Path, _label: str) -> None:
        observed.append(path)

    module.run_validator = fake_run
    try:
        module.run_post_write_validators()
    finally:
        module.run_validator = original
    require(
        observed == expected,
        "execution status transaction does not enforce canonical/foundation/operability validators in order",
    )


def main() -> int:
    module = load_module(RECONCILER, "version_compatibility_execution_status_reconciler")
    expect_validator_order(module)
    expect_blocker_monotonicity(module)
    expect_post_write_rollback(module)
    print("PASS: compatibility execution status preserves stronger blockers and rolls back aggregate failures")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
