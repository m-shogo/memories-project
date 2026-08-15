#!/usr/bin/env python3
"""Validate the read-only restore-preflight environment-generation eligibility authority."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-eligibility-contract.v1.json"
GEN_CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
ENV_SCHEMA = ROOT / "contracts/operations/production-equivalent-environment-record.v1.schema.json"
ENV_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-record.py"
HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {display_path(path)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {display_path(path)}")
    return value


def load_helper():
    try:
        expected = (ROOT / "scripts/memory_os_environment_generation_eligibility.py").resolve(strict=True)
        actual = HELPER.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError) as exc:
        raise Fail("environment generation eligibility helper missing") from exc
    require(actual == expected and HELPER.is_file(), "environment generation eligibility helper executable authority drift")
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_eligibility_validator", HELPER)
    require(spec is not None and spec.loader is not None, "cannot load environment generation eligibility helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    contract = load(CONTRACT)
    generation_contract = load(GEN_CONTRACT)
    registry = load(GEN_REGISTRY)
    helper = load_helper()

    require(contract.get("schemaVersion") == "memory-os-production-equivalent-environment-eligibility-contract.v1", "eligibility contract schema drift")
    refs = {
        "generationContract": GEN_CONTRACT,
        "generationRegistry": GEN_REGISTRY,
        "environmentRecordSchema": ENV_SCHEMA,
        "environmentSemanticValidator": ENV_VALIDATOR,
        "generationEligibilityHelper": HELPER,
        "validator": Path("scripts/validate-memory-os-production-equivalent-environment-eligibility.py"),
        "reconcile": Path("scripts/reconcile-memory-os-production-equivalent-environment-eligibility.py"),
        "workflow": Path(".github/workflows/production-equivalent-environment-eligibility.yml"),
    }
    for field, path in refs.items():
        expected = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
        require(contract.get(field) == expected, f"eligibility ref drift: {field}")
        require((ROOT / expected).is_file(), f"eligibility artifact missing: {expected}")
    rules = contract.get("rules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "eligibility rules must remain fail-closed")
    for key in (
        "registrationAloneCannotCreateEligibility",
        "semanticEnvironmentValidationRequired",
        "productionEquivalentDependenciesRequired",
        "independentReviewRequired",
        "repositoryResolvableEvidenceRequired",
        "supersededGenerationCannotBeCurrentlyEligible",
        "restorePairRequiresTwoEligibleGenerations",
        "restorePairRequiresDistinctEnvironmentIds",
    ):
        require(rules.get(key) is True, f"required eligibility rule missing: {key}")

    require(registry.get("appendOnly") is True and registry.get("productionEvidence") is False, "generation registry boundary drift")
    state = helper.derive(GEN_REGISTRY)
    expected = {
        "registeredGenerationCount": state["registeredGenerationCount"],
        "unsupersededGenerationCount": state["unsupersededGenerationCount"],
        "preflightEligibleGenerationCount": state["preflightEligibleGenerationCount"],
        "unsupersededPreflightEligibleGenerationCount": state["unsupersededPreflightEligibleGenerationCount"],
        "distinctPreflightEligibleEnvironmentCount": state["distinctPreflightEligibleEnvironmentCount"],
        "eligibleDirectedRestorePairCount": state["eligibleDirectedPairCount"],
    }
    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "eligibility authority state missing")
    for field, value in expected.items():
        require(boundary.get(field) == value, f"eligibility boundary drift: {field}")
    require(boundary.get("productionEvidence") is False and boundary.get("productionReady") is False and boundary.get("productionDecision") == "NO_GO", "eligibility authority cannot promote production")

    eligible_count = expected["preflightEligibleGenerationCount"]
    unsuperseded_eligible = expected["unsupersededPreflightEligibleGenerationCount"]
    distinct_eligible = expected["distinctPreflightEligibleEnvironmentCount"]
    pair_count = expected["eligibleDirectedRestorePairCount"]
    require(unsuperseded_eligible <= eligible_count <= expected["registeredGenerationCount"], "eligibility count ordering invalid")
    require(distinct_eligible <= unsuperseded_eligible, "distinct eligible environment count invalid")
    if pair_count > 0:
        require(unsuperseded_eligible >= 2 and distinct_eligible >= 2, "eligible restore pair requires two distinct eligible environments")
    if distinct_eligible < 2:
        require(pair_count == 0, "eligible restore pair cannot exist with fewer than two distinct eligible environments")

    generation_boundary = generation_contract.get("currentBoundary")
    require(isinstance(generation_boundary, dict), "generation contract boundary missing")
    require(generation_boundary.get("registeredGenerationCount") == expected["registeredGenerationCount"], "generation/eligibility registered count drift")
    require(generation_boundary.get("preflightEligibleGenerationCount") == eligible_count, "generation/eligibility eligible count drift")
    require(generation_boundary.get("productionEvidence") is False and generation_boundary.get("productionReady") is False, "generation contract cannot promote production")

    require(readiness.get("eligibleGenerationAvailable") is (eligible_count > 0), "eligibleGenerationAvailable drift")
    require(readiness.get("twoDistinctEligibleEnvironmentsAvailable") is (distinct_eligible >= 2), "twoDistinctEligibleEnvironmentsAvailable drift")
    require(readiness.get("eligibleDirectedRestorePairAvailable") is (pair_count > 0), "eligibleDirectedRestorePairAvailable drift")
    require(readiness.get("productionReady") is False, "eligibility authority cannot make production ready")

    print("Memory OS production-equivalent environment eligibility validation PASS")
    print(f"registered generations: {expected['registeredGenerationCount']}")
    print(f"preflight-eligible generations: {eligible_count}")
    print(f"unsuperseded preflight-eligible generations: {unsuperseded_eligible}")
    print(f"distinct preflight-eligible environments: {distinct_eligible}")
    print(f"eligible directed restore pairs: {pair_count}")
    print("eligibility helper executable authority pinned: true")
    print("unreadable eligibility authority accepted: false")
    print("registration implies eligibility: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT ENVIRONMENT ELIGIBILITY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
