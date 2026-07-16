#!/usr/bin/env python3
"""Execute Memory OS object-authorization matrix cases offline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

REGISTRY_PATH = Path("docs/schemas/memory-os-security/schema-registry.v1.json")
ISSUE_CODES_PATH = Path("docs/fixtures/memory-os-security/security-issue-code-registry.round9.v1.json")
MATRIX_PATH = Path("docs/fixtures/memory-os-security/authorization-matrix.round9.valid.v1.json")
CASES_PATH = Path("docs/fixtures/memory-os-security/authorization-cases.round9.v1.json")


class AuthorizationValidationFailure(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuthorizationValidationFailure(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AuthorizationValidationFailure(f"invalid JSON: {path}: {exc}") from exc


def build_registry(repo_root: Path) -> tuple[Registry, dict[str, dict[str, Any]]]:
    registry_document = load_json(repo_root / REGISTRY_PATH)
    if registry_document.get("networkResolutionAllowed") is not False:
        raise AuthorizationValidationFailure("network schema resolution must be disabled")

    registry = Registry()
    schemas: dict[str, dict[str, Any]] = {}
    for entry in registry_document["schemas"]:
        schema = load_json(repo_root / entry["repositoryPath"])
        if schema.get("$id") != entry["schemaId"]:
            raise AuthorizationValidationFailure(
                f"schema ID mismatch: {entry['repositoryPath']}"
            )
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(
            entry["schemaId"], Resource.from_contents(schema)
        )
        schemas[entry["schemaId"]] = schema
    return registry, schemas


def validate_shape(
    document: dict[str, Any],
    registry: Registry,
    schemas: dict[str, dict[str, Any]],
) -> None:
    schema_id = document.get("$schema")
    if schema_id not in schemas:
        raise AuthorizationValidationFailure(f"unregistered schema: {schema_id}")
    errors = sorted(
        Draft202012Validator(
            schemas[schema_id],
            registry=registry,
            format_checker=FormatChecker(),
        ).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        messages = "\n".join(
            f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: "
            f"{error.message}"
            for error in errors
        )
        raise AuthorizationValidationFailure(messages)


def index_matrix(matrix: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for resource in matrix["resources"]:
        resource_type = resource["resourceType"]
        for operation in resource["operations"]:
            key = (resource_type, operation["operation"])
            if key in indexed:
                raise AuthorizationValidationFailure(
                    f"duplicate authorization rule: {key}"
                )
            indexed[key] = operation
    return indexed


def decide(
    case: dict[str, Any],
    matrix: dict[str, Any],
    rules: dict[tuple[str, str], dict[str, Any]],
) -> tuple[str, str]:
    rule = rules.get((case["resourceType"], case["operation"]))
    if rule is None:
        return "deny", "SEC_AUTHORITY_NOT_ALLOWED"

    if case["authority"] not in rule["allowedAuthorities"]:
        return "deny", "SEC_AUTHORITY_NOT_ALLOWED"

    if rule["sameOwnerRequired"] and (
        case["principalAccountId"] != case["resourceOwnerAccountId"]
    ):
        return "deny", "SEC_CROSS_USER_ACCESS_DENIED"

    if rule["sameEpochRequired"] and (
        case["principalEpoch"] != case["resourceEpoch"]
    ):
        return "deny", "SEC_STALE_ACCOUNT_EPOCH"

    if rule["objectLookupRequired"] and not case["objectLookupPerformed"]:
        return "deny", "SEC_OBJECT_LOOKUP_REQUIRED"

    if (
        case["operation"] == "list"
        and matrix["globalRules"]["listQueriesOwnerScoped"]
        and not case["queryOwnerScoped"]
    ):
        return "deny", "SEC_QUERY_OWNER_SCOPE_REQUIRED"

    return "allow", "SEC_AUTHORIZED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    try:
        registry, schemas = build_registry(repo_root)
        issue_document = load_json(repo_root / ISSUE_CODES_PATH)
        matrix = load_json(repo_root / MATRIX_PATH)
        cases_document = load_json(repo_root / CASES_PATH)

        validate_shape(issue_document, registry, schemas)
        validate_shape(matrix, registry, schemas)
        validate_shape(cases_document, registry, schemas)

        issue_codes = {item["code"] for item in issue_document["codes"]}
        rules = index_matrix(matrix)

        allow_count = 0
        deny_count = 0
        for case in cases_document["cases"]:
            decision, issue_code = decide(case, matrix, rules)
            if issue_code not in issue_codes:
                raise AuthorizationValidationFailure(
                    f"case produced unregistered issue code: {issue_code}"
                )
            if decision != case["expectedDecision"]:
                raise AuthorizationValidationFailure(
                    f"{case['caseId']}: expected {case['expectedDecision']}, "
                    f"got {decision}"
                )
            if issue_code != case["expectedIssueCode"]:
                raise AuthorizationValidationFailure(
                    f"{case['caseId']}: expected {case['expectedIssueCode']}, "
                    f"got {issue_code}"
                )
            if decision == "allow":
                allow_count += 1
            else:
                deny_count += 1
    except AuthorizationValidationFailure as exc:
        print(f"AUTHORIZATION VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"AUTHORIZATION VALIDATION FAILED WITH UNEXPECTED ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    print("Memory OS authorization validation PASS")
    print(f"authorization resources: {len(matrix['resources'])}")
    print(f"authorization cases: {len(cases_document['cases'])}")
    print(f"allowed cases: {allow_count}")
    print(f"denied cases: {deny_count}")
    print("deny by default: enabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
