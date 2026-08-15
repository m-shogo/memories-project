#!/usr/bin/env python3
"""Fail closed if drill-request executable authorities drift."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-request.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py"
EXPECTED_ELIGIBILITY_HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
EXPECTED_OBJECTIVES_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"


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


def main() -> int:
    writer = load_module(WRITER, "memory_os_restore_drill_request_writer_authority", "drill request writer")
    reconciler = load_module(RECONCILER, "memory_os_restore_drill_request_reconcile_authority", "drill request reconciler")

    writer_eligibility = getattr(writer, "ELIGIBILITY_HELPER", None)
    writer_objectives = getattr(writer, "OBJECTIVES_WRITER", None)
    require(writer_eligibility == EXPECTED_ELIGIBILITY_HELPER, "drill request eligibility helper authority drift")
    require(writer_objectives == EXPECTED_OBJECTIVES_WRITER, "drill request recovery-objectives writer authority drift")
    canonical_repo_file(writer_eligibility, "drill request eligibility helper")
    canonical_repo_file(writer_objectives, "drill request recovery-objectives writer")

    expected_reconcile_authorities = {
        "WRITER": WRITER,
        "VALIDATOR": VALIDATOR,
        "ELIGIBILITY_HELPER": EXPECTED_ELIGIBILITY_HELPER,
        "OBJECTIVES_WRITER": EXPECTED_OBJECTIVES_WRITER,
    }
    for name, expected in expected_reconcile_authorities.items():
        actual = getattr(reconciler, name, None)
        require(actual == expected, f"drill request reconciler authority drift: {name}")
        canonical_repo_file(actual, f"drill request reconciler {name}")

    print("PASS: drill request writer and reconciler executable authorities are canonical")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
