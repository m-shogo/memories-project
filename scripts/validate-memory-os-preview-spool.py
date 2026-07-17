#!/usr/bin/env python3
"""Validate Preview spool manifest invariants that JSON Schema cannot express."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SECURITY_REGISTRY = Path("docs/schemas/memory-os-security/schema-registry.v1.json")
ISSUE_CODE_FIXTURE = Path(
    "docs/fixtures/memory-os-security/security-issue-code-registry.round9.v1.json"
)
MANIFEST_FIXTURE = Path(
    "docs/fixtures/memory-os-security/preview-spool-manifest.round9.valid.v1.json"
)
SEMANTIC_CASES = Path(
    "docs/fixtures/memory-os-security/"
    "preview-spool-manifest-semantic-cases.round9.v1.json"
)
MAX_SOURCE_ROWS = 100_000
MAX_SPOOL_BYTES = 512 * 1024 * 1024
MAX_SPOOL_TTL = timedelta(hours=24)
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


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


def build_registry(
    repo_root: Path, registry_document: dict[str, Any]
) -> tuple[Registry, dict[str, dict[str, Any]]]:
    if registry_document.get("networkResolutionAllowed") is not False:
        raise ValidationFailure("network schema resolution must be disabled")

    resources = Registry()
    schemas: dict[str, dict[str, Any]] = {}
    for entry in registry_document["schemas"]:
        schema_id = entry["schemaId"]
        schema = load_json(repo_root / entry["repositoryPath"])
        if schema.get("$id") != schema_id:
            raise ValidationFailure(
                f"schema ID mismatch: registry={schema_id} file={schema.get('$id')}"
            )
        Draft202012Validator.check_schema(schema)
        resources = resources.with_resource(schema_id, Resource.from_contents(schema))
        schemas[schema_id] = schema
    return resources, schemas


def validate_document(
    document: dict[str, Any],
    schema_id: str,
    schemas: dict[str, dict[str, Any]],
    resources: Registry,
) -> list[str]:
    if schema_id not in schemas:
        raise ValidationFailure(f"unregistered schema ID: {schema_id}")
    validator = Draft202012Validator(
        schemas[schema_id],
        registry=resources,
        format_checker=FormatChecker(),
    )
    return sorted(
        f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: "
        f"{error.message}"
        for error in validator.iter_errors(document)
    )


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def semantic_issue_codes(document: dict[str, Any]) -> set[str]:
    issues: set[str] = set()
    job_id = document["jobId"]
    object_key = document["source"]["objectKey"]
    accepted = document["streams"]["accepted"]
    rejected = document["streams"]["rejected"]

    if not object_key.startswith(f"quarantine/{job_id}/"):
        issues.add("SEC_PREVIEW_SPOOL_BINDING_INVALID")

    stream_rows = accepted["recordCount"] + rejected["recordCount"]
    stream_bytes = accepted["byteLength"] + rejected["byteLength"]
    if document["sourceRowCount"] != stream_rows:
        issues.add("SEC_PREVIEW_SPOOL_BINDING_INVALID")
    if document["spoolByteLength"] != stream_bytes:
        issues.add("SEC_PREVIEW_SPOOL_BINDING_INVALID")
    if stream_rows > MAX_SOURCE_ROWS or stream_bytes > MAX_SPOOL_BYTES:
        issues.add("SEC_PREVIEW_SPOOL_LIMIT_EXCEEDED")

    if rejected["recordCount"] == 0:
        if rejected["byteLength"] != 0 or rejected["sha256"] != EMPTY_SHA256:
            issues.add("SEC_PREVIEW_SPOOL_BINDING_INVALID")
    elif rejected["byteLength"] == 0:
        issues.add("SEC_PREVIEW_SPOOL_BINDING_INVALID")

    created_at = parse_utc(document["createdAt"])
    expires_at = parse_utc(document["expiresAt"])
    if expires_at <= created_at or expires_at - created_at > MAX_SPOOL_TTL:
        issues.add("SEC_PREVIEW_SPOOL_TTL_INVALID")

    return issues


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
        resources, schemas = build_registry(repo_root, registry_document)

        issue_registry = load_json(repo_root / ISSUE_CODE_FIXTURE)
        known_issue_codes = {entry["code"] for entry in issue_registry["codes"]}

        manifest = load_json(repo_root / MANIFEST_FIXTURE)
        manifest_schema_id = manifest["$schema"]
        manifest_errors = validate_document(
            manifest, manifest_schema_id, schemas, resources
        )
        if manifest_errors:
            raise ValidationFailure(
                "valid Preview spool manifest failed schema validation:\n"
                + "\n".join(manifest_errors)
            )
        baseline_issues = semantic_issue_codes(manifest)
        if baseline_issues:
            raise ValidationFailure(
                "valid Preview spool manifest failed semantic validation: "
                + ", ".join(sorted(baseline_issues))
            )

        case_set = load_json(repo_root / SEMANTIC_CASES)
        case_set_errors = validate_document(
            case_set, case_set["$schema"], schemas, resources
        )
        if case_set_errors:
            raise ValidationFailure(
                "Preview spool semantic case set failed schema validation:\n"
                + "\n".join(case_set_errors)
            )
        if case_set["targetSchemaId"] != manifest_schema_id:
            raise ValidationFailure("semantic case target schema does not match manifest")
        if repo_root / case_set["baseFixtureRef"] != repo_root / MANIFEST_FIXTURE:
            raise ValidationFailure("semantic case base fixture is not canonical")

        executed = 0
        for case in case_set["cases"]:
            expected = case["expectedIssueCode"]
            if expected not in known_issue_codes:
                raise ValidationFailure(
                    f"semantic case references unknown issue code: {expected}"
                )
            mutated = apply_mutation(manifest, case["mutation"])
            mutation_errors = validate_document(
                mutated, manifest_schema_id, schemas, resources
            )
            if mutation_errors:
                raise ValidationFailure(
                    f"semantic case was rejected structurally: {case['caseId']}\n"
                    + "\n".join(mutation_errors)
                )
            actual = semantic_issue_codes(mutated)
            if expected not in actual:
                raise ValidationFailure(
                    f"expected semantic issue {expected} was not produced: "
                    f"{case['caseId']} actual={sorted(actual)}"
                )
            executed += 1

    except ValidationFailure as exc:
        print(f"PREVIEW SPOOL VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"PREVIEW SPOOL VALIDATION FAILED WITH UNEXPECTED ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    print("Memory OS Preview spool contract validation PASS")
    print(f"semantic negative cases: {executed}")
    print(f"maximum source rows: {MAX_SOURCE_ROWS}")
    print(f"maximum spool bytes: {MAX_SPOOL_BYTES}")
    print("maximum spool TTL hours: 24")
    print("network schema resolution: disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
