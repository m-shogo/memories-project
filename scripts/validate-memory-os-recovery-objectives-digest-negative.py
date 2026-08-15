#!/usr/bin/env python3
"""Prove recovery-objective approval evidence stays byte-bound after registration."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
APPROVAL_DIR = ROOT / "docs/fixtures/memory-os-operability/recovery-objectives-approval"
APPROVAL_REF = "docs/fixtures/memory-os-operability/recovery-objectives-approval"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_recovery_objective_digest_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load recovery objective writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.APPROVAL_DIR = APPROVAL_DIR
    return module


def record() -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-recovery-objectives-record.v1",
        "objectiveId": "ro_negative_base",
        "scope": "PRODUCTION_RECOVERY_OBJECTIVES",
        "rpoSeconds": 60,
        "rtoSeconds": 120,
        "maximumObjectDatabaseSkewSeconds": 10,
        "rpoMeasurementMethod": "measure backup watermark to selected restore point",
        "rtoMeasurementMethod": "measure drill start to validated recovery completion",
        "skewMeasurementMethod": "compare restored database and object recovery point timestamps",
        "ownerRef": "contracts/operations/recovery-objectives-admission-contract.v1.json",
        "approvalEvidenceRefs": [
            f"{APPROVAL_REF}/recovery-owner.valid.json",
            f"{APPROVAL_REF}/operability.valid.json",
        ],
        "approvedAt": "2026-08-08T00:00:00Z",
        "supersedesObjectiveId": None,
        "productionEvidence": False,
        "productionReady": False,
    }


def expect_rejected(writer: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except writer.Fail:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def main() -> int:
    writer = load_writer()
    row = record()
    writer.validate_record(row)
    refs = row["approvalEvidenceRefs"]
    digests = {ref: writer.approval_sha256(ref) for ref in refs}
    baseline = {
        "schemaVersion": "memory-os-recovery-objectives-registry.v1",
        "appendOnly": True,
        "approvedObjectiveCount": 1,
        "currentObjectiveId": row["objectiveId"],
        "records": [row],
        "approvalEvidenceDigestsByObjectiveId": {row["objectiveId"]: digests},
        "productionEvidence": False,
        "productionReady": False,
        "limitations": ["synthetic digest-binding fixture only"],
    }
    writer.validate_registry_for_append(copy.deepcopy(baseline))
    print("PASS accept: exact approval bytes match append-only digest authority")

    missing_map = copy.deepcopy(baseline)
    missing_map.pop("approvalEvidenceDigestsByObjectiveId")
    expect_rejected(writer, "missing approval digest map", lambda: writer.validate_registry_for_append(missing_map))

    unknown_objective = copy.deepcopy(baseline)
    unknown_objective["approvalEvidenceDigestsByObjectiveId"]["ro_unknown_digest"] = dict(digests)
    expect_rejected(writer, "unknown objective in approval digest map", lambda: writer.validate_registry_for_append(unknown_objective))

    stale_digest = copy.deepcopy(baseline)
    stale_digest["approvalEvidenceDigestsByObjectiveId"][row["objectiveId"]][refs[0]] = "0" * 64
    expect_rejected(writer, "stale approval evidence digest", lambda: writer.validate_registry_for_append(stale_digest))

    approval_path = ROOT / refs[0]
    original = approval_path.read_bytes()
    try:
        approval_path.write_bytes(original + b" ")
        expect_rejected(writer, "approval evidence bytes changed after registration", lambda: writer.validate_registry_for_append(copy.deepcopy(baseline)))
    finally:
        approval_path.write_bytes(original)

    writer.validate_registry_for_append(copy.deepcopy(baseline))
    print("PASS restore: approval fixture restored byte-for-byte")
    print("production objective created: false")
    print("objective values invented/defaulted: false")
    print("production evidence: false")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVE DIGEST NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
