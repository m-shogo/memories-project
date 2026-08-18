#!/usr/bin/env python3
"""Prove fail-closed negative cases for drill-request-bound generation recovery evidence.

The canonical registries are never mutated. The generation writer is pointed at
temporary generation/objective/drill/typed registries so admission, historical
audit and candidate invalidation are deterministic.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
DRILL_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
NON_RESURRECTION_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
SOURCE_ENV_FIXTURE = ROOT / "docs/fixtures/memory-os-operability/backup-restore-generation-evidence/source-environment-record.valid.json"
TARGET_ENV_FIXTURE = ROOT / "docs/fixtures/memory-os-operability/backup-restore-generation-evidence/target-environment-record.valid.json"
DRILL_APPROVAL_FIXTURE_DIR = "docs/fixtures/memory-os-operability/backup-restore-generation-evidence"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
DIGEST_F = "f" * 64


class Fail(RuntimeError):
    pass


EXPECTED_FAILURE_MODULES: set[str] = set()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def head_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, "cannot resolve HEAD")
    value = completed.stdout.strip()
    require(len(value) == 40, "HEAD must be full SHA")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_ref(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_backup_restore_generation_writer_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load generation evidence writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def expect_rejected(name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except Exception as exc:
        if type(exc).__name__ == "Fail" and type(exc).__module__ in EXPECTED_FAILURE_MODULES:
            print(f"PASS reject: {name}")
            return
        raise
    raise Fail(f"negative case unexpectedly accepted: {name}")


def generation_record(
    *,
    generation_id: str,
    environment_id: str,
    environment_manifest_sha256: str,
    environment_record: Path,
    commit_sha: str,
) -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-production-equivalent-environment-generation-record.v1",
        "environmentId": environment_id,
        "generationId": generation_id,
        "registeredAt": "2026-08-08T00:00:00Z",
        "sourceCommitSha": commit_sha,
        "environmentManifestSha256": environment_manifest_sha256,
        "dependencyInventorySha256": DIGEST_C,
        "evidenceBundleManifestSha256": DIGEST_D,
        "materialDeltaLedgerSha256": DIGEST_E,
        "environmentRecordRef": repo_ref(environment_record),
        "environmentRecordSha256": sha256(environment_record),
        "supersedesGenerationId": None,
        "productionTraffic": False,
        "productionCredentials": False,
        "productionEvidence": False,
        "productionReady": False,
    }


def base_record(commit_sha: str) -> dict[str, Any]:
    contract = load(CONTRACT)
    record = {field: None for field in contract["requiredRecordFields"]}
    record.update({
        "schemaVersion": contract["recordSchemaVersion"],
        "evidenceId": "brge_negative_base",
        "drillRequestId": "brrq_negative_base",
        "sourceCommitSha": commit_sha,
        "sourceEnvironmentGenerationId": "pegen_source",
        "sourceEnvironmentManifestSha256": DIGEST_A,
        "restoreTargetGenerationId": "pegen_target",
        "restoreTargetManifestSha256": DIGEST_B,
        "backupArtifactSha256": DIGEST_C,
        "backupManifestSha256": DIGEST_D,
        "databaseRecoveryPointDigest": DIGEST_E,
        "objectRecoveryPointDigest": DIGEST_F,
        "restoreEvidenceBundleSha256": DIGEST_A,
        "restoredBackupArtifactSha256": DIGEST_C,
        "isolatedRestoreVerified": True,
        "postgresPitrVerified": True,
        "independentObjectRetentionVerified": True,
        "tlsVerified": True,
        "restoreOnlyCredentialSeparationVerified": True,
        "databaseObjectRecoveryCoherenceVerified": True,
        "nonResurrectionVerification": "PASS",
        "recoveryObjectivesId": "recovery_objectives_ci",
        "measuredRpoSeconds": 30,
        "measuredRtoSeconds": 60,
        "measuredObjectDatabaseSkewSeconds": 5,
        "materialDeltaReviewRef": "SECURITY.md",
        "securityReviewRef": "SECURITY.md",
        "operabilityReviewRef": "README.md",
        "unresolvedFindings": [],
        "evidenceComplete": True,
        "productionTraffic": False,
        "productionCredentials": False,
        "productionEvidence": False,
        "productionReady": False,
    })
    return record


def base_drill_request() -> dict[str, Any]:
    contract = load(DRILL_CONTRACT)
    operability_ref = "contracts/operations/backup-restore-drill-request-contract.v1.json"
    return {
        "schemaVersion": contract["recordSchemaVersion"],
        "requestId": "brrq_negative_base",
        "requestedAt": "2026-08-08T00:00:00Z",
        "sourceEnvironmentGenerationId": "pegen_source",
        "sourceEnvironmentManifestSha256": DIGEST_A,
        "restoreTargetEnvironmentGenerationId": "pegen_target",
        "restoreTargetManifestSha256": DIGEST_B,
        "recoveryObjectivesId": "recovery_objectives_ci",
        "isolationPolicy": {
            "environmentClass": "PRODUCTION_EQUIVALENT_ISOLATED_RESTORE_DRILL",
            "networkIsolated": True,
            "productionRoutingForbidden": True,
            "syntheticOrApprovedSanitizedDataOnly": True,
        },
        "databasePolicy": {
            "pitrRequired": True,
            "walContinuityRequired": True,
            "restoreIntoSeparateDatabaseRequired": True,
            "destructiveDownMigrationAllowed": False,
        },
        "objectPolicy": {
            "independentRetentionRequired": True,
            "exactVersionRestoreRequired": True,
            "tlsRequired": True,
            "restoreOnlyCredentialsRequired": True,
            "deletionProtectionRequired": True,
            "immutabilityRequired": True,
        },
        "requiredEvidenceDomains": list(contract["requiredEvidenceDomains"]),
        "entryCriteriaRefs": ["SECURITY.md", "README.md", operability_ref],
        "approvalRefs": {
            "recoveryOwner": f"{DRILL_APPROVAL_FIXTURE_DIR}/drill-request-recovery-owner-approval.valid.json",
            "securityReview": f"{DRILL_APPROVAL_FIXTURE_DIR}/drill-request-security-approval.valid.json",
            "operabilityReview": f"{DRILL_APPROVAL_FIXTURE_DIR}/drill-request-operability-approval.valid.json",
        },
        "stopConditions": list(contract["requiredStopConditions"]),
        "openRisks": [],
        "productionTraffic": False,
        "productionCredentials": False,
        "automaticPromotion": False,
        "productionEvidence": False,
        "productionReady": False,
    }


def typed_overlay_record(evidence_id: str, commit_sha: str) -> dict[str, Any]:
    contract = load(NON_RESURRECTION_CONTRACT)
    domains = {
        name: {"result": "PASS", "evidenceRef": f"docs/evidence/backup-restore/non-resurrection/{name}.json"}
        for name in contract["requiredDomains"]
    }
    return {
        "schemaVersion": contract["recordSchemaVersion"],
        "recordId": "brnr_negative_overlay",
        "generationEvidenceId": evidence_id,
        "sourceCommitSha": commit_sha,
        "domains": domains,
        "securityReviewRef": "SECURITY.md",
        "operabilityReviewRef": "README.md",
        "unresolvedFindings": [],
        "evidenceComplete": True,
        "productionTraffic": False,
        "productionCredentials": False,
        "productionEvidence": False,
        "productionReady": False,
    }


def main() -> int:
    global EXPECTED_FAILURE_MODULES
    require(
        WRITER.is_file()
        and CONTRACT.is_file()
        and DRILL_CONTRACT.is_file()
        and NON_RESURRECTION_CONTRACT.is_file()
        and SOURCE_ENV_FIXTURE.is_file()
        and TARGET_ENV_FIXTURE.is_file(),
        "generation evidence foundation missing",
    )
    writer = load_writer()
    EXPECTED_FAILURE_MODULES = {
        writer.Fail.__module__,
        "memory_os_restore_drill_request_writer_for_generation_evidence",
    }
    contract = load(CONTRACT)
    require(
        contract.get("recordRules", {}).get("registryMustRevalidateAfterAppendAndRollbackOnFailure") is True,
        "generation evidence transactional append contract guard missing",
    )
    print("PASS accept: generation evidence transactional append contract guard")

    with tempfile.TemporaryDirectory(prefix="memory-os-generation-append-rollback-") as transaction_tmp:
        temp_registry = Path(transaction_tmp) / "generation-evidence-registry.json"
        original_payload = {"sentinel": "original authority bytes"}
        write_json(temp_registry, original_payload)
        before = temp_registry.read_bytes()
        original_registry = writer.REGISTRY
        original_validator = writer.validate_registry_for_append
        writer.REGISTRY = temp_registry
        writer.validate_registry_for_append = lambda value: (_ for _ in ()).throw(writer.Fail("synthetic post-append validation failure"))
        try:
            expect_rejected(
                "generation evidence post-append validation rollback",
                lambda: writer.write_registry_transactionally({"sentinel": "mutated authority bytes"}),
            )
            require(temp_registry.read_bytes() == before, "generation evidence registry bytes changed after rejected transactional append")
            print("PASS preserve: generation evidence append failure rolled back byte-for-byte")
        finally:
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validator

    commit_sha = head_sha()

    original_drill_loader = writer.load_drill_writer

    class RejectingCanonicalDrillAuthority:
        @staticmethod
        def validate_registry_for_append(_registry: dict[str, Any]) -> list[dict[str, Any]]:
            raise writer.Fail("approval evidence digest authority drift")

    try:
        writer.load_drill_writer = lambda: RejectingCanonicalDrillAuthority()
        expect_rejected(
            "direct candidate path delegates canonical drill registry authority",
            lambda: writer.drill_request_for_record({"drillRequestId": "brrq_negative_probe"}, require_current=False),
        )
    finally:
        writer.load_drill_writer = original_drill_loader

    no_generation = base_record(commit_sha)
    no_generation["evidenceId"] = "brge_no_generation"
    expect_rejected("no registered production-equivalent generation", lambda: writer.validate_record(no_generation))

    with tempfile.TemporaryDirectory(prefix="memory-os-restore-negative-") as tmp:
        tmp_path = Path(tmp)
        generation_registry = tmp_path / "generations.json"
        objectives_registry = tmp_path / "objectives.json"
        drill_registry = tmp_path / "drill-requests.json"
        overlay_registry = tmp_path / "typed-overlay.json"

        source_generation = generation_record(
            generation_id="pegen_source",
            environment_id="pe_source",
            environment_manifest_sha256=DIGEST_A,
            environment_record=SOURCE_ENV_FIXTURE,
            commit_sha=commit_sha,
        )
        target_generation = generation_record(
            generation_id="pegen_target",
            environment_id="pe_target",
            environment_manifest_sha256=DIGEST_B,
            environment_record=TARGET_ENV_FIXTURE,
            commit_sha=commit_sha,
        )
        write_json(generation_registry, {
            "schemaVersion": "memory-os-production-equivalent-environment-generation-registry.v1",
            "registryClass": "PRODUCTION_EQUIVALENT_ENVIRONMENT_GENERATIONS",
            "appendOnly": True,
            "registeredGenerationCount": 2,
            "currentGenerationId": "pegen_target",
            "productionEvidence": False,
            "generations": [source_generation, target_generation],
            "limitations": [],
        })
        write_json(objectives_registry, {
            "schemaVersion": "memory-os-recovery-objectives-registry.v1",
            "appendOnly": True,
            "approvedObjectiveCount": 2,
            "currentObjectiveId": "recovery_objectives_ci",
            "records": [
                {"objectiveId": "recovery_objectives_old", "rpoSeconds": 120, "rtoSeconds": 300, "maximumObjectDatabaseSkewSeconds": 30, "approvedAt": "2026-08-07T23:50:00Z"},
                {"objectiveId": "recovery_objectives_ci", "rpoSeconds": 60, "rtoSeconds": 120, "maximumObjectDatabaseSkewSeconds": 10, "approvedAt": "2026-08-07T23:55:00Z"},
            ],
            "productionEvidence": False,
            "productionReady": False,
        })
        write_json(drill_registry, {
            "schemaVersion": "memory-os-backup-restore-drill-request-registry.v1",
            "registryClass": "PRODUCTION_EQUIVALENT_BACKUP_RESTORE_DRILL_REQUESTS",
            "appendOnly": True,
            "registeredRequestCount": 0,
            "currentExecutableRequestCount": 0,
            "requests": [],
            "productionEvidence": False,
            "productionReady": False,
        })
        write_json(overlay_registry, {
            "schemaVersion": "memory-os-backup-restore-non-resurrection-admission-registry.v1",
            "appendOnly": True,
            "registeredRecordCount": 0,
            "completeRecordCount": 0,
            "candidateCoveredCount": 0,
            "records": [],
            "productionEvidence": False,
            "productionReady": False,
        })

        writer.GEN_REGISTRY = generation_registry
        writer.OBJECTIVES_REGISTRY = objectives_registry
        writer.DRILL_REQUEST_REGISTRY = drill_registry
        writer.NON_RESURRECTION_REGISTRY = overlay_registry

        valid = base_record(commit_sha)
        expect_rejected("unregistered drill request", lambda: writer.validate_record(valid))

        request = base_drill_request()
        write_json(drill_registry, {
            "schemaVersion": "memory-os-backup-restore-drill-request-registry.v1",
            "registryClass": "PRODUCTION_EQUIVALENT_BACKUP_RESTORE_DRILL_REQUESTS",
            "appendOnly": True,
            "registeredRequestCount": 1,
            "currentExecutableRequestCount": 1,
            "requests": [request],
            "productionEvidence": False,
            "productionReady": False,
        })

        writer.validate_record(valid)
        require(writer.base_candidate(valid) is True, "complete request-bound record must satisfy pre-overlay gates")
        require(writer.candidate(valid) is False, "generic non-resurrection PASS without typed overlay must not become candidate")
        print("PASS non-candidate: request-bound record lacks typed coverage")

        healthy_objectives = load(objectives_registry)

        count_drift = copy.deepcopy(healthy_objectives)
        count_drift["approvedObjectiveCount"] = len(count_drift["records"]) + 1
        write_json(objectives_registry, count_drift)
        expect_rejected("recovery objective aggregate count drift", lambda: writer.validate_record(valid))

        boolean_count = copy.deepcopy(healthy_objectives)
        boolean_count["approvedObjectiveCount"] = True
        write_json(objectives_registry, boolean_count)
        expect_rejected("boolean recovery objective aggregate count", lambda: writer.validate_record(valid))

        current_pointer_drift = copy.deepcopy(healthy_objectives)
        current_pointer_drift["currentObjectiveId"] = "recovery_objectives_old"
        write_json(objectives_registry, current_pointer_drift)
        expect_rejected("recovery objective current pointer drift", lambda: writer.validate_record(valid))

        objective_promotion_drift = copy.deepcopy(healthy_objectives)
        objective_promotion_drift["productionReady"] = True
        write_json(objectives_registry, objective_promotion_drift)
        expect_rejected("recovery objective production boundary drift", lambda: writer.validate_record(valid))

        write_json(objectives_registry, healthy_objectives)
        writer.validate_record(valid)
        print("PASS restore: healthy recovery objective authority remains admissible")

        absolute_review = copy.deepcopy(valid)
        absolute_review["evidenceId"] = "brge_absolute_review"
        absolute_review["securityReviewRef"] = str((ROOT / "SECURITY.md").resolve())
        expect_rejected("absolute generation review ref", lambda: writer.validate_record(absolute_review))

        parent_alias_review = copy.deepcopy(valid)
        parent_alias_review["evidenceId"] = "brge_parent_alias"
        parent_alias_review["securityReviewRef"] = "scripts/../SECURITY.md"
        expect_rejected("parent-traversal generation review ref", lambda: writer.validate_record(parent_alias_review))

        outside_review = tmp_path / "outside-review.txt"
        outside_review.write_text("external review\n", encoding="utf-8")
        escape_link = ROOT / "docs/fixtures/memory-os-operability/.generation-evidence-review-escape"
        try:
            escape_link.unlink(missing_ok=True)
            escape_link.symlink_to(outside_review)
            escaped_review = copy.deepcopy(valid)
            escaped_review["evidenceId"] = "brge_symlink_review"
            escaped_review["securityReviewRef"] = repo_ref(escape_link)
            expect_rejected("repo-local generation review symlink escapes repository", lambda: writer.validate_record(escaped_review))
        finally:
            escape_link.unlink(missing_ok=True)

        overlay = typed_overlay_record(valid["evidenceId"], commit_sha)
        write_json(overlay_registry, {
            "schemaVersion": "memory-os-backup-restore-non-resurrection-admission-registry.v1",
            "appendOnly": True,
            "registeredRecordCount": 1,
            "completeRecordCount": 1,
            "candidateCoveredCount": 1,
            "records": [overlay],
            "productionEvidence": False,
            "productionReady": False,
        })
        require(writer.candidate(valid) is True, "complete typed overlay must unlock current candidate predicate")
        print("PASS candidate: current request + generation evidence + typed coverage")

        bad_request_id = copy.deepcopy(valid)
        bad_request_id["evidenceId"] = "brge_missing_request"
        bad_request_id["drillRequestId"] = "brrq_missing_request"
        expect_rejected("missing drill request ID", lambda: writer.validate_record(bad_request_id))

        source_mismatch = copy.deepcopy(valid)
        source_mismatch["evidenceId"] = "brge_source_mismatch"
        source_mismatch["sourceEnvironmentGenerationId"] = "pegen_target"
        source_mismatch["sourceEnvironmentManifestSha256"] = DIGEST_B
        expect_rejected("drill request source generation mismatch", lambda: writer.validate_record(source_mismatch))

        target_mismatch = copy.deepcopy(valid)
        target_mismatch["evidenceId"] = "brge_target_mismatch"
        target_mismatch["restoreTargetGenerationId"] = "pegen_source"
        target_mismatch["restoreTargetManifestSha256"] = DIGEST_A
        expect_rejected("drill request restore target mismatch", lambda: writer.validate_record(target_mismatch))

        old_objective = copy.deepcopy(valid)
        old_objective["evidenceId"] = "brge_objective_mismatch"
        old_objective["recoveryObjectivesId"] = "recovery_objectives_old"
        expect_rejected("drill request recovery objective mismatch", lambda: writer.validate_record(old_objective))

        same_review = copy.deepcopy(valid)
        same_review["evidenceId"] = "brge_same_review"
        same_review["operabilityReviewRef"] = same_review["securityReviewRef"]
        expect_rejected("security/operability review reuse", lambda: writer.validate_record(same_review))

        missing_delta = copy.deepcopy(valid)
        missing_delta["evidenceId"] = "brge_missing_delta"
        missing_delta["materialDeltaReviewRef"] = None
        expect_rejected("cross-generation restore without material delta review", lambda: writer.validate_record(missing_delta))

        artifact_swap = copy.deepcopy(valid)
        artifact_swap["evidenceId"] = "brge_artifact_swap"
        artifact_swap["restoredBackupArtifactSha256"] = DIGEST_D
        expect_rejected("restored artifact differs from exact backup", lambda: writer.validate_record(artifact_swap))

        unsafe_finding = copy.deepcopy(valid)
        unsafe_finding["evidenceId"] = "brge_high_finding"
        unsafe_finding["unresolvedFindings"] = [{"findingId": "finding_high", "severity": "HIGH", "status": "OPEN"}]
        expect_rejected("HIGH unresolved finding", lambda: writer.validate_record(unsafe_finding))

        production_flag = copy.deepcopy(valid)
        production_flag["evidenceId"] = "brge_prod_flag"
        production_flag["productionEvidence"] = True
        expect_rejected("production evidence relabel", lambda: writer.validate_record(production_flag))

        stale_objectives = load(objectives_registry)
        stale_objectives["approvedObjectiveCount"] = 3
        stale_objectives["currentObjectiveId"] = "recovery_objectives_new"
        stale_objectives["records"].append(
            {"objectiveId": "recovery_objectives_new", "rpoSeconds": 45, "rtoSeconds": 90, "maximumObjectDatabaseSkewSeconds": 8, "approvedAt": "2026-08-08T00:10:00Z"}
        )
        write_json(objectives_registry, stale_objectives)
        stale_drill_registry = load(drill_registry)
        stale_drill_registry["currentExecutableRequestCount"] = 0
        write_json(drill_registry, stale_drill_registry)
        expect_rejected("stale drill request for new evidence", lambda: writer.validate_record(valid))
        writer.validate_record(valid, require_current_drill_request=False)
        require(writer.candidate(valid) is False, "stale drill request must invalidate current candidate")
        print("PASS history: stale request evidence remains auditable but non-candidate")

    print("Memory OS drill-request-bound generation negative admission suite PASS")
    print("canonical registries mutated: false")
    print("request bypass to generation evidence: false")
    print("direct candidate bypasses canonical drill registry authority: false")
    print("recovery objective aggregate/current authority drift accepted: false")
    print("generation evidence post-append validation failure persisted: false")
    print("stale request creates current candidate: false")
    print("generic non-resurrection PASS creates candidate: false")
    print("generation review refs escape repository: false")
    print("unexpected exception accepted as a valid rejection: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
