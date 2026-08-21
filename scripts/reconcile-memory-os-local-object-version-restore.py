#!/usr/bin/env python3
"""Register exact-source local object-version restore evidence without claiming production retention."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/local-object-version-restore-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/local-object-version-restore-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-local-object-version-restore.py"
BACKUP_RESTORE_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-backup-restore.py"
OPERABILITY_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-operability.py"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

NEW_EXISTING = (
    "executable local three-bucket MinIO exact-version recovery drill using explicit source and backup VersionIds",
    "complete simulated source-version loss before restore with backup checksum and source-version metadata binding preserved",
    "privacy-safe exact-source object recovery result storing only SHA-256 digests of bucket, key and provider version identifiers",
)
NEW_REFS = (
    "contracts/operations/local-object-version-restore-contract.v1.json",
    "scripts/run-memory-os-local-object-version-restore.py",
    "scripts/validate-memory-os-local-object-version-restore.py",
    "scripts/reconcile-memory-os-local-object-version-restore.py",
    "docs/fixtures/memory-os-operability/local-object-version-restore-results.sample.v1.json",
    ".github/workflows/local-object-version-restore.yml",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def validate_runtime_authority() -> None:
    for path, expected, label in (
        (
            CONTRACT_PATH,
            ROOT / "contracts/operations/local-object-version-restore-contract.v1.json",
            "local object-version restore contract",
        ),
        (
            RESULT_PATH,
            ROOT / "docs/fixtures/memory-os-operability/local-object-version-restore-results.sample.v1.json",
            "local object-version restore result",
        ),
        (
            STATUS_PATH,
            ROOT / "contracts/operations/production-operability-status.json",
            "production operability status",
        ),
        (
            VALIDATOR_PATH,
            ROOT / "scripts/validate-memory-os-local-object-version-restore.py",
            "local object-version restore validator",
        ),
        (
            BACKUP_RESTORE_VALIDATOR_PATH,
            ROOT / "scripts/validate-memory-os-backup-restore.py",
            "backup/restore validator",
        ),
        (
            OPERABILITY_VALIDATOR_PATH,
            ROOT / "scripts/validate-memory-os-operability.py",
            "operability validator",
        ),
    ):
        require(path == expected, f"canonical {label} identity drift")
        require(path.is_file(), f"canonical {label} missing")
        require(not path.is_symlink(), f"canonical {label} must not be a symlink")
        try:
            require(path.resolve(strict=True) == expected, f"canonical {label} path drift")
        except OSError as exc:
            raise ReconcileFailure(f"cannot resolve canonical {label}") from exc


def run_validator(path: Path) -> None:
    completed = subprocess.run([sys.executable, str(path)], cwd=ROOT, check=False)
    require(
        type(completed.returncode) is int and completed.returncode == 0,
        f"canonical validator rejected local object-version restore authority: {path.name}",
    )


def main() -> int:
    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA", "")
    require(SHA_RE.fullmatch(expected_sha) is not None,
            "EXPECTED_COMMIT_SHA must be a full commit SHA")
    validate_runtime_authority()
    for validator in (
        VALIDATOR_PATH,
        BACKUP_RESTORE_VALIDATOR_PATH,
        OPERABILITY_VALIDATOR_PATH,
    ):
        run_validator(validator)

    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)
    require(contract.get("schemaVersion") ==
            "memory-os-local-object-version-restore.v1",
            "object restore contract drift")
    require(result.get("commitSha") == expected_sha,
            "object restore result is not tied to expected source commit")
    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "object restore scenario must be an object")
    require(scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "object restore result is not an integrity PASS")
    environment = result.get("environment")
    require(isinstance(environment, dict) and
            environment.get("productionEvidence") is False,
            "local object restore cannot be production evidence")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "object restore reconcile requires productionDecision NO_GO")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-007"]
    require(len(matches) == 1, "OPS-P0-007 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") in {
        "NOT_IMPLEMENTED_OR_PROVEN", "PARTIAL_FOUNDATIONS_ONLY", "PARTIAL"
    }, "object restore reconcile cannot modify the current backup status")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-007 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-007 missingEvidence must be a list")
    if refs is None:
        refs = []
        gate["evidenceRefs"] = refs
    require(isinstance(refs, list), "OPS-P0-007 evidenceRefs must be a list")
    require_canonical_gaps(missing, ReconcileFailure)

    changed = False
    if gate.get("status") == "NOT_IMPLEMENTED_OR_PROVEN":
        gate["status"] = "PARTIAL_FOUNDATIONS_ONLY"
        changed = True
    for item in NEW_EXISTING:
        changed = append_once(existing, item) or changed
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"object restore evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    # Local evidence can add local evidence only. The canonical production
    # blocker set is a single imported authority and must never be expanded or
    # rewritten by this per-drill reconciler.
    require_canonical_gaps(missing, ReconcileFailure)
    require(gate.get("status") != "READY",
            "local object restore cannot make OPS-P0-007 READY")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        print("Local object-version restore status already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    original_status = STATUS_PATH.read_bytes()
    STATUS_PATH.write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        for validator in (
            VALIDATOR_PATH,
            BACKUP_RESTORE_VALIDATOR_PATH,
            OPERABILITY_VALIDATOR_PATH,
        ):
            run_validator(validator)
    except Exception:
        STATUS_PATH.write_bytes(original_status)
        raise

    print("Registered exact-source local object-version restore PASS; canonical production blockers unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"LOCAL OBJECT RESTORE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
