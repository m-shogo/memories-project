#!/usr/bin/env python3
"""Prove typed non-resurrection registry row mutation revokes candidate coverage.

This harness never mutates canonical registries. It builds an isolated generation
recovery evidence registry plus one fully bound typed overlay, proves the typed
coverage predicate accepts the intact row, then mutates only the registry row
while leaving the referenced domain/review payloads untouched. Every mutation
must fail closed.
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
            generation_evidence_registry = tmp_path / "generation-evidence.json"
            overlay_registry = tmp_path / "typed-overlay.json"

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

            writer.REGISTRY = generation_evidence_registry
            writer.NON_RESURRECTION_REGISTRY = overlay_registry
            writer.CANONICAL_NON_RESURRECTION_REGISTRY = overlay_registry

            evidence_id = valid["evidenceId"]
            require(writer.typed_non_resurrection_covered(evidence_id) is True, "intact typed registry row must cover generation evidence")
            print("PASS candidate coverage: intact typed registry row accepted")

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
            require(writer.typed_non_resurrection_covered(evidence_id) is True, "restored intact row must restore isolated typed coverage predicate")

        print("Memory OS generation candidate registry-row mutation negative suite PASS")
        print("canonical registries mutated: false")
        print("repository-local canonical simulation: true")
        print("typed registry schema drift accepted: false")
        print("typed registry append-only boundary mutation accepted: false")
        print("typed registry productionEvidence mutation accepted: false")
        print("typed registry productionReady mutation accepted: false")
        print("typed registry records container mutation accepted: false")
        print("typed registry row stale mutation accepted: false")
        print("typed production boundary mutation accepted: false")
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
