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

REQUIRED_P0 = {
    "OPS-P0-001": "migration_rollback",
    "OPS-P0-002": "incident_recovery",
    "OPS-P0-003": "observability",
    "OPS-P0-004": "metrics",
    "OPS-P0-005": "rate_limiting",
    "OPS-P0-006": "load_testing",
    "OPS-P0-007": "backup_restore",
    "OPS-P0-008": "version_compatibility",
    "OPS-P0-009": "chaos_and_failure_drills",
}
REQUIRED_P1 = {"OPS-P1-001": "tracing"}
ALLOWED_DECISIONS = {"NO_GO", "GO"}
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
ANTI_CONFLATION_RULES = {
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


def require_nonempty_strings(value: Any, field: str, area_id: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValidationFailure(f"{area_id}.{field} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ValidationFailure(f"{area_id}.{field} contains duplicates")
    return value


def validate_area(area: dict[str, Any], repo_root: Path) -> None:
    area_id = area.get("id")
    name = area.get("area")
    status = area.get("status")
    if status not in ALLOWED_STATUSES:
        raise ValidationFailure(f"{area_id}: unsupported status {status!r}")

    existing = require_nonempty_strings(area.get("existingEvidence", []), "existingEvidence", area_id)
    missing = require_nonempty_strings(area.get("missingEvidence", []), "missingEvidence", area_id)
    evidence_refs = require_nonempty_strings(area.get("evidenceRefs", []), "evidenceRefs", area_id)

    if area_id in REQUIRED_P0:
        if name != REQUIRED_P0[area_id]:
            raise ValidationFailure(f"{area_id}: expected area {REQUIRED_P0[area_id]!r}, got {name!r}")
        if area.get("blocking") is not True:
            raise ValidationFailure(f"{area_id}: P0 gate must remain blocking")
    elif area_id in REQUIRED_P1:
        if name != REQUIRED_P1[area_id]:
            raise ValidationFailure(f"{area_id}: expected area {REQUIRED_P1[area_id]!r}, got {name!r}")
        if area.get("blocking") is not False:
            raise ValidationFailure(f"{area_id}: tracing remains P1 only under the declared single-process condition")
        if not isinstance(area.get("becomesP0When"), str) or not area["becomesP0When"].strip():
            raise ValidationFailure(f"{area_id}: becomesP0When is required")
    else:
        raise ValidationFailure(f"unknown operability gate: {area_id}")

    if status == "READY":
        if missing:
            raise ValidationFailure(f"{area_id}: READY cannot retain missing evidence")
        if not existing or not evidence_refs:
            raise ValidationFailure(f"{area_id}: READY requires existingEvidence and evidenceRefs")
        for ref in evidence_refs:
            path = repo_root / ref
            if not path.is_file():
                raise ValidationFailure(f"{area_id}: evidenceRef does not exist: {ref}")
    else:
        if not missing:
            raise ValidationFailure(f"{area_id}: incomplete status requires explicit missingEvidence")
        if evidence_refs:
            for ref in evidence_refs:
                if not (repo_root / ref).is_file():
                    raise ValidationFailure(f"{area_id}: evidenceRef does not exist: {ref}")


def validate(repo_root: Path) -> tuple[int, int]:
    status_path = repo_root / STATUS_PATH
    audit_path = repo_root / AUDIT_PATH
    authority_path = repo_root / AUTHORITY_PATH
    document = load_json(status_path)

    if document.get("schemaVersion") != "memory-os-operability-status.0.2":
        raise ValidationFailure("unsupported operability schemaVersion")
    if document.get("authority") != AUTHORITY_PATH.as_posix():
        raise ValidationFailure("operability status must point to the Round 10 authority")
    decision = document.get("productionDecision")
    if decision not in ALLOWED_DECISIONS:
        raise ValidationFailure(f"invalid productionDecision: {decision!r}")

    rules = document.get("rules")
    if not isinstance(rules, dict) or rules.get("evidenceRequiredForReady") is not True:
        raise ValidationFailure("evidenceRequiredForReady must be true")
    for rule in ANTI_CONFLATION_RULES:
        if rules.get(rule) is not True:
            raise ValidationFailure(f"anti-conflation rule must remain true: {rule}")

    areas = document.get("areas")
    if not isinstance(areas, list):
        raise ValidationFailure("areas must be a list")
    ids = [area.get("id") for area in areas if isinstance(area, dict)]
    expected_ids = set(REQUIRED_P0) | set(REQUIRED_P1)
    if set(ids) != expected_ids or len(ids) != len(expected_ids):
        raise ValidationFailure(f"gate set mismatch: expected {sorted(expected_ids)}, got {sorted(ids)}")

    for area in areas:
        if not isinstance(area, dict):
            raise ValidationFailure("every area must be an object")
        validate_area(area, repo_root)

    blocking = [area for area in areas if area.get("blocking") is True]
    all_blocking_ready = all(area.get("status") == "READY" for area in blocking)
    if decision == "GO" and not all_blocking_ready:
        raise ValidationFailure("productionDecision GO requires every P0 gate to be READY")
    if decision == "NO_GO" and all_blocking_ready:
        raise ValidationFailure("all P0 gates are READY; productionDecision must be explicitly re-reviewed")

    try:
        audit = audit_path.read_text(encoding="utf-8")
        authority = authority_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing authority document: {exc.filename}") from exc

    for gate_id in expected_ids:
        if gate_id not in audit:
            raise ValidationFailure(f"audit omits gate {gate_id}")
        if gate_id not in authority:
            raise ValidationFailure(f"Round 10 authority omits gate {gate_id}")
    for phrase in (
        "transaction rollback is not migration rollback",
        "object versioning is not backup",
        "fault injection is not chaos completion",
        "CI green is not production observability",
    ):
        if phrase not in authority:
            raise ValidationFailure(f"Round 10 authority omits binding phrase: {phrase}")
    if STATUS_PATH.as_posix() not in authority or AUDIT_PATH.as_posix() not in authority:
        raise ValidationFailure("Round 10 authority must link both machine status and detailed audit")
    if decision not in audit or decision not in authority:
        raise ValidationFailure("production decision must agree across JSON, audit and authority")

    ready = sum(area.get("status") == "READY" for area in areas)
    return ready, len(areas)


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
        ready, total = validate(args.repo_root.resolve())
    except ValidationFailure as exc:
        print(f"OPERABILITY VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"OPERABILITY VALIDATION FAILED WITH UNEXPECTED ERROR: {exc}", file=sys.stderr)
        return 2

    print("Memory OS production-operability validation PASS")
    print(f"ready gates: {ready}/{total}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
