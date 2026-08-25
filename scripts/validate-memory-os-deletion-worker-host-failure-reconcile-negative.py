#!/usr/bin/env python3
"""Focused fail-closed checks for host-failure admission reconciliation."""

from __future__ import annotations

import importlib.util
import os
import stat
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/reconcile-memory-os-deletion-worker-host-failure.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_target() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_host_failure_reconcile_negative", TARGET)
    require(spec is not None and spec.loader is not None, "cannot load host-failure reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def snapshots(module: ModuleType) -> dict[Path, bytes]:
    return {
        module.CANONICAL_CONTRACT: module.CANONICAL_CONTRACT.read_bytes(),
        module.CANONICAL_STATUS: module.CANONICAL_STATUS.read_bytes(),
    }


def assert_unchanged(values: dict[Path, bytes]) -> None:
    for path, payload in values.items():
        require(path.read_bytes() == payload, f"canonical authority mutated: {path.relative_to(ROOT)}")


def expect_rejection(
    module: ModuleType,
    label: str,
    mutate: Callable[[], Callable[[], None]],
    check: Callable[[], None],
) -> None:
    before = snapshots(module)
    restore = mutate()
    try:
        try:
            check()
        except module.Fail:
            pass
        else:
            raise RuntimeError(f"authority substitution accepted: {label}")
    finally:
        restore()
    assert_unchanged(before)


def main() -> int:
    module = load_target()
    module.validate_executable_authorities()
    module.validate_atomic_writer_authority()

    alternate_root = module.CANONICAL_ROOT / "scripts"
    expect_rejection(
        module,
        "paired repository root",
        lambda: swap_many((module, "CANONICAL_ROOT", alternate_root), (module, "ROOT", alternate_root)),
        module.validate_data_authorities,
    )
    expect_rejection(
        module,
        "paired contract authority",
        lambda: swap_many((module, "CANONICAL_CONTRACT", module.CANONICAL_LOAD), (module, "CONTRACT", module.CANONICAL_LOAD)),
        module.validate_data_authorities,
    )

    fake_run = lambda *args, **kwargs: None
    expect_rejection(
        module,
        "paired subprocess transport",
        lambda: swap_many((module, "CANONICAL_SUBPROCESS_RUN", fake_run), (module.subprocess, "run", fake_run)),
        module.validate_executable_authorities,
    )

    fake_replace = lambda *args, **kwargs: None
    expect_rejection(
        module,
        "paired replacement transport",
        lambda: swap_many((module, "CANONICAL_OS_REPLACE", fake_replace), (module.os, "replace", fake_replace)),
        module.validate_executable_authorities,
    )

    fake_spec = lambda *args, **kwargs: None
    expect_rejection(
        module,
        "paired module spec loader",
        lambda: swap_many(
            (module, "CANONICAL_SPEC_FROM_FILE_LOCATION", fake_spec),
            (module.importlib.util, "spec_from_file_location", fake_spec),
        ),
        module.validate_executable_authorities,
    )

    fake_module = lambda *args, **kwargs: None
    expect_rejection(
        module,
        "paired module loader",
        lambda: swap_many(
            (module, "CANONICAL_MODULE_FROM_SPEC", fake_module),
            (module.importlib.util, "module_from_spec", fake_module),
        ),
        module.validate_executable_authorities,
    )

    fake_writer = lambda *args, **kwargs: None
    expect_rejection(
        module,
        "paired atomic writer",
        lambda: swap_many(
            (module, "CANONICAL_ATOMIC_WRITE_BYTES", fake_writer),
            (module, "atomic_write_bytes", fake_writer),
        ),
        module.validate_atomic_writer_authority,
    )

    with tempfile.TemporaryDirectory(prefix="memory-os-host-failure-mode-") as tmp:
        target = Path(tmp) / "authority.json"
        target.write_bytes(b"before\n")
        os.chmod(target, 0o640)
        module.atomic_write_bytes(target, b"after\n")
        require(target.read_bytes() == b"after\n", "atomic host-failure payload mismatch")
        require(stat.S_IMODE(target.stat().st_mode) == 0o640, "atomic host-failure writer changed file mode")
        require(not list(target.parent.glob(f".{target.name}.*.tmp")), "atomic host-failure writer left temp residue")

    assert_unchanged(snapshots(module))
    print("PASS: host-failure reconcile authority transaction is fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
