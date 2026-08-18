#!/usr/bin/env python3
"""Register the approved-release registry foundation without approving a release."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
WRITER_PATH = ROOT / "scripts/register-memory-os-release-baseline.py"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-release-baseline-registry.py"
EVIDENCE_BINDING_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-release-baseline-evidence-binding.py"
VERSION_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-version-compatibility.py"
OPERABILITY_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-operability.py"

EXISTING = (
    "append-only approved release baseline registry authority separating historical candidates, CI results, tags and branch heads from multi-role production release approval",
    "empty release registry explicitly records that no approved predecessor or rollback-eligible release exists",
    "release records require distinct Security, Operability and Release Owner approvals plus immutable API, migration, parser artifact and runtime configuration digests",
    "release evidence references are source-bound to tracked non-symlink Git blobs at the approved release commit, so later evidence-path edits invalidate the authority instead of silently changing a historical release",
    "fail-closed release registry validator prevents active or rejected historical candidates from being relabeled as approved releases",
    "exclusive-lock and atomic-replacement release writer verifies exact clean HEAD, exact tag binding, external input record, three-role approval, complete source-bound evidence and unique release ID, tag and commit without manufacturing any authority",
)
MISSING = (
    "approved predecessor release record with three distinct required approvers and complete compatibility, restore, security, migration, parser and load evidence",
    "rollback-eligible approved release whose binary and retained artifacts are verified against the expanded target schema",
    "independent review of the first release registration and writer execution evidence",
)
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


def run_canonical_validators() -> None:
    for validator in (
        VALIDATOR_PATH,
        EVIDENCE_BINDING_VALIDATOR_PATH,
        VERSION_VALIDATOR_PATH,
        OPERABILITY_VALIDATOR_PATH,
    ):
        subprocess.run([sys.executable, str(validator)], cwd=ROOT, check=True)


def commit_status_transaction(
    status: dict[str, Any],
    *,
    validator_runner: Callable[[], None] | None = None,
) -> None:
    original = STATUS_PATH.read_bytes()
    try:
        STATUS_PATH.write_text(
            json.dumps(status, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if validator_runner is None:
            run_canonical_validators()
        else:
            validator_runner()
    except BaseException:
        STATUS_PATH.write_bytes(original)
        raise


def main() -> int:
    contract = load(CONTRACT_PATH)
    registry = load(REGISTRY_PATH)
    writer = load_writer()
    try:
        writer.validate_registry_for_append(registry, contract)
    except Exception as exc:
        raise ReconcileFailure(f"release registry append-only authority invalid: {exc}") from exc
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "release registry readiness missing")
    for foundation in (
        "contractDefined", "registryImplemented", "validatorImplemented", "writerImplemented"
    ):
        require(readiness.get(foundation) is True,
                f"release registry foundation is incomplete: {foundation}")
    require(registry.get("approvedReleaseCount") == 0 and
            registry.get("releases") == [],
            "foundation reconcile cannot run after a release is registered")
    require(readiness.get("approvedReleaseCount") == 0 and
            readiness.get("approvedPredecessorAvailable") is False and
            readiness.get("rollbackEligibleReleaseAvailable") is False and
            readiness.get("independentReviewCompleted") is False and
            readiness.get("productionReady") is False,
            "empty release registry readiness drift")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "release registry foundation cannot change production decision")
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
    for item in OBSOLETE_MISSING:
        if item in missing:
            missing.remove(item)
            changed = True
    for item in MISSING:
        changed = append_once(missing, item) or changed
    for ref in REFS:
        require((ROOT / ref).is_file(), f"release registry evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    lowered = [str(item).lower() for item in missing]
    require(any("approved" in item and "predecessor" in item and "release" in item
                for item in lowered),
            "approved predecessor release gap disappeared")
    require(any("rollback-eligible" in item for item in lowered),
            "rollback-eligible release gap disappeared")
    require(any("independent review" in item for item in lowered),
            "release registration review gap disappeared")
    require(not any("implemented append-only release registration writer" in item
                    for item in lowered),
            "implemented writer remains listed as missing")
    require(gate.get("status") == "PARTIAL" and
            status.get("productionDecision") == "NO_GO",
            "release foundation changed readiness")

    if not changed:
        print("Release baseline registry foundation already reconciled")
        return 0
    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    commit_status_transaction(status)
    print("Registered release writer foundation; approved release count remains zero")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"RELEASE BASELINE REGISTRY RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
