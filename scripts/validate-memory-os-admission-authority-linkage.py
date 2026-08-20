#!/usr/bin/env python3
"""Validate repository path linkage for high-impact admission authorities."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROOT_RESOLVED = ROOT.resolve()
CONTRACTS = [
    "contracts/operations/migration-production-shaped-admission-contract.v1.json",
    "contracts/operations/incident-human-tabletop-evidence-contract.v1.json",
    "contracts/operations/incident-contact-routing-admission-contract.v1.json",
    "contracts/operations/observability-stack-deployment-contract.v1.json",
    "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json",
    "contracts/operations/deletion-worker-host-failure-contract.v1.json",
    "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "contracts/operations/client-baseline-registry-contract.v1.json",
    "contracts/operations/production-shaped-failure-drill-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
]
FILE_KEYS = {
    "registryPath", "registry", "writer", "validator", "reconcile", "workflow",
    "sourceMigrationLifecycleContract", "sourceMigrationEvidenceRegistryContract",
    "sourceReleaseRegistry", "sourceReleasePairRegistry", "sourceCompatibilityExecutionAuthority",
    "environmentGenerationContract", "environmentGenerationRegistry",
    "environmentRecordSemanticValidator", "generationRegistryRecordSchema", "negativeAdmissionValidator",
    "backupRestoreGenerationContract", "sourceIncidentPolicy",
    "sourceObservabilityStackContract", "sourceObservabilityStackRegistry",
    "sourceLogContract", "sourceLogAccessContract", "sourceMetricsContract",
    "sourceMetricsScrapeContract", "sourceMetricsOperationsContract",
    "sourceAlertingContract", "sourcePolicyContract", "sourceOperationsContract",
    "sourceOperationEvidenceContract", "backupRestorePolicyContract",
    "localFoundationEvidence", "environmentRecordSchema", "canonicalRunbook",
    "runbook", "sourcePlan", "sourceIncidentResponseContract",
}
DIRECTORY_KEYS = {"ledgerDirectory", "canonicalDirectory"}
FILE_SLOT_KEYS = {"appendLockPath"}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def safe_relative(value: str, field: str) -> Path:
    path = Path(value)
    require(
        bool(path.parts) and path != Path(".") and not path.is_absolute() and ".." not in path.parts,
        f"unsafe linked path in {field}: {value}",
    )
    return path


def require_contained_path(linked: Path, field: str, value: str, *, include_leaf: bool) -> None:
    cursor = ROOT
    parts = linked.parts if include_leaf else linked.parts[:-1]
    for part in parts:
        cursor = cursor / part
        require(not cursor.is_symlink(), f"symlinked admission authority path in {field}: {value}")
    target = ROOT / linked if include_leaf else (ROOT / linked).parent
    try:
        resolved = target.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise Fail(f"unresolvable admission authority path in {field}: {value}: {exc}") from exc
    require(
        resolved == ROOT_RESOLVED or ROOT_RESOLVED in resolved.parents,
        f"admission authority path escapes repository in {field}: {value}",
    )


def repository_entry(value: str, field: str, *, directory: bool) -> Path:
    linked = safe_relative(value, field)
    candidate = ROOT / linked
    require_contained_path(linked, field, value, include_leaf=True)
    if directory:
        require(candidate.is_dir(), f"broken admission authority directory link: {field} -> {value}")
    else:
        require(candidate.is_file(), f"broken admission authority file link: {field} -> {value}")
    return candidate


def repository_file_slot(value: str, field: str) -> Path:
    linked = safe_relative(value, field)
    require(linked.name not in {"", ".", ".."}, f"invalid admission authority file slot in {field}: {value}")
    candidate = ROOT / linked
    require_contained_path(linked, field, value, include_leaf=False)
    require(candidate.parent.is_dir(), f"broken admission authority parent directory: {field} -> {value}")
    require(not candidate.is_symlink(), f"symlinked admission authority file slot in {field}: {value}")
    if candidate.exists():
        require(candidate.is_file(), f"admission authority file slot is not a file: {field} -> {value}")
    return candidate


def main() -> int:
    checked_files = 0
    checked_directories = 0
    checked_file_slots = 0
    for relative in CONTRACTS:
        contract_path = ROOT / relative
        require(contract_path.is_file(), f"admission contract missing: {relative}")
        contract = load(contract_path)
        for key, value in contract.items():
            if key in FILE_KEYS:
                require(isinstance(value, str) and value, f"{relative}.{key} must be a non-empty repository path")
                repository_entry(value, f"{relative}.{key}", directory=False)
                checked_files += 1
            elif key in DIRECTORY_KEYS:
                require(isinstance(value, str) and value, f"{relative}.{key} must be a non-empty repository directory")
                repository_entry(value, f"{relative}.{key}", directory=True)
                checked_directories += 1
            elif key in FILE_SLOT_KEYS:
                require(isinstance(value, str) and value, f"{relative}.{key} must be a non-empty repository file slot")
                repository_file_slot(value, f"{relative}.{key}")
                checked_file_slots += 1
    print("Memory OS admission authority linkage validation PASS")
    print(f"contracts checked: {len(CONTRACTS)}")
    print(f"file links checked: {checked_files}")
    print(f"directory links checked: {checked_directories}")
    print(f"file slots checked: {checked_file_slots}")
    print("production decision: unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION AUTHORITY LINKAGE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
