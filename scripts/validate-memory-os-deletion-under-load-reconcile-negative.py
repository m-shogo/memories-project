#!/usr/bin/env python3
"""Focused fail-closed checks for deletion-under-load authority reconciliation."""

from __future__ import annotations

import importlib.util
import os
import stat
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/reconcile-memory-os-deletion-under-load-status.py"


def load_target() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_deletion_under_load_reconcile", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load deletion-under-load reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def canonical_snapshots(module: ModuleType) -> dict[Path, bytes]:
    return {
        module.CANONICAL_CONTRACT_PATH: module.CANONICAL_CONTRACT_PATH.read_bytes(),
        module.CANONICAL_LOAD_PATH: module.CANONICAL_LOAD_PATH.read_bytes(),
        module.CANONICAL_STATUS_PATH: module.CANONICAL_STATUS_PATH.read_bytes(),
    }


def canonical_modes(module: ModuleType) -> dict[Path, int]:
    return {
        path: stat.S_IMODE(path.stat().st_mode)
        for path in (
            module.CANONICAL_CONTRACT_PATH,
            module.CANONICAL_LOAD_PATH,
            module.CANONICAL_STATUS_PATH,
        )
    }


def require_snapshots_unchanged(snapshots: dict[Path, bytes]) -> None:
    for path, payload in snapshots.items():
        require(path.read_bytes() == payload, f"canonical authority mutated after rejection: {path.relative_to(ROOT)}")


def require_modes_unchanged(modes: dict[Path, int]) -> None:
    for path, mode in modes.items():
        require(
            stat.S_IMODE(path.stat().st_mode) == mode,
            f"canonical authority mode changed after rejection: {path.relative_to(ROOT)}",
        )


def expect_rejection(
    module: ModuleType,
    label: str,
    mutate: Callable[[], Callable[[], None]],
    check: Callable[[], None] | None = None,
) -> None:
    snapshots = canonical_snapshots(module)
    modes = canonical_modes(module)
    restore = mutate()
    try:
        try:
            (check or module.enforce_runtime_authorities)()
        except module.ReconcileFailure:
            pass
        else:
            raise RuntimeError(f"authority substitution was accepted: {label}")
    finally:
        restore()
    require_snapshots_unchanged(snapshots)
    require_modes_unchanged(modes)


def swap_attr(target: object, name: str, value: object) -> Callable[[], None]:
    original = getattr(target, name)
    setattr(target, name, value)
    return lambda: setattr(target, name, original)


def swap_many(*changes: tuple[object, str, object]) -> Callable[[], None]:
    originals = [(target, name, getattr(target, name)) for target, name, _ in changes]
    for target, name, value in changes:
        setattr(target, name, value)

    def restore() -> None:
        for target, name, value in reversed(originals):
            setattr(target, name, value)

    return restore


def exercise_rollback_failure(module: ModuleType) -> None:
    snapshots = canonical_snapshots(module)
    modes = canonical_modes(module)
    real_writer = module.CANONICAL_ATOMIC_WRITE_BYTES
    real_run_validator = module.run_validator
    real_enforce_writer = module.enforce_atomic_writer_authority
    writer_calls: list[Path] = []

    def synthetic_primary_failure(*args: object, **kwargs: object) -> None:
        raise module.ReconcileFailure("synthetic primary validator failure")

    def writer_with_first_rollback_failure(path: Path, payload: bytes) -> None:
        writer_calls.append(path)
        real_writer(path, payload)
        if len(writer_calls) == 4:
            raise RuntimeError("synthetic rollback writer failure")

    contract = module.load(module.CANONICAL_CONTRACT_PATH)
    load_contract = module.load(module.CANONICAL_LOAD_PATH)
    status = module.load(module.CANONICAL_STATUS_PATH)
    contract["__negativeRollbackTest"] = True
    load_contract["__negativeRollbackTest"] = True
    status["__negativeRollbackTest"] = True

    module.CANONICAL_ATOMIC_WRITE_BYTES = writer_with_first_rollback_failure
    module.atomic_write_bytes = writer_with_first_rollback_failure
    module.enforce_atomic_writer_authority = lambda: None
    module.run_validator = synthetic_primary_failure
    try:
        try:
            module.write_and_validate_transactionally(contract, load_contract, status)
        except module.ReconcileFailure as exc:
            diagnostic = str(exc)
            require("synthetic primary validator failure" in diagnostic,
                    "rollback failure masked primary validator diagnostic")
            require("rollback incomplete" in diagnostic,
                    "rollback failure did not report incomplete rollback")
            require("synthetic rollback writer failure" in diagnostic,
                    "rollback failure diagnostic missing")
        else:
            raise RuntimeError("synthetic rollback failure was accepted")
    finally:
        module.run_validator = real_run_validator
        module.enforce_atomic_writer_authority = real_enforce_writer
        module.atomic_write_bytes = real_writer
        module.CANONICAL_ATOMIC_WRITE_BYTES = real_writer

    require(len(writer_calls) == 6, "rollback did not continue across all three canonical authorities")
    require(
        writer_calls[3:] == [
            module.CANONICAL_CONTRACT_PATH,
            module.CANONICAL_LOAD_PATH,
            module.CANONICAL_STATUS_PATH,
        ],
        "rollback authority order or exhaustiveness drifted",
    )
    require_snapshots_unchanged(snapshots)
    require_modes_unchanged(modes)


def main() -> int:
    module = load_target()
    module.enforce_runtime_authorities()
    module.enforce_atomic_writer_authority()

    expect_rejection(module, "repository root", lambda: swap_attr(module, "ROOT", module.CANONICAL_ROOT / "scripts"))
    expect_rejection(module, "deletion contract", lambda: swap_attr(module, "CONTRACT_PATH", module.CANONICAL_LOAD_PATH))
    expect_rejection(module, "production status", lambda: swap_attr(module, "STATUS_PATH", module.CANONICAL_LOAD_PATH))
    expect_rejection(module, "deletion validator", lambda: swap_attr(module, "DELETION_VALIDATOR", module.CANONICAL_LOAD_VALIDATOR))

    fake_run = lambda *args, **kwargs: None
    expect_rejection(module, "subprocess transport", lambda: swap_attr(module.subprocess, "run", fake_run))
    expect_rejection(
        module,
        "paired subprocess transport",
        lambda: swap_many(
            (module, "CANONICAL_SUBPROCESS_RUN", fake_run),
            (module.subprocess, "run", fake_run),
        ),
    )

    fake_replace = lambda *args, **kwargs: None
    expect_rejection(module, "atomic replacement transport", lambda: swap_attr(module.os, "replace", fake_replace))
    expect_rejection(
        module,
        "paired atomic replacement transport",
        lambda: swap_many(
            (module, "CANONICAL_OS_REPLACE", fake_replace),
            (module.os, "replace", fake_replace),
        ),
    )

    fake_writer = lambda *args, **kwargs: None
    expect_rejection(
        module,
        "atomic writer",
        lambda: swap_attr(module, "atomic_write_bytes", fake_writer),
        module.enforce_atomic_writer_authority,
    )
    expect_rejection(
        module,
        "paired atomic writer",
        lambda: swap_many(
            (module, "CANONICAL_ATOMIC_WRITE_BYTES", fake_writer),
            (module, "atomic_write_bytes", fake_writer),
        ),
        module.enforce_atomic_writer_authority,
    )

    alternate_root = module.CANONICAL_ROOT / "scripts"
    expect_rejection(
        module,
        "paired repository root",
        lambda: swap_many(
            (module, "CANONICAL_ROOT", alternate_root),
            (module, "ROOT", alternate_root),
        ),
    )
    expect_rejection(
        module,
        "paired contract authority",
        lambda: swap_many(
            (module, "CANONICAL_CONTRACT_PATH", module.CANONICAL_LOAD_PATH),
            (module, "CONTRACT_PATH", module.CANONICAL_LOAD_PATH),
        ),
    )

    with tempfile.TemporaryDirectory(prefix="memory-os-deletion-load-negative-") as tmp:
        path = Path(tmp) / "authority.json"
        path.write_bytes(b"before\n")
        os.chmod(path, 0o640)
        module.atomic_write_bytes(path, b"after\n")
        require(path.read_bytes() == b"after\n", "atomic writer payload mismatch")
        require(stat.S_IMODE(path.stat().st_mode) == 0o640, "atomic writer changed existing file mode")
        require(not list(path.parent.glob(f".{path.name}.*.tmp")), "atomic writer left temporary residue")

    exercise_rollback_failure(module)
    require_snapshots_unchanged(canonical_snapshots(module))
    require_modes_unchanged(canonical_modes(module))
    print("Deletion-under-load reconcile negative checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
