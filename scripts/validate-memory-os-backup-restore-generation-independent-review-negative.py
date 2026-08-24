#!/usr/bin/env python3
"""Negative suite for typed, append-only generation candidate reviews."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review.py"
SUBSTITUTE = ROOT / "scripts/validate-memory-os-operability.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_generation_independent_review_validator_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load independent review validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def head_sha() -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, "cannot resolve HEAD")
    value = completed.stdout.strip()
    require(len(value) == 40, "HEAD sha invalid")
    return value


def expect_fail(module, registry: dict, label: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as handle:
        path = Path(handle.name)
        json.dump(registry, handle)
        handle.write("\n")
    original_registry = module.REGISTRY
    original_enforcer = module.enforce_runtime_authorities
    try:
        module.REGISTRY = path
        module.enforce_runtime_authorities = lambda: None
        try:
            module.main()
        except module.Fail:
            return
        raise Fail(f"negative case unexpectedly passed: {label}")
    finally:
        module.enforce_runtime_authorities = original_enforcer
        module.REGISTRY = original_registry
        path.unlink(missing_ok=True)


def expect_authority_substitution_fail(module, field: str, substitute: Path) -> None:
    canonical_contract = (ROOT / module.CONTRACT_REL).read_bytes()
    canonical_registry = (ROOT / module.REGISTRY_REL).read_bytes()
    original = getattr(module, field)
    setattr(module, field, substitute)
    try:
        try:
            module.main()
        except module.Fail:
            pass
        else:
            raise Fail(f"runtime authority substitution unexpectedly passed: {field}")
        require((ROOT / module.CONTRACT_REL).read_bytes() == canonical_contract, f"canonical contract mutated while rejecting {field}")
        require((ROOT / module.REGISTRY_REL).read_bytes() == canonical_registry, f"canonical registry mutated while rejecting {field}")
    finally:
        setattr(module, field, original)


def base_row() -> dict:
    return {
        "evidenceId": "brge_negative_review_authority",
        "sourceCommitSha": head_sha(),
        "drillRequestId": "brrq_negative_review_authority",
        "recoveryObjectivesId": "ro_negative_review_authority",
        "sourceEnvironmentGenerationId": "pegen_negative_source",
        "restoreTargetGenerationId": "pegen_negative_target",
        "materialDeltaReviewRef": "docs/evidence/backup-restore/material-delta/synthetic-review.json",
        "securityReviewRef": "README.md",
        "operabilityReviewRef": "SECURITY.md",
    }


def registry(row: dict) -> dict:
    return {
        "schemaVersion": "memory-os-backup-restore-generation-evidence-registry.v1",
        "appendOnly": True,
        "registeredEvidenceCount": 1,
        "drillRequestBoundEvidenceCount": 1,
        "completeGenerationBoundBackupCount": 0,
        "completeGenerationBoundRestoreCount": 0,
        "productionEquivalentRecoveryCandidateCount": 0,
        "records": [row],
        "productionEvidence": False,
        "productionReady": False,
    }


def typed_payload(row: dict, role: str) -> dict:
    return {
        "schemaVersion": "memory-os-backup-restore-generation-review-evidence.v1",
        "evidenceId": row["evidenceId"],
        "drillRequestId": row["drillRequestId"],
        "recoveryObjectivesId": row["recoveryObjectivesId"],
        "sourceEnvironmentGenerationId": row["sourceEnvironmentGenerationId"],
        "restoreTargetGenerationId": row["restoreTargetGenerationId"],
        "reviewRole": role,
        "reviewResult": "APPROVED",
        "reviewedAt": "2026-08-15T00:00:00Z",
        "reviewerPseudonym": "reviewer-security" if role == "SECURITY" else "reviewer-operability",
        "productionTrafficChanged": False,
        "productionCredentialsUsed": False,
        "automaticPromotion": False,
    }


def expect_review_payload_fail(module, payload: dict, label: str) -> None:
    row = base_row()
    original_canonical_ref = module.canonical_ref
    original_append_only = module.require_append_only_review
    original_load_json = module.load_json
    try:
        module.canonical_ref = lambda _value, _field: (
            "docs/evidence/backup-restore/synthetic-review.json",
            Path("/tmp/synthetic-generation-review.json"),
        )
        module.require_append_only_review = lambda _ref, _path, _field: None
        module.load_json = lambda _path, _field: payload
        try:
            module.validate_review(row, "securityReviewRef", "SECURITY")
        except module.Fail:
            return
        raise Fail(f"review payload negative unexpectedly passed: {label}")
    finally:
        module.canonical_ref = original_canonical_ref
        module.require_append_only_review = original_append_only
        module.load_json = original_load_json


def expect_bound_field_fail(module, field: str) -> None:
    row = base_row()
    payload = typed_payload(row, "SECURITY")
    payload[field] = "mismatched-authority"
    expect_review_payload_fail(module, payload, f"authority mismatch: {field}")


def expect_contract_fail(module, mutate, label: str) -> None:
    canonical = json.loads(module.CONTRACT.read_text(encoding="utf-8"))
    mutated = json.loads(json.dumps(canonical))
    mutate(mutated)
    original_load_json = module.load_json
    try:
        module.load_json = lambda path, field: mutated if path == module.CONTRACT else original_load_json(path, field)
        try:
            module.validate_contract_authority()
        except module.Fail:
            return
        raise Fail(f"contract authority negative unexpectedly passed: {label}")
    finally:
        module.load_json = original_load_json


def expect_material_delta_candidate_delegation(module) -> None:
    class RejectMaterialDelta:
        @staticmethod
        def material_delta_review_approved(_row):
            raise module.Fail("synthetic material-delta rejection")

    original_loader = module.load_material_delta_validator
    original_validate_review = module.validate_review
    try:
        module.load_material_delta_validator = lambda: RejectMaterialDelta()
        module.validate_review = lambda _row, ref_field, _role: (
            f"docs/evidence/backup-restore/{ref_field}.json",
            "reviewer-security" if ref_field == "securityReviewRef" else "reviewer-operability",
        )
        try:
            module.candidate_reviews_approved(base_row())
        except module.Fail as exc:
            require("material-delta review authority invalid" in str(exc), f"unexpected material-delta delegation rejection: {exc}")
            return
        raise Fail("candidate review authority bypassed material-delta rejection")
    finally:
        module.load_material_delta_validator = original_loader
        module.validate_review = original_validate_review


def main() -> int:
    module = load_validator()

    for field, substitute in (
        ("CONTRACT", module.REGISTRY),
        ("REGISTRY", module.CONTRACT),
        ("MATERIAL_DELTA_VALIDATOR", SUBSTITUTE),
        ("VALIDATOR", SUBSTITUTE),
    ):
        expect_authority_substitution_fail(module, field, substitute)

    expect_fail(module, registry(base_row()), "generic repository review refs")

    same_ref = base_row()
    same_ref["securityReviewRef"] = "docs/evidence/backup-restore/README.md"
    same_ref["operabilityReviewRef"] = "docs/evidence/backup-restore/README.md"
    expect_fail(module, registry(same_ref), "security/operability ref reuse")

    production_boundary = registry(base_row())
    production_boundary["productionReady"] = True
    expect_fail(module, production_boundary, "productionReady promotion")

    expect_material_delta_candidate_delegation(module)

    for field in module.BOUND_FIELDS:
        expect_bound_field_fail(module, field)

    for invalid_reviewed_at in (
        "2026-08-15",
        "2026-08-15T00:00:00+00:00",
        "2026-08-15T00:00:00.000Z",
        "2026-13-15T00:00:00Z",
    ):
        payload = typed_payload(base_row(), "SECURITY")
        payload["reviewedAt"] = invalid_reviewed_at
        expect_review_payload_fail(module, payload, f"non-canonical reviewedAt: {invalid_reviewed_at}")

    for invalid_reviewer in (
        "ab", "Security Reviewer", "security@example.com", "../security",
        "SECURITY_REVIEWER", " reviewer-security",
    ):
        payload = typed_payload(base_row(), "SECURITY")
        payload["reviewerPseudonym"] = invalid_reviewer
        expect_review_payload_fail(module, payload, f"unsafe reviewer pseudonym: {invalid_reviewer}")

    expect_contract_fail(module, lambda contract: contract["requiredIndependentReviewEvidenceFields"].remove("drillRequestId"), "required review field removed")
    expect_contract_fail(module, lambda contract: contract["recordRules"].__setitem__("independentReviewMustBindRecoveryObjectivesId", False), "binding rule disabled")
    expect_contract_fail(module, lambda contract: contract["recordRules"].__setitem__("candidateDerivationMustUseTypedIndependentReviewAuthority", False), "candidate review authority delegation disabled")
    expect_contract_fail(module, lambda contract: contract["promotionBoundary"].__setitem__("completeReviewedRecordAlsoRequiresTypedAppendOnlyIndependentReviews", False), "independent review promotion boundary disabled")
    expect_contract_fail(module, lambda contract: contract.__setitem__("materialDeltaReviewValidator", "scripts/validate-memory-os-backup-restore-generation-evidence.py"), "candidate material-delta validator substituted")
    expect_contract_fail(module, lambda contract: contract["independentReviewRoles"].__setitem__("securityReviewRef", "OPERABILITY"), "review role map substituted")

    original_history = module.git_history
    try:
        module.git_history = lambda _ref, _field: ["a" * 40, "b" * 40]
        try:
            module.require_append_only_review(
                "docs/evidence/backup-restore/synthetic-review.json",
                Path("/tmp/not-read-after-history-rejection"),
                "securityReviewRef",
            )
        except module.Fail:
            pass
        else:
            raise Fail("review evidence edited after first commit was accepted")
    finally:
        module.git_history = original_history

    print("PASS: generation candidate review negatives reject runtime authority substitution, generic refs, review reuse, material-delta bypass, authority mismatch, malformed timestamps, unsafe reviewer identities, candidate/promotion contract drift, post-commit edits, and production promotion")
    print("runtime data/executable authority substitution accepted: false")
    print("canonical generation evidence authority mutated: false")
    print("human production promotion remains separate: true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
