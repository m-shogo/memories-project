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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
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


def repo_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def review_payload(
    *,
    role: str,
    reviewer: str,
    decision_id: str = "brpr_negative_base",
    evidence_id: str = "brge_negative_candidate",
) -> dict[str, Any]:
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


def build_fixture(root: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    rationale = root / "rationale.txt"
    rationale.write_text("Synthetic negative-suite rationale only; not human production authority.\n", encoding="utf-8")
    specs = {
        "recoveryOwner": ("RECOVERY_OWNER", "reviewer_recovery_owner"),
        "security": ("SECURITY", "reviewer_security"),
        "operability": ("OPERABILITY", "reviewer_operability"),
    }
    paths: dict[str, Path] = {"rationale": rationale}
    for name, (role, reviewer) in specs.items():
        path = root / f"{name}.json"
        write_json(path, review_payload(role=role, reviewer=reviewer))
        paths[name] = path
    return {
        "schemaVersion": "memory-os-backup-restore-promotion-review-record.v2",
        "decisionId": "brpr_negative_base",
        "recoveryEvidenceId": "brge_negative_candidate",
        "decidedAt": "2026-08-08T00:00:00Z",
        "decision": "GO_RECOMMENDATION",
        "rationaleRef": repo_rel(rationale),
        "rationaleSha256": sha256(rationale),
        "recoveryOwnerReviewRef": repo_rel(paths["recoveryOwner"]),
        "recoveryOwnerReviewSha256": sha256(paths["recoveryOwner"]),
        "securityReviewRef": repo_rel(paths["security"]),
        "securityReviewSha256": sha256(paths["security"]),
        "operabilityReviewRef": repo_rel(paths["operability"]),
        "operabilityReviewSha256": sha256(paths["operability"]),
        "unresolvedFindings": [],
        "productionTrafficChanged": False,
        "productionCredentialsUsed": False,
        "productionEvidence": False,
        "productionReady": False,
    }, paths


def empty_registry() -> dict[str, Any]:
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
    require(WRITER.is_file() and VALIDATOR.is_file(), "promotion review authority scripts missing")
    writer = load_module(WRITER, "memory_os_promotion_review_writer_negative")
    validator = load_module(VALIDATOR, "memory_os_promotion_review_validator_negative")
    EXPECTED_FAILURE = writer.Fail

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

    contract = json.loads(writer.CONTRACT.read_text(encoding="utf-8"))
    require(
        contract.get("rules", {}).get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
        "promotion review transactional append contract guard missing",
    )
    print("PASS accept: promotion review transactional append contract guard")

    registry = empty_registry()
    writer.validate_registry_for_append(registry)
    print("PASS accept: empty append-only promotion registry authority")
    for name, mutate in (
        ("promotion registry schema drift", lambda value: value.__setitem__("schemaVersion", "memory-os-backup-restore-promotion-review-registry.v0")),
        ("promotion registry append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        ("promotion registry production-ready relabel", lambda value: value.__setitem__("productionReady", True)),
        ("promotion registry boolean registered count", lambda value: value.__setitem__("registeredReviewCount", False)),
        ("promotion registry boolean decision count", lambda value: value.__setitem__("goRecommendationCount", False)),
        ("empty promotion registry current pointer drift", lambda value: value.__setitem__("currentDecisionId", "brpr_impossible_current")),
        ("empty promotion registry latest pointer drift", lambda value: value.__setitem__("latestDecisionId", "brpr_impossible_latest")),
    ):
        value = copy.deepcopy(registry)
        mutate(value)
        expect_rejected(name, lambda value=value: writer.validate_registry_for_append(value))

    original_registry_path = writer.REGISTRY
    original_validate_registry = writer.validate_registry_for_append
    with tempfile.TemporaryDirectory(prefix="memory-os-promotion-review-append-rollback-") as registry_tmp:
        temp_registry = Path(registry_tmp) / "promotion-registry.json"
        write_json(temp_registry, registry)
        before = temp_registry.read_bytes()
        writer.REGISTRY = temp_registry
        writer.validate_registry_for_append = lambda value: (_ for _ in ()).throw(writer.Fail("synthetic post-append validation failure"))
        try:
            candidate = copy.deepcopy(registry)
            candidate["limitations"] = ["synthetic write that must be rolled back"]
            expect_rejected(
                "promotion registry post-append validation rollback",
                lambda: writer.write_registry_transactionally(candidate),
            )
            require(temp_registry.read_bytes() == before, "promotion registry bytes changed after rejected transactional append")
            print("PASS preserve: promotion registry append failure rolled back byte-for-byte")
        finally:
            writer.REGISTRY = original_registry_path
            writer.validate_registry_for_append = original_validate_registry

    require(writer.EVIDENCE_ROOT.is_dir(), "monitored backup/restore evidence namespace missing")
    with tempfile.TemporaryDirectory(prefix=".promotion-review-negative-", dir=writer.EVIDENCE_ROOT) as tmp:
        record, paths = build_fixture(Path(tmp))

        expect_rejected("no current final recovery candidate", lambda: writer.validate_record(copy.deepcopy(record)))
        try:
            expect_rejected("unexpected implementation TypeError", lambda: (_ for _ in ()).throw(TypeError("synthetic implementation fault")))
        except TypeError:
            print("PASS preserve: unexpected implementation TypeError is not normalized as domain rejection")
        else:
            raise Fail("unexpected implementation TypeError was accepted as valid rejection")

        expect_rejected("absolute review authority ref", lambda: writer.repo_ref(str((ROOT / "README.md").resolve()), "negative.absolute"))
        expect_rejected("parent-traversal review authority ref", lambda: writer.repo_ref("docs/../README.md", "negative.parent"))
        expect_rejected("review evidence outside monitored namespace", lambda: writer.promotion_evidence_ref("README.md", "negative.namespace"))

        real_root = writer.ROOT
        with tempfile.TemporaryDirectory(prefix="memory-os-promotion-review-path-negative-") as escaped_root:
            escaped = Path(escaped_root) / "escaped-review.md"
            escaped.symlink_to(ROOT / "README.md")
            writer.ROOT = Path(escaped_root)
            try:
                expect_rejected("review authority symlink escapes repository root", lambda: writer.repo_ref("escaped-review.md", "negative.symlink"))
            finally:
                writer.ROOT = real_root

        real_candidate = writer.recovery_candidate
        real_registered = writer.registered_recovery_evidence
        writer.recovery_candidate = lambda evidence_id: {"evidenceId": evidence_id}
        writer.registered_recovery_evidence = lambda evidence_id: {"evidenceId": evidence_id}
        try:
            valid = copy.deepcopy(record)
            writer.validate_record(valid)
            writer.validate_record(valid, require_current_candidate=False)
            print("PASS accept: isolated typed synthetic current and historical review")

            arbitrary = copy.deepcopy(valid)
            arbitrary["recoveryOwnerReviewRef"] = "README.md"
            arbitrary["recoveryOwnerReviewSha256"] = sha256(ROOT / "README.md")
            expect_rejected("arbitrary repository file cannot impersonate human review evidence", lambda: writer.validate_record(arbitrary))

            duplicate_ref = copy.deepcopy(valid)
            duplicate_ref["operabilityReviewRef"] = duplicate_ref["securityReviewRef"]
            duplicate_ref["operabilityReviewSha256"] = duplicate_ref["securityReviewSha256"]
            expect_rejected("review evidence reuse", lambda: writer.validate_record(duplicate_ref))

            rationale_reuse = copy.deepcopy(valid)
            rationale_reuse["rationaleRef"] = rationale_reuse["securityReviewRef"]
            rationale_reuse["rationaleSha256"] = rationale_reuse["securityReviewSha256"]
            expect_rejected("rationale reused as reviewer evidence", lambda: writer.validate_record(rationale_reuse))

            def mutate_review(path: Path, mutate: Callable[[dict[str, Any]], None]) -> str:
                payload = json.loads(path.read_text(encoding="utf-8"))
                mutate(payload)
                write_json(path, payload)
                return sha256(path)

            wrong_role = copy.deepcopy(valid)
            wrong_role["recoveryOwnerReviewSha256"] = mutate_review(paths["recoveryOwner"], lambda p: p.__setitem__("reviewRole", "OPERABILITY"))
            expect_rejected("review role substitution", lambda: writer.validate_record(wrong_role))
            write_json(paths["recoveryOwner"], review_payload(role="RECOVERY_OWNER", reviewer="reviewer_recovery_owner"))

            wrong_decision = copy.deepcopy(valid)
            wrong_decision["recoveryOwnerReviewSha256"] = mutate_review(paths["recoveryOwner"], lambda p: p.__setitem__("decisionId", "brpr_other_review"))
            expect_rejected("review decisionId binding mismatch", lambda: writer.validate_record(wrong_decision))
            write_json(paths["recoveryOwner"], review_payload(role="RECOVERY_OWNER", reviewer="reviewer_recovery_owner"))

            wrong_candidate = copy.deepcopy(valid)
            wrong_candidate["recoveryOwnerReviewSha256"] = mutate_review(paths["recoveryOwner"], lambda p: p.__setitem__("recoveryEvidenceId", "brge_other_candidate"))
            expect_rejected("review recoveryEvidenceId binding mismatch", lambda: writer.validate_record(wrong_candidate))
            write_json(paths["recoveryOwner"], review_payload(role="RECOVERY_OWNER", reviewer="reviewer_recovery_owner"))

            duplicate_reviewer = copy.deepcopy(valid)
            duplicate_reviewer["operabilityReviewSha256"] = mutate_review(paths["operability"], lambda p: p.__setitem__("reviewerPseudonym", "reviewer_security"))
            expect_rejected("human reviewer identity reuse", lambda: writer.validate_record(duplicate_reviewer))
            write_json(paths["operability"], review_payload(role="OPERABILITY", reviewer="reviewer_operability"))

            unapproved = copy.deepcopy(valid)
            unapproved["securityReviewSha256"] = mutate_review(paths["security"], lambda p: p.__setitem__("reviewResult", "DEFER"))
            expect_rejected("human review result not approved", lambda: writer.validate_record(unapproved))
            write_json(paths["security"], review_payload(role="SECURITY", reviewer="reviewer_security"))

            late = copy.deepcopy(valid)
            late["securityReviewSha256"] = mutate_review(paths["security"], lambda p: p.__setitem__("reviewedAt", "2026-08-09T00:00:00Z"))
            expect_rejected("human review post-dates promotion decision", lambda: writer.validate_record(late))
            write_json(paths["security"], review_payload(role="SECURITY", reviewer="reviewer_security"))

            automatic = copy.deepcopy(valid)
            automatic["securityReviewSha256"] = mutate_review(paths["security"], lambda p: p.__setitem__("automaticPromotion", True))
            expect_rejected("human review cannot authorize automatic promotion", lambda: writer.validate_record(automatic))
            write_json(paths["security"], review_payload(role="SECURITY", reviewer="reviewer_security"))

            digest_drift = copy.deepcopy(valid)
            paths["security"].write_text(paths["security"].read_text(encoding="utf-8") + "\n", encoding="utf-8")
            expect_rejected("human review payload changed after digest binding", lambda: writer.validate_record(digest_drift))
            write_json(paths["security"], review_payload(role="SECURITY", reviewer="reviewer_security"))

            rationale_drift = copy.deepcopy(valid)
            paths["rationale"].write_text("Mutated rationale after digest binding.\n", encoding="utf-8")
            expect_rejected("rationale changed after digest binding", lambda: writer.validate_record(rationale_drift))
            paths["rationale"].write_text("Synthetic negative-suite rationale only; not human production authority.\n", encoding="utf-8")

            go_findings = copy.deepcopy(valid)
            go_findings["unresolvedFindings"] = [{"findingId": "finding_open", "severity": "LOW", "status": "OPEN", "ownerRef": "README.md"}]
            expect_rejected("GO recommendation with unresolved finding", lambda: writer.validate_record(go_findings))
            defer_findings = copy.deepcopy(go_findings)
            defer_findings["decision"] = "DEFER"
            writer.validate_record(defer_findings)
            print("PASS accept: DEFER may preserve owned unresolved finding")

            for field, value, label in (
                ("productionTrafficChanged", True, "traffic change claimed by review"),
                ("productionCredentialsUsed", True, "production credentials claimed by review"),
                ("productionEvidence", True, "production evidence relabel"),
                ("productionReady", True, "production ready relabel"),
            ):
                changed = copy.deepcopy(valid)
                changed[field] = value
                expect_rejected(label, lambda changed=changed: writer.validate_record(changed))

            one = empty_registry()
            one.update({
                "registeredReviewCount": 1,
                "goRecommendationCount": 1,
                "latestDecisionId": valid["decisionId"],
                "currentDecisionId": valid["decisionId"],
                "records": [copy.deepcopy(valid)],
            })
            writer.validate_registry_for_append(one)
            print("PASS accept: latest historical review is current while candidate remains current")
            writer.recovery_candidate = lambda evidence_id: (_ for _ in ()).throw(writer.Fail("synthetic supersession"))
            expect_rejected("stale current pointer after candidate supersession", lambda: writer.validate_registry_for_append(copy.deepcopy(one)))
            revoked = copy.deepcopy(one)
            rows, current_id = writer.reconcile_current_decision(revoked)
            require(len(rows) == 1 and revoked["records"] == one["records"], "reconcile mutated historical review rows")
            require(current_id is None and revoked["currentDecisionId"] is None, "reconcile did not revoke current promotion authority")
            writer.validate_registry_for_append(revoked)
            print("PASS preserve: superseded review remains historical while current authority is revoked")
            corrupt = copy.deepcopy(revoked)
            corrupt["currentDecisionId"] = "brpr_unregistered_corrupt"
            expect_rejected("reconcile refuses corrupt current pointer", lambda: writer.reconcile_current_decision(corrupt))

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
    print("promotion evidence outside monitored namespace accepted: false")
    print("arbitrary repository file accepted as human review: false")
    print("review payload mutation accepted after digest binding: false")
    print("candidate bypass: false")
    print("historical review deleted on supersession: false")
    print("current promotion authority retained after supersession: false")
    print("review authority path escape accepted: false")
    print("promotion review lock substitution accepted: false")
    print("corrupt promotion registry accepted on append: false")
    print("post-append promotion registry validation failure persisted: false")
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