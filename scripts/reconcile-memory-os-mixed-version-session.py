#!/usr/bin/env python3
"""Register exact-source mixed-version session evidence without over-promoting compatibility."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RESULT = ROOT / "docs/fixtures/memory-os-operability/mixed-version-session-results.sample.v1.json"
CANONICAL_CONTRACT = ROOT / "contracts/operations/mixed-version-session-contract.v1.json"
CANONICAL_STATUS = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_SESSION_VALIDATOR = ROOT / "scripts/validate-memory-os-mixed-version-session.py"
CANONICAL_VERSION_VALIDATOR = ROOT / "scripts/validate-memory-os-version-compatibility.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
RESULT = CANONICAL_RESULT
CONTRACT = CANONICAL_CONTRACT
STATUS = CANONICAL_STATUS
SESSION_VALIDATOR = CANONICAL_SESSION_VALIDATOR
VERSION_VALIDATOR = CANONICAL_VERSION_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

EVIDENCE = (
    "pinned old/current Import API two-process compatibility drill proving sessions issued by either version are resolved by the other against the complete current PostgreSQL schema while account-epoch fencing remains enforced",
)
REFS = (
    "contracts/operations/mixed-version-session-contract.v1.json",
    "scripts/run-memory-os-mixed-version-session-drill.sh",
    "scripts/validate-memory-os-mixed-version-session.py",
    "scripts/reconcile-memory-os-mixed-version-session.py",
    "docs/fixtures/memory-os-operability/mixed-version-session-results.sample.v1.json",
    ".github/workflows/mixed-version-session.yml",
)
PRECISE_GAP = (
    "full old/current backend mixed-version route, mutation, persisted-state and rollback coverage beyond the proven session/authentication slice"
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority substitution")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")
    try:
        resolved = canonical.resolve(strict=True)
    except OSError as exc:
        raise ReconcileFailure(f"canonical {label} cannot be resolved") from exc
    require(resolved == canonical, f"canonical {label} escaped repository path")


def enforce_runtime_authorities() -> None:
    for path, canonical, label in (
        (RESULT, CANONICAL_RESULT, "mixed-version session result"),
        (CONTRACT, CANONICAL_CONTRACT, "mixed-version session contract"),
        (STATUS, CANONICAL_STATUS, "production status"),
        (SESSION_VALIDATOR, CANONICAL_SESSION_VALIDATOR, "mixed-version session validator"),
        (VERSION_VALIDATOR, CANONICAL_VERSION_VALIDATOR, "version compatibility validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
    ):
        require_exact_authority(path, canonical, label)


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def append_unique(values: list[str], additions: tuple[str, ...]) -> list[str]:
    result = list(values)
    for item in additions:
        if item not in result:
            result.append(item)
    return result


def source_is_ancestor(source_sha: str) -> bool:
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", source_sha, "HEAD"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def run_validator(path: Path, *args: str) -> None:
    enforce_runtime_authorities()
    completed = subprocess.run(
        [sys.executable, str(path), *args],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"canonical validator rejected authority: {path.relative_to(ROOT)}\n{completed.stdout[-4000:]}")


def validate_authority_chain(source_sha: str) -> None:
    enforce_runtime_authorities()
    run_validator(SESSION_VALIDATOR, "--expected-commit-sha", source_sha)
    run_validator(VERSION_VALIDATOR)
    run_validator(OPERABILITY_VALIDATOR)


def main() -> int:
    enforce_runtime_authorities()
    result = load(RESULT)
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and SHA_RE.fullmatch(source_sha) is not None,
            "mixed-version session result source SHA is invalid")
    expected = os.getenv("EXPECTED_COMMIT_SHA")
    if expected:
        require(source_sha == expected, "result is not bound to the expected source SHA")
    require(source_is_ancestor(source_sha), "mixed-version session source SHA is not an ancestor of current HEAD")

    # The canonical session validator owns result/contract semantics. The direct
    # reconciler may only project authority after the full aggregate chain passes.
    validate_authority_chain(source_sha)

    original_status_bytes = STATUS.read_bytes()
    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "reconcile cannot change productionDecision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-008"]
    require(len(matches) == 1, "OPS-P0-008 must exist exactly once")
    area = matches[0]
    require(area.get("status") == "PARTIAL", "session slice cannot reconcile a non-PARTIAL OPS-P0-008")

    existing = area.get("existingEvidence")
    missing = area.get("missingEvidence")
    refs = area.get("evidenceRefs")
    require(all(isinstance(value, list) for value in (existing, missing, refs)),
            "OPS-P0-008 evidence fields must be lists")
    area["existingEvidence"] = append_unique(existing, EVIDENCE)
    area["evidenceRefs"] = append_unique(refs, REFS)

    filtered = [
        item for item in missing
        if item != "old/current backend mixed-version executable tests against an expanded schema"
    ]
    if PRECISE_GAP not in filtered:
        filtered.append(PRECISE_GAP)
    for phrase in ("persisted-state", "parser artifact", "client/server", "PostgreSQL"):
        require(any(phrase in item for item in filtered), f"required compatibility gap disappeared: {phrase}")
    area["missingEvidence"] = filtered
    require(status.get("productionDecision") == "NO_GO", "production decision changed unexpectedly")

    candidate_bytes = json.dumps(status, indent=2).encode("utf-8") + b"\n"
    if candidate_bytes == original_status_bytes:
        validate_authority_chain(source_sha)
        print("Mixed-version session authority already reconciled")
        return 0

    STATUS.write_bytes(candidate_bytes)
    try:
        validate_authority_chain(source_sha)
    except Exception:
        STATUS.write_bytes(original_status_bytes)
        raise

    print("Mixed-version session evidence reconciled without readiness promotion")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"MIXED-VERSION SESSION RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
