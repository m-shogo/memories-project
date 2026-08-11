#!/usr/bin/env python3
"""Prove generation/objective/request rollover invalidates current recovery candidates.

This suite uses only temporary registries and existing synthetic fixtures. It
never mutates canonical evidence or creates production authority.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py"
WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def drill_registry_value(request: dict) -> dict:
    return {
        "schemaVersion": "memory-os-backup-restore-drill-request-registry.v1",
        "registryClass": "PRODUCTION_EQUIVALENT_BACKUP_RESTORE_DRILL_REQUESTS",
        "appendOnly": True,
        "registeredRequestCount": 1,
        "currentExecutableRequestCount": 1,
        "requests": [request],
        "productionEvidence": False,
        "productionReady": False,
    }


def reject_current_registration(writer, record: dict, label: str) -> None:
    try:
        writer.validate_record(record)
    except Exception as exc:
        require(type(exc).__name__ == "Fail", f"unexpected exception escaped {label} rejection")
    else:
        raise Fail(f"new evidence remained admissible after {label}")


def main() -> int:
    require(NEGATIVE.is_file() and WRITER.is_file(), "generation negative authorities missing")
    fixture = load_module(NEGATIVE, "memory_os_generation_negative_fixture_for_supersession")
    writer = load_module(WRITER, "memory_os_generation_writer_for_supersession")
    commit_sha = fixture.head_sha()

    with tempfile.TemporaryDirectory(prefix="memory-os-generation-supersession-") as tmp:
        tmp_path = Path(tmp)
        generation_registry = tmp_path / "generations.json"
        objectives_registry = tmp_path / "objectives.json"
        drill_registry = tmp_path / "drill-requests.json"
        overlay_registry = tmp_path / "typed-overlay.json"

        source = fixture.generation_record(
            generation_id="pegen_source",
            environment_id="pe_source",
            environment_manifest_sha256=fixture.DIGEST_A,
            environment_record=fixture.SOURCE_ENV_FIXTURE,
            commit_sha=commit_sha,
        )
        target = fixture.generation_record(
            generation_id="pegen_target",
            environment_id="pe_target",
            environment_manifest_sha256=fixture.DIGEST_B,
            environment_record=fixture.TARGET_ENV_FIXTURE,
            commit_sha=commit_sha,
        )
        baseline_generations = {
            "schemaVersion": "memory-os-production-equivalent-environment-generation-registry.v1",
            "appendOnly": True,
            "registeredGenerationCount": 2,
            "currentGenerationId": "pegen_target",
            "productionEvidence": False,
            "generations": [source, target],
        }
        write_json(generation_registry, baseline_generations)
        baseline_objectives = {
            "schemaVersion": "memory-os-recovery-objectives-registry.v1",
            "appendOnly": True,
            "approvedObjectiveCount": 1,
            "currentObjectiveId": "recovery_objectives_ci",
            "records": [{
                "objectiveId": "recovery_objectives_ci",
                "rpoSeconds": 60,
                "rtoSeconds": 120,
                "maximumObjectDatabaseSkewSeconds": 10,
                "approvedAt": "2026-08-07T23:55:00Z",
            }],
            "productionEvidence": False,
            "productionReady": False,
        }
        write_json(objectives_registry, baseline_objectives)
        request = fixture.base_drill_request()
        write_json(drill_registry, drill_registry_value(request))
        record = fixture.base_record(commit_sha)
        overlay = fixture.typed_overlay_record(record["evidenceId"], commit_sha)
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
        writer.NON_RESURRECTION_REGISTRY = overlay_registry

        writer.validate_record(record)
        require(writer.candidate(record) is True, "baseline current candidate must be derivable before authority rollover")

        source_successor = fixture.generation_record(
            generation_id="pegen_source_v2",
            environment_id="pe_source",
            environment_manifest_sha256=fixture.DIGEST_A,
            environment_record=fixture.SOURCE_ENV_FIXTURE,
            commit_sha=commit_sha,
        )
        source_successor["supersedesGenerationId"] = "pegen_source"
        source_superseded = dict(baseline_generations)
        source_superseded["generations"] = [source, target, source_successor]
        source_superseded["registeredGenerationCount"] = 3
        write_json(generation_registry, source_superseded)

        writer.validate_record(record, require_current_drill_request=False)
        require(writer.candidate(record) is False, "superseded source generation must invalidate current candidate")
        reject_current_registration(writer, record, "source generation supersession")
        print("PASS revoke: superseded source generation invalidates candidate and new evidence")

        write_json(generation_registry, baseline_generations)
        writer.validate_record(record)
        require(writer.candidate(record) is True, "baseline candidate must recover after isolated source supersession fixture reset")

        target_successor = fixture.generation_record(
            generation_id="pegen_target_v2",
            environment_id="pe_target",
            environment_manifest_sha256=fixture.DIGEST_B,
            environment_record=fixture.TARGET_ENV_FIXTURE,
            commit_sha=commit_sha,
        )
        target_successor["supersedesGenerationId"] = "pegen_target"
        target_superseded = dict(baseline_generations)
        target_superseded["generations"] = [source, target, target_successor]
        target_superseded["registeredGenerationCount"] = 3
        target_superseded["currentGenerationId"] = "pegen_target_v2"
        write_json(generation_registry, target_superseded)

        writer.validate_record(record, require_current_drill_request=False)
        require(writer.candidate(record) is False, "superseded restore-target generation must invalidate current candidate")
        reject_current_registration(writer, record, "restore-target generation supersession")
        print("PASS revoke: superseded restore-target generation invalidates candidate and new evidence")

        write_json(generation_registry, baseline_generations)
        write_json(objectives_registry, baseline_objectives)
        write_json(drill_registry, drill_registry_value(request))
        writer.validate_record(record)
        require(writer.candidate(record) is True, "baseline candidate must recover after isolated target supersession fixture reset")

        replaced_approval_request = copy.deepcopy(request)
        replaced_approval_request["approvalRefs"]["securityReview"] = request["approvalRefs"]["operabilityReview"]
        write_json(drill_registry, drill_registry_value(replaced_approval_request))

        require(writer.candidate(record) is False, "review approval path replacement must invalidate current candidate")
        reject_current_registration(writer, record, "review approval path replacement")
        print("PASS revoke: review approval path replacement invalidates candidate and new evidence")

        write_json(drill_registry, drill_registry_value(request))
        writer.validate_record(record)
        require(writer.candidate(record) is True, "baseline candidate must recover after isolated approval replacement fixture reset")

        rolled_objectives = dict(baseline_objectives)
        rolled_objectives["approvedObjectiveCount"] = 2
        rolled_objectives["currentObjectiveId"] = "recovery_objectives_ci_v2"
        rolled_objectives["records"] = [
            *baseline_objectives["records"],
            {
                "objectiveId": "recovery_objectives_ci_v2",
                "rpoSeconds": 45,
                "rtoSeconds": 90,
                "maximumObjectDatabaseSkewSeconds": 8,
                "approvedAt": "2026-08-08T00:10:00Z",
            },
        ]
        write_json(objectives_registry, rolled_objectives)

        writer.validate_record(record, require_current_drill_request=False)
        require(writer.candidate(record) is False, "recovery objective rollover must invalidate current candidate")
        reject_current_registration(writer, record, "recovery objective rollover")
        print("PASS revoke: recovery objective rollover invalidates stale request candidate and new evidence")

    print("Memory OS generation/objective/request rollover candidate negative suite PASS")
    print("historical evidence remains auditable after valid supersession: true")
    print("superseded source generation creates current candidate: false")
    print("superseded restore-target generation creates current candidate: false")
    print("replaced review approval path creates current candidate: false")
    print("stale recovery objective creates current candidate: false")
    print("new evidence accepted against stale generation/objective/request authority: false")
    print("canonical registries mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION SUPERSESSION NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
