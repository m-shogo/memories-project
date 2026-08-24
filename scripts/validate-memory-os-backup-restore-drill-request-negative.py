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


EXPECTED_FAILURE: type[Exception] = Fail


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def path_label(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path_label(path)}")
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
    except EXPECTED_FAILURE:
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
            "recoveryOwner": "recovery-owner-approval.json",
            "securityReview": "security-approval.json",
            "operabilityReview": "operability-approval.json",
        },
        "stopConditions": list(contract["requiredStopConditions"]),
        "openRisks": [],
        "productionTraffic": False,
        "productionCredentials": False,
        "automaticPromotion": False,
        "productionEvidence": False,
        "productionReady": False,
    }


def approval_payload(writer: Any, contract: dict[str, Any], request: dict[str, Any], role: str, reviewer: str) -> dict[str, Any]:
    return {
        "schemaVersion": contract["approvalSchemaVersion"],
        "requestId": request["requestId"],
        "requestRecordSha256": writer.canonical_request_sha256(request),
        "reviewRole": role,
        "decision": "APPROVED",
        "sourceEnvironmentGenerationId": request["sourceEnvironmentGenerationId"],
        "restoreTargetEnvironmentGenerationId": request["restoreTargetEnvironmentGenerationId"],
        "recoveryObjectivesId": request["recoveryObjectivesId"],
        "approvedAt": "2026-08-08T00:01:00Z",
        "reviewerPseudonym": reviewer,
        "productionTraffic": False,
        "productionCredentials": False,
        "automaticPromotion": False,
    }


def bind_approvals(tmp_path: Path, writer: Any, contract: dict[str, Any], request: dict[str, Any]) -> None:
    mapping = (
        ("recoveryOwner", "RECOVERY_OWNER", "reviewer_recovery_owner"),
        ("securityReview", "SECURITY", "reviewer_security"),
        ("operabilityReview", "OPERABILITY", "reviewer_operability"),
    )
    for key, role, reviewer in mapping:
        write_json(tmp_path / request["approvalRefs"][key], approval_payload(writer, contract, request, role, reviewer))


def main() -> int:
    global EXPECTED_FAILURE
    require(WRITER.is_file() and CONTRACT.is_file(), "drill request foundation missing")
    contract = load(CONTRACT)
    writer = load_writer()
    EXPECTED_FAILURE = writer.Fail
    require(contract.get("approvalSchemaVersion") == "memory-os-backup-restore-drill-request-approval.v2", "approval schema must remain digest-bound v2")
    require("requestRecordSha256" in set(contract.get("requiredApprovalFields", [])), "approval requestRecordSha256 authority missing")
    require(contract.get("admissionRules", {}).get("approvalDocumentsMustBindCanonicalRequestRecordDigest") is True, "approval digest admission rule missing")
    require(contract.get("admissionRules", {}).get("approvalDocumentsMustNotPredateRequest") is True, "approval chronology admission rule missing")
    require(contract.get("admissionRules", {}).get("approvalReviewerPseudonymsMustBeCanonicalNonEmptyText") is True, "canonical reviewer pseudonym admission rule missing")

    canonical_probe = base_request(contract)
    canonical_probe["requestId"] = "brrq_no_prerequisites"
    expect_rejected("canonical empty generation/objective registries", lambda: writer.validate_request(canonical_probe))

    shared_eligibility_helper = writer.load_eligibility_helper()

    class SyntheticGenerationWriter:
        class Fail(RuntimeError):
            pass

        @staticmethod
        def validate_record(record: dict[str, Any]) -> bool:
            return True

        @classmethod
        def validate_registry_for_append(cls, registry: dict[str, Any]) -> list[dict[str, Any]]:
            if registry.get("schemaVersion") != "memory-os-production-equivalent-environment-generation-registry.v1":
                raise cls.Fail("registry schema drift")
            if registry.get("registryClass") != "PRODUCTION_EQUIVALENT_ENVIRONMENT_GENERATIONS":
                raise cls.Fail("registry class drift")
            if registry.get("appendOnly") is not True:
                raise cls.Fail("registry must remain append-only")
            if registry.get("productionEvidence") is not False:
                raise cls.Fail("registry production evidence boundary drift")
            rows = registry.get("generations")
            count = registry.get("registeredGenerationCount")
            if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
                raise cls.Fail("registry generations invalid")
            if not isinstance(count, int) or isinstance(count, bool) or count != len(rows):
                raise cls.Fail("registeredGenerationCount drift")
            ids: set[str] = set()
            previous_by_environment: dict[str, str] = {}
            for row in rows:
                generation_id = row.get("generationId")
                environment_id = row.get("environmentId")
                if not isinstance(generation_id, str) or not generation_id or generation_id in ids:
                    raise cls.Fail("generationId authority invalid")
                if not isinstance(environment_id, str) or not environment_id:
                    raise cls.Fail("environmentId authority invalid")
                ids.add(generation_id)
                if row.get("supersedesGenerationId") != previous_by_environment.get(environment_id):
                    raise cls.Fail("generation supersession chain drift")
                previous_by_environment[environment_id] = generation_id
                cls.validate_record(row)
            expected_current = rows[-1].get("generationId") if rows else None
            if registry.get("currentGenerationId") != expected_current:
                raise cls.Fail("currentGenerationId must equal latest append-only record")
            return rows

    real_independent_review_ref = shared_eligibility_helper.independent_review_ref_for_row
    shared_eligibility_helper.load_generation_writer = lambda: SyntheticGenerationWriter
    shared_eligibility_helper.independent_review_ref_for_row = (
        lambda _writer, row: f"synthetic-review:{row['generationId']}"
    )

    with tempfile.TemporaryDirectory(prefix="memory-os-restore-drill-request-negative-") as tmp:
        tmp_path = Path(tmp)
        generation_registry = tmp_path / "generations.json"
        objectives_registry = tmp_path / "objectives.json"
        simulated_contract = tmp_path / CONTRACT.name
        write_json(simulated_contract, contract)
        write_json(generation_registry, {
            "schemaVersion": "memory-os-production-equivalent-environment-generation-registry.v1",
            "registryClass": "PRODUCTION_EQUIVALENT_ENVIRONMENT_GENERATIONS",
            "appendOnly": True,
            "productionEvidence": False,
            "registeredGenerationCount": 2,
            "currentGenerationId": "pegen_target",
            "generations": [
                {
                    "generationId": "pegen_source",
                    "environmentId": "pe_source",
                    "environmentManifestSha256": DIGEST_A,
                    "registeredAt": "2026-08-07T23:00:00Z",
                    "supersedesGenerationId": None,
                },
                {
                    "generationId": "pegen_target",
                    "environmentId": "pe_target",
                    "environmentManifestSha256": DIGEST_B,
                    "registeredAt": "2026-08-07T23:10:00Z",
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
                {"objectiveId": "recovery_objectives_old", "approvedAt": "2026-08-07T23:20:00Z"},
                {"objectiveId": "recovery_objectives_current", "approvedAt": "2026-08-07T23:30:00Z"},
            ],
            "productionEvidence": False,
            "productionReady": False,
        })
        for ref in ("SECURITY.md", "README.md", "CLAUDE.md"):
            (tmp_path / ref).write_text("fixture entry criterion\n", encoding="utf-8")

        writer.GEN_REGISTRY = generation_registry
        writer.OBJECTIVES_REGISTRY = objectives_registry
        real_root = writer.ROOT
        real_eligibility_guard = writer.require_preflight_eligible_generation
        real_eligibility_loader = writer.load_eligibility_helper
        writer.ROOT = tmp_path
        writer.CONTRACT = simulated_contract
        writer.CANONICAL_CONTRACT = simulated_contract
        writer.load_eligibility_helper = lambda: shared_eligibility_helper
        writer.require_preflight_eligible_generation = lambda generation_id, field: None if generation_id in {"pegen_source", "pegen_target"} else (_ for _ in ()).throw(writer.Fail(f"{field} synthetic generation not eligible"))

        def validate_bound(request: dict[str, Any], *, require_current: bool = True) -> None:
            bind_approvals(tmp_path, writer, contract, request)
            writer.validate_request(request, require_current=require_current)

        valid = base_request(contract)
        validate_bound(valid)
        validate_bound(valid, require_current=False)
        require(writer.request_currently_executable(valid) is True, "valid synthetic request should be current in isolated negative fixture")
        print("PASS accept: fully bound isolated planning request with digest-bound typed approvals and prerequisite chronology")

        generation_authority = load(generation_registry)
        generation_authority["registeredGenerationCount"] = 3
        write_json(generation_registry, generation_authority)
        expect_rejected("generation registry aggregate count drift", lambda: validate_bound(valid))
        generation_authority["registeredGenerationCount"] = 2
        write_json(generation_registry, generation_authority)

        generation_authority["registryClass"] = "LEGACY_GENERATIONS"
        write_json(generation_registry, generation_authority)
        expect_rejected("generation registry class drift", lambda: validate_bound(valid))
        generation_authority["registryClass"] = "PRODUCTION_EQUIVALENT_ENVIRONMENT_GENERATIONS"
        write_json(generation_registry, generation_authority)

        expect_rejected("absolute drill authority ref", lambda: writer.repo_ref(str((tmp_path / "SECURITY.md").resolve()), "negative.absolute"))
        expect_rejected("parent-traversal drill authority ref", lambda: writer.repo_ref("nested/../SECURITY.md", "negative.parent"))
        escaped_ref = tmp_path / "escaped-entry.md"
        try:
            escaped_ref.symlink_to(ROOT / "SECURITY.md")
            expect_rejected("drill authority symlink escapes repository root", lambda: writer.repo_ref("escaped-entry.md", "negative.symlink"))
        finally:
            escaped_ref.unlink(missing_ok=True)

        predates_generation = copy.deepcopy(valid)
        predates_generation["requestId"] = "brrq_predates_generation"
        predates_generation["requestedAt"] = "2026-08-07T22:59:59Z"
        expect_rejected("request predates registered generations", lambda: validate_bound(predates_generation))

        objectives_after_request = load(objectives_registry)
        objectives_after_request["records"][1]["approvedAt"] = "2026-08-08T00:00:01Z"
        write_json(objectives_registry, objectives_after_request)
        expect_rejected("request predates current recovery objective approval", lambda: validate_bound(valid))
        objectives_after_request["records"][1]["approvedAt"] = "2026-08-07T23:30:00Z"
        write_json(objectives_registry, objectives_after_request)

        bind_approvals(tmp_path, writer, contract, valid)
        security_path = tmp_path / valid["approvalRefs"]["securityReview"]
        security = load(security_path)
        security["approvedAt"] = "2026-08-07T23:59:59Z"
        write_json(security_path, security)
        expect_rejected("approval predates request", lambda: writer.validate_request(valid))

        bind_approvals(tmp_path, writer, contract, valid)
        mutated_after_approval = copy.deepcopy(valid)
        mutated_after_approval["openRisks"] = [{"riskId": "risk_low_after_approval", "severity": "LOW", "status": "OPEN", "ownerRef": "README.md"}]
        expect_rejected("request mutated after human approvals", lambda: writer.validate_request(mutated_after_approval))

        bind_approvals(tmp_path, writer, contract, valid)
        security = load(security_path)
        security["requestRecordSha256"] = "0" * 64
        write_json(security_path, security)
        expect_rejected("approval request digest mismatch", lambda: writer.validate_request(valid))

        bind_approvals(tmp_path, writer, contract, valid)
        (tmp_path / "SECURITY.md").write_text("not json\n", encoding="utf-8")
        arbitrary_approval = copy.deepcopy(valid)
        arbitrary_approval["approvalRefs"]["securityReview"] = "SECURITY.md"
        expect_rejected("arbitrary repository file used as approval", lambda: writer.validate_request(arbitrary_approval))

        bind_approvals(tmp_path, writer, contract, valid)
        security = load(security_path)
        security["requestId"] = "brrq_other_request"
        write_json(security_path, security)
        expect_rejected("approval bound to another request", lambda: writer.validate_request(valid))

        bind_approvals(tmp_path, writer, contract, valid)
        security = load(security_path)
        security["reviewRole"] = "OPERABILITY"
        write_json(security_path, security)
        expect_rejected("approval review role mismatch", lambda: writer.validate_request(valid))

        bind_approvals(tmp_path, writer, contract, valid)
        security = load(security_path)
        security["recoveryObjectivesId"] = "recovery_objectives_old"
        write_json(security_path, security)
        expect_rejected("approval bound to another recovery objective", lambda: writer.validate_request(valid))

        bind_approvals(tmp_path, writer, contract, valid)
        security = load(security_path)
        security["decision"] = "REJECTED"
        write_json(security_path, security)
        expect_rejected("approval decision not approved", lambda: writer.validate_request(valid))

        bind_approvals(tmp_path, writer, contract, valid)
        security = load(security_path)
        security["productionTraffic"] = True
        write_json(security_path, security)
        expect_rejected("approval permits production traffic", lambda: writer.validate_request(valid))

        bind_approvals(tmp_path, writer, contract, valid)
        operability_path = tmp_path / valid["approvalRefs"]["operabilityReview"]
        operability = load(operability_path)
        operability["reviewerPseudonym"] = "reviewer_security"
        write_json(operability_path, operability)
        expect_rejected("approval reviewer pseudonym reuse", lambda: writer.validate_request(valid))

        bind_approvals(tmp_path, writer, contract, valid)
        operability = load(operability_path)
        operability["reviewerPseudonym"] = " reviewer_security "
        write_json(operability_path, operability)
        expect_rejected("whitespace-aliased reviewer pseudonym reuse", lambda: writer.validate_request(valid))

        real_guard_for_probe = writer.require_preflight_eligible_generation
        writer.require_preflight_eligible_generation = lambda generation_id, field: (_ for _ in ()).throw(writer.Fail(f"{field} not semantically eligible"))
        expect_rejected("semantically ineligible source/target generation", lambda: validate_bound(valid))
        writer.require_preflight_eligible_generation = real_guard_for_probe

        same_generation = copy.deepcopy(valid)
        same_generation["requestId"] = "brrq_same_generation"
        same_generation["restoreTargetEnvironmentGenerationId"] = "pegen_source"
        same_generation["restoreTargetManifestSha256"] = DIGEST_A
        expect_rejected("same generation source and target", lambda: validate_bound(same_generation))

        manifest_mismatch = copy.deepcopy(valid)
        manifest_mismatch["requestId"] = "brrq_manifest_mismatch"
        manifest_mismatch["sourceEnvironmentManifestSha256"] = DIGEST_B
        expect_rejected("source manifest mismatch", lambda: validate_bound(manifest_mismatch))

        old_objective = copy.deepcopy(valid)
        old_objective["requestId"] = "brrq_old_objective"
        old_objective["recoveryObjectivesId"] = "recovery_objectives_old"
        expect_rejected("historical non-current recovery objective for new request", lambda: validate_bound(old_objective))
        validate_bound(old_objective, require_current=False)
        print("PASS history: registered historical objective remains structurally valid")

        missing_domain = copy.deepcopy(valid)
        missing_domain["requestId"] = "brrq_missing_domain"
        missing_domain["requiredEvidenceDomains"] = missing_domain["requiredEvidenceDomains"][:-1]
        expect_rejected("missing required evidence domain", lambda: validate_bound(missing_domain))

        missing_stop = copy.deepcopy(valid)
        missing_stop["requestId"] = "brrq_missing_stop"
        missing_stop["stopConditions"] = missing_stop["stopConditions"][:-1]
        expect_rejected("missing required stop condition", lambda: validate_bound(missing_stop))

        weak_isolation = copy.deepcopy(valid)
        weak_isolation["requestId"] = "brrq_weak_isolation"
        weak_isolation["isolationPolicy"]["networkIsolated"] = False
        expect_rejected("network isolation disabled", lambda: validate_bound(weak_isolation))

        weak_pitr = copy.deepcopy(valid)
        weak_pitr["requestId"] = "brrq_no_pitr"
        weak_pitr["databasePolicy"]["pitrRequired"] = False
        expect_rejected("PITR not required", lambda: validate_bound(weak_pitr))

        weak_object = copy.deepcopy(valid)
        weak_object["requestId"] = "brrq_weak_object"
        weak_object["objectPolicy"]["restoreOnlyCredentialsRequired"] = False
        expect_rejected("restore-only credential separation disabled", lambda: validate_bound(weak_object))

        same_approval = copy.deepcopy(valid)
        same_approval["requestId"] = "brrq_same_approval"
        same_approval["approvalRefs"]["operabilityReview"] = same_approval["approvalRefs"]["securityReview"]
        expect_rejected("review approval path reuse", lambda: validate_bound(same_approval))

        high_risk = copy.deepcopy(valid)
        high_risk["requestId"] = "brrq_high_risk"
        high_risk["openRisks"] = [{"riskId": "risk_high", "severity": "HIGH", "status": "OPEN", "ownerRef": "README.md"}]
        expect_rejected("HIGH open risk", lambda: validate_bound(high_risk))

        production_traffic = copy.deepcopy(valid)
        production_traffic["requestId"] = "brrq_prod_traffic"
        production_traffic["productionTraffic"] = True
        expect_rejected("production traffic enabled", lambda: validate_bound(production_traffic))

        automatic_promotion = copy.deepcopy(valid)
        automatic_promotion["requestId"] = "brrq_auto_promotion"
        automatic_promotion["automaticPromotion"] = True
        expect_rejected("automatic promotion enabled", lambda: validate_bound(automatic_promotion))

        mutable_alias = copy.deepcopy(valid)
        mutable_alias["requestId"] = "brrq_latest_alias"
        expect_rejected("mutable latest alias", lambda: validate_bound(mutable_alias))

        superseded_registry = load(generation_registry)
        superseded_registry["registeredGenerationCount"] = 3
        superseded_registry["currentGenerationId"] = "pegen_source_successor"
        superseded_registry["generations"].append({
            "generationId": "pegen_source_successor",
            "environmentId": "pe_source",
            "environmentManifestSha256": "c" * 64,
            "registeredAt": "2026-08-08T00:10:00Z",
            "supersedesGenerationId": "pegen_source",
        })
        write_json(generation_registry, superseded_registry)
        superseded = copy.deepcopy(valid)
        superseded["requestId"] = "brrq_superseded_source"
        expect_rejected("superseded source generation for new/current execution", lambda: validate_bound(superseded))
        validate_bound(superseded, require_current=False)
        bind_approvals(tmp_path, writer, contract, superseded)
        require(writer.request_currently_executable(superseded) is False, "superseded historical request must not remain executable")
        print("PASS history: superseded generation request remains auditable but non-executable")

        writer.ROOT = real_root
        writer.require_preflight_eligible_generation = real_eligibility_guard
        writer.load_eligibility_helper = real_eligibility_loader

    shared_eligibility_helper.independent_review_ref_for_row = real_independent_review_ref

    print("Memory OS production-equivalent backup/restore drill request negative suite PASS")
    print("canonical request registry mutated: false")
    print("semantic generation eligibility bypass: false")
    print("corrupt generation aggregate authority accepted: false")
    print("request chronology predates generation/objective authority: false")
    print("arbitrary repository approval authority: false")
    print("drill request authority refs escape repository: false")
    print("typed approval request/generation/objective binding enforced: true")
    print("typed approvals bind canonical request-record digest: true")
    print("approval chronology bound to request creation: true")
    print("post-approval planning request mutation accepted: false")
    print("independent reviewer pseudonyms enforced: true")
    print("whitespace-aliased reviewer identity accepted: false")
    print("historical authority preserved across supersession: true")
    print("current execution revalidation preserved: true")
    print("unexpected exception accepted as a valid rejection: false")
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
