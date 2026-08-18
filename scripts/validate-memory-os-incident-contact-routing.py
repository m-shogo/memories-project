#!/usr/bin/env python3
"""Validate incident-contact routing admission registry."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/incident-contact-routing-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/incident-contact-routing-admission-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-incident-contact-routing.py"
LOCK = ROOT / "contracts/operations/.incident-contact-routing.lock"
OBS_REGISTRY = ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json"
OBS_WRITER = ROOT / "scripts/register-memory-os-observability-stack-deployment.py"


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
    spec = importlib.util.spec_from_file_location("memory_os_incident_contact_writer", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load contact routing writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "CONTRACT", None) == CONTRACT,
            "contact routing writer contract authority drift")
    require(getattr(module, "REGISTRY", None) == REGISTRY,
            "contact routing writer registry authority drift")
    require(getattr(module, "LOCK", None) == LOCK,
            "contact routing writer append lock authority drift")
    require(getattr(module, "OBS_REGISTRY", None) == OBS_REGISTRY,
            "contact routing observability registry authority drift")
    require(getattr(module, "OBS_WRITER", None) == OBS_WRITER,
            "contact routing observability executable authority drift")
    require(callable(getattr(module, "validate_registry_for_append", None)),
            "contact routing writer registry validator missing")
    require(callable(getattr(module, "commit_registry_candidate", None)),
            "contact routing transactional append authority missing")
    return module


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    require(contract.get("schemaVersion") == "memory-os-incident-contact-routing-admission.v1", "contract schema drift")
    require(contract.get("recordSchemaVersion") == "memory-os-incident-contact-routing-record.v1", "record schema drift")
    require(contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "registry binding drift")
    require(contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)), "append lock binding drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)), "writer binding drift")
    require(contract.get("sourceObservabilityStackRegistry") == str(OBS_REGISTRY.relative_to(ROOT)), "observability registry contract binding drift")
    required_classes = contract.get("requiredContactClasses")
    require(required_classes == [
        "INCIDENT_COMMAND",
        "SECURITY_PRIVACY",
        "SYSTEM_OWNER",
        "EXTERNAL_PROVIDER_ESCALATION",
        "USER_COMMUNICATION",
    ], "required contact class set drift")
    rules = contract.get("bindingRules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "binding rules must remain true")
    require(rules.get("appendLockMustRemainCanonical") is True, "append lock requirement drift")
    require(rules.get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
            "transactional append rollback requirement drift")
    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict), "promotionRules missing")
    for key, value in promotion.items():
        if key == "automaticProductionReadyForbidden":
            require(value is True, "automatic production-ready prohibition must remain true")
        else:
            require(value is False, f"unsafe contact routing promotion enabled: {key}")

    writer = load_writer()
    try:
        writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"contact routing registry invalid: {exc}") from exc

    routings = registry["routings"]
    pe = registry["productionEquivalentRoutingCount"]
    prod = registry["productionRoutingCount"]

    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "contract authority missing")
    require(current.get("admittedRoutingCount") in {0, len(routings)}, "current routing count drift before reconcile")
    require(current.get("productionReady") is False and current.get("productionDecision") == "NO_GO", "production boundary drift")
    require(readiness.get("productionReady") is False, "readiness cannot promote production")
    print("Memory OS incident contact routing validation PASS")
    print(f"admitted routings: {len(routings)}")
    print(f"production-equivalent routings: {pe}")
    print(f"production routings: {prod}")
    print("application production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"INCIDENT CONTACT ROUTING VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
