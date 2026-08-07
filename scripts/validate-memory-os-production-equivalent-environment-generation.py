#!/usr/bin/env python3
"""Validate immutable production-equivalent environment generation authority."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
ENV_SCHEMA = ROOT / "contracts/operations/production-equivalent-environment-record.v1.schema.json"
GEN_SCHEMA = ROOT / "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json"
WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
ENV_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
GEN_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,95}$")
RECORD_FIELDS = {
    "schemaVersion", "environmentId", "generationId", "registeredAt",
    "sourceCommitSha", "environmentManifestSha256", "dependencyInventorySha256",
    "evidenceBundleManifestSha256", "materialDeltaLedgerSha256", "environmentRecordRef",
    "environmentRecordSha256", "supersedesGenerationId", "productionTraffic",
    "productionCredentials", "productionEvidence", "productionReady",
}


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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def commit_exists(sha: str) -> bool:
    completed = subprocess.run(
        ["git", "cat-file", "-e", sha + "^{commit}"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def repo_file(ref: Any, field: str) -> Path:
    require(isinstance(ref, str) and ref and not Path(ref).is_absolute(), f"{field} invalid")
    path = Path(ref)
    require(".." not in path.parts, f"{field} traversal forbidden")
    absolute = ROOT / path
    require(absolute.is_file(), f"{field} missing: {ref}")
    return absolute


def validate_generation_record(record: dict[str, Any], prior_by_environment: dict[str, str]) -> dict[str, Any]:
    require(set(record) == RECORD_FIELDS, f"generation record field drift: {sorted(set(record) ^ RECORD_FIELDS)}")
    require(record.get("schemaVersion") == "memory-os-production-equivalent-environment-generation-record.v1", "generation record schema drift")
    env_id = record.get("environmentId")
    gen_id = record.get("generationId")
    require(isinstance(env_id, str) and ENV_ID.fullmatch(env_id), "environmentId invalid")
    require(isinstance(gen_id, str) and GEN_ID.fullmatch(gen_id), "generationId invalid")
    require("latest" not in gen_id.lower() and "current" not in gen_id.lower(), "mutable generation alias forbidden")
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source), "sourceCommitSha invalid")
    require(commit_exists(source), f"sourceCommitSha not present in repository history: {source}")
    for field in (
        "environmentManifestSha256", "dependencyInventorySha256", "evidenceBundleManifestSha256",
        "materialDeltaLedgerSha256", "environmentRecordSha256",
    ):
        require(isinstance(record.get(field), str) and DIGEST.fullmatch(record[field]), f"{field} invalid")
    expected_supersedes = prior_by_environment.get(env_id)
    require(record.get("supersedesGenerationId") == expected_supersedes, f"supersedes chain drift for environment {env_id}")
    prior_by_environment[env_id] = gen_id
    for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
        require(record.get(field) is False, f"generation record cannot enable {field}")

    env_path = repo_file(record.get("environmentRecordRef"), "environmentRecordRef")
    require(record.get("environmentRecordSha256") == sha256(env_path), "environmentRecordSha256 mismatch")
    env = load(env_path)
    require(env.get("schemaVersion") == "memory-os-production-equivalent-environment-record.v1", "environment record schema drift")
    require(env.get("environmentId") == env_id and env.get("generationId") == gen_id, "environment/generation identity mismatch")
    topology = env.get("topology")
    identity = env.get("identityAndSecrets")
    boundary = env.get("evidenceBoundary")
    require(isinstance(topology, dict) and topology.get("productionTraffic") is False and topology.get("productionCredentials") is False, "generation environment must remain non-production")
    require(isinstance(identity, dict) and identity.get("containsSecretMaterial") is False, "generation environment contains secret material")
    require(isinstance(boundary, dict) and boundary.get("productionEvidence") is False and boundary.get("productionReady") is False, "generation environment production boundary drift")
    return env


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    env_schema = load(ENV_SCHEMA)
    gen_schema = load(GEN_SCHEMA)

    require(contract.get("schemaVersion") == "memory-os-production-equivalent-environment-generation.v1", "contract schema drift")
    require(contract.get("environmentRecordSchema") == str(ENV_SCHEMA.relative_to(ROOT)), "environment schema ref drift")
    require(contract.get("generationRegistryRecordSchema") == str(GEN_SCHEMA.relative_to(ROOT)), "generation record schema ref drift")
    require(contract.get("registry") == str(REGISTRY.relative_to(ROOT)), "registry ref drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)) and WRITER.is_file(), "generation writer ref drift")
    require(env_schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "environment schema draft drift")
    require(gen_schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "generation record schema draft drift")

    bindings = contract.get("bindingRules")
    require(isinstance(bindings, dict), "bindingRules required")
    for key, value in bindings.items():
        require(value is True, f"generation binding rule must remain true: {key}")
    material = contract.get("materialChangeRules")
    require(isinstance(material, dict) and material and all(value is True for value in material.values()), "material change rules must remain fail-closed")
    result_rules = contract.get("resultAdmissionRules")
    require(isinstance(result_rules, dict) and result_rules and all(value is True for value in result_rules.values()), "result admission rules must remain fail-closed")

    require(registry.get("schemaVersion") == "memory-os-production-equivalent-environment-generation-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "generation registry must be append-only")
    require(registry.get("productionEvidence") is False, "generation registry cannot itself be production evidence")
    count = registry.get("registeredGenerationCount")
    rows = registry.get("generations")
    require(isinstance(count, int) and count >= 0, "registeredGenerationCount invalid")
    require(isinstance(rows, list) and len(rows) == count and all(isinstance(row, dict) for row in rows), "generation registry count mismatch")
    ids: set[str] = set()
    prior_by_environment: dict[str, str] = {}
    env_by_generation: dict[str, dict[str, Any]] = {}
    for row in rows:
        generation_id = row.get("generationId")
        require(isinstance(generation_id, str) and generation_id not in ids, f"duplicate generationId: {generation_id}")
        ids.add(generation_id)
        env_by_generation[generation_id] = validate_generation_record(row, prior_by_environment)

    current_id = registry.get("currentGenerationId")
    if count == 0:
        require(current_id is None, "empty generation registry must have null currentGenerationId")
        current_env = None
    else:
        require(current_id == rows[-1].get("generationId"), "currentGenerationId must equal latest append-only registry record")
        current_env = env_by_generation[current_id]

    derived_provisioned = bool(current_env and current_env.get("status") in {"PROVISIONED_UNVALIDATED", "VALIDATION_IN_PROGRESS", "VALIDATED_LOCAL_NONPRODUCTION"})
    derived_validated = bool(current_env and current_env.get("status") == "VALIDATED_LOCAL_NONPRODUCTION")
    current_evidence_boundary = current_env.get("evidenceBoundary", {}) if current_env else {}
    derived_reviewed = bool(derived_validated and current_evidence_boundary.get("independentReviewCompleted") is True)
    derived_equivalent = bool(derived_reviewed and current_evidence_boundary.get("productionEquivalentDependencies") is True)

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "currentBoundary required")
    require(boundary.get("registeredGenerationCount") == count, "contract/registry generation count mismatch")
    require(boundary.get("currentGenerationId") == current_id, "current generation drift")
    require(boundary.get("environmentProvisioned") is derived_provisioned, "environmentProvisioned derivation drift")
    require(boundary.get("environmentValidated") is derived_validated, "environmentValidated derivation drift")
    require(boundary.get("productionEquivalentDependencies") is derived_equivalent, "productionEquivalentDependencies derivation drift")
    require(boundary.get("productionEvidence") is False and boundary.get("productionReady") is False, "generation authority cannot promote production")
    require(boundary.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness required")
    for key in ("contractDefined", "registryDefined", "registryRecordSchemaDefined", "writerImplemented", "validatorImplemented", "automaticWorkflowImplemented"):
        require(readiness.get(key) is True, f"generation foundation incomplete: {key}")
    require(readiness.get("generationRegistered") is (count > 0), "generationRegistered derivation drift")
    require(readiness.get("generationEvidenceBound") is (count > 0), "generationEvidenceBound derivation drift")
    require(readiness.get("independentReviewCompleted") is derived_reviewed, "independentReviewCompleted derivation drift")
    require(readiness.get("productionEquivalentDependencies") is derived_equivalent, "readiness productionEquivalentDependencies drift")
    require(readiness.get("productionReady") is False, "generation authority cannot make application production ready")

    print("Memory OS production-equivalent environment generation validation PASS")
    print(f"registered generations: {count}")
    print(f"current generation: {current_id or 'none'}")
    print(f"production-equivalent dependencies: {str(derived_equivalent).lower()}")
    print("cross-generation evidence reuse: forbidden")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT GENERATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
