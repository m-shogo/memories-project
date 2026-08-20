#!/usr/bin/env python3
"""Validate every source authority used by the operability inventory."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUEST = "contracts/operations/requests/operability-admission-inventory.v1.json"
REQUEST_FIELDS = {
    "schemaVersion",
    "requestId",
    "operation",
    "productionTraffic",
    "productionCredentials",
    "productionEvidence",
    "constraints",
}
REQUEST_CONSTRAINTS = {
    "deterministicOutputRequired",
    "canonicalRegistryCountsOnly",
    "foundationImplementationMustNotEqualProductionEvidence",
    "productionDecisionMustRemainNoGo",
    "registeredGenerationCountMustRemainDistinctFromSemanticPreflightEligibility",
    "approvedRecoveryObjectiveCountMustDeriveFromTypedHumanApprovalAuthority",
    "recoveryCandidateRequiresIndependentEvidenceReview",
    "recoveryCandidateMustNotImplyHumanProductionPromotionReview",
    "recoveryCandidateMustNotAuthorizeProductionPromotion",
    "humanProductionPromotionAuthorityMustRemainSeparate",
}

SOURCES: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "contracts/operations/migration-production-shaped-admission-registry.v1.json",
        "scripts/register-memory-os-migration-production-shaped-admission.py",
        "memory_os_inventory_source_migration",
        "validate_registry_for_append",
        "migration production-shaped admission registry",
    ),
    (
        "contracts/operations/incident-contact-routing-admission-registry.v1.json",
        "scripts/register-memory-os-incident-contact-routing.py",
        "memory_os_inventory_source_incident_contact",
        "validate_registry_for_append",
        "incident contact routing registry",
    ),
    (
        "contracts/operations/observability-stack-deployment-registry.v1.json",
        "scripts/register-memory-os-observability-stack-deployment.py",
        "memory_os_inventory_source_observability_stack",
        "validate_registry_for_append",
        "observability stack deployment registry",
    ),
    (
        "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json",
        "scripts/validate-memory-os-rate-limit-distributed-runtime.py",
        "memory_os_inventory_source_rate_runtime",
        "validate_registry_for_append",
        "rate-limit distributed runtime registry",
    ),
    (
        "contracts/operations/sustained-soak-independent-review-registry.v1.json",
        "scripts/register-memory-os-sustained-soak-independent-review.py",
        "memory_os_inventory_source_sustained_soak_review",
        "validate_registry_for_append",
        "sustained-soak independent review registry",
    ),
    (
        "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
        "scripts/register-memory-os-production-equivalent-environment-generation.py",
        "memory_os_inventory_source_generation",
        "validate_registry_for_append",
        "environment generation registry",
    ),
    (
        "contracts/operations/recovery-objectives-registry.v1.json",
        "scripts/register-memory-os-recovery-objectives.py",
        "memory_os_inventory_source_objective",
        "validate_registry_for_append",
        "recovery objective registry",
    ),
    (
        "contracts/operations/backup-restore-drill-request-registry.v1.json",
        "scripts/request-memory-os-backup-restore-drill.py",
        "memory_os_inventory_source_drill_request",
        "validate_registry_for_append",
        "backup/restore drill request registry",
    ),
    (
        "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
        "scripts/register-memory-os-backup-restore-generation-evidence.py",
        "memory_os_inventory_source_generation_evidence",
        "validate_registry_for_append",
        "generation recovery evidence registry",
    ),
    (
        "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
        "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py",
        "memory_os_inventory_source_non_resurrection",
        "validate_registry_for_append",
        "typed non-resurrection registry",
    ),
    (
        "contracts/operations/backup-restore-promotion-review-registry.v1.json",
        "scripts/register-memory-os-backup-restore-promotion-review.py",
        "memory_os_inventory_source_promotion_review",
        "validate_registry_for_append",
        "human promotion review registry",
    ),
    (
        "contracts/operations/release-baseline-registry.v1.json",
        "scripts/register-memory-os-release-baseline.py",
        "memory_os_inventory_source_release",
        "validate_registry_for_append",
        "release baseline registry",
    ),
    (
        "contracts/operations/release-compatibility-pair-registry.v1.json",
        "scripts/register-memory-os-release-compatibility-pair.py",
        "memory_os_inventory_source_release_pair",
        "validate_registry_for_append",
        "release compatibility pair registry",
    ),
    (
        "contracts/operations/client-baseline-registry.v1.json",
        "scripts/register-memory-os-client-baseline.py",
        "memory_os_inventory_source_client",
        "validate_registry_for_append",
        "client baseline registry",
    ),
    (
        "contracts/operations/parser-artifact-registry.v1.json",
        "scripts/register-memory-os-parser-artifact.py",
        "memory_os_inventory_source_parser",
        "validate_registry_for_append",
        "parser artifact registry",
    ),
    (
        "contracts/operations/production-shaped-failure-drill-registry.v1.json",
        "scripts/register-memory-os-production-shaped-failure-drill.py",
        "memory_os_inventory_source_failure_drill",
        "validate_registry_for_append",
        "production-shaped failure drill registry",
    ),
)

COMMAND_SOURCES: tuple[tuple[str, str, str], ...] = (
    (
        "scripts/validate-memory-os-backup-restore-generation-binding.py",
        "memory_os_inventory_source_backup_generation_binding",
        "backup/restore generation binding authority",
    ),
    (
        "scripts/validate-memory-os-backup-restore-drill-request.py",
        "memory_os_inventory_source_backup_drill_request_contract",
        "backup/restore drill request derived authority",
    ),
    (
        "scripts/validate-memory-os-backup-restore-drill-preflight.py",
        "memory_os_inventory_source_backup_drill_preflight",
        "backup/restore drill preflight authority",
    ),
    (
        "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py",
        "memory_os_inventory_source_backup_non_resurrection_contract",
        "backup/restore typed non-resurrection authority",
    ),
)

DOMAIN_REJECTIONS = {"Fail", "Failure", "RegistrationFailure"}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def exact_success(result: Any, label: str) -> None:
    require(
        isinstance(result, int) and not isinstance(result, bool) and result == 0,
        f"{label} invalid: validator exit {result}",
    )


def validate_registry_result(result: Any, label: str) -> None:
    require(not isinstance(result, bool), f"{label} invalid: registry validator returned boolean {result!r}")
    require(
        result is None or isinstance(result, (list, dict, tuple, set)),
        f"{label} invalid: unsupported registry validator result {result!r}",
    )


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


def validate_inventory_request() -> None:
    request = load(REQUEST)
    require(set(request) == REQUEST_FIELDS, "operability inventory request field shape drift")
    require(request.get("schemaVersion") == "memory-os-operation-request.v1", "operability inventory request schema drift")
    require(request.get("requestId") == "operability-admission-inventory-20260807-v1", "operability inventory request identity drift")
    require(request.get("operation") == "GENERATE_OPERABILITY_ADMISSION_INVENTORY", "operability inventory request operation drift")
    for field in ("productionTraffic", "productionCredentials", "productionEvidence"):
        require(request.get(field) is False, f"operability inventory request cannot enable {field}")
    constraints = request.get("constraints")
    require(isinstance(constraints, dict), "operability inventory request constraints missing")
    require(set(constraints) == REQUEST_CONSTRAINTS, "operability inventory request constraint shape drift")
    for field in REQUEST_CONSTRAINTS:
        require(constraints.get(field) is True, f"operability inventory request constraint must remain true: {field}")


def load_validator(relative: str, module_name: str, function_name: str):
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
    validator = getattr(module, function_name, None)
    require(callable(validator), f"source validator missing {function_name}: {relative}")
    return validator


def validate_source(
    relative: str,
    validator_path: str,
    module_name: str,
    function_name: str,
    label: str,
) -> None:
    registry = load(relative)
    validator = load_validator(validator_path, module_name, function_name)
    try:
        result = validator(registry)
    except RuntimeError as exc:
        if exc.__class__.__name__ in DOMAIN_REJECTIONS:
            raise Fail(f"{label} invalid: {exc}") from exc
        raise
    validate_registry_result(result, label)


def validate_human_tabletop_source() -> int:
    validator = load_validator(
        "scripts/validate-memory-os-incident-human-tabletops.py",
        "memory_os_inventory_source_human_tabletop",
        "validate_ledger",
    )
    try:
        scenarios = validator()
    except RuntimeError as exc:
        if exc.__class__.__name__ in DOMAIN_REJECTIONS:
            raise Fail(f"human incident tabletop ledger invalid: {exc}") from exc
        raise
    require(isinstance(scenarios, set), "human incident tabletop validator result invalid")
    require(all(isinstance(scenario, str) for scenario in scenarios), "human incident tabletop scenario authority invalid")
    return len(scenarios)


def validate_load_source() -> None:
    validator = load_validator(
        "scripts/validate-memory-os-load.py",
        "memory_os_inventory_source_load",
        "main",
    )
    try:
        result = validator()
    except RuntimeError as exc:
        if exc.__class__.__name__ in DOMAIN_REJECTIONS:
            raise Fail(f"load-test source authority invalid: {exc}") from exc
        raise
    exact_success(result, "load-test source authority")


def validate_command_source(relative: str, module_name: str, label: str) -> None:
    validator = load_validator(relative, module_name, "main")
    try:
        result = validator()
    except RuntimeError as exc:
        if exc.__class__.__name__ in DOMAIN_REJECTIONS:
            raise Fail(f"{label} invalid: {exc}") from exc
        raise
    exact_success(result, label)


def main() -> int:
    validate_inventory_request()
    human_tabletop_count = validate_human_tabletop_source()
    validate_load_source()
    for relative, module_name, label in COMMAND_SOURCES:
        validate_command_source(relative, module_name, label)
    for relative, validator_path, module_name, function_name, label in SOURCES:
        validate_source(relative, validator_path, module_name, function_name, label)
    print("Memory OS operability inventory source authority validation PASS")
    print("operability inventory generation request authority: PASS")
    print(f"canonical append-only source registries: {len(SOURCES)}")
    print(f"validated backup/restore derived authorities: {len(COMMAND_SOURCES)}")
    print(f"validated human tabletop scenarios: {human_tabletop_count}")
    print("canonical load contract/results/status validation: PASS")
    print("boolean validator exit codes accepted as success: false")
    print("scalar registry validator returns accepted as success: false")
    print("raw human tabletop filename counts accepted without canonical ledger validation: false")
    print("raw load readiness/counts accepted without canonical load validation: false")
    print("raw backup/restore derived counts accepted without canonical validators: false")
    print("raw registry counts accepted without owning authority validation: false")
    print("request production traffic/credentials/evidence enabled: false")
    print("request human-approved recovery-objective constraint bypassed: false")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY INVENTORY SOURCE AUTHORITY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)