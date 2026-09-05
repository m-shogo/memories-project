#!/usr/bin/env python3
"""Fail-closed corruption negatives for the append-only release baseline registry."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/release-baseline-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-release-baseline.py"
LOCK = ROOT / "contracts/operations/.release-baseline-registry.lock"
RECONCILER = ROOT / "scripts/reconcile-memory-os-release-baseline-registry.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def temp_residue() -> list[Path]:
    return sorted(REGISTRY.parent.glob(".release-baseline-registry.*.tmp"))


def load_writer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_release_baseline_writer_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load release baseline writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "CONTRACT_PATH", None) == CONTRACT,
            "release writer contract authority drift")
    require(getattr(module, "REGISTRY_PATH", None) == REGISTRY,
            "release writer registry authority drift")
    require(getattr(module, "LOCK_PATH", None) == LOCK,
            "release writer append lock authority drift")
    require(callable(getattr(module, "append_registry_transactionally", None)),
            "release writer transactional append authority missing")
    return module


def load_reconciler() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_release_baseline_reconciler_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load release baseline reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "CONTRACT_PATH", None) == CONTRACT,
            "release reconciler contract authority drift")
    require(getattr(module, "REGISTRY_PATH", None) == REGISTRY,
            "release reconciler registry authority drift")
    require(getattr(module, "STATUS_PATH", None) == STATUS,
            "release reconciler status authority drift")
    return module


def validate_lock_binding(writer: ModuleType, contract: dict[str, Any]) -> None:
    require(contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)),
            "release contract append lock binding drift")
    require(getattr(writer, "LOCK_PATH", None) == LOCK,
            "release writer append lock binding drift")


def expect_lock_binding_rejected(writer: ModuleType, contract: dict[str, Any]) -> None:
    corrupt = copy.deepcopy(contract)
    corrupt["appendLockPath"] = "contracts/operations/.release-baseline-registry-alternate.lock"
    try:
        validate_lock_binding(writer, corrupt)
    except Fail:
        return
    raise Fail("release lock authority accepted substituted contract path")


def expect_writer_rejected(
    writer: ModuleType,
    contract: dict[str, Any],
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    corrupt = copy.deepcopy(load(REGISTRY))
    mutate(corrupt)
    try:
        writer.validate_registry_for_append(corrupt, contract)
    except Exception:
        return
    raise Fail(f"release writer accepted corrupt registry: {name}")


def expect_contract_rejected(
    writer: ModuleType,
    contract: dict[str, Any],
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    corrupt = copy.deepcopy(contract)
    mutate(corrupt)
    try:
        writer.validate_registry_for_append(copy.deepcopy(load(REGISTRY)), corrupt)
    except Exception:
        return
    raise Fail(f"release writer accepted corrupt contract: {name}")


def expect_append_rollback(writer: ModuleType, contract: dict[str, Any]) -> None:
    original = REGISTRY.read_bytes()
    original_mode = mode(REGISTRY)
    candidate = copy.deepcopy(load(REGISTRY))
    candidate["approvedReleaseCount"] = candidate.get("approvedReleaseCount", 0) + 1
    original_validator = writer.validate_registry_for_append

    try:
        os.chmod(REGISTRY, 0o640)
        test_mode = mode(REGISTRY)

        def fail_after_write(registry: dict[str, Any], candidate_contract: dict[str, Any]) -> None:
            raise writer.RegistrationFailure("synthetic post-append release validation failure")

        writer.validate_registry_for_append = fail_after_write
        try:
            writer.append_registry_transactionally(candidate, contract, original, test_mode)
        except writer.RegistrationFailure:
            pass
        else:
            raise Fail("release writer accepted synthetic post-append validation failure")
        require(REGISTRY.read_bytes() == original,
                "release registry did not roll back byte-for-byte after post-append failure")
        require(mode(REGISTRY) == test_mode,
                "release registry did not preserve mode after post-append rollback")
        require(not temp_residue(),
                "release registry rollback left temporary residue")
    finally:
        writer.validate_registry_for_append = original_validator
        REGISTRY.write_bytes(original)
        os.chmod(REGISTRY, original_mode)


def expect_replace_rejected_without_mutation(writer: ModuleType, contract: dict[str, Any]) -> None:
    original = REGISTRY.read_bytes()
    original_mode = mode(REGISTRY)
    candidate = copy.deepcopy(load(REGISTRY))
    candidate["approvedReleaseCount"] = candidate.get("approvedReleaseCount", 0) + 1
    original_replace = writer.os.replace

    try:
        os.chmod(REGISTRY, 0o640)
        test_mode = mode(REGISTRY)

        def reject_replace(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
            raise OSError("synthetic release registry replace rejection")

        writer.os.replace = reject_replace
        try:
            writer.append_registry_transactionally(candidate, contract, original, test_mode)
        except OSError as exc:
            require("synthetic release registry replace rejection" in str(exc),
                    "unexpected release replace rejection reason")
        else:
            raise Fail("release writer ignored replace rejection")
        require(REGISTRY.read_bytes() == original,
                "release replace rejection mutated canonical bytes")
        require(mode(REGISTRY) == test_mode,
                "release replace rejection mutated canonical mode")
        require(not temp_residue(),
                "release replace rejection left temporary residue")
    finally:
        writer.os.replace = original_replace
        REGISTRY.write_bytes(original)
        os.chmod(REGISTRY, original_mode)


def expect_reconcile_rejected_without_mutation(
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    registry_before = REGISTRY.read_bytes()
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    corrupt = load(REGISTRY)
    mutate(corrupt)
    REGISTRY.write_text(json.dumps(corrupt, indent=2) + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(RECONCILER)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        require(completed.returncode != 0, f"release reconciler auto-healed corrupt registry: {name}")
        require(CONTRACT.read_bytes() == contract_before,
                f"release reconciler mutated contract after rejecting: {name}")
        require(STATUS.read_bytes() == status_before,
                f"release reconciler mutated status after rejecting: {name}")
    finally:
        REGISTRY.write_bytes(registry_before)
        CONTRACT.write_bytes(contract_before)
        STATUS.write_bytes(status_before)


def validate_reconcile_validator_chain(reconciler: ModuleType) -> None:
    expected = [
        reconciler.VALIDATOR_PATH,
        reconciler.EVIDENCE_BINDING_VALIDATOR_PATH,
        reconciler.VERSION_VALIDATOR_PATH,
        reconciler.OPERABILITY_VALIDATOR_PATH,
    ]
    observed: list[Path] = []
    original_run = reconciler.subprocess.run

    def fake_run(command: list[str], *, cwd: Path, check: bool) -> None:
        require(cwd == ROOT, "release aggregate validator cwd drift")
        require(check is True, "release aggregate validators must fail closed")
        require(len(command) == 2 and command[0] == sys.executable,
                "release aggregate validator command drift")
        observed.append(Path(command[1]))

    reconciler.subprocess.run = fake_run
    try:
        reconciler.run_canonical_validators()
    finally:
        reconciler.subprocess.run = original_run

    require(observed == expected,
            "release reconcile does not enforce registry/evidence/version/operability validators in order")


def validate_record_shape_authority(writer: ModuleType, contract: dict[str, Any]) -> None:
    required_fields = writer.validate_contract_for_append(copy.deepcopy(contract))
    record = {
        "schemaVersion": "memory-os-release-baseline-record.v1",
        "releaseId": "rel_20991231_shape",
        "releaseTag": "v9999.1.0",
        "commitSha": "1" * 40,
        "approvedAt": "2099-12-31T00:00:00Z",
        "approvalClass": "PRODUCTION_RELEASE_BASELINE",
        "approvers": [
            {"role": "SECURITY_REVIEWER", "approverRef": "apr_security_ci11"},
            {"role": "OPERABILITY_REVIEWER", "approverRef": "apr_operability_ci22"},
            {"role": "RELEASE_OWNER", "approverRef": "apr_release_ci33"},
        ],
        "apiContractSha256": "0" * 64,
        "migrationSequenceSha256": "1" * 64,
        "parserArtifactSetSha256": "2" * 64,
        "runtimeConfigurationSchemaSha256": "3" * 64,
        "compatibilityEvidenceRefs": ["README.md"],
        "restoreEvidenceRefs": ["SECURITY.md"],
        "securityEvidenceRefs": ["README.md"],
        "rollbackEligibility": {"status": "ELIGIBLE", "verified": True, "conditions": []},
        "openRisks": [],
        "evidenceComplete": True,
        "productionReady": True,
    }
    original_lineage = writer.validate_release_commit_lineage
    original_evidence = writer.validate_evidence_ref_binding
    writer.validate_release_commit_lineage = lambda commit_sha: None
    writer.validate_evidence_ref_binding = lambda commit_sha, ref: None
    try:
        writer.validate_record(copy.deepcopy(record), required_fields)
        mutations: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
            ("unknown record field", lambda value: value.__setitem__("automaticPromotion", True)),
            ("approver field drift", lambda value: value["approvers"][0].__setitem__("decision", "APPROVED")),
            ("rollback field drift", lambda value: value["rollbackEligibility"].__setitem__("automaticRollback", True)),
            (
                "risk field drift",
                lambda value: value.__setitem__(
                    "openRisks",
                    [{"riskId": "risk_ci", "ownerRef": "apr_release_ci33", "deadline": "2099-12-31", "status": "OPEN", "approved": True}],
                ),
            ),
        ]
        for name, mutate in mutations:
            candidate = copy.deepcopy(record)
            mutate(candidate)
            try:
                writer.validate_record(candidate, required_fields)
            except Exception:
                continue
            raise Fail(f"release writer accepted record shape drift: {name}")
    finally:
        writer.validate_release_commit_lineage = original_lineage
        writer.validate_evidence_ref_binding = original_evidence


def validate_nonempty_progression(reconciler: ModuleType) -> None:
    contract = copy.deepcopy(load(CONTRACT))
    changed = reconciler.reconcile_contract_readiness(contract, 2, True)
    require(changed, "approved release inventory did not update contract readiness")
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "release readiness missing after progression")
    require(readiness.get("approvedReleaseCount") == 2,
            "approved release count did not progress")
    require(readiness.get("approvedPredecessorAvailable") is True,
            "approved predecessor did not progress")
    require(readiness.get("rollbackEligibleReleaseAvailable") is True,
            "rollback-eligible release did not progress")
    require(readiness.get("independentReviewCompleted") is False and
            readiness.get("productionReady") is False,
            "release inventory progression promoted production readiness")

    status = copy.deepcopy(load(STATUS))
    gate = next(
        (item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"),
        None,
    )
    require(isinstance(gate, dict), "OPS-P0-008 missing for release progression probe")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(missing, list),
            "OPS-P0-008 release progression lists missing")
    if reconciler.EMPTY_REGISTRY_EVIDENCE not in existing:
        existing.append(reconciler.EMPTY_REGISTRY_EVIDENCE)
    for gap in (reconciler.PREDECESSOR_GAP, reconciler.ROLLBACK_GAP):
        if gap not in missing:
            missing.append(gap)
    reconciler.reconcile_status(status, 2, True)
    require(reconciler.EMPTY_REGISTRY_EVIDENCE not in existing,
            "empty release evidence survived approved release inventory")
    require(reconciler.PREDECESSOR_GAP not in missing,
            "approved predecessor gap survived approved release inventory")
    require(reconciler.ROLLBACK_GAP not in missing,
            "rollback-eligible gap survived verified rollback authority")
    require(reconciler.INDEPENDENT_REVIEW_GAP in missing,
            "independent release review blocker disappeared")
    require(status.get("productionDecision") == "NO_GO",
            "release inventory progression changed production decision")


def validate_reconcile_rollback(reconciler: ModuleType) -> None:
    contract_original = CONTRACT.read_bytes()
    status_original = STATUS.read_bytes()
    contract = copy.deepcopy(load(CONTRACT))
    status = copy.deepcopy(load(STATUS))
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "release readiness missing for rollback probe")
    readiness["note"] = "synthetic release baseline rollback probe"
    gate = next(
        (item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"),
        None,
    )
    require(isinstance(gate, dict), "OPS-P0-008 missing for release rollback probe")
    evidence = gate.get("existingEvidence")
    require(isinstance(evidence, list), "OPS-P0-008 existingEvidence missing for release rollback probe")
    evidence.append("synthetic release baseline rollback probe")

    def fail_post_write() -> None:
        raise RuntimeError("synthetic release aggregate validator failure")

    try:
        reconciler.commit_authority_transaction(contract, status, validator_runner=fail_post_write)
    except RuntimeError as exc:
        require("synthetic release aggregate validator failure" in str(exc),
                "unexpected release rollback failure reason")
    else:
        raise Fail("release reconcile accepted synthetic post-write aggregate failure")

    require(CONTRACT.read_bytes() == contract_original,
            "release reconcile left partial contract after post-write aggregate failure")
    require(STATUS.read_bytes() == status_original,
            "release reconcile left partial status after post-write aggregate failure")


def main() -> int:
    writer = load_writer()
    reconciler = load_reconciler()
    contract = load(CONTRACT)
    validate_lock_binding(writer, contract)
    expect_lock_binding_rejected(writer, contract)
    expect_append_rollback(writer, contract)
    expect_replace_rejected_without_mutation(writer, contract)
    validate_reconcile_validator_chain(reconciler)
    validate_record_shape_authority(writer, contract)
    validate_nonempty_progression(reconciler)
    validate_reconcile_rollback(reconciler)

    contract_cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("append lock path drift", lambda value: value.__setitem__("appendLockPath", "contracts/operations/.alternate-release.lock")),
        ("append rollback guard disabled", lambda value: value.__setitem__("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure", False)),
        ("required fields drift", lambda value: value.__setitem__("requiredFields", value["requiredFields"][:-1])),
        ("boolean minimum approvers", lambda value: value["approvalPolicy"].__setitem__("minimumDistinctApprovers", True)),
        ("approval role drift", lambda value: value["approvalPolicy"].__setitem__("requiredRoles", ["RELEASE_OWNER"])),
        ("evidence binding drift", lambda value: value["evidenceBinding"].__setitem__("currentBytesMustMatchSourceCommit", False)),
        ("production decision promotion", lambda value: value.__setitem__("productionDecision", "GO")),
    ]
    for name, mutate in contract_cases:
        expect_contract_rejected(writer, contract, name, mutate)

    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("schema drift", lambda value: value.__setitem__("schemaVersion", "invalid")),
        ("registry class drift", lambda value: value.__setitem__("registryClass", "CANDIDATE_RELEASES")),
        ("appendOnly false", lambda value: value.__setitem__("appendOnly", False)),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
        ("boolean approved count", lambda value: value.__setitem__("approvedReleaseCount", True)),
        ("approved count drift", lambda value: value.__setitem__("approvedReleaseCount", len(value.get("releases", [])) + 1)),
        ("latest approved pointer drift", lambda value: value.__setitem__("latestApprovedReleaseId", "rel_20991231_invalid")),
        ("latest rollback pointer drift", lambda value: value.__setitem__("latestRollbackEligibleReleaseId", "rel_20991231_invalid")),
        ("unknown registry field", lambda value: value.__setitem__("unexpectedAuthority", True)),
    ]
    for name, mutate in cases:
        expect_writer_rejected(writer, contract, name, mutate)
        expect_reconcile_rejected_without_mutation(name, mutate)
    print("PASS: release baseline contract/record/registry corruption, mode-safe transactional append rollback/replace rejection, approved-inventory progression and aggregate rollback are fail-closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE BASELINE REGISTRY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
