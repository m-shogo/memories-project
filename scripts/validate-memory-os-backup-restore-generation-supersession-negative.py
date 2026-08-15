#!/usr/bin/env python3
"""Prove generation/objective/request rollover invalidates current recovery candidates.

This suite uses only temporary registries and existing synthetic fixtures. It
never mutates canonical evidence or creates production authority.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
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


def reject_candidate(writer, record: dict, label: str) -> None:
    """Accept only a false predicate or an explicit domain Fail as rejection."""
    try:
        eligible = writer.candidate(record)
    except Exception as exc:
        require(type(exc).__name__ == "Fail", f"unexpected exception escaped {label} candidate rejection")
        return
    require(eligible is False, f"{label} unexpectedly remained a current candidate")


def successor_environment_record(source_path: Path, generation_id: str, destination: Path) -> Path:
    value = json.loads(source_path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "successor environment fixture root must be object")
    value["generationId"] = generation_id
    write_json(destination, value)
    return destination


def temporary_source_commit(base_commit: str, path: Path) -> str:
    """Create an unreferenced local commit containing one synthetic environment record.

    This exercises real sourceCommitSha byte binding without moving any branch/ref or
    weakening the production writer. The object is intentionally unreachable after
    the test process exits.
    """
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise Fail("temporary source-bound environment fixture must remain inside repository") from exc
    require(path.is_file(), "temporary source-bound environment fixture missing")

    with tempfile.TemporaryDirectory(prefix="memory-os-generation-source-index-") as index_tmp:
        index_path = Path(index_tmp) / "index"
        env = dict(os.environ)
        env["GIT_INDEX_FILE"] = str(index_path)
        env["GIT_AUTHOR_NAME"] = "memory-os-negative-suite"
        env["GIT_AUTHOR_EMAIL"] = "memory-os-negative-suite@example.invalid"
        env["GIT_COMMITTER_NAME"] = env["GIT_AUTHOR_NAME"]
        env["GIT_COMMITTER_EMAIL"] = env["GIT_AUTHOR_EMAIL"]

        def run(*args: str) -> str:
            completed = subprocess.run(
                ["git", *args],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            require(completed.returncode == 0, f"temporary source commit git {' '.join(args)} failed: {completed.stderr.strip()}")
            return completed.stdout.strip()

        run("read-tree", base_commit)
        run("add", "-f", "--", relative)
        tree = run("write-tree")
        commit = run("commit-tree", tree, "-p", base_commit, "-m", "memory-os synthetic source-bound supersession fixture")
        require(len(commit) == 40, "temporary source commit must be full SHA")
        return commit


def main() -> int:
    require(NEGATIVE.is_file() and WRITER.is_file(), "generation negative authorities missing")
    fixture = load_module(NEGATIVE, "memory_os_generation_negative_fixture_for_supersession")
    writer = load_module(WRITER, "memory_os_generation_writer_for_supersession")
    commit_sha = fixture.head_sha()

    env_fixture_parent = fixture.SOURCE_ENV_FIXTURE.parent
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-supersession-") as tmp, tempfile.TemporaryDirectory(
        prefix=".generation-supersession-", dir=env_fixture_parent
    ) as env_tmp:
        tmp_path = Path(tmp)
        env_tmp_path = Path(env_tmp)
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
            "registryClass": "PRODUCTION_EQUIVALENT_ENVIRONMENT_GENERATIONS",
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

        source_successor_env = successor_environment_record(
            fixture.SOURCE_ENV_FIXTURE,
            "pegen_source_v2",
            env_tmp_path / "source-environment-record.v2.valid.json",
        )
        source_successor_commit = temporary_source_commit(commit_sha, source_successor_env)
        source_successor = fixture.generation_record(
            generation_id="pegen_source_v2",
            environment_id="pe_source",
            environment_manifest_sha256=fixture.DIGEST_A,
            environment_record=source_successor_env,
            commit_sha=source_successor_commit,
        )
        source_successor["supersedesGenerationId"] = "pegen_source"
        source_superseded = dict(baseline_generations)
        source_superseded["generations"] = [source, target, source_successor]
        source_superseded["registeredGenerationCount"] = 3
        source_superseded["currentGenerationId"] = "pegen_source_v2"
        write_json(generation_registry, source_superseded)
        source_superseded_drill = drill_registry_value(request)
        source_superseded_drill["currentExecutableRequestCount"] = 0
        write_json(drill_registry, source_superseded_drill)

        writer.validate_record(record, require_current_drill_request=False)
        require(writer.candidate(record) is False, "superseded source generation must invalidate current candidate")
        reject_current_registration(writer, record, "source generation supersession")
        print("PASS revoke: superseded source generation invalidates candidate and new evidence")

        write_json(generation_registry, baseline_generations)
        write_json(drill_registry, drill_registry_value(request))
        writer.validate_record(record)
        require(writer.candidate(record) is True, "baseline candidate must recover after isolated source supersession fixture reset")

        target_successor_env = successor_environment_record(
            fixture.TARGET_ENV_FIXTURE,
            "pegen_target_v2",
            env_tmp_path / "target-environment-record.v2.valid.json",
        )
        target_successor_commit = temporary_source_commit(commit_sha, target_successor_env)
        target_successor = fixture.generation_record(
            generation_id="pegen_target_v2",
            environment_id="pe_target",
            environment_manifest_sha256=fixture.DIGEST_B,
            environment_record=target_successor_env,
            commit_sha=target_successor_commit,
        )
        target_successor["supersedesGenerationId"] = "pegen_target"
        target_superseded = dict(baseline_generations)
        target_superseded["generations"] = [source, target, target_successor]
        target_superseded["registeredGenerationCount"] = 3
        target_superseded["currentGenerationId"] = "pegen_target_v2"
        write_json(generation_registry, target_superseded)
        target_superseded_drill = drill_registry_value(request)
        target_superseded_drill["currentExecutableRequestCount"] = 0
        write_json(drill_registry, target_superseded_drill)

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

        mutated_request = copy.deepcopy(request)
        mutated_request["productionTraffic"] = True
        write_json(drill_registry, drill_registry_value(mutated_request))

        require(writer.candidate(record) is False, "in-place drill request mutation must invalidate current candidate")
        reject_current_registration(writer, record, "in-place drill request mutation")
        print("PASS revoke: in-place drill request mutation invalidates candidate and new evidence")

        write_json(drill_registry, drill_registry_value(request))
        writer.validate_record(record)
        require(writer.candidate(record) is True, "baseline candidate must recover after isolated request mutation fixture reset")

        duplicate_request_registry = drill_registry_value(request)
        duplicate_request_registry["registeredRequestCount"] = 2
        duplicate_request_registry["currentExecutableRequestCount"] = 2
        duplicate_request_registry["requests"] = [request, copy.deepcopy(request)]
        write_json(drill_registry, duplicate_request_registry)

        require(writer.candidate(record) is False, "duplicate drill request identity must invalidate current candidate")
        reject_current_registration(writer, record, "duplicate drill request identity")
        print("PASS revoke: duplicate drill request identity invalidates candidate and new evidence")

        write_json(drill_registry, drill_registry_value(request))
        writer.validate_record(record)
        require(writer.candidate(record) is True, "baseline candidate must recover after isolated duplicate request fixture reset")

        drifted_boundary_registry = drill_registry_value(request)
        drifted_boundary_registry["productionReady"] = True
        write_json(drill_registry, drifted_boundary_registry)

        require(writer.candidate(record) is False, "drill registry production boundary drift must invalidate current candidate")
        reject_current_registration(writer, record, "drill registry production boundary drift")
        print("PASS revoke: drill registry production boundary drift invalidates candidate and new evidence")

        write_json(drill_registry, drill_registry_value(request))
        writer.validate_record(record)
        require(writer.candidate(record) is True, "baseline candidate must recover after isolated registry boundary fixture reset")

        registered_count_drift = drill_registry_value(request)
        registered_count_drift["registeredRequestCount"] = 2
        write_json(drill_registry, registered_count_drift)
        reject_candidate(writer, record, "registered request aggregate drift")
        reject_current_registration(writer, record, "registered request aggregate drift")
        print("PASS revoke: registeredRequestCount drift invalidates candidate and new evidence")

        boolean_registered_count = drill_registry_value(request)
        boolean_registered_count["registeredRequestCount"] = True
        write_json(drill_registry, boolean_registered_count)
        reject_candidate(writer, record, "boolean registered request aggregate")
        reject_current_registration(writer, record, "boolean registered request aggregate")
        print("PASS revoke: boolean registeredRequestCount invalidates candidate and new evidence")

        current_count_drift = drill_registry_value(request)
        current_count_drift["currentExecutableRequestCount"] = 0
        write_json(drill_registry, current_count_drift)
        reject_candidate(writer, record, "current executable request aggregate drift")
        reject_current_registration(writer, record, "current executable request aggregate drift")
        print("PASS revoke: currentExecutableRequestCount drift invalidates candidate and new evidence")

        boolean_current_count = drill_registry_value(request)
        boolean_current_count["currentExecutableRequestCount"] = True
        write_json(drill_registry, boolean_current_count)
        reject_candidate(writer, record, "boolean current executable request aggregate")
        reject_current_registration(writer, record, "boolean current executable request aggregate")
        print("PASS revoke: boolean currentExecutableRequestCount invalidates candidate and new evidence")

        write_json(drill_registry, drill_registry_value(request))
        writer.validate_record(record)
        require(writer.candidate(record) is True, "baseline candidate must recover after isolated request counter drift fixtures reset")

        duplicate_objectives = copy.deepcopy(baseline_objectives)
        duplicate_objectives["approvedObjectiveCount"] = 2
        duplicate_objectives["records"] = [
            baseline_objectives["records"][0],
            copy.deepcopy(baseline_objectives["records"][0]),
        ]
        write_json(objectives_registry, duplicate_objectives)

        reject_candidate(writer, record, "duplicate recovery objective identity")
        reject_current_registration(writer, record, "duplicate recovery objective identity")
        print("PASS revoke: duplicate recovery objective identity invalidates candidate and new evidence")

        write_json(objectives_registry, baseline_objectives)
        writer.validate_record(record)
        require(writer.candidate(record) is True, "baseline candidate must recover after isolated duplicate objective fixture reset")

        missing_current_objective = copy.deepcopy(baseline_objectives)
        missing_current_objective["currentObjectiveId"] = None
        write_json(objectives_registry, missing_current_objective)

        reject_candidate(writer, record, "missing current recovery objective authority")
        reject_current_registration(writer, record, "missing current recovery objective authority")
        print("PASS revoke: missing current recovery objective authority invalidates candidate and new evidence")

        write_json(objectives_registry, baseline_objectives)
        writer.validate_record(record)
        require(writer.candidate(record) is True, "baseline candidate must recover after isolated current objective fixture reset")

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
        rolled_objective_drill = drill_registry_value(request)
        rolled_objective_drill["currentExecutableRequestCount"] = 0
        write_json(drill_registry, rolled_objective_drill)

        writer.validate_record(record, require_current_drill_request=False)
        require(writer.candidate(record) is False, "recovery objective rollover must invalidate current candidate")
        reject_current_registration(writer, record, "recovery objective rollover")
        print("PASS revoke: recovery objective rollover invalidates stale request candidate and new evidence")

    print("Memory OS generation/objective/request rollover candidate negative suite PASS")
    print("historical evidence remains auditable after valid supersession: true")
    print("synthetic successor environment records source-bound via unreferenced commits: true")
    print("branch or ref updated by synthetic source commits: false")
    print("superseded source generation creates current candidate: false")
    print("superseded restore-target generation creates current candidate: false")
    print("replaced review approval path creates current candidate: false")
    print("mutated drill request row creates current candidate: false")
    print("duplicate drill request identity creates current candidate: false")
    print("drill registry production boundary drift creates current candidate: false")
    print("drill registry registered count drift creates current candidate: false")
    print("drill registry current executable count drift creates current candidate: false")
    print("boolean drill registry aggregate counts accepted: false")
    print("duplicate recovery objective identity creates current candidate: false")
    print("missing current recovery objective creates current candidate: false")
    print("stale recovery objective creates current candidate: false")
    print("new evidence accepted against stale generation/objective/request authority: false")
    print("unexpected candidate exceptions accepted as rejection: false")
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
