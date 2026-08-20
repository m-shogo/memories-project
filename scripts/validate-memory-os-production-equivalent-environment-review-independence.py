#!/usr/bin/env python3
"""Validate independent-review evidence separation for eligible environment generations."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-review-independence-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
HELPER_REL = Path("scripts/memory_os_environment_generation_eligibility.py")

EXPECTED_ROOT_FIELDS = {
    "contractId",
    "schemaVersion",
    "description",
    "generationRegistry",
    "generationEligibilityHelper",
    "validator",
    "workflow",
    "rules",
    "currentBoundary",
}
EXPECTED_RULE_FIELDS = {
    "appliesOnlyToPreflightEligibleGenerations",
    "environmentIndependentReviewRefRequired",
    "environmentReviewMustDifferFromPostgresqlRestoreEvidence",
    "environmentReviewMustDifferFromObjectRestoreEvidence",
    "environmentReviewMustDifferFromLatencyEvidence",
    "environmentReviewMustDifferFromFailureInjectionEvidence",
    "environmentReviewMustDifferFromCredentialScopeEvidence",
    "environmentReviewMustDifferFromBackupRestoreEvidence",
    "environmentReviewMustDifferFromMaterialDeltaReviewEvidence",
    "allComparedEvidenceRefsMustResolveInRepository",
    "productionEvidenceForbidden",
    "productionReadyForbidden",
}
EXPECTED_BOUNDARY_FIELDS = {
    "preflightEligibleGenerationCount",
    "independentlyReviewedEligibleGenerationCount",
    "reviewReuseViolationCount",
    "productionEvidence",
    "productionReady",
    "productionDecision",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def exact_int(value: Any, field: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{field} must be an integer")
    require(value >= 0, f"{field} must be non-negative")
    return value


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        raise Fail(f"cannot load {label}: {exc}") from exc
    try:
        label = path.relative_to(ROOT)
    except ValueError:
        label = path
    require(isinstance(value, dict), f"root must be object: {label}")
    return value


def validate_contract_shape(contract: dict[str, Any]) -> None:
    require(set(contract) == EXPECTED_ROOT_FIELDS, "review independence contract field set drift")
    require(contract.get("contractId") == "memory-os.operability.production-equivalent-environment-review-independence.v1", "review independence contract id drift")
    require(contract.get("schemaVersion") == "memory-os-production-equivalent-environment-review-independence-contract.v1", "review independence contract schema drift")
    rules = contract.get("rules")
    require(isinstance(rules, dict) and set(rules) == EXPECTED_RULE_FIELDS, "review independence rule field set drift")
    require(all(rules[field] is True for field in EXPECTED_RULE_FIELDS), "review independence rules must remain fail-closed")
    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict) and set(boundary) == EXPECTED_BOUNDARY_FIELDS, "review independence currentBoundary field set drift")


def canonical_helper_path() -> Path:
    expected = ROOT / HELPER_REL
    require(HELPER == expected, "generation eligibility helper executable authority drift")
    try:
        resolved = HELPER.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail("generation eligibility helper missing or escapes repository") from exc
    require(resolved == HELPER_REL and HELPER.is_file(), "generation eligibility helper must be canonical repository file")
    return HELPER


def load_helper():
    path = canonical_helper_path()
    spec = importlib.util.spec_from_file_location("memory_os_generation_eligibility_review_independence", path)
    require(spec is not None and spec.loader is not None, "cannot load generation eligibility helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def repo_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value, f"{field} invalid")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == value, f"{field} invalid")
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} evidence missing or escapes repository") from exc
    require(resolved == relative and path.is_file(), f"{field} must resolve to the canonical repository file")
    return value


def main() -> int:
    contract = load(CONTRACT)
    validate_contract_shape(contract)
    helper = load_helper()
    state = helper.derive(GEN_REGISTRY)
    refs = {
        "generationRegistry": GEN_REGISTRY,
        "generationEligibilityHelper": HELPER,
        "validator": Path("scripts/validate-memory-os-production-equivalent-environment-review-independence.py"),
        "workflow": Path(".github/workflows/production-equivalent-environment-review-independence.yml"),
    }
    for field, path in refs.items():
        expected = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
        require(contract.get(field) == expected, f"review independence ref drift: {field}")
        require((ROOT / expected).is_file(), f"review independence artifact missing: {expected}")

    violations = 0
    reviewed_count = 0
    for row in state["preflightEligibleRows"]:
        generation_id = row.get("generationId")
        env_ref = row.get("environmentRecordRef")
        require(isinstance(env_ref, str), f"eligible generation environment record ref missing: {generation_id}")
        env = load(ROOT / env_ref)
        boundary = env.get("evidenceBoundary")
        require(isinstance(boundary, dict), f"eligible generation evidenceBoundary missing: {generation_id}")
        independent_ref = repo_ref(boundary.get("independentReviewRef"), f"{generation_id}.independentReviewRef")
        require(boundary.get("independentReviewCompleted") is True, f"eligible generation lacks independent review: {generation_id}")

        component_refs = [
            repo_ref(env.get("postgresql", {}).get("restoreEvidenceRef"), f"{generation_id}.postgresql.restoreEvidenceRef"),
            repo_ref(env.get("objectStorage", {}).get("restoreEvidenceRef"), f"{generation_id}.objectStorage.restoreEvidenceRef"),
            repo_ref(env.get("network", {}).get("latencyProfileRef"), f"{generation_id}.network.latencyProfileRef"),
            repo_ref(env.get("network", {}).get("failureInjectionRef"), f"{generation_id}.network.failureInjectionRef"),
            repo_ref(env.get("identityAndSecrets", {}).get("credentialScopeRef"), f"{generation_id}.identityAndSecrets.credentialScopeRef"),
            repo_ref(env.get("backupRestore", {}).get("evidenceRef"), f"{generation_id}.backupRestore.evidenceRef"),
        ]
        delta_refs: list[str] = []
        deltas = env.get("materialDeltas")
        require(isinstance(deltas, list), f"eligible generation materialDeltas invalid: {generation_id}")
        for index, delta in enumerate(deltas):
            require(isinstance(delta, dict), f"{generation_id}.materialDeltas[{index}] invalid")
            value = delta.get("independentReviewRef")
            if value is not None:
                delta_refs.append(repo_ref(value, f"{generation_id}.materialDeltas[{index}].independentReviewRef"))
        reused = [ref for ref in component_refs + delta_refs if ref == independent_ref]
        if reused:
            violations += 1
            raise Fail(f"eligible generation reuses environment independent review evidence as implementation/delta evidence: {generation_id}")
        reviewed_count += 1

    eligible_count = exact_int(state["preflightEligibleGenerationCount"], "semantic eligibility preflightEligibleGenerationCount")
    require(reviewed_count == eligible_count, "eligible/reviewed generation count drift")
    boundary = contract["currentBoundary"]
    require(exact_int(boundary.get("preflightEligibleGenerationCount"), "currentBoundary.preflightEligibleGenerationCount") == eligible_count, "review independence eligible count drift")
    require(exact_int(boundary.get("independentlyReviewedEligibleGenerationCount"), "currentBoundary.independentlyReviewedEligibleGenerationCount") == reviewed_count, "review independence reviewed count drift")
    require(exact_int(boundary.get("reviewReuseViolationCount"), "currentBoundary.reviewReuseViolationCount") == violations, "review independence violation count drift")
    require(boundary.get("productionEvidence") is False and boundary.get("productionReady") is False and boundary.get("productionDecision") == "NO_GO", "review independence cannot promote production")

    print("Memory OS production-equivalent environment review independence PASS")
    print(f"preflight-eligible generations: {eligible_count}")
    print(f"independently reviewed eligible generations: {reviewed_count}")
    print(f"review reuse violations: {violations}")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT ENVIRONMENT REVIEW INDEPENDENCE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
