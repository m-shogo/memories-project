#!/usr/bin/env python3
"""Fail-closed structural validator for the production-equivalent environment-record JSON Schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts/operations/production-equivalent-environment-record.v1.schema.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing schema: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid schema JSON: {exc}") from exc
    require(isinstance(value, dict), "schema root must be object")
    return value


def prop(schema: dict[str, Any], *path: str) -> dict[str, Any]:
    current: Any = schema
    for key in path:
        require(isinstance(current, dict) and key in current, f"schema path missing: {'.'.join(path)}")
        current = current[key]
    require(isinstance(current, dict), f"schema path must be object: {'.'.join(path)}")
    return current


def main() -> int:
    schema = load(SCHEMA_PATH)
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "JSON Schema draft drift")
    require(schema.get("type") == "object", "root type must be object")
    require(schema.get("additionalProperties") is False, "root must reject unknown fields")

    required = schema.get("required")
    require(isinstance(required, list), "root required must be array")
    for name in (
        "schemaVersion",
        "environmentId",
        "generationId",
        "status",
        "topology",
        "postgresql",
        "objectStorage",
        "queueWorkers",
        "network",
        "identityAndSecrets",
        "backupRestore",
        "materialDeltas",
        "evidenceBoundary",
    ):
        require(name in required, f"required environment field missing: {name}")

    properties = prop(schema, "properties")
    statuses = prop(properties, "status").get("enum")
    require(isinstance(statuses, list), "status enum required")
    require("VALIDATED_LOCAL_NONPRODUCTION" in statuses, "validated non-production state missing")
    for forbidden in ("PRODUCTION", "PRODUCTION_READY", "READY"):
        require(forbidden not in statuses, f"unsafe environment status present: {forbidden}")

    topology = prop(properties, "topology", "properties")
    require(prop(topology, "productionTraffic").get("const") is False, "production traffic must remain false")
    require(prop(topology, "productionCredentials").get("const") is False, "production credentials must remain false")

    postgres = prop(properties, "postgresql", "properties")
    require(prop(postgres, "runtimeRoleBypassRLS").get("const") is False, "runtime role may not bypass RLS")
    identity = prop(properties, "identityAndSecrets", "properties")
    require(prop(identity, "containsSecretMaterial").get("const") is False, "secret material must remain forbidden")
    boundary = prop(properties, "evidenceBoundary", "properties")
    require(prop(boundary, "productionEvidence").get("const") is False, "environment record is not production evidence")
    require(prop(boundary, "productionReady").get("const") is False, "environment record cannot mark production ready")

    delta_items = prop(properties, "materialDeltas", "items")
    delta_rules = delta_items.get("allOf")
    require(isinstance(delta_rules, list) and delta_rules, "material delta conditional review rule missing")
    delta_rule = delta_rules[0]
    condition = prop(delta_rule, "if", "properties")
    require(prop(condition, "classification").get("const") == "MATERIAL", "material-delta condition drift")
    require(prop(condition, "accepted").get("const") is True, "accepted-delta condition drift")
    review = prop(delta_rule, "then", "properties", "independentReviewRef")
    require(review.get("type") == "string" and review.get("minLength") == 1, "accepted material delta must require review reference")

    promotion_rules = schema.get("allOf")
    require(isinstance(promotion_rules, list) and promotion_rules, "production-equivalent conditional admission rule missing")
    promotion = promotion_rules[0]
    trigger = prop(promotion, "if", "properties", "evidenceBoundary", "properties", "productionEquivalentDependencies")
    require(trigger.get("const") is True, "production-equivalent trigger drift")
    then_props = prop(promotion, "then", "properties")

    required_true = {
        "topology": ("nonLoopback",),
        "postgresql": ("tlsVerified", "forceRLSVerified", "connectionBudgetDeclared", "poolTelemetryVerified"),
        "objectStorage": ("tlsVerified", "scopedCredentialsVerified", "versioningVerified", "retentionLifecycleVerified", "exactVersionDeleteVerified"),
        "queueWorkers": ("boundedBackpressureVerified", "queueTelemetryVerified", "deletionBacklogTelemetryVerified", "leaseRetryVerified"),
        "identityAndSecrets": ("dedicatedNonProductionCredentials",),
        "backupRestore": ("sameGenerationLinked", "isolatedRestoreVerified"),
        "evidenceBoundary": ("independentReviewCompleted",),
    }
    for domain, names in required_true.items():
        domain_props = prop(then_props, domain, "properties")
        for name in names:
            require(prop(domain_props, name).get("const") is True, f"equivalence promotion must require {domain}.{name}=true")

    required_refs = {
        "postgresql": ("restoreEvidenceRef",),
        "objectStorage": ("restoreEvidenceRef",),
        "network": ("latencyProfileRef", "failureInjectionRef"),
        "identityAndSecrets": ("credentialScopeRef",),
        "backupRestore": ("evidenceRef",),
    }
    for domain, names in required_refs.items():
        domain_props = prop(then_props, domain, "properties")
        for name in names:
            ref = prop(domain_props, name)
            require(ref.get("type") == "string" and ref.get("minLength") == 1, f"equivalence promotion must require evidence ref {domain}.{name}")

    print("Memory OS production-equivalent environment schema PASS")
    print("automatic local-to-production-equivalent relabel: forbidden")
    print("accepted material delta review reference: required")
    print("production traffic: false")
    print("production credentials: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT ENVIRONMENT SCHEMA FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
