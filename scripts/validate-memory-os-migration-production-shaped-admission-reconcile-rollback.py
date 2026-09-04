#!/usr/bin/env python3
"""Prove migration production admission rejects authority substitution and rolls back aggregate failures."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-migration-production-shaped-admission.py"
CONTRACT = ROOT / "contracts/operations/migration-production-shaped-admission-contract.v1.json"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
SUBSTITUTE = ROOT / "scripts/validate-memory-os-migration-evidence-registry.py"
DATA_SUBSTITUTE = ROOT / "contracts/operations/migration-evidence-registry.v1.json"


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


def require_authorities_unchanged(
    originals: dict[Path, bytes],
    modes: dict[Path, int],
    label: str,
) -> None:
    for path, expected_bytes in originals.items():
        require(path.read_bytes() == expected_bytes, f"{label}: mutated {path.relative_to(ROOT)} bytes")
        require(
            path.stat().st_mode & 0o7777 == modes[path],
            f"{label}: mutated {path.relative_to(ROOT)} mode",
        )


def executable_substitution_rejected(
    module: ModuleType,
    originals: dict[Path, bytes],
    modes: dict[Path, int],
) -> None:
    cases = (
        ("VALIDATOR", "migration admission validator authority drift"),
        ("LIFECYCLE_VALIDATOR", "migration lifecycle validator authority drift"),
        ("OPERABILITY_VALIDATOR", "operability validator authority drift"),
        ("WRITER", "migration admission writer authority drift"),
        ("RELEASE_WRITER", "release baseline writer authority drift"),
        ("RELEASE_PAIR_WRITER", "release compatibility pair writer authority drift"),
        ("GENERATION_WRITER", "environment generation writer authority drift"),
    )
    for attr, expected in cases:
        original = getattr(module, attr)
        try:
            setattr(module, attr, SUBSTITUTE)
            try:
                module.enforce_runtime_authorities()
            except module.Fail as exc:
                require(expected in str(exc), f"unexpected {attr} substitution rejection: {exc}")
            else:
                raise Fail(f"migration reconciler accepted substituted executable authority: {attr}")
            require_authorities_unchanged(originals, modes, f"{attr}: rejected executable authority")
        finally:
            setattr(module, attr, original)


def data_authority_substitution_rejected(
    module: ModuleType,
    originals: dict[Path, bytes],
    modes: dict[Path, int],
) -> None:
    cases = (
        ("CONTRACT", "migration admission contract authority drift"),
        ("REGISTRY", "migration admission registry authority drift"),
        ("WORKFLOW", "migration admission workflow authority drift"),
        ("RELEASES", "release baseline registry authority drift"),
        ("RELEASE_CONTRACT", "release baseline contract authority drift"),
        ("RELEASE_PAIRS", "release compatibility pair registry authority drift"),
        ("GENERATIONS", "environment generation registry authority drift"),
        ("LIFECYCLE", "migration lifecycle contract authority drift"),
        ("STATUS", "production operability status authority drift"),
    )
    for attr, expected in cases:
        original = getattr(module, attr)
        try:
            setattr(module, attr, DATA_SUBSTITUTE)
            try:
                module.enforce_runtime_authorities()
            except module.Fail as exc:
                require(expected in str(exc), f"unexpected {attr} substitution rejection: {exc}")
            else:
                raise Fail(f"migration reconciler accepted substituted data authority: {attr}")
            require_authorities_unchanged(originals, modes, f"{attr}: rejected data authority")
        finally:
            setattr(module, attr, original)


def successful_replace_preserves_mode(
    module: ModuleType,
    originals: dict[Path, bytes],
    modes: dict[Path, int],
) -> None:
    for path, payload in originals.items():
        module.atomic_replace_bytes(path, payload)
    require_authorities_unchanged(originals, modes, "successful atomic replace")


def aggregate_rollback_rejected(
    module: ModuleType,
    originals: dict[Path, bytes],
    modes: dict[Path, int],
) -> None:
    original_run = module.subprocess.run

    def injected_run(args, *pargs, **kwargs):
        if (
            isinstance(args, list)
            and len(args) >= 2
            and args[0] == "python"
            and args[1] == str(module.OPERABILITY_VALIDATOR)
        ):
            raise subprocess.CalledProcessError(73, args)
        return original_run(args, *pargs, **kwargs)

    module.subprocess.run = injected_run
    try:
        try:
            module.main()
        except subprocess.CalledProcessError as exc:
            require(exc.returncode == 73, "reconciler failed before the injected post-write aggregate validator")
        else:
            raise Fail("reconciler accepted an injected post-write aggregate validator failure")
    finally:
        module.subprocess.run = original_run

    require_authorities_unchanged(originals, modes, "aggregate rollback")


def main() -> int:
    module = load_reconciler()
    authorities = (CONTRACT, LIFECYCLE, STATUS)
    originals = {path: path.read_bytes() for path in authorities}
    modes = {path: path.stat().st_mode & 0o7777 for path in authorities}
    successful_replace_preserves_mode(module, originals, modes)
    executable_substitution_rejected(module, originals, modes)
    data_authority_substitution_rejected(module, originals, modes)
    aggregate_rollback_rejected(module, originals, modes)
    print("PASS: migration production-shaped reconciler preserves authority modes, rejects executable/data authority substitution, and rolls back contract, lifecycle, and status bytes/modes after aggregate validation failure")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION PRODUCTION-SHAPED ROLLBACK NEGATIVE FAILED: {exc}")
        raise SystemExit(1)