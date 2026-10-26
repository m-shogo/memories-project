#!/usr/bin/env python3
"""Negative suite for generation material-delta review authority."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-material-delta-review.py"
SUBSTITUTE = ROOT / "scripts/validate-memory-os-operability.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_generation_material_delta_review_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load material-delta validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_registry_fail(module, row: dict, label: str, expected: str) -> None:
    # The canonical main's execution guard rejects monkeypatched runtime helpers
    # before registry rows are inspected. Test the actual row validator directly.
    fields = module.validate_contract_authority()["requiredMaterialDeltaReviewEvidenceFields"]
    same_generation = {
        "sourceEnvironmentGenerationId": "pegen_same_negative",
        "restoreTargetGenerationId": "pegen_same_negative",
        "materialDeltaReviewRef": None,
    }
    module.validate_row(same_generation, 0, fields)
    try:
        module.validate_row(row, 0, fields)
    except module.Fail as exc:
        require(str(exc) == expected,
                f"material-delta registry row rejected at wrong boundary ({label}): {exc}")
    else:
        raise Fail(f"material-delta registry row unexpectedly passed: {label}")
    module.validate_row(same_generation, 0, fields)


def expect_authority_substitution_fail(module, field: str, substitute: Path) -> None:
    # The unchanged canonical path set must pass before and after each mutation.
    module.enforce_execution_authority()
    module.enforce_runtime_authorities()
    canonical_contract = (ROOT / module.CONTRACT_REL).read_bytes()
    canonical_registry = (ROOT / module.REGISTRY_REL).read_bytes()
    expected = {
        "CONTRACT": "generation evidence contract authority drift",
        "REGISTRY": "generation evidence registry authority drift",
        "VALIDATOR": "material-delta review validator authority drift",
        "NEGATIVE": "material-delta review negative validator authority drift",
    }[field]
    original = getattr(module, field)
    setattr(module, field, substitute)
    try:
        try:
            module.main()
        except module.Fail as exc:
            require(str(exc) == expected,
                    f"material-delta runtime authority substitution rejected at wrong boundary ({field}): {exc}")
        else:
            raise Fail(f"runtime authority substitution unexpectedly accepted: {field}")
        require((ROOT / module.CONTRACT_REL).read_bytes() == canonical_contract,
                f"canonical contract mutated while rejecting {field}")
        require((ROOT / module.REGISTRY_REL).read_bytes() == canonical_registry,
                f"canonical registry mutated while rejecting {field}")
    finally:
        setattr(module, field, original)
    module.enforce_execution_authority()
    module.enforce_runtime_authorities()


def expect_contract_fail(module, mutate, label: str, expected: str) -> None:
    module.validate_contract_authority()
    canonical = json.loads(module.CONTRACT.read_text(encoding="utf-8"))
    mutated = json.loads(json.dumps(canonical))
    mutate(mutated)
    original_load_json = module.load_json
    try:
        module.load_json = lambda path, field: mutated if path == module.CONTRACT else original_load_json(path, field)
        try:
            module.validate_contract_authority()
        except module.Fail as exc:
            require(str(exc) == expected,
                    f"material-delta contract rejected at wrong authority ({label}): {exc}")
        else:
            raise Fail(f"contract authority negative unexpectedly passed: {label}")
    finally:
        module.load_json = original_load_json
    module.validate_contract_authority()


def base_row() -> dict:
    return {
        "evidenceId": "brge_material_delta_negative",
        "drillRequestId": "brrq_material_delta_negative",
        "recoveryObjectivesId": "ro_material_delta_negative",
        "sourceEnvironmentGenerationId": "pegen_source_negative",
        "restoreTargetGenerationId": "pegen_target_negative",
        "materialDeltaReviewRef": "docs/evidence/backup-restore/material-delta/review.json",
    }


def base_payload(module) -> dict:
    return {
        "schemaVersion": module.EXPECTED_SCHEMA,
        "evidenceId": "brge_material_delta_negative",
        "drillRequestId": "brrq_material_delta_negative",
        "recoveryObjectivesId": "ro_material_delta_negative",
        "sourceEnvironmentGenerationId": "pegen_source_negative",
        "restoreTargetGenerationId": "pegen_target_negative",
        "reviewResult": "APPROVED",
        "reviewedAt": "2026-08-15T18:00:00Z",
        "reviewerPseudonym": "material_delta_reviewer",
        "productionTrafficChanged": False,
        "productionCredentialsUsed": False,
        "automaticPromotion": False,
    }


def expect_payload_fail(module, mutate, label: str, expected: str) -> None:
    row = base_row()
    payload = base_payload(module)
    fields = json.loads(module.CONTRACT.read_text(encoding="utf-8"))["requiredMaterialDeltaReviewEvidenceFields"]
    module.validate_material_delta_payload(row, payload, 0, fields)
    mutate(payload)
    try:
        module.validate_material_delta_payload(row, payload, 0, fields)
    except module.Fail as exc:
        require(str(exc) == f"records[0].materialDeltaReviewRef {expected}",
                f"material-delta payload rejected at wrong authority ({label}): {exc}")
    else:
        raise Fail(f"typed material-delta negative unexpectedly passed: {label}")
    module.validate_material_delta_payload(row, base_payload(module), 0, fields)


def prove_material_delta_json_reader(module) -> None:
    """Exercise the actual material-delta reader on disposable fixtures."""
    before = (module.CONTRACT.read_bytes(), module.REGISTRY.read_bytes())
    with tempfile.TemporaryDirectory(prefix="memory-os-material-delta-json-", dir=ROOT) as directory:
        path = Path(directory) / "candidate.json"
        positive = b'{"safe":true,"nested":{"count":1}}'
        path.write_bytes(positive)
        require(module.load_json(path, "synthetic") == {"safe": True, "nested": {"count": 1}}, "material-delta JSON positive control failed")
        cases = (
            ("duplicate root", b'{"safe":true,"safe":false}', "material-delta JSON duplicate key refused"),
            ("duplicate nested", b'{"nested":{"a":1,"a":2}}', "material-delta JSON duplicate key refused"),
            ("NaN", b'{"number":NaN}', "material-delta JSON nonfinite number refused"),
            ("Infinity", b'{"number":Infinity}', "material-delta JSON nonfinite number refused"),
            ("negative Infinity", b'{"number":-Infinity}', "material-delta JSON nonfinite number refused"),
            ("float overflow", b'{"number":1e999}', "material-delta JSON nonfinite number refused"),
            ("large integer", b'{"number":' + b"9" * 5000 + b"}", "material-delta JSON integer too large"),
            ("oversized JSON", b'{"data":"' + b"x" * module.MAX_JSON_BYTES + b'"}', "material-delta JSON size limit exceeded"),
            ("invalid UTF-8", b'{"private":"\xff"}', "material-delta JSON unreadable or invalid"),
            ("malformed private", b'{"private":"synthetic-secret",', "material-delta JSON unreadable or invalid"),
            ("nonobject root", b"[]", "material-delta JSON root must be object"),
        )
        def rejected(candidate, expected: str, label: str) -> None:
            try:
                module.load_json(candidate, "synthetic-secret")
            except module.Fail as exc:
                require(str(exc) == expected, f"{label}: wrong material-delta JSON rejection boundary")
                require("synthetic-secret" not in str(exc), f"{label}: private marker disclosed")
            else:
                raise Fail(f"{label}: unsafe material-delta JSON accepted")
        for label, payload, expected in cases:
            path.write_bytes(payload)
            rejected(path, expected, label)
        path.write_bytes(positive)
        alias = Path(directory) / "alias.json"
        alias.symlink_to(path)
        rejected(alias, "material-delta JSON path missing or unsafe", "symlink")
        rejected(Path(directory), "material-delta JSON path missing or unsafe", "directory")
        rejected(Path(directory) / "missing.json", "material-delta JSON path missing or unsafe", "missing")
        rejected("candidate.json", "material-delta JSON path invalid", "non-Path")
        with tempfile.TemporaryDirectory(prefix="memory-os-material-delta-canary-") as outside:
            canary = Path(outside) / "canary.json"
            canary.write_bytes(positive)
            escaped = Path(directory) / "escaped.json"
            escaped.symlink_to(canary)
            rejected(escaped, "material-delta JSON path missing or unsafe", "external symlink")
            require(canary.read_bytes() == positive, "material-delta JSON reader modified external canary")
        require(path.read_bytes() == positive, "material-delta JSON reader modified positive fixture")
    require((module.CONTRACT.read_bytes(), module.REGISTRY.read_bytes()) == before, "material-delta JSON reader mutated canonical authorities")
    print("PASS: actual material-delta JSON reader positive and 16 fail-closed negatives")


def main() -> int:
    module = load_validator()
    prove_material_delta_json_reader(module)

    for field, substitute in (
        ("CONTRACT", module.REGISTRY),
        ("REGISTRY", module.CONTRACT),
        ("VALIDATOR", SUBSTITUTE),
        ("NEGATIVE", SUBSTITUTE),
    ):
        expect_authority_substitution_fail(module, field, substitute)

    expect_registry_fail(module, {
        "sourceEnvironmentGenerationId": "pegen_source_negative",
        "restoreTargetGenerationId": "pegen_target_negative",
        "materialDeltaReviewRef": "SECURITY.md",
    }, "generic repository file",
       "records[0].materialDeltaReviewRef must remain inside docs/evidence/backup-restore/material-delta/")
    expect_registry_fail(module, {
        "sourceEnvironmentGenerationId": "pegen_same_negative",
        "restoreTargetGenerationId": "pegen_same_negative",
        "materialDeltaReviewRef": "docs/evidence/backup-restore/material-delta/review.json",
    }, "same-generation material delta review",
       "records[0] same-generation restore must not declare materialDeltaReviewRef")
    expect_registry_fail(module, {
        "sourceEnvironmentGenerationId": "pegen_source_negative",
        "restoreTargetGenerationId": "pegen_target_negative",
        "materialDeltaReviewRef": "docs/evidence/backup-restore/../outside.json",
    }, "path traversal",
       "records[0].materialDeltaReviewRef must be canonical repository-relative path")

    for field, invalid in (
        ("evidenceId", "brge_wrong_negative"),
        ("drillRequestId", "brrq_wrong_negative"),
        ("recoveryObjectivesId", "ro_wrong_negative"),
        ("sourceEnvironmentGenerationId", "pegen_wrong_source"),
        ("restoreTargetGenerationId", "pegen_wrong_target"),
    ):
        expect_payload_fail(
            module, lambda payload, field=field, invalid=invalid: payload.__setitem__(field, invalid),
            f"material-delta provenance mismatch: {field}", f"{field} mismatch",
        )
    for field, invalid, expected in (
        ("reviewResult", "REJECTED", "reviewResult must be APPROVED"),
        ("automaticPromotion", True, "automaticPromotion must remain false"),
        ("productionTrafficChanged", True, "productionTrafficChanged must remain false"),
        ("productionCredentialsUsed", True, "productionCredentialsUsed must remain false"),
        ("reviewedAt", "2026-08-15", "reviewedAt must be canonical UTC RFC3339 seconds"),
        ("reviewedAt", "2026-99-99T99:99:99Z", "reviewedAt must be canonical UTC RFC3339 seconds"),
        ("reviewerPseudonym", "Reviewer Name", "reviewerPseudonym invalid"),
    ):
        expect_payload_fail(
            module, lambda payload, field=field, invalid=invalid: payload.__setitem__(field, invalid),
            f"material-delta typed boundary: {field} {invalid}", expected,
        )
    expect_payload_fail(
        module, lambda payload: payload.__setitem__("unexpectedField", True),
        "unexpected typed review field", "typed review fields drift",
    )
    expect_payload_fail(
        module, lambda payload: payload.pop("reviewedAt"),
        "missing typed review field", "typed review fields drift",
    )
    expect_payload_fail(
        module, lambda payload: payload.__setitem__("schemaVersion", "memory-os-backup-restore-material-delta-review.v0"),
        "obsolete typed review schema", "schemaVersion drift",
    )

    expect_contract_fail(
        module, lambda contract: contract.__setitem__("materialDeltaReviewEvidenceRoot", "docs/evidence/backup-restore"),
        "material-delta evidence root widened", "material-delta review evidence root authority drift",
    )
    expect_contract_fail(
        module, lambda contract: contract.__setitem__("materialDeltaReviewEvidenceSchemaVersion", "memory-os-backup-restore-material-delta-review.v0"),
        "material-delta schema authority drift", "material-delta review evidence schema authority drift",
    )
    expect_contract_fail(
        module, lambda contract: contract.__setitem__("materialDeltaReviewValidator", "scripts/validate-memory-os-backup-restore-generation-evidence.py"),
        "material-delta validator substituted", "material-delta review validator authority drift",
    )
    expect_contract_fail(
        module, lambda contract: contract.__setitem__("materialDeltaReviewNegativeValidator", "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py"),
        "material-delta negative validator substituted", "material-delta review negative validator authority drift",
    )
    for mutation, label in (
        (lambda fields: fields.pop(), "required field removed"),
        (lambda fields: fields.append("reviewedAt"), "required field duplicated"),
        (lambda fields: fields.append("unexpectedField"), "required field added"),
    ):
        expect_contract_fail(
            module, lambda contract, mutation=mutation: mutation(contract["requiredMaterialDeltaReviewEvidenceFields"]),
            f"material-delta {label}", "material-delta review required fields authority drift",
        )
    mandatory_rules = (
        "crossGenerationRestoreRequiresMaterialDeltaReview",
        "sameGenerationRestoreMayUseNullMaterialDeltaReview",
        "crossGenerationMaterialDeltaReviewMustRemainInsideMonitoredNamespace",
        "crossGenerationMaterialDeltaReviewMustRemainAppendOnlyAfterFirstCommit",
        "crossGenerationMaterialDeltaReviewMustBeTyped",
        "crossGenerationMaterialDeltaReviewMustBindEvidenceId",
        "crossGenerationMaterialDeltaReviewMustBindDrillRequestId",
        "crossGenerationMaterialDeltaReviewMustBindRecoveryObjectivesId",
        "crossGenerationMaterialDeltaReviewMustBindSourceGenerationId",
        "crossGenerationMaterialDeltaReviewMustBindRestoreTargetGenerationId",
        "crossGenerationMaterialDeltaReviewMustBeApproved",
        "crossGenerationMaterialDeltaReviewCannotAuthorizeAutomaticPromotion",
        "candidateDerivationMustUseTypedMaterialDeltaReviewAuthority",
    )
    for rule in mandatory_rules:
        expect_contract_fail(
            module, lambda contract, rule=rule: contract["recordRules"].__setitem__(rule, False),
            f"mandatory material-delta review rule disabled: {rule}",
            f"material-delta review contract rule drift: {rule}",
        )
    expect_contract_fail(
        module, lambda contract: contract["promotionBoundary"].__setitem__(
            "completeReviewedRecordAlsoRequiresTypedAppendOnlyMaterialDeltaReviewForCrossGenerationRestore", False
        ),
        "material-delta promotion boundary disabled", "material-delta promotion boundary drift",
    )

    original_history = module.git_history
    original_transport = module.subprocess.run
    try:
        review_ref = "docs/evidence/backup-restore/material-delta/synthetic.json"
        module.git_history = lambda _ref, _field: ["a" * 40, "b" * 40]
        try:
            module.require_append_only_review(
                review_ref, Path("/tmp/not-read-after-history-rejection"), "materialDeltaReviewRef",
            )
        except module.Fail as exc:
            require(str(exc) == "materialDeltaReviewRef must remain append-only after its first committed version",
                    f"material-delta multi-commit negative wrong diagnostic: {exc}")
        else:
            raise Fail("material-delta review with multiple committed versions was accepted")

        with tempfile.TemporaryDirectory(prefix="material-delta-review-immutability-negative-") as tmp:
            path = Path(tmp) / "synthetic-review.json"
            creation_bytes = b'{"reviewResult":"APPROVED"}\n'
            path.write_bytes(creation_bytes)
            module.git_history = lambda _ref, _field: ["a" * 40]

            def synthetic_git_show(args, **_kwargs):
                require(args == ["git", "show", f"{'a' * 40}:{review_ref}"],
                        f"unexpected synthetic material-delta history transport: {args}")
                return subprocess.CompletedProcess(args, 0, stdout=creation_bytes, stderr=b"")

            module.subprocess.run = synthetic_git_show
            module.require_append_only_review(review_ref, path, "materialDeltaReviewRef")
            path.write_bytes(b'{"reviewResult":"REJECTED"}\n')
            try:
                module.require_append_only_review(review_ref, path, "materialDeltaReviewRef")
            except module.Fail as exc:
                require(str(exc) == "materialDeltaReviewRef bytes drift from initial committed material-delta review evidence",
                        f"material-delta review byte mutation wrong diagnostic: {exc}")
            else:
                raise Fail("material-delta review changed after creation was accepted")
            path.write_bytes(creation_bytes)
            module.require_append_only_review(review_ref, path, "materialDeltaReviewRef")
    finally:
        module.git_history = original_history
        module.subprocess.run = original_transport
    print("PASS: material-delta append-only history and creation-blob immutability positive/negative controls")

    print("PASS: material-delta review negatives reject runtime authority substitution, generic refs, semantic binding drift, candidate/promotion drift, unsafe claims, contract drift, and post-commit edits")
    print("runtime data/executable authority substitution accepted: false")
    print("canonical generation evidence authority mutated: false")
    print("automatic production promotion authority created: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
