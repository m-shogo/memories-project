#!/usr/bin/env python3
"""Exercise fail-closed negative cases for production-equivalent restore drill requests."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_request_writer_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load drill request writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except Exception:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def base_request(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": contract["recordSchemaVersion"],
        "requestId": "brrq_negative_base",
        "requestedAt": "2026-08-08T00:00:00Z",
        "sourceEnvironmentGenerationId": "pegen_source",
        "sourceEnvironmentManifestSha256": DIGEST_A,
        "restoreTargetEnvironmentGenerationId": "pegen_target",
        "restoreTargetManifestSha256": DIGEST_B,
        "recoveryObjectivesId": "recovery_objectives_current",
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
        "entryCriteriaRefs": ["SECURITY.md", "README.md", "CLAUDE.md"],
        "approvalRefs": {
            "recoveryOwner": "README.md",
            "securityReview": "SECURITY.md",
            "operabilityReview": "CLAUDE.md",
        },
        "stopConditions": list(contract["requiredStopConditions"]),
        "openRisks": [],
        "productionTraffic": False,
        "productionCredentials": False,
        "automaticPromotion": False,
        "productionEvidence": False,
        "productionReady": False,
    }


def main() -> int:
    require(WRITER.is_file() and CONTRACT.is_file(), "drill request foundation missing")
    contract = load(CONTRACT)
    writer = load_writer()

    canonical_probe = base_request(contract)
    canonical_probe["requestId"] = "brrq_no_prerequisites"
    expect_rejected("canonical empty generation/objective registries", lambda: writer.validate_request(canonical_probe))

    with tempfile.TemporaryDirectory(prefix="memory-os-restore-drill-request-negative-") as tmp:
        tmp_path = Path(tmp)
        generation_registry = tmp_path / "generations.json"
        objectives_registry = tmp_path / "objectives.json"
        write_json(generation_registry, {
            "schemaVersion": "memory-os-production-equivalent-environment-generation-registry.v1",
            "appendOnly": True,
            "productionEvidence": False,
            "registeredGenerationCount": 2,
            "currentGenerationId": "pegen_target",
            "generations": [
                {
                    "generationId": "pegen_source",
                    "environmentId": "pe_source",
                    "environmentManifestSha256": DIGEST_A,
                    "supersedesGenerationId": None,
                },
                {
                    "generationId": "pegen_target",
                    "environmentId": "pe_target",
                    "environmentManifestSha256": DIGEST_B,
                    "supersedesGenerationId": None,
                },
            ],
        })
        write_json(objectives_registry, {
            "schemaVersion": "memory-os-recovery-objectives-registry.v1",
            "appendOnly": True,
            "approvedObjectiveCount": 2,
            "currentObjectiveId": "recovery_objectives_current",
            "records": [
                {"objectiveId": "recovery_objectives_old"},
                {"objectiveId": "recovery_objectives_current"},
            ],
            "productionEvidence": False,
            "productionReady": False,
        })
        writer.GEN_REGISTRY = generation_registry
        writer.OBJECTIVES_REGISTRY = objectives_registry
        real_repo_ref = writer.repo_ref
        writer.repo_ref = lambda value, field: value if isinstance(value, str) and value else (_ for _ in ()).throw(writer.Fail(f"{field} invalid"))

        valid = base_request(contract)
        writer.validate_request(valid)
        require(writer.request_currently_executable(valid) is True, "valid synthetic request should be current in isolated negative fixture")
        print("PASS accept: fully bound isolated planning request")

        same_generation = copy.deepcopy(valid)
        same_generation["requestId"] = "brrq_same_generation"
        same_generation["restoreTargetEnvironmentGenerationId"] = "pegen_source"
        same_generation["restoreTargetManifestSha256"] = DIGEST_A
        expect_rejected("same generation source and target", lambda: writer.validate_request(same_generation))

        manifest_mismatch = copy.deepcopy(valid)
        manifest_mismatch["requestId"] = "brrq_manifest_mismatch"
        manifest_mismatch["sourceEnvironmentManifestSha256"] = DIGEST_B
        expect_rejected("source manifest mismatch", lambda: writer.validate_request(manifest_mismatch))

        old_objective = copy.deepcopy(valid)
        old_objective["requestId"] = "brrq_old_objective"
        old_objective["recoveryObjectivesId"] = "recovery_objectives_old"
        expect_rejected("historical non-current recovery objective", lambda: writer.validate_request(old_objective))

        missing_domain = copy.deepcopy(valid)
        missing_domain["requestId"] = "brrq_missing_domain"
        missing_domain["requiredEvidenceDomains"] = missing_domain["requiredEvidenceDomains"][:-1]
        expect_rejected("missing required evidence domain", lambda: writer.validate_request(missing_domain))

        missing_stop = copy.deepcopy(valid)
        missing_stop["requestId"] = "brrq_missing_stop"
        missing_stop["stopConditions"] = missing_stop["stopConditions"][:-1]
        expect_rejected("missing required stop condition", lambda: writer.validate_request(missing_stop))

        weak_isolation = copy.deepcopy(valid)
        weak_isolation["requestId"] = "brrq_weak_isolation"
        weak_isolation["isolationPolicy"]["networkIsolated"] = False
        expect_rejected("network isolation disabled", lambda: writer.validate_request(weak_isolation))

        weak_pitr = copy.deepcopy(valid)
        weak_pitr["requestId"] = "brrq_no_pitr"
        weak_pitr["databasePolicy"]["pitrRequired"] = False
        expect_rejected("PITR not required", lambda: writer.validate_request(weak_pitr))

        weak_object = copy.deepcopy(valid)
        weak_object["requestId"] = "brrq_weak_object"
        weak_object["objectPolicy"]["restoreOnlyCredentialsRequired"] = False
        expect_rejected("restore-only credential separation disabled", lambda: writer.validate_request(weak_object))

        same_approval = copy.deepcopy(valid)
        same_approval["requestId"] = "brrq_same_approval"
        same_approval["approvalRefs"]["operabilityReview"] = same_approval["approvalRefs"]["securityReview"]
        expect_rejected("review approval reuse", lambda: writer.validate_request(same_approval))

        high_risk = copy.deepcopy(valid)
        high_risk["requestId"] = "brrq_high_risk"
        high_risk["openRisks"] = [{"riskId": "risk_high", "severity": "HIGH", "status": "OPEN", "ownerRef": "README.md"}]
        expect_rejected("HIGH open risk", lambda: writer.validate_request(high_risk))

        production_traffic = copy.deepcopy(valid)
        production_traffic["requestId"] = "brrq_prod_traffic"
        production_traffic["productionTraffic"] = True
        expect_rejected("production traffic enabled", lambda: writer.validate_request(production_traffic))

        automatic_promotion = copy.deepcopy(valid)
        automatic_promotion["requestId"] = "brrq_auto_promotion"
        automatic_promotion["automaticPromotion"] = True
        expect_rejected("automatic promotion enabled", lambda: writer.validate_request(automatic_promotion))

        mutable_alias = copy.deepcopy(valid)
        mutable_alias["requestId"] = "brrq_latest_alias"
        expect_rejected("mutable latest alias", lambda: writer.validate_request(mutable_alias))

        superseded_registry = load(generation_registry)
        superseded_registry["registeredGenerationCount"] = 3
        superseded_registry["generations"].append({
            "generationId": "pegen_source_successor",
            "environmentId": "pe_source",
            "environmentManifestSha256": "c" * 64,
            "supersedesGenerationId": "pegen_source",
        })
        write_json(generation_registry, superseded_registry)
        superseded = copy.deepcopy(valid)
        superseded["requestId"] = "brrq_superseded_source"
        expect_rejected("superseded source generation", lambda: writer.validate_request(superseded))

        writer.repo_ref = real_repo_ref

    print("Memory OS production-equivalent backup/restore drill request negative suite PASS")
    print("canonical request registry mutated: false")
    print("production traffic: false")
    print("automatic promotion: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL REQUEST NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
