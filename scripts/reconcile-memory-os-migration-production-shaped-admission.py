#!/usr/bin/env python3
"""Reconcile migration production-shaped admission without inventing rehearsals."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/migration-production-shaped-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/migration-production-shaped-admission-registry.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-migration-production-shaped-admission.py"
WRITER = ROOT / "scripts/register-memory-os-migration-production-shaped-admission.py"
WORKFLOW = ROOT / ".github/workflows/migration-production-shaped-admission.yml"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
GENERATIONS = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

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


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def main() -> int:
    for path in (REGISTRY, VALIDATOR, WRITER, WORKFLOW):
        require(path.is_file(), f"migration production admission missing: {path.relative_to(ROOT)}")
    registry = load(REGISTRY)
    admissions = registry.get("admissions")
    require(isinstance(admissions, list), "migration production admission registry missing")
    release_pairs = {(row.get("predecessorReleaseId"), row.get("successorReleaseId")) for row in admissions if isinstance(row, dict)}
    release_pairs.discard((None, None))
    generations_used = {row.get("environmentGenerationId") for row in admissions if isinstance(row, dict) and row.get("environmentGenerationId")}
    complete = len(admissions) > 0

    releases = load(RELEASES)
    generations = load(GENERATIONS)
    require(isinstance(releases.get("approvedReleaseCount"), int), "approvedReleaseCount invalid")
    require(isinstance(generations.get("registeredGenerationCount"), int), "registeredGenerationCount invalid")

    contract = load(CONTRACT)
    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "migration production authority missing")
    current["admittedRehearsalCount"] = len(admissions)
    current["approvedReleasePairCount"] = len(release_pairs)
    current["registeredEnvironmentGenerationCount"] = generations["registeredGenerationCount"]
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
    print("Memory OS migration production-shaped admission reconciliation PASS")
    print(f"admitted rehearsals: {len(admissions)}")
    print(f"approved release pairs used: {len(release_pairs)}")
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
