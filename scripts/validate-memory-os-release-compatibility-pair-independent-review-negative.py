#!/usr/bin/env python3
"""Negative coverage for typed release-pair independent review semantics."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-release-compatibility-pair-independent-review.py"
WRITER = ROOT / "scripts/register-memory-os-release-compatibility-pair.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load authority module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action: Callable[[], None]) -> None:
    try:
        action()
    except Exception:
        return
    raise Fail(f"typed independent review accepted invalid case: {name}")


def expect_rejected_with(name: str, expected: str, action: Callable[[], None]) -> None:
    try:
        action()
    except Exception as exc:
        require(expected in str(exc), f"{name} rejected for wrong reason: {exc}")
        return
    raise Fail(f"typed independent review accepted invalid case: {name}")


def pair() -> dict[str, Any]:
    return {
        "pairId": "rcp_release_pair_test1",
        "predecessorReleaseId": "rel_20260815_pairpred",
        "successorReleaseId": "rel_20260816_pairsucc",
        "approvedAt": "2026-08-16T00:00:00Z",
    }


def review(role: str, reviewer: str) -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-release-compatibility-pair-independent-review.v1",
        "pairId": "rcp_release_pair_test1",
        "predecessorReleaseId": "rel_20260815_pairpred",
        "successorReleaseId": "rel_20260816_pairsucc",
        "reviewRole": role,
        "reviewerPseudonym": reviewer,
        "decision": "APPROVED",
        "reviewedAt": "2026-08-15T23:59:00Z",
        "productionTrafficChanged": False,
        "credentialsChanged": False,
        "automaticPromotion": False,
    }


def main() -> int:
    validator = load_module(VALIDATOR, "memory_os_release_pair_independent_review_negative")
    base_pair = pair()
    security = review("SECURITY", "security-reviewer-a")
    operability = review("OPERABILITY", "operability-reviewer-b")
    validator.validate_pair_reviews_from_payloads(base_pair, [security, operability])

    cases: list[tuple[str, Callable[[], None]]] = []

    generic = {"approved": True}
    cases.append(("generic repository document", lambda: validator.validate_pair_reviews_from_payloads(base_pair, [generic, operability])))

    wrong_pair = copy.deepcopy(security)
    wrong_pair["pairId"] = "rcp_wrong_pair"
    cases.append(("pair binding mismatch", lambda: validator.validate_pair_reviews_from_payloads(base_pair, [wrong_pair, operability])))

    wrong_predecessor = copy.deepcopy(security)
    wrong_predecessor["predecessorReleaseId"] = "rel_wrong_predecessor"
    cases.append(("predecessor binding mismatch", lambda: validator.validate_pair_reviews_from_payloads(base_pair, [wrong_predecessor, operability])))

    wrong_successor = copy.deepcopy(operability)
    wrong_successor["successorReleaseId"] = "rel_wrong_successor"
    cases.append(("successor binding mismatch", lambda: validator.validate_pair_reviews_from_payloads(base_pair, [security, wrong_successor])))

    duplicate_role = copy.deepcopy(operability)
    duplicate_role["reviewRole"] = "SECURITY"
    cases.append(("duplicate review role", lambda: validator.validate_pair_reviews_from_payloads(base_pair, [security, duplicate_role])))

    reused_reviewer = copy.deepcopy(operability)
    reused_reviewer["reviewerPseudonym"] = security["reviewerPseudonym"]
    cases.append(("reviewer identity reuse", lambda: validator.validate_pair_reviews_from_payloads(base_pair, [security, reused_reviewer])))

    rejected = copy.deepcopy(security)
    rejected["decision"] = "REJECTED"
    cases.append(("non-approved decision", lambda: validator.validate_pair_reviews_from_payloads(base_pair, [rejected, operability])))

    post_approval = copy.deepcopy(operability)
    post_approval["reviewedAt"] = "2026-08-16T00:00:01Z"
    cases.append(("review after pair approval", lambda: validator.validate_pair_reviews_from_payloads(base_pair, [security, post_approval])))

    traffic = copy.deepcopy(security)
    traffic["productionTrafficChanged"] = True
    cases.append(("production traffic mutation", lambda: validator.validate_pair_reviews_from_payloads(base_pair, [traffic, operability])))

    credentials = copy.deepcopy(security)
    credentials["credentialsChanged"] = True
    cases.append(("credential mutation", lambda: validator.validate_pair_reviews_from_payloads(base_pair, [credentials, operability])))

    automatic = copy.deepcopy(security)
    automatic["automaticPromotion"] = True
    cases.append(("automatic promotion", lambda: validator.validate_pair_reviews_from_payloads(base_pair, [automatic, operability])))

    malformed_time = copy.deepcopy(security)
    malformed_time["reviewedAt"] = "2026-99-99T99:99:99Z"
    cases.append(("invalid reviewedAt", lambda: validator.validate_pair_reviews_from_payloads(base_pair, [malformed_time, operability])))

    for name, action in cases:
        expect_rejected(name, action)

    writer = load_module(WRITER, "memory_os_release_pair_writer_review_delegation_negative")
    original_validate_record = writer.validate_record
    original_validated_release_registry = writer.validated_release_registry
    original_load_module = writer.load_module

    class RejectingReviewValidator:
        @staticmethod
        def validate_pair_reviews(_pair: dict[str, Any]) -> None:
            raise RuntimeError("controlled typed review rejection")

    try:
        writer.validate_record = lambda _row: None
        writer.validated_release_registry = lambda: {"approvedReleaseCount": 2}
        writer.load_module = lambda _path, _name: RejectingReviewValidator
        historical_registry = {
            "schemaVersion": "memory-os-release-compatibility-pair-registry.v1",
            "appendOnly": True,
            "approvedPairCount": 1,
            "rollbackEligiblePairCount": 1,
            "latestPairId": "rcp_release_pair_test1",
            "pairs": [
                {
                    "pairId": "rcp_release_pair_test1",
                    "predecessorReleaseId": "rel_20260815_pairpred",
                    "successorReleaseId": "rel_20260816_pairsucc",
                }
            ],
            "productionEvidence": False,
            "productionReady": False,
            "limitations": ["synthetic registry used only to prove historical review delegation"],
        }
        expect_rejected_with(
            "historical registry typed review delegation",
            "typed independent review authority invalid",
            lambda: writer.validate_registry_for_append(historical_registry),
        )
    finally:
        writer.validate_record = original_validate_record
        writer.validated_release_registry = original_validated_release_registry
        writer.load_module = original_load_module

    print(f"PASS: typed release-pair independent review rejects {len(cases)} semantic bypass cases and historical registry bypass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE COMPATIBILITY PAIR INDEPENDENT REVIEW NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
