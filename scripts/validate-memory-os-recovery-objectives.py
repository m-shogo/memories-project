#!/usr/bin/env python3
"""Validate append-only explicitly approved recovery objectives."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/recovery-objectives-admission-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/recovery-objectives-registry.v1.json")
WRITER_REL = Path("scripts/register-memory-os-recovery-objectives.py")
NEGATIVE_REL = Path("scripts/validate-memory-os-recovery-objectives-negative.py")
EXPECTED_LOCK_REL = Path("contracts/operations/.recovery-objectives.lock")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
WRITER = ROOT / WRITER_REL
EXPECTED_LOCK = ROOT / EXPECTED_LOCK_REL
NEGATIVE = ROOT / NEGATIVE_REL
EXPECTED_NEGATIVE_CASES = {
    "arbitrary repository files used as approval evidence",
    "absolute, parent-traversal or symlinked authority refs",
    "typed approval evidence content changed after registration",
    "approval evidence digest map missing, stale or contains unknown objectives",
    "typed approval bound to a different objectiveId",
    "typed approval bound to different RPO/RTO/skew values",
    "zero or negative RPO/RTO",
    "boolean RPO/RTO/skew values",
    "negative object-database skew",
    "placeholder measurement method",
    "missing owner evidence path",
    "owner evidence reused as independent approval evidence",
    "duplicate approval evidence refs",
    "missing approval evidence path",
    "approvedAt without UTC Z",
    "mutable latest alias",
    "production evidence relabel",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail(f"{field} missing or escapes repository") from None
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file() and not path.is_symlink(),
        f"{field} authority drift",
    )
    return path


def require_canonical_lock_path(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        parent = path.parent.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail(f"{field} parent missing or escapes repository") from None
    require(lexical == expected_relative, f"{field} authority drift")
    require(parent == expected_relative.parent, f"{field} parent authority drift")
    require(not path.is_symlink(), f"{field} must not be symlink")
    if path.exists():
        require(path.is_file(), f"{field} must be a file when materialized")
        try:
            resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
        except (FileNotFoundError, OSError, RuntimeError, ValueError):
            raise Fail(f"{field} materialized path escapes repository") from None
        require(resolved == expected_relative, f"{field} materialized authority drift")
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "recovery objective contract"),
        (REGISTRY, REGISTRY_REL, "recovery objective registry"),
        (WRITER, WRITER_REL, "recovery objective writer"),
        (NEGATIVE, NEGATIVE_REL, "recovery objective negative validator"),
    ):
        require_exact_repo_file(path, expected, field)
    require_canonical_lock_path(EXPECTED_LOCK, EXPECTED_LOCK_REL, "recovery objective append lock")


def repo_file(value: Any, field: str) -> Path:
    require(isinstance(value, str) and value, f"contract artifact ref invalid: {field}")
    relative = Path(value)
    require(
        not relative.is_absolute()
        and ".." not in relative.parts
        and relative.as_posix() == value,
        f"contract artifact ref must be canonical repository-relative path: {field}",
    )
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail(f"contract artifact missing or escapes repository: {field}") from None
    require(resolved == relative and path.is_file(), f"contract artifact must resolve to canonical repository file: {field}")
    return path


def repo_directory(path: Path, field: str) -> Path:
    try:
        relative = path.relative_to(ROOT)
        resolved = path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        raise Fail(f"contract authority directory escapes repository: {field}") from None
    require(relative == resolved, f"contract authority directory must resolve canonically: {field}")
    require(not path.exists() or path.is_dir(), f"contract authority path must be a directory when present: {field}")
    return path


MAX_JSON_BYTES = 1024 * 1024


def load(path: Path) -> dict[str, Any]:
    """Admit only bounded, unambiguous explicitly approved recovery-objective JSON."""
    require(isinstance(path, Path) and path.is_absolute(), "recovery objective JSON path invalid")
    try:
        relative = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail("recovery objective JSON path missing or outside repository") from None
    require(
        relative == resolved and path.is_file() and not path.is_symlink(),
        "recovery objective JSON path unsafe",
    )

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, "recovery objective JSON duplicate key refused")
            result[key] = value
        return result

    def reject_nonfinite(_value: str) -> None:
        raise Fail("recovery objective JSON nonfinite number refused")

    def parse_finite_float(value: str) -> float:
        number = float(value)
        require(math.isfinite(number), "recovery objective JSON nonfinite number refused")
        return number

    def parse_bounded_int(value: str) -> int:
        require(len(value.lstrip("-")) <= 128, "recovery objective JSON integer too large")
        return int(value)

    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_NONBLOCK"),
            "recovery objective JSON platform unsafe")
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        metadata = os.fstat(descriptor)
        require(stat.S_ISREG(metadata.st_mode), "recovery objective JSON path unsafe")
        require(metadata.st_size <= MAX_JSON_BYTES, "recovery objective JSON size limit exceeded")
        with os.fdopen(descriptor, "rb") as source:
            descriptor = None
            raw = source.read(MAX_JSON_BYTES + 1)
        require(len(raw) <= MAX_JSON_BYTES, "recovery objective JSON size limit exceeded")
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_nonfinite,
            parse_float=parse_finite_float,
            parse_int=parse_bounded_int,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError,
            OverflowError, RecursionError):
        raise Fail("recovery objective JSON unreadable or invalid") from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                raise Fail("recovery objective JSON descriptor cleanup failed") from None
    require(isinstance(value, dict), "recovery objective JSON root must be object")
    return value

def load_writer():
    require_exact_repo_file(WRITER, WRITER_REL, "recovery objective writer")
    writer_path = WRITER
    spec = importlib.util.spec_from_file_location("memory_os_recovery_objectives_writer", writer_path)
    require(spec is not None and spec.loader is not None, "cannot load recovery objectives writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_negative() -> None:
    """Execute negative admission without retaining or echoing private validator output."""
    require_exact_repo_file(NEGATIVE, NEGATIVE_REL, "recovery objective negative validator")
    try:
        completed = subprocess.run(
            [sys.executable, str(NEGATIVE)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail("recovery objective negative admission unavailable or timed out (raw output withheld)") from None
    require(
        type(completed.returncode) is int and completed.returncode == 0,
        "recovery objective negative admission suite failed (raw output withheld)",
    )


def require_negative_admission_cases(negative_cases: Any) -> None:
    """Validate typed case authority before constructing any set."""
    require(
        isinstance(negative_cases, list)
        and all(isinstance(case, str) for case in negative_cases)
        and len(negative_cases) == len(set(negative_cases))
        and set(negative_cases) == EXPECTED_NEGATIVE_CASES,
        "negative admission case authority drift",
    )


def main() -> int:
    enforce_runtime_authorities()
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    writer = load_writer()

    writer_authorities = (
        ("CONTRACT", "CANONICAL_CONTRACT", CONTRACT, "recovery objective contract"),
        ("REGISTRY", "CANONICAL_REGISTRY", REGISTRY, "recovery objective registry"),
    )
    for runtime_name, canonical_name, expected_path, field in writer_authorities:
        runtime_path = getattr(writer, runtime_name, None)
        canonical_path = getattr(writer, canonical_name, None)
        require(runtime_path == expected_path, f"writer runtime authority drift: {runtime_name}")
        require(canonical_path == expected_path, f"writer canonical authority drift: {canonical_name}")
        writer.canonical_repo_file(runtime_path, field)
    writer_lock = getattr(writer, "LOCK", None)
    require(writer_lock == EXPECTED_LOCK, "writer append lock authority drift")
    require_canonical_lock_path(writer_lock, EXPECTED_LOCK_REL, "writer recovery objective append lock")
    require(writer_lock.parent == REGISTRY.parent, "writer append lock must share registry authority directory")
    approval_dir = getattr(writer, "APPROVAL_DIR", None)
    canonical_approval_dir = getattr(writer, "CANONICAL_APPROVAL_DIR", None)
    require(approval_dir == canonical_approval_dir, "writer approval authority directory drift")
    require(isinstance(approval_dir, Path), "writer approval authority directory missing")
    repo_directory(approval_dir, "recovery objective approval authority directory")

    require(contract.get("schemaVersion") == "memory-os-recovery-objectives-admission.v1", "contract schema drift")
    expected_refs = {
        "registry": REGISTRY,
        "writer": WRITER,
        "negativeAdmissionValidator": NEGATIVE,
    }
    for field, path in expected_refs.items():
        expected_ref = str(path.relative_to(ROOT))
        require(contract.get(field) == expected_ref, f"contract ref drift: {field}")
        repo_file(expected_ref, field)
    for field in ("validator", "reconcile", "workflow"):
        repo_file(contract.get(field), field)
    rules = contract.get("rules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "recovery-objective rules must remain fail-closed")
    for key in (
        "measurementMethodsCannotBePlaceholderText",
        "ownerRefMustExistInRepository",
        "authorityRefsMustBeCanonicalRepositoryFiles",
        "exactlyTwoTypedApprovalEvidenceRefsRequired",
        "approvalEvidenceMustUseDedicatedAuthorityDirectory",
        "approvalEvidenceContentMustBeSha256BoundInRegistry",
        "approvalEvidenceDigestMapMustExactlyMatchRegisteredObjectives",
        "recoveryOwnerAndOperabilityApprovalRolesRequired",
        "approvalReviewersMustBeDistinct",
        "reviewerPseudonymsMustBeCanonicalNonEmptyText",
        "approvalDecisionMustBeApproved",
        "approvalMustBindObjectiveIdScopeRpoRtoAndSkew",
        "approvalCannotPostDateObjectiveApproval",
        "approvalCannotAuthorizeProductionTrafficCredentialsOrAutomaticPromotion",
        "ownerRefMustBeDistinctFromApprovalEvidenceRefs",
        "approvedAtMustBeUtcRfc3339Z",
        "implicitDefaultsForbidden",
        "mutableLatestAliasForbidden",
        "rawUrlsSecretsAccountAndSessionIdentifiersForbidden",
    ):
        require(rules.get(key) is True, f"required recovery-objective rule missing: {key}")
    require_negative_admission_cases(contract.get("negativeAdmissionCases"))

    rows = writer.validate_registry_for_append(registry)
    count = registry.get("approvedObjectiveCount")
    current_id = registry.get("currentObjectiveId")
    require(isinstance(count, int) and not isinstance(count, bool) and count == len(rows), "approvedObjectiveCount drift")

    authority = contract.get("currentAuthority")
    require(isinstance(authority, dict), "currentAuthority required")
    authority_count = authority.get("approvedObjectiveCount")
    require(isinstance(authority_count, int) and not isinstance(authority_count, bool), "contract approvedObjectiveCount must be integer")
    require(authority_count == count, "contract objective count drift")
    require(authority.get("currentObjectiveId") == current_id, "contract currentObjectiveId drift")
    defined = count > 0
    require(authority.get("rpoDefined") is defined, "rpoDefined drift")
    require(authority.get("rtoDefined") is defined, "rtoDefined drift")
    require(authority.get("objectDatabaseSkewDefined") is defined, "objectDatabaseSkewDefined drift")
    require(authority.get("productionEvidence") is False and authority.get("productionReady") is False, "objective authority cannot promote production")
    require(authority.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")

    run_negative()

    print("Memory OS recovery objectives validation PASS")
    print("recovery objective validator canonical runtime authorities enforced: true")
    print("ephemeral append lock may be absent but path authority remains canonical: true")
    print(f"approved objective records: {count}")
    print(f"current objective: {current_id or 'none'}")
    print(f"RPO/RTO defined: {str(defined).lower()}")
    print("typed Recovery Owner/Operability approval binding: required")
    print("approval evidence SHA-256 binding: required")
    print("arbitrary repository approval files accepted: false")
    print("canonical repository authority refs required: true")
    print("canonical writer contract/registry/approval authority validated without objective rows: true")
    print("canonical writer append lock authority validated: true")
    print("empty canonical approval authority directory permitted before first evidence file: true")
    print("canonical reviewer pseudonyms required: true")
    print("objective values chosen/defaulted by validator: false")
    print("boolean objective counts accepted: false")
    print("negative admission case authority exact: true")
    print("negative admission suite: PASS")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVES VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
