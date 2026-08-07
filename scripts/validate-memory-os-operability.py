#!/usr/bin/env python3
"""Fail-closed validator for Memory OS production-operability claims."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

STATUS_PATH = Path("contracts/operations/production-operability-status.json")
AUDIT_PATH = Path("docs/memory-os-production-operability-audit-2026-07-24.md")
AUTHORITY_PATH = Path("docs/memory-os-current-authority-order-round-10-operability.md")
LIVE_POSTGRES_CONTRACT_PATH = Path(
    "contracts/operations/live-postgres-load-scenario-contract.v1.json"
)
LIVE_OBJECT_CONTRACT_PATH = Path(
    "contracts/operations/live-object-load-scenario-contract.v1.json"
)
LONG_SOAK_CONTRACT_PATH = Path(
    "contracts/operations/sustained-local-soak-contract.v1.json"
)
LONG_SOAK_REVIEW_PATH = Path(
    "docs/fixtures/memory-os-operability/sustained-local-soak-trend-review.v1.json"
)
LIVE_LOAD_FOUNDATION_REFS = {
    "services/import-api/internal/httpserver/live_load_test.go",
    "services/import-api/internal/httpserver/live_object_load_test.go",
    LIVE_POSTGRES_CONTRACT_PATH.as_posix(),
    LIVE_OBJECT_CONTRACT_PATH.as_posix(),
    "scripts/validate-memory-os-live-load.py",
    "scripts/validate-memory-os-live-object-load.py",
    ".github/workflows/regenerate-live-postgres-load-results.yml",
}

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


def validate_date(value: Any, field: str) -> None:
    if not isinstance(value, str):
        raise ValidationFailure(f"{field} must be an ISO date")
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationFailure(f"{field} must be an ISO date") from exc
    if parsed > dt.date.today():
        raise ValidationFailure(f"{field} cannot be in the future")


def validate_local_load_contract(
    repo_root: Path,
    relative_path: Path,
    expected_mode: str,
) -> dict[str, Any]:
    contract = load_json(repo_root / relative_path)
    if contract.get("dependencyMode") != expected_mode:
        raise ValidationFailure(
            f"{relative_path}: dependencyMode must remain {expected_mode}"
        )
    if contract.get("productionEvidence") is not False:
        raise ValidationFailure(
            f"{relative_path}: ephemeral dependency evidence must not claim production"
        )
    readiness = contract.get("readiness")
    if not isinstance(readiness, dict):
        raise ValidationFailure(f"{relative_path}: readiness must be an object")
    for claim in (
        "sustainedSoakEvidence",
        "capacityBoundaryEstablished",
        "productionEquivalentDependencies",
    ):
        if readiness.get(claim) is not False:
            raise ValidationFailure(
                f"{relative_path}: local checkpoint cannot claim {claim}"
            )
    return contract


def local_sustained_soak_completed(repo_root: Path, refs: list[str]) -> bool:
    contract_path = repo_root / LONG_SOAK_CONTRACT_PATH
    review_path = repo_root / LONG_SOAK_REVIEW_PATH
    if not contract_path.is_file() or not review_path.is_file():
        return False
    if LONG_SOAK_CONTRACT_PATH.as_posix() not in refs or LONG_SOAK_REVIEW_PATH.as_posix() not in refs:
        return False
    contract = load_json(contract_path)
    readiness = contract.get("readiness")
    if not isinstance(readiness, dict):
        return False
    review = load_json(review_path)
    return (
        readiness.get("secondIndependentLongRunCommitted") is True
        and readiness.get("trendReviewCompleted") is True
        and readiness.get("localSustainedSoakEvidence") is True
        and readiness.get("productionSustainedSoakEvidence") is False
        and readiness.get("leakProofAvailable") is False
        and review.get("trendReviewCompleted") is True
        and review.get("localSustainedSoakEvidenceEligible") is True
        and review.get("leakProof") is False
        and review.get("productionEvidence") is False
        and review.get("productionReady") is False
    )


def validate_load_gate(
    repo_root: Path,
    area: dict[str, Any],
    existing: list[str],
    missing: list[str],
    refs: list[str],
) -> None:
    ref_set = set(refs)
    absent = LIVE_LOAD_FOUNDATION_REFS - ref_set
    if absent:
        raise ValidationFailure(
            "OPS-P0-006: live dependency foundations omitted from evidenceRefs: "
            + ", ".join(sorted(absent))
        )

    postgres_contract = validate_local_load_contract(
        repo_root,
        LIVE_POSTGRES_CONTRACT_PATH,
        "LOCAL_POSTGRES",
    )
    object_contract = validate_local_load_contract(
        repo_root,
        LIVE_OBJECT_CONTRACT_PATH,
        "LOCAL_POSTGRES_MINIO",
    )

    if not any("live PostgreSQL" in item for item in existing):
        raise ValidationFailure(
            "OPS-P0-006: existingEvidence must identify the live PostgreSQL checkpoint"
        )
    if not any("live MinIO" in item for item in existing):
        raise ValidationFailure(
            "OPS-P0-006: existingEvidence must identify the live MinIO checkpoint"
        )

    if area.get("status") == "READY":
        # These contracts intentionally describe ephemeral local dependencies.
        # Their PASS results improve confidence but never establish a production
        # capacity boundary, production object-store controls or dependency
        # equivalence. A future READY transition must add distinct production
        # evidence rather than relabel these local contracts.
        if (
            postgres_contract.get("productionEvidence") is False
            or object_contract.get("productionEvidence") is False
        ):
            raise ValidationFailure(
                "OPS-P0-006: local PostgreSQL/MinIO evidence cannot make load_testing READY"
            )

    if area.get("status") != "READY":
        for phrase in ("capacity boundary", "production-equivalent"):
            if not any(phrase in item for item in missing):
                raise ValidationFailure(
                    f"OPS-P0-006: missingEvidence must retain the open gap: {phrase}"
                )

        if local_sustained_soak_completed(repo_root, refs):
            if not any(
                "production-shaped" in item and "soak" in item
                for item in missing
            ):
                raise ValidationFailure(
                    "OPS-P0-006: completed local repeated soak must retain a distinct production-shaped soak gap"
                )
            if not any(
                "leak/stability" in item and "independent" in item
                for item in missing
            ):
                raise ValidationFailure(
                    "OPS-P0-006: local descriptive trend review must retain independent leak/stability review gap"
                )
        elif not any("sustained soak" in item for item in missing):
            raise ValidationFailure(
                "OPS-P0-006: missingEvidence must retain the open gap: sustained soak"
            )


def validate(repo_root: Path) -> tuple[int, int, str]:
    document = load_json(repo_root / STATUS_PATH)
    if document.get("schemaVersion") != "memory-os-operability-status.0.1":
        raise ValidationFailure("unsupported schemaVersion")
    validate_date(document.get("asOf"), "asOf")

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
        if gate == "OPS-P0-006":
            validate_load_gate(repo_root, area, existing, missing, refs)

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
        if gate not in authority:
            raise ValidationFailure(f"Round 10 authority omits {gate}")
    for gate in (gate for gate in REQUIRED if gate.startswith("OPS-P0-")):
        if gate not in audit:
            raise ValidationFailure(f"production audit omits {gate}")

    return ready_count, len(blocking), decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    ready_count, p0_count, decision = validate(args.repo_root.resolve())
    print("Memory OS production operability validation PASS")
    print(f"P0 ready: {ready_count}/{p0_count}")
    print(f"production decision: {decision}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"OPERABILITY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
