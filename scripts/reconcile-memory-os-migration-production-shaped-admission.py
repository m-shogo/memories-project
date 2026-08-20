#!/usr/bin/env python3
"""Reconcile migration production-shaped admission without inventing rehearsals."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/migration-production-shaped-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/migration-production-shaped-admission-registry.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-migration-production-shaped-admission.py"
LIFECYCLE_VALIDATOR = ROOT / "scripts/validate-memory-os-migration-lifecycle.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
WRITER = ROOT / "scripts/register-memory-os-migration-production-shaped-admission.py"
WORKFLOW = ROOT / ".github/workflows/migration-production-shaped-admission.yml"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
RELEASE_CONTRACT = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
RELEASE_WRITER = ROOT / "scripts/register-memory-os-release-baseline.py"
RELEASE_PAIRS = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
RELEASE_PAIR_WRITER = ROOT / "scripts/register-memory-os-release-compatibility-pair.py"
GENERATIONS = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GENERATION_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

CANONICAL_EXECUTABLES = {
    "migration admission validator": ROOT / "scripts/validate-memory-os-migration-production-shaped-admission.py",
    "migration lifecycle validator": ROOT / "scripts/validate-memory-os-migration-lifecycle.py",
    "operability validator": ROOT / "scripts/validate-memory-os-operability.py",
    "migration admission writer": ROOT / "scripts/register-memory-os-migration-production-shaped-admission.py",
    "release baseline writer": ROOT / "scripts/register-memory-os-release-baseline.py",
    "release compatibility pair writer": ROOT / "scripts/register-memory-os-release-compatibility-pair.py",
    "environment generation writer": ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py",
}

EVIDENCE = (
    "production-shaped migration rehearsal admission is generation-bound and reuses the canonical append-only migration evidence ledger: admission additionally requires a registered environment generation, an approved predecessor/successor release pair, generation-consistent recovery evidence, mixed-version observation and independent security/operability review; the admission registry is currently empty"
)
REFS = (
    "contracts/operations/migration-production-shaped-admission-contract.v1.json",
    "contracts/operations/migration-production-shaped-admission-registry.v1.json",
    "scripts/register-memory-os-migration-production-shaped-admission.py",
    "scripts/validate-memory-os-migration-production-shaped-admission.py",
    "scripts/reconcile-memory-os-migration-production-shaped-admission.py",
    ".github/workflows/migration-production-shaped-admission.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def require_exact_executable(path: Path, label: str) -> None:
    canonical = CANONICAL_EXECUTABLES[label]
    require(path == canonical, f"{label} authority drift")
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"canonical {label} missing or escapes repository") from exc
    require(lexical == resolved and path.is_file() and not path.is_symlink(), f"{label} authority drift")


def enforce_runtime_authorities() -> None:
    for path, label in (
        (VALIDATOR, "migration admission validator"),
        (LIFECYCLE_VALIDATOR, "migration lifecycle validator"),
        (OPERABILITY_VALIDATOR, "operability validator"),
        (WRITER, "migration admission writer"),
        (RELEASE_WRITER, "release baseline writer"),
        (RELEASE_PAIR_WRITER, "release compatibility pair writer"),
        (GENERATION_WRITER, "environment generation writer"),
    ):
        require_exact_executable(path, label)


def load_module(path: Path, name: str, label: str) -> ModuleType:
    require_exact_executable(path, label)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load canonical {label}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_writer() -> ModuleType:
    return load_module(WRITER, "memory_os_migration_production_admission_writer", "migration admission writer")


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def main() -> int:
    enforce_runtime_authorities()
    for path in (
        REGISTRY,
        VALIDATOR,
        LIFECYCLE_VALIDATOR,
        OPERABILITY_VALIDATOR,
        WRITER,
        WORKFLOW,
        RELEASES,
        RELEASE_CONTRACT,
        RELEASE_WRITER,
        RELEASE_PAIRS,
        RELEASE_PAIR_WRITER,
        GENERATIONS,
        GENERATION_WRITER,
    ):
        require(path.is_file(), f"migration production admission authority missing: {path.relative_to(ROOT)}")
    registry = load(REGISTRY)
    writer = load_writer()
    try:
        writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"migration production admission registry invalid before reconcile: {exc}") from exc
    admissions = registry["admissions"]
    release_pairs_used = {(row.get("predecessorReleaseId"), row.get("successorReleaseId")) for row in admissions}
    release_pairs_used.discard((None, None))
    generations_used = {row.get("environmentGenerationId") for row in admissions if row.get("environmentGenerationId")}
    complete = len(admissions) > 0

    releases = load(RELEASES)
    release_contract = load(RELEASE_CONTRACT)
    release_writer = load_module(RELEASE_WRITER, "memory_os_release_baseline_writer_for_migration_reconcile", "release baseline writer")
    try:
        release_writer.validate_registry_for_append(releases, release_contract)
    except Exception as exc:
        raise Fail(f"release baseline authority invalid before migration reconcile: {exc}") from exc

    release_pairs = load(RELEASE_PAIRS)
    release_pair_writer = load_module(RELEASE_PAIR_WRITER, "memory_os_release_pair_writer_for_migration_reconcile", "release compatibility pair writer")
    try:
        release_pair_writer.validate_registry_for_append(release_pairs)
    except Exception as exc:
        raise Fail(f"release compatibility pair authority invalid before migration reconcile: {exc}") from exc

    generations = load(GENERATIONS)
    generation_writer = load_module(GENERATION_WRITER, "memory_os_environment_generation_writer_for_migration_reconcile", "environment generation writer")
    try:
        generation_writer.validate_registry_for_append(generations)
    except Exception as exc:
        raise Fail(f"environment generation authority invalid before migration reconcile: {exc}") from exc

    approved_release_count = releases.get("approvedReleaseCount")
    approved_pair_count = release_pairs.get("approvedPairCount")
    registered_generation_count = generations.get("registeredGenerationCount")
    require(isinstance(approved_release_count, int) and not isinstance(approved_release_count, bool), "approvedReleaseCount invalid")
    require(isinstance(approved_pair_count, int) and not isinstance(approved_pair_count, bool), "approvedPairCount invalid")
    require(isinstance(registered_generation_count, int) and not isinstance(registered_generation_count, bool), "registeredGenerationCount invalid")

    contract = load(CONTRACT)
    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "migration production authority missing")
    current["admittedRehearsalCount"] = len(admissions)
    current["approvedReleasePairCount"] = approved_pair_count
    current["registeredEnvironmentGenerationCount"] = registered_generation_count
    current["productionShapedRehearsalCompleted"] = complete
    current["mixedVersionCompatibilityProvenForApprovedPair"] = complete
    current["generationBoundRecoveryLinked"] = complete
    current["independentReviewCompleted"] = complete
    current["productionEvidence"] = False
    current["productionReady"] = False
    current["productionDecision"] = "NO_GO"
    readiness["registryImplemented"] = True
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["admittedRehearsalCount"] = len(admissions)
    readiness["productionShapedRehearsalCompleted"] = complete
    readiness["productionReady"] = False

    originals = {path: path.read_bytes() for path in (CONTRACT, LIFECYCLE, STATUS)}
    try:
        write(CONTRACT, contract)

        lifecycle = load(LIFECYCLE)
        life_ready = lifecycle.get("readiness")
        require(isinstance(life_ready, dict), "migration lifecycle readiness missing")
        require(life_ready.get("operatorEvidenceRecordImplemented") is True, "operator evidence registry must already be implemented")
        if complete:
            life_ready["productionShapedRehearsalCompleted"] = True
            life_ready["mixedVersionCompatibilityProven"] = True
            life_ready["isolatedRestoreLinked"] = True
        else:
            require(life_ready.get("productionShapedRehearsalCompleted") is False, "empty admission registry cannot retain production-shaped rehearsal=true")
            require(life_ready.get("mixedVersionCompatibilityProven") is False, "empty admission registry cannot retain approved mixed-version proof=true")
            require(life_ready.get("isolatedRestoreLinked") is False, "empty admission registry cannot retain isolated restore link=true")
        require(life_ready.get("ready") is False, "admission alone cannot make migration lifecycle ready")
        write(LIFECYCLE, lifecycle)

        status = load(STATUS)
        require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
        gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-001"), None)
        require(isinstance(gate, dict), "OPS-P0-001 missing")
        require(gate.get("blocking") is True, "OPS-P0-001 must remain blocking until canonical migration readiness is complete")
        existing = gate.get("existingEvidence")
        refs = gate.get("evidenceRefs")
        require(isinstance(existing, list) and isinstance(refs, list), "OPS-P0-001 authority arrays missing")
        append_once(existing, EVIDENCE)
        for ref in REFS:
            append_once(refs, ref)
        write(STATUS, status)

        subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)
        subprocess.run(["python", str(LIFECYCLE_VALIDATOR)], cwd=ROOT, check=True)
        subprocess.run(["python", str(OPERABILITY_VALIDATOR)], cwd=ROOT, check=True)
    except Exception:
        for path, content in originals.items():
            path.write_bytes(content)
        raise

    print("Memory OS migration production-shaped admission reconciliation PASS")
    print(f"admitted rehearsals: {len(admissions)}")
    print(f"approved release pairs available: {approved_pair_count}")
    print(f"approved release pairs used: {len(release_pairs_used)}")
    print(f"environment generations used: {len(generations_used)}")
    print("production evidence: false")
    print("OPS-P0-001: incomplete")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION PRODUCTION-SHAPED RECONCILE FAILED: {exc}")
        raise SystemExit(1)
