#!/usr/bin/env python3
"""Fail-closed source-order validation for OPS-P0-007 recovery review evidence.

A typed Security, Operability, or cross-generation material-delta review must be created
strictly after the exact source commit recorded by the generation recovery evidence it
approves. Independent Security/Operability reviews remain optional until candidate
review begins, but once either appears both must be present. Cross-generation material-
delta review authority remains mandatory for cross-generation evidence. Review timestamps
must also fall between the source commit and the review evidence creation commit. The
current review payload must remain byte-identical to its creation blob so append-only
review evidence cannot be rewritten in place after admission. This adds chronology and
immutability binding without creating evidence, production authority, recovery objectives,
credentials, or traffic.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-generation-evidence-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
SELF_REL = Path("scripts/validate-memory-os-backup-restore-review-source-order.py")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
EVIDENCE_ROOT = Path("docs/evidence/backup-restore")
MATERIAL_DELTA_ROOT = EVIDENCE_ROOT / "material-delta"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


MAX_JSON_BYTES = 1024 * 1024


def load_json(path: Path, field: str) -> dict[str, Any]:
    """Admit only bounded, unambiguous review chronology JSON."""
    require(isinstance(path, Path) and path.is_absolute(), "review source-order JSON path invalid")
    try:
        resolved = path.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail("review source-order JSON path missing or unsafe") from None
    require(
        resolved == path and path.is_file() and not path.is_symlink(),
        "review source-order JSON path missing or unsafe",
    )

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, "review source-order JSON duplicate key refused")
            result[key] = value
        return result

    def reject_nonfinite(_value: str) -> None:
        raise Fail("review source-order JSON nonfinite number refused")

    def parse_finite_float(value: str) -> float:
        number = float(value)
        require(math.isfinite(number), "review source-order JSON nonfinite number refused")
        return number

    def parse_bounded_int(value: str) -> int:
        require(len(value.lstrip("-")) <= 128, "review source-order JSON integer too large")
        return int(value)

    try:
        with path.open("rb") as source:
            raw = source.read(MAX_JSON_BYTES + 1)
        require(len(raw) <= MAX_JSON_BYTES, "review source-order JSON size limit exceeded")
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_nonfinite,
            parse_float=parse_finite_float,
            parse_int=parse_bounded_int,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, OverflowError, RecursionError):
        raise Fail("review source-order JSON unreadable or invalid") from None
    require(isinstance(value, dict), "review source-order JSON root must be object")
    return value

def validate_contract(contract: dict[str, Any]) -> None:
    require(
        contract.get("schemaVersion") == "memory-os-backup-restore-generation-evidence.v1",
        "generation evidence contract schema drift",
    )
    require(contract.get("reviewSourceOrderValidator") == SELF_REL.as_posix(), "recovery review source-order validator authority drift")
    rules = contract.get("recordRules")
    require(isinstance(rules, dict), "generation evidence recordRules missing")
    require(
        rules.get("independentReviewMustBeCreatedStrictlyAfterSourceCommit") is True,
        "generation evidence contract must require post-source independent reviews",
    )
    require(
        rules.get("crossGenerationMaterialDeltaReviewMustBeCreatedStrictlyAfterSourceCommit") is True,
        "generation evidence contract must require post-source material-delta review",
    )
    require(
        rules.get("independentReviewPayloadMustRemainAppendOnlyAfterFirstCommit") is True,
        "generation evidence contract must preserve independent review creation payloads",
    )
    require(
        rules.get("crossGenerationMaterialDeltaReviewMustRemainAppendOnlyAfterFirstCommit") is True,
        "generation evidence contract must preserve material-delta review creation payloads",
    )
    readiness = contract.get("readiness")
    require(
        isinstance(readiness, dict) and readiness.get("reviewSourceOrderValidatorImplemented") is True,
        "generation evidence review source-order readiness drift",
    )


def canonical_review_ref(value: Any, field: str, material_delta: bool = False) -> tuple[str, Path]:
    require(isinstance(value, str) and value, f"{field} required")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == value,
            f"{field} must be canonical repository-relative path")
    root = MATERIAL_DELTA_ROOT if material_delta else EVIDENCE_ROOT
    require(relative.parts[: len(root.parts)] == root.parts and len(relative.parts) > len(root.parts),
            f"{field} must remain inside {root.as_posix()}/")
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(resolved == relative and path.is_file() and not path.is_symlink(),
            f"{field} must resolve to canonical repository file")
    return value, path


def git_output(args: list[str], field: str) -> str:
    # A source SHA or commit timestamp never requires unbounded Git diagnostics.
    try:
        completed = subprocess.run(
            ["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail(f"cannot inspect {field}") from None
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"cannot inspect {field}")
    require(isinstance(completed.stdout, str) and len(completed.stdout) <= 256,
            f"cannot inspect {field} output")
    return completed.stdout.strip()


def first_commit_for_path(ref: str, field: str) -> str:
    output = git_output(["log", "--diff-filter=A", "--max-count=2", "--follow", "--format=%H", "--", ref], field)
    commits = [line.strip() for line in output.splitlines() if line.strip()]
    require(len(commits) == 1 and SHA40.fullmatch(commits[0]) is not None,
            f"{field} must have exactly one committed creation point")
    return commits[0]


def creation_blob(commit_sha: str, ref: str, field: str) -> bytes:
    require(isinstance(commit_sha, str) and SHA40.fullmatch(commit_sha) is not None,
            f"{field} creation commit invalid")
    object_ref = f"{commit_sha}:{ref}"
    # Bound the immutable object size before asking Git to return its raw bytes.
    try:
        size_result = subprocess.run(
            ["git", "cat-file", "-s", object_ref], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail(f"cannot inspect {field} creation blob") from None
    require(type(size_result.returncode) is int and size_result.returncode == 0
            and isinstance(size_result.stdout, str)
            and re.fullmatch(r"[0-9]{1,7}\n?", size_result.stdout) is not None,
            f"cannot inspect {field} creation blob")
    expected_bytes = int(size_result.stdout.strip())
    require(0 < expected_bytes <= MAX_JSON_BYTES, f"{field} creation blob size limit exceeded")
    try:
        completed = subprocess.run(
            ["git", "show", object_ref], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail(f"cannot inspect {field} creation blob") from None
    require(type(completed.returncode) is int and completed.returncode == 0
            and isinstance(completed.stdout, bytes),
            f"cannot inspect {field} creation blob")
    require(len(completed.stdout) == expected_bytes, f"{field} creation blob size mismatch")
    return completed.stdout


def require_creation_blob_immutable(current: bytes, created: bytes, field: str) -> None:
    require(current == created, f"{field} review evidence changed after its creation commit")


def commit_exists(commit_sha: str, field: str) -> None:
    completed = subprocess.run(["git", "cat-file", "-e", f"{commit_sha}^{{commit}}"], cwd=ROOT,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"{field} sourceCommitSha must resolve to a commit")


def commit_time(commit_sha: str, field: str) -> datetime:
    value = git_output(["show", "-s", "--format=%cI", commit_sha], field)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise Fail(f"cannot parse {field} commit timestamp") from exc
    require(parsed.tzinfo is not None, f"{field} commit timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def review_time(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and len(value) == 20 and value.endswith("Z"),
            f"{field}.reviewedAt must be canonical UTC RFC3339 seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise Fail(f"{field}.reviewedAt must be canonical UTC RFC3339 seconds") from exc
    return parsed


def is_ancestor(ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant], cwd=ROOT,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise Fail("cannot compare review/source commit ancestry")


def require_source_precedes_review(source_commit: str, review_commit: str, field: str,
                                   ancestor_check: Callable[[str, str], bool] = is_ancestor) -> None:
    require(SHA40.fullmatch(source_commit) is not None, f"{field} sourceCommitSha invalid")
    require(SHA40.fullmatch(review_commit) is not None, f"{field} review commit invalid")
    require(source_commit != review_commit,
            f"{field} review must be created strictly after sourceCommitSha")
    require(ancestor_check(source_commit, review_commit),
            f"{field} review predates or is not descended from sourceCommitSha")


def require_review_time_window(reviewed_at: datetime, source_time: datetime,
                               review_commit_time: datetime, field: str) -> None:
    require(source_time <= reviewed_at, f"{field}.reviewedAt predates sourceCommitSha")
    require(reviewed_at <= review_commit_time, f"{field}.reviewedAt is later than review evidence commit")


def independent_review_refs(row: dict[str, Any], index: int) -> list[tuple[str, str, bool]]:
    security = row.get("securityReviewRef")
    operability = row.get("operabilityReviewRef")
    if security is None and operability is None:
        return []
    require(
        isinstance(security, str) and security and isinstance(operability, str) and operability,
        f"records[{index}] must provide Security and Operability reviews together",
    )
    return [
        ("securityReviewRef", security, False),
        ("operabilityReviewRef", operability, False),
    ]


def validate_row(row: dict[str, Any], index: int) -> None:
    source_commit = row.get("sourceCommitSha")
    require(isinstance(source_commit, str) and SHA40.fullmatch(source_commit) is not None,
            f"records[{index}].sourceCommitSha invalid")
    commit_exists(source_commit, f"records[{index}]")
    source_time = commit_time(source_commit, f"records[{index}].sourceCommitSha")

    refs: list[tuple[str, Any, bool]] = list(independent_review_refs(row, index))
    source_generation = row.get("sourceEnvironmentGenerationId")
    target_generation = row.get("restoreTargetGenerationId")
    if source_generation != target_generation:
        refs.append(("materialDeltaReviewRef", row.get("materialDeltaReviewRef"), True))
    else:
        require(row.get("materialDeltaReviewRef") is None,
                f"records[{index}].materialDeltaReviewRef must remain null for same-generation restore")

    for name, value, material_delta in refs:
        field = f"records[{index}].{name}"
        ref, path = canonical_review_ref(value, field, material_delta=material_delta)
        review_commit = first_commit_for_path(ref, field)
        require_source_precedes_review(source_commit, review_commit, field)
        try:
            with path.open("rb") as source:
                current_blob = source.read(MAX_JSON_BYTES + 1)
        except OSError:
            raise Fail(f"cannot read {field} current blob") from None
        require(len(current_blob) <= MAX_JSON_BYTES,
                f"{field} current blob size limit exceeded")
        require_creation_blob_immutable(current_blob, creation_blob(review_commit, ref, field), field)
        payload = load_json(path, field)
        reviewed_at = review_time(payload.get("reviewedAt"), field)
        require_review_time_window(reviewed_at, source_time, commit_time(review_commit, field), field)


def self_test() -> None:
    source = "1" * 40
    review = "2" * 40
    require_source_precedes_review(source, review, "self-test", ancestor_check=lambda _a, _b: True)
    try:
        require_source_precedes_review(source, source, "self-test", ancestor_check=lambda _a, _b: True)
    except Fail as exc:
        require("strictly after" in str(exc), "self-test rejected same-commit review at wrong boundary")
    else:
        raise Fail("self-test accepted review created in source commit")
    try:
        require_source_precedes_review(source, review, "self-test", ancestor_check=lambda _a, _b: False)
    except Fail as exc:
        require("predates" in str(exc), "self-test rejected stale review at wrong boundary")
    else:
        raise Fail("self-test accepted review that predates source commit")
    for invalid in ("", "x" * 40, "1" * 39, "1" * 41):
        try:
            require_source_precedes_review(invalid, review, "self-test", ancestor_check=lambda _a, _b: True)
        except Fail:
            pass
        else:
            raise Fail("self-test accepted invalid sourceCommitSha")

    require(independent_review_refs({}, 0) == [], "self-test rejected unreviewed non-candidate evidence")
    for partial in (
        {"securityReviewRef": "docs/evidence/backup-restore/security/review.json"},
        {"operabilityReviewRef": "docs/evidence/backup-restore/operability/review.json"},
    ):
        try:
            independent_review_refs(partial, 0)
        except Fail as exc:
            require("must provide Security and Operability reviews together" in str(exc),
                    "self-test rejected partial review pair at wrong boundary")
        else:
            raise Fail("self-test accepted partial independent review pair")

    require_creation_blob_immutable(b"review-payload\n", b"review-payload\n", "self-test")
    try:
        require_creation_blob_immutable(b"rewritten-review\n", b"review-payload\n", "self-test")
    except Fail as exc:
        require("changed after its creation commit" in str(exc), "self-test rejected rewritten review at wrong boundary")
    else:
        raise Fail("self-test accepted review evidence rewritten after creation")

    source_time = datetime(2026, 9, 12, 9, 0, 0, tzinfo=timezone.utc)
    review_time_ok = datetime(2026, 9, 12, 9, 5, 0, tzinfo=timezone.utc)
    commit_time_ok = datetime(2026, 9, 12, 9, 10, 0, tzinfo=timezone.utc)
    require_review_time_window(review_time_ok, source_time, commit_time_ok, "self-test")
    for stale, label in (
        (datetime(2026, 9, 12, 8, 59, 59, tzinfo=timezone.utc), "predates sourceCommitSha"),
        (datetime(2026, 9, 12, 9, 10, 1, tzinfo=timezone.utc), "later than review evidence commit"),
    ):
        try:
            require_review_time_window(stale, source_time, commit_time_ok, "self-test")
        except Fail as exc:
            require(label in str(exc), f"self-test rejected review timestamp at wrong boundary: {exc}")
        else:
            raise Fail("self-test accepted review timestamp outside source/review commit window")
    print("PASS: review source-order negative rejects same-commit/stale/non-descendant commits, partial independent review pairs, rewritten creation blobs, malformed source SHAs, and out-of-window review timestamps while allowing unreviewed non-candidate evidence")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        self_test()
        return 0
    require(len(sys.argv) == 1, "usage: validate-memory-os-backup-restore-review-source-order.py [--self-test]")
    contract = load_json(CONTRACT, "generation evidence contract")
    validate_contract(contract)
    registry = load_json(REGISTRY, "generation evidence registry")
    require(registry.get("schemaVersion") == "memory-os-backup-restore-generation-evidence-registry.v1",
            "generation evidence registry schema drift")
    require(registry.get("appendOnly") is True, "generation evidence registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False,
            "generation evidence registry production boundary drift")
    rows = registry.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows),
            "generation evidence registry records invalid")
    for index, row in enumerate(rows):
        validate_row(row, index)
    print(f"PASS: recovery review source-order binding records={len(rows)} productionEvidence=false productionReady=false")
    print("generation review contract source-order authority: enforced")
    print("unreviewed non-candidate generation evidence accepted: true")
    print("partial independent review pairs accepted: false")
    print("cross-generation material-delta chronology remains mandatory: true")
    print("review created in sourceCommitSha accepted: false")
    print("review predating sourceCommitSha accepted: false")
    print("review rewritten after creation accepted: false")
    print("review timestamp outside source/review commit window accepted: false")
    print("production authority created: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
