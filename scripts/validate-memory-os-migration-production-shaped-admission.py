#!/usr/bin/env python3
"""Validate production-shaped migration rehearsal admission registry."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/migration-production-shaped-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/migration-production-shaped-admission-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-migration-production-shaped-admission.py"
LOCK = ROOT / "contracts/operations/.migration-production-shaped-admission.lock"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
RELEASE_CONTRACT = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
RELEASE_WRITER = ROOT / "scripts/register-memory-os-release-baseline.py"
RELEASE_VALIDATOR = ROOT / "scripts/validate-memory-os-release-baseline-registry.py"
RELEASE_PAIRS = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
RELEASE_PAIR_WRITER = ROOT / "scripts/register-memory-os-release-compatibility-pair.py"
GENERATIONS = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GENERATION_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
GENERATION_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-generation.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def run_canonical_validator(path: Path, label: str) -> None:
    require(path.is_file(), f"canonical {label} validator missing")
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    require(completed.returncode == 0, f"canonical {label} authority validation failed")


def load_module(path: Path, name: str, label: str) -> ModuleType:
    require(path.is_file(), f"canonical {label} missing")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load canonical {label}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_generation_authority(generations: dict[str, Any]) -> None:
    generation_writer = load_module(
        GENERATION_WRITER,
        "memory_os_environment_generation_writer_for_migration_admission_validator",
        "environment generation writer",
    )
    require(getattr(generation_writer, "REGISTRY", None) == GENERATIONS,
            "environment generation writer registry authority drift")
    require(callable(getattr(generation_writer, "validate_registry_for_append", None)),
            "environment generation registry validator missing")
    try:
        generation_writer.validate_registry_for_append(generations)
    except Exception as exc:
        raise Fail(f"environment generation append-only authority invalid: {exc}") from exc


def main() -> int:
    run_canonical_validator(RELEASE_VALIDATOR, "release baseline")
    run_canonical_validator(GENERATION_VALIDATOR, "environment generation")

    contract = load(CONTRACT)
    registry = load(REGISTRY)
    releases = load(RELEASES)
    release_pairs = load(RELEASE_PAIRS)
    generations = load(GENERATIONS)
    release_contract = load(RELEASE_CONTRACT)
    require(contract.get("schemaVersion") == "memory-os-migration-production-shaped-admission.v1", "contract schema drift")
    require(contract.get("recordSchemaVersion") == "memory-os-migration-production-shaped-admission-record.v1", "record schema drift")
    require(contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "registry binding drift")
    require(contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)), "append lock binding drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)), "writer binding drift")
    require(contract.get("sourceReleasePairRegistry") == str(RELEASE_PAIRS.relative_to(ROOT)), "release pair registry binding drift")
    rules = contract.get("admissionRules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "admissionRules must remain true")
    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict), "promotionRules missing")
    for key, value in promotion.items():
        if key == "automaticProductionReadyForbidden":
            require(value is True, "automatic production-ready prohibition must remain true")
        else:
            require(value is False, f"unsafe migration admission promotion enabled: {key}")

    release_writer = load_module(
        RELEASE_WRITER,
        "memory_os_release_baseline_writer_for_migration_admission",
        "release baseline writer",
    )
    try:
        release_writer.validate_registry_for_append(releases, release_contract)
    except Exception as exc:
        raise Fail(f"release baseline append-only authority invalid: {exc}") from exc

    pair_writer = load_module(
        RELEASE_PAIR_WRITER,
        "memory_os_release_pair_writer_for_migration_admission",
        "release compatibility pair writer",
    )
    try:
        pair_writer.validate_registry_for_append(release_pairs)
    except Exception as exc:
        raise Fail(f"release compatibility pair append-only authority invalid: {exc}") from exc

    validate_generation_authority(generations)

    writer = load_module(
        WRITER,
        "memory_os_migration_production_admission_writer",
        "migration admission writer",
    )
    require(getattr(writer, "LOCK", None) == LOCK, "migration admission writer append lock authority drift")
    require(getattr(writer, "GENERATION_WRITER", None) == GENERATION_WRITER,
            "migration admission generation writer authority drift")
    try:
        writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"migration admission registry invalid: {exc}") from exc
    admissions = registry["admissions"]

    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "contract authority missing")
    require(current.get("admittedRehearsalCount") in {0, len(admissions)}, "current admission count drift before reconcile")
    approved_release_count = releases.get("approvedReleaseCount")
    approved_pair_count = release_pairs.get("approvedPairCount")
    require(isinstance(approved_release_count, int) and not isinstance(approved_release_count, bool), "approvedReleaseCount invalid")
    require(isinstance(approved_pair_count, int) and not isinstance(approved_pair_count, bool), "approvedPairCount invalid")
    registered_generation_count = generations.get("registeredGenerationCount")
    require(isinstance(registered_generation_count, int) and not isinstance(registered_generation_count, bool), "registeredGenerationCount invalid")
    require(current.get("approvedReleasePairCount") in {0, approved_pair_count}, "approved release pair count drift")
    require(current.get("registeredEnvironmentGenerationCount") in {0, registered_generation_count}, "environment generation count drift")
    require(current.get("productionEvidence") is False and current.get("productionReady") is False, "current authority cannot promote production")
    require(current.get("productionDecision") == "NO_GO", "production decision drift")
    require(readiness.get("productionReady") is False, "readiness cannot promote production")
    print("Memory OS migration production-shaped admission validation PASS")
    print(f"admitted rehearsals: {len(admissions)}")
    print(f"approved releases: {approved_release_count}")
    print(f"approved release pairs: {approved_pair_count}")
    print(f"registered environment generations: {registered_generation_count}")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION PRODUCTION-SHAPED ADMISSION VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
