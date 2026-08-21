#!/usr/bin/env python3
"""Register exact-source local logical restore evidence without claiming DR readiness."""

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
CONTRACT_PATH = ROOT / "contracts/operations/local-logical-restore-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-local-logical-restore.py"
OPERABILITY_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-operability.py"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

NEW_EXISTING = (
    "executable local PostgreSQL custom-format logical dump and separate-database restore drill",
    "restored database verification for runtime NOBYPASSRLS roles, FORCE RLS and the complete SQL integration suite",
    "synthetic deleted account and session-digest non-resurrection check across logical dump/restore",
    "exact-source machine-readable local restore result with explicit same-cluster/non-PITR limitations",
)
NEW_REFS = (
    "contracts/operations/local-logical-restore-contract.v1.json",
    "scripts/run-memory-os-local-logical-restore.sh",
    "scripts/validate-memory-os-local-logical-restore.py",
    "scripts/reconcile-memory-os-local-logical-restore.py",
    "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json",
    ".github/workflows/local-logical-restore.yml",
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
            ROOT / "contracts/operations/local-logical-restore-contract.v1.json",
            "local logical restore contract",
        ),
        (
            RESULT_PATH,
            ROOT / "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json",
            "local logical restore result",
        ),
        (
            STATUS_PATH,
            ROOT / "contracts/operations/production-operability-status.json",
            "production operability status",
        ),
        (
            VALIDATOR_PATH,
            ROOT / "scripts/validate-memory-os-local-logical-restore.py",
            "local logical restore validator",
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
        f"canonical validator rejected local logical restore authority: {path.name}",
    )


def main() -> int:
    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA", "")
    require(SHA_RE.fullmatch(expected_sha) is not None,
            "EXPECTED_COMMIT_SHA must be a full commit SHA")
    validate_runtime_authority()
    run_validator(VALIDATOR_PATH)
    run_validator(OPERABILITY_VALIDATOR_PATH)

    contract = load(CONTRACT_PATH)
    result = load(RESULT_PATH)
    require(contract.get("schemaVersion") == "memory-os-local-logical-restore.v1",
            "logical restore contract drift")
    require(result.get("commitSha") == expected_sha,
            "logical restore result is not tied to the expected source commit")
    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "logical restore scenario must be an object")
    require(scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "logical restore result is not an integrity PASS")
    environment = result.get("environment")
    require(isinstance(environment, dict) and
            environment.get("productionEvidence") is False,
            "local restore result cannot be production evidence")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "logical restore reconcile requires productionDecision NO_GO")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-007"]
    require(len(matches) == 1, "OPS-P0-007 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") in {
        "NOT_IMPLEMENTED_OR_PROVEN", "PARTIAL_FOUNDATIONS_ONLY", "PARTIAL"
    }, "logical restore reconcile cannot modify the current backup status")
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
        require((ROOT / ref).is_file(), f"logical restore evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    # Local evidence can add local evidence only. The canonical production
    # blocker set is a single imported authority and must never be expanded or
    # rewritten by this per-drill reconciler.
    require_canonical_gaps(missing, ReconcileFailure)
    require(gate.get("status") != "READY",
            "local logical restore cannot make OPS-P0-007 READY")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        print("Local logical restore status already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    original_status = STATUS_PATH.read_bytes()
    STATUS_PATH.write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        run_validator(VALIDATOR_PATH)
        run_validator(OPERABILITY_VALIDATOR_PATH)
    except Exception:
        STATUS_PATH.write_bytes(original_status)
        raise

    print("Registered exact-source local logical restore PASS; canonical production blockers unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"LOCAL LOGICAL RESTORE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
