#!/usr/bin/env python3
"""Validate the Preview canonical adapter record contract.

The frame payload bytes are authoritative: an accepted record must be exactly
the deterministic Go encoding/json serialization (fixed field order, compact
separators, HTML-escaping of '<', '>' and '&'), and its fingerprint must be
the SHA-256 of TrimSpace(title), occurredAt, TrimSpace(url) and
TrimSpace(text) joined by 0x1F — matching the genericcsv adapter. The Go
implementation (services/import-api/internal/canonrecord) cross-validates the
same fixture file, so both languages enforce one contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SECURITY_REGISTRY = Path("docs/schemas/memory-os-security/schema-registry.v1.json")
CASE_SET_FIXTURE = Path(
    "docs/fixtures/memory-os-security/preview-canonical-records.round9.v1.json"
)
RECORD_SCHEMA_ID = (
    "https://memory-os.example/schemas/security/preview-canonical-record.v1.schema.json"
)

CANDIDATE_FIELD_ORDER = [
    "recordType", "recordVersion", "sourceRow", "title",
    "occurredAt", "url", "text", "fingerprint", "issues",
]
REJECTION_FIELD_ORDER = ["recordType", "recordVersion", "sourceRow", "issueCodes"]


class ValidationFailure(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path}: {exc}") from exc


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


def schema_errors(
    document: Any,
    schema_id: str,
    schemas: dict[str, dict[str, Any]],
    resources: Registry,
) -> list[str]:
    validator = Draft202012Validator(
        schemas[schema_id], registry=resources, format_checker=FormatChecker()
    )
    return sorted(
        f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: "
        f"{error.message}"
        for error in validator.iter_errors(document)
    )


def go_canonical_encoding(record: dict[str, Any]) -> str:
    """Reproduce Go encoding/json output for a contract-ordered record."""
    order = (
        CANDIDATE_FIELD_ORDER
        if record.get("recordType") == "candidate"
        else REJECTION_FIELD_ORDER
    )
    if sorted(record.keys()) != sorted(order):
        raise ValidationFailure(f"record fields do not match the contract: {sorted(record)}")
    ordered = {key: record[key] for key in order}
    encoded = json.dumps(ordered, separators=(",", ":"), ensure_ascii=False)
    return (
        encoded.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    )


def expected_fingerprint(record: dict[str, Any]) -> str:
    canonical = "\x1f".join(
        [
            record["title"].strip(),
            record["occurredAt"],
            record["url"].strip(),
            record["text"].strip(),
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def semantic_errors(record: dict[str, Any]) -> list[str]:
    if record.get("recordType") != "candidate":
        return []
    errors = []
    if record["fingerprint"] != expected_fingerprint(record):
        errors.append("fingerprint does not match the recomputed candidate fingerprint")
    return errors


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

    counts = {"accept": 0, "reject_schema": 0, "reject_semantic": 0, "reject_encoding": 0}
    try:
        registry_document = load_json(repo_root / SECURITY_REGISTRY)
        resources, schemas = build_registry(repo_root, registry_document)
        if RECORD_SCHEMA_ID not in schemas:
            raise ValidationFailure("canonical record schema is not registered")

        case_set = load_json(repo_root / CASE_SET_FIXTURE)
        case_set_errors = schema_errors(
            case_set, case_set["$schema"], schemas, resources
        )
        if case_set_errors:
            raise ValidationFailure(
                "canonical record case set failed schema validation:\n"
                + "\n".join(case_set_errors)
            )
        if case_set["recordSchemaId"] != RECORD_SCHEMA_ID:
            raise ValidationFailure("case set does not target the record schema")

        seen_ids: set[str] = set()
        for case in case_set["cases"]:
            case_id = case["caseId"]
            if case_id in seen_ids:
                raise ValidationFailure(f"duplicate caseId: {case_id}")
            seen_ids.add(case_id)
            expected = case["expected"]

            if expected == "accept":
                record = case["record"]
                encoding = case["canonicalEncoding"]
                errors = schema_errors(record, RECORD_SCHEMA_ID, schemas, resources)
                if errors:
                    raise ValidationFailure(
                        f"{case_id}: accept case failed the record schema:\n"
                        + "\n".join(errors)
                    )
                sem = semantic_errors(record)
                if sem:
                    raise ValidationFailure(
                        f"{case_id}: accept case failed semantics: {sem}"
                    )
                rebuilt = go_canonical_encoding(record)
                if rebuilt != encoding:
                    raise ValidationFailure(
                        f"{case_id}: canonicalEncoding does not match the Go serialization\n"
                        f"  fixture: {encoding}\n  rebuilt: {rebuilt}"
                    )
                if json.loads(encoding) != record:
                    raise ValidationFailure(
                        f"{case_id}: canonicalEncoding does not parse back to the record"
                    )
            elif expected == "reject_schema":
                record = case["record"]
                if not schema_errors(record, RECORD_SCHEMA_ID, schemas, resources):
                    raise ValidationFailure(
                        f"{case_id}: reject_schema case passed the record schema"
                    )
            elif expected == "reject_semantic":
                record = case["record"]
                errors = schema_errors(record, RECORD_SCHEMA_ID, schemas, resources)
                if errors:
                    raise ValidationFailure(
                        f"{case_id}: reject_semantic case must pass the schema first:\n"
                        + "\n".join(errors)
                    )
                if not semantic_errors(record):
                    raise ValidationFailure(
                        f"{case_id}: reject_semantic case passed semantic validation"
                    )
            elif expected == "reject_encoding":
                encoding = case["canonicalEncoding"]
                record = json.loads(encoding)
                errors = schema_errors(record, RECORD_SCHEMA_ID, schemas, resources)
                if errors:
                    raise ValidationFailure(
                        f"{case_id}: reject_encoding payload must parse to a schema-valid record:\n"
                        + "\n".join(errors)
                    )
                if go_canonical_encoding(record) == encoding:
                    raise ValidationFailure(
                        f"{case_id}: reject_encoding payload is actually canonical"
                    )
            else:
                raise ValidationFailure(f"{case_id}: unknown expectation {expected}")
            counts[expected] += 1

        if counts["accept"] < 3 or counts["reject_schema"] < 5:
            raise ValidationFailure(f"case coverage is too thin: {counts}")

    except ValidationFailure as exc:
        print(f"CANONICAL RECORD VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(
            f"CANONICAL RECORD VALIDATION FAILED WITH UNEXPECTED ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    print("Memory OS canonical adapter record contract validation PASS")
    for key, value in counts.items():
        print(f"{key} cases: {value}")
    print("network schema resolution: disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
