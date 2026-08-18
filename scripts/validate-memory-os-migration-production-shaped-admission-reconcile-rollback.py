#!/usr/bin/env python3
"""Prove production-shaped migration reconcile rolls back post-write aggregate failures."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-migration-production-shaped-admission.py"
CONTRACT = ROOT / "contracts/operations/migration-production-shaped-admission-contract.v1.json"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_migration_production_admission_reconcile_rollback", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load migration production admission reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_reconciler()
    originals = {path: path.read_bytes() for path in (CONTRACT, LIFECYCLE, STATUS)}

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=".migration-production-post-operability-",
        suffix=".py",
        dir=ROOT / "scripts",
        delete=False,
    ) as handle:
        handle.write("raise SystemExit(73)\n")
        failing_validator = Path(handle.name)

    try:
        module.OPERABILITY_VALIDATOR = failing_validator
        try:
            module.main()
        except subprocess.CalledProcessError as exc:
            require(exc.returncode == 73, "reconciler failed before the injected post-write aggregate validator")
        else:
            raise Fail("reconciler accepted an injected post-write aggregate validator failure")
    finally:
        failing_validator.unlink(missing_ok=True)

    for path, expected in originals.items():
        require(path.read_bytes() == expected, f"reconciler failed to roll back {path.relative_to(ROOT)}")

    print("PASS: migration production-shaped admission reconciler rolls back contract, lifecycle, and status after post-write aggregate validation failure")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION PRODUCTION-SHAPED ROLLBACK NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
