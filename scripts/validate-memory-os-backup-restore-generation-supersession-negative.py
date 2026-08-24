#!/usr/bin/env python3
"""Prove generation/objective supersession revokes current recovery authority.

This suite uses temporary registries and temporary descendant commits only. It never
moves a branch ref, creates production evidence, or weakens ancestor-only source
binding. The temporary commit is checked out detached solely so canonical lineage
validation sees synthetic successor generations as real ancestors of the test HEAD.
"""

from __future__ import annotations

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


def run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0, f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def drill_registry_value(request: dict, *, current_count: int = 1) -> dict:
    return {
        "schemaVersion": "memory-os-backup-restore-drill-request-registry.v1",
        "registryClass": "PRODUCTION_EQUIVALENT_BACKUP_RESTORE_DRILL_REQUESTS",
        "appendOnly": True,
        "registeredRequestCount": 1,
        "currentExecutableRequestCount": current_count,
        "requests": [request],
        "productionEvidence": False,
        "productionReady": False,
    }


def successor_environment_record(
    source_path: Path,
    generation_id: str,
    destination: Path,
    *,
    independent_review_ref: str,
) -> Path:
    value = json.loads(source_path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "successor environment fixture root must be object")
    value["generationId"] = generation_id
    boundary = value.get("evidenceBoundary")
    require(isinstance(boundary, dict), "successor environment fixture evidenceBoundary missing")
    require(isinstance(independent_review_ref, str) and independent_review_ref, "successor independent review ref required")
    boundary["independentReviewRef"] = independent_review_ref
    write_json(destination, value)
    return destination


def temporary_source_commit(base_commit: str, paths: list[Path]) -> str:
    relatives: list[str] = []
    for path in paths:
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError as exc:
            raise Fail("temporary source-bound environment fixture must remain inside repository") from exc
        require(path.is_file(), "temporary source-bound environment fixture missing")
        relatives.append(relative)

    with tempfile.TemporaryDirectory(prefix="memory-os-generation-source-index-") as index_tmp:
        env = dict(os.environ)
        env["GIT_INDEX_FILE"] = str(Path(index_tmp) / "index")
        env["GIT_AUTHOR_NAME"] = "memory-os-negative-suite"
        env["GIT_AUTHOR_EMAIL"] = "memory-os-negative-suite@example.invalid"
        env["GIT_COMMITTER_NAME"] = env["GIT_AUTHOR_NAME"]
        env["GIT_COMMITTER_EMAIL"] = env["GIT_AUTHOR_EMAIL"]

        def isolated_git(*args: str) -> str:
            completed = subprocess.run(
                ["git", *args], cwd=ROOT, env=env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            require(completed.returncode == 0, f"temporary source commit git {' '.join(args)} failed: {completed.stderr.strip()}")
            return completed.stdout.strip()

        isolated_git("read-tree", base_commit)
        isolated_git("add", "-f", "--", *relatives)
        tree = isolated_git("write-tree")
        commit = isolated_git(
            "commit-tree", tree, "-p", base_commit, "-m",
            "memory-os synthetic source-bound supersession fixture",
        )
        require(len(commit) == 40, "temporary source commit must be full SHA")
        return commit


def reject_current_registration(writer, record: dict, label: str) -> None:
    try:
        writer.validate_record(record)
    except Exception as exc:
        require(type(exc).__name__ == "Fail", f"unexpected exception escaped {label} rejection")
        return
    raise Fail(f"new evidence remained admissible after {label}")


def main() -> int:
    require(NEGATIVE.is_file() and WRITER.is_file(), "generation negative authorities missing")
    fixture = load_module(NEGATIVE, "memory_os_generation_negative_fixture_for_supersession")
    writer = load_module(WRITER, "memory_os_generation_writer_for_supersession")
    original_head = run_git("rev-parse", "HEAD")
    original_branch = run_git("branch", "--show-current")

    env_fixture_parent = fixture.SOURCE_ENV_FIXTURE.parent
    try:
        with tempfile.TemporaryDirectory(prefix="memory-os-generation-supersession-") as tmp, tempfile.TemporaryDirectory(
            prefix=".generation-supersession-", dir=env_fixture_parent
        ) as env_tmp:
            tmp_path = Path(tmp)
            env_tmp_path = Path(env_tmp)
            generation_registry = tmp_path / "generations.json"
            objectives_registry = tmp_path / "objectives.json"
            drill_registry = tmp_path / "drill-requests.json"
            overlay_registry = tmp_path / "typed-overlay.json"

            source_review = env_tmp_path / "source-independent-review.valid.md"
            target_review = env_tmp_path / "target-independent-review.valid.md"
            source_review.write_text("Synthetic source successor independent review fixture.\n", encoding="utf-8")
            target_review.write_text("Synthetic target successor independent review fixture.\n", encoding="utf-8")
            source_review_ref = source_review.relative_to(ROOT).as_posix()
            target_review_ref = target_review.relative_to(ROOT).as_posix()

            source_successor_env = successor_environment_record(
                fixture.SOURCE_ENV_FIXTURE,
                "pegen_source_v2",
                env_tmp_path / "source-environment-record.v2.valid.json",
                independent_review_ref=source_review_ref,
            )
            target_successor_env = successor_environment_record(
                fixture.TARGET_ENV_FIXTURE,
                "pegen_target_v2",
                env_tmp_path / "target-environment-record.v2.valid.json",
                independent_review_ref=target_review_ref,
            )
            successor_commit = temporary_source_commit(
                original_head,
                [source_successor_env, target_successor_env, source_review, target_review],
            )
            source_successor_env.unlink()
            target_successor_env.unlink()
            source_review.unlink()
            target_review.unlink()
            run_git("checkout", "--quiet", "--detach", successor_commit)

            source = fixture.generation_record(
                generation_id="pegen_source", environment_id="pe_source",
                environment_manifest_sha256=fixture.DIGEST_A,
                environment_record=fixture.SOURCE_ENV_FIXTURE, commit_sha=original_head,
            )
            target = fixture.generation_record(
                generation_id="pegen_target", environment_id="pe_target",
                environment_manifest_sha256=fixture.DIGEST_B,
                environment_record=fixture.TARGET_ENV_FIXTURE, commit_sha=original_head,
            )
            source_successor = fixture.generation_record(
                generation_id="pegen_source_v2", environment_id="pe_source",
                environment_manifest_sha256=fixture.DIGEST_A,
                environment_record=source_successor_env, commit_sha=successor_commit,
            )
            source_successor["supersedesGenerationId"] = "pegen_source"
            target_successor = fixture.generation_record(
                generation_id="pegen_target_v2", environment_id="pe_target",
                environment_manifest_sha256=fixture.DIGEST_B,
                environment_record=target_successor_env, commit_sha=successor_commit,
            )
            target_successor["supersedesGenerationId"] = "pegen_target"

            baseline_generations = {
                "schemaVersion": "memory-os-production-equivalent-environment-generation-registry.v1",
                "registryClass": "PRODUCTION_EQUIVALENT_ENVIRONMENT_GENERATIONS",
                "appendOnly": True,
                "registeredGenerationCount": 2,
                "currentGenerationId": "pegen_target",
                "productionEvidence": False,
                "generations": [source, target],
                "limitations": [],
            }
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
            request = fixture.base_drill_request()
            record = fixture.base_record(original_head)
            overlay = fixture.typed_overlay_record(record["evidenceId"], original_head)
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

            def restore_baseline() -> None:
                write_json(generation_registry, baseline_generations)
                write_json(objectives_registry, baseline_objectives)
                write_json(drill_registry, drill_registry_value(request))
                writer.validate_record(record)
                require(writer.candidate(record) is True, "baseline current candidate must be derivable")

            restore_baseline()

            source_superseded = dict(baseline_generations)
            source_superseded["generations"] = [source, target, source_successor]
            source_superseded["registeredGenerationCount"] = 3
            source_superseded["currentGenerationId"] = "pegen_source_v2"
            write_json(generation_registry, source_superseded)
            write_json(drill_registry, drill_registry_value(request, current_count=0))
            writer.validate_record(record, require_current_drill_request=False)
            require(writer.candidate(record) is False, "superseded source generation must revoke candidate")
            reject_current_registration(writer, record, "source generation supersession")
            print("PASS revoke: superseded source generation invalidates candidate and new evidence")

            restore_baseline()
            target_superseded = dict(baseline_generations)
            target_superseded["generations"] = [source, target, target_successor]
            target_superseded["registeredGenerationCount"] = 3
            target_superseded["currentGenerationId"] = "pegen_target_v2"
            write_json(generation_registry, target_superseded)
            write_json(drill_registry, drill_registry_value(request, current_count=0))
            writer.validate_record(record, require_current_drill_request=False)
            require(writer.candidate(record) is False, "superseded target generation must revoke candidate")
            reject_current_registration(writer, record, "restore-target generation supersession")
            print("PASS revoke: superseded restore-target generation invalidates candidate and new evidence")

            restore_baseline()
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
            write_json(drill_registry, drill_registry_value(request, current_count=0))
            writer.validate_record(record, require_current_drill_request=False)
            require(writer.candidate(record) is False, "recovery objective rollover must revoke candidate")
            reject_current_registration(writer, record, "recovery objective rollover")
            print("PASS revoke: recovery objective rollover invalidates candidate and new evidence")

        print("Memory OS generation/objective/request rollover candidate negative suite PASS")
        print("historical evidence remains auditable after valid supersession: true")
        print("synthetic successor sourceCommitSha ancestor validation exercised: true")
        print("eligible generation independent review reuse accepted: false")
        print("successor review evidence reused as implementation/restore evidence: false")
        print("branch or ref updated by synthetic source commits: false")
        print("production evidence: false")
        print("production decision: NO_GO")
        return 0
    finally:
        if original_branch:
            run_git("checkout", "--quiet", original_branch)
        else:
            run_git("checkout", "--quiet", "--detach", original_head)
        require(run_git("rev-parse", "HEAD") == original_head, "negative suite failed to restore original HEAD")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION SUPERSESSION NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
