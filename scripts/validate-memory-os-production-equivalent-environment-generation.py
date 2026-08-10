#!/usr/bin/env python3
"""Validate immutable production-equivalent environment generation authority."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
ENV_SCHEMA = ROOT / "contracts/operations/production-equivalent-environment-record.v1.schema.json"
GEN_SCHEMA = ROOT / "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json"
ENV_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-record.py"
WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
NEGATIVE = ROOT / "scripts/validate-memory-os-production-equivalent-environment-generation-negative.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_writer_for_validator", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load environment generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_negative() -> None:
    completed = subprocess.run([sys.executable, str(NEGATIVE)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"environment generation negative admission suite failed:\n{completed.stdout[-8000:]}{completed.stderr[-8000:]}")


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    env_schema = load(ENV_SCHEMA)
    gen_schema = load(GEN_SCHEMA)
    writer = load_writer()

    require(contract.get("schemaVersion") == "memory-os-production-equivalent-environment-generation.v1", "contract schema drift")
    expected_refs = {
        "environmentRecordSchema": ENV_SCHEMA,
        "environmentRecordSemanticValidator": ENV_VALIDATOR,
        "generationRegistryRecordSchema": GEN_SCHEMA,
        "registry": REGISTRY,
        "writer": WRITER,
        "negativeAdmissionValidator": NEGATIVE,
    }
    for field, path in expected_refs.items():
        require(contract.get(field) == str(path.relative_to(ROOT)), f"contract ref drift: {field}")
        require(path.is_file(), f"generation artifact missing: {field}")
    for field in ("validator", "workflow"):
        ref = contract.get(field)
        require(isinstance(ref, str) and ref and (ROOT / ref).is_file(), f"generation artifact missing: {field}")
    require(env_schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "environment schema draft drift")
    require(gen_schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "generation record schema draft drift")
    evidence_boundary_schema = env_schema.get("properties", {}).get("evidenceBoundary", {})
    require("independentReviewRef" in evidence_boundary_schema.get("required", []), "environment schema must require independentReviewRef field")

    bindings = contract.get("bindingRules")
    require(isinstance(bindings, dict) and bindings and all(value is True for value in bindings.values()), "generation binding rules must remain fail-closed")
    for key in (
        "environmentRecordFullSemanticValidationRequired",
        "allNonNullEnvironmentEvidenceRefsMustResolveInRepository",
        "equivalentEnvironmentRequiresIndependentReviewEvidence",
        "registrationDoesNotImplyPreflightEligibility",
        "preflightEligibilityRequiresValidatedEquivalentDependenciesAndIndependentReview",
    ):
        require(bindings.get(key) is True, f"required generation binding rule missing: {key}")
    material = contract.get("materialChangeRules")
    require(isinstance(material, dict) and material and all(value is True for value in material.values()), "material change rules must remain fail-closed")
    result_rules = contract.get("resultAdmissionRules")
    require(isinstance(result_rules, dict) and result_rules and all(value is True for value in result_rules.values()), "result admission rules must remain fail-closed")
    negative_cases = contract.get("negativeAdmissionCases")
    require(isinstance(negative_cases, list) and len(negative_cases) >= 10 and len(negative_cases) == len(set(negative_cases)), "generation negative admission cases incomplete or duplicated")

    require(registry.get("schemaVersion") == "memory-os-production-equivalent-environment-generation-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "generation registry must be append-only")
    require(registry.get("productionEvidence") is False, "generation registry cannot itself be production evidence")
    count = registry.get("registeredGenerationCount")
    rows = registry.get("generations")
    require(isinstance(count, int) and not isinstance(count, bool) and count >= 0, "registeredGenerationCount invalid")
    require(isinstance(rows, list) and len(rows) == count and all(isinstance(row, dict) for row in rows), "generation registry count mismatch")

    ids: set[str] = set()
    prior_by_environment: dict[str, str] = {}
    eligibility_by_id: dict[str, bool] = {}
    env_by_generation: dict[str, dict[str, Any]] = {}
    for row in rows:
        generation_id = row.get("generationId")
        environment_id = row.get("environmentId")
        require(isinstance(generation_id, str) and generation_id not in ids, f"duplicate generationId: {generation_id}")
        ids.add(generation_id)
        expected_supersedes = prior_by_environment.get(environment_id)
        require(row.get("supersedesGenerationId") == expected_supersedes, f"supersedes chain drift for environment {environment_id}")
        require(isinstance(environment_id, str), "environmentId invalid")
        prior_by_environment[environment_id] = generation_id
        try:
            eligible = writer.validate_record(row)
        except writer.Fail as exc:
            raise Fail(f"generation record validation failed for {generation_id}: {exc}") from exc
        require(isinstance(eligible, bool), "generation semantic eligibility predicate invalid")
        eligibility_by_id[generation_id] = eligible
        env_ref = row.get("environmentRecordRef")
        require(isinstance(env_ref, str) and (ROOT / env_ref).is_file(), "environment record ref missing after writer validation")
        env_by_generation[generation_id] = load(ROOT / env_ref)

    current_id = registry.get("currentGenerationId")
    if count == 0:
        require(current_id is None, "empty generation registry must have null currentGenerationId")
        current_env = None
    else:
        require(current_id == rows[-1].get("generationId"), "currentGenerationId must equal latest append-only registry record")
        current_env = env_by_generation[current_id]

    preflight_eligible_count = sum(1 for value in eligibility_by_id.values() if value)
    derived_provisioned = bool(current_env and current_env.get("status") in {"PROVISIONED_UNVALIDATED", "VALIDATION_IN_PROGRESS", "VALIDATED_LOCAL_NONPRODUCTION"})
    derived_validated = bool(current_env and current_env.get("status") == "VALIDATED_LOCAL_NONPRODUCTION")
    current_eligible = bool(current_id and eligibility_by_id.get(current_id) is True)
    current_evidence_boundary = current_env.get("evidenceBoundary", {}) if current_env else {}
    derived_reviewed = bool(current_eligible and current_evidence_boundary.get("independentReviewCompleted") is True)
    derived_equivalent = current_eligible

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "currentBoundary required")
    boundary_registered_count = boundary.get("registeredGenerationCount")
    boundary_eligible_count = boundary.get("preflightEligibleGenerationCount")
    require(isinstance(boundary_registered_count, int) and not isinstance(boundary_registered_count, bool), "contract registeredGenerationCount must be integer")
    require(isinstance(boundary_eligible_count, int) and not isinstance(boundary_eligible_count, bool), "contract preflightEligibleGenerationCount must be integer")
    require(boundary_registered_count == count, "contract/registry generation count mismatch")
    require(boundary_eligible_count == preflight_eligible_count, "preflightEligibleGenerationCount derivation drift")
    require(boundary.get("currentGenerationId") == current_id, "current generation drift")
    require(boundary.get("environmentProvisioned") is derived_provisioned, "environmentProvisioned derivation drift")
    require(boundary.get("environmentValidated") is derived_validated, "environmentValidated derivation drift")
    require(boundary.get("productionEquivalentDependencies") is derived_equivalent, "productionEquivalentDependencies derivation drift")
    require(boundary.get("productionEvidence") is False and boundary.get("productionReady") is False, "generation authority cannot promote production")
    require(boundary.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness required")
    for key in (
        "contractDefined", "registryDefined", "registryRecordSchemaDefined", "environmentRecordSemanticValidatorImplemented",
        "writerImplemented", "validatorImplemented", "negativeAdmissionSuiteImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(key) is True, f"generation foundation incomplete: {key}")
    require(readiness.get("generationRegistered") is (count > 0), "generationRegistered derivation drift")
    require(readiness.get("preflightEligibleGenerationAvailable") is (preflight_eligible_count > 0), "preflightEligibleGenerationAvailable drift")
    require(readiness.get("generationEvidenceBound") is (count > 0), "generationEvidenceBound derivation drift")
    require(readiness.get("independentReviewCompleted") is derived_reviewed, "independentReviewCompleted derivation drift")
    require(readiness.get("productionEquivalentDependencies") is derived_equivalent, "readiness productionEquivalentDependencies drift")
    require(readiness.get("productionReady") is False, "generation authority cannot make application production ready")

    run_negative()

    print("Memory OS production-equivalent environment generation validation PASS")
    print(f"registered generations: {count}")
    print(f"preflight-eligible generations: {preflight_eligible_count}")
    print(f"current generation: {current_id or 'none'}")
    print(f"current production-equivalent dependencies: {str(derived_equivalent).lower()}")
    print("registration implies preflight eligibility: false")
    print("boolean generation counts accepted: false")
    print("unexpected generation-writer exceptions normalized as expected rejection: false")
    print("cross-generation evidence reuse: forbidden")
    print("negative admission suite: PASS")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT GENERATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
