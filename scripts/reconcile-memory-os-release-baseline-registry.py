#!/usr/bin/env python3
"""Reconcile approved-release registry authority without promoting production readiness."""

from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/release-baseline-registry-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/release-baseline-registry.v1.json")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
WRITER_REL = Path("scripts/register-memory-os-release-baseline.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-release-baseline-registry.py")
EVIDENCE_BINDING_VALIDATOR_REL = Path("scripts/validate-memory-os-release-baseline-evidence-binding.py")
VERSION_VALIDATOR_REL = Path("scripts/validate-memory-os-version-compatibility.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
WORKFLOW_REL = Path(".github/workflows/release-baseline-registry.yml")
EVIDENCE_README_REL = Path("docs/evidence/releases/README.md")
CONTRACT_PATH = ROOT / CONTRACT_REL
REGISTRY_PATH = ROOT / REGISTRY_REL
STATUS_PATH = ROOT / STATUS_REL
WRITER_PATH = ROOT / WRITER_REL
VALIDATOR_PATH = ROOT / VALIDATOR_REL
EVIDENCE_BINDING_VALIDATOR_PATH = ROOT / EVIDENCE_BINDING_VALIDATOR_REL
VERSION_VALIDATOR_PATH = ROOT / VERSION_VALIDATOR_REL
OPERABILITY_VALIDATOR_PATH = ROOT / OPERABILITY_VALIDATOR_REL
WORKFLOW_PATH = ROOT / WORKFLOW_REL
EVIDENCE_README_PATH = ROOT / EVIDENCE_README_REL

STATIC_EXISTING = (
    "append-only approved release baseline registry authority separating historical candidates, CI results, tags and branch heads from multi-role production release approval",
    "release records require distinct Security, Operability and Release Owner approvals plus immutable API, migration, parser artifact and runtime configuration digests",
    "release evidence references are source-bound to tracked non-symlink Git blobs at the approved release commit, so later evidence-path edits invalidate the authority instead of silently changing a historical release",
    "fail-closed release registry validator prevents active or rejected historical candidates from being relabeled as approved releases",
    "exclusive-lock and atomic-replacement release writer verifies exact clean HEAD, exact tag binding, external input record, three-role approval, complete source-bound evidence and unique release ID, tag and commit without manufacturing any authority",
)
EMPTY_REGISTRY_EVIDENCE = "empty release registry explicitly records that no approved predecessor or rollback-eligible release exists"
PREDECESSOR_GAP = "approved predecessor release record with three distinct required approvers and complete compatibility, restore, security, migration, parser and load evidence"
ROLLBACK_GAP = "rollback-eligible approved release whose binary and retained artifacts are verified against the expanded target schema"
INDEPENDENT_REVIEW_GAP = "independent review of the first release registration and writer execution evidence"
OBSOLETE_MISSING = (
    "implemented append-only release registration writer with exclusive release ID, tag and commit uniqueness enforcement",
)
REFS = (
    "contracts/operations/release-baseline-registry-contract.v1.json",
    "contracts/operations/release-baseline-registry.v1.json",
    "docs/evidence/releases/README.md",
    "scripts/register-memory-os-release-baseline.py",
    "scripts/validate-memory-os-release-baseline-registry.py",
    "scripts/validate-memory-os-release-baseline-evidence-binding.py",
    "scripts/validate-memory-os-release-baseline-evidence-binding-negative.py",
    "scripts/reconcile-memory-os-release-baseline-registry.py",
    ".github/workflows/release-baseline-registry.yml",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ReconcileFailure(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, relative, field in (
        (CONTRACT_PATH, CONTRACT_REL, "release baseline contract"),
        (REGISTRY_PATH, REGISTRY_REL, "release baseline registry"),
        (STATUS_PATH, STATUS_REL, "production operability status"),
        (WRITER_PATH, WRITER_REL, "release baseline writer"),
        (VALIDATOR_PATH, VALIDATOR_REL, "release baseline validator"),
        (EVIDENCE_BINDING_VALIDATOR_PATH, EVIDENCE_BINDING_VALIDATOR_REL, "release evidence binding validator"),
        (VERSION_VALIDATOR_PATH, VERSION_VALIDATOR_REL, "version compatibility validator"),
        (OPERABILITY_VALIDATOR_PATH, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (WORKFLOW_PATH, WORKFLOW_REL, "release baseline workflow"),
        (EVIDENCE_README_PATH, EVIDENCE_README_REL, "release evidence README"),
    ):
        require_exact_repo_file(path, relative, field)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> ModuleType:
    require_exact_repo_file(WRITER_PATH, WRITER_REL, "release baseline writer")
    spec = importlib.util.spec_from_file_location("memory_os_release_baseline_writer_for_reconcile", WRITER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load release baseline writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def remove_value(items: list[Any], value: str) -> bool:
    before = len(items)
    items[:] = [item for item in items if item != value]
    return len(items) != before


def run_canonical_validators() -> None:
    enforce_runtime_authorities()
    for validator in (
        VALIDATOR_PATH,
        EVIDENCE_BINDING_VALIDATOR_PATH,
        VERSION_VALIDATOR_PATH,
        OPERABILITY_VALIDATOR_PATH,
    ):
        subprocess.run([sys.executable, str(validator)], cwd=ROOT, check=True)


def commit_authority_transaction(
    contract: dict[str, Any],
    status: dict[str, Any],
    *,
    validator_runner: Callable[[], None] | None = None,
) -> None:
    originals = {
        CONTRACT_PATH: CONTRACT_PATH.read_bytes(),
        STATUS_PATH: STATUS_PATH.read_bytes(),
    }
    try:
        CONTRACT_PATH.write_text(
            json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        STATUS_PATH.write_text(
            json.dumps(status, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if validator_runner is None:
            run_canonical_validators()
        else:
            validator_runner()
    except BaseException:
        for path, payload in originals.items():
            path.write_bytes(payload)
        raise


def release_inventory(registry: dict[str, Any]) -> tuple[int, bool]:
    releases = registry.get("releases")
    count = registry.get("approvedReleaseCount")
    require(isinstance(releases, list) and all(isinstance(item, dict) for item in releases),
            "release registry releases invalid")
    require(isinstance(count, int) and not isinstance(count, bool) and count == len(releases),
            "approvedReleaseCount drift")
    rollback_eligible = any(
        item.get("rollbackEligibility", {}).get("status") in {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"}
        for item in releases
    )
    return count, rollback_eligible


def reconcile_contract_readiness(
    contract: dict[str, Any], approved_count: int, rollback_eligible: bool
) -> bool:
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "release registry readiness missing")
    for foundation in (
        "contractDefined", "registryImplemented", "validatorImplemented", "writerImplemented"
    ):
        require(readiness.get(foundation) is True,
                f"release registry foundation is incomplete: {foundation}")

    changed = False
    desired = {
        "approvedReleaseCount": approved_count,
        "approvedPredecessorAvailable": approved_count > 0,
        "rollbackEligibleReleaseAvailable": rollback_eligible,
        "independentReviewCompleted": False,
        "productionReady": False,
    }
    for field, value in desired.items():
        if readiness.get(field) != value:
            readiness[field] = value
            changed = True

    if approved_count == 0:
        note = (
            "The writer exists but cannot manufacture approvals, evidence, a release tag or production readiness. "
            "No release is approved, so approved predecessor and rollback eligibility remain unavailable."
        )
    else:
        note = (
            f"The append-only registry contains {approved_count} human-approved release baseline(s). "
            "This establishes release inventory only; independent integrated review and application production readiness remain separate and automatic promotion is forbidden."
        )
    if readiness.get("note") != note:
        readiness["note"] = note
        changed = True
    return changed


def reconcile_status(
    status: dict[str, Any], approved_count: int, rollback_eligible: bool
) -> bool:
    require(status.get("productionDecision") == "NO_GO",
            "release registry cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL",
            "OPS-P0-008 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-008 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-008 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-008 evidenceRefs must be a list")

    changed = False
    for item in STATIC_EXISTING:
        changed = append_once(existing, item) or changed
    if approved_count == 0:
        changed = append_once(existing, EMPTY_REGISTRY_EVIDENCE) or changed
    else:
        changed = remove_value(existing, EMPTY_REGISTRY_EVIDENCE) or changed

    for item in OBSOLETE_MISSING:
        changed = remove_value(missing, item) or changed
    if approved_count == 0:
        changed = append_once(missing, PREDECESSOR_GAP) or changed
    else:
        changed = remove_value(missing, PREDECESSOR_GAP) or changed
    if rollback_eligible:
        changed = remove_value(missing, ROLLBACK_GAP) or changed
    else:
        changed = append_once(missing, ROLLBACK_GAP) or changed
    changed = append_once(missing, INDEPENDENT_REVIEW_GAP) or changed

    for ref in REFS:
        require((ROOT / ref).is_file(), f"release registry evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    lowered = [str(item).lower() for item in missing]
    if approved_count == 0:
        require(any("approved" in item and "predecessor" in item and "release" in item
                    for item in lowered),
                "approved predecessor release gap disappeared")
    else:
        require(PREDECESSOR_GAP not in missing,
                "approved predecessor gap survived approved release inventory")
    if not rollback_eligible:
        require(any("rollback-eligible" in item for item in lowered),
                "rollback-eligible release gap disappeared")
    else:
        require(ROLLBACK_GAP not in missing,
                "rollback-eligible release gap survived verified rollback authority")
    require(any("independent review" in item for item in lowered),
            "release registration review gap disappeared")
    require(not any("implemented append-only release registration writer" in item
                    for item in lowered),
            "implemented writer remains listed as missing")
    require(gate.get("status") == "PARTIAL" and
            status.get("productionDecision") == "NO_GO",
            "release authority changed production readiness")
    return changed


def main() -> int:
    enforce_runtime_authorities()
    contract = load(CONTRACT_PATH)
    registry = load(REGISTRY_PATH)
    writer = load_writer()
    try:
        writer.validate_registry_for_append(registry, contract)
    except Exception as exc:
        raise ReconcileFailure(f"release registry append-only authority invalid: {exc}") from exc

    approved_count, rollback_eligible = release_inventory(registry)
    candidate_contract = copy.deepcopy(contract)
    contract_changed = reconcile_contract_readiness(
        candidate_contract, approved_count, rollback_eligible
    )

    status = load(STATUS_PATH)
    status_changed = reconcile_status(status, approved_count, rollback_eligible)

    if not contract_changed and not status_changed:
        run_canonical_validators()
        print("Release baseline registry authority already reconciled")
        return 0
    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    commit_authority_transaction(candidate_contract, status)
    print("Reconciled approved release baseline inventory; OPS-P0-008 remains PARTIAL")
    print(f"approved releases: {approved_count}")
    print(f"rollback-eligible release available: {rollback_eligible}")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReconcileFailure, subprocess.CalledProcessError) as exc:
        print(f"RELEASE BASELINE REGISTRY RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
