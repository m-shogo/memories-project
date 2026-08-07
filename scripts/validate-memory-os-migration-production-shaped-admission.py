#!/usr/bin/env python3
"""Validate production-shaped migration rehearsal admission registry."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/migration-production-shaped-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/migration-production-shaped-admission-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-migration-production-shaped-admission.py"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
GENERATIONS = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_migration_production_admission_writer", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load migration admission writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    releases = load(RELEASES)
    generations = load(GENERATIONS)
    require(contract.get("schemaVersion") == "memory-os-migration-production-shaped-admission.v1", "contract schema drift")
    require(contract.get("recordSchemaVersion") == "memory-os-migration-production-shaped-admission-record.v1", "record schema drift")
    require(contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "registry binding drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)), "writer binding drift")
    rules = contract.get("admissionRules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "admissionRules must remain true")
    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict), "promotionRules missing")
    for key, value in promotion.items():
        if key == "automaticProductionReadyForbidden":
            require(value is True, "automatic production-ready prohibition must remain true")
        else:
            require(value is False, f"unsafe migration admission promotion enabled: {key}")

    require(registry.get("schemaVersion") == "memory-os-migration-production-shaped-admission-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    admissions = registry.get("admissions")
    require(isinstance(admissions, list), "registry admissions missing")
    writer = load_writer()
    ids: set[str] = set()
    runs: set[str] = set()
    for index, record in enumerate(admissions):
        require(isinstance(record, dict), f"admissions[{index}] invalid")
        try:
            writer.validate_record(record)
        except Exception as exc:
            raise Fail(f"admissions[{index}] invalid: {exc}") from exc
        require(record["admissionId"] not in ids, f"duplicate admissionId: {record['admissionId']}")
        require(record["migrationRunId"] not in runs, f"duplicate migrationRunId admission: {record['migrationRunId']}")
        ids.add(record["admissionId"])
        runs.add(record["migrationRunId"])
    require(registry.get("admittedRehearsalCount") == len(admissions), "admittedRehearsalCount drift")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "registry cannot promote production")

    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "contract authority missing")
    require(current.get("admittedRehearsalCount") in {0, len(admissions)}, "current admission count drift before reconcile")
    require(current.get("approvedReleasePairCount") in {0, max(0, releases.get("approvedReleaseCount", 0) - 1)}, "approved release pair count drift")
    require(current.get("registeredEnvironmentGenerationCount") in {0, generations.get("registeredGenerationCount")}, "environment generation count drift")
    require(current.get("productionEvidence") is False and current.get("productionReady") is False, "current authority cannot promote production")
    require(current.get("productionDecision") == "NO_GO", "production decision drift")
    require(readiness.get("productionReady") is False, "readiness cannot promote production")
    print("Memory OS migration production-shaped admission validation PASS")
    print(f"admitted rehearsals: {len(admissions)}")
    print(f"approved releases: {releases.get('approvedReleaseCount')}")
    print(f"registered environment generations: {generations.get('registeredGenerationCount')}")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION PRODUCTION-SHAPED ADMISSION VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
