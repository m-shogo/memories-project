#!/usr/bin/env python3
"""Prove evidence-ownership reconciliation is exact-authority and transactional."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-operability-evidence-ownership.py"
WORKFLOW = ROOT / ".github/workflows/operability-evidence-ownership.yml"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_operability_evidence_ownership_reconcile_negative", RECONCILER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load evidence ownership reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_atomic_diagnostic_publication() -> None:
    if not WORKFLOW.is_file():
        raise RuntimeError("evidence ownership workflow missing")
    text = WORKFLOW.read_text(encoding="utf-8")
    required = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required if fragment not in text]
    if missing:
        raise RuntimeError(
            f"evidence ownership diagnostic publication is not crash-safe: missing {missing}"
        )
    if "path.write_text(json.dumps(value" in text:
        raise RuntimeError("evidence ownership diagnostic publication regressed to direct write_text")


def expect_authority_identity(reconciler) -> None:
    reconciler.enforce_runtime_authorities()
    original_contract = reconciler.CANONICAL_CONTRACT.read_bytes()
    substitutions = (
        (
            "CONTRACT",
            ROOT / "contracts/operations/production-operability-status.json",
            "ownership contract",
        ),
        ("VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "ownership validator"),
        ("OPERABILITY_VALIDATOR", reconciler.VALIDATOR, "operability validator"),
        (
            "WORKFLOW",
            ROOT / ".github/workflows/operability-contracts.yml",
            "ownership workflow",
        ),
    )
    for attribute, substitute, label in substitutions:
        original = getattr(reconciler, attribute)
        try:
            setattr(reconciler, attribute, substitute)
            try:
                reconciler.enforce_runtime_authorities()
            except reconciler.ReconcileFailure as exc:
                if "authority drift" not in str(exc) and "authority missing" not in str(exc):
                    raise RuntimeError(f"{label} rejected for unrelated reason: {exc}") from exc
            else:
                raise RuntimeError(f"reconciler accepted authority substitution: {label}")
        finally:
            setattr(reconciler, attribute, original)

    if reconciler.CANONICAL_CONTRACT.read_bytes() != original_contract:
        raise RuntimeError("ownership contract changed after authority substitution rejection")
    reconciler.enforce_runtime_authorities()


def prove_validator_chain(reconciler) -> None:
    observed: list[Path] = []
    original_run_validator = reconciler.run_validator

    def capture(path: Path, _label: str) -> None:
        observed.append(path.resolve())

    try:
        reconciler.run_validator = capture
        reconciler.validate_written_authority()
    finally:
        reconciler.run_validator = original_run_validator

    expected = [
        reconciler.VALIDATOR.resolve(),
        reconciler.OPERABILITY_VALIDATOR.resolve(),
    ]
    if observed != expected:
        raise RuntimeError(f"validator chain drift: {observed!r} != {expected!r}")


def prove_noop_validation(reconciler) -> None:
    original = reconciler.CANONICAL_CONTRACT.read_bytes()
    observed: list[Path] = []
    original_run_validator = reconciler.run_validator

    def capture(path: Path, _label: str) -> None:
        observed.append(path.resolve())

    try:
        reconciler.run_validator = capture
        code = reconciler.main()
        if code != 0:
            raise RuntimeError(f"no-op reconcile returned {code}")
    finally:
        reconciler.run_validator = original_run_validator

    expected = [
        reconciler.VALIDATOR.resolve(),
        reconciler.VALIDATOR.resolve(),
        reconciler.OPERABILITY_VALIDATOR.resolve(),
    ]
    if observed != expected:
        raise RuntimeError(f"no-op validator chain drift: {observed!r} != {expected!r}")
    if reconciler.CANONICAL_CONTRACT.read_bytes() != original:
        raise RuntimeError("no-op reconcile changed ownership contract bytes")


def prove_transaction_rollback(reconciler) -> None:
    original = reconciler.CANONICAL_CONTRACT.read_bytes()
    contract = copy.deepcopy(load_json(reconciler.CANONICAL_CONTRACT))
    contract["_negativeTransactionalProbe"] = True

    original_validate = reconciler.validate_written_authority
    reconciler.validate_written_authority = lambda: (_ for _ in ()).throw(
        reconciler.ReconcileFailure("synthetic aggregate validation failure")
    )
    try:
        try:
            reconciler.transactional_write(contract)
        except reconciler.ReconcileFailure as exc:
            if "synthetic aggregate validation failure" not in str(exc):
                raise RuntimeError(f"rollback failed for unrelated reason: {exc}") from exc
        else:
            raise RuntimeError("transactional write accepted synthetic aggregate validation failure")
        if reconciler.CANONICAL_CONTRACT.read_bytes() != original:
            raise RuntimeError("ownership contract rollback was not byte-for-byte")
    finally:
        reconciler.validate_written_authority = original_validate
        if reconciler.CANONICAL_CONTRACT.read_bytes() != original:
            reconciler.CANONICAL_CONTRACT.write_bytes(original)


def main() -> int:
    reconciler = load_module()
    validate_atomic_diagnostic_publication()
    expect_authority_identity(reconciler)
    prove_validator_chain(reconciler)
    prove_noop_validation(reconciler)
    prove_transaction_rollback(reconciler)

    print("PASS: evidence ownership diagnostic publication is atomic and crash-safe")
    print("PASS: evidence ownership data/executable authorities reject substitution")
    print("PASS: no-op reconciliation still validates ownership and aggregate operability")
    print("PASS: post-write aggregate failure restores ownership contract byte-for-byte")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
