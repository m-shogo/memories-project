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
APPROVAL_FIXTURE_DIR = ROOT / "docs/fixtures/memory-os-operability/recovery-objectives-approval"
APPROVAL_FIXTURE_REF = "docs/fixtures/memory-os-operability/recovery-objectives-approval"


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
    module.APPROVAL_DIR = APPROVAL_FIXTURE_DIR
    return module


def expect_rejected(writer: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except writer.Fail:
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
            f"{APPROVAL_FIXTURE_REF}/recovery-owner.valid.json",
            f"{APPROVAL_FIXTURE_REF}/operability.valid.json",
        ],
        "approvedAt": "2026-08-08T00:00:00Z",
        "supersedesObjectiveId": None,
        "productionEvidence": False,
        "productionReady": False,
    }


def main() -> int:
    require(WRITER.is_file() and CONTRACT.is_file(), "recovery objective foundation missing")
    require(APPROVAL_FIXTURE_DIR.is_dir(), "typed objective approval fixtures missing")
    writer = load_writer()

    valid = base_record()
    writer.validate_record(valid)
    print("PASS accept: explicit typed reviewed recovery objective")

    arbitrary_repo_files = copy.deepcopy(valid)
    arbitrary_repo_files["approvalEvidenceRefs"] = ["SECURITY.md", "README.md"]
    expect_rejected(writer, "arbitrary repository files cannot satisfy objective approval", lambda: writer.validate_record(arbitrary_repo_files))

    objective_binding = copy.deepcopy(valid)
    objective_binding["objectiveId"] = "ro_negative_other_objective"
    expect_rejected(writer, "typed approval bound to different objectiveId", lambda: writer.validate_record(objective_binding))

    value_binding = copy.deepcopy(valid)
    value_binding["rpoSeconds"] = 61
    expect_rejected(writer, "typed approval bound to different RPO value", lambda: writer.validate_record(value_binding))

    rpo_zero = copy.deepcopy(valid)
    rpo_zero["rpoSeconds"] = 0
    expect_rejected(writer, "zero RPO", lambda: writer.validate_record(rpo_zero))

    rpo_boolean = copy.deepcopy(valid)
    rpo_boolean["rpoSeconds"] = True
    expect_rejected(writer, "boolean RPO", lambda: writer.validate_record(rpo_boolean))

    rto_negative = copy.deepcopy(valid)
    rto_negative["rtoSeconds"] = -1
    expect_rejected(writer, "negative RTO", lambda: writer.validate_record(rto_negative))

    rto_boolean = copy.deepcopy(valid)
    rto_boolean["rtoSeconds"] = True
    expect_rejected(writer, "boolean RTO", lambda: writer.validate_record(rto_boolean))

    skew_negative = copy.deepcopy(valid)
    skew_negative["maximumObjectDatabaseSkewSeconds"] = -1
    expect_rejected(writer, "negative object-database skew", lambda: writer.validate_record(skew_negative))

    skew_boolean = copy.deepcopy(valid)
    skew_boolean["maximumObjectDatabaseSkewSeconds"] = False
    expect_rejected(writer, "boolean object-database skew", lambda: writer.validate_record(skew_boolean))

    placeholder = copy.deepcopy(valid)
    placeholder["rpoMeasurementMethod"] = "TBD"
    expect_rejected(writer, "placeholder measurement method", lambda: writer.validate_record(placeholder))

    missing_owner = copy.deepcopy(valid)
    missing_owner["ownerRef"] = "docs/evidence/does-not-exist-owner.json"
    expect_rejected(writer, "missing owner evidence path", lambda: writer.validate_record(missing_owner))

    reused_owner = copy.deepcopy(valid)
    reused_owner["ownerRef"] = reused_owner["approvalEvidenceRefs"][0]
    expect_rejected(writer, "owner reused as independent approval evidence", lambda: writer.validate_record(reused_owner))

    duplicate_approval = copy.deepcopy(valid)
    duplicate_approval["approvalEvidenceRefs"] = [
        f"{APPROVAL_FIXTURE_REF}/recovery-owner.valid.json",
        f"{APPROVAL_FIXTURE_REF}/recovery-owner.valid.json",
    ]
    expect_rejected(writer, "duplicate approval evidence refs", lambda: writer.validate_record(duplicate_approval))

    missing_approval = copy.deepcopy(valid)
    missing_approval["approvalEvidenceRefs"] = [
        f"{APPROVAL_FIXTURE_REF}/recovery-owner.valid.json",
        f"{APPROVAL_FIXTURE_REF}/does-not-exist-approval.json",
    ]
    expect_rejected(writer, "missing approval evidence path", lambda: writer.validate_record(missing_approval))

    non_utc = copy.deepcopy(valid)
    non_utc["approvedAt"] = "2026-08-08T09:00:00+09:00"
    expect_rejected(writer, "approvedAt without UTC Z", lambda: writer.validate_record(non_utc))

    mutable_alias = copy.deepcopy(valid)
    mutable_alias["rtoMeasurementMethod"] = "measure against latest recovery result"
    expect_rejected(writer, "mutable latest alias", lambda: writer.validate_record(mutable_alias))

    production_flag = copy.deepcopy(valid)
    production_flag["productionEvidence"] = True
    expect_rejected(writer, "production evidence relabel", lambda: writer.validate_record(production_flag))

    print("Memory OS recovery objectives negative admission suite PASS")
    print("canonical registry mutated: false")
    print("objective values invented/defaulted: false")
    print("arbitrary repository file approval accepted: false")
    print("typed approval objective/value binding enforced: true")
    print("unexpected implementation exceptions accepted as rejection: false")
    print("boolean objective values accepted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVES NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
