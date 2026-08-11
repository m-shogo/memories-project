#!/usr/bin/env python3
"""Prove current restore planning/evidence rejects registered but semantically ineligible generations.

The canonical registries are never mutated. This suite uses temporary generation
and recovery-objective registries and reuses the canonical semantic environment
fixtures already owned by the generation-evidence negative suite.
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
DRILL_WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
EVIDENCE_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
DRILL_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
EVIDENCE_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_ref(path: Path) -> str:
    return str(path.relative_to(ROOT))


def head_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0, "cannot resolve HEAD")
    value = completed.stdout.strip()
    require(len(value) == 40, "HEAD must be full SHA")
    return value


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_expected_domain_failure(exc: BaseException) -> bool:
    """Accept only explicit fail-closed validation exceptions, including nested dynamic modules."""
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        failure_type = type(current)
        if failure_type.__name__ == "Fail" and issubclass(failure_type, RuntimeError):
            return True
        current = current.__cause__ if current.__cause__ is not None else current.__context__
    return False


def expect_rejected(name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except Exception as exc:
        if is_expected_domain_failure(exc):
            print(f"PASS reject: {name}")
            return
        raise
    raise Fail(f"negative case unexpectedly accepted: {name}")


def generation_record(*, generation_id: str, environment_id: str, manifest: str, environment_record: Path, commit_sha: str) -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-production-equivalent-environment-generation-record.v1",
        "environmentId": environment_id,
        "generationId": generation_id,
        "registeredAt": "2026-08-08T00:00:00Z",
        "sourceCommitSha": commit_sha,
        "environmentManifestSha256": manifest,
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


def drill_request() -> dict[str, Any]:
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


def evidence_record(commit_sha: str) -> dict[str, Any]:
    contract = load(EVIDENCE_CONTRACT)
    record = {field: None for field in contract["requiredRecordFields"]}
    record.update({
        "schemaVersion": contract["recordSchemaVersion"],
        "evidenceId": "brge_semantic_negative",
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


def main() -> int:
    for path in (DRILL_WRITER, EVIDENCE_WRITER, DRILL_CONTRACT, EVIDENCE_CONTRACT, NON_RESURRECTION_CONTRACT, SOURCE_ENV_FIXTURE, TARGET_ENV_FIXTURE):
        require(path.is_file(), f"semantic negative foundation missing: {path}")

    commit_sha = head_sha()
    drill_writer = load_module(DRILL_WRITER, "memory_os_restore_drill_semantic_negative")
    evidence_writer = load_module(EVIDENCE_WRITER, "memory_os_restore_evidence_semantic_negative")

    source = generation_record(generation_id="pegen_source", environment_id="pe_source", manifest=DIGEST_A, environment_record=SOURCE_ENV_FIXTURE, commit_sha=commit_sha)
    target = generation_record(generation_id="pegen_target", environment_id="pe_target", manifest=DIGEST_B, environment_record=TARGET_ENV_FIXTURE, commit_sha=commit_sha)

    with tempfile.TemporaryDirectory(prefix="memory-os-semantic-generation-negative-") as tmp:
        tmp_path = Path(tmp)
        generation_registry = tmp_path / "generations.json"
        objectives_registry = tmp_path / "objectives.json"
        drill_registry = tmp_path / "drill-requests.json"
        overlay_registry = tmp_path / "typed-overlay.json"

        canonical_generations = {
            "schemaVersion": "memory-os-production-equivalent-environment-generation-registry.v1",
            "registryClass": "PRODUCTION_EQUIVALENT_ENVIRONMENT_GENERATIONS",
            "appendOnly": True,
            "registeredGenerationCount": 2,
            "currentGenerationId": "pegen_target",
            "productionEvidence": False,
            "generations": [source, target],
        }
        write_json(generation_registry, canonical_generations)
        write_json(objectives_registry, {
            "schemaVersion": "memory-os-recovery-objectives-registry.v1",
            "appendOnly": True,
            "approvedObjectiveCount": 1,
            "currentObjectiveId": "recovery_objectives_ci",
            "records": [{"objectiveId": "recovery_objectives_ci", "rpoSeconds": 60, "rtoSeconds": 120, "maximumObjectDatabaseSkewSeconds": 10, "approvedAt": "2026-08-07T23:55:00Z"}],
            "productionEvidence": False,
            "productionReady": False,
        })
        request = drill_request()
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

        drill_writer.GEN_REGISTRY = generation_registry
        drill_writer.OBJECTIVES_REGISTRY = objectives_registry
        evidence_writer.GEN_REGISTRY = generation_registry
        evidence_writer.OBJECTIVES_REGISTRY = objectives_registry
        evidence_writer.DRILL_REQUEST_REGISTRY = drill_registry
        evidence_writer.NON_RESURRECTION_REGISTRY = overlay_registry

        drill_writer.validate_request(request, require_current=True)
        valid_evidence = evidence_record(commit_sha)
        evidence_writer.validate_record(valid_evidence)
        print("PASS baseline: both registered generations are semantically preflight eligible")

        bad_source = copy.deepcopy(canonical_generations)
        bad_source["generations"][0]["environmentRecordSha256"] = DIGEST_F
        write_json(generation_registry, bad_source)
        expect_rejected("registered source generation loses semantic eligibility for drill request", lambda: drill_writer.validate_request(request, require_current=True))
        expect_rejected("registered source generation loses semantic eligibility for new recovery evidence", lambda: evidence_writer.validate_record(valid_evidence))

        bad_target = copy.deepcopy(canonical_generations)
        bad_target["generations"][1]["environmentRecordSha256"] = DIGEST_F
        write_json(generation_registry, bad_target)
        expect_rejected("registered restore target generation loses semantic eligibility for drill request", lambda: drill_writer.validate_request(request, require_current=True))
        expect_rejected("registered restore target generation loses semantic eligibility for new recovery evidence", lambda: evidence_writer.validate_record(valid_evidence))

        write_json(generation_registry, canonical_generations)
        evidence_writer.validate_record(valid_evidence, require_current_drill_request=False)
        print("PASS history: valid immutable evidence remains auditable when current-only gate is disabled")

    print("Memory OS semantic generation negative admission suite PASS")
    print("registered generation alone creates current drill authority: false")
    print("semantically ineligible generation creates new recovery evidence: false")
    print("nested explicit domain validation failures recognized: true")
    print("unexpected implementation exception accepted as valid rejection: false")
    print("canonical registries mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE SEMANTIC GENERATION NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
