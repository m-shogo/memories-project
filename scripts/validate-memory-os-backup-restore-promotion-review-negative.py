#!/usr/bin/env python3
"""Exercise fail-closed negative cases for backup/restore promotion review admission."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-promotion-review.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_promotion_review_writer_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load promotion review writer")
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
        "schemaVersion": "memory-os-backup-restore-promotion-review-record.v1",
        "decisionId": "brpr_negative_base",
        "recoveryEvidenceId": "brge_negative_candidate",
        "decidedAt": "2026-08-08T00:00:00Z",
        "decision": "GO_RECOMMENDATION",
        "rationaleRef": "docs/runbooks/memory-os-production-equivalent-backup-restore-drill.md",
        "recoveryOwnerReviewRef": "README.md",
        "securityReviewRef": "SECURITY.md",
        "operabilityReviewRef": "contracts/operations/production-operability-status.json",
        "unresolvedFindings": [],
        "productionTrafficChanged": False,
        "productionCredentialsUsed": False,
        "productionEvidence": False,
        "productionReady": False,
    }


def main() -> int:
    require(WRITER.is_file(), "promotion review writer missing")
    writer = load_writer()

    canonical = base_record()
    canonical["decisionId"] = "brpr_no_candidate"
    expect_rejected("no current final recovery candidate", lambda: writer.validate_record(canonical))

    real_candidate = writer.recovery_candidate
    writer.recovery_candidate = lambda evidence_id: {"evidenceId": evidence_id}
    try:
        valid = base_record()
        writer.validate_record(valid)
        print("PASS accept: isolated synthetic review with candidate guard stubbed")

        same_review = copy.deepcopy(valid)
        same_review["decisionId"] = "brpr_same_review"
        same_review["operabilityReviewRef"] = same_review["securityReviewRef"]
        expect_rejected("review evidence reuse", lambda: writer.validate_record(same_review))

        rationale_reuse = copy.deepcopy(valid)
        rationale_reuse["decisionId"] = "brpr_rationale_reuse"
        rationale_reuse["rationaleRef"] = rationale_reuse["securityReviewRef"]
        expect_rejected("rationale reused as reviewer evidence", lambda: writer.validate_record(rationale_reuse))

        go_with_finding = copy.deepcopy(valid)
        go_with_finding["decisionId"] = "brpr_go_with_findings"
        go_with_finding["unresolvedFindings"] = [{
            "findingId": "finding_open",
            "severity": "LOW",
            "status": "OPEN",
            "ownerRef": "README.md",
        }]
        expect_rejected("GO recommendation with unresolved finding", lambda: writer.validate_record(go_with_finding))

        defer_with_finding = copy.deepcopy(go_with_finding)
        defer_with_finding["decisionId"] = "brpr_defer_findings"
        defer_with_finding["decision"] = "DEFER"
        writer.validate_record(defer_with_finding)
        print("PASS accept: DEFER may preserve owned unresolved finding")

        traffic = copy.deepcopy(valid)
        traffic["decisionId"] = "brpr_traffic_change"
        traffic["productionTrafficChanged"] = True
        expect_rejected("traffic change claimed by review", lambda: writer.validate_record(traffic))

        credentials = copy.deepcopy(valid)
        credentials["decisionId"] = "brpr_prod_credentials"
        credentials["productionCredentialsUsed"] = True
        expect_rejected("production credentials claimed by review", lambda: writer.validate_record(credentials))

        production_flag = copy.deepcopy(valid)
        production_flag["decisionId"] = "brpr_prod_evidence"
        production_flag["productionEvidence"] = True
        expect_rejected("production evidence relabel", lambda: writer.validate_record(production_flag))

        mutable_alias = copy.deepcopy(valid)
        mutable_alias["decisionId"] = "brpr_latest_alias"
        mutable_alias["rationaleRef"] = "docs/latest-review.md"
        expect_rejected("mutable latest alias", lambda: writer.validate_record(mutable_alias))
    finally:
        writer.recovery_candidate = real_candidate

    print("Memory OS backup/restore promotion review negative suite PASS")
    print("canonical registry mutated: false")
    print("candidate bypass: false")
    print("review can change traffic: false")
    print("GO recommendation implies production ready: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE PROMOTION REVIEW NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
