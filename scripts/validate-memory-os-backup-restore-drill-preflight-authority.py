#!/usr/bin/env python3
"""Fail closed if restore-drill preflight executable authorities drift."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-preflight.py"
EXPECTED_ELIGIBILITY_HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
EXPECTED_GEN_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-generation.py"
EXPECTED_OBJECTIVE_VALIDATOR = ROOT / "scripts/validate-memory-os-recovery-objectives.py"
EXPECTED_DRILL_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py"


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
    validator = load_module(VALIDATOR, "memory_os_restore_drill_preflight_authority_validator", "restore drill preflight validator")
    reconciler = load_module(RECONCILER, "memory_os_restore_drill_preflight_authority_reconciler", "restore drill preflight reconciler")

    expected_validator_authorities = {
        "ELIGIBILITY_HELPER": EXPECTED_ELIGIBILITY_HELPER,
        "GEN_VALIDATOR": EXPECTED_GEN_VALIDATOR,
        "OBJECTIVE_VALIDATOR": EXPECTED_OBJECTIVE_VALIDATOR,
        "DRILL_VALIDATOR": EXPECTED_DRILL_VALIDATOR,
    }
    for name, expected in expected_validator_authorities.items():
        actual = getattr(validator, name, None)
        require(actual == expected, f"restore drill preflight validator authority drift: {name}")
        canonical_repo_file(actual, f"restore drill preflight validator {name}")

    actual_validator_module = getattr(reconciler, "VALIDATOR_MODULE", None)
    require(actual_validator_module == VALIDATOR, "restore drill preflight reconciler validator authority drift")
    canonical_repo_file(actual_validator_module, "restore drill preflight reconciler validator")

    print("PASS: restore drill preflight executable authorities are canonical")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
