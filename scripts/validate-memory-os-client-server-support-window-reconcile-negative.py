#!/usr/bin/env python3
"""Focused negatives for support-window atomic reconciliation and evidence ordering."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-client-server-support-window-status.py"
CONTRACT = ROOT / "contracts/operations/client-server-support-window-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_support_window_atomic_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load support-window reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def temp_residue(path: Path) -> list[Path]:
    return list(path.parent.glob(f".{path.name}.*.tmp"))


def verify_atomic_replace_failure() -> None:
    reconciler = load_module()
    reconciler.enforce_runtime_authorities()
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    residues_before = set(temp_residue(CONTRACT) + temp_residue(STATUS))

    original_replace = reconciler.os.replace
    calls = 0

    def fail_first_replace(src: str | bytes | Path, dst: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic atomic replacement failure")
        original_replace(src, dst)

    reconciler.os.replace = fail_first_replace
    try:
        contract = reconciler.load(CONTRACT)
        status = reconciler.load(STATUS)
        rejected = False
        try:
            reconciler.write_and_validate_transactionally(contract, status)
        except Exception as exc:
            rejected = True
            require(
                "synthetic atomic replacement failure" in str(exc),
                f"unexpected atomic replacement rejection: {exc}",
            )
        require(rejected, "support-window reconciliation accepted synthetic atomic replacement failure")
        require(CONTRACT.read_bytes() == contract_before, "atomic replacement failure mutated support-window contract")
        require(STATUS.read_bytes() == status_before, "atomic replacement failure mutated production status")
        residues_after = set(temp_residue(CONTRACT) + temp_residue(STATUS))
        require(residues_after == residues_before, "atomic replacement failure left temporary authority residue")
    finally:
        reconciler.os.replace = original_replace
        if CONTRACT.read_bytes() != contract_before:
            reconciler.atomic_write_bytes(CONTRACT, contract_before)
        if STATUS.read_bytes() != status_before:
            reconciler.atomic_write_bytes(STATUS, status_before)


def verify_order_preservation() -> None:
    reconciler = load_module()
    prefix = reconciler.EVIDENCE_PREFIX
    old = prefix + " old"
    values: list[Any] = ["before", old, "after"]
    reconciler.replace_prefixed_once(values, prefix, reconciler.EVIDENCE)
    require(values == ["before", reconciler.EVIDENCE, "after"], "support-window evidence moved during replacement")

    duplicate = [old, "middle", prefix + " duplicate"]
    rejected = False
    try:
        reconciler.replace_prefixed_once(duplicate, prefix, reconciler.EVIDENCE)
    except reconciler.Fail:
        rejected = True
    require(rejected, "duplicate support-window evidence prefix was not rejected")


def main() -> int:
    verify_atomic_replace_failure()
    verify_order_preservation()
    print("Memory OS client/server support-window reconcile negative PASS")
    print("atomic replacement failure: rejected without authority mutation")
    print("temporary authority residue: none")
    print("existingEvidence replacement: stable index")
    print("duplicate evidence prefix: rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
