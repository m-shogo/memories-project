#!/usr/bin/env python3
"""Fail-closed source-order validation for OPS-P0-007 recovery review evidence.

A typed Security, Operability, or cross-generation material-delta review must not predate
the exact source commit recorded by the generation recovery evidence it approves. This
adds a chronology binding without creating evidence, production authority, recovery
objectives, credentials, or traffic.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
REGISTRY = ROOT / REGISTRY_REL
EVIDENCE_ROOT = Path("docs/evidence/backup-restore")
MATERIAL_DELTA_ROOT = EVIDENCE_ROOT / "material-delta"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


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
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"cannot inspect {field}: {completed.stderr.strip()}")
    return completed.stdout.strip()


def first_commit_for_path(ref: str, field: str) -> str:
    output = git_output(["log", "--diff-filter=A", "--follow", "--format=%H", "--", ref], field)
    commits = [line.strip() for line in output.splitlines() if line.strip()]
    require(len(commits) == 1 and SHA40.fullmatch(commits[0]) is not None,
            f"{field} must have exactly one committed creation point")
    return commits[0]


def commit_exists(commit_sha: str, field: str) -> None:
    completed = subprocess.run(["git", "cat-file", "-e", f"{commit_sha}^{{commit}}"], cwd=ROOT,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"{field} sourceCommitSha must resolve to a commit")


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
    require(ancestor_check(source_commit, review_commit),
            f"{field} review predates or is not descended from sourceCommitSha")


def validate_row(row: dict[str, Any], index: int) -> None:
    source_commit = row.get("sourceCommitSha")
    require(isinstance(source_commit, str) and SHA40.fullmatch(source_commit) is not None,
            f"records[{index}].sourceCommitSha invalid")
    commit_exists(source_commit, f"records[{index}]")

    refs: list[tuple[str, Any, bool]] = [
        ("securityReviewRef", row.get("securityReviewRef"), False),
        ("operabilityReviewRef", row.get("operabilityReviewRef"), False),
    ]
    source_generation = row.get("sourceEnvironmentGenerationId")
    target_generation = row.get("restoreTargetGenerationId")
    if source_generation != target_generation:
        refs.append(("materialDeltaReviewRef", row.get("materialDeltaReviewRef"), True))
    else:
        require(row.get("materialDeltaReviewRef") is None,
                f"records[{index}].materialDeltaReviewRef must remain null for same-generation restore")

    for name, value, material_delta in refs:
        field = f"records[{index}].{name}"
        ref, _path = canonical_review_ref(value, field, material_delta=material_delta)
        review_commit = first_commit_for_path(ref, field)
        require_source_precedes_review(source_commit, review_commit, field)


def self_test() -> None:
    source = "1" * 40
    review = "2" * 40
    require_source_precedes_review(source, review, "self-test", ancestor_check=lambda _a, _b: True)
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
    print("PASS: review source-order negative rejects stale/non-descendant and malformed source commit bindings")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        self_test()
        return 0
    require(len(sys.argv) == 1, "usage: validate-memory-os-backup-restore-review-source-order.py [--self-test]")
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
    print("review predating sourceCommitSha accepted: false")
    print("production authority created: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
