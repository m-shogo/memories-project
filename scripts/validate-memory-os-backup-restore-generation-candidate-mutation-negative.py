#!/usr/bin/env python3
"""Prove final recovery candidate eligibility is revoked by typed evidence mutation.

This harness never mutates canonical registries. It constructs isolated temporary
registries, writes transient typed evidence files under the contract-approved
repository prefixes, forces the generation candidate predicate through the real
typed non-resurrection validator, mutates one domain payload and one review
payload in place, and proves both stale authorities fail closed.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GEN_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py"
GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
NONRES_WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
NONRES_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def repo_ref(path: Path) -> str:
    return str(path.relative_to(ROOT))


def transient_path(prefix: str, suffix: str) -> Path:
    prefix_path = ROOT / prefix
    prefix_path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        prefix=prefix_path.name,
        suffix=suffix,
        dir=prefix_path.parent,
        delete=False,
        encoding="utf-8",
    )
    path = Path(handle.name)
    handle.close()
    return path


def build_typed_overlay(
    *,
    contract: dict[str, Any],
    overlay_writer: Any,
    evidence_id: str,
    commit_sha: str,
    cleanup: list[Path],
) -> tuple[dict[str, Any], dict[str, Path], dict[str, Path]]:
    record_id = "brnr_candidate_mutation_negative"
    domains: dict[str, Any] = {}
    domain_payloads: dict[str, dict[str, Any]] = {}
    domain_paths: dict[str, Path] = {}
    domain_digests: dict[str, str] = {}

    prefixes = contract["domainEvidencePathPrefixes"]
    for domain in contract["requiredDomains"]:
        path = transient_path(prefixes[domain], ".json")
        cleanup.append(path)
        payload = {
            "schemaVersion": "memory-os-backup-restore-non-resurrection-domain-evidence.v1",
            "generationEvidenceId": evidence_id,
            "sourceCommitSha": commit_sha,
            "domain": domain,
            "result": "PASS",
            "productionTraffic": False,
            "productionCredentials": False,
            "productionEvidence": False,
            "productionReady": False,
        }
        write_json(path, payload)
        ref = repo_ref(path)
        domains[domain] = {"result": "PASS", "evidenceRef": ref}
        domain_payloads[domain] = payload
        domain_paths[domain] = path
        domain_digests[ref] = overlay_writer.payload_sha256(payload)

    review_paths: dict[str, Path] = {}
    review_payloads: dict[str, dict[str, Any]] = {}
    review_prefixes = contract["reviewEvidencePathPrefixes"]
    for review_type, reviewer in (("SECURITY", "security_reviewer_ci"), ("OPERABILITY", "operability_reviewer_ci")):
        path = transient_path(review_prefixes[review_type], ".json")
        cleanup.append(path)
        payload = {
            "schemaVersion": "memory-os-backup-restore-non-resurrection-review-evidence.v1",
            "generationEvidenceId": evidence_id,
            "sourceCommitSha": commit_sha,
            "typedRecordId": record_id,
            "reviewType": review_type,
            "reviewerPseudonym": reviewer,
            "reviewedDomainEvidenceRefs": sorted(domain_digests),
            "reviewedDomainEvidenceSha256": dict(sorted(domain_digests.items())),
            "result": "APPROVED",
            "productionTraffic": False,
            "productionCredentials": False,
            "productionEvidence": False,
            "productionReady": False,
        }
        write_json(path, payload)
        review_paths[review_type] = path
        review_payloads[review_type] = payload

    record = {
        "schemaVersion": contract["recordSchemaVersion"],
        "recordId": record_id,
        "generationEvidenceId": evidence_id,
        "sourceCommitSha": commit_sha,
        "domains": domains,
        "securityReviewRef": repo_ref(review_paths["SECURITY"]),
        "securityReviewSha256": overlay_writer.payload_sha256(review_payloads["SECURITY"]),
        "operabilityReviewRef": repo_ref(review_paths["OPERABILITY"]),
        "operabilityReviewSha256": overlay_writer.payload_sha256(review_payloads["OPERABILITY"]),
        "unresolvedFindings": [],
        "evidenceComplete": True,
        "productionTraffic": False,
        "productionCredentials": False,
        "productionEvidence": False,
        "productionReady": False,
    }
    return record, domain_paths, review_paths


def main() -> int:
    require(GEN_NEGATIVE.is_file() and GEN_WRITER.is_file() and NONRES_WRITER.is_file() and NONRES_CONTRACT.is_file(), "candidate mutation foundation missing")
    helpers = load_module(GEN_NEGATIVE, "memory_os_generation_negative_helpers")
    writer = load_module(GEN_WRITER, "memory_os_generation_writer_candidate_mutation")
    overlay_writer = load_module(NONRES_WRITER, "memory_os_nonres_writer_candidate_mutation")
    contract = load_json(NONRES_CONTRACT)
    commit_sha = helpers.head_sha()
    cleanup: list[Path] = []

    try:
        with tempfile.TemporaryDirectory(prefix="memory-os-candidate-mutation-") as tmp:
            tmp_path = Path(tmp)
            generation_registry = tmp_path / "generations.json"
            objectives_registry = tmp_path / "objectives.json"
            drill_registry = tmp_path / "drill-requests.json"
            generation_evidence_registry = tmp_path / "generation-evidence.json"
            overlay_registry = tmp_path / "typed-overlay.json"

            source_generation = helpers.generation_record(
                generation_id="pegen_source",
                environment_id="pe_source",
                environment_manifest_sha256=helpers.DIGEST_A,
                environment_record=helpers.SOURCE_ENV_FIXTURE,
                commit_sha=commit_sha,
            )
            target_generation = helpers.generation_record(
                generation_id="pegen_target",
                environment_id="pe_target",
                environment_manifest_sha256=helpers.DIGEST_B,
                environment_record=helpers.TARGET_ENV_FIXTURE,
                commit_sha=commit_sha,
            )
            write_json(generation_registry, {
                "schemaVersion": "memory-os-production-equivalent-environment-generation-registry.v1",
                "appendOnly": True,
                "registeredGenerationCount": 2,
                "currentGenerationId": "pegen_target",
                "productionEvidence": False,
                "generations": [source_generation, target_generation],
            })
            write_json(objectives_registry, {
                "schemaVersion": "memory-os-recovery-objectives-registry.v1",
                "appendOnly": True,
                "approvedObjectiveCount": 1,
                "currentObjectiveId": "recovery_objectives_ci",
                "records": [{
                    "objectiveId": "recovery_objectives_ci",
                    "rpoSeconds": 60,
                    "rtoSeconds": 120,
                    "maximumObjectDatabaseSkewSeconds": 10,
                    "approvedAt": "2026-08-07T23:55:00Z"
                }],
                "productionEvidence": False,
                "productionReady": False,
            })
            request = helpers.base_drill_request()
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

            valid = helpers.base_record(commit_sha)
            write_json(generation_evidence_registry, {
                "schemaVersion": "memory-os-backup-restore-generation-evidence-registry.v1",
                "appendOnly": True,
                "registeredEvidenceCount": 1,
                "productionEquivalentRecoveryCandidateCount": 0,
                "records": [valid],
                "productionEvidence": False,
                "productionReady": False,
            })

            overlay, domain_paths, review_paths = build_typed_overlay(
                contract=contract,
                overlay_writer=overlay_writer,
                evidence_id=valid["evidenceId"],
                commit_sha=commit_sha,
                cleanup=cleanup,
            )
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

            writer.GEN_REGISTRY = generation_registry
            writer.OBJECTIVES_REGISTRY = objectives_registry
            writer.DRILL_REQUEST_REGISTRY = drill_registry
            writer.REGISTRY = generation_evidence_registry
            writer.NON_RESURRECTION_REGISTRY = overlay_registry
            writer.CANONICAL_NON_RESURRECTION_REGISTRY = overlay_registry

            require(writer.candidate(valid) is True, "fully bound typed evidence must produce isolated test candidate")
            print("PASS candidate: full typed validator accepts intact bundle")

            domain = contract["requiredDomains"][0]
            original_domain = load_json(domain_paths[domain])
            mutated_domain = copy.deepcopy(original_domain)
            mutated_domain["result"] = "FAIL"
            write_json(domain_paths[domain], mutated_domain)
            require(writer.candidate(valid) is False, "mutated domain payload must revoke candidate")
            print("PASS revoke: in-place domain evidence mutation invalidates candidate")
            write_json(domain_paths[domain], original_domain)
            require(writer.candidate(valid) is True, "restored domain payload must restore isolated candidate predicate")

            original_review = load_json(review_paths["SECURITY"])
            mutated_review = copy.deepcopy(original_review)
            mutated_review["reviewerPseudonym"] = "security_reviewer_mutated"
            write_json(review_paths["SECURITY"], mutated_review)
            require(writer.candidate(valid) is False, "mutated review payload must revoke candidate")
            print("PASS revoke: in-place security review mutation invalidates candidate")
            write_json(review_paths["SECURITY"], original_review)
            require(writer.candidate(valid) is True, "restored review payload must restore isolated candidate predicate")

        print("Memory OS generation candidate mutation negative suite PASS")
        print("canonical registries mutated: false")
        print("domain payload stale reuse accepted: false")
        print("review payload stale reuse accepted: false")
        print("production evidence: false")
        print("production decision: NO_GO")
        return 0
    finally:
        for path in cleanup:
            try:
                path.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION CANDIDATE MUTATION SUITE FAILED: {exc}")
        raise SystemExit(1)
