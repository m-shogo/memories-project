#!/usr/bin/env python3
"""Reconcile rollback rehearsal planning authority without executing rollback."""

from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
REHEARSAL_REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
WRITER_PATH = ROOT / "scripts/request-memory-os-rollback-rehearsal.py"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-rollback-rehearsal-gate.py"
RELEASE_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-release-baseline-registry.py"
VERSION_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-version-compatibility.py"
OPERABILITY_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-operability.py"

STATIC_EXISTING = (
    "fail-closed rollback rehearsal admission authority requiring distinct approved source and rollback-target releases before any isolated rehearsal request can be recorded",
    "rollback target must already be verified ELIGIBLE or CONDITIONALLY_ELIGIBLE and every target condition is retained as a rehearsal stop condition",
    "exclusive-lock atomic request writer forbids production traffic, production credentials, automatic promotion and destructive down migration",
)
EMPTY_RELEASE_EVIDENCE = "empty approved release registry produces zero admissible pairs and BLOCKED_NO_APPROVED_ROLLBACK_PAIR without treating candidate or CI evidence as release authority"
APPROVED_PAIR_GAP = "approved source and rollback-target release pair with verified rollback eligibility and retained exact artifacts"
ADMITTED_REQUEST_GAP = "admitted isolated rollback rehearsal request with distinct Release Owner and Database Recovery Owner approvals"
EXECUTED_REHEARSAL_GAP = "executed rollback rehearsal proving startup, session, tenant, deletion, idempotency, parser artifact and exact object-version invariants"
INDEPENDENT_REVIEW_GAP = "traffic-drain and rollback timing evidence with monitored stop conditions and independent review"
REFS = (
    "contracts/operations/rollback-rehearsal-gate-contract.v1.json",
    "contracts/operations/rollback-rehearsal-registry.v1.json",
    "contracts/operations/release-baseline-registry.v1.json",
    "docs/runbooks/memory-os-rollback-rehearsal.md",
    "scripts/request-memory-os-rollback-rehearsal.py",
    "scripts/validate-memory-os-rollback-rehearsal-gate.py",
    "scripts/reconcile-memory-os-rollback-rehearsal-gate.py",
    ".github/workflows/rollback-rehearsal-gate.yml",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None,
            f"cannot load authority module: {path.relative_to(ROOT)}")
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


def derive_counts(releases: dict[str, Any], rehearsals: dict[str, Any]) -> tuple[int, int, int, int]:
    release_rows = releases.get("releases")
    request_rows = rehearsals.get("requests")
    release_count = releases.get("approvedReleaseCount")
    request_count = rehearsals.get("rehearsalRequestCount")
    require(isinstance(release_rows, list) and all(isinstance(item, dict) for item in release_rows),
            "approved release rows invalid")
    require(isinstance(request_rows, list) and all(isinstance(item, dict) for item in request_rows),
            "rollback rehearsal rows invalid")
    require(isinstance(release_count, int) and not isinstance(release_count, bool) and
            release_count == len(release_rows), "approvedReleaseCount drift")
    require(isinstance(request_count, int) and not isinstance(request_count, bool) and
            request_count == len(request_rows), "rehearsalRequestCount drift")
    eligible_count = sum(
        1 for item in release_rows
        if isinstance(item.get("rollbackEligibility"), dict) and
        item["rollbackEligibility"].get("status") in {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"} and
        item["rollbackEligibility"].get("verified") is True
    )
    admissible_pairs = max(0, release_count - 1) * eligible_count
    return release_count, eligible_count, admissible_pairs, request_count


def reconcile_contract(
    contract: dict[str, Any],
    release_count: int,
    eligible_count: int,
    admissible_pairs: int,
    request_count: int,
) -> bool:
    readiness = contract.get("readiness")
    state = contract.get("currentAdmissionState")
    boundary = contract.get("evidenceBoundary")
    require(isinstance(readiness, dict) and isinstance(state, dict) and isinstance(boundary, dict),
            "rollback rehearsal contract authority missing")
    for field in (
        "contractDefined", "registryImplemented", "writerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True, f"rollback gate foundation missing: {field}")
    require(boundary.get("planningAuthorityOnly") is True and
            boundary.get("rehearsalExecuted") is False and
            boundary.get("rollbackExecuted") is False and
            boundary.get("productionEvidence") is False and
            boundary.get("releaseCompatibilityEvidence") is False and
            boundary.get("productionReady") is False,
            "rollback rehearsal evidence boundary drift")

    decision = "ADMISSION_AVAILABLE" if admissible_pairs > 0 else "BLOCKED_NO_APPROVED_ROLLBACK_PAIR"
    desired_state = {
        "approvedReleaseCount": release_count,
        "rollbackEligibleReleaseCount": eligible_count,
        "admissibleReleasePairCount": admissible_pairs,
        "rehearsalRequestCount": request_count,
        "admissionDecision": decision,
    }
    desired_readiness = {
        "approvedReleasePairAvailable": admissible_pairs > 0,
        "rollbackTargetAvailable": eligible_count > 0,
        "rehearsalRequested": request_count > 0,
        "rehearsalExecuted": False,
        "independentReviewCompleted": False,
        "productionReady": False,
    }
    changed = False
    for field, value in desired_state.items():
        if state.get(field) != value:
            state[field] = value
            changed = True
    for field, value in desired_readiness.items():
        if readiness.get(field) != value:
            readiness[field] = value
            changed = True
    return changed


def reconcile_status(
    status: dict[str, Any],
    release_count: int,
    admissible_pairs: int,
    request_count: int,
) -> bool:
    require(status.get("productionDecision") == "NO_GO",
            "rollback gate cannot change production decision")
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
    if release_count == 0:
        changed = append_once(existing, EMPTY_RELEASE_EVIDENCE) or changed
    else:
        changed = remove_value(existing, EMPTY_RELEASE_EVIDENCE) or changed

    if admissible_pairs > 0:
        changed = remove_value(missing, APPROVED_PAIR_GAP) or changed
    else:
        changed = append_once(missing, APPROVED_PAIR_GAP) or changed
    if request_count > 0:
        changed = remove_value(missing, ADMITTED_REQUEST_GAP) or changed
    else:
        changed = append_once(missing, ADMITTED_REQUEST_GAP) or changed
    changed = append_once(missing, EXECUTED_REHEARSAL_GAP) or changed
    changed = append_once(missing, INDEPENDENT_REVIEW_GAP) or changed

    for ref in REFS:
        require((ROOT / ref).is_file(), f"rollback rehearsal evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    if admissible_pairs == 0:
        require(APPROVED_PAIR_GAP in missing, "approved rollback pair gap disappeared")
    else:
        require(APPROVED_PAIR_GAP not in missing, "approved rollback pair gap survived valid pair authority")
    if request_count == 0:
        require(ADMITTED_REQUEST_GAP in missing, "admitted request gap disappeared")
    else:
        require(ADMITTED_REQUEST_GAP not in missing, "admitted request gap survived planning authority")
    require(EXECUTED_REHEARSAL_GAP in missing,
            "planning authority cannot satisfy executed rehearsal gap")
    require(INDEPENDENT_REVIEW_GAP in missing,
            "planning authority cannot satisfy independent review gap")
    require(gate.get("status") == "PARTIAL" and status.get("productionDecision") == "NO_GO",
            "rollback planning authority changed production readiness")
    return changed


def run_canonical_validators() -> None:
    for validator in (
        VALIDATOR_PATH,
        RELEASE_VALIDATOR_PATH,
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
        CONTRACT_PATH.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        STATUS_PATH.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if validator_runner is None:
            run_canonical_validators()
        else:
            validator_runner()
    except BaseException:
        for path, payload in originals.items():
            path.write_bytes(payload)
        raise


def main() -> int:
    contract = load(CONTRACT_PATH)
    releases = load(RELEASE_REGISTRY_PATH)
    rehearsals = load(REHEARSAL_REGISTRY_PATH)
    try:
        writer = load_module(WRITER_PATH, "rollback_rehearsal_writer_reconcile")
        writer.validate_registry_for_append(rehearsals, contract, releases)
    except Exception as exc:
        raise ReconcileFailure(f"rollback rehearsal append authority invalid: {exc}") from exc

    release_count, eligible_count, admissible_pairs, request_count = derive_counts(releases, rehearsals)
    candidate_contract = copy.deepcopy(contract)
    contract_changed = reconcile_contract(
        candidate_contract, release_count, eligible_count, admissible_pairs, request_count
    )
    status = load(STATUS_PATH)
    status_changed = reconcile_status(status, release_count, admissible_pairs, request_count)

    if not contract_changed and not status_changed:
        print("Rollback rehearsal admission authority already reconciled")
        return 0
    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    commit_authority_transaction(candidate_contract, status)
    print("Reconciled rollback rehearsal planning authority; execution remains absent")
    print(f"approved releases: {release_count}")
    print(f"rollback eligible releases: {eligible_count}")
    print(f"admissible pairs: {admissible_pairs}")
    print(f"rehearsal requests: {request_count}")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReconcileFailure, subprocess.CalledProcessError) as exc:
        print(f"ROLLBACK REHEARSAL GATE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
