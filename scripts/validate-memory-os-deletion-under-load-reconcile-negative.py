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


def require_snapshots_unchanged(snapshots: dict[Path, bytes]) -> None:
    for path, payload in snapshots.items():
        require(path.read_bytes() == payload, f"canonical authority mutated after rejection: {path.relative_to(ROOT)}")


def expect_authority_rejection(
    module: ModuleType,
    label: str,
    mutate: Callable[[], Callable[[], None]],
) -> None:
    snapshots = canonical_snapshots(module)
    restore = mutate()
    try:
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            pass
        else:
            raise RuntimeError(f"authority substitution was accepted: {label}")
    finally:
        restore()
    require_snapshots_unchanged(snapshots)


def swap_attr(module: ModuleType, name: str, value: object) -> Callable[[], None]:
    original = getattr(module, name)
    setattr(module, name, value)
    return lambda: setattr(module, name, original)


def main() -> int:
    module = load_target()
    module.enforce_runtime_authorities()

    expect_authority_rejection(
        module,
        "repository root",
        lambda: swap_attr(module, "ROOT", module.CANONICAL_ROOT / "scripts"),
    )
    expect_authority_rejection(
        module,
        "deletion contract",
        lambda: swap_attr(module, "CONTRACT_PATH", module.CANONICAL_LOAD_PATH),
    )
    expect_authority_rejection(
        module,
        "production status",
        lambda: swap_attr(module, "STATUS_PATH", module.CANONICAL_LOAD_PATH),
    )
    expect_authority_rejection(
        module,
        "deletion validator",
        lambda: swap_attr(module, "DELETION_VALIDATOR", module.CANONICAL_LOAD_VALIDATOR),
    )

    original_subprocess_run = module.subprocess.run
    expect_authority_rejection(
        module,
        "subprocess transport",
        lambda: swap_attr(module.subprocess, "run", lambda *args, **kwargs: None),
    )
    require(module.subprocess.run is original_subprocess_run, "subprocess transport was not restored")

    original_os_replace = module.os.replace
    expect_authority_rejection(
        module,
        "atomic replacement transport",
        lambda: swap_attr(module.os, "replace", lambda *args, **kwargs: None),
    )
    require(module.os.replace is original_os_replace, "os.replace transport was not restored")

    expect_authority_rejection(
        module,
        "atomic writer",
        lambda: swap_attr(module, "atomic_write_bytes", lambda *args, **kwargs: None),
    )

    with tempfile.TemporaryDirectory(prefix="memory-os-deletion-load-negative-") as tmp:
        path = Path(tmp) / "authority.json"
        path.write_bytes(b"before\n")
        os.chmod(path, 0o640)
        module.atomic_write_bytes(path, b"after\n")
        require(path.read_bytes() == b"after\n", "atomic writer payload mismatch")
        require(stat.S_IMODE(path.stat().st_mode) == 0o640, "atomic writer changed existing file mode")
        require(not list(path.parent.glob(f".{path.name}.*.tmp")), "atomic writer left temporary residue")

    require_snapshots_unchanged(canonical_snapshots(module))
    print("Deletion-under-load reconcile negative checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
