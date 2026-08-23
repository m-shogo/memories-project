#!/usr/bin/env python3
"""Fail closed if restore-drill preflight data or executable authorities drift."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-preflight.py"
WORKFLOW = ROOT / ".github/workflows/backup-restore-drill-preflight.yml"
EXPECTED_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
EXPECTED_GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
EXPECTED_OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
EXPECTED_DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
EXPECTED_STATUS = ROOT / "contracts/operations/production-operability-status.json"
EXPECTED_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
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
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(lexical == resolved and path.is_file(), f"{field} must be canonical repository file")
    return path


def load_module(path: Path, name: str, field: str):
    canonical_repo_file(path, field)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {field}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_module_authority(module: object, name: str, expected: Path, field: str) -> None:
    actual = getattr(module, name, None)
    require(actual == expected, f"{field} authority drift: {name}")
    canonical_repo_file(actual, f"{field} {name}")


def require_atomic_diagnostic_publication() -> None:
    canonical_repo_file(WORKFLOW, "restore drill preflight workflow")
    text = WORKFLOW.read_text(encoding="utf-8")
    required = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required if fragment not in text]
    require(not missing, f"restore drill preflight diagnostic publication is not crash-safe: missing {missing}")
    require(
        "path.write_text(json.dumps(value" not in text,
        "restore drill preflight diagnostic publication regressed to direct write_text",
    )


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
        require_module_authority(validator, name, expected, "restore drill preflight validator")

    expected_reconciler_authorities = {
        "CONTRACT": EXPECTED_CONTRACT,
        "GEN_REGISTRY": EXPECTED_GEN_REGISTRY,
        "OBJECTIVES": EXPECTED_OBJECTIVES,
        "DRILL_REGISTRY": EXPECTED_DRILL_REGISTRY,
        "VALIDATOR_MODULE": VALIDATOR,
        "OPERABILITY_VALIDATOR": EXPECTED_OPERABILITY_VALIDATOR,
        "STATUS": EXPECTED_STATUS,
    }
    for name, expected in expected_reconciler_authorities.items():
        require_module_authority(reconciler, name, expected, "restore drill preflight reconciler")

    require_atomic_diagnostic_publication()
    print("PASS: restore drill preflight data/executable authorities are canonical")
    print(f"validator executable authorities checked: {len(expected_validator_authorities)}")
    print(f"reconciler data/executable authorities checked: {len(expected_reconciler_authorities)}")
    print("crash-safe failure diagnostic publication required: true")
    print("production evidence created: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
