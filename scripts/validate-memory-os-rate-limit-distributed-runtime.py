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
POLICY = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
WRITER = ROOT / "scripts/register-memory-os-rate-limit-distributed-runtime.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-distributed-runtime.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-rate-limit-distributed-runtime.py"
WORKFLOW = ROOT / ".github/workflows/rate-limit-distributed-runtime-admission.yml"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
LOCK = ROOT / "contracts/operations/.rate-limit-distributed-runtime.lock"
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


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_writer() -> ModuleType:
    return load_module(WRITER, "memory_os_rate_limit_runtime_writer")


def validate_writer_authority(writer: ModuleType) -> None:
    require(writer.ROOT.resolve() == ROOT.resolve(), "distributed runtime writer root authority drift")
    require(writer.CONTRACT.resolve() == CONTRACT.resolve(), "distributed runtime writer contract authority drift")
    require(writer.REGISTRY.resolve() == REGISTRY.resolve(), "distributed runtime writer registry authority drift")
    require(writer.POLICY.resolve() == POLICY.resolve(), "distributed runtime writer policy authority drift")
    require(writer.GEN_REGISTRY.resolve() == GEN_REGISTRY.resolve(), "distributed runtime writer generation registry authority drift")
    require(writer.GEN_WRITER.resolve() == GEN_WRITER.resolve(), "distributed runtime writer generation writer authority drift")
    require(writer.VALIDATOR.resolve() == VALIDATOR.resolve(), "distributed runtime writer validator authority drift")
    require(writer.LOCK.resolve() == LOCK.resolve(), "distributed runtime writer lock authority drift")


def validate_reconciler_authority(reconciler: ModuleType) -> None:
    require(reconciler.ROOT.resolve() == ROOT.resolve(), "distributed runtime reconciler root authority drift")
    require(reconciler.CONTRACT.resolve() == CONTRACT.resolve(), "distributed runtime reconciler contract authority drift")
    require(reconciler.REGISTRY.resolve() == REGISTRY.resolve(), "distributed runtime reconciler registry authority drift")
    require(reconciler.WRITER.resolve() == WRITER.resolve(), "distributed runtime reconciler writer authority drift")
    require(reconciler.VALIDATOR.resolve() == VALIDATOR.resolve(), "distributed runtime reconciler validator authority drift")
    require(reconciler.WORKFLOW.resolve() == WORKFLOW.resolve(), "distributed runtime reconciler workflow authority drift")
    require(reconciler.STATUS.resolve() == STATUS.resolve(), "distributed runtime reconciler status authority drift")


def validate_generation_authority(writer: ModuleType) -> list[dict[str, Any]]:
    try:
        rows = writer.validated_generation_rows()
    except Exception as exc:
        raise Fail(f"environment-generation authority invalid: {exc}") from exc
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows),
            "environment-generation validator returned invalid rows")
    return rows


def validate_registry_for_append(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the append-only runtime authority without consulting derived contract state."""
    require(set(registry) == EXPECTED_REGISTRY_FIELDS, "registry field drift")
    require(registry.get("schemaVersion") == "memory-os-rate-limit-distributed-runtime-admission-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    runtimes = registry.get("runtimes")
    require(isinstance(runtimes, list), "registry runtimes missing")
    writer = load_writer()
    validate_writer_authority(writer)
    validate_generation_authority(writer)
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


def require_runtime_authorities(
    _root: Path = ROOT,
    _paths: tuple[tuple[str, Path], ...] = (
        ("CONTRACT", CONTRACT),
        ("REGISTRY", REGISTRY),
        ("POLICY", POLICY),
        ("GEN_REGISTRY", GEN_REGISTRY),
        ("GEN_WRITER", GEN_WRITER),
        ("WRITER", WRITER),
        ("VALIDATOR", VALIDATOR),
        ("RECONCILER", RECONCILER),
        ("WORKFLOW", WORKFLOW),
        ("STATUS", STATUS),
        ("LOCK", LOCK),
    ),
    _helpers: tuple[tuple[str, object], ...] = (
        ("require", require),
        ("require_count", require_count),
        ("load", load),
        ("load_module", load_module),
        ("load_writer", load_writer),
        ("validate_writer_authority", validate_writer_authority),
        ("validate_reconciler_authority", validate_reconciler_authority),
        ("validate_generation_authority", validate_generation_authority),
        ("validate_registry_for_append", validate_registry_for_append),
    ),
) -> None:
    if ROOT != _root or ROOT.resolve() != _root.resolve():
        raise Fail("distributed runtime validator repository root authority drift")
    for attribute, canonical in _paths:
        current = globals().get(attribute)
        if current != canonical:
            raise Fail(f"distributed runtime validator {attribute} authority drift")
        if attribute != "LOCK":
            if not canonical.is_file() or canonical.is_symlink() or canonical.resolve() != current.resolve():
                raise Fail(f"distributed runtime validator {attribute} canonical file authority invalid")
        elif canonical.exists() and (canonical.is_symlink() or not canonical.is_file()):
            raise Fail("distributed runtime validator LOCK authority invalid")
    for name, canonical in _helpers:
        if globals().get(name) is not canonical:
            raise Fail(f"distributed runtime validator {name} execution authority drift")


def main(_guard=require_runtime_authorities) -> int:
    if _guard is not require_runtime_authorities or _guard is not main.__defaults__[0]:
        raise Fail("distributed runtime validator runtime guard authority drift")
    _guard()
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    require(contract.get("schemaVersion") == "memory-os-rate-limit-distributed-runtime-admission.v1", "contract schema drift")
    require(contract.get("recordSchemaVersion") == "memory-os-rate-limit-distributed-runtime-record.v1", "record schemaVersion drift")
    require(contract.get("independentReviewSchemaVersion") == "memory-os-rate-limit-runtime-independent-review.v1", "independent review schema drift")
    require(contract.get("sourcePolicyContract") == str(POLICY.relative_to(ROOT)), "policy binding drift")
    require(contract.get("environmentGenerationRegistry") == str(GEN_REGISTRY.relative_to(ROOT)), "generation registry binding drift")
    require(contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "registry binding drift")
    require(contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)), "append lock binding drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)), "writer binding drift")
    require(contract.get("validator") == str(VALIDATOR.relative_to(ROOT)), "validator binding drift")
    require(contract.get("reconcile") == str(RECONCILER.relative_to(ROOT)), "reconciler binding drift")
    require(contract.get("workflow") == str(WORKFLOW.relative_to(ROOT)), "workflow binding drift")
    writer = load_writer()
    validate_writer_authority(writer)
    reconciler = load_module(RECONCILER, "memory_os_rate_limit_runtime_reconciler_authority")
    validate_reconciler_authority(reconciler)
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
