#!/usr/bin/env python3
"""Prove rate-limit operations reconcile pins exact authorities and rolls back post-write failure."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-operations.py"
CANONICAL_POLICY_PATH = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_operations_reconcile_negative", RECONCILER_PATH
    )
    require(spec is not None and spec.loader is not None,
            "cannot load rate-limit operations reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def prove_transaction_rollback(reconciler: Any) -> None:
    originals = {
        CANONICAL_POLICY_PATH: CANONICAL_POLICY_PATH.read_bytes(),
        CANONICAL_STATUS_PATH: CANONICAL_STATUS_PATH.read_bytes(),
    }
    policy = copy.deepcopy(load_json(CANONICAL_POLICY_PATH))
    status = copy.deepcopy(load_json(CANONICAL_STATUS_PATH))
    policy["operations"]["drillCompleted"] = False
    status["asOf"] = "2099-01-01"

    original_validator = reconciler.validate_written_authority
    reconciler.validate_written_authority = lambda: (_ for _ in ()).throw(
        reconciler.ReconcileFailure("synthetic post-write validation failure")
    )
    try:
        try:
            reconciler.transactional_write(policy, status)
        except reconciler.ReconcileFailure as exc:
            require("synthetic post-write validation failure" in str(exc),
                    "transaction rollback failed for unrelated reason")
        else:
            raise NegativeFailure(
                "transactional write accepted synthetic post-write validation failure"
            )

        for path, original in originals.items():
            require(path.read_bytes() == original,
                    f"rollback failed for {path.relative_to(ROOT)}")
    finally:
        reconciler.validate_written_authority = original_validator
        for path, original in originals.items():
            path.write_bytes(original)


def prove_validator_chain(reconciler: Any) -> None:
    expected = [
        reconciler.OPERATIONS_VALIDATOR_PATH.resolve(),
        reconciler.RATE_LIMIT_VALIDATOR_PATH.resolve(),
        reconciler.OPERABILITY_VALIDATOR_PATH.resolve(),
        reconciler.ENTRY_DOCS_VALIDATOR_PATH.resolve(),
    ]
    observed: list[Path] = []
    original_run = reconciler.run_validator

    def capture(path: Path, _label: str) -> None:
        observed.append(path.resolve())

    try:
        reconciler.run_validator = capture
        reconciler.validate_written_authority()
    finally:
        reconciler.run_validator = original_run
    require(observed == expected,
            f"post-write validator chain drift: {observed!r} != {expected!r}")


def expect_substitution_rejection(
    reconciler: Any, attribute: str, substitute: Path, label: str
) -> None:
    original_attribute = getattr(reconciler, attribute)
    original_policy = CANONICAL_POLICY_PATH.read_bytes()
    original_status = CANONICAL_STATUS_PATH.read_bytes()
    setattr(reconciler, attribute, substitute)
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            message = str(exc)
            require(
                "authority drift" in message or "missing or escapes repository" in message,
                f"{label} rejected for unrelated reason: {message}",
            )
        else:
            raise NegativeFailure(
                f"rate-limit operations reconciler accepted authority substitution: {label}"
            )
        require(CANONICAL_POLICY_PATH.read_bytes() == original_policy,
                f"canonical policy mutated after authority substitution: {label}")
        require(CANONICAL_STATUS_PATH.read_bytes() == original_status,
                f"canonical status mutated after authority substitution: {label}")
    finally:
        setattr(reconciler, attribute, original_attribute)
        CANONICAL_POLICY_PATH.write_bytes(original_policy)
        CANONICAL_STATUS_PATH.write_bytes(original_status)


def main() -> int:
    reconciler = load_module()
    reconciler.enforce_runtime_authorities()
    prove_transaction_rollback(reconciler)
    prove_validator_chain(reconciler)
    cases = (
        ("OPERATIONS_VALIDATOR_PATH", reconciler.RATE_LIMIT_VALIDATOR_PATH, "operations validator"),
        ("RATE_LIMIT_VALIDATOR_PATH", reconciler.OPERABILITY_VALIDATOR_PATH, "rate-limit validator"),
        ("OPERABILITY_VALIDATOR_PATH", reconciler.RATE_LIMIT_VALIDATOR_PATH, "operability validator"),
        ("ENTRY_DOCS_VALIDATOR_PATH", reconciler.OPERABILITY_VALIDATOR_PATH, "entry docs validator"),
        ("POLICY_PATH", reconciler.STATUS_PATH, "policy contract path"),
        ("STATUS_PATH", reconciler.POLICY_PATH, "production status path"),
    )
    for attribute, substitute, label in cases:
        expect_substitution_rejection(reconciler, attribute, substitute, label)

    print("PASS: rate-limit operations exact authorities and post-write rollback are fail-closed")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
