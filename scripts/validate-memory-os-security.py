#!/usr/bin/env python3
"""Offline validator for Memory OS Round 9 security contracts."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SECURITY_REGISTRY = Path("docs/schemas/memory-os-security/schema-registry.v1.json")
SECURITY_FIXTURE_INDEX = Path("docs/fixtures/memory-os-security/fixture-index.round9.s1.v1.json")

MANDATORY_DELETION_SCOPES = {
    "database_records",
    "import_jobs",
    "worker_leases",
    "pairing_sessions",
    "upload_authorizations",
    "quarantine_objects",
    "previews",
    "apply_requests",
    "exports",
    "search_indexes",
    "push_payloads",
    "app_group_files",
    "backup_restore_tombstones",
}


class ValidationFailure(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path}: {exc}") from exc


def json_pointer_parts(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise ValidationFailure(f"invalid JSON pointer: {pointer}")
    return [
        part.replace("~1", "/").replace("~0", "~")
        for part in pointer.split("/")[1:]
    ]


def apply_mutation(document: Any, mutation: dict[str, Any]) -> Any:
    output = copy.deepcopy(document)
    parts = json_pointer_parts(mutation["path"])
    if not parts:
        raise ValidationFailure("root mutation is not supported")

    target = output
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]

    last = parts[-1]
    operation = mutation["op"]
    if operation == "remove":
        if isinstance(target, list):
            target.pop(int(last))
        else:
            target.pop(last)
    elif operation in {"add", "replace"}:
        value = mutation.get("value")
        if isinstance(target, list):
            index = int(last)
            if operation == "add":
                target.insert(index, value)
            else:
                target[index] = value
        else:
            target[last] = value
    else:
        raise ValidationFailure(f"unsupported mutation operation: {operation}")

    return output


def semantic_issue_codes(document: dict[str, Any]) -> set[str]:
    issues: set[str] = set()

    if document.get("$schema", "").endswith("/adapter-manifest.v1.schema.json"):
        artifact = document.get("artifactDigest")
        reviewed = document.get("review", {}).get("reviewedArtifactDigest")
        if artifact != reviewed:
            issues.add("SEC_ADAPTER_ARTIFACT_REVIEW_MISMATCH")

    if document.get("$schema", "").endswith("/deletion-fence.v1.schema.json"):
        scopes = set(document.get("scopes", []))
        if not MANDATORY_DELETION_SCOPES.issubset(scopes):
            issues.add("SEC_DELETION_FENCE_SCOPE_INCOMPLETE")

    return issues


def build_registry(
    repo_root: Path, registry_document: dict[str, Any]
) -> tuple[Registry, dict[str, dict[str, Any]]]:
    if registry_document.get("networkResolutionAllowed") is not False:
        raise ValidationFailure("network schema resolution must be disabled")

    resources = Registry()
    schema_documents: dict[str, dict[str, Any]] = {}
    seen_ids: set[str] = set()

    for entry in registry_document["schemas"]:
        schema_id = entry["schemaId"]
        path = repo_root / entry["repositoryPath"]

        if schema_id in seen_ids:
            raise ValidationFailure(f"duplicate schema ID: {schema_id}")
        seen_ids.add(schema_id)

        schema = load_json(path)
        if schema.get("$id") != schema_id:
            raise ValidationFailure(
                f"schema ID mismatch: registry={schema_id} file={schema.get('$id')}"
            )

        Draft202012Validator.check_schema(schema)
        resources = resources.with_resource(schema_id, Resource.from_contents(schema))
        schema_documents[schema_id] = schema

    return resources, schema_documents


def validate_document(
    document: dict[str, Any],
    schema_id: str,
    schema_documents: dict[str, dict[str, Any]],
    resources: Registry,
) -> list[str]:
    if schema_id not in schema_documents:
        raise ValidationFailure(f"unregistered schema ID: {schema_id}")

    validator = Draft202012Validator(
        schema_documents[schema_id],
        registry=resources,
        format_checker=FormatChecker(),
    )
    return sorted(
        f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: "
        f"{error.message}"
        for error in validator.iter_errors(document)
    )


def validate_issue_code_registry(
    repo_root: Path,
    fixture_index: dict[str, Any],
    schema_documents: dict[str, dict[str, Any]],
    resources: Registry,
) -> set[str]:
    matches = [
        item
        for item in fixture_index["fixtures"]
        if item["fixtureId"] == "memory-os.security.issue-codes.round9"
    ]
    if len(matches) != 1:
        raise ValidationFailure(
            "exactly one security issue-code registry fixture is required"
        )

    entry = matches[0]
    document = load_json(repo_root / entry["path"])
    errors = validate_document(
        document, entry["schemaId"], schema_documents, resources
    )
    if errors:
        raise ValidationFailure(
            "security issue-code registry failed validation:\n" + "\n".join(errors)
        )

    codes = [item["code"] for item in document["codes"]]
    if len(codes) != len(set(codes)):
        raise ValidationFailure("duplicate security issue codes")

    return set(codes)


def validate_fixtures(
    repo_root: Path,
    fixture_index: dict[str, Any],
    schema_documents: dict[str, dict[str, Any]],
    resources: Registry,
    issue_codes: set[str],
) -> tuple[int, int, int]:
    positive_count = 0
    schema_rejection_count = 0
    semantic_rejection_count = 0

    for entry in fixture_index["fixtures"]:
        path = repo_root / entry["path"]
        document = load_json(path)
        errors = validate_document(
            document, entry["schemaId"], schema_documents, resources
        )
        if errors:
            raise ValidationFailure(
                f"fixture failed validation: {entry['fixtureId']}\n"
                + "\n".join(errors)
            )

        if entry["schemaId"].endswith(
            "/security-negative-case-set.v1.schema.json"
        ):
            for case in document["cases"]:
                expected_code = case["expectedIssueCode"]
                if expected_code not in issue_codes:
                    raise ValidationFailure(
                        f"negative case references unknown issue code: {expected_code}"
                    )

                base_document = load_json(repo_root / case["baseFixtureRef"])
                mutated = apply_mutation(base_document, case["mutation"])
                mutation_errors = validate_document(
                    mutated,
                    case["targetSchemaId"],
                    schema_documents,
                    resources,
                )
                expected_result = case["expectedResult"]

                if expected_result == "schema_reject":
                    if not mutation_errors:
                        raise ValidationFailure(
                            "expected schema rejection but mutation passed: "
                            f"{case['caseId']}"
                        )
                    schema_rejection_count += 1
                elif expected_result == "semantic_reject":
                    if mutation_errors:
                        raise ValidationFailure(
                            f"semantic case was rejected structurally: {case['caseId']}\n"
                            + "\n".join(mutation_errors)
                        )
                    semantic_codes = semantic_issue_codes(mutated)
                    if expected_code not in semantic_codes:
                        raise ValidationFailure(
                            f"expected semantic issue {expected_code} was not produced: "
                            f"{case['caseId']}"
                        )
                    semantic_rejection_count += 1
                else:
                    raise ValidationFailure(
                        "unsupported executable expectedResult: "
                        f"{expected_result}"
                    )
        else:
            positive_count += 1

    return positive_count, schema_rejection_count, semantic_rejection_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    try:
        registry_document = load_json(repo_root / SECURITY_REGISTRY)
        fixture_index = load_json(repo_root / SECURITY_FIXTURE_INDEX)
        resources, schema_documents = build_registry(repo_root, registry_document)
        issue_codes = validate_issue_code_registry(
            repo_root, fixture_index, schema_documents, resources
        )
        positives, schema_rejections, semantic_rejections = validate_fixtures(
            repo_root,
            fixture_index,
            schema_documents,
            resources,
            issue_codes,
        )
    except ValidationFailure as exc:
        print(f"SECURITY CONTRACT VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            "SECURITY CONTRACT VALIDATION FAILED WITH UNEXPECTED ERROR: "
            f"{exc}",
            file=sys.stderr,
        )
        return 2

    print("Memory OS security contract validation PASS")
    print(f"schemas: {len(schema_documents)}")
    print(f"positive fixtures: {positives}")
    print(f"schema negative rejections: {schema_rejections}")
    print(f"semantic negative rejections: {semantic_rejections}")
    print("network schema resolution: disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
