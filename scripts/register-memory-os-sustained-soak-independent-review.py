#!/usr/bin/env python3
"""Append an externally supplied sustained-soak criteria or review record.

This command never invents thresholds, reviewers, approval evidence, production
state, or run bindings. The caller must supply a complete typed JSON record and
its referenced human evidence must already exist in the dedicated repository
location. The full candidate registry is validated before the append is made.
"""

from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/sustained-soak-independent-review-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/sustained-soak-independent-review-registry.v1.json"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-sustained-soak-independent-review.py"
LOCK_PATH = ROOT / "contracts/operations/.sustained-soak-independent-review.lock"
CANONICAL_LOCK_REF = "contracts/operations/.sustained-soak-independent-review.lock"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing JSON input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON input: {path}: {exc}") from exc
    require(isinstance(value, dict), f"JSON root must be object: {path}")
    return value


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_sustained_soak_review_validator", VALIDATOR_PATH)
    require(spec is not None and spec.loader is not None, "unable to import sustained-soak independent review validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_lock_authority() -> None:
    contract = load(CONTRACT_PATH)
    lock_ref = contract.get("appendLockPath")
    require(lock_ref == CANONICAL_LOCK_REF, "sustained-soak append lock contract authority drift")
    require((ROOT / lock_ref).resolve() == LOCK_PATH.resolve(), "sustained-soak append lock writer authority drift")


def validate_existing_registry() -> None:
    """Fail closed on the canonical append-only authority before any mutation."""
    validate_lock_authority()
    registry = load(REGISTRY)
    validator = load_validator()
    require(validator.REGISTRY.resolve() == REGISTRY.resolve(), "sustained-soak registry validator authority drift")
    try:
        validator.validate_registry_aggregates(registry)
        validator.main()
    except validator.Fail as exc:
        raise Fail(f"existing registry rejected before append: {exc}") from exc


def recompute_counts(registry: dict[str, Any]) -> None:
    criteria = registry.get("criteria")
    reviews = registry.get("reviews")
    require(isinstance(criteria, list), "registry.criteria must be list")
    require(isinstance(reviews, list), "registry.reviews must be list")
    current_criteria_id: str | None = None
    if criteria:
        current = criteria[-1]
        require(isinstance(current, dict), "current criteria row must be object")
        current_criteria_id = current.get("criteriaId")
        require(isinstance(current_criteria_id, str) and current_criteria_id,
                "current criteria row requires criteriaId")
    registry["registeredCriteriaCount"] = len(criteria)
    registry["approvedLeakStabilityCriteriaCount"] = len(criteria)
    registry["registeredReviewCount"] = len(reviews)
    registry["passingIndependentReviewCount"] = sum(
        1
        for review in reviews
        if isinstance(review, dict)
        and review.get("outcome") == "PASS"
        and review.get("criteriaId") == current_criteria_id
    )
    for field in (
        "leakProof",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "productionSustainedSoakEvidence",
        "productionReady",
    ):
        registry[field] = False
    registry["productionEvidence"] = False


def append_record(registry: dict[str, Any], kind: str, record: dict[str, Any]) -> str:
    if kind == "criteria":
        rows = registry.get("criteria")
        require(isinstance(rows, list), "registry.criteria must be list")
        record_id = record.get("criteriaId")
        require(isinstance(record_id, str) and record_id, "criteria record requires criteriaId")
        require(all(not isinstance(row, dict) or row.get("criteriaId") != record_id for row in rows), "criteriaId already registered")
        rows.append(record)
    else:
        rows = registry.get("reviews")
        require(isinstance(rows, list), "registry.reviews must be list")
        record_id = record.get("reviewId")
        require(isinstance(record_id, str) and record_id, "review record requires reviewId")
        require(all(not isinstance(row, dict) or row.get("reviewId") != record_id for row in rows), "reviewId already registered")
        rows.append(record)
    recompute_counts(registry)
    return record_id


def validate_candidate(candidate: dict[str, Any]) -> Path:
    validator = load_validator()
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        prefix=".sustained-soak-independent-review-registry-candidate-",
        dir=REGISTRY.parent,
        delete=False,
    )
    path = Path(handle.name)
    try:
        json.dump(candidate, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        original_registry = validator.REGISTRY
        validator.REGISTRY = path
        try:
            validator.main()
        except validator.Fail as exc:
            raise Fail(f"candidate registry rejected: {exc}") from exc
        finally:
            validator.REGISTRY = original_registry
        return path
    except Exception:
        try:
            handle.close()
        except Exception:
            pass
        path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=("criteria", "review"))
    parser.add_argument("--record", required=True, type=Path, help="Externally supplied typed JSON record. This command does not create it.")
    args = parser.parse_args()

    require(args.record.resolve() != REGISTRY.resolve(), "record input must not be the canonical registry")
    record = load(args.record)
    validate_lock_authority()
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        validate_existing_registry()
        registry = load(REGISTRY)
        record_id = append_record(registry, args.kind, record)
        candidate_path = validate_candidate(registry)
        try:
            os.replace(candidate_path, REGISTRY)
        finally:
            candidate_path.unlink(missing_ok=True)

    print("Memory OS sustained-soak independent review record appended")
    print(f"kind: {args.kind}")
    print(f"record id: {record_id}")
    print("thresholds generated automatically: false")
    print("human evidence generated automatically: false")
    print("superseded criteria PASS review remains current authority: false")
    print("leak proof promoted automatically: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"SUSTAINED SOAK INDEPENDENT REVIEW REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
