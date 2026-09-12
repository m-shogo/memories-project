#!/usr/bin/env python3
"""Fail-closed chronology validation for human backup/restore promotion reviews.

Human Recovery Owner, Security, and Operability review evidence must be created strictly
after the source commit of the final recovery evidence it reviews. Review timestamps
must also not claim a time later than the commit that first introduced the review
payload. The committed review payload must remain byte-identical to its creation blob
so review evidence cannot be rewritten in place after admission. This validator is
read-only and cannot create promotion authority, production evidence, credentials,
recovery objectives, or traffic.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
PROMOTION_REGISTRY_REL = Path("contracts/operations/backup-restore-promotion-review-registry.v1.json")
GENERATION_REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
PROMOTION_REGISTRY = ROOT / PROMOTION_REGISTRY_REL
GENERATION_REGISTRY = ROOT / GENERATION_REGISTRY_REL
EVIDENCE_ROOT = Path("docs/evidence/backup-restore")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
REVIEW_REFS = (
    "recoveryOwnerReviewRef",
    "securityReviewRef",
    "operabilityReviewRef",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_json(path: Path, field: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Fail(f"{field} unreadable or invalid JSON: {exc}") from exc
    require(isinstance(value, dict), f"{field} root must be object")
    return value


def canonical_review_ref(value: Any, field: str) -> tuple[str, Path]:
    require(isinstance(value, str) and value, f"{field} required")
    relative = Path(value)
    require(
        not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == value,
        f"{field} must be canonical repository-relative path",
    )
    require(
        relative.parts[: len(EVIDENCE_ROOT.parts)] == EVIDENCE_ROOT.parts
        and len(relative.parts) > len(EVIDENCE_ROOT.parts),
        f"{field} must remain inside {EVIDENCE_ROOT.as_posix()}/",
    )
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        resolved == relative and path.is_file() and not path.is_symlink(),
        f"{field} must resolve to canonical repository file",
    )
    return value, path


def git_output(args: list[str], field: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, f"cannot inspect {field}: {completed.stderr.strip()}")
    return completed.stdout.strip()


def first_commit_for_path(ref: str, field: str) -> str:
    output = git_output(["log", "--diff-filter=A", "--follow", "--format=%H", "--", ref], field)
    commits = [line.strip() for line in output.splitlines() if line.strip()]
    require(
        len(commits) == 1 and SHA40.fullmatch(commits[0]) is not None,
        f"{field} must have exactly one committed creation point",
    )
    return commits[0]


def creation_blob(commit_sha: str, ref: str, field: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit_sha}:{ref}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, f"cannot inspect {field} creation blob: {completed.stderr.decode('utf-8', errors='replace').strip()}")
    return completed.stdout


def require_creation_blob_immutable(current: bytes, created: bytes, field: str) -> None:
    require(current == created, f"{field} review evidence changed after its creation commit")


def commit_exists(commit_sha: str, field: str) -> None:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit_sha}^{{commit}}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
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
    require(isinstance(value, str) and value.endswith("Z"), f"{field}.reviewedAt must be UTC RFC3339 ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail(f"{field}.reviewedAt invalid") from exc
    require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, f"{field}.reviewedAt must be UTC")
    return parsed.astimezone(timezone.utc)


def is_ancestor(ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise Fail("cannot compare promotion review/source commit ancestry")


def require_source_precedes_review(
    source_commit: str,
    review_commit: str,
    field: str,
    ancestor_check: Callable[[str, str], bool] = is_ancestor,
) -> None:
    require(SHA40.fullmatch(source_commit) is not None, f"{field} sourceCommitSha invalid")
    require(SHA40.fullmatch(review_commit) is not None, f"{field} review commit invalid")
    require(source_commit != review_commit, f"{field} human promotion review must be created strictly after recovery sourceCommitSha")
    require(
        ancestor_check(source_commit, review_commit),
        f"{field} human promotion review predates or is not descended from recovery sourceCommitSha",
    )


def require_review_time_window(
    reviewed_at: datetime,
    source_time: datetime,
    review_commit_time: datetime,
    field: str,
) -> None:
    require(source_time <= reviewed_at, f"{field}.reviewedAt predates recovery sourceCommitSha")
    require(reviewed_at <= review_commit_time, f"{field}.reviewedAt is later than committed review evidence")


def generation_by_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    require(
        registry.get("schemaVersion") == "memory-os-backup-restore-generation-evidence-registry.v1",
        "generation evidence registry schema drift",
    )
    require(registry.get("appendOnly") is True, "generation evidence registry must remain append-only")
    require(
        registry.get("productionEvidence") is False and registry.get("productionReady") is False,
        "generation evidence registry production boundary drift",
    )
    rows = registry.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "generation evidence registry records invalid")
    mapping: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        evidence_id = row.get("evidenceId")
        require(isinstance(evidence_id, str) and evidence_id and evidence_id not in mapping, f"generation records[{index}].evidenceId invalid/duplicate")
        mapping[evidence_id] = row
    return mapping


def validate_row(row: dict[str, Any], index: int, generations: dict[str, dict[str, Any]]) -> None:
    evidence_id = row.get("recoveryEvidenceId")
    require(isinstance(evidence_id, str) and evidence_id in generations, f"records[{index}].recoveryEvidenceId not registered")
    generation = generations[evidence_id]
    source_commit = generation.get("sourceCommitSha")
    require(isinstance(source_commit, str) and SHA40.fullmatch(source_commit) is not None, f"records[{index}] recovery sourceCommitSha invalid")
    commit_exists(source_commit, f"records[{index}]")
    source_time = commit_time(source_commit, f"records[{index}].sourceCommitSha")

    for name in REVIEW_REFS:
        field = f"records[{index}].{name}"
        ref, path = canonical_review_ref(row.get(name), field)
        review_commit = first_commit_for_path(ref, field)
        require_source_precedes_review(source_commit, review_commit, field)
        try:
            current_blob = path.read_bytes()
        except OSError as exc:
            raise Fail(f"cannot read {field} current blob: {exc}") from exc
        require_creation_blob_immutable(current_blob, creation_blob(review_commit, ref, field), field)
        payload = load_json(path, field)
        require(payload.get("recoveryEvidenceId") == evidence_id, f"{field} recoveryEvidenceId binding mismatch")
        reviewed_at = review_time(payload.get("reviewedAt"), field)
        require_review_time_window(reviewed_at, source_time, commit_time(review_commit, field), field)


def self_test() -> None:
    source = "1" * 40
    review = "2" * 40
    require_source_precedes_review(source, review, "self-test", ancestor_check=lambda _a, _b: True)
    try:
        require_source_precedes_review(source, source, "self-test", ancestor_check=lambda _a, _b: True)
    except Fail as exc:
        require("strictly after" in str(exc), "self-test rejected same-commit promotion review at wrong boundary")
    else:
        raise Fail("self-test accepted human promotion review created in recovery source commit")
    try:
        require_source_precedes_review(source, review, "self-test", ancestor_check=lambda _a, _b: False)
    except Fail as exc:
        require("predates" in str(exc), "self-test rejected stale promotion review at wrong boundary")
    else:
        raise Fail("self-test accepted promotion review that predates recovery source commit")

    require_creation_blob_immutable(b"review-payload\n", b"review-payload\n", "self-test")
    try:
        require_creation_blob_immutable(b"rewritten-review\n", b"review-payload\n", "self-test")
    except Fail as exc:
        require("changed after its creation commit" in str(exc), "self-test rejected rewritten review at wrong boundary")
    else:
        raise Fail("self-test accepted promotion review evidence rewritten after creation")

    source_time = datetime(2026, 9, 12, 9, 0, 0, tzinfo=timezone.utc)
    review_time_ok = datetime(2026, 9, 12, 9, 5, 0, tzinfo=timezone.utc)
    commit_time_ok = datetime(2026, 9, 12, 9, 10, 0, tzinfo=timezone.utc)
    require_review_time_window(review_time_ok, source_time, commit_time_ok, "self-test")
    for invalid, label in (
        (datetime(2026, 9, 12, 8, 59, 59, tzinfo=timezone.utc), "predates recovery sourceCommitSha"),
        (datetime(2026, 9, 12, 9, 10, 1, tzinfo=timezone.utc), "later than committed review evidence"),
    ):
        try:
            require_review_time_window(invalid, source_time, commit_time_ok, "self-test")
        except Fail as exc:
            require(label in str(exc), f"self-test rejected promotion timestamp at wrong boundary: {exc}")
        else:
            raise Fail("self-test accepted promotion review timestamp outside recovery-source/review-commit window")

    for invalid in ("", "x" * 40, "1" * 39, "1" * 41):
        try:
            require_source_precedes_review(invalid, review, "self-test", ancestor_check=lambda _a, _b: True)
        except Fail:
            pass
        else:
            raise Fail("self-test accepted invalid recovery sourceCommitSha")
    print("PASS: promotion review chronology negative rejects same-commit/stale/non-descendant commits, rewritten creation blobs, malformed source SHAs, and out-of-window review timestamps")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        self_test()
        return 0
    require(len(sys.argv) == 1, "usage: validate-memory-os-backup-restore-promotion-review-source-order.py [--self-test]")

    promotion = load_json(PROMOTION_REGISTRY, "promotion review registry")
    generation = load_json(GENERATION_REGISTRY, "generation evidence registry")
    require(
        promotion.get("schemaVersion") == "memory-os-backup-restore-promotion-review-registry.v1",
        "promotion review registry schema drift",
    )
    require(promotion.get("appendOnly") is True, "promotion review registry must remain append-only")
    require(
        promotion.get("productionTrafficChanged") is False
        and promotion.get("productionEvidence") is False
        and promotion.get("productionReady") is False,
        "promotion review registry production boundary drift",
    )
    rows = promotion.get("records")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "promotion review registry records invalid")
    generations = generation_by_id(generation)
    for index, row in enumerate(rows):
        validate_row(row, index, generations)

    print(f"PASS: human promotion review source-order binding records={len(rows)} productionEvidence=false productionReady=false")
    print("promotion review created in recovery sourceCommitSha accepted: false")
    print("promotion review predating recovery sourceCommitSha accepted: false")
    print("promotion review rewritten after creation accepted: false")
    print("promotion review timestamp later than committed review evidence accepted: false")
    print("human promotion remains separate non-automatic authority: true")
    print("production authority created: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
