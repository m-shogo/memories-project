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
    recovery_objectives = load("contracts/operations/recovery-objectives-registry.v1.json")
    backup_binding = load("contracts/operations/backup-restore-generation-binding-contract.v1.json")
    backup_recovery = load("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
    backup_non_resurrection_contract = load("contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json")
    backup_non_resurrection = load("contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json")
    backup_drill_request_contract = load("contracts/operations/backup-restore-drill-request-contract.v1.json")
    backup_drill_requests = load("contracts/operations/backup-restore-drill-request-registry.v1.json")
    backup_drill_preflight = load("contracts/operations/backup-restore-drill-preflight-contract.v1.json")
    releases = load("contracts/operations/release-baseline-registry.v1.json")
    release_pairs = load("contracts/operations/release-compatibility-pair-registry.v1.json")
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
    non_resurrection_boundary = backup_non_resurrection_contract.get("currentBoundary")
    if not isinstance(non_resurrection_boundary, dict):
        raise SystemExit("backup typed non-resurrection boundary missing")
    drill_request_state = backup_drill_request_contract.get("currentAdmissionState")
    if not isinstance(drill_request_state, dict):
        raise SystemExit("backup drill request admission state missing")
    preflight_state = backup_drill_preflight.get("currentState")
    if not isinstance(preflight_state, dict):
        raise SystemExit("backup drill preflight state missing")

    objective_count = recovery_objectives.get("approvedObjectiveCount")
    if not isinstance(objective_count, int) or objective_count < 0:
        raise SystemExit("approved recovery objective count invalid")
    release_pair_count = release_pairs.get("approvedPairCount")
    if not isinstance(release_pair_count, int) or release_pair_count < 0:
        raise SystemExit("approved release pair count invalid")
    typed_record_count = backup_non_resurrection.get("registeredRecordCount")
    typed_complete_count = backup_non_resurrection.get("completeRecordCount")
    typed_covered_count = backup_non_resurrection.get("candidateCoveredCount")
    pending_typed_count = non_resurrection_boundary.get("preOverlayEligiblePendingTypedCoverageCount")
    drill_request_count = backup_drill_requests.get("registeredRequestCount")
    executable_drill_request_count = backup_drill_requests.get("currentExecutableRequestCount")
    generation_evidence_count = backup_recovery.get("registeredEvidenceCount")
    drill_bound_generation_evidence_count = backup_recovery.get("drillRequestBoundEvidenceCount")
    unsuperseded_generation_count = preflight_state.get("unsupersededGenerationCount")
    distinct_unsuperseded_environment_count = preflight_state.get("distinctUnsupersededEnvironmentCount")
    eligible_pair_count = preflight_state.get("eligibleDirectedSourceTargetPairCount")
    preflight_eligible = preflight_state.get("eligibleToSubmitReviewedDrillRequest")
    preflight_decision = preflight_state.get("preflightDecision")

    for value, field in (
        (typed_record_count, "typed non-resurrection record"),
        (typed_complete_count, "complete typed non-resurrection"),
        (typed_covered_count, "typed candidate coverage"),
        (pending_typed_count, "pending typed coverage"),
        (drill_request_count, "backup/restore drill request"),
        (executable_drill_request_count, "current executable backup/restore drill request"),
        (generation_evidence_count, "generation recovery evidence"),
        (drill_bound_generation_evidence_count, "drill-request-bound generation recovery evidence"),
        (unsuperseded_generation_count, "unsuperseded environment generation"),
        (distinct_unsuperseded_environment_count, "distinct unsuperseded environment"),
        (eligible_pair_count, "eligible restore drill source-target pair"),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise SystemExit(f"{field} count invalid")
    if not isinstance(preflight_eligible, bool):
        raise SystemExit("restore drill preflight eligibility invalid")
    if not isinstance(preflight_decision, str) or not preflight_decision:
        raise SystemExit("restore drill preflight decision invalid")
    if not (typed_covered_count <= typed_complete_count <= typed_record_count):
        raise SystemExit("typed non-resurrection count ordering invalid")
    if executable_drill_request_count > drill_request_count:
        raise SystemExit("drill request executable count exceeds request history")
    if drill_bound_generation_evidence_count != generation_evidence_count:
        raise SystemExit("every generation recovery evidence row must be drill-request-bound")
    if drill_request_state.get("registeredRequestCount") != drill_request_count:
        raise SystemExit("drill request contract/registry request count drift")
    if drill_request_state.get("currentExecutableRequestCount") != executable_drill_request_count:
        raise SystemExit("drill request contract/registry executable count drift")
    if drill_request_state.get("productionEvidence") is not False or drill_request_state.get("productionReady") is not False:
        raise SystemExit("drill request authority cannot promote production")
    if preflight_state.get("registeredGenerationCount") != generations.get("registeredGenerationCount"):
        raise SystemExit("restore drill preflight generation count drift")
    if preflight_state.get("approvedRecoveryObjectiveCount") != objective_count:
        raise SystemExit("restore drill preflight objective count drift")
    if preflight_state.get("reviewedDrillRequestCount") != drill_request_count:
        raise SystemExit("restore drill preflight request count drift")
    if preflight_state.get("currentExecutableDrillRequestCount") != executable_drill_request_count:
        raise SystemExit("restore drill preflight executable request count drift")
    if any(preflight_state.get(field) is not False for field in ("requestCreated", "backupExecuted", "restoreExecuted", "productionTrafficChanged", "productionEvidence", "productionReady")):
        raise SystemExit("restore drill preflight execution/production boundary drift")
    if preflight_state.get("productionDecision") != "NO_GO":
        raise SystemExit("restore drill preflight production decision drift")

    local_soak_complete = bool(load_ready.get("localLongSoakRunCount", 0) >= 2 and load_ready.get("localSustainedSoakEvidence") is True)
    if preflight_decision == "BLOCKED_NEEDS_TWO_UNSUPERSEDED_DISTINCT_ENVIRONMENT_GENERATIONS":
        backup_next_gate = "register two distinct reviewed production-equivalent environment generations that are both unsuperseded; then approve explicit recovery objectives before submitting any restore drill request"
    elif preflight_decision == "BLOCKED_NEEDS_CURRENT_APPROVED_RECOVERY_OBJECTIVE":
        backup_next_gate = "approve explicit RPO, RTO and maximum object/database skew for the current recovery objective; then submit a planning-only cross-environment restore drill request for review"
    elif preflight_decision == "READY_FOR_REVIEWED_DRILL_REQUEST_SUBMISSION":
        backup_next_gate = "submit an external reviewed planning-only restore drill request bound to one eligible source/target generation pair and the current recovery objective; do not execute from preflight alone"
    elif preflight_decision == "READY_EXISTING_EXECUTABLE_DRILL_REQUEST":
        backup_next_gate = "immediately revalidate the existing reviewed drill request before any isolated restore execution, then admit request-bound generation recovery evidence and all eight typed non-resurrection domains"
    else:
        raise SystemExit(f"unknown restore drill preflight decision: {preflight_decision}")

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
                "approvedReleasePairs": release_pair_count,
                "environmentGenerations": generations.get("registeredGenerationCount", 0),
            },
            "nextGate": "registered production-equivalent generation plus an approved predecessor/successor release pair before production-shaped migration rehearsal admission",
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
            "tertiaryAuthority": "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
            "quaternaryAuthority": "contracts/operations/backup-restore-drill-request-contract.v1.json",
            "quinaryAuthority": "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
            "foundationImplemented": all(exists(path) for path in (
                "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
                "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
                "contracts/operations/recovery-objectives-admission-contract.v1.json",
                "contracts/operations/recovery-objectives-registry.v1.json",
                "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
                "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
                "contracts/operations/backup-restore-drill-request-contract.v1.json",
                "contracts/operations/backup-restore-drill-request-registry.v1.json",
                "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
                "docs/runbooks/memory-os-production-equivalent-backup-restore-drill.md",
                "scripts/register-memory-os-backup-restore-generation-evidence.py",
                "scripts/validate-memory-os-backup-restore-generation-evidence.py",
                "scripts/validate-memory-os-recovery-objectives.py",
                "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py",
                "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py",
                "scripts/request-memory-os-backup-restore-drill.py",
                "scripts/validate-memory-os-backup-restore-drill-request.py",
                "scripts/reconcile-memory-os-backup-restore-drill-request.py",
                "scripts/validate-memory-os-backup-restore-drill-preflight.py",
                "scripts/reconcile-memory-os-backup-restore-drill-preflight.py",
                ".github/workflows/backup-restore-generation-evidence.yml",
                ".github/workflows/recovery-objectives-admission.yml",
                ".github/workflows/backup-restore-non-resurrection-admission.yml",
                ".github/workflows/backup-restore-drill-request.yml",
                ".github/workflows/backup-restore-drill-preflight.yml",
            )),
            "admittedEvidenceCount": backup_boundary.get("generationBoundRestoreCount", 0),
            "preflightDecision": preflight_decision,
            "preflightEligible": preflight_eligible,
            "dependencyCounts": {
                "environmentGenerations": generations.get("registeredGenerationCount", 0),
                "unsupersededEnvironmentGenerations": unsuperseded_generation_count,
                "distinctUnsupersededEnvironments": distinct_unsuperseded_environment_count,
                "eligibleDirectedRestorePairs": eligible_pair_count,
                "approvedRecoveryObjectives": objective_count,
                "reviewedRestoreDrillRequests": drill_request_count,
                "currentExecutableRestoreDrillRequests": executable_drill_request_count,
                "generationRecoveryEvidenceRecords": generation_evidence_count,
                "drillRequestBoundGenerationEvidence": drill_bound_generation_evidence_count,
                "generationBoundBackups": backup_boundary.get("generationBoundBackupCount", 0),
                "generationBoundRestores": backup_boundary.get("generationBoundRestoreCount", 0),
                "typedNonResurrectionRecords": typed_record_count,
                "completeTypedNonResurrectionRecords": typed_complete_count,
                "preOverlayEligiblePendingTypedCoverage": pending_typed_count,
                "typedCoveredRecoveryCandidates": typed_covered_count,
                "productionEquivalentRecoveryCandidates": backup_recovery.get("productionEquivalentRecoveryCandidateCount", 0),
            },
            "nextGate": backup_next_gate,
        },
        {
            "id": "OPS-P0-008",
            "authority": "contracts/operations/release-compatibility-pair-contract.v1.json",
            "secondaryAuthority": "contracts/operations/compatibility-admission-gaps.v1.json",
            "foundationImplemented": all(exists(path) for path in (
                "contracts/operations/release-compatibility-pair-contract.v1.json",
                "contracts/operations/release-compatibility-pair-registry.v1.json",
                "scripts/register-memory-os-release-compatibility-pair.py",
                "scripts/validate-memory-os-release-compatibility-pair.py",
                "scripts/reconcile-memory-os-release-compatibility-pair.py",
                ".github/workflows/release-compatibility-pair.yml",
            )),
            "admittedEvidenceCount": release_pair_count,
            "dependencyCounts": {
                "approvedReleases": releases.get("approvedReleaseCount", 0),
                "approvedRollbackPairs": release_pair_count,
                "approvedClients": clients.get("approvedClientBaselineCount", 0),
                "reviewedParserArtifacts": parsers.get("reviewedArtifactCount", 0),
            },
            "nextGate": "approve two release baselines and their rolling/rollback compatibility pair, then admit an immutable client baseline and reviewed retained parser artifact before production release compatibility; candidate/local execution remains separate non-release evidence",
        },
        {
            "id": "OPS-P0-009",
            "authority": "contracts/operations/production-shaped-failure-drill-contract.v1.json",
            "foundationImplemented": exists("contracts/operations/production-shaped-failure-drill-contract.v1.json"),
            "admittedEvidenceCount": failure_drills.get("registeredDrillCount", 0),
            "requiredEvidenceCount": 4,
            "dependencyCounts": {
                "environmentGenerations": generations.get("registeredGenerationCount", 0),
                "approvedReleasePairs": release_pair_count,
            },
            "nextGate": "generation-bound multi-instance, object-store, PostgreSQL failover and parser durable-spool restart drills; mixed-version failure evidence additionally requires an approved release pair",
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
        "backupRestoreUnsupersededEnvironmentGenerationCount": unsuperseded_generation_count,
        "backupRestoreDistinctUnsupersededEnvironmentCount": distinct_unsuperseded_environment_count,
        "backupRestoreEligibleDirectedPairCount": eligible_pair_count,
        "backupRestoreDrillPreflightEligible": preflight_eligible,
        "backupRestoreDrillPreflightDecision": preflight_decision,
        "approvedRecoveryObjectiveCount": objective_count,
        "reviewedBackupRestoreDrillRequestCount": drill_request_count,
        "currentExecutableBackupRestoreDrillRequestCount": executable_drill_request_count,
        "generationRecoveryEvidenceRecordCount": generation_evidence_count,
        "drillRequestBoundGenerationEvidenceCount": drill_bound_generation_evidence_count,
        "approvedReleaseCompatibilityPairCount": release_pair_count,
        "typedNonResurrectionRecordCount": typed_record_count,
        "completeTypedNonResurrectionRecordCount": typed_complete_count,
        "productionEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
        "notes": [
            "foundationImplemented means the admission path exists; it does not mean runtime or production evidence exists",
            "admittedEvidenceCount is derived only from canonical append-only registries or accepted human tabletop ledger files",
            "candidate/local evidence is not counted as production admission unless its owning authority explicitly admits it",
            "local repeated soak evidence is tracked separately from independent leak proof and production-shaped soak evidence",
            "recovery-objective values are never defaulted by this inventory; zero approved objectives means RPO/RTO/skew remain intentionally undefined",
            "restore drill preflight is read-only: READY authorizes only external reviewed request submission and BLOCKED never creates missing generations or recovery objectives",
            "backup/restore drill requests are planning authority only; historical requests remain auditable after supersession while current executable count requires immediate generation/objective revalidation",
            "every generation recovery evidence record must remain bound to one admitted restore drill request; an unbound record is an inventory validation failure",
            "a generic generation recovery nonResurrectionVerification PASS cannot create a final recovery candidate; complete typed coverage of all eight non-resurrection domains is independently required",
            "candidate/local mixed-version execution remains separate from the approved release-pair registry and can never create an approved predecessor/successor pair"
        ]
    }
    OUTPUT.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Memory OS operability admission inventory generated")
    print(f"P0 areas inventoried: {len(areas)}")
    print(f"production-equivalent generations: {document['productionEquivalentEnvironmentGenerationCount']}")
    print(f"restore preflight decision: {preflight_decision}")
    print(f"restore preflight eligible pairs: {eligible_pair_count}")
    print(f"approved recovery objectives: {objective_count}")
    print(f"reviewed backup/restore drill requests: {drill_request_count}")
    print(f"currently executable backup/restore drill requests: {executable_drill_request_count}")
    print(f"generation/drill-bound recovery evidence: {generation_evidence_count}/{drill_bound_generation_evidence_count}")
    print(f"typed non-resurrection records: {typed_record_count}")
    print(f"final recovery candidates: {backup_recovery.get('productionEquivalentRecoveryCandidateCount', 0)}")
    print(f"approved release compatibility pairs: {release_pair_count}")
    print(f"local repeated soak complete: {str(local_soak_complete).lower()}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
