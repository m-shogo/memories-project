#!/usr/bin/env python3
"""Register rollback rehearsal admission foundations without admitting a request."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
REHEARSAL_REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
WRITER_PATH = ROOT / "scripts/request-memory-os-rollback-rehearsal.py"

EXISTING = (
    "fail-closed rollback rehearsal admission authority requiring distinct approved source and rollback-target releases before any isolated rehearsal request can be recorded",
    "rollback target must already be verified ELIGIBLE or CONDITIONALLY_ELIGIBLE and every target condition is retained as a rehearsal stop condition",
    "exclusive-lock atomic request writer forbids production traffic, production credentials, automatic promotion and destructive down migration",
    "empty approved release registry produces zero admissible pairs and BLOCKED_NO_APPROVED_ROLLBACK_PAIR without treating candidate or CI evidence as release authority",
)
MISSING = (
    "approved source and rollback-target release pair with verified rollback eligibility and retained exact artifacts",
    "admitted isolated rollback rehearsal request with distinct Release Owner and Database Recovery Owner approvals",
    "executed rollback rehearsal proving startup, session, tenant, deletion, idempotency, parser artifact and exact object-version invariants",
    "traffic-drain and rollback timing evidence with monitored stop conditions and independent review",
)
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


def main() -> int:
    contract = load(CONTRACT_PATH)
    releases = load(RELEASE_REGISTRY_PATH)
    rehearsals = load(REHEARSAL_REGISTRY_PATH)
    try:
        writer = load_module(WRITER_PATH, "rollback_rehearsal_writer_reconcile")
        writer.validate_registry_for_append(rehearsals, contract, releases)
    except Exception as exc:
        raise ReconcileFailure(f"rollback rehearsal append authority invalid: {exc}") from exc

    readiness = contract.get("readiness")
    state = contract.get("currentAdmissionState")
    require(isinstance(readiness, dict) and isinstance(state, dict),
            "rollback rehearsal contract readiness missing")
    for field in (
        "contractDefined", "registryImplemented", "writerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True, f"rollback gate foundation missing: {field}")
    require(releases.get("approvedReleaseCount") == 0 and releases.get("releases") == [],
            "foundation reconcile currently requires no approved release")
    require(rehearsals.get("rehearsalRequestCount") == 0 and rehearsals.get("requests") == [],
            "foundation reconcile cannot overwrite admitted rehearsal requests")
    require(state.get("approvedReleaseCount") == 0 and
            state.get("rollbackEligibleReleaseCount") == 0 and
            state.get("admissibleReleasePairCount") == 0 and
            state.get("rehearsalRequestCount") == 0 and
            state.get("admissionDecision") == "BLOCKED_NO_APPROVED_ROLLBACK_PAIR",
            "empty rollback admission state drift")
    require(readiness.get("approvedReleasePairAvailable") is False and
            readiness.get("rollbackTargetAvailable") is False and
            readiness.get("rehearsalRequested") is False and
            readiness.get("rehearsalExecuted") is False and
            readiness.get("productionReady") is False,
            "empty rollback gate cannot claim readiness")

    status = load(STATUS_PATH)
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
    for item in EXISTING:
        changed = append_once(existing, item) or changed
    for item in MISSING:
        changed = append_once(missing, item) or changed
    for ref in REFS:
        require((ROOT / ref).is_file(), f"rollback rehearsal evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    lowered = [str(item).lower() for item in missing]
    for label, terms in {
        "approved rollback pair": ("approved", "rollback-target", "eligibility"),
        "admitted request": ("admitted", "release owner", "database recovery owner"),
        "executed rehearsal": ("executed", "idempotency", "parser artifact"),
        "independent review": ("traffic-drain", "independent review"),
    }.items():
        require(any(all(term in item for term in terms) for item in lowered),
                f"required rollback gap disappeared: {label}")
    require(gate.get("status") == "PARTIAL" and
            status.get("productionDecision") == "NO_GO",
            "rollback foundation changed readiness")

    if not changed:
        print("Rollback rehearsal admission authority already reconciled")
        return 0
    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    STATUS_PATH.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print("Registered rollback rehearsal admission gate; admission remains blocked")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"ROLLBACK REHEARSAL GATE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
