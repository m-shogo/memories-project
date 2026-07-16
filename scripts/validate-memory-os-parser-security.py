#!/usr/bin/env python3
"""Validate Memory OS parser sandbox and archive safety contracts."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SCHEMA_REGISTRY_PATH = Path("docs/schemas/memory-os-security/schema-registry.v1.json")
SANDBOX_PROFILE_PATH = Path("docs/fixtures/memory-os-security/parser-sandbox-profile.round9.valid.v1.json")
SANDBOX_CASES_PATH = Path("docs/fixtures/memory-os-security/parser-sandbox-negative-cases.round9.v1.json")
ARCHIVE_PROFILE_PATH = Path("docs/fixtures/memory-os-security/archive-safety-profile.round9.valid.v1.json")
ARCHIVE_CASES_PATH = Path("docs/fixtures/memory-os-security/archive-safety-cases.round9.v1.json")
ISSUE_REGISTRY_PATHS = [
    Path("docs/fixtures/memory-os-security/security-issue-code-registry.round9.v1.json"),
    Path("docs/fixtures/memory-os-security/parser-security-issue-code-registry.round9.v1.json"),
]


class ValidationFailure(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationFailure(f"expected JSON object: {path}")
    return value


def build_registry(root: Path) -> tuple[Registry, dict[str, dict[str, Any]]]:
    registry_doc = load_json(root / SCHEMA_REGISTRY_PATH)
    if registry_doc.get("networkResolutionAllowed") is not False:
        raise ValidationFailure("network schema resolution must be disabled")
    registry = Registry()
    schemas: dict[str, dict[str, Any]] = {}
    for entry in registry_doc["schemas"]:
        schema = load_json(root / entry["repositoryPath"])
        if schema.get("$id") != entry["schemaId"]:
            raise ValidationFailure(f"schema ID mismatch: {entry['repositoryPath']}")
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(entry["schemaId"], Resource.from_contents(schema))
        schemas[entry["schemaId"]] = schema
    return registry, schemas


def validate_document(
    document: dict[str, Any],
    schemas: dict[str, dict[str, Any]],
    registry: Registry,
) -> list[str]:
    schema_id = document.get("$schema")
    if schema_id not in schemas:
        raise ValidationFailure(f"unregistered schema: {schema_id}")
    validator = Draft202012Validator(
        schemas[schema_id],
        registry=registry,
        format_checker=FormatChecker(),
    )
    return sorted(
        f"{'/'.join(str(p) for p in error.absolute_path) or '<root>'}: {error.message}"
        for error in validator.iter_errors(document)
    )


def pointer_parts(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise ValidationFailure(f"invalid JSON pointer: {pointer}")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def mutate(document: dict[str, Any], pointer: str, value: Any) -> dict[str, Any]:
    output = copy.deepcopy(document)
    parts = pointer_parts(pointer)
    target: Any = output
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    last = parts[-1]
    if isinstance(target, list):
        target[int(last)] = value
    else:
        target[last] = value
    return output


def issue_codes(root: Path) -> set[str]:
    codes: set[str] = set()
    for relative in ISSUE_REGISTRY_PATHS:
        doc = load_json(root / relative)
        for entry in doc["codes"]:
            code = entry["code"]
            if code in codes:
                raise ValidationFailure(f"duplicate issue code across registries: {code}")
            codes.add(code)
    return codes


def decide_archive(case: dict[str, Any], profile: dict[str, Any]) -> tuple[str, str]:
    sizes = profile["sizeLimits"]
    paths = profile["pathRules"]
    entries = profile["entryRules"]
    json_limits = profile["jsonLimits"]
    csv_limits = profile["csvLimits"]

    if case["archiveType"] not in profile["archiveTypes"]["allowed"]:
        return "deny", "SEC_ARCHIVE_FILENAME_INVALID"
    if not case["centralDirectoryValid"]:
        return "deny", "SEC_ARCHIVE_FILENAME_INVALID"
    if not case["compressionMethodKnown"]:
        return "deny", "SEC_ARCHIVE_FILENAME_INVALID"
    if case["compressedBytes"] > sizes["compressedBytes"]:
        return "deny", "SEC_ARCHIVE_COMPRESSED_SIZE_LIMIT"
    if case["expandedBytes"] > sizes["expandedBytes"]:
        return "deny", "SEC_ARCHIVE_EXPANDED_SIZE_LIMIT"
    if case["singleEntryExpandedBytes"] > sizes["singleEntryExpandedBytes"]:
        return "deny", "SEC_ARCHIVE_ENTRY_SIZE_LIMIT"
    if case["entryCount"] > sizes["entryCount"]:
        return "deny", "SEC_ARCHIVE_ENTRY_COUNT_LIMIT"
    if case["compressionRatio"] > sizes["compressionRatio"]:
        return "deny", "SEC_ARCHIVE_COMPRESSION_RATIO_LIMIT"
    if case["nestedArchiveDepth"] > sizes["nestedArchiveDepth"]:
        return "deny", "SEC_ARCHIVE_NESTING_LIMIT"

    path_kind = case["pathKind"]
    if path_kind in {"parent_traversal", "backslash_traversal"}:
        return "deny", "SEC_ARCHIVE_PATH_TRAVERSAL"
    if path_kind == "absolute_unix":
        return "deny", "SEC_ARCHIVE_ABSOLUTE_PATH"
    if path_kind == "windows_drive":
        return "deny", "SEC_ARCHIVE_WINDOWS_DRIVE_PATH"
    if path_kind in {"nul", "too_long"}:
        return "deny", "SEC_ARCHIVE_FILENAME_INVALID"
    if case["duplicateNormalizedPath"] and not paths["duplicateNormalizedPathsAllowed"]:
        return "deny", "SEC_ARCHIVE_DUPLICATE_PATH"
    if case["caseFoldCollision"] and not paths["caseFoldCollisionsAllowed"]:
        return "deny", "SEC_ARCHIVE_CASE_COLLISION"

    entry_type = case["entryType"]
    if entry_type in {"symlink", "hardlink"}:
        return "deny", "SEC_ARCHIVE_LINK_FORBIDDEN"
    entry_rule = {
        "device": "deviceFilesAllowed",
        "fifo": "fifosAllowed",
        "socket": "socketsAllowed",
        "sparse": "sparseFilesAllowed",
    }.get(entry_type)
    if entry_rule and not entries[entry_rule]:
        return "deny", "SEC_ARCHIVE_SPECIAL_FILE_FORBIDDEN"

    if case["encrypted"] and not profile["archiveTypes"]["encryptedAllowed"]:
        return "deny", "SEC_ARCHIVE_ENCRYPTED_FORBIDDEN"
    if case["multiVolume"] and not profile["archiveTypes"]["multiVolumeAllowed"]:
        return "deny", "SEC_ARCHIVE_MULTIVOLUME_FORBIDDEN"
    if case["jsonDepth"] > json_limits["maxDepth"]:
        return "deny", "SEC_JSON_DEPTH_LIMIT"
    if case["jsonDuplicateKeys"] and not json_limits["duplicateObjectKeysAllowed"]:
        return "deny", "SEC_JSON_DUPLICATE_KEY_FORBIDDEN"
    if case["csvMaxCellBytes"] > csv_limits["maxCellBytes"]:
        return "deny", "SEC_CSV_CELL_SIZE_LIMIT"
    return "allow", "SEC_AUTHORIZED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()

    try:
        registry, schemas = build_registry(root)
        known_codes = issue_codes(root)
        sandbox = load_json(root / SANDBOX_PROFILE_PATH)
        sandbox_cases = load_json(root / SANDBOX_CASES_PATH)
        archive = load_json(root / ARCHIVE_PROFILE_PATH)
        archive_cases = load_json(root / ARCHIVE_CASES_PATH)

        for name, doc in (
            ("sandbox profile", sandbox),
            ("sandbox case set", sandbox_cases),
            ("archive profile", archive),
            ("archive case set", archive_cases),
        ):
            errors = validate_document(doc, schemas, registry)
            if errors:
                raise ValidationFailure(f"{name} invalid:\n" + "\n".join(errors))

        if sandbox_cases["baseFixtureRef"] != SANDBOX_PROFILE_PATH.as_posix():
            raise ValidationFailure("sandbox cases point to a different profile")
        if archive_cases["profileRef"] != ARCHIVE_PROFILE_PATH.as_posix():
            raise ValidationFailure("archive cases point to a different profile")

        sandbox_denies = 0
        for case in sandbox_cases["cases"]:
            if case["expectedIssueCode"] not in known_codes:
                raise ValidationFailure(f"unknown sandbox issue code: {case['expectedIssueCode']}")
            mutated = mutate(sandbox, case["mutation"]["path"], case["mutation"]["value"])
            if not validate_document(mutated, schemas, registry):
                raise ValidationFailure(f"unsafe sandbox mutation passed schema: {case['caseId']}")
            sandbox_denies += 1

        archive_allows = 0
        archive_denies = 0
        seen: set[str] = set()
        for case in archive_cases["cases"]:
            if case["caseId"] in seen:
                raise ValidationFailure(f"duplicate archive case: {case['caseId']}")
            seen.add(case["caseId"])
            if case["expectedIssueCode"] not in known_codes:
                raise ValidationFailure(f"unknown archive issue code: {case['expectedIssueCode']}")
            actual = decide_archive(case, archive)
            expected = (case["expectedDecision"], case["expectedIssueCode"])
            if actual != expected:
                raise ValidationFailure(
                    f"archive case mismatch {case['caseId']}: expected={expected} actual={actual}"
                )
            if actual[0] == "allow":
                archive_allows += 1
            else:
                archive_denies += 1
    except ValidationFailure as exc:
        print(f"PARSER SECURITY VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"PARSER SECURITY VALIDATION FAILED WITH UNEXPECTED ERROR: {exc}", file=sys.stderr)
        return 2

    print("Memory OS parser security validation PASS")
    print(f"sandbox unsafe mutations rejected: {sandbox_denies}")
    print(f"archive cases: {archive_allows + archive_denies}")
    print(f"archive allow: {archive_allows}")
    print(f"archive deny: {archive_denies}")
    print("parser network: none")
    print("parser secrets: none")
    print("parser root filesystem: read-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
