#!/usr/bin/env python3
"""Validate append-only human backup/restore promotion review authority."""

from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-promotion-review-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/backup-restore-promotion-review-registry.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
TYPED_REGISTRY_REL = Path("contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json")
INVENTORY_REL = Path("contracts/operations/operability-admission-inventory.v1.json")
WRITER_REL = Path("scripts/register-memory-os-backup-restore-promotion-review.py")
GEN_WRITER_REL = Path("scripts/register-memory-os-backup-restore-generation-evidence.py")
EXPECTED_EVIDENCE_ROOT_REL = Path("docs/evidence/backup-restore")
EXPECTED_LOCK_REL = Path("contracts/operations/.backup-restore-promotion-review.lock")
NEGATIVE_REL = Path("scripts/validate-memory-os-backup-restore-promotion-review-negative.py")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
TYPED_REGISTRY = ROOT / TYPED_REGISTRY_REL
INVENTORY = ROOT / INVENTORY_REL
WRITER = ROOT / WRITER_REL
GEN_WRITER = ROOT / GEN_WRITER_REL
EXPECTED_EVIDENCE_ROOT = ROOT / EXPECTED_EVIDENCE_ROOT_REL
EXPECTED_LOCK = ROOT / EXPECTED_LOCK_REL
NEGATIVE = ROOT / NEGATIVE_REL
EXPECTED_RECORD_SCHEMA = "memory-os-backup-restore-promotion-review-record.v2"
EXPECTED_REVIEW_SCHEMA = "memory-os-backup-restore-promotion-review-evidence.v1"
EXPECTED_REVIEW_FIELDS = {
    "schemaVersion", "decisionId", "recoveryEvidenceId", "reviewRole", "reviewResult",
    "reviewedAt", "reviewerPseudonym", "productionTrafficChanged",
    "productionCredentialsUsed", "automaticPromotion",
}
EXPECTED_REVIEW_ROLES = {
    "recoveryOwnerReviewRef": "RECOVERY_OWNER",
    "securityReviewRef": "SECURITY",
    "operabilityReviewRef": "OPERABILITY",
}
EXPECTED_RECORD_FIELDS = {
    "schemaVersion", "decisionId", "recoveryEvidenceId", "decidedAt", "decision",
    "rationaleRef", "rationaleSha256", "recoveryOwnerReviewRef", "recoveryOwnerReviewSha256",
    "securityReviewRef", "securityReviewSha256", "operabilityReviewRef", "operabilityReviewSha256",
    "unresolvedFindings", "productionTrafficChanged", "productionCredentialsUsed",
    "productionEvidence", "productionReady",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file() and not path.is_symlink(),
        f"{field} authority drift",
    )
    return path


def require_exact_repo_dir(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_dir() and not path.is_symlink(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "promotion review contract"),
        (REGISTRY, REGISTRY_REL, "promotion review registry"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "generation recovery evidence registry"),
        (TYPED_REGISTRY, TYPED_REGISTRY_REL, "typed non-resurrection registry"),
        (INVENTORY, INVENTORY_REL, "operability admission inventory"),
        (WRITER, WRITER_REL, "promotion review writer"),
        (GEN_WRITER, GEN_WRITER_REL, "generation recovery evidence writer"),
        (NEGATIVE, NEGATIVE_REL, "promotion review negative validator"),
    ):
        require_exact_repo_file(path, expected, field)
    require_exact_repo_dir(EXPECTED_EVIDENCE_ROOT, EXPECTED_EVIDENCE_ROOT_REL, "promotion review evidence namespace")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer():
    require_exact_repo_file(WRITER, WRITER_REL, "promotion review writer")
    spec = importlib.util.spec_from_file_location("memory_os_promotion_review_writer_validator", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load promotion review writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_writer_cli_authority_boundary(writer) -> None:
    main_source = inspect.getsource(writer.main)
    guard_index = main_source.find("require_cli_authorities()")
    parser_index = main_source.find("argparse.ArgumentParser")
    require(guard_index >= 0, "promotion review CLI does not enforce canonical authority guard")
    require(parser_index >= 0 and guard_index < parser_index, "promotion review CLI authority guard must run before argument parsing")

    substitutions = {
        "CONTRACT": INVENTORY,
        "REGISTRY": GEN_REGISTRY,
        "GEN_REGISTRY": TYPED_REGISTRY,
        "GEN_WRITER": NEGATIVE,
        "EVIDENCE_ROOT": ROOT / "docs/evidence/recovery-objectives/approvals",
        "LOCK": CONTRACT,
    }
    for name, alternate in substitutions.items():
        original = getattr(writer, name)
        setattr(writer, name, alternate)
        try:
            try:
                writer.require_cli_authorities()
            except writer.Fail:
                pass
            else:
                raise Fail(f"promotion review CLI accepted substituted authority: {name}")
        finally:
            setattr(writer, name, original)
    try:
        writer.require_cli_authorities()
    except writer.Fail as exc:
        raise Fail(f"canonical promotion review CLI authority rejected: {exc}") from exc


def inventory_area(inventory: dict[str, Any], area_id: str) -> dict[str, Any]:
    rows = inventory.get("areas")
    require(isinstance(rows, list), "operability inventory areas missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("id") == area_id]
    require(len(matches) == 1, f"operability inventory area missing/duplicate: {area_id}")
    return matches[0]


def main() -> int:
    enforce_runtime_authorities()
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generation = load(GEN_REGISTRY)
    typed = load(TYPED_REGISTRY)
    inventory = load(INVENTORY)
    writer = load_writer()
    require(getattr(writer, "CONTRACT", None) == CONTRACT, "promotion review writer contract authority drift")
    require(getattr(writer, "REGISTRY", None) == REGISTRY, "promotion review writer registry authority drift")
    require(getattr(writer, "GEN_REGISTRY", None) == GEN_REGISTRY, "promotion review writer generation registry authority drift")
    require(getattr(writer, "GEN_WRITER", None) == GEN_WRITER, "promotion review candidate writer authority drift")
    require(getattr(writer, "EVIDENCE_ROOT", None) == EXPECTED_EVIDENCE_ROOT, "promotion review evidence namespace drift")
    require(getattr(writer, "REVIEW_EVIDENCE_SCHEMA", None) == EXPECTED_REVIEW_SCHEMA, "promotion review writer evidence schema drift")
    require(getattr(writer, "REVIEW_RESULT", None) == "APPROVED", "promotion review writer approval authority drift")
    writer_lock = getattr(writer, "LOCK", None)
    require(writer_lock == EXPECTED_LOCK, "promotion review writer append lock authority drift")
    require(writer_lock.parent == REGISTRY.parent, "promotion review append lock must share registry authority directory")
    require_writer_cli_authority_boundary(writer)
    writer.canonical_repo_file(CONTRACT, "promotion review contract")
    writer.canonical_repo_file(REGISTRY, "promotion review registry")
    writer.canonical_repo_file(GEN_REGISTRY, "generation recovery evidence registry")
    writer.canonical_repo_file(GEN_WRITER, "generation recovery evidence writer")
    require_exact_repo_dir(EXPECTED_EVIDENCE_ROOT, EXPECTED_EVIDENCE_ROOT_REL, "promotion review evidence namespace")

    require(contract.get("schemaVersion") == "memory-os-backup-restore-promotion-review-contract.v1", "promotion review contract schema drift")
    require(contract.get("recordSchemaVersion") == EXPECTED_RECORD_SCHEMA, "promotion review record schema authority drift")
    require(contract.get("reviewEvidenceSchemaVersion") == EXPECTED_REVIEW_SCHEMA, "promotion review evidence schema authority drift")
    require(contract.get("reviewEvidenceRoot") == str(EXPECTED_EVIDENCE_ROOT.relative_to(ROOT)), "promotion review evidence root contract drift")
    record_fields = contract.get("requiredRecordFields")
    require(isinstance(record_fields, list) and len(record_fields) == len(set(record_fields)) and set(record_fields) == EXPECTED_RECORD_FIELDS, "promotion review record field authority drift")
    review_fields = contract.get("requiredReviewEvidenceFields")
    require(isinstance(review_fields, list) and len(review_fields) == len(set(review_fields)) and set(review_fields) == EXPECTED_REVIEW_FIELDS, "promotion review evidence field authority drift")
    require(contract.get("reviewRoles") == EXPECTED_REVIEW_ROLES, "promotion review role authority drift")
    refs = {
        "registry": REGISTRY,
        "generationEvidenceRegistry": GEN_REGISTRY,
        "typedNonResurrectionRegistry": TYPED_REGISTRY,
        "writer": WRITER,
        "validator": Path("scripts/validate-memory-os-backup-restore-promotion-review.py"),
        "negativeAdmissionValidator": NEGATIVE,
        "workflow": Path(".github/workflows/backup-restore-promotion-review.yml"),
    }
    for field, path in refs.items():
        expected = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
        require(contract.get(field) == expected, f"promotion review ref drift: {field}")
        require((ROOT / expected).is_file(), f"promotion review artifact missing: {expected}")
    rules = contract.get("rules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "promotion review rules must remain fail-closed")
    for rule in (
        "promotionEvidenceMustRemainInsideMonitoredNamespace",
        "threeDistinctHumanReviewerPseudonymsRequired",
        "typedHumanReviewEvidenceRequired",
        "humanReviewMustBindDecisionId",
        "humanReviewMustBindRecoveryEvidenceId",
        "humanReviewRoleMustMatchReference",
        "humanReviewMustBeApproved",
        "humanReviewMustNotPostdateDecision",
        "humanReviewPayloadSha256BindingRequired",
        "rationalePayloadSha256BindingRequired",
    ):
        require(rules.get(rule) is True, f"typed promotion review rule missing: {rule}")
    decisions = contract.get("decisionValues")
    require(isinstance(decisions, list) and set(decisions) == {"GO_RECOMMENDATION", "NO_GO", "DEFER"}, "promotion review decision values drift")

    rows = writer.validate_registry_for_append(registry)
    count = registry.get("registeredReviewCount")
    go_count = registry.get("goRecommendationCount")
    no_go_count = registry.get("noGoCount")
    defer_count = registry.get("deferCount")
    latest_id = registry.get("latestDecisionId")
    current_id = registry.get("currentDecisionId")
    candidate_count = generation.get("productionEquivalentRecoveryCandidateCount")
    typed_covered = typed.get("candidateCoveredCount")
    require(valid_count(candidate_count), "recovery candidate count invalid")
    require(valid_count(typed_covered), "typed candidate coverage count invalid")
    require(candidate_count == typed_covered, "promotion review requires typed-final candidate count coherence")
    if current_id is not None:
        require(candidate_count > 0, "current promotion review cannot exist without a current final recovery candidate")
        require(current_id == latest_id, "only the latest historical review may hold current promotion authority")
    if candidate_count == 0:
        require(current_id is None, "zero final recovery candidates requires revoked current promotion authority")

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "promotion review currentBoundary missing")
    expected = {
        "registeredReviewCount": count,
        "goRecommendationCount": go_count,
        "noGoCount": no_go_count,
        "deferCount": defer_count,
        "latestDecisionId": latest_id,
        "currentDecisionId": current_id,
    }
    for field, value in expected.items():
        require(boundary.get(field) == value, f"promotion review boundary drift: {field}")
    require(boundary.get("productionTrafficChanged") is False and boundary.get("productionEvidence") is False and boundary.get("productionReady") is False and boundary.get("productionDecision") == "NO_GO", "promotion review boundary cannot promote production")

    inventory_review_completed = current_id is not None
    backup_area = inventory_area(inventory, "OPS-P0-007")
    require(inventory.get("productionDecision") == "NO_GO", "operability inventory production decision drift")
    require(inventory.get("humanProductionPromotionReviewCompleted") is inventory_review_completed, "operability inventory human promotion review must derive from current promotion-review registry authority")
    require(backup_area.get("humanProductionPromotionReviewCompleted") is inventory_review_completed, "OPS-P0-007 inventory human promotion review must derive from current promotion-review registry authority")
    require(inventory.get("humanProductionPromotionAuthorized") is False, "promotion review cannot authorize production in operability inventory")
    require(backup_area.get("humanProductionPromotionAuthorized") is False, "promotion review cannot authorize production in OPS-P0-007 inventory")

    require_exact_repo_file(NEGATIVE, NEGATIVE_REL, "promotion review negative validator")
    completed = subprocess.run([sys.executable, str(NEGATIVE)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"promotion review negative suite failed:\n{completed.stdout[-7000:]}{completed.stderr[-7000:]}")
    print("Memory OS backup/restore promotion review validation PASS")
    print("promotion review validator canonical runtime authorities enforced: true")
    print(f"final recovery candidates: {candidate_count}")
    print(f"registered historical promotion reviews: {count}")
    print(f"GO/NO_GO/DEFER: {go_count}/{no_go_count}/{defer_count}")
    print(f"latest historical decision: {latest_id}")
    print(f"current promotion authority decision: {current_id}")
    print("historical review/current authority separation: PASS")
    print("typed human review evidence schema authority: PASS")
    print("typed human review role authority: PASS")
    print("human promotion evidence namespace monitored: true")
    print("human review payload digest binding required: true")
    print("rationale payload digest binding required: true")
    print("promotion review candidate writer identity canonical: true")
    print("promotion review append lock authority canonical: true")
    print("promotion review CLI authority substitutions accepted: false")
    print("operability inventory current human review source: promotion-review registry")
    print("review changes production traffic: false")
    print("review creates production ready: false")
    print("review authorizes production: false")
    print("negative admission suite: PASS")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        if isinstance(exc, RuntimeError) and exc.__class__.__name__ == "Fail":
            print(f"BACKUP RESTORE PROMOTION REVIEW VALIDATION FAILED: {exc}", file=sys.stderr)
            raise SystemExit(1)
        raise
