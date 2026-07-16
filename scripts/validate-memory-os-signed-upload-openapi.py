#!/usr/bin/env python3
"""Validate the Memory OS signed quarantine upload OpenAPI security boundary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SPEC_PATH = Path("contracts/openapi/memory-os-import-security.v1.openapi.json")
FORBIDDEN_REQUEST_FIELDS = {
    "ownerAccountId",
    "accountEpoch",
    "objectKey",
    "bucket",
    "bucketName",
    "storageVersionId",
}
REQUIRED_CREATE_BINDINGS = {
    "deriveOwnerFromVerifiedAuth",
    "deriveEpochFromServerAccount",
    "deriveObjectKeyOnServer",
    "pairingTokenMustMatchJobScope",
    "singleActiveAuthorizationPerIdempotencyKey",
}
REQUIRED_COMPLETE_BINDINGS = {
    "trustClientObjectMetadata": False,
    "headExactServerGeneratedObjectKey": True,
    "compareStoredContentLength": True,
    "compareStoredChecksum": True,
    "compareStoredContentType": True,
    "authorizationMustBeIssuedAndUnexpired": True,
    "authorizationConsumedAtomically": True,
    "cancelledOrDeletedAccountRejected": True,
    "queueOnlyAfterVerification": True,
}


class ValidationFailure(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing OpenAPI spec: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid OpenAPI JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationFailure("OpenAPI document must be an object")
    return value


def resolve_local_ref(document: dict[str, Any], ref: str) -> Any:
    if not ref.startswith("#/"):
        raise ValidationFailure(f"remote or non-local OpenAPI reference forbidden: {ref}")
    current: Any = document
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        current = current[part]
    return current


def dereference(document: dict[str, Any], value: Any) -> Any:
    if isinstance(value, dict) and set(value) == {"$ref"}:
        return resolve_local_ref(document, value["$ref"])
    return value


def schema_properties(document: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    resolved = dereference(document, schema)
    return resolved.get("properties", {})


def validate_no_store(document: dict[str, Any], response: dict[str, Any], label: str) -> None:
    resolved = dereference(document, response)
    header = resolved.get("headers", {}).get("Cache-Control")
    if header is None:
        raise ValidationFailure(f"Cache-Control no-store missing: {label}")
    header = dereference(document, header)
    if header.get("schema", {}).get("const") != "no-store":
        raise ValidationFailure(f"Cache-Control is not exact no-store: {label}")


def validate_security_schemes(document: dict[str, Any]) -> None:
    schemes = document["components"]["securitySchemes"]
    if set(schemes) != {"IOSAccessToken", "PairingAccessToken"}:
        raise ValidationFailure("unexpected security scheme set")
    for name, scheme in schemes.items():
        if scheme.get("type") != "http" or scheme.get("scheme") != "bearer":
            raise ValidationFailure(f"cookie or non-bearer auth forbidden: {name}")


def validate_create(document: dict[str, Any]) -> None:
    operation = document["paths"]["/v1/import-jobs/{jobId}/upload-authorizations"]["post"]
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    properties = schema_properties(document, request_schema)
    forbidden = set(properties) & FORBIDDEN_REQUEST_FIELDS
    if forbidden:
        raise ValidationFailure(f"client may provide authoritative upload fields: {sorted(forbidden)}")

    required = set(dereference(document, request_schema).get("required", []))
    expected_required = {
        "contentLength",
        "checksumSha256Hex",
        "declaredContentType",
        "sourceSurface",
    }
    if not expected_required.issubset(required):
        raise ValidationFailure("create authorization request lacks exact size/checksum/type/source")

    security = operation.get("x-memory-security", {})
    for field in REQUIRED_CREATE_BINDINGS:
        if security.get(field) is not True:
            raise ValidationFailure(f"create authorization binding missing: {field}")
    if security.get("logSignedUrl") is not False:
        raise ValidationFailure("signed URL logging must be false")

    response = operation["responses"]["201"]
    validate_no_store(document, response, "createUploadAuthorization 201")
    response_schema = response["content"]["application/json"]["schema"]
    response_properties = schema_properties(document, response_schema)
    for field in ("uploadUrl", "objectKey", "requiredHeaders", "expiresAt"):
        if field not in response_properties:
            raise ValidationFailure(f"authorization response missing {field}")

    required_headers = response_properties["requiredHeaders"]
    header_names = set(required_headers.get("required", []))
    if not {"Content-Type", "Content-Length", "X-Content-SHA256"}.issubset(header_names):
        raise ValidationFailure("signed request headers are not exactly bound")


def validate_complete(document: dict[str, Any]) -> None:
    operation = document["paths"][
        "/v1/import-jobs/{jobId}/upload-authorizations/{uploadAuthorizationId}/complete"
    ]["post"]
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    properties = schema_properties(document, request_schema)
    forbidden = set(properties) & (
        FORBIDDEN_REQUEST_FIELDS
        | {"contentLength", "checksumSha256Hex", "declaredContentType", "etag"}
    )
    if forbidden:
        raise ValidationFailure(
            f"completion request trusts client object metadata: {sorted(forbidden)}"
        )

    security = operation.get("x-memory-security", {})
    for field, expected in REQUIRED_COMPLETE_BINDINGS.items():
        if security.get(field) is not expected:
            raise ValidationFailure(f"completion verification mismatch: {field}")
    validate_no_store(document, operation["responses"]["202"], "completeUploadAuthorization 202")


def validate_global_boundary(document: dict[str, Any]) -> None:
    boundary = document.get("x-memory-security-boundary", {})
    required_false = {
        "cookiesUsed",
        "csrfByCookieSession",
        "clientProvidedOwnerAccepted",
        "clientProvidedEpochAccepted",
        "clientProvidedObjectKeyAccepted",
        "clientProvidedBucketAccepted",
        "signedUrlStoredInLogs",
        "signedUrlStoredInAnalytics",
        "rawFilenameUsedAsObjectKey",
        "storageBucketPublic",
        "storageListPermissionForClients",
        "objectMovesDirectlyToConfirmedStorage",
    }
    required_true = {"crossOwnerLookupReturnsGenericNotFound"}
    for field in required_false:
        if boundary.get(field) is not False:
            raise ValidationFailure(f"global signed-upload boundary must be false: {field}")
    for field in required_true:
        if boundary.get(field) is not True:
            raise ValidationFailure(f"global signed-upload boundary must be true: {field}")

    for path, path_item in document["paths"].items():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not operation.get("security"):
                raise ValidationFailure(f"unauthenticated operation forbidden: {method.upper()} {path}")
            for code, response in operation.get("responses", {}).items():
                if code in {"400", "401", "404", "409", "410", "413", "415", "422", "429"}:
                    validate_no_store(document, response, f"{method.upper()} {path} {code}")


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
        document = load_json(root / SPEC_PATH)
        if document.get("openapi") != "3.1.0":
            raise ValidationFailure("OpenAPI 3.1.0 is required")
        if any(
            isinstance(value, dict) and "$ref" in value and not value["$ref"].startswith("#/")
            for value in _walk(document)
        ):
            raise ValidationFailure("remote OpenAPI references are forbidden")
        validate_security_schemes(document)
        validate_create(document)
        validate_complete(document)
        validate_global_boundary(document)
    except ValidationFailure as exc:
        print(f"SIGNED UPLOAD OPENAPI VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"SIGNED UPLOAD OPENAPI VALIDATION FAILED WITH UNEXPECTED ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    print("Memory OS signed upload OpenAPI validation PASS")
    print("client owner/epoch/object-key authority: disabled")
    print("exact size/checksum/content-type binding: required")
    print("completion metadata authority: object storage")
    print("signed URL caching/logging: disabled")
    return 0


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


if __name__ == "__main__":
    raise SystemExit(main())
