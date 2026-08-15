#!/usr/bin/env python3
"""Exercise fail-closed negative cases for backup/restore promotion review admission."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-promotion-review.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-promotion-review.py"


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


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_promotion_review_validator_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load promotion review validator")
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def review_payload(*, role: str, reviewer: str, decision_id: str = "brpr_negative_base", evidence_id: str = "brge_negative_candidate") -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-backup-restore-promotion-review-evidence.v1",
        "decisionId": decision_id,
        "recoveryEvidenceId": evidence_id,
        "reviewRole": role,
        "reviewResult": "APPROVED",
        "reviewedAt": "2026-08-08T00:00:00Z",
        "reviewerPseudonym": reviewer,
        "productionTrafficChanged": False,
        "productionCredentialsUsed": False,
        "automaticPromotion": False,
    }


def fixture_record(root: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    root.mkdir(parents=True, exist_ok=True)
    rationale = root / "rationale.txt"
    rationale.write_text("Synthetic negative-suite rationale only; not human production authority.\n", encoding="utf-8")

    review_specs = {
        "recoveryOwner": ("RECOVERY_OWNER", "reviewer_recovery_owner"),
        "security": ("SECURITY", "reviewer_security"),
        "operability": ("OPERABILITY", "reviewer_operability"),
    }
    paths: dict[str, Path] = {"rationale": rationale}
    for name, (role, reviewer) in review_specs.items():
        path = root / f"{name}.json"
        write_json(path, review_payload(role=role, reviewer=reviewer))
        paths[name] = path

    record = {
        "schemaVersion": "memory-os-backup-restore-promotion-review-record.v2",
        "decisionId": "brpr_negative_base",
        "recoveryEvidenceId": "brge_negative_candidate",
        "decidedAt": "2026-08-08T00:00:00Z",
        "decision": "GO_RECOMMENDATION",
        "rationaleRef": relative(rationale),
        "rationaleSha256": sha256(rationale),
        "recoveryOwnerReviewRef": relative(paths["recoveryOwner"]),
        "recoveryOwnerReviewSha256": sha256(paths["recoveryOwner"]),
        "securityReviewRef": relative(paths["security"]),
        "securityReviewSha256": sha256(paths["security"]),
        "operabilityReviewRef": relative(paths["operability"]),
        "operabilityReviewSha256": sha256(paths["operability"]),
        "unresolvedFindings": [],
        "productionTrafficChanged": False,
        "productionCredentialsUsed": False,
        "productionEvidence": False,
        "productionReady": False,
    }
    return record, paths


def base_registry() -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-backup-restore-promotion-review-registry.v1",
        "appendOnly": True,
        "registeredReviewCount": 0,
        "goRecommendationCount": 0,
        "noGoCount": 0,
        "deferCount": 0,
        "latestDecisionId": None,
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
    require(VALIDATOR.is_file(), "promotion review validator missing")
    writer = load_writer()
    EXPECTED_FAILURE = writer.Fail

    validator = load_validator()
    original_lock = writer.LOCK
    original_load_writer = validator.load_writer
    try:
        writer.LOCK = ROOT / "contracts/operations/.backup-restore-generation-evidence.lock"
        validator.load_writer = lambda: writer
        try:
            validator.main()
        except validator.Fail as exc:
            require("promotion review writer append lock authority drift" in str(exc), f"unexpected promotion lock rejection: {exc}")
            print("PASS reject: promotion review append lock authority substitution")
        else:
            raise Fail("promotion review append lock substitution unexpectedly accepted")
    finally:
        writer.LOCK = original_lock
        validator.load_writer = original_load_writer

    with tempfile.TemporaryDirectory(prefix=".promotion-review-negative-", dir=ROOT) as tmp:
        fixture_root = Path(tmp)
        canonical, paths = fixture_record(fixture_root)

        no_candidate = copy.deepcopy(canonical)
        expect_rejected("no current final recovery candidate", lambda: writer.validate_record(no_candidate))
        try:
            expect_rejected("unexpected implementation TypeError", lambda: (_ for _ in ()).throw(TypeError("synthetic implementation fault")))
        except TypeError:
            print("PASS preserve: unexpected implementation TypeError is not normalized as domain rejection")
        else:
            raise Fail("unexpected implementation TypeError was accepted as a valid rejection")
        expect_rejected("absolute review authority ref", lambda: writer.repo_ref(str((ROOT / "README.md").resolve()), "negative.absolute"))
        expect_rejected("parent-traversal review authority ref", lambda: writer.repo_ref("docs/../README.md", "negative.parent"))
        real_root = writer.ROOT
        with tempfile.TemporaryDirectory(prefix="memory-os-promotion-review-path-negative-") as path_tmp:
            tmp_path = Path(path_tmp)
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
        latest_pointer_drift = copy.deepcopy(valid_registry)
        latest_pointer_drift["latestDecisionId"] = "brpr_impossible_latest"
        expect_rejected("empty promotion registry latest pointer drift", lambda: writer.validate_registry_for_append(latest_pointer_drift))

        real_candidate = writer.recovery_candidate
        real_registered = writer.registered_recovery_evidence
        writer.recovery_candidate = lambda evidence_id: {"evidenceId": evidence_id}
        writer.registered_recovery_evidence = lambda evidence_id: {"evidenceId": evidence_id}
        try:
            valid = copy.deepcopy(canonical)
            writer.validate_record(valid)
            writer.validate_record(valid, require_current_candidate=False)
            print("PASS accept: isolated typed synthetic current and historical review")

            arbitrary_review = copy.deepcopy(valid)
            arbitrary_review["recoveryOwnerReviewRef"] = "README.md"
            arbitrary_review["recoveryOwnerReviewSha256"] = sha256(ROOT / "README.md")
            expect_rejected("arbitrary repository file cannot impersonate human review evidence", lambda: writer.validate_record(arbitrary_review))

            same_review = copy.deepcopy(valid)
            same_review["operabilityReviewRef"] = same_review["securityReviewRef"]
            same_review["operabilityReviewSha256"] = same_review["securityReviewSha256"]
            expect_rejected("review evidence reuse", lambda: writer.validate_record(same_review))
            rationale_reuse = copy.deepcopy(valid)
            rationale_reuse["rationaleRef"] = rationale_reuse["securityReviewRef"]
            rationale_reuse["rationaleSha256"] = rationale_reuse["securityReviewSha256"]
            expect_rejected("rationale reused as reviewer evidence", lambda: writer.validate_record(rationale_reuse))

            wrong_role_payload = review_payload(role="OPERABILITY", reviewer="reviewer_recovery_owner")
            write_json(paths["recoveryOwner"], wrong_role_payload)
            wrong_role = copy.deepcopy(valid)
            wrong_role["recoveryOwnerReviewSha256"] = sha256(paths["recoveryOwner"])
            expect_rejected("review role substitution", lambda: writer.validate_record(wrong_role))
            write_json(paths["recoveryOwner"], review_payload(role="RECOVERY_OWNER", reviewer="reviewer_recovery_owner"))

            wrong_decision_payload = review_payload(role="RECOVERY_OWNER", reviewer="reviewer_recovery_owner", decision_id="brpr_other_review")
            write_json(paths["recoveryOwner"], wrong_decision_payload)
            wrong_decision = copy.deepcopy(valid)
            wrong_decision["recoveryOwnerReviewSha256"] = sha256(paths["recoveryOwner"])
            expect_rejected("review decisionId binding mismatch", lambda: writer.validate_record(wrong_decision))
            write_json(paths["recoveryOwner"], review_payload(role="RECOVERY_OWNER", reviewer="reviewer_recovery_owner"))

            wrong_candidate_payload = review_payload(role="RECOVERY_OWNER", reviewer="reviewer_recovery_owner", evidence_id="brge_other_candidate")
            write_json(paths["recoveryOwner"], wrong_candidate_payload)
            wrong_candidate = copy.deepcopy(valid)
            wrong_candidate["recoveryOwnerReviewSha256"] = sha256(paths["recoveryOwner"])
            expect_rejected("review recoveryEvidenceId binding mismatch", lambda: writer.validate_record(wrong_candidate))
            write_json(paths["recoveryOwner"], review_payload(role="RECOVERY_OWNER", reviewer="reviewer_recovery_owner"))

            duplicate_reviewer_payload = review_payload(role="OPERABILITY", reviewer="reviewer_security")
            write_json(paths["operability"], duplicate_reviewer_payload)
            duplicate_reviewer = copy.deepcopy(valid)
            duplicate_reviewer["operabilityReviewSha256"] = sha256(paths["operability"])
            expect_rejected("human reviewer identity reuse", lambda: writer.validate_record(duplicate_reviewer))
            write_json(paths["operability"], review_payload(role="OPERABILITY", reviewer="reviewer_operability"))

            unapproved_payload = review_payload(role="SECURITY", reviewer="reviewer_security")
            unapproved_payload["reviewResult"] = "DEFER"
            write_json(paths["security"], unapproved_payload)
            unapproved = copy.deepcopy(valid)
            unapproved["securityReviewSha256"] = sha256(paths["security"])
            expect_rejected("human review result not approved", lambda: writer.validate_record(unapproved))
            write_json(paths["security"], review_payload(role="SECURITY", reviewer="reviewer_security"))

            late_payload = review_payload(role="SECURITY", reviewer="reviewer_security")
            late_payload["reviewedAt"] = "2026-08-09T00:00:00Z"
            write_json(paths["security"], late_payload)
            late_review = copy.deepcopy(valid)
            late_review["securityReviewSha256"] = sha256(paths["security"])
            expect_rejected("human review post-dates promotion decision", lambda: writer.validate_record(late_review))
            write_json(paths["security"], review_payload(role="SECURITY", reviewer="reviewer_security"))

            automatic_payload = review_payload(role="SECURITY", reviewer="reviewer_security")
            automatic_payload["automaticPromotion"] = True
            write_json(paths["security"], automatic_payload)
            automatic_review = copy.deepcopy(valid)
            automatic_review["securityReviewSha256"] = sha256(paths["security"])
            expect_rejected("human review cannot authorize automatic promotion", lambda: writer.validate_record(automatic_review))
            write_json(paths["security"], review_payload(role="SECURITY", reviewer="reviewer_security"))

            digest_mismatch = copy.deepcopy(valid)
            paths["security"].write_text(paths["security"].read_text(encoding="utf-8") + "\n", encoding="utf-8")
            expect_rejected("human review payload changed after digest binding", lambda: writer.validate_record(digest_mismatch))
            write_json(paths["security"], review_payload(role="SECURITY", reviewer="reviewer_security"))

            rationale_digest_mismatch = copy.deepcopy(valid)
            paths["rationale"].write_text("Mutated rationale after digest binding.\n", encoding="utf-8")
            expect_rejected("rationale changed after digest binding", lambda: writer.validate_record(rationale_digest_mismatch))
            paths["rationale"].write_text("Synthetic negative-suite rationale only; not human production authority.\n", encoding="utf-8")

            go_with_finding = copy.deepcopy(valid)
            go_with_finding["unresolvedFindings"] = [{"findingId": "finding_open", "severity": "LOW", "status": "OPEN", "ownerRef": "README.md"}]
            expect_rejected("GO recommendation with unresolved finding", lambda: writer.validate_record(go_with_finding))
            defer_with_finding = copy.deepcopy(go_with_finding)
            defer_with_finding["decision"] = "DEFER"
            writer.validate_record(defer_with_finding)
            print("PASS accept: DEFER may preserve owned unresolved finding")
            traffic = copy.deepcopy(valid)
            traffic["productionTrafficChanged"] = True
            expect_rejected("traffic change claimed by review", lambda: writer.validate_record(traffic))
            credentials = copy.deepcopy(valid)
            credentials["productionCredentialsUsed"] = True
            expect_rejected("production credentials claimed by review", lambda: writer.validate_record(credentials))
            production_flag = copy.deepcopy(valid)
            production_flag["productionEvidence"] = True
            expect_rejected("production evidence relabel", lambda: writer.validate_record(production_flag))
            mutable_alias = copy.deepcopy(valid)
            mutable_alias["rationaleRef"] = "docs/latest-review.md"
            expect_rejected("mutable latest alias", lambda: writer.validate_record(mutable_alias))

            one = base_registry()
            one.update({"registeredReviewCount": 1, "goRecommendationCount": 1, "latestDecisionId": valid["decisionId"], "currentDecisionId": valid["decisionId"], "records": [copy.deepcopy(valid)]})
            writer.validate_registry_for_append(one)
            print("PASS accept: latest historical review is current while candidate remains current")
            writer.recovery_candidate = lambda evidence_id: (_ for _ in ()).throw(writer.Fail("synthetic supersession"))
            expect_rejected("stale current pointer after candidate supersession", lambda: writer.validate_registry_for_append(copy.deepcopy(one)))
            revoked = copy.deepcopy(one)
            rows, current_id = writer.reconcile_current_decision(revoked)
            require(len(rows) == 1 and revoked["records"] == one["records"], "reconcile mutated historical review rows")
            require(revoked["latestDecisionId"] == valid["decisionId"], "reconcile changed latest historical decision")
            require(current_id is None and revoked["currentDecisionId"] is None, "reconcile did not revoke current promotion authority")
            writer.validate_registry_for_append(revoked)
            print("PASS preserve: superseded review remains historical while current authority is revoked")
            corrupt_current = copy.deepcopy(revoked)
            corrupt_current["currentDecisionId"] = "brpr_unregistered_corrupt"
            expect_rejected("reconcile refuses corrupt current pointer", lambda: writer.reconcile_current_decision(corrupt_current))
            writer.recovery_candidate = lambda evidence_id: (_ for _ in ()).throw(TypeError("synthetic current predicate fault"))
            try:
                writer.review_current(valid)
            except TypeError:
                print("PASS preserve: unexpected current-predicate TypeError surfaces")
            else:
                raise Fail("unexpected current-predicate TypeError was normalized into revocation")
        finally:
            writer.recovery_candidate = real_candidate
            writer.registered_recovery_evidence = real_registered

    print("Memory OS backup/restore promotion review negative suite PASS")
    print("canonical registry mutated: false")
    print("synthetic typed review evidence persisted: false")
    print("arbitrary repository file accepted as human review: false")
    print("review payload mutation accepted after digest binding: false")
    print("candidate bypass: false")
    print("historical review deleted on supersession: false")
    print("current promotion authority retained after supersession: false")
    print("review authority path escape accepted: false")
    print("promotion review lock substitution accepted: false")
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