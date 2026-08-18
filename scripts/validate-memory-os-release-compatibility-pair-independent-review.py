#!/usr/bin/env python3
"""Validate typed independent review evidence for approved release compatibility pairs."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PAIR_WRITER = ROOT / "scripts/register-memory-os-release-compatibility-pair.py"
REGISTRY = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
REVIEW_ROOT = ROOT / "docs/evidence/release-compatibility-pairs/reviews"
REVIEW_SCHEMA = "memory-os-release-compatibility-pair-independent-review.v1"
REVIEW_FIELDS = {
    "schemaVersion",
    "pairId",
    "predecessorReleaseId",
    "successorReleaseId",
    "reviewRole",
    "reviewerPseudonym",
    "decision",
    "reviewedAt",
    "productionTrafficChanged",
    "credentialsChanged",
    "automaticPromotion",
}
REVIEWER = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
EXPECTED_ROLES = {"SECURITY", "OPERABILITY"}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot load {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load authority module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_utc_seconds(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be canonical UTC RFC3339 seconds")
    require("." not in value, f"{field} must not contain fractional seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise Fail(f"{field} must be canonical UTC RFC3339 seconds") from exc
    return parsed


def validate_review_payload(pair: dict[str, Any], review: dict[str, Any]) -> tuple[str, str]:
    require(set(review) == REVIEW_FIELDS, f"independent review field drift: {sorted(set(review) ^ REVIEW_FIELDS)}")
    require(review.get("schemaVersion") == REVIEW_SCHEMA, "independent review schema drift")
    require(review.get("pairId") == pair.get("pairId"), "independent review pairId mismatch")
    require(review.get("predecessorReleaseId") == pair.get("predecessorReleaseId"), "independent review predecessor mismatch")
    require(review.get("successorReleaseId") == pair.get("successorReleaseId"), "independent review successor mismatch")
    role = review.get("reviewRole")
    require(role in EXPECTED_ROLES, "independent review role must be SECURITY or OPERABILITY")
    reviewer = review.get("reviewerPseudonym")
    require(isinstance(reviewer, str) and REVIEWER.fullmatch(reviewer), "independent review reviewerPseudonym invalid")
    require(review.get("decision") == "APPROVED", "independent review decision must be APPROVED")
    reviewed_at = parse_utc_seconds(review.get("reviewedAt"), "independent review reviewedAt")
    approved_at = parse_utc_seconds(pair.get("approvedAt"), "pair approvedAt")
    require(reviewed_at <= approved_at, "independent review cannot post-date pair approval")
    require(review.get("productionTrafficChanged") is False, "independent review cannot change production traffic")
    require(review.get("credentialsChanged") is False, "independent review cannot change credentials")
    require(review.get("automaticPromotion") is False, "independent review cannot authorize automatic promotion")
    return role, reviewer


def validate_pair_reviews_from_payloads(pair: dict[str, Any], payloads: list[dict[str, Any]]) -> None:
    require(len(payloads) == 2, "exactly two typed independent reviews are required")
    approvals = [validate_review_payload(pair, review) for review in payloads]
    roles = {role for role, _ in approvals}
    reviewers = {reviewer for _, reviewer in approvals}
    require(roles == EXPECTED_ROLES, "independent reviews must contain exactly SECURITY and OPERABILITY roles")
    require(len(reviewers) == 2, "independent reviews require distinct reviewer identities")


def review_path(ref: Any) -> Path:
    require(isinstance(ref, str) and ref, "independentReviewRefs must contain non-empty strings")
    path = ROOT / ref
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(REVIEW_ROOT.resolve())
    except (OSError, ValueError) as exc:
        raise Fail(f"independent review must be under docs/evidence/release-compatibility-pairs/reviews: {ref}") from exc
    require(path.is_file(), f"independent review is not a regular file: {ref}")
    return path


def validate_pair_reviews(pair: dict[str, Any]) -> None:
    refs = pair.get("independentReviewRefs")
    require(isinstance(refs, list) and len(refs) == 2 and len(set(refs)) == 2, "independentReviewRefs must contain exactly two distinct refs")
    payloads = [load(review_path(ref)) for ref in refs]
    validate_pair_reviews_from_payloads(pair, payloads)


def main() -> int:
    writer = load_module(PAIR_WRITER, "memory_os_release_pair_writer_for_review_validation")
    registry = load(REGISTRY)
    try:
        writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"release compatibility pair registry authority invalid: {exc}") from exc
    pairs = registry.get("pairs")
    require(isinstance(pairs, list), "release compatibility pair registry pairs invalid")
    print(f"PASS: typed independent review authority validated for {len(pairs)} release compatibility pair(s)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE COMPATIBILITY PAIR INDEPENDENT REVIEW FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
