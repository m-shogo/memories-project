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
CONTRACT_REL = Path("contracts/operations/production-equivalent-environment-generation-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
ENV_SCHEMA_REL = Path("contracts/operations/production-equivalent-environment-record.v1.schema.json")
GEN_SCHEMA_REL = Path("contracts/operations/production-equivalent-environment-generation-record.v1.schema.json")
ENV_VALIDATOR_REL = Path("scripts/validate-memory-os-production-equivalent-environment-record.py")
WRITER_REL = Path("scripts/register-memory-os-production-equivalent-environment-generation.py")
EXPECTED_LOCK_REL = Path("contracts/operations/.production-equivalent-environment-generation.lock")
NEGATIVE_REL = Path("scripts/validate-memory-os-production-equivalent-environment-generation-negative.py")
SOURCE_BINDING_NEGATIVE_REL = Path("scripts/validate-memory-os-production-equivalent-environment-generation-source-binding-negative.py")
LINEAGE_NEGATIVE_REL = Path("scripts/validate-memory-os-production-equivalent-environment-generation-lineage-negative.py")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
ENV_SCHEMA = ROOT / ENV_SCHEMA_REL
GEN_SCHEMA = ROOT / GEN_SCHEMA_REL
ENV_VALIDATOR = ROOT / ENV_VALIDATOR_REL
WRITER = ROOT / WRITER_REL
EXPECTED_LOCK = ROOT / EXPECTED_LOCK_REL
NEGATIVE = ROOT / NEGATIVE_REL
SOURCE_BINDING_NEGATIVE = ROOT / SOURCE_BINDING_NEGATIVE_REL
LINEAGE_NEGATIVE = ROOT / LINEAGE_NEGATIVE_REL
EXPECTED_NEGATIVE_CASES = {
    "environment record missing required nested section",
    "environment record unknown nested field",
    "environment record production traffic or credentials enabled",
    "environment record contains secret material",
    "productionEquivalentDependencies true with incomplete dependency controls",
    "productionEquivalentDependencies true with missing evidence ref",
    "independent review completed without review evidence ref",
    "accepted material delta without independent review evidence",
    "absolute, parent-traversal or symlinked environment evidence ref",
    "absolute, parent-traversal or symlinked environment record ref",
    "semantic environment validator implementation exception",
    "mutable generation alias",
    "environment record digest mismatch",
    "missing environment record path",
    "source commit exists but is not an ancestor of the current validation HEAD",
    "production evidence relabel",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


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


def require_canonical_lock_path(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        parent = path.parent.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} parent missing or escapes repository") from exc
    require(lexical == expected_relative, f"{field} authority drift")
    require(parent == expected_relative.parent, f"{field} parent authority drift")
    require(not path.is_symlink(), f"{field} must not be symlink")
    if path.exists():
        require(path.is_file(), f"{field} must be a file when materialized")
        try:
            resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
        except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
            raise Fail(f"{field} materialized path escapes repository") from exc
        require(resolved == expected_relative, f"{field} materialized authority drift")
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "environment generation contract"),
        (REGISTRY, REGISTRY_REL, "environment generation registry"),
        (ENV_SCHEMA, ENV_SCHEMA_REL, "environment record schema"),
        (GEN_SCHEMA, GEN_SCHEMA_REL, "generation record schema"),
        (ENV_VALIDATOR, ENV_VALIDATOR_REL, "environment record semantic validator"),
        (WRITER, WRITER_REL, "environment generation writer"),
        (NEGATIVE, NEGATIVE_REL, "environment generation negative validator"),
        (SOURCE_BINDING_NEGATIVE, SOURCE_BINDING_NEGATIVE_REL, "environment generation source-binding negative validator"),
        (LINEAGE_NEGATIVE, LINEAGE_NEGATIVE_REL, "environment generation source-lineage negative validator"),
    ):
        require_exact_repo_file(path, expected, field)
    require_canonical_lock_path(EXPECTED_LOCK, EXPECTED_LOCK_REL, "environment generation append lock")


def repo_file(ref: Any, field: str) -> Path:
    require(isinstance(ref, str) and ref and ref == ref.strip(), f"generation artifact ref invalid: {field}")
    candidate = Path(ref)
    require(not candidate.is_absolute() and ".." not in candidate.parts, f"generation artifact ref must be canonical repository-relative path: {field}")
    path = ROOT / candidate
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"generation artifact must resolve inside repository: {field}") from exc
    require(resolved.is_file(), f"generation artifact missing: {field}")
    require(resolved.relative_to(ROOT.resolve()) == candidate, f"generation artifact must resolve to its canonical repository path: {field}")
    return resolved


def load(path: Path) -> dict[str, Any]:
    try:
        relative = path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"authority path escapes repository: {path}") from exc
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def load_writer():
    require_exact_repo_file(WRITER, WRITER_REL, "environment generation writer")
    writer_path = WRITER
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_writer_for_validator", writer_path)
    require(spec is not None and spec.loader is not None, "cannot load environment generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_suite(path: Path, expected_relative: Path, label: str) -> None:
    require_exact_repo_file(path, expected_relative, label)
    completed = subprocess.run([sys.executable, str(path)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"{label} failed:\n{completed.stdout[-8000:]}{completed.stderr[-8000:]}")


def main() -> int:
    enforce_runtime_authorities()
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    env_schema = load(ENV_SCHEMA)
    gen_schema = load(GEN_SCHEMA)
    writer = load_writer()

    writer_authorities = (
        ("CONTRACT", "CANONICAL_CONTRACT", CONTRACT, "environment generation contract"),
        ("REGISTRY", "CANONICAL_REGISTRY", REGISTRY, "environment generation registry"),
        ("ENV_SCHEMA", "CANONICAL_ENV_SCHEMA", ENV_SCHEMA, "environment record schema"),
        ("GEN_SCHEMA", "CANONICAL_GEN_SCHEMA", GEN_SCHEMA, "generation record schema"),
        ("ENV_VALIDATOR", "CANONICAL_ENV_VALIDATOR", ENV_VALIDATOR, "environment record semantic validator"),
    )
    for runtime_name, canonical_name, expected_path, field in writer_authorities:
        runtime_path = getattr(writer, runtime_name, None)
        canonical_path = getattr(writer, canonical_name, None)
        require(runtime_path == expected_path, f"writer runtime authority drift: {runtime_name}")
        require(canonical_path == expected_path, f"writer canonical authority drift: {canonical_name}")
        writer.require_canonical_runtime_authority(runtime_path, canonical_path, field)
    writer_lock = getattr(writer, "LOCK", None)
    require(writer_lock == EXPECTED_LOCK, "writer append lock authority drift")
    require_canonical_lock_path(writer_lock, EXPECTED_LOCK_REL, "writer environment generation append lock")
    require(writer_lock.parent == REGISTRY.parent, "writer append lock must share registry authority directory")
    try:
        writer.validate_registry_for_append(registry)
    except writer.Fail as exc:
        raise Fail(f"generation registry append authority invalid: {exc}") from exc

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
        require(repo_file(str(path.relative_to(ROOT)), field) == path.resolve(), f"generation artifact canonical path drift: {field}")
    require_exact_repo_file(SOURCE_BINDING_NEGATIVE, SOURCE_BINDING_NEGATIVE_REL, "source-binding negative validator")
    require_exact_repo_file(LINEAGE_NEGATIVE, LINEAGE_NEGATIVE_REL, "source-lineage negative validator")
    for field in ("validator", "workflow"):
        repo_file(contract.get(field), field)
    require(env_schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "environment schema draft drift")
    require(gen_schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "generation record schema draft drift")
    evidence_boundary_schema = env_schema.get("properties", {}).get("evidenceBoundary", {})
    require("independentReviewRef" in evidence_boundary_schema.get("required", []), "environment schema must require independentReviewRef field")

    bindings = contract.get("bindingRules")
    require(isinstance(bindings, dict) and bindings and all(value is True for value in bindings.values()), "generation binding rules must remain fail-closed")
    for key in (
        "sourceCommitShaMustBeAncestorOfCurrentHead",
        "environmentRecordFullSemanticValidationRequired",
        "environmentRecordRefMustBeCanonicalRepositoryFile",
        "environmentRecordMustMatchSourceCommitSha",
        "semanticValidatorImplementationErrorsMustSurface",
        "allNonNullEnvironmentEvidenceRefsMustResolveInRepository",
        "allNonNullEnvironmentEvidenceRefsMustMatchSourceCommitSha",
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
    require(
        isinstance(negative_cases, list)
        and len(negative_cases) == len(set(negative_cases))
        and set(negative_cases) == EXPECTED_NEGATIVE_CASES,
        "generation negative admission case authority drift",
    )

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
        require(isinstance(env_ref, str), "environment record ref missing after writer validation")
        env_by_generation[generation_id] = load(repo_file(env_ref, "environmentRecordRef"))

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

    run_suite(NEGATIVE, NEGATIVE_REL, "environment generation negative admission suite")
    run_suite(SOURCE_BINDING_NEGATIVE, SOURCE_BINDING_NEGATIVE_REL, "environment generation source-binding negative suite")
    run_suite(LINEAGE_NEGATIVE, LINEAGE_NEGATIVE_REL, "environment generation source-lineage negative suite")

    print("Memory OS production-equivalent environment generation validation PASS")
    print("environment generation validator canonical runtime authorities enforced: true")
    print("ephemeral append lock may be absent but path authority remains canonical: true")
    print(f"registered generations: {count}")
    print(f"preflight-eligible generations: {preflight_eligible_count}")
    print(f"current generation: {current_id or 'none'}")
    print(f"current production-equivalent dependencies: {str(derived_equivalent).lower()}")
    print("registration implies preflight eligibility: false")
    print("boolean generation counts accepted: false")
    print("canonical environmentRecordRef required: true")
    print("environmentRecordRef source-bound: true")
    print("environment evidence refs source-bound: true")
    print("sourceCommitSha ancestor-only: true")
    print("canonical writer runtime authorities validated without generation rows: true")
    print("canonical writer append lock authority validated: true")
    print("semantic environment evidence refs canonical: true")
    print("semantic validator implementation exceptions surfaced: true")
    print("unexpected generation-writer exceptions normalized as expected rejection: false")
    print("cross-generation evidence reuse: forbidden")
    print("negative admission case authority exact: true")
    print("negative admission suite: PASS")
    print("source-binding negative suite: PASS")
    print("source-lineage negative suite: PASS")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT GENERATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
