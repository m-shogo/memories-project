#!/usr/bin/env python3
"""Register exact-source local database commit outage evidence conservatively."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/database-commit-outage-results.sample.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_DATABASE_VALIDATOR = ROOT / "scripts/validate-memory-os-database-commit-outage.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
RESULT_PATH = CANONICAL_RESULT_PATH
STATUS_PATH = CANONICAL_STATUS_PATH
DATABASE_VALIDATOR = CANONICAL_DATABASE_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

OLD_MISSING = "database loss or failover drill"
OBSOLETE_MISSING = "direct commit resume from the preserved sealed spool without re-fetching and re-parsing the source"
NEW_EXISTING = (
    "local PostgreSQL commit-outage recovery drill proving a failed atomic Preview commit leaves zero durable rows, preserves sealed spool evidence, and ResumeCommit commits from the exact same spool/request after connectivity returns without object-store or parser access",
)
NEW_MISSING = (
    "production-shaped PostgreSQL process loss, connection-pool disruption and replication failover drill",
    "host or container restart between spool seal and ResumeCommit with durable spool remount verification",
    "database recovery verification for expired sessions, deleted accounts, leases and duplicate effects under failover",
)
NEW_REFS = (
    "contracts/operations/database-commit-outage-contract.v1.json",
    "docs/fixtures/memory-os-operability/database-commit-outage-results.sample.v1.json",
    "services/import-api/internal/importflow/database_outage_drill_linux_test.go",
    "services/import-api/internal/importflow/resume.go",
    "scripts/validate-memory-os-database-commit-outage.py",
    "scripts/reconcile-memory-os-database-commit-outage.py",
    ".github/workflows/database-commit-outage.yml",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def path_label(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


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
        (RESULT_PATH, CANONICAL_RESULT_PATH, "database outage result"),
        (STATUS_PATH, CANONICAL_STATUS_PATH, "production status"),
        (DATABASE_VALIDATOR, CANONICAL_DATABASE_VALIDATOR, "database outage validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
    ):
        require_exact_authority(path, canonical, label)


def load(path: Path) -> dict[str, Any]:
    label = path_label(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {label}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {label}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {label}")
    return value


def source_is_ancestor(source_sha: str) -> bool:
    try:
        return subprocess.run(["git", "merge-base", "--is-ancestor", source_sha, "HEAD"], cwd=ROOT, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        return False


def run_validator(path: Path, *, expected_sha: str | None = None) -> None:
    enforce_runtime_authorities()
    require(path.is_file(), f"canonical validator missing: {path.relative_to(ROOT)}")
    require(not path.is_symlink(), f"canonical validator cannot be a symlink: {path.relative_to(ROOT)}")
    env = os.environ.copy()
    if expected_sha is not None: env["EXPECTED_COMMIT_SHA"] = expected_sha
    completed = subprocess.run([sys.executable, str(path)], cwd=ROOT, env=env, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    require(type(completed.returncode) is int and completed.returncode == 0, f"canonical validator rejected authority: {path.relative_to(ROOT)}\n{completed.stdout[-4000:]}")


def validate_authority_chain(source_sha: str) -> None:
    enforce_runtime_authorities()
    run_validator(DATABASE_VALIDATOR, expected_sha=source_sha)
    run_validator(OPERABILITY_VALIDATOR)


def main() -> int:
    enforce_runtime_authorities()
    result = load(RESULT_PATH)
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and SHA_RE.fullmatch(source_sha) is not None, "database outage result source SHA is invalid")
    require(source_is_ancestor(source_sha), "database outage source SHA is not an ancestor of current HEAD")
    validate_authority_chain(source_sha)
    original_status_bytes = STATUS_PATH.read_bytes()
    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO", "database outage evidence cannot change production decision")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict), "OPS-P0-009 missing")
    require(gate.get("status") == "PARTIAL", "OPS-P0-009 must remain PARTIAL")
    existing = gate.get("existingEvidence"); missing = gate.get("missingEvidence"); refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-009 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-009 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-009 evidenceRefs must be a list")
    changed = False
    for old in (OLD_MISSING, OBSOLETE_MISSING):
        if old in missing: missing.remove(old); changed = True
    for item in NEW_EXISTING:
        if item not in existing: existing.append(item); changed = True
    for item in NEW_MISSING:
        if item not in missing: missing.append(item); changed = True
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"database outage evidence path missing: {ref}")
        if ref not in refs: refs.append(ref); changed = True
    for phrase in ("mixed-version failure", "production multi-instance", "production-shaped object-store", "production-shaped PostgreSQL", "host or container restart", "expired sessions"):
        require(any(phrase in item for item in missing), f"required OPS-P0-009 gap disappeared: {phrase}")
    require(status.get("productionDecision") == "NO_GO", "production decision changed unexpectedly")
    if not changed:
        validate_authority_chain(source_sha)
        print("Database commit outage authority already reconciled")
        return 0
    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    STATUS_PATH.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        validate_authority_chain(source_sha)
    except Exception:
        STATUS_PATH.write_bytes(original_status_bytes)
        raise
    print("Registered exact-source same-spool database commit recovery; OPS-P0-009 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"DATABASE COMMIT OUTAGE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
