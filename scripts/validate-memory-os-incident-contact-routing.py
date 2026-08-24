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
CONTRACT_REL = Path("contracts/operations/incident-contact-routing-admission-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/incident-contact-routing-admission-registry.v1.json")
WRITER_REL = Path("scripts/register-memory-os-incident-contact-routing.py")
LOCK_REL = Path("contracts/operations/.incident-contact-routing.lock")
OBS_REGISTRY_REL = Path("contracts/operations/observability-stack-deployment-registry.v1.json")
OBS_WRITER_REL = Path("scripts/register-memory-os-observability-stack-deployment.py")
GEN_REGISTRY_REL = Path("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
GEN_WRITER_REL = Path("scripts/register-memory-os-production-equivalent-environment-generation.py")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
WRITER = ROOT / WRITER_REL
LOCK = ROOT / LOCK_REL
OBS_REGISTRY = ROOT / OBS_REGISTRY_REL
OBS_WRITER = ROOT / OBS_WRITER_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
GEN_WRITER = ROOT / GEN_WRITER_REL


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
        (CONTRACT, CONTRACT_REL, "contact routing contract"),
        (REGISTRY, REGISTRY_REL, "contact routing registry"),
        (WRITER, WRITER_REL, "contact routing writer"),
        (OBS_REGISTRY, OBS_REGISTRY_REL, "observability stack registry"),
        (OBS_WRITER, OBS_WRITER_REL, "observability stack writer"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "environment generation registry"),
        (GEN_WRITER, GEN_WRITER_REL, "environment generation writer"),
    ):
        require_exact_repo_file(path, expected, field)
    require_canonical_lock_path(LOCK, LOCK_REL, "contact routing append lock")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_generation_writer() -> ModuleType:
    require_exact_repo_file(GEN_WRITER, GEN_WRITER_REL, "environment generation writer")
    spec = importlib.util.spec_from_file_location("memory_os_generation_writer_for_contact_routing_validator", GEN_WRITER)
    require(spec is not None and spec.loader is not None, "cannot load environment-generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "REGISTRY", None) == GEN_REGISTRY,
            "environment-generation writer registry authority drift")
    require(callable(getattr(module, "validate_registry_for_append", None)),
            "environment-generation registry validator missing")
    return module


def validate_generation_authority() -> None:
    registry = load(GEN_REGISTRY)
    writer = load_generation_writer()
    try:
        writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"environment-generation authority invalid: {exc}") from exc


def load_writer() -> ModuleType:
    require_exact_repo_file(WRITER, WRITER_REL, "contact routing writer")
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
    require(getattr(module, "GEN_REGISTRY", None) == GEN_REGISTRY,
            "contact routing generation registry authority drift")
    require(callable(getattr(module, "validate_registry_for_append", None)),
            "contact routing writer registry validator missing")
    require(callable(getattr(module, "commit_registry_candidate", None)),
            "contact routing transactional append authority missing")
    return module


def main() -> int:
    enforce_runtime_authorities()
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

    validate_generation_authority()
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
    print("contact routing validator canonical runtime authorities enforced: true")
    print("ephemeral append lock may be absent but path authority remains canonical: true")
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
