#!/usr/bin/env python3
"""Fail closed if generation-evidence executable or data authority is substituted."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
EXPECTED_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
EXPECTED_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
EXPECTED_GENERATION_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
EXPECTED_GENERATION_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
EXPECTED_OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
EXPECTED_OBJECTIVES_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
EXPECTED_DRILL_REQUEST_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
EXPECTED_DRILL_REQUEST_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
EXPECTED_DRILL_REQUEST_WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
EXPECTED_NON_RESURRECTION_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
EXPECTED_NON_RESURRECTION_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
EXPECTED_NON_RESURRECTION_WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer() -> Any:
    require(WRITER.is_file(), "canonical generation-evidence writer missing")
    spec = importlib.util.spec_from_file_location("memory_os_generation_evidence_writer_authority", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load canonical generation-evidence writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_authority(writer: Any, name: str, expected: Path, label: str) -> None:
    actual = getattr(writer, name, None)
    require(actual == expected, f"generation-evidence {label} authority drift")
    canonical_repo_file = getattr(writer, "canonical_repo_file", None)
    require(callable(canonical_repo_file), "canonical repository authority guard missing")
    canonical_repo_file(actual, label)


def main() -> int:
    writer = load_writer()

    for name, expected, label in (
        ("CONTRACT", EXPECTED_CONTRACT, "contract"),
        ("REGISTRY", EXPECTED_REGISTRY, "registry"),
        ("GEN_REGISTRY", EXPECTED_GENERATION_REGISTRY, "environment-generation registry"),
        ("GEN_WRITER", EXPECTED_GENERATION_WRITER, "environment-generation writer"),
        ("OBJECTIVES_REGISTRY", EXPECTED_OBJECTIVES_REGISTRY, "recovery-objectives registry"),
        ("OBJECTIVES_WRITER", EXPECTED_OBJECTIVES_WRITER, "recovery-objectives writer"),
        ("DRILL_REQUEST_CONTRACT", EXPECTED_DRILL_REQUEST_CONTRACT, "drill-request contract"),
        ("DRILL_REQUEST_REGISTRY", EXPECTED_DRILL_REQUEST_REGISTRY, "drill-request registry"),
        ("DRILL_REQUEST_WRITER", EXPECTED_DRILL_REQUEST_WRITER, "drill-request writer"),
        ("NON_RESURRECTION_CONTRACT", EXPECTED_NON_RESURRECTION_CONTRACT, "typed non-resurrection contract"),
        ("NON_RESURRECTION_REGISTRY", EXPECTED_NON_RESURRECTION_REGISTRY, "typed non-resurrection registry"),
        ("NON_RESURRECTION_WRITER", EXPECTED_NON_RESURRECTION_WRITER, "typed non-resurrection writer"),
    ):
        require_authority(writer, name, expected, label)

    print("Memory OS generation-evidence executable/data authority validation PASS")
    print("environment-generation authority substitution accepted: false")
    print("recovery-objectives authority substitution accepted: false")
    print("drill-request authority substitution accepted: false")
    print("typed non-resurrection authority substitution accepted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE WRITER AUTHORITY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
