#!/usr/bin/env python3
"""Validate every append-only source authority used by the operability inventory."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SOURCES: tuple[tuple[str, str, str, str], ...] = (
    (
        "contracts/operations/migration-production-shaped-admission-registry.v1.json",
        "scripts/register-memory-os-migration-production-shaped-admission.py",
        "memory_os_inventory_source_migration",
        "migration production-shaped admission registry",
    ),
    (
        "contracts/operations/incident-contact-routing-admission-registry.v1.json",
        "scripts/register-memory-os-incident-contact-routing.py",
        "memory_os_inventory_source_incident_contact",
        "incident contact routing registry",
    ),
    (
        "contracts/operations/observability-stack-deployment-registry.v1.json",
        "scripts/register-memory-os-observability-stack-deployment.py",
        "memory_os_inventory_source_observability_stack",
        "observability stack deployment registry",
    ),
    (
        "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json",
        "scripts/validate-memory-os-rate-limit-distributed-runtime.py",
        "memory_os_inventory_source_rate_runtime",
        "rate-limit distributed runtime registry",
    ),
    (
        "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
        "scripts/register-memory-os-production-equivalent-environment-generation.py",
        "memory_os_inventory_source_generation",
        "environment generation registry",
    ),
    (
        "contracts/operations/recovery-objectives-registry.v1.json",
        "scripts/register-memory-os-recovery-objectives.py",
        "memory_os_inventory_source_objective",
        "recovery objective registry",
    ),
    (
        "contracts/operations/backup-restore-drill-request-registry.v1.json",
        "scripts/request-memory-os-backup-restore-drill.py",
        "memory_os_inventory_source_drill_request",
        "backup/restore drill request registry",
    ),
    (
        "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
        "scripts/register-memory-os-backup-restore-generation-evidence.py",
        "memory_os_inventory_source_generation_evidence",
        "generation recovery evidence registry",
    ),
    (
        "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
        "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py",
        "memory_os_inventory_source_non_resurrection",
        "typed non-resurrection registry",
    ),
    (
        "contracts/operations/backup-restore-promotion-review-registry.v1.json",
        "scripts/register-memory-os-backup-restore-promotion-review.py",
        "memory_os_inventory_source_promotion_review",
        "human promotion review registry",
    ),
    (
        "contracts/operations/release-baseline-registry.v1.json",
        "scripts/register-memory-os-release-baseline.py",
        "memory_os_inventory_source_release",
        "release baseline registry",
    ),
    (
        "contracts/operations/release-compatibility-pair-registry.v1.json",
        "scripts/register-memory-os-release-compatibility-pair.py",
        "memory_os_inventory_source_release_pair",
        "release compatibility pair registry",
    ),
    (
        "contracts/operations/client-baseline-registry.v1.json",
        "scripts/register-memory-os-client-baseline.py",
        "memory_os_inventory_source_client",
        "client baseline registry",
    ),
    (
        "contracts/operations/parser-artifact-registry.v1.json",
        "scripts/register-memory-os-parser-artifact.py",
        "memory_os_inventory_source_parser",
        "parser artifact registry",
    ),
    (
        "contracts/operations/production-shaped-failure-drill-registry.v1.json",
        "scripts/register-memory-os-production-shaped-failure-drill.py",
        "memory_os_inventory_source_failure_drill",
        "production-shaped failure drill registry",
    ),
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"source authority missing or escapes repository: {relative}") from exc
    require(resolved == Path(relative) and path.is_file(), f"source authority path drift: {relative}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load source authority: {relative}: {exc}") from exc
    require(isinstance(value, dict), f"source authority root must be object: {relative}")
    return value


def load_validator(relative: str, module_name: str):
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"source validator missing or escapes repository: {relative}") from exc
    require(resolved == Path(relative) and path.is_file(), f"source validator path drift: {relative}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None, f"cannot load source validator: {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = getattr(module, "validate_registry_for_append", None)
    require(callable(validator), f"source validator missing validate_registry_for_append: {relative}")
    return validator


def validate_source(relative: str, validator_path: str, module_name: str, label: str) -> None:
    registry = load(relative)
    validator = load_validator(validator_path, module_name)
    try:
        validator(registry)
    except RuntimeError as exc:
        raise Fail(f"{label} invalid: {exc}") from exc


def main() -> int:
    for relative, validator_path, module_name, label in SOURCES:
        validate_source(relative, validator_path, module_name, label)
    print("Memory OS operability inventory source authority validation PASS")
    print(f"canonical append-only source registries: {len(SOURCES)}")
    print("raw registry counts accepted without owning authority validation: false")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY INVENTORY SOURCE AUTHORITY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
