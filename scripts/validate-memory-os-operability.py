#!/usr/bin/env python3
"""Fail-closed validator for Memory OS production-operability claims."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

STATUS_PATH = Path("contracts/operations/production-operability-status.json")
AUDIT_PATH = Path("docs/memory-os-production-operability-audit-2026-07-24.md")
AUTHORITY_PATH = Path("docs/memory-os-current-authority-order-round-10-operability.md")

REQUIRED = {
    "OPS-P0-001": ("migration_rollback", True),
    "OPS-P0-002": ("incident_recovery", True),
    "OPS-P0-003": ("observability", True),
    "OPS-P0-004": ("metrics", True),
    "OPS-P0-005": ("rate_limiting", True),
    "OPS-P0-006": ("load_testing", True),
    "OPS-P0-007": ("backup_restore", True),
    "OPS-P0-008": ("version_compatibility", True),
    "OPS-P0-009": ("chaos_and_failure_drills", True),
    "OPS-P1-001": ("tracing", False),
}
ALLOWED_STATUSES = {
    "NOT_IMPLEMENTED",
    "NOT_IMPLEMENTED_OR_PROVEN",
    "MINIMAL",
    "PARTIAL",
    "PARTIAL_FOUNDATIONS_ONLY",
    "PARTIAL_PINNING_NO_POLICY",
    "COMPONENT_FAULT_INJECTION_ONLY",
    "READY",
}
REQUIRED_RULES = {
    "evidenceRequiredForReady",
    "componentFaultInjectionIsNotChaosCompletion",
    "objectVersioningIsNotBackupCompletion",
    "transactionRollbackIsNotMigrationRollbackCompletion",
    "localOrCIHealthIsNotProductionObservability",
}


class ValidationFailure(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationFailure(f"root must be an object: {path}")
    return value


def string_list(value: Any, field: str, gate: str) -> list[str]:
    if not isinstance(value, list):
        raise ValidationFailure(f"{gate}.{field} must be a list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValidationFailure(f"{gate}.{field} contains an empty or non-string value")
    if len(value) != len(set(value)):
        raise ValidationFailure(f"{gate}.{field} contains duplicates")
    return value


def validate(repo_root: Path) -> tuple[int, int, str]:
    document = load_json(repo_root / STATUS_PATH)
    if document.get("schemaVersion") != "memory-os-operability-status.0.1":
        raise ValidationFailure("unsupported schemaVersion")

    decision = document.get("productionDecision")
    if decision not in {"NO_GO", "GO"}:
        raise ValidationFailure(f"invalid productionDecision: {decision!r}")

    rules = document.get("rules")
    if not isinstance(rules, dict):
        raise ValidationFailure("rules must be an object")
    for rule in REQUIRED_RULES:
        if rules.get(rule) is not True:
            raise ValidationFailure(f"binding rule must remain true: {rule}")

    areas = document.get("areas")
    if not isinstance(areas, list) or any(not isinstance(area, dict) for area in areas):
        raise ValidationFailure("areas must be a list of objects")
    ids = [area.get("id") for area in areas]
    if len(ids) != len(set(ids)) or set(ids) != set(REQUIRED):
        raise ValidationFailure(f"gate set mismatch: {ids}")

    ready_count = 0
    for area in areas:
        gate = area["id"]
        expected_name, expected_blocking = REQUIRED[gate]
        if area.get("area") != expected_name:
            raise ValidationFailure(f"{gate}: area name changed")
        if area.get("blocking") is not expected_blocking:
            raise ValidationFailure(f"{gate}: blocking classification changed")
        if area.get("status") not in ALLOWED_STATUSES:
            raise ValidationFailure(f"{gate}: unsupported status {area.get('status')!r}")
        existing = string_list(area.get("existingEvidence", []), "existingEvidence", gate)
        missing = string_list(area.get("missingEvidence", []), "missingEvidence", gate)
        refs = string_list(area.get("evidenceRefs", []), "evidenceRefs", gate)
        for ref in refs:
            if not (repo_root / ref).is_file():
                raise ValidationFailure(f"{gate}: evidence path does not exist: {ref}")
        if area.get("status") == "READY":
            ready_count += 1
            if missing or not existing or not refs:
                raise ValidationFailure(
                    f"{gate}: READY requires no missing evidence and named repository evidence"
                )
        elif not missing:
            raise ValidationFailure(f"{gate}: incomplete status requires missingEvidence")
        if gate == "OPS-P1-001" and not str(area.get("becomesP0When", "")).strip():
            raise ValidationFailure("OPS-P1-001: becomesP0When is required")

    blocking = [area for area in areas if area.get("blocking") is True]
    all_p0_ready = all(area.get("status") == "READY" for area in blocking)
    if decision == "GO" and not all_p0_ready:
        raise ValidationFailure("GO requires every P0 gate to be READY")
    if decision == "NO_GO" and all_p0_ready:
        raise ValidationFailure("all P0 gates are READY; a dedicated decision review is required")

    try:
        audit = (repo_root / AUDIT_PATH).read_text(encoding="utf-8")
        authority = (repo_root / AUTHORITY_PATH).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing authority document: {exc.filename}") from exc

    for gate in REQUIRED:
        if gate not in audit or gate not in authority:
            raise ValidationFailure(f"authority documents omit {gate}")
    for phrase in (
        "transaction rollback is not migration rollback",
        "object versioning is not backup",
        "fault injection is not chaos completion",
        "CI green is not production observability",
    ):
        if phrase not in authority:
            raise ValidationFailure(f"Round 10 authority omits: {phrase}")
    for path in (STATUS_PATH.as_posix(), AUDIT_PATH.as_posix()):
        if path not in authority:
            raise ValidationFailure(f"Round 10 authority does not link {path}")
    if decision not in audit or decision not in authority:
        raise ValidationFailure("production decision disagrees across authority files")

    return ready_count, len(areas), decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root",
    )
    args = parser.parse_args()
    try:
        ready, total, decision = validate(args.repo_root.resolve())
    except ValidationFailure as exc:
        print(f"OPERABILITY VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"OPERABILITY VALIDATION FAILED WITH UNEXPECTED ERROR: {exc}", file=sys.stderr)
        return 2

    print("Memory OS production-operability validation PASS")
    print(f"ready gates: {ready}/{total}")
    print(f"production decision: {decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
