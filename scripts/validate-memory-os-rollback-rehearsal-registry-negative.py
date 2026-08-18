#!/usr/bin/env python3
"""Negative coverage for rollback rehearsal append-only registry authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/request-memory-os-rollback-rehearsal.py"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-rollback-rehearsal-gate.py"
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rollback-rehearsal-gate.py"
CONTRACT_PATH = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object: {path.relative_to(ROOT)}")
    return value


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(label: str, action: Callable[[], None]) -> None:
    try:
        action()
    except Exception:
        return
    raise RuntimeError(f"corruption was accepted: {label}")


def reconcile_rejects_without_authority_write(
    registry: dict[str, Any], registry_bytes: bytes, contract_bytes: bytes,
    status_bytes: bytes, label: str
) -> None:
    try:
        REGISTRY_PATH.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        completed = subprocess.run(
            [sys.executable, str(RECONCILER_PATH)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode == 0:
            raise RuntimeError(f"reconciler accepted corrupt registry: {label}")
        if CONTRACT_PATH.read_bytes() != contract_bytes:
            raise RuntimeError(f"reconciler mutated rollback contract on rejection: {label}")
        if STATUS_PATH.read_bytes() != status_bytes:
            raise RuntimeError(f"reconciler mutated production status on rejection: {label}")
    finally:
        REGISTRY_PATH.write_bytes(registry_bytes)
        CONTRACT_PATH.write_bytes(contract_bytes)
        STATUS_PATH.write_bytes(status_bytes)


def validator_rejects_lock_drift(contract: dict[str, Any], contract_bytes: bytes) -> None:
    candidate = copy.deepcopy(contract)
    candidate["appendLockPath"] = "contracts/operations/.rollback-rehearsal-registry.alternate.lock"
    try:
        CONTRACT_PATH.write_text(
            json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode == 0:
            raise RuntimeError("standalone validator accepted alternate append lock authority")
    finally:
        CONTRACT_PATH.write_bytes(contract_bytes)


def validate_contract_append_authority(
    writer: Any, contract: dict[str, Any], registry: dict[str, Any],
    release_registry: dict[str, Any]
) -> None:
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("contract appendOnly", lambda value: value.__setitem__("appendOnly", False)),
        (
            "contract writer path",
            lambda value: value.__setitem__("writer", "scripts/validate-memory-os-rollback-rehearsal-gate.py"),
        ),
        (
            "contract required fields",
            lambda value: value.__setitem__(
                "requiredRequestFields",
                [item for item in value["requiredRequestFields"] if item != "openRisks"],
            ),
        ),
        (
            "contract digest guard",
            lambda value: value.__setitem__(
                "admissionGuards",
                [item for item in value["admissionGuards"] if item != writer.EVIDENCE_DIGEST_GUARD],
            ),
        ),
        (
            "contract production evidence boundary",
            lambda value: value["evidenceBoundary"].__setitem__("productionEvidence", True),
        ),
        (
            "contract production traffic boundary",
            lambda value: value["environmentPolicy"].__setitem__("productionTrafficAllowed", True),
        ),
    ]
    for label, mutate in cases:
        candidate = copy.deepcopy(contract)
        mutate(candidate)
        expect_rejected(
            label,
            lambda candidate=candidate: writer.validate_registry_for_append(
                copy.deepcopy(registry), candidate, copy.deepcopy(release_registry)
            ),
        )


def validate_evidence_ref_containment(writer: Any) -> None:
    fixture_root = ROOT / "docs/fixtures/memory-os-operability"
    leaf_link = fixture_root / ".rollback-rehearsal-ref-link"
    parent_link = fixture_root / ".rollback-rehearsal-ref-parent"
    untracked = fixture_root / ".rollback-rehearsal-ref-untracked.json"
    for path in (leaf_link, parent_link, untracked):
        try:
            if path.is_symlink() or path.is_file():
                path.unlink()
        except FileNotFoundError:
            pass
    try:
        leaf_link.symlink_to(ROOT / "README.md")
        expect_rejected(
            "leaf symlink evidence ref",
            lambda: writer.safe_ref(str(leaf_link.relative_to(ROOT)), "negative.leaf"),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            outside = Path(temp_dir) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            parent_link.symlink_to(Path(temp_dir), target_is_directory=True)
            expect_rejected(
                "parent symlink evidence ref",
                lambda: writer.safe_ref(
                    str((parent_link / outside.name).relative_to(ROOT)), "negative.parent"
                ),
            )
            parent_link.unlink()
        untracked.write_text("{}\n", encoding="utf-8")
        expect_rejected(
            "untracked evidence ref",
            lambda: writer.safe_ref(str(untracked.relative_to(ROOT)), "negative.untracked"),
        )
    finally:
        for path in (leaf_link, parent_link, untracked):
            try:
                if path.is_symlink() or path.is_file():
                    path.unlink()
            except FileNotFoundError:
                pass


def validate_evidence_digest_authority(writer: Any) -> None:
    request = {
        "databasePolicy": {
            "recoveryPointEvidenceRef": "contracts/operations/rollback-rehearsal-gate-contract.v1.json",
            "forwardFixDecisionRef": "contracts/operations/rollback-rehearsal-registry.v1.json",
        },
        "artifactPolicy": {
            "parserArtifactEvidenceRef": "contracts/operations/release-baseline-registry.v1.json",
            "objectVersionEvidenceRef": "contracts/operations/production-operability-status.json",
        },
        "entryCriteriaRefs": [
            "scripts/request-memory-os-rollback-rehearsal.py",
            "scripts/validate-memory-os-rollback-rehearsal-gate.py",
            "scripts/reconcile-memory-os-rollback-rehearsal-gate.py",
            "contracts/operations/rollback-rehearsal-gate-contract.v1.json",
            "contracts/operations/release-baseline-registry.v1.json",
        ],
    }
    request[writer.EVIDENCE_DIGEST_FIELD] = writer.evidence_digest_map(request)
    writer.validate_evidence_digest_binding(request, required=True)

    stale = copy.deepcopy(request)
    first_ref = next(iter(stale[writer.EVIDENCE_DIGEST_FIELD]))
    stale[writer.EVIDENCE_DIGEST_FIELD][first_ref] = "0" * 64
    expect_rejected(
        "stale evidence digest",
        lambda: writer.validate_evidence_digest_binding(stale, required=True),
    )

    missing = copy.deepcopy(request)
    missing[writer.EVIDENCE_DIGEST_FIELD].pop(first_ref)
    expect_rejected(
        "missing evidence digest",
        lambda: writer.validate_evidence_digest_binding(missing, required=True),
    )

    absent = copy.deepcopy(request)
    absent.pop(writer.EVIDENCE_DIGEST_FIELD)
    expect_rejected(
        "missing digest authority",
        lambda: writer.validate_evidence_digest_binding(absent, required=True),
    )

    evidence_path = ROOT / first_ref
    original = evidence_path.read_bytes()
    try:
        evidence_path.write_bytes(original + b"\n")
        expect_rejected(
            "tracked evidence differs from exact HEAD",
            lambda: writer.validate_evidence_digest_binding(request, required=True),
        )
    finally:
        evidence_path.write_bytes(original)


def validate_approver_field_authority(writer: Any) -> None:
    valid = [
        {"role": "RELEASE_OWNER", "approverRef": "apr_release_ci11"},
        {"role": "DATABASE_RECOVERY_OWNER", "approverRef": "apr_database_ci22"},
    ]
    writer.validate_approvers(copy.deepcopy(valid))

    unknown = copy.deepcopy(valid)
    unknown[0]["decision"] = "APPROVED"
    expect_rejected(
        "approver unknown field",
        lambda: writer.validate_approvers(unknown),
    )

    missing = copy.deepcopy(valid)
    missing[1].pop("approverRef")
    expect_rejected(
        "approver missing field",
        lambda: writer.validate_approvers(missing),
    )


def validate_planning_progression(reconciler: Any) -> None:
    contract = copy.deepcopy(load_json(CONTRACT_PATH))
    changed = reconciler.reconcile_contract(contract, 2, 1, 1, 1)
    if not changed:
        raise RuntimeError("rollback planning progression did not update contract authority")
    state = contract.get("currentAdmissionState")
    readiness = contract.get("readiness")
    if not isinstance(state, dict) or not isinstance(readiness, dict):
        raise RuntimeError("rollback planning progression lost contract authority")
    expected_state = {
        "approvedReleaseCount": 2,
        "rollbackEligibleReleaseCount": 1,
        "admissibleReleasePairCount": 1,
        "rehearsalRequestCount": 1,
        "admissionDecision": "ADMISSION_AVAILABLE",
    }
    for field, expected in expected_state.items():
        if state.get(field) != expected:
            raise RuntimeError(f"rollback planning state did not progress: {field}")
    if readiness.get("approvedReleasePairAvailable") is not True:
        raise RuntimeError("approved release pair was not reflected")
    if readiness.get("rollbackTargetAvailable") is not True:
        raise RuntimeError("rollback target was not reflected")
    if readiness.get("rehearsalRequested") is not True:
        raise RuntimeError("reviewed rehearsal request was not reflected")
    if readiness.get("rehearsalExecuted") is not False:
        raise RuntimeError("planning authority manufactured rehearsal execution")
    if readiness.get("independentReviewCompleted") is not False:
        raise RuntimeError("planning authority manufactured independent review")
    if readiness.get("productionReady") is not False:
        raise RuntimeError("planning authority manufactured production readiness")

    status = copy.deepcopy(load_json(STATUS_PATH))
    gate = next(
        (item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"),
        None,
    )
    if not isinstance(gate, dict):
        raise RuntimeError("OPS-P0-008 missing for rollback progression probe")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    if not isinstance(existing, list) or not isinstance(missing, list):
        raise RuntimeError("OPS-P0-008 rollback progression lists missing")
    if reconciler.EMPTY_RELEASE_EVIDENCE not in existing:
        existing.append(reconciler.EMPTY_RELEASE_EVIDENCE)
    for gap in (
        reconciler.APPROVED_PAIR_GAP,
        reconciler.ADMITTED_REQUEST_GAP,
        reconciler.EXECUTED_REHEARSAL_GAP,
        reconciler.INDEPENDENT_REVIEW_GAP,
    ):
        if gap not in missing:
            missing.append(gap)
    reconciler.reconcile_status(status, 2, 1, 1)
    if reconciler.EMPTY_RELEASE_EVIDENCE in existing:
        raise RuntimeError("empty release evidence survived approved release progression")
    if reconciler.APPROVED_PAIR_GAP in missing:
        raise RuntimeError("approved rollback pair gap survived valid pair authority")
    if reconciler.ADMITTED_REQUEST_GAP in missing:
        raise RuntimeError("admitted request gap survived planning authority")
    if reconciler.EXECUTED_REHEARSAL_GAP not in missing:
        raise RuntimeError("planning authority removed executed rehearsal blocker")
    if reconciler.INDEPENDENT_REVIEW_GAP not in missing:
        raise RuntimeError("planning authority removed independent review blocker")
    if status.get("productionDecision") != "NO_GO":
        raise RuntimeError("planning authority changed production decision")


def validate_transaction_rollback(reconciler: Any) -> None:
    contract_original = CONTRACT_PATH.read_bytes()
    status_original = STATUS_PATH.read_bytes()
    contract = copy.deepcopy(load_json(CONTRACT_PATH))
    status = copy.deepcopy(load_json(STATUS_PATH))
    state = contract.get("currentAdmissionState")
    if not isinstance(state, dict):
        raise RuntimeError("rollback state missing for transaction probe")
    state["rehearsalRequestCount"] = 99

    def fail_post_write() -> None:
        raise RuntimeError("synthetic rollback aggregate validator failure")

    try:
        reconciler.commit_authority_transaction(contract, status, validator_runner=fail_post_write)
    except RuntimeError as exc:
        if "synthetic rollback aggregate validator failure" not in str(exc):
            raise
    else:
        raise RuntimeError("rollback reconcile accepted synthetic post-write validator failure")
    if CONTRACT_PATH.read_bytes() != contract_original:
        raise RuntimeError("rollback reconcile left partial contract after validator failure")
    if STATUS_PATH.read_bytes() != status_original:
        raise RuntimeError("rollback reconcile left partial status after validator failure")


def main() -> int:
    writer = load_module(WRITER_PATH, "rollback_rehearsal_writer_negative")
    reconciler = load_module(RECONCILER_PATH, "rollback_rehearsal_reconciler_negative")
    contract = load_json(CONTRACT_PATH)
    release_registry = load_json(RELEASE_REGISTRY_PATH)
    registry = load_json(REGISTRY_PATH)
    contract_bytes = CONTRACT_PATH.read_bytes()
    registry_bytes = REGISTRY_PATH.read_bytes()
    status_bytes = STATUS_PATH.read_bytes()

    writer.validate_registry_for_append(
        copy.deepcopy(registry), copy.deepcopy(contract), copy.deepcopy(release_registry)
    )
    validate_contract_append_authority(writer, contract, registry, release_registry)
    validate_evidence_ref_containment(writer)
    validate_evidence_digest_authority(writer)
    validate_approver_field_authority(writer)
    validate_planning_progression(reconciler)
    validate_transaction_rollback(reconciler)

    registry_cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("registryClass", lambda value: value.__setitem__("registryClass", "OTHER")),
        ("appendOnly", lambda value: value.__setitem__("appendOnly", False)),
        ("planningAuthorityOnly", lambda value: value.__setitem__("planningAuthorityOnly", False)),
        ("productionEvidence", lambda value: value.__setitem__("productionEvidence", True)),
        ("boolean count", lambda value: value.__setitem__("rehearsalRequestCount", False)),
        ("count drift", lambda value: value.__setitem__("rehearsalRequestCount", 1)),
        ("latest pointer drift", lambda value: value.__setitem__("latestRehearsalId", "rrh_20991231_forged")),
        ("limitations drift", lambda value: value.__setitem__("limitations", ["production traffic allowed"])),
        ("unknown field", lambda value: value.__setitem__("unexpectedAuthority", True)),
    ]
    for label, mutate in registry_cases:
        candidate = copy.deepcopy(registry)
        mutate(candidate)
        expect_rejected(
            label,
            lambda candidate=candidate: writer.validate_registry_for_append(
                candidate, copy.deepcopy(contract), copy.deepcopy(release_registry)
            ),
        )
        if label in {"registryClass", "appendOnly", "productionEvidence", "boolean count", "limitations drift"}:
            reconcile_rejects_without_authority_write(
                copy.deepcopy(candidate), registry_bytes, contract_bytes, status_bytes, label
            )

    release_cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("release productionEvidence", lambda value: value.__setitem__("productionEvidence", True)),
        ("release boolean count", lambda value: value.__setitem__("approvedReleaseCount", False)),
    ]
    for label, mutate in release_cases:
        candidate_release = copy.deepcopy(release_registry)
        mutate(candidate_release)
        expect_rejected(
            label,
            lambda candidate_release=candidate_release: writer.validate_registry_for_append(
                copy.deepcopy(registry), copy.deepcopy(contract), candidate_release
            ),
        )

    validator_rejects_lock_drift(contract, contract_bytes)

    if CONTRACT_PATH.read_bytes() != contract_bytes:
        raise RuntimeError("rollback contract bytes changed after negative suite")
    if REGISTRY_PATH.read_bytes() != registry_bytes:
        raise RuntimeError("rollback registry bytes changed after negative suite")
    if STATUS_PATH.read_bytes() != status_bytes:
        raise RuntimeError("production status bytes changed after negative suite")

    print("PASS: rollback rehearsal authority accepts planning progression while rejecting corrupt contract/registry authority, unsafe refs, uncommitted or stale evidence bytes, approver shape drift and aggregate partial writes")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ROLLBACK REHEARSAL REGISTRY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
