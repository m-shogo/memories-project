#!/usr/bin/env python3
"""Validate repository path linkage for high-impact admission authorities."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
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
    "registryPath", "writer", "validator", "reconcile", "workflow",
    "sourceMigrationLifecycleContract", "sourceMigrationEvidenceRegistryContract",
    "sourceReleaseRegistry", "sourceCompatibilityExecutionAuthority",
    "environmentGenerationContract", "environmentGenerationRegistry",
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
    require(not path.is_absolute() and ".." not in path.parts, f"unsafe linked path in {field}: {value}")
    return path


def main() -> int:
    checked_files = 0
    checked_directories = 0
    for relative in CONTRACTS:
        contract_path = ROOT / relative
        require(contract_path.is_file(), f"admission contract missing: {relative}")
        contract = load(contract_path)
        for key, value in contract.items():
            if key in FILE_KEYS:
                require(isinstance(value, str) and value, f"{relative}.{key} must be a non-empty repository path")
                linked = safe_relative(value, f"{relative}.{key}")
                require((ROOT / linked).is_file(), f"broken admission authority file link: {relative}.{key} -> {value}")
                checked_files += 1
            elif key in DIRECTORY_KEYS:
                require(isinstance(value, str) and value, f"{relative}.{key} must be a non-empty repository directory")
                linked = safe_relative(value, f"{relative}.{key}")
                require((ROOT / linked).is_dir(), f"broken admission authority directory link: {relative}.{key} -> {value}")
                checked_directories += 1
    print("Memory OS admission authority linkage validation PASS")
    print(f"contracts checked: {len(CONTRACTS)}")
    print(f"file links checked: {checked_files}")
    print(f"directory links checked: {checked_directories}")
    print("production decision: unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION AUTHORITY LINKAGE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
