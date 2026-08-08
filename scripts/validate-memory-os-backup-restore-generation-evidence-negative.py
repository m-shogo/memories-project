#!/usr/bin/env python3
"""Prove fail-closed negative cases for generation-bound backup/restore admission.

This validator never mutates the canonical registries. It imports the canonical
writer and redirects generation/objective/typed-overlay lookups to temporary
fixtures so rejection and two-phase candidate boundaries are deterministic.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
NON_RESURRECTION_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
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
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
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
    except Exception:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def base_record(commit_sha: str) -> dict[str, Any]:
    contract = load(CONTRACT)
    record = {field: None for field in contract["requiredRecordFields"]}
    record.update(
        {
            "schemaVersion": contract["recordSchemaVersion"],
            "evidenceId": "brge_negative_base",
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
        }
    )
    return record


def typed_overlay_record(evidence_id: str) -> dict[str, Any]:
    contract = load(NON_RESURRECTION_CONTRACT)
    domains = {
        name: {"result": "PASS", "evidenceRef": f"docs/evidence/backup-restore/non-resurrection/{name}.json"}
        for name in contract["requiredDomains"]
    }
    return {
        "schemaVersion": contract["recordSchemaVersion"],
        "recordId": "brnr_negative_overlay",
        "generationEvidenceId": evidence_id,
        "sourceCommitSha": "0" * 40,
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
    require(WRITER.is_file() and CONTRACT.is_file() and NON_RESURRECTION_CONTRACT.is_file(), "generation evidence foundation missing")
    writer = load_writer()
    commit_sha = head_sha()

    unregistered_case = base_record(commit_sha)
    unregistered_case["evidenceId"] = "brge_no_generation"
    unregistered_case["sourceEnvironmentGenerationId"] = "pegen_negative_unregistered_source"
    unregistered_case["restoreTargetGenerationId"] = "pegen_negative_unregistered_target"
    expect_rejected("no registered production-equivalent generation", lambda: writer.validate_record(unregistered_case))

    with tempfile.TemporaryDirectory(prefix="memory-os-restore-negative-") as tmp:
        tmp_path = Path(tmp)
        generation_registry = tmp_path / "generations.json"
        objectives_registry = tmp_path / "objectives.json"
        overlay_registry = tmp_path / "typed-overlay.json"
        write_json(
            generation_registry,
            {
                "schemaVersion": "memory-os-production-equivalent-environment-generation-registry.v1",
                "appendOnly": True,
                "registeredGenerationCount": 2,
                "currentGenerationId": "pegen_target",
                "productionEvidence": False,
                "generations": [
                    {"generationId": "pegen_source", "environmentManifestSha256": DIGEST_A, "sourceCommitSha": commit_sha},
                    {"generationId": "pegen_target", "environmentManifestSha256": DIGEST_B, "sourceCommitSha": commit_sha},
                ],
            },
        )
        write_json(
            objectives_registry,
            {
                "schemaVersion": "memory-os-recovery-objectives-registry.v1",
                "appendOnly": True,
                "approvedObjectiveCount": 2,
                "currentObjectiveId": "recovery_objectives_ci",
                "records": [
                    {"objectiveId": "recovery_objectives_old", "rpoSeconds": 120, "rtoSeconds": 300, "maximumObjectDatabaseSkewSeconds": 30},
                    {"objectiveId": "recovery_objectives_ci", "rpoSeconds": 60, "rtoSeconds": 120, "maximumObjectDatabaseSkewSeconds": 10},
                ],
            },
        )
        write_json(
            overlay_registry,
            {
                "schemaVersion": "memory-os-backup-restore-non-resurrection-admission-registry.v1",
                "appendOnly": True,
                "registeredRecordCount": 0,
                "completeRecordCount": 0,
                "candidateCoveredCount": 0,
                "records": [],
                "productionEvidence": False,
                "productionReady": False,
            },
        )

        writer.GEN_REGISTRY = generation_registry
        writer.OBJECTIVES_REGISTRY = objectives_registry
        writer.NON_RESURRECTION_REGISTRY = overlay_registry

        valid = base_record(commit_sha)
        writer.validate_record(valid)
        require(writer.base_candidate(valid) is True, "synthetic complete reviewed record must satisfy pre-overlay gates")
        require(writer.candidate(valid) is False, "generic non-resurrection PASS without typed overlay must not become candidate")
        print("PASS non-candidate: generic PASS lacks typed non-resurrection coverage")

        overlay = typed_overlay_record(valid["evidenceId"])
        overlay["sourceCommitSha"] = commit_sha
        write_json(
            overlay_registry,
            {
                "schemaVersion": "memory-os-backup-restore-non-resurrection-admission-registry.v1",
                "appendOnly": True,
                "registeredRecordCount": 1,
                "completeRecordCount": 1,
                "candidateCoveredCount": 1,
                "records": [overlay],
                "productionEvidence": False,
                "productionReady": False,
            },
        )
        require(writer.candidate(valid) is True, "complete typed overlay must unlock final candidate predicate")
        print("PASS candidate: complete typed non-resurrection coverage present")

        same_review = copy.deepcopy(valid)
        same_review["evidenceId"] = "brge_same_review"
        same_review["operabilityReviewRef"] = same_review["securityReviewRef"]
        expect_rejected("security/operability review reuse", lambda: writer.validate_record(same_review))

        missing_review = copy.deepcopy(valid)
        missing_review["evidenceId"] = "brge_missing_review"
        missing_review["securityReviewRef"] = "docs/evidence/does-not-exist.json"
        expect_rejected("missing review evidence path", lambda: writer.validate_record(missing_review))

        missing_delta = copy.deepcopy(valid)
        missing_delta["evidenceId"] = "brge_missing_delta"
        missing_delta["materialDeltaReviewRef"] = None
        expect_rejected("cross-generation restore without material delta review", lambda: writer.validate_record(missing_delta))

        fake_generation = copy.deepcopy(valid)
        fake_generation["evidenceId"] = "brge_fake_generation"
        fake_generation["restoreTargetGenerationId"] = "pegen_unregistered"
        expect_rejected("unregistered restore target generation", lambda: writer.validate_record(fake_generation))

        digest_mismatch = copy.deepcopy(valid)
        digest_mismatch["evidenceId"] = "brge_manifest_mismatch"
        digest_mismatch["restoreTargetManifestSha256"] = DIGEST_A
        expect_rejected("generation manifest digest mismatch", lambda: writer.validate_record(digest_mismatch))

        artifact_swap = copy.deepcopy(valid)
        artifact_swap["evidenceId"] = "brge_artifact_swap"
        artifact_swap["restoredBackupArtifactSha256"] = DIGEST_D
        expect_rejected("restored artifact differs from exact backup", lambda: writer.validate_record(artifact_swap))

        old_objective = copy.deepcopy(valid)
        old_objective["evidenceId"] = "brge_old_objective"
        old_objective["recoveryObjectivesId"] = "recovery_objectives_old"
        writer.validate_record(old_objective)
        require(writer.base_candidate(old_objective) is False, "non-current objective must fail pre-overlay gates")
        print("PASS non-candidate: historical approved objective")

        missed_rpo = copy.deepcopy(valid)
        missed_rpo["evidenceId"] = "brge_missed_rpo"
        missed_rpo["measuredRpoSeconds"] = 61
        writer.validate_record(missed_rpo)
        require(writer.base_candidate(missed_rpo) is False, "missed RPO must fail pre-overlay gates")
        print("PASS non-candidate: measured RPO exceeds approved target")

        unsafe_finding = copy.deepcopy(valid)
        unsafe_finding["evidenceId"] = "brge_high_finding"
        unsafe_finding["unresolvedFindings"] = [{"findingId": "finding_high", "severity": "HIGH", "status": "OPEN"}]
        expect_rejected("HIGH unresolved finding", lambda: writer.validate_record(unsafe_finding))

        mutable_alias = copy.deepcopy(valid)
        mutable_alias["evidenceId"] = "brge_latest_alias"
        expect_rejected("mutable latest alias", lambda: writer.validate_record(mutable_alias))

        production_flag = copy.deepcopy(valid)
        production_flag["evidenceId"] = "brge_prod_flag"
        production_flag["productionEvidence"] = True
        expect_rejected("production evidence relabel", lambda: writer.validate_record(production_flag))

    print("Memory OS generation-bound backup/restore negative admission suite PASS")
    print("canonical registries mutated: false")
    print("generic non-resurrection PASS creates candidate: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
