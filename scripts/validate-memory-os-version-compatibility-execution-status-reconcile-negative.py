#!/usr/bin/env python3
"""Pin monotonicity, authority identity and rollback for compatibility execution status reconciliation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-version-compatibility-execution-status.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
EXECUTION = ROOT / "contracts/operations/version-compatibility-execution-evidence.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-version-compatibility-execution-evidence.py"


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
    sentinel = "synthetic stronger canonical blocker preserved by execution projection"
    require(sentinel not in before, "synthetic blocker unexpectedly present in canonical status")
    gate["missingEvidence"].append(sentinel)
    expected = list(gate["missingEvidence"])

    reconciled = module.reconcile_execution_projection(status)
    after = ops_gate(reconciled).get("missingEvidence")
    require(after == expected, "candidate/local execution projection rewrote production blockers")
    require(sentinel in after, "candidate/local execution projection dropped a stronger canonical blocker")
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


def expect_authority_substitution_rejected(status_bytes: bytes) -> None:
    substitutions = (
        ("EXECUTION", STATUS),
        ("STATUS", EXECUTION),
        ("VALIDATOR", STATUS),
        ("CANONICAL_VALIDATOR", VALIDATOR),
        ("FOUNDATION_VALIDATOR", VALIDATOR),
        ("OPERABILITY_VALIDATOR", VALIDATOR),
        ("WORKFLOW", VALIDATOR),
    )
    for index, (attribute, replacement) in enumerate(substitutions):
        module = load_module(RECONCILER, f"version_compat_execution_authority_{index}")
        setattr(module, attribute, replacement)
        try:
            module.main()
        except module.Fail:
            pass
        else:
            raise NegativeFailure(f"execution status reconciler accepted {attribute} substitution")
        require(
            STATUS.read_bytes() == status_bytes,
            f"execution status reconciler mutated production authority after {attribute} substitution",
        )


def main() -> int:
    original_status = STATUS.read_bytes()
    module = load_module(RECONCILER, "version_compatibility_execution_status_reconciler")
    expect_validator_order(module)
    expect_blocker_monotonicity(module)
    expect_post_write_rollback(module)
    expect_authority_substitution_rejected(original_status)
    require(STATUS.read_bytes() == original_status, "execution status negative suite mutated production authority")
    print("PASS: compatibility execution status pins canonical authorities, preserves stronger blockers and rolls back aggregate failures")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
