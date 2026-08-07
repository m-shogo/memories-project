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
    return module


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    require(contract.get("schemaVersion") == "memory-os-observability-stack-deployment.v1", "contract schema drift")
    require(contract.get("recordSchemaVersion") == "memory-os-observability-stack-deployment-record.v1", "record schema drift")
    require(contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "registry binding drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)), "writer binding drift")
    requirements = contract.get("recordRequirements")
    require(isinstance(requirements, dict) and requirements and all(value is True for value in requirements.values()), "record requirements must remain fail-closed")
    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict) and promotion and all(value is False or key == "automaticProductionReadyForbidden" and value is True for key, value in promotion.items()), "promotion rules drift")

    require(registry.get("schemaVersion") == "memory-os-observability-stack-deployment-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must be append-only")
    stacks = registry.get("stacks")
    require(isinstance(stacks, list), "registry stacks missing")
    writer = load_writer()
    ids: set[str] = set()
    identities: set[str] = set()
    pe = 0
    prod = 0
    for index, record in enumerate(stacks):
        require(isinstance(record, dict), f"stacks[{index}] invalid")
        confirmation = writer.PRODUCTION_CONFIRMATION if record.get("environmentClass") == "PRODUCTION" else ""
        try:
            writer.validate_record(record, confirmation)
        except Exception as exc:
            raise Fail(f"stacks[{index}] validation failed: {exc}") from exc
        require(record["stackId"] not in ids, f"duplicate stackId: {record['stackId']}")
        require(record["environmentIdentityDigest"] not in identities, "duplicate environment identity digest")
        ids.add(record["stackId"])
        identities.add(record["environmentIdentityDigest"])
        pe += 1 if record["environmentClass"] == "PRODUCTION_EQUIVALENT" else 0
        prod += 1 if record["environmentClass"] == "PRODUCTION" else 0
    require(registry.get("admittedStackCount") == len(stacks), "admittedStackCount drift")
    require(registry.get("productionEquivalentStackCount") == pe, "productionEquivalentStackCount drift")
    require(registry.get("productionStackCount") == prod, "productionStackCount drift")
    require(registry.get("productionReady") is False, "stack registry cannot make application productionReady")

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
