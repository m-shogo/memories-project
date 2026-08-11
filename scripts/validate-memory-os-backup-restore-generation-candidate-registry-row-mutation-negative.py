#!/usr/bin/env python3
"""Prove typed non-resurrection registry row mutation revokes candidate coverage.

This harness never mutates canonical registries. It builds isolated, fully bound
source/target generation, objective, drill-request and generation-evidence
authorities plus one complete typed overlay. The intact authority must pass;
registry aggregate or row mutations must fail closed.
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
CANDIDATE_MUTATION = ROOT / "scripts/validate-memory-os-backup-restore-generation-candidate-mutation-negative.py"
NONRES_CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


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


def main() -> int:
    for path in (GEN_NEGATIVE, GEN_WRITER, NONRES_WRITER, CANDIDATE_MUTATION, NONRES_CONTRACT):
        require(path.is_file(), f"registry-row mutation foundation missing: {path}")
    require(TMP_PARENT.is_dir(), "registry-row mutation repository-local temp parent missing")

    helpers = load_module(GEN_NEGATIVE, "memory_os_generation_negative_helpers_row_mutation")
    writer = load_module(GEN_WRITER, "memory_os_generation_writer_row_mutation")
    overlay_writer = load_module(NONRES_WRITER, "memory_os_nonres_writer_row_mutation")
    candidate_helpers = load_module(CANDIDATE_MUTATION, "memory_os_candidate_mutation_helpers_row_mutation")
    contract = load_json(NONRES_CONTRACT)
    commit_sha = helpers.head_sha()
    cleanup: list[Path] = []

    try:
        with tempfile.TemporaryDirectory(prefix=".tmp-memory-os-candidate-row-mutation-", dir=TMP_PARENT) as tmp:
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
                "registryClass": "PRODUCTION_EQUIVALENT_BACKUP_RESTORE_EVIDENCE",
                "appendOnly": True,
                "registeredEvidenceCount": 1,
                "drillRequestBoundEvidenceCount": 1,
                "completeGenerationBoundBackupCount": 1,
                "completeGenerationBoundRestoreCount": 1,
                "productionEquivalentRecoveryCandidateCount": 1,
                "records": [valid],
                "productionEvidence": False,
                "productionReady": False,
                "limitations": [],
            })

            overlay, _, _ = candidate_helpers.build_typed_overlay(
                contract=contract,
                overlay_writer=overlay_writer,
                evidence_id=valid["evidenceId"],
                commit_sha=commit_sha,
                cleanup=cleanup,
            )
            intact_registry = {
                "schemaVersion": "memory-os-backup-restore-non-resurrection-admission-registry.v1",
                "appendOnly": True,
                "registeredRecordCount": 1,
                "completeRecordCount": 1,
                "candidateCoveredCount": 1,
                "records": [overlay],
                "productionEvidence": False,
                "productionReady": False,
            }
            write_json(overlay_registry, intact_registry)

            writer.GEN_REGISTRY = generation_registry
            writer.OBJECTIVES_REGISTRY = objectives_registry
            writer.DRILL_REQUEST_REGISTRY = drill_registry
            writer.REGISTRY = generation_evidence_registry
            writer.NON_RESURRECTION_REGISTRY = overlay_registry
            writer.CANONICAL_NON_RESURRECTION_REGISTRY = overlay_registry

            evidence_id = valid["evidenceId"]
            require(writer.base_candidate(valid) is True, "fully bound upstream authority must satisfy pre-overlay candidate gates")
            print("PASS candidate foundation: fully bound upstream authority satisfies pre-overlay gates")
            require(writer.candidate(valid) is True, "intact fully bound authority must satisfy the final candidate predicate")
            print("PASS candidate: intact fully bound authority accepted")
            require(writer.typed_non_resurrection_covered(evidence_id) is True, "intact typed registry row must cover generation evidence")
            print("PASS candidate coverage: intact fully bound typed registry accepted")

            registered_count_mutation = copy.deepcopy(intact_registry)
            registered_count_mutation["registeredRecordCount"] = 0
            write_json(overlay_registry, registered_count_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "typed registry registeredRecordCount drift must revoke coverage")
            print("PASS revoke: typed registry registeredRecordCount drift invalidates coverage")

            boolean_registered_count_mutation = copy.deepcopy(intact_registry)
            boolean_registered_count_mutation["registeredRecordCount"] = True
            write_json(overlay_registry, boolean_registered_count_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "typed registry boolean registeredRecordCount must revoke coverage")
            print("PASS revoke: typed registry boolean registeredRecordCount invalidates coverage")

            complete_count_mutation = copy.deepcopy(intact_registry)
            complete_count_mutation["completeRecordCount"] = 0
            write_json(overlay_registry, complete_count_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "typed registry completeRecordCount drift must revoke coverage")
            print("PASS revoke: typed registry completeRecordCount drift invalidates coverage")

            candidate_count_mutation = copy.deepcopy(intact_registry)
            candidate_count_mutation["candidateCoveredCount"] = 0
            write_json(overlay_registry, candidate_count_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "typed registry candidateCoveredCount drift must revoke coverage")
            print("PASS revoke: typed registry candidateCoveredCount drift invalidates coverage")

            schema_mutation = copy.deepcopy(intact_registry)
            schema_mutation["schemaVersion"] = "memory-os-backup-restore-non-resurrection-admission-registry.v0"
            write_json(overlay_registry, schema_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "typed registry schema drift must revoke coverage")
            print("PASS revoke: typed registry schema drift invalidates coverage")

            append_only_mutation = copy.deepcopy(intact_registry)
            append_only_mutation["appendOnly"] = False
            write_json(overlay_registry, append_only_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "typed registry append-only boundary drift must revoke coverage")
            print("PASS revoke: typed registry append-only boundary mutation invalidates coverage")

            registry_production_evidence_mutation = copy.deepcopy(intact_registry)
            registry_production_evidence_mutation["productionEvidence"] = True
            write_json(overlay_registry, registry_production_evidence_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "typed registry productionEvidence mutation must revoke coverage")
            print("PASS revoke: typed registry productionEvidence mutation invalidates coverage")

            registry_production_ready_mutation = copy.deepcopy(intact_registry)
            registry_production_ready_mutation["productionReady"] = True
            write_json(overlay_registry, registry_production_ready_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "typed registry productionReady mutation must revoke coverage")
            print("PASS revoke: typed registry productionReady mutation invalidates coverage")

            row_container_mutation = copy.deepcopy(intact_registry)
            row_container_mutation["records"] = {"unexpected": copy.deepcopy(overlay)}
            write_json(overlay_registry, row_container_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "typed registry records container drift must revoke coverage")
            print("PASS revoke: typed registry records container mutation invalidates coverage")

            digest_mutation = copy.deepcopy(intact_registry)
            digest_mutation["records"][0]["securityReviewSha256"] = "0" * 64
            write_json(overlay_registry, digest_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "mutated review digest in registry row must revoke coverage")
            print("PASS revoke: registry-row review digest mutation invalidates coverage")

            domain_mutation = copy.deepcopy(intact_registry)
            first_domain = contract["requiredDomains"][0]
            domain_mutation["records"][0]["domains"][first_domain]["result"] = "FAIL"
            write_json(overlay_registry, domain_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "mutated domain result in registry row must revoke coverage")
            print("PASS revoke: registry-row domain result mutation invalidates coverage")

            generation_mutation = copy.deepcopy(intact_registry)
            generation_mutation["records"][0]["generationEvidenceId"] = "brge_mutated_registry_row"
            write_json(overlay_registry, generation_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "mutated generation binding in registry row must revoke coverage")
            print("PASS revoke: registry-row generation binding mutation invalidates coverage")

            completion_mutation = copy.deepcopy(intact_registry)
            completion_mutation["records"][0]["evidenceComplete"] = False
            write_json(overlay_registry, completion_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "mutated completion bit in registry row must revoke coverage")
            print("PASS revoke: registry-row completion mutation invalidates coverage")

            production_boundary_mutation = copy.deepcopy(intact_registry)
            production_boundary_mutation["records"][0]["productionReady"] = True
            write_json(overlay_registry, production_boundary_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "mutated productionReady bit in typed row must revoke coverage")
            print("PASS revoke: registry-row production boundary mutation invalidates coverage")

            production_traffic_mutation = copy.deepcopy(intact_registry)
            production_traffic_mutation["records"][0]["productionTraffic"] = True
            write_json(overlay_registry, production_traffic_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "mutated productionTraffic bit in typed row must revoke coverage")
            print("PASS revoke: registry-row productionTraffic mutation invalidates coverage")

            production_credentials_mutation = copy.deepcopy(intact_registry)
            production_credentials_mutation["records"][0]["productionCredentials"] = True
            write_json(overlay_registry, production_credentials_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "mutated productionCredentials bit in typed row must revoke coverage")
            print("PASS revoke: registry-row productionCredentials mutation invalidates coverage")

            findings_mutation = copy.deepcopy(intact_registry)
            findings_mutation["records"][0]["unresolvedFindings"] = [{
                "findingId": "finding_candidate_row_mutation",
                "severity": "LOW",
                "status": "OPEN",
            }]
            write_json(overlay_registry, findings_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "new unresolved finding in typed row must revoke coverage")
            print("PASS revoke: registry-row unresolved finding mutation invalidates coverage")

            duplicate_binding = copy.deepcopy(intact_registry)
            duplicate_binding.update({
                "registeredRecordCount": 2,
                "completeRecordCount": 2,
                "candidateCoveredCount": 2,
                "records": [copy.deepcopy(overlay), copy.deepcopy(overlay)],
            })
            write_json(overlay_registry, duplicate_binding)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "duplicate typed coverage for one generation evidence id must revoke coverage")
            print("PASS revoke: duplicate typed generation binding invalidates coverage")

            review_independence_mutation = copy.deepcopy(intact_registry)
            review_independence_mutation["records"][0]["operabilityReviewRef"] = review_independence_mutation["records"][0]["securityReviewRef"]
            write_json(overlay_registry, review_independence_mutation)
            require(writer.typed_non_resurrection_covered(evidence_id) is False, "collapsed security/operability review refs must revoke coverage")
            print("PASS revoke: registry-row review independence mutation invalidates coverage")

            write_json(overlay_registry, intact_registry)
            require(writer.base_candidate(valid) is True, "restored intact authority must retain pre-overlay candidate eligibility")
            require(writer.candidate(valid) is True, "restored intact authority must restore final candidate predicate")
            require(writer.typed_non_resurrection_covered(evidence_id) is True, "restored intact row must restore isolated typed coverage predicate")

        print("Memory OS generation candidate registry-row mutation negative suite PASS")
        print("canonical registries mutated: false")
        print("repository-local canonical simulation: true")
        print("fully bound upstream candidate authority: true")
        print("typed registeredRecordCount drift accepted: false")
        print("typed boolean registeredRecordCount accepted: false")
        print("typed completeRecordCount drift accepted: false")
        print("typed candidateCoveredCount drift accepted: false")
        print("typed registry schema drift accepted: false")
        print("typed registry append-only boundary mutation accepted: false")
        print("typed registry productionEvidence mutation accepted: false")
        print("typed registry productionReady mutation accepted: false")
        print("typed registry records container mutation accepted: false")
        print("typed registry row stale mutation accepted: false")
        print("typed production boundary mutation accepted: false")
        print("typed productionTraffic mutation accepted: false")
        print("typed productionCredentials mutation accepted: false")
        print("typed unresolved finding mutation accepted: false")
        print("duplicate typed generation binding accepted: false")
        print("collapsed independent review refs accepted: false")
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
        print(f"BACKUP RESTORE GENERATION CANDIDATE REGISTRY ROW MUTATION SUITE FAILED: {exc}")
        raise SystemExit(1)
