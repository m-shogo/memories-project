#!/usr/bin/env python3
"""Fail closed if drill-request executable or data authorities drift."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-request.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py"
EXPECTED_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
EXPECTED_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
EXPECTED_GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
EXPECTED_OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
EXPECTED_STATUS = ROOT / "contracts/operations/production-operability-status.json"
EXPECTED_ELIGIBILITY_HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
EXPECTED_OBJECTIVES_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
EXPECTED_LOCK = ROOT / "contracts/operations/.backup-restore-drill-request.lock"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def canonical_repo_file(path: Path, field: str) -> Path:
    try:
        relative = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(relative.parts and ".." not in relative.parts and path.is_file(), f"{field} must be canonical repository file")
    return path


def load_module(path: Path, name: str, field: str):
    canonical_repo_file(path, field)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {field}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_module_authorities(module, expected: dict[str, Path], prefix: str) -> None:
    for name, canonical in expected.items():
        actual = getattr(module, name, None)
        require(actual == canonical, f"{prefix} authority drift: {name}")
        canonical_repo_file(actual, f"{prefix} {name}")


def main() -> int:
    writer = load_module(WRITER, "memory_os_restore_drill_request_writer_authority", "drill request writer")
    reconciler = load_module(RECONCILER, "memory_os_restore_drill_request_reconcile_authority", "drill request reconciler")

    require_module_authorities(
        writer,
        {
            "CONTRACT": EXPECTED_CONTRACT,
            "REGISTRY": EXPECTED_REGISTRY,
            "GEN_REGISTRY": EXPECTED_GEN_REGISTRY,
            "OBJECTIVES_REGISTRY": EXPECTED_OBJECTIVES_REGISTRY,
            "ELIGIBILITY_HELPER": EXPECTED_ELIGIBILITY_HELPER,
            "OBJECTIVES_WRITER": EXPECTED_OBJECTIVES_WRITER,
        },
        "drill request writer",
    )
    writer_lock = getattr(writer, "LOCK", None)
    require(writer_lock == EXPECTED_LOCK, "drill request writer authority drift: LOCK")
    require(writer_lock.parent == EXPECTED_REGISTRY.parent, "drill request writer lock must share registry authority directory")

    require_module_authorities(
        reconciler,
        {
            "CONTRACT": EXPECTED_CONTRACT,
            "REGISTRY": EXPECTED_REGISTRY,
            "GEN_REGISTRY": EXPECTED_GEN_REGISTRY,
            "OBJECTIVES_REGISTRY": EXPECTED_OBJECTIVES_REGISTRY,
            "STATUS": EXPECTED_STATUS,
            "WRITER": WRITER,
            "VALIDATOR": VALIDATOR,
            "ELIGIBILITY_HELPER": EXPECTED_ELIGIBILITY_HELPER,
            "OBJECTIVES_WRITER": EXPECTED_OBJECTIVES_WRITER,
        },
        "drill request reconciler",
    )

    try:
        registry = writer.load(EXPECTED_REGISTRY)
        writer.validate_registry_for_append(registry)
    except writer.Fail as exc:
        raise Fail(f"canonical drill request append-only registry authority invalid: {exc}") from exc

    print("PASS: drill request writer and reconciler executable/data/lock authorities are canonical")
    print("PASS: canonical drill request append-only registry including approval evidence digests is valid")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
