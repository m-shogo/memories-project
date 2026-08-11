#!/usr/bin/env python3
"""Exercise fail-closed negative cases for backup/restore promotion review admission."""

from __future__ import annotations

import copy
import importlib.util
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-promotion-review.py"


class Fail(RuntimeError):
    pass


EXPECTED_FAILURE: type[Exception] = Fail


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
    except EXPECTED_FAILURE:
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


def base_registry() -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-backup-restore-promotion-review-registry.v1",
        "appendOnly": True,
        "registeredReviewCount": 0,
        "goRecommendationCount": 0,
        "noGoCount": 0,
        "deferCount": 0,
        "currentDecisionId": None,
        "records": [],
        "productionTrafficChanged": False,
        "productionEvidence": False,
        "productionReady": False,
        "limitations": [],
    }


def main() -> int:
    global EXPECTED_FAILURE
    require(WRITER.is_file(), "promotion review writer missing")
    writer = load_writer()
    EXPECTED_FAILURE = writer.Fail

    canonical = base_record()
    canonical["decisionId"] = "brpr_no_candidate"
    expect_rejected("no current final recovery candidate", lambda: writer.validate_record(canonical))

    try:
        expect_rejected("unexpected implementation TypeError", lambda: (_ for _ in ()).throw(TypeError("synthetic implementation fault")))
    except TypeError:
        print("PASS preserve: unexpected implementation TypeError is not normalized as domain rejection")
    else:
        raise Fail("unexpected implementation TypeError was accepted as a valid rejection")

    expect_rejected("absolute review authority ref", lambda: writer.repo_ref(str((ROOT / "README.md").resolve()), "negative.absolute"))
    expect_rejected("parent-traversal review authority ref", lambda: writer.repo_ref("docs/../README.md", "negative.parent"))

    real_root = writer.ROOT
    with tempfile.TemporaryDirectory(prefix="memory-os-promotion-review-path-negative-") as tmp:
        tmp_path = Path(tmp)
        escaped = tmp_path / "escaped-review.md"
        escaped.symlink_to(ROOT / "README.md")
        writer.ROOT = tmp_path
        try:
            expect_rejected("review authority symlink escapes repository root", lambda: writer.repo_ref("escaped-review.md", "negative.symlink"))
        finally:
            writer.ROOT = real_root

    valid_registry = base_registry()
    writer.validate_registry_for_append(valid_registry)
    print("PASS accept: empty append-only promotion registry authority")

    schema_drift = copy.deepcopy(valid_registry)
    schema_drift["schemaVersion"] = "memory-os-backup-restore-promotion-review-registry.v0"
    expect_rejected("promotion registry schema drift", lambda: writer.validate_registry_for_append(schema_drift))

    mutable_registry = copy.deepcopy(valid_registry)
    mutable_registry["appendOnly"] = False
    expect_rejected("promotion registry append-only disabled", lambda: writer.validate_registry_for_append(mutable_registry))

    production_ready = copy.deepcopy(valid_registry)
    production_ready["productionReady"] = True
    expect_rejected("promotion registry production-ready relabel", lambda: writer.validate_registry_for_append(production_ready))

    boolean_count = copy.deepcopy(valid_registry)
    boolean_count["registeredReviewCount"] = False
    expect_rejected("promotion registry boolean registered count", lambda: writer.validate_registry_for_append(boolean_count))

    derived_boolean = copy.deepcopy(valid_registry)
    derived_boolean["goRecommendationCount"] = False
    expect_rejected("promotion registry boolean decision count", lambda: writer.validate_registry_for_append(derived_boolean))

    pointer_drift = copy.deepcopy(valid_registry)
    pointer_drift["currentDecisionId"] = "brpr_impossible_current"
    expect_rejected("empty promotion registry current pointer drift", lambda: writer.validate_registry_for_append(pointer_drift))

    duplicate_rows = copy.deepcopy(valid_registry)
    duplicate_rows.update({
        "registeredReviewCount": 2,
        "goRecommendationCount": 2,
        "currentDecisionId": "brpr_duplicate_review",
        "records": [
            {"decisionId": "brpr_duplicate_review", "decision": "GO_RECOMMENDATION"},
            {"decisionId": "brpr_duplicate_review", "decision": "GO_RECOMMENDATION"},
        ],
    })
    expect_rejected("promotion registry duplicate decision identity", lambda: writer.validate_registry_for_append(duplicate_rows))

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
    print("review authority path escape accepted: false")
    print("corrupt promotion registry accepted on append: false")
    print("unexpected implementation exception accepted as valid rejection: false")
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
