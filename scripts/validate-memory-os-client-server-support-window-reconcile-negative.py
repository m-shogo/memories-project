#!/usr/bin/env python3
"""Focused negatives for client compatibility atomic reconciliation and evidence ordering."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUPPORT_RECONCILER = ROOT / "scripts/reconcile-memory-os-client-server-support-window-status.py"
CLIENT_RECONCILER = ROOT / "scripts/reconcile-memory-os-client-baseline-registry.py"
SUPPORT_CONTRACT = ROOT / "contracts/operations/client-server-support-window-contract.v1.json"
CLIENT_CONTRACT = ROOT / "contracts/operations/client-baseline-registry-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def temp_residue(path: Path) -> list[Path]:
    return list(path.parent.glob(f".{path.name}.*.tmp"))


def verify_support_runtime_authority_substitutions() -> None:
    canonical = {
        SUPPORT_CONTRACT: SUPPORT_CONTRACT.read_bytes(),
        STATUS: STATUS.read_bytes(),
    }
    cases = (
        ("ROOT", ROOT / "scripts"),
        ("CONTRACT", CLIENT_CONTRACT),
        ("STATUS", SUPPORT_CONTRACT),
        ("require", lambda condition, message: None),
        ("require_exact_repo_file", lambda path, expected_relative, field, **kwargs: path),
        ("enforce_runtime_authorities", lambda: None),
    )
    for index, (attribute, replacement) in enumerate(cases):
        reconciler = load_module(
            SUPPORT_RECONCILER,
            f"memory_os_support_window_authority_negative_{index}",
        )
        original = getattr(reconciler, attribute)
        setattr(reconciler, attribute, replacement)
        try:
            rejected = False
            try:
                if attribute == "enforce_runtime_authorities":
                    reconciler.main()
                else:
                    reconciler.enforce_runtime_authorities()
            except Exception:
                rejected = True
            require(rejected, f"support-window reconciler accepted {attribute} authority substitution")
            for path, payload in canonical.items():
                require(
                    path.read_bytes() == payload,
                    f"support-window {attribute} rejection mutated {path.relative_to(ROOT)}",
                )
        finally:
            setattr(reconciler, attribute, original)


def verify_support_atomic_replace_failure() -> None:
    reconciler = load_module(SUPPORT_RECONCILER, "memory_os_support_window_atomic_negative")
    reconciler.enforce_runtime_authorities()
    originals = {
        SUPPORT_CONTRACT: SUPPORT_CONTRACT.read_bytes(),
        STATUS: STATUS.read_bytes(),
    }
    residues_before = set(temp_residue(SUPPORT_CONTRACT) + temp_residue(STATUS))

    original_replace = reconciler.os.replace
    calls = 0

    def fail_first_replace(src: str | bytes | Path, dst: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic support-window atomic replacement failure")
        original_replace(src, dst)

    reconciler.os.replace = fail_first_replace
    try:
        rejected = False
        try:
            reconciler.write_and_validate_transactionally(
                reconciler.load(SUPPORT_CONTRACT),
                reconciler.load(STATUS),
            )
        except Exception as exc:
            rejected = True
            require(
                "synthetic support-window atomic replacement failure" in str(exc),
                f"unexpected support-window atomic rejection: {exc}",
            )
        require(rejected, "support-window reconciliation accepted synthetic atomic replacement failure")
        for path, payload in originals.items():
            require(path.read_bytes() == payload, f"support-window atomic failure mutated {path.relative_to(ROOT)}")
        residues_after = set(temp_residue(SUPPORT_CONTRACT) + temp_residue(STATUS))
        require(residues_after == residues_before, "support-window atomic failure left temporary authority residue")
    finally:
        reconciler.os.replace = original_replace
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                reconciler.atomic_write_bytes(path, payload)


def verify_client_atomic_replace_failure() -> None:
    reconciler = load_module(CLIENT_RECONCILER, "memory_os_client_baseline_atomic_negative")
    reconciler.enforce_runtime_authorities()
    originals = {
        CLIENT_CONTRACT: CLIENT_CONTRACT.read_bytes(),
        SUPPORT_CONTRACT: SUPPORT_CONTRACT.read_bytes(),
        STATUS: STATUS.read_bytes(),
    }
    residues_before = set(
        temp_residue(CLIENT_CONTRACT)
        + temp_residue(SUPPORT_CONTRACT)
        + temp_residue(STATUS)
    )

    original_replace = reconciler.os.replace
    calls = 0

    def fail_first_replace(src: str | bytes | Path, dst: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic client-baseline atomic replacement failure")
        original_replace(src, dst)

    reconciler.os.replace = fail_first_replace
    try:
        rejected = False
        try:
            reconciler.write_and_validate_transactionally(
                reconciler.load(CLIENT_CONTRACT),
                reconciler.load(SUPPORT_CONTRACT),
                reconciler.load(STATUS),
            )
        except Exception as exc:
            rejected = True
            require(
                "synthetic client-baseline atomic replacement failure" in str(exc),
                f"unexpected client-baseline atomic rejection: {exc}",
            )
        require(rejected, "client-baseline reconciliation accepted synthetic atomic replacement failure")
        for path, payload in originals.items():
            require(path.read_bytes() == payload, f"client-baseline atomic failure mutated {path.relative_to(ROOT)}")
        residues_after = set(
            temp_residue(CLIENT_CONTRACT)
            + temp_residue(SUPPORT_CONTRACT)
            + temp_residue(STATUS)
        )
        require(residues_after == residues_before, "client-baseline atomic failure left temporary authority residue")
    finally:
        reconciler.os.replace = original_replace
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                reconciler.atomic_write_bytes(path, payload)


def verify_support_order_preservation() -> None:
    reconciler = load_module(SUPPORT_RECONCILER, "memory_os_support_window_order_negative")
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
    verify_support_runtime_authority_substitutions()
    verify_support_atomic_replace_failure()
    verify_client_atomic_replace_failure()
    verify_support_order_preservation()
    print("Memory OS client compatibility reconcile negative PASS")
    print("support-window runtime authority substitutions: rejected")
    print("support-window atomic replacement failure: rejected without authority mutation")
    print("client-baseline atomic replacement failure: rejected without authority mutation")
    print("temporary authority residue: none")
    print("support-window existingEvidence replacement: stable index")
    print("duplicate support-window evidence prefix: rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
