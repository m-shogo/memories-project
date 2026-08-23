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
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/sustained-soak-independent-review-contract.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/sustained-soak-independent-review-registry.v1.json"
CANONICAL_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-sustained-soak-independent-review.py"
CANONICAL_LOCK_PATH = ROOT / "contracts/operations/.sustained-soak-independent-review.lock"
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
REGISTRY = CANONICAL_REGISTRY
VALIDATOR_PATH = CANONICAL_VALIDATOR_PATH
LOCK_PATH = CANONICAL_LOCK_PATH
CANONICAL_LOCK_REF = "contracts/operations/.sustained-soak-independent-review.lock"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_file(path: Path, expected: Path, label: str) -> None:
    require(path == expected, f"{label} authority substitution")
    require(path.is_file() and not path.is_symlink(), f"{label} canonical file missing or symlinked")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise Fail(f"{label} canonical authority cannot be resolved") from exc
    require(resolved == expected, f"{label} canonical authority escaped repository path")


def enforce_runtime_authorities() -> None:
    require_exact_file(CONTRACT_PATH, CANONICAL_CONTRACT_PATH, "sustained-soak review contract")
    require_exact_file(REGISTRY, CANONICAL_REGISTRY, "sustained-soak review registry")
    require_exact_file(VALIDATOR_PATH, CANONICAL_VALIDATOR_PATH, "sustained-soak review validator")
    require(LOCK_PATH == CANONICAL_LOCK_PATH, "sustained-soak append lock authority substitution")
    require(LOCK_PATH.parent.resolve(strict=True) == CANONICAL_LOCK_PATH.parent, "sustained-soak append lock parent escaped repository path")
    if LOCK_PATH.exists():
        require(not LOCK_PATH.is_symlink(), "sustained-soak append lock must not be symlinked")
        require(LOCK_PATH.resolve(strict=True) == CANONICAL_LOCK_PATH, "sustained-soak append lock escaped repository path")


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
    enforce_runtime_authorities()
    spec = importlib.util.spec_from_file_location("memory_os_sustained_soak_review_validator", VALIDATOR_PATH)
    require(spec is not None and spec.loader is not None, "unable to import sustained-soak independent review validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.CONTRACT.resolve() == CANONICAL_CONTRACT_PATH.resolve(), "sustained-soak review validator contract authority drift")
    require(module.REGISTRY.resolve() == CANONICAL_REGISTRY.resolve(), "sustained-soak review validator registry authority drift")
    return module


def validate_lock_authority() -> None:
    enforce_runtime_authorities()
    contract = load(CONTRACT_PATH)
    lock_ref = contract.get("appendLockPath")
    require(lock_ref == CANONICAL_LOCK_REF, "sustained-soak append lock contract authority drift")
    require((ROOT / lock_ref).resolve() == LOCK_PATH.resolve(), "sustained-soak append lock writer authority drift")
    require(
        contract.get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
        "sustained-soak transactional append authority drift",
    )


def validate_existing_registry() -> None:
    """Fail closed on the canonical append-only authority before any mutation."""
    validate_lock_authority()
    registry = load(REGISTRY)
    validate_registry_for_append(registry)


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
    enforce_runtime_authorities()
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


def validate_registry_for_append(registry: dict[str, Any]) -> None:
    """Validate an arbitrary registry with the canonical full review authority."""
    validate_lock_authority()
    candidate_path = validate_candidate(registry)
    candidate_path.unlink(missing_ok=True)


def atomic_restore(payload: bytes) -> None:
    enforce_runtime_authorities()
    descriptor, temp_name = tempfile.mkstemp(
        prefix=".sustained-soak-independent-review-rollback-",
        suffix=".tmp",
        dir=REGISTRY.parent,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def replace_registry_transactionally(candidate_path: Path) -> None:
    """Install a validated candidate and rollback if canonical revalidation fails."""
    enforce_runtime_authorities()
    try:
        original = REGISTRY.read_bytes()
    except OSError as exc:
        raise Fail("cannot snapshot sustained-soak review registry before append") from exc

    validator = load_validator()
    require(validator.REGISTRY.resolve() == REGISTRY.resolve(), "sustained-soak registry validator authority drift")
    try:
        os.replace(candidate_path, REGISTRY)
        validate_registry_for_append(load(REGISTRY))
    except Exception as exc:
        atomic_restore(original)
        if isinstance(exc, (Fail, validator.Fail)):
            raise Fail(f"post-append canonical registry validation failed: {exc}") from exc
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=("criteria", "review"))
    parser.add_argument("--record", required=True, type=Path, help="Externally supplied typed JSON record. This command does not create it.")
    args = parser.parse_args()

    enforce_runtime_authorities()
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
            replace_registry_transactionally(candidate_path)
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
