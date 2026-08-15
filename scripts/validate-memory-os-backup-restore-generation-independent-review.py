#!/usr/bin/env python3
"""Fail-closed validation for generation recovery candidate independent reviews.

Security and Operability review payloads must be typed, distinct, repository-contained,
append-only in Git history after their first committed version, and bound to the exact
recovery authority they approve. This validator never creates review evidence or
production authority.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-evidence-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
EVIDENCE_ROOT = Path("docs/evidence/backup-restore")
REVIEW_SCHEMA = "memory-os-backup-restore-generation-review-evidence.v1"
REQUIRED_FIELDS = {
    "schemaVersion",
    "evidenceId",
    "drillRequestId",
    "recoveryObjectivesId",
    "sourceEnvironmentGenerationId",
    "restoreTargetGenerationId",
    "reviewRole",
    "reviewResult",
    "reviewedAt",
    "reviewerPseudonym",
    "productionTrafficChanged",
    "productionCredentialsUsed",
    "automaticPromotion",
}
BOUND_FIELDS = (
    "evidenceId",
    "drillRequestId",
    "recoveryObjectivesId",
    "sourceEnvironmentGenerationId",
    "restoreTargetGenerationId",
)
ROLE_BY_REF = {
    "securityReviewRef": "SECURITY",
    "operabilityReviewRef": "OPERABILITY",
}
BOUND_RULE_BY_FIELD = {
    "evidenceId": "independentReviewMustBindEvidenceId",
    "drillRequestId": "independentReviewMustBindDrillRequestId",
    "recoveryObjectivesId": "independentReviewMustBindRecoveryObjectivesId",
    "sourceEnvironmentGenerationId": "independentReviewMustBindSourceEnvironmentGenerationId",
    "restoreTargetGenerationId": "independentReviewMustBindRestoreTargetGenerationId",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_json(path: Path, field: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"{field} unreadable or invalid JSON: {exc}") from exc
    require(isinstance(value, dict), f"{field} root must be object")
    return value


def validate_contract_authority() -> None:
    contract = load_json(CONTRACT, "generation evidence contract")
    require(
        contract.get("independentReviewEvidenceSchemaVersion") == REVIEW_SCHEMA,
        "independent review evidence schema authority drift",
    )
    require(
        contract.get("independentReviewEvidenceRoot") == EVIDENCE_ROOT.as_posix(),
        "independent review evidence root authority drift",
    )
    fields = contract.get("requiredIndependentReviewEvidenceFields")
    require(
        isinstance(fields, list)
        and all(isinstance(field, str) and field for field in fields)
        and len(fields) == len(set(fields))
        and set(fields) == REQUIRED_FIELDS,
        "independent review required field authority drift",
    )
    require(contract.get("independentReviewRoles") == ROLE_BY_REF, "independent review role authority drift")
    rules = contract.get("recordRules")
    require(isinstance(rules, dict), "generation evidence recordRules missing")
    for rule in (
        "independentSecurityAndOperabilityReviewsRequired",
        "typedIndependentReviewEvidenceRequired",
        "independentReviewEvidenceMustRemainInsideMonitoredNamespace",
        "independentReviewRoleMustMatchReference",
        "independentReviewMustBeApproved",
        "independentReviewReviewerPseudonymsMustBeDistinct",
        "independentReviewPayloadMustRemainAppendOnlyAfterFirstCommit",
        "independentReviewCannotAuthorizeAutomaticPromotion",
    ):
        require(rules.get(rule) is True, f"independent review contract rule drift: {rule}")
    for field, rule in BOUND_RULE_BY_FIELD.items():
        require(rules.get(rule) is True, f"independent review binding rule drift: {field}")


def canonical_ref(value: Any, field: str) -> tuple[str, Path]:
    require(isinstance(value, str) and value, f"{field} required")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == value, f"{field} must be canonical repository-relative path")
    require(relative.parts[:3] == EVIDENCE_ROOT.parts, f"{field} must remain inside docs/evidence/backup-restore")
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(resolved == relative and path.is_file(), f"{field} must resolve to canonical repository file")
    return value, path


def git_history(ref: str, field: str) -> list[str]:
    completed = subprocess.run(
        ["git", "log", "--format=%H", "--follow", "--", ref],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, f"cannot inspect {field} Git history")
    commits = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    require(commits, f"{field} must be committed review evidence")
    return commits


def require_append_only_review(ref: str, path: Path, field: str) -> None:
    commits = git_history(ref, field)
    require(len(commits) == 1, f"{field} must remain append-only after its first committed version")
    completed = subprocess.run(
        ["git", "show", f"{commits[0]}:{ref}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, f"cannot read initial committed bytes for {field}")
    require(path.read_bytes() == completed.stdout, f"{field} bytes drift from initial committed review evidence")


def validate_review(row: dict[str, Any], ref_field: str, expected_role: str) -> tuple[str, str]:
    ref, path = canonical_ref(row.get(ref_field), ref_field)
    require_append_only_review(ref, path, ref_field)
    payload = load_json(path, ref_field)
    require(set(payload) == REQUIRED_FIELDS, f"{ref_field} typed review fields drift")
    require(payload.get("schemaVersion") == REVIEW_SCHEMA, f"{ref_field} schemaVersion drift")
    for field in BOUND_FIELDS:
        require(payload.get(field) == row.get(field), f"{ref_field} {field} mismatch")
    require(payload.get("reviewRole") == expected_role, f"{ref_field} reviewRole mismatch")
    require(payload.get("reviewResult") == "APPROVED", f"{ref_field} review must be APPROVED")
    reviewer = payload.get("reviewerPseudonym")
    reviewed_at = payload.get("reviewedAt")
    require(isinstance(reviewer, str) and reviewer.strip(), f"{ref_field} reviewerPseudonym required")
    require(isinstance(reviewed_at, str) and reviewed_at.strip(), f"{ref_field} reviewedAt required")
    require(payload.get("productionTrafficChanged") is False, f"{ref_field} cannot change production traffic")
    require(payload.get("productionCredentialsUsed") is False, f"{ref_field} cannot use production credentials")
    require(payload.get("automaticPromotion") is False, f"{ref_field} cannot authorize automatic promotion")
    return ref, reviewer


def main() -> int:
    validate_contract_authority()
    registry = load_json(REGISTRY, "generation evidence registry")
    require(registry.get("schemaVersion") == "memory-os-backup-restore-generation-evidence-registry.v1", "generation evidence registry schema drift")
    require(registry.get("appendOnly") is True, "generation evidence registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "generation evidence registry production boundary drift")
    rows = registry.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "generation evidence registry records invalid")

    for index, row in enumerate(rows):
        try:
            security_ref, security_reviewer = validate_review(row, "securityReviewRef", ROLE_BY_REF["securityReviewRef"])
            operability_ref, operability_reviewer = validate_review(row, "operabilityReviewRef", ROLE_BY_REF["operabilityReviewRef"])
            require(security_ref != operability_ref, "Security and Operability review refs must remain distinct")
            require(security_reviewer != operability_reviewer, "Security and Operability reviewers must remain distinct")
        except Fail as exc:
            raise Fail(f"records[{index}] independent review authority invalid: {exc}") from exc

    print(f"PASS: generation independent review authority records={len(rows)} productionEvidence=false productionReady=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
