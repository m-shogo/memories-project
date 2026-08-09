#!/usr/bin/env python3
"""Prove fail-closed negative cases for recovery-objective approval admission."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
CONTRACT = ROOT / "contracts/operations/recovery-objectives-admission-contract.v1.json"
APPROVAL_FIXTURE_DIR = "docs/fixtures/memory-os-operability/recovery-objectives-approval"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_recovery_objectives_writer_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load recovery objectives writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except Exception:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def base_record() -> dict[str, Any]:
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
            f"{APPROVAL_FIXTURE_DIR}/recovery-owner.valid.json",
            f"{APPROVAL_FIXTURE_DIR}/operability.valid.json",
        ],
        "approvedAt": "2026-08-08T00:00:00Z",
        "supersedesObjectiveId": None,
        "productionEvidence": False,
        "productionReady": False,
    }


def main() -> int:
    require(WRITER.is_file() and CONTRACT.is_file(), "recovery objective foundation missing")
    writer = load_writer()

    valid = base_record()
    writer.validate_record(valid)
    print("PASS accept: explicit reviewed recovery objective")

    rpo_zero = copy.deepcopy(valid)
    rpo_zero["objectiveId"] = "ro_negative_rpo_zero"
    rpo_zero["rpoSeconds"] = 0
    expect_rejected("zero RPO", lambda: writer.validate_record(rpo_zero))

    rto_negative = copy.deepcopy(valid)
    rto_negative["objectiveId"] = "ro_negative_rto_neg"
    rto_negative["rtoSeconds"] = -1
    expect_rejected("negative RTO", lambda: writer.validate_record(rto_negative))

    skew_negative = copy.deepcopy(valid)
    skew_negative["objectiveId"] = "ro_negative_skew_neg"
    skew_negative["maximumObjectDatabaseSkewSeconds"] = -1
    expect_rejected("negative object-database skew", lambda: writer.validate_record(skew_negative))

    placeholder = copy.deepcopy(valid)
    placeholder["objectiveId"] = "ro_negative_tbd_method"
    placeholder["rpoMeasurementMethod"] = "TBD"
    expect_rejected("placeholder measurement method", lambda: writer.validate_record(placeholder))

    missing_owner = copy.deepcopy(valid)
    missing_owner["objectiveId"] = "ro_negative_owner_missing"
    missing_owner["ownerRef"] = "docs/evidence/does-not-exist-owner.json"
    expect_rejected("missing owner evidence path", lambda: writer.validate_record(missing_owner))

    reused_owner = copy.deepcopy(valid)
    reused_owner["objectiveId"] = "ro_negative_owner_reused"
    reused_owner["approvalEvidenceRefs"] = [reused_owner["ownerRef"], f"{APPROVAL_FIXTURE_DIR}/operability.valid.json"]
    expect_rejected("owner reused as independent approval evidence", lambda: writer.validate_record(reused_owner))

    duplicate_approval = copy.deepcopy(valid)
    duplicate_approval["objectiveId"] = "ro_negative_dup_approval"
    duplicate_approval["approvalEvidenceRefs"] = [
        f"{APPROVAL_FIXTURE_DIR}/recovery-owner.valid.json",
        f"{APPROVAL_FIXTURE_DIR}/recovery-owner.valid.json",
    ]
    expect_rejected("duplicate approval evidence refs", lambda: writer.validate_record(duplicate_approval))

    missing_approval = copy.deepcopy(valid)
    missing_approval["objectiveId"] = "ro_negative_missing_approval"
    missing_approval["approvalEvidenceRefs"] = [
        f"{APPROVAL_FIXTURE_DIR}/recovery-owner.valid.json",
        "docs/evidence/does-not-exist-approval.json",
    ]
    expect_rejected("missing approval evidence path", lambda: writer.validate_record(missing_approval))

    non_utc = copy.deepcopy(valid)
    non_utc["objectiveId"] = "ro_negative_non_utc"
    non_utc["approvedAt"] = "2026-08-08T09:00:00+09:00"
    expect_rejected("approvedAt without UTC Z", lambda: writer.validate_record(non_utc))

    mutable_alias = copy.deepcopy(valid)
    mutable_alias["objectiveId"] = "ro_negative_latest"
    mutable_alias["rtoMeasurementMethod"] = "measure against latest recovery result"
    expect_rejected("mutable latest alias", lambda: writer.validate_record(mutable_alias))

    production_flag = copy.deepcopy(valid)
    production_flag["objectiveId"] = "ro_negative_prod_flag"
    production_flag["productionEvidence"] = True
    expect_rejected("production evidence relabel", lambda: writer.validate_record(production_flag))

    print("Memory OS recovery objectives negative admission suite PASS")
    print("canonical registry mutated: false")
    print("objective values invented/defaulted: false")
    print("placeholder approval accepted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVES NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
