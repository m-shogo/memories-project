#!/usr/bin/env python3
"""Validate integrated observability-stack deployment admission records."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/observability-stack-deployment-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-observability-stack-deployment.py"
LOCK = ROOT / "contracts/operations/.observability-stack-deployment.lock"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_observability_stack_writer", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load stack writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "CONTRACT", None) == CONTRACT,
            "stack writer contract authority drift")
    require(getattr(module, "REGISTRY", None) == REGISTRY,
            "stack writer registry authority drift")
    require(getattr(module, "LOCK", None) == LOCK,
            "stack writer append lock authority drift")
    require(getattr(module, "GEN_REGISTRY", None) == GEN_REGISTRY,
            "stack writer generation registry authority drift")
    require(getattr(module, "GEN_WRITER", None) == GEN_WRITER,
            "stack writer generation executable authority drift")
    require(callable(getattr(module, "validate_registry_for_append", None)),
            "stack writer registry validator missing")
    require(callable(getattr(module, "commit_registry_candidate", None)),
            "stack writer transactional append authority missing")
    return module


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    require(contract.get("schemaVersion") == "memory-os-observability-stack-deployment.v1", "contract schema drift")
    require(contract.get("recordSchemaVersion") == "memory-os-observability-stack-deployment-record.v1", "record schema drift")
    require(contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "registry binding drift")
    require(contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)), "append lock binding drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)), "writer binding drift")
    require(contract.get("environmentGenerationRegistry") == str(GEN_REGISTRY.relative_to(ROOT)), "generation registry contract binding drift")
    requirements = contract.get("recordRequirements")
    require(isinstance(requirements, dict) and requirements and all(value is True for value in requirements.values()), "record requirements must remain fail-closed")
    require(requirements.get("appendLockMustRemainCanonical") is True, "append lock requirement drift")
    require(requirements.get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
            "transactional append rollback requirement drift")
    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict) and promotion and all(value is False or key == "automaticProductionReadyForbidden" and value is True for key, value in promotion.items()), "promotion rules drift")

    writer = load_writer()
    try:
        writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"stack registry invalid: {exc}") from exc
    stacks = registry["stacks"]
    pe = registry["productionEquivalentStackCount"]
    prod = registry["productionStackCount"]

    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "contract authority missing")
    require(current.get("admittedStackCount") in {0, len(stacks)}, "current admitted count drift before reconcile")
    require(current.get("productionReady") is False and current.get("productionDecision") == "NO_GO", "production boundary drift")
    require(readiness.get("productionReady") is False, "readiness cannot promote production")
    print("Memory OS observability stack deployment validation PASS")
    print(f"admitted stacks: {len(stacks)}")
    print(f"production-equivalent stacks: {pe}")
    print(f"production stacks: {prod}")
    print("application production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OBSERVABILITY STACK VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
