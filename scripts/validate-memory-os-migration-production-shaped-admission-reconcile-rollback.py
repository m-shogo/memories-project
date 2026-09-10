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


def rollback_failure_preserves_primary_and_continues(
    module: ModuleType,
    originals: dict[Path, bytes],
    modes: dict[Path, int],
) -> None:
    original_run = module.subprocess.run
    original_atomic_replace = module.atomic_replace_bytes
    rollback_attempts: list[Path] = []
    post_write_failure_seen = False
    first_restore_failure_injected = False

    def injected_run(args, *pargs, **kwargs):
        nonlocal post_write_failure_seen
        if (
            isinstance(args, list)
            and len(args) >= 2
            and args[0] == "python"
            and args[1] == str(module.OPERABILITY_VALIDATOR)
        ):
            post_write_failure_seen = True
            raise subprocess.CalledProcessError(73, args)
        return original_run(args, *pargs, **kwargs)

    def injected_atomic_replace(path: Path, payload: bytes) -> None:
        nonlocal first_restore_failure_injected
        if post_write_failure_seen and path in originals and payload == originals[path]:
            rollback_attempts.append(path)
            original_atomic_replace(path, payload)
            if path == CONTRACT and not first_restore_failure_injected:
                first_restore_failure_injected = True
                raise OSError("injected migration rollback restore rejection")
            return
        original_atomic_replace(path, payload)

    module.subprocess.run = injected_run
    module.atomic_replace_bytes = injected_atomic_replace
    try:
        try:
            module.main()
        except module.Fail as exc:
            text = str(exc)
            require("returned non-zero exit status 73" in text, f"primary validator failure was lost: {exc}")
            require("rollback incomplete" in text, f"rollback incompleteness was not reported: {exc}")
            require(
                "injected migration rollback restore rejection" in text,
                f"rollback restore failure was lost: {exc}",
            )
        else:
            raise Fail("reconciler accepted aggregate validator plus rollback restore failure")
    finally:
        module.subprocess.run = original_run
        module.atomic_replace_bytes = original_atomic_replace

    require(
        rollback_attempts == list(originals),
        f"rollback did not attempt every authority after the first restore failure: {rollback_attempts}",
    )
    require_authorities_unchanged(originals, modes, "rollback failure diagnostics")


def main() -> int:
    module = load_reconciler()
    authorities = (CONTRACT, LIFECYCLE, STATUS)
    originals = {path: path.read_bytes() for path in authorities}
    modes = {path: path.stat().st_mode & 0o7777 for path in authorities}
    successful_replace_preserves_mode(module, originals, modes)
    executable_substitution_rejected(module, originals, modes)
    data_authority_substitution_rejected(module, originals, modes)
    aggregate_rollback_rejected(module, originals, modes)
    rollback_failure_preserves_primary_and_continues(module, originals, modes)
    print("PASS: migration production-shaped reconciler preserves authority modes, rejects executable/data authority substitution, rolls back contract/lifecycle/status after aggregate failure, and preserves primary plus exhaustive rollback diagnostics when restore fails")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION PRODUCTION-SHAPED ROLLBACK NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
