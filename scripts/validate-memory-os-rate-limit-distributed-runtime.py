#!/usr/bin/env python3
"""Validate generation-bound distributed rate-limit runtime admission."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-rate-limit-distributed-runtime.py"
EXPECTED_REGISTRY_FIELDS = {
    "schemaVersion",
    "appendOnly",
    "admittedRuntimeCount",
    "productionEquivalentRuntimeCount",
    "productionRuntimeCount",
    "runtimes",
    "productionReady",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_count(value: Any, expected: int, field: str) -> None:
    require(isinstance(value, int) and not isinstance(value, bool), f"{field} must be integer, not boolean")
    require(value == expected, f"{field} drift")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_rate_limit_runtime_writer", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load distributed runtime writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_registry_for_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the append-only runtime authority without consulting derived contract state."""
    require(set(registry) == EXPECTED_REGISTRY_FIELDS, "registry field drift")
    require(registry.get("schemaVersion") == "memory-os-rate-limit-distributed-runtime-admission-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    runtimes = registry.get("runtimes")
    require(isinstance(runtimes, list), "registry runtimes missing")
    writer = load_writer()
    ids: set[str] = set()
    identities: set[str] = set()
    pe = 0
    prod = 0
    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(runtimes):
        require(isinstance(record, dict), f"runtimes[{index}] invalid")
        confirmation = writer.PRODUCTION_CONFIRMATION if record.get("environmentClass") == "PRODUCTION" else ""
        try:
            writer.validate_record(record, confirmation)
        except Exception as exc:
            raise Fail(f"runtimes[{index}] invalid: {exc}") from exc
        require(record["runtimeId"] not in ids, f"duplicate runtimeId: {record['runtimeId']}")
        require(record["environmentIdentityDigest"] not in identities, "duplicate environment identity digest")
        ids.add(record["runtimeId"])
        identities.add(record["environmentIdentityDigest"])
        pe += 1 if record["environmentClass"] == "PRODUCTION_EQUIVALENT" else 0
        prod += 1 if record["environmentClass"] == "PRODUCTION" else 0
        normalized.append(record)
    require_count(registry.get("admittedRuntimeCount"), len(runtimes), "admittedRuntimeCount")
    require_count(registry.get("productionEquivalentRuntimeCount"), pe, "productionEquivalentRuntimeCount")
    require_count(registry.get("productionRuntimeCount"), prod, "productionRuntimeCount")
    require(registry.get("productionReady") is False, "registry cannot make application productionReady")
    return normalized


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    require(contract.get("schemaVersion") == "memory-os-rate-limit-distributed-runtime-admission.v1", "contract schema drift")
    require(contract.get("recordSchemaVersion") == "memory-os-rate-limit-distributed-runtime-record.v1", "record schema drift")
    require(contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "registry binding drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)), "writer binding drift")
    assertions = contract.get("requiredRuntimeAssertions")
    require(isinstance(assertions, dict) and assertions and all(value is True for value in assertions.values()), "required runtime assertions must remain true")
    drills = contract.get("requiredDrillClasses")
    require(drills == [
        "CROSS_INSTANCE_SHARED_BUDGET",
        "RUNTIME_RESTART_CONTINUITY",
        "SHARED_STORE_UNAVAILABLE_FAIL_CLOSED",
        "TRUSTED_PROXY_MISCONFIGURATION_FAIL_CLOSED",
        "EMERGENCY_MODE_AUTOMATIC_EXPIRY",
        "NORMAL_MODE_RESTORATION",
    ], "required drill class set drift")
    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict), "promotionRules missing")
    for key, value in promotion.items():
        if key == "automaticProductionReadyForbidden":
            require(value is True, "automatic production-ready prohibition must remain true")
        else:
            require(value is False, f"unsafe distributed-runtime promotion enabled: {key}")

    runtimes = validate_registry_for_append(registry)
    pe = sum(1 for record in runtimes if record["environmentClass"] == "PRODUCTION_EQUIVALENT")
    prod = sum(1 for record in runtimes if record["environmentClass"] == "PRODUCTION")

    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "contract authority missing")
    require(current.get("admittedRuntimeCount") in {0, len(runtimes)}, "current admitted count drift before reconcile")
    require(current.get("productionReady") is False and current.get("productionDecision") == "NO_GO", "production boundary drift")
    require(readiness.get("productionReady") is False, "readiness cannot promote production")
    print("Memory OS distributed rate-limit runtime validation PASS")
    print(f"admitted runtimes: {len(runtimes)}")
    print(f"production-equivalent runtimes: {pe}")
    print(f"production runtimes: {prod}")
    print("application production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DISTRIBUTED RATE LIMIT RUNTIME VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
