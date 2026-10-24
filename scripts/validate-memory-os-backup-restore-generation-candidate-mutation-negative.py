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
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GEN_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py"
GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
NONRES_WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
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


OWNED_TRANSIENTS: dict[Path, tuple[int, int, int, int]] = {}


def canonical_parent_identity(parent: Path) -> tuple[int, int]:
    try:
        relative = parent.relative_to(ROOT)
    except ValueError as exc:
        raise Fail("candidate transient parent escapes repository") from exc
    require(ROOT.is_dir() and not ROOT.is_symlink(), "candidate transient root missing or symlinked")
    cursor = ROOT
    for part in relative.parts:
        cursor = cursor / part
        require(cursor.is_dir() and not cursor.is_symlink(),
                "candidate transient ancestor missing or symlinked")
    require(parent.resolve(strict=True) == ROOT.resolve(strict=True) / relative,
            "candidate transient parent canonical resolution drift")
    parent_stat = parent.stat()
    return parent_stat.st_dev, parent_stat.st_ino


def require_owned_transient(path: Path) -> None:
    require(path in OWNED_TRANSIENTS, "candidate transient file was not exclusively registered")
    parent_dev, parent_ino, leaf_dev, leaf_ino = OWNED_TRANSIENTS[path]
    require(canonical_parent_identity(path.parent) == (parent_dev, parent_ino),
            "candidate transient parent identity drift")
    leaf = path.lstat()
    require(stat.S_ISREG(leaf.st_mode) and (leaf.st_dev, leaf.st_ino) == (leaf_dev, leaf_ino),
            "candidate transient leaf identity drift")


def cleanup_owned_transients(cleanup: list[Path]) -> None:
    require(set(cleanup).issubset(OWNED_TRANSIENTS),
            "candidate transient cleanup contains an unowned file")
    for path in reversed(tuple(OWNED_TRANSIENTS)):
        parent_dev, parent_ino, leaf_dev, leaf_ino = OWNED_TRANSIENTS[path]
        require(canonical_parent_identity(path.parent) == (parent_dev, parent_ino),
                "candidate transient cleanup parent identity drift")
        try:
            leaf = path.lstat()
        except FileNotFoundError:
            continue
        require(stat.S_ISREG(leaf.st_mode) and (leaf.st_dev, leaf.st_ino) == (leaf_dev, leaf_ino),
                "candidate transient cleanup leaf identity drift")
        path.unlink()
    OWNED_TRANSIENTS.clear()


def write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if path in OWNED_TRANSIENTS:
        require_owned_transient(path)
        fd = os.open(path, os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            leaf = os.fstat(fd)
            require((leaf.st_dev, leaf.st_ino) == OWNED_TRANSIENTS[path][2:],
                    "candidate transient descriptor identity drift")
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                fd = -1
                output.truncate(0)
                output.write(payload)
        finally:
            if fd >= 0:
                os.close(fd)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


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
    try:
        parent_identity = canonical_parent_identity(path.parent)
        leaf = os.fstat(handle.fileno())
        require_owned = path.lstat()
        require(stat.S_ISREG(require_owned.st_mode)
                and (leaf.st_dev, leaf.st_ino) == (require_owned.st_dev, require_owned.st_ino),
                "candidate transient descriptor/leaf identity drift")
        OWNED_TRANSIENTS[path] = (*parent_identity, leaf.st_dev, leaf.st_ino)
    finally:
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
    require(TMP_PARENT.is_dir(), "candidate mutation repository-local temp parent missing")
    helpers = load_module(GEN_NEGATIVE, "memory_os_generation_negative_helpers")
    writer = load_module(GEN_WRITER, "memory_os_generation_writer_candidate_mutation")
    overlay_writer = load_module(NONRES_WRITER, "memory_os_nonres_writer_candidate_mutation")
    contract = load_json(NONRES_CONTRACT)
    commit_sha = helpers.head_sha()
    cleanup: list[Path] = []

    try:
        with tempfile.TemporaryDirectory(prefix=".tmp-memory-os-candidate-mutation-", dir=TMP_PARENT) as tmp:
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

            # Negative proof of the fixture ownership guard itself. Mutate only
            # the recorded identity, never an actual evidence path or symlink.
            owned_path = next(iter(domain_paths.values()))
            owned_identity = OWNED_TRANSIENTS[owned_path]
            original_bytes = owned_path.read_bytes()
            for label, offset, diagnostic in (
                ("parent", 1, "candidate transient parent identity drift"),
                ("leaf", 3, "candidate transient leaf identity drift"),
            ):
                wrong = list(owned_identity)
                wrong[offset] += 1
                OWNED_TRANSIENTS[owned_path] = tuple(wrong)
                try:
                    try:
                        write_json(owned_path, {"synthetic": "must not overwrite"})
                    except Fail as exc:
                        require(str(exc) == diagnostic,
                                f"owned fixture {label} drift rejected at wrong boundary: {exc}")
                    else:
                        raise Fail(f"owned fixture {label} identity drift accepted")
                finally:
                    OWNED_TRANSIENTS[owned_path] = owned_identity
                require(owned_path.read_bytes() == original_bytes,
                        f"owned fixture {label} drift modified existing bytes")
            try:
                cleanup_owned_transients([tmp_path / "unowned-negative.json"])
            except Fail as exc:
                require(str(exc) == "candidate transient cleanup contains an unowned file",
                        f"unowned fixture cleanup rejected at wrong boundary: {exc}")
            else:
                raise Fail("unowned fixture cleanup was accepted")
            require(writer.candidate(valid) is True,
                    "candidate did not survive identity guard negative probes")
            print("PASS: owned fixture parent/leaf substitution and unowned cleanup reject without mutation")


            original_drill_request_for_record = writer.drill_request_for_record
            try:
                def reject_drill_request(*args: Any, **kwargs: Any) -> None:
                    raise writer.Fail("synthetic domain rejection")

                writer.drill_request_for_record = reject_drill_request
                require(writer.drill_request_current(valid) is False, "explicit drill-request domain rejection must revoke candidate")
                print("PASS reject: explicit drill-request domain failure returns false")

                def break_drill_request(*args: Any, **kwargs: Any) -> None:
                    raise TypeError("synthetic unexpected drill-request implementation error")

                writer.drill_request_for_record = break_drill_request
                try:
                    writer.drill_request_current(valid)
                except TypeError:
                    pass
                else:
                    raise Fail("unexpected drill-request implementation exception was hidden as candidate rejection")
                print("PASS surface: unexpected drill-request implementation exception propagates")
            finally:
                writer.drill_request_for_record = original_drill_request_for_record

            original_overlay_loader = writer.load_non_resurrection_writer
            try:
                class RejectingOverlay:
                    @staticmethod
                    def validate_registry_for_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
                        raise writer.Fail("synthetic typed domain rejection")

                writer.load_non_resurrection_writer = lambda: RejectingOverlay()
                require(writer.typed_non_resurrection_covered(valid["evidenceId"]) is False, "explicit typed domain rejection must revoke coverage")
                print("PASS reject: explicit typed domain failure returns false")

                class BrokenOverlay:
                    @staticmethod
                    def validate_registry_for_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
                        raise TypeError("synthetic unexpected typed implementation error")

                writer.load_non_resurrection_writer = lambda: BrokenOverlay()
                try:
                    writer.typed_non_resurrection_covered(valid["evidenceId"])
                except TypeError:
                    pass
                else:
                    raise Fail("unexpected typed implementation exception was hidden as coverage rejection")
                print("PASS surface: unexpected typed implementation exception propagates")
            finally:
                writer.load_non_resurrection_writer = original_overlay_loader

            require(writer.candidate(valid) is True, "candidate must recover after exception-boundary probes")

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
        print("repository-local canonical simulation: true")
        print("domain payload stale reuse accepted: false")
        print("review payload stale reuse accepted: false")
        print("unexpected candidate implementation exceptions hidden: false")
        print("production evidence: false")
        print("production decision: NO_GO")
        return 0
    finally:
        cleanup_owned_transients(cleanup)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION CANDIDATE MUTATION SUITE FAILED: {exc}")
        raise SystemExit(1)
