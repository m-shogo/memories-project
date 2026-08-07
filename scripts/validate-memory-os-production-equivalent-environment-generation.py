#!/usr/bin/env python3
"""Validate fail-closed generation binding for future production-equivalent evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
SCHEMA = ROOT / "contracts/operations/production-equivalent-environment-record.v1.schema.json"


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


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    schema = load(SCHEMA)

    require(contract.get("schemaVersion") == "memory-os-production-equivalent-environment-generation.v1", "contract schema drift")
    require(contract.get("environmentRecordSchema") == str(SCHEMA.relative_to(ROOT)), "environment schema ref drift")
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "environment schema draft drift")

    bindings = contract.get("bindingRules")
    require(isinstance(bindings, dict), "bindingRules required")
    for key in (
        "generationIdRequired",
        "environmentManifestSha256Required",
        "dependencyInventorySha256Required",
        "evidenceBundleManifestSha256Required",
        "sourceCommitShaRequired",
        "materialDeltaLedgerSha256Required",
        "restoreEvidenceGenerationMustMatch",
        "loadEvidenceGenerationMustMatch",
        "failureDrillGenerationMustMatch",
        "reviewEvidenceGenerationMustMatch",
        "crossGenerationEvidenceReuseForbidden",
        "mutableLatestAliasForbiddenAsEvidenceKey",
        "unknownGenerationFailsClosed",
    ):
        require(bindings.get(key) is True, f"generation binding rule must remain true: {key}")

    material = contract.get("materialChangeRules")
    require(isinstance(material, dict) and material, "materialChangeRules required")
    for key, value in material.items():
        require(value is True, f"material change must create new generation: {key}")

    result_rules = contract.get("resultAdmissionRules")
    require(isinstance(result_rules, dict) and result_rules, "resultAdmissionRules required")
    for key, value in result_rules.items():
        require(value is True, f"result admission rule must remain true: {key}")

    require(registry.get("schemaVersion") == "memory-os-production-equivalent-environment-generation-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "generation registry must be append-only")
    require(registry.get("productionEvidence") is False, "generation registry cannot itself be production evidence")
    count = registry.get("registeredGenerationCount")
    rows = registry.get("generations")
    require(isinstance(count, int) and count >= 0, "registeredGenerationCount invalid")
    require(isinstance(rows, list) and len(rows) == count, "generation registry count mismatch")

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "currentBoundary required")
    require(boundary.get("registeredGenerationCount") == count, "contract/registry generation count mismatch")
    require(boundary.get("currentGenerationId") == registry.get("currentGenerationId"), "current generation drift")
    if count == 0:
        require(registry.get("currentGenerationId") is None, "empty generation registry must have null currentGenerationId")
        require(boundary.get("currentGenerationId") is None, "empty boundary must have null currentGenerationId")
    for key in ("environmentProvisioned", "environmentValidated", "productionEquivalentDependencies", "productionEvidence", "productionReady"):
        require(boundary.get(key) is False, f"generation foundation cannot enable {key}")
    require(boundary.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness required")
    require(readiness.get("contractDefined") is True and readiness.get("registryDefined") is True, "generation foundation definition drift")
    for key in ("validatorImplemented", "automaticWorkflowImplemented"):
        require(isinstance(readiness.get(key), bool), f"readiness.{key} must be boolean")
    for key in ("generationRegistered", "generationEvidenceBound", "independentReviewCompleted", "productionEquivalentDependencies", "productionReady"):
        require(readiness.get(key) is False, f"empty generation foundation cannot enable readiness.{key}")

    print("Memory OS production-equivalent environment generation validation PASS")
    print(f"registered generations: {count}")
    print("cross-generation evidence reuse: forbidden")
    print("mutable latest alias as evidence key: forbidden")
    print("production-equivalent dependencies: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT GENERATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
