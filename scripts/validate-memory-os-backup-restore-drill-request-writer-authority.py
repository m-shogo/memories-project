#!/usr/bin/env python3
"""Fail closed if drill-request writer executable authorities drift."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
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


def load_writer():
    canonical_repo_file(WRITER, "drill request writer")
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_request_writer_authority", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load drill request writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    writer = load_writer()
    eligibility = getattr(writer, "ELIGIBILITY_HELPER", None)
    objectives = getattr(writer, "OBJECTIVES_WRITER", None)
    require(eligibility == EXPECTED_ELIGIBILITY_HELPER, "drill request eligibility helper authority drift")
    require(objectives == EXPECTED_OBJECTIVES_WRITER, "drill request recovery-objectives writer authority drift")
    canonical_repo_file(eligibility, "drill request eligibility helper")
    canonical_repo_file(objectives, "drill request recovery-objectives writer")
    print("PASS: drill request writer executable authorities are canonical")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
