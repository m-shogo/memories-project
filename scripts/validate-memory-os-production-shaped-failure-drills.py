#!/usr/bin/env python3
"""Validate generation-bound production-shaped failure-drill registry."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-shaped-failure-drill-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-shaped-failure-drill-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-production-shaped-failure-drill.py"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
LOCK = ROOT / "contracts/operations/.production-shaped-failure-drill.lock"
EXPECTED_REGISTRY_FIELDS = {
    "schemaVersion",
    "appendOnly",
    "registeredDrillCount",
    "productionEquivalentDrillCount",
    "productionDrillCount",
    "evidenceDigestsByDrillId",
    "drills",
    "productionReady",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_count(value: Any, expected: int, field: str) -> None:
    require(isinstance(value, int) and not isinstance(value, bool), f"{field} must be integer, not boolean")
    require(value == expected, f"{field} drift")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_writer() -> ModuleType:
    return load_module(WRITER, "memory_os_production_failure_writer")


def validate_writer_authority(writer: ModuleType) -> None:
    require(writer.ROOT.resolve() == ROOT.resolve(), "failure-drill writer root authority drift")
    require(writer.CONTRACT.resolve() == CONTRACT.resolve(), "failure-drill writer contract authority drift")
    require(writer.REGISTRY.resolve() == REGISTRY.resolve(), "failure-drill writer registry authority drift")
    require(writer.GEN_REGISTRY.resolve() == GEN_REGISTRY.resolve(), "failure-drill writer generation registry authority drift")
    require(writer.VALIDATOR.resolve() == Path(__file__).resolve(), "failure-drill writer validator authority drift")
    require(writer.LOCK.resolve() == LOCK.resolve(), "failure-drill writer lock authority drift")
    require(callable(getattr(writer, "append_registry_transactionally", None)), "failure-drill writer transactional append authority missing")


def validate_generation_registry_authority() -> None:
    generation_writer = load_module(GEN_WRITER, "memory_os_environment_generation_writer_for_failure_drill")
    require(generation_writer.REGISTRY.resolve() == GEN_REGISTRY.resolve(), "environment generation registry authority drift")
    try:
        generation_writer.validate_registry_for_append(load(GEN_REGISTRY))
    except generation_writer.Fail as exc:
        raise Fail(f"environment generation registry rejected: {exc}") from exc


def record_evidence_refs(record: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    assertions = record.get("assertions")
    if isinstance(assertions, list):
        for row in assertions:
            if isinstance(row, dict) and isinstance(row.get("evidenceRefs"), list):
                refs.extend(item for item in row["evidenceRefs"] if isinstance(item, str))
    for field in ("operabilityReviewRef", "securityReviewRef"):
        value = record.get(field)
        if isinstance(value, str):
            refs.append(value)
    return sorted(set(refs))


def expected_evidence_digests(record: dict[str, Any]) -> dict[str, str]:
    digests: dict[str, str] = {}
    for relative in record_evidence_refs(record):
        path = ROOT / relative
        require(path.is_file(), f"evidence path missing: {relative}")
        digests[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def validate_registry_for_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    validate_generation_registry_authority()
    require(set(registry) == EXPECTED_REGISTRY_FIELDS, "registry field drift")
    require(registry.get("schemaVersion") == "memory-os-production-shaped-failure-drill-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    drills = registry.get("drills")
    require(isinstance(drills, list), "registry drills missing")
    digest_authority = registry.get("evidenceDigestsByDrillId")
    require(isinstance(digest_authority, dict), "evidence digest authority missing")
    writer = load_writer()
    validate_writer_authority(writer)
    ids: set[str] = set()
    pe = 0
    prod = 0
    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(drills):
        require(isinstance(record, dict), f"drills[{index}] invalid")
        confirmation = writer.PRODUCTION_CONFIRMATION if record.get("environmentClass") == "PRODUCTION" else ""
        try:
            writer.validate_record(record, confirmation)
        except Exception as exc:
            raise Fail(f"drills[{index}] invalid: {exc}") from exc
        drill_id = record["drillId"]
        require(drill_id not in ids, f"duplicate drillId: {drill_id}")
        ids.add(drill_id)
        expected_digests = expected_evidence_digests(record)
        actual_digests = digest_authority.get(drill_id)
        require(isinstance(actual_digests, dict), f"evidence digest authority missing for {drill_id}")
        require(actual_digests == expected_digests, f"evidence digest authority drift for {drill_id}")
        pe += 1 if record["environmentClass"] == "PRODUCTION_EQUIVALENT" else 0
        prod += 1 if record["environmentClass"] == "PRODUCTION" else 0
        normalized.append(record)
    require(set(digest_authority) == ids, "evidence digest authority contains unknown drill ids")
    require_count(registry.get("registeredDrillCount"), len(drills), "registeredDrillCount")
    require_count(registry.get("productionEquivalentDrillCount"), pe, "productionEquivalentDrillCount")
    require_count(registry.get("productionDrillCount"), prod, "productionDrillCount")
    require(registry.get("productionReady") is False, "registry cannot make application productionReady")
    return normalized


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    require(contract.get("schemaVersion") == "memory-os-production-shaped-failure-drill.v1", "contract schema drift")
    require(contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "registry binding drift")
    require(contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)), "append lock binding drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)), "writer binding drift")
    writer = load_writer()
    validate_writer_authority(writer)
    scenarios = contract.get("scenarioClasses")
    require(isinstance(scenarios, list) and len(scenarios) == 4, "four required scenario classes expected")
    scenario_ids = {row.get("id") for row in scenarios if isinstance(row, dict)}
    require(scenario_ids == {"FAIL-PROD-001", "FAIL-PROD-002", "FAIL-PROD-003", "FAIL-PROD-004"}, "scenario set drift")
    requirements = contract.get("recordRequirements")
    require(isinstance(requirements, dict) and requirements and all(value is True for value in requirements.values()), "record requirements must remain true")
    require(requirements.get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True, "transactional append requirement must remain true")
    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict), "promotionRules missing")
    for key, value in promotion.items():
        if key == "automaticProductionReadyForbidden":
            require(value is True, "automatic production-ready prohibition must remain true")
        else:
            require(value is False, f"unsafe promotion rule enabled: {key}")

    drills = validate_registry_for_append(registry)
    pe = sum(1 for record in drills if record["environmentClass"] == "PRODUCTION_EQUIVALENT")
    prod = sum(1 for record in drills if record["environmentClass"] == "PRODUCTION")
    completed_scenarios = {record["scenarioId"] for record in drills}

    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "contract authority missing")
    require(current.get("registeredDrillCount") in {0, len(drills)}, "current drill count drift before reconcile")
    require(current.get("productionReady") is False and current.get("productionDecision") == "NO_GO", "production boundary drift")
    require(readiness.get("productionReady") is False, "readiness cannot promote production")
    print("Memory OS production-shaped failure drill validation PASS")
    print(f"registered drills: {len(drills)}")
    print(f"completed scenario classes: {len(completed_scenarios)}/4")
    print(f"production-equivalent drills: {pe}")
    print(f"production drills: {prod}")
    print("application production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-SHAPED FAILURE DRILL VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
