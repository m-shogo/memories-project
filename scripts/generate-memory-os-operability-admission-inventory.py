#!/usr/bin/env python3
"""Generate a deterministic inventory of P0 admission authorities and admitted evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


def load(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"root must be object: {relative}")
    return value


def exists(relative: str) -> bool:
    return (ROOT / relative).is_file()


def p0_status(status: dict[str, Any], area_id: str) -> dict[str, Any]:
    rows = status.get("areas")
    if not isinstance(rows, list):
        raise SystemExit("operability status areas missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("id") == area_id]
    if len(matches) != 1:
        raise SystemExit(f"status area missing/duplicate: {area_id}")
    return matches[0]


def main() -> int:
    status = load("contracts/operations/production-operability-status.json")
    if status.get("productionDecision") != "NO_GO":
        raise SystemExit("inventory generation refuses productionDecision != NO_GO")

    migration = load("contracts/operations/migration-production-shaped-admission-registry.v1.json")
    incident_contact = load("contracts/operations/incident-contact-routing-admission-registry.v1.json")
    observability = load("contracts/operations/observability-stack-deployment-registry.v1.json")
    rate_runtime = load("contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json")
    load_contract = load("contracts/operations/load-test-scenario-contract.v1.json")
    generations = load("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
    backup_binding = load("contracts/operations/backup-restore-generation-binding-contract.v1.json")
    backup_recovery = load("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
    releases = load("contracts/operations/release-baseline-registry.v1.json")
    clients = load("contracts/operations/client-baseline-registry.v1.json")
    parsers = load("contracts/operations/parser-artifact-registry.v1.json")
    failure_drills = load("contracts/operations/production-shaped-failure-drill-registry.v1.json")

    human_tabletop_count = len(list((ROOT / "docs/evidence/incident-tabletops").glob("IR-DRILL-*.json")))
    load_ready = load_contract.get("readiness")
    if not isinstance(load_ready, dict):
        raise SystemExit("load readiness missing")
    backup_boundary = backup_binding.get("currentBoundary")
    if not isinstance(backup_boundary, dict):
        raise SystemExit("backup generation boundary missing")
    local_soak_complete = bool(
        load_ready.get("localLongSoakRunCount", 0) >= 2
        and load_ready.get("localSustainedSoakEvidence") is True
    )

    areas: list[dict[str, Any]] = [
        {
            "id": "OPS-P0-001",
            "authority": "contracts/operations/migration-production-shaped-admission-contract.v1.json",
            "foundationImplemented": all(exists(path) for path in (
                "contracts/operations/migration-production-shaped-admission-contract.v1.json",
                "contracts/operations/migration-production-shaped-admission-registry.v1.json",
                "scripts/register-memory-os-migration-production-shaped-admission.py",
                "scripts/validate-memory-os-migration-production-shaped-admission.py",
                ".github/workflows/migration-production-shaped-admission.yml",
            )),
            "admittedEvidenceCount": migration.get("admittedRehearsalCount", 0),
            "dependencyCounts": {
                "approvedReleases": releases.get("approvedReleaseCount", 0),
                "environmentGenerations": generations.get("registeredGenerationCount", 0),
            },
            "nextGate": "registered production-equivalent generation plus approved predecessor/successor before production-shaped migration rehearsal admission",
        },
        {
            "id": "OPS-P0-002",
            "authority": "contracts/operations/incident-human-tabletop-evidence-contract.v1.json",
            "secondaryAuthority": "contracts/operations/incident-contact-routing-admission-contract.v1.json",
            "foundationImplemented": all(exists(path) for path in (
                "contracts/operations/incident-human-tabletop-evidence-contract.v1.json",
                "scripts/register-memory-os-incident-human-tabletop.py",
                "contracts/operations/incident-contact-routing-admission-contract.v1.json",
                "scripts/register-memory-os-incident-contact-routing.py",
            )),
            "admittedEvidenceCount": human_tabletop_count,
            "requiredEvidenceCount": 6,
            "secondaryAdmittedEvidenceCount": incident_contact.get("admittedRoutingCount", 0),
            "dependencyCounts": {"observabilityStacks": observability.get("admittedStackCount", 0)},
            "nextGate": "human-led completion of six canonical tabletop scenarios; configured contact routing additionally requires an admitted observability stack",
        },
        {
            "id": "OPS-P0-003",
            "authority": "contracts/operations/observability-stack-deployment-contract.v1.json",
            "foundationImplemented": exists("contracts/operations/observability-stack-deployment-contract.v1.json"),
            "admittedEvidenceCount": observability.get("admittedStackCount", 0),
            "nextGate": "admit integrated structured-log backend, retention deletion, access audit and review evidence",
        },
        {
            "id": "OPS-P0-004",
            "authority": "contracts/operations/observability-stack-deployment-contract.v1.json",
            "foundationImplemented": exists("contracts/operations/observability-stack-deployment-contract.v1.json"),
            "admittedEvidenceCount": observability.get("admittedStackCount", 0),
            "nextGate": "admit real metrics scrape/backend/dashboard/paging delivery and response evidence",
        },
        {
            "id": "OPS-P0-005",
            "authority": "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json",
            "foundationImplemented": all(exists(path) for path in (
                "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json",
                "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json",
                "scripts/register-memory-os-rate-limit-distributed-runtime.py",
            )),
            "admittedEvidenceCount": rate_runtime.get("admittedRuntimeCount", 0),
            "nextGate": "admit shared-store/trusted-proxy multi-instance runtime with restart continuity and runtime-observed emergency expiry drills",
        },
        {
            "id": "OPS-P0-006",
            "authority": "contracts/operations/load-test-scenario-contract.v1.json",
            "foundationImplemented": True,
            "admittedEvidenceCount": load_ready.get("localLongSoakRunCount", 0),
            "requiredEvidenceCount": 2,
            "dependencyCounts": {
                "environmentGenerations": generations.get("registeredGenerationCount", 0),
                "localSustainedSoakEvidence": local_soak_complete,
                "repeatableLocalDegradationSignalObserved": bool(load_ready.get("repeatableLocalDegradationSignalObserved")),
            },
            "nextGate": (
                "local repeated 60-minute soak and descriptive trend review are complete; next require independent leak/stability criteria plus generation-bound production-equivalent capacity, dependency and host-failure evidence"
                if local_soak_complete
                else "complete two independent 60-minute LOCAL_LONG_SOAK results plus descriptive trend review before production-equivalent capacity/host-failure admission"
            ),
        },
        {
            "id": "OPS-P0-007",
            "authority": "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
            "secondaryAuthority": "contracts/operations/backup-restore-generation-binding-contract.v1.json",
            "foundationImplemented": all(exists(path) for path in (
                "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
                "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
                "scripts/register-memory-os-backup-restore-generation-evidence.py",
                "scripts/validate-memory-os-backup-restore-generation-evidence.py",
                ".github/workflows/backup-restore-generation-evidence.yml",
            )),
            "admittedEvidenceCount": backup_boundary.get("generationBoundRestoreCount", 0),
            "dependencyCounts": {
                "environmentGenerations": generations.get("registeredGenerationCount", 0),
                "generationBoundBackups": backup_boundary.get("generationBoundBackupCount", 0),
                "productionEquivalentRecoveryCandidates": backup_recovery.get("productionEquivalentRecoveryCandidateCount", 0),
            },
            "nextGate": "register a reviewed production-equivalent environment generation, then admit generation-bound PITR, independent object retention and isolated restore evidence with approved/measured RPO/RTO and non-resurrection verification",
        },
        {
            "id": "OPS-P0-008",
            "authority": "contracts/operations/compatibility-admission-gaps.v1.json",
            "foundationImplemented": exists("contracts/operations/compatibility-admission-gaps.v1.json"),
            "admittedEvidenceCount": 0,
            "dependencyCounts": {
                "approvedReleases": releases.get("approvedReleaseCount", 0),
                "approvedClients": clients.get("approvedClientBaselineCount", 0),
                "reviewedParserArtifacts": parsers.get("reviewedArtifactCount", 0),
            },
            "nextGate": "approved predecessor/successor, immutable client baseline and reviewed parser artifact before production release compatibility",
        },
        {
            "id": "OPS-P0-009",
            "authority": "contracts/operations/production-shaped-failure-drill-contract.v1.json",
            "foundationImplemented": exists("contracts/operations/production-shaped-failure-drill-contract.v1.json"),
            "admittedEvidenceCount": failure_drills.get("registeredDrillCount", 0),
            "requiredEvidenceCount": 4,
            "dependencyCounts": {"environmentGenerations": generations.get("registeredGenerationCount", 0)},
            "nextGate": "generation-bound multi-instance, object-store, PostgreSQL failover and parser durable-spool restart drills",
        },
    ]

    for row in areas:
        source = p0_status(status, row["id"])
        row["status"] = source.get("status")
        row["blocking"] = source.get("blocking")
        row["missingEvidenceCount"] = len(source.get("missingEvidence", [])) if isinstance(source.get("missingEvidence"), list) else None
        row["productionEvidence"] = False
        row["productionReady"] = False

    document = {
        "schemaVersion": "memory-os-operability-admission-inventory.v1",
        "deterministic": True,
        "areas": areas,
        "productionEquivalentEnvironmentGenerationCount": generations.get("registeredGenerationCount", 0),
        "productionEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
        "notes": [
            "foundationImplemented means the admission path exists; it does not mean runtime or production evidence exists",
            "admittedEvidenceCount is derived only from canonical append-only registries or accepted human tabletop ledger files",
            "candidate/local evidence is not counted as production admission unless its owning authority explicitly admits it",
            "local repeated soak evidence is tracked separately from independent leak proof and production-shaped soak evidence"
        ]
    }
    OUTPUT.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Memory OS operability admission inventory generated")
    print(f"P0 areas inventoried: {len(areas)}")
    print(f"production-equivalent generations: {document['productionEquivalentEnvironmentGenerationCount']}")
    print(f"local repeated soak complete: {str(local_soak_complete).lower()}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
