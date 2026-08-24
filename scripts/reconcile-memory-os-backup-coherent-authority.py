#!/usr/bin/env python3
"""Register local coherent DB/object recovery-set evidence without duplicating production gaps."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "contracts/operations/production-operability-status.json"
INDEX = ROOT / "contracts/operations/backup-local-foundation-evidence.v1.json"
RESULT = ROOT / "docs/fixtures/memory-os-operability/local-coherent-recovery-set-results.sample.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-local-coherent-recovery-set.py"
BACKUP_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
SHA40 = re.compile(r"^[0-9a-f]{40}$")

EVIDENCE = (
    "exact-source local PostgreSQL plus MinIO coherent recovery-set drill destroys source database state and source object versions, restores both into separate targets, independently re-derives one shared opaque recovery-set digest from restored database and object state, verifies exact backup-object checksum, and rejects a deliberate one-sided digest mismatch; this proves local shared recovery-set binding only, not temporal recovery-point skew, PITR or production-equivalent recovery",
)
REFS = (
    "contracts/operations/local-coherent-recovery-set-contract.v1.json",
    "docs/fixtures/memory-os-operability/local-coherent-recovery-set-results.sample.v1.json",
    "scripts/run-memory-os-local-coherent-recovery-set.py",
    "scripts/validate-memory-os-local-coherent-recovery-set.py",
    "scripts/reconcile-memory-os-backup-coherent-authority.py",
    ".github/workflows/local-coherent-recovery-set.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def validate_runtime_authority() -> None:
    for path, expected, label in (
        (STATUS, ROOT / "contracts/operations/production-operability-status.json", "production status"),
        (INDEX, ROOT / "contracts/operations/backup-local-foundation-evidence.v1.json", "backup local foundation index"),
        (RESULT, ROOT / "docs/fixtures/memory-os-operability/local-coherent-recovery-set-results.sample.v1.json", "coherent recovery result"),
        (VALIDATOR, ROOT / "scripts/validate-memory-os-local-coherent-recovery-set.py", "coherent restore validator"),
        (BACKUP_VALIDATOR, ROOT / "scripts/validate-memory-os-backup-restore.py", "backup restore validator"),
        (OPERABILITY_VALIDATOR, ROOT / "scripts/validate-memory-os-operability.py", "operability validator"),
    ):
        require(path == expected, f"canonical {label} identity drift")
        require(path.is_file(), f"canonical {label} missing")
        require(not path.is_symlink(), f"canonical {label} must not be a symlink")
        try:
            require(path.resolve(strict=True) == expected, f"canonical {label} path drift")
        except OSError as exc:
            raise Fail(f"cannot resolve canonical {label}") from exc


def run_validator(path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        check=False,
    )
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"canonical validator rejected coherent backup authority: {path.name}")


def source_is_ancestor(value: Any) -> bool:
    if not isinstance(value, str) or SHA40.fullmatch(value) is None:
        return False
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", value, "HEAD"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def normalized(status: dict[str, Any]) -> dict[str, Any]:
    index = load(INDEX)
    boundary = index.get("combinedBoundary")
    require(isinstance(boundary, dict), "backup local combinedBoundary missing")
    require(boundary.get("coherentDatabaseObjectRestoreCompleted") is True,
            "local coherent recovery foundation is not registered")
    require(boundary.get("coherentDatabaseObjectRestoreScope") ==
            "LOCAL_SHARED_RECOVERY_SET_DIGEST_BINDING_ONLY",
            "local coherent recovery scope drift")
    require(boundary.get("recoveryPointTimeSkewMeasured") is False,
            "local coherent recovery must not claim temporal skew measurement")

    result = load(RESULT)
    require(source_is_ancestor(result.get("commitSha")), "coherent result source is not an ancestor")
    environment = result.get("environment")
    scenario = result.get("scenario")
    require(isinstance(environment, dict) and environment.get("productionEvidence") is False,
            "coherent result production boundary drift")
    require(isinstance(scenario, dict) and scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "coherent result is not PASS")
    recovery = scenario.get("recoverySetDigest")
    require(recovery == scenario.get("databaseRecoverySetDigest") == scenario.get("objectRecoverySetDigest"),
            "coherent recovery-set digest mismatch")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict) and assertions.get("deliberateOneSidedSkewRejected") is True,
            "deliberate skew rejection missing")

    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") in {"PARTIAL_FOUNDATIONS_ONLY", "PARTIAL"},
            "unexpected OPS-P0-007 status")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(refs, list),
            "OPS-P0-007 evidence arrays missing")
    require_canonical_gaps(missing, Fail)

    for item in EVIDENCE:
        append_once(existing, item)
    for ref in REFS:
        require((ROOT / ref).is_file(), f"coherent evidence path missing: {ref}")
        append_once(refs, ref)
    gate["existingEvidence"] = existing
    gate["evidenceRefs"] = refs

    require_canonical_gaps(gate.get("missingEvidence"), Fail)
    require(gate.get("status") != "READY", "local coherence cannot make OPS-P0-007 READY")
    require(status.get("productionDecision") == "NO_GO", "production decision changed unexpectedly")
    return status


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    except OSError as exc:
        raise Fail(f"atomic authority write failed: {path.name}") from exc
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    validate_runtime_authority()
    run_validator(VALIDATOR)
    current = load(STATUS)
    candidate = normalized(copy.deepcopy(current))
    candidate["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    left = copy.deepcopy(current)
    right = copy.deepcopy(candidate)
    left.pop("asOf", None)
    right.pop("asOf", None)
    changed = left != right
    if args.check:
        require(not changed, "coherent backup authority is not normalized")
        print("Memory OS coherent backup authority check PASS")
        return 0
    if changed:
        original_bytes = STATUS.read_bytes()
        payload = (json.dumps(candidate, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        atomic_write_bytes(STATUS, payload)
        try:
            run_validator(BACKUP_VALIDATOR)
            run_validator(OPERABILITY_VALIDATOR)
        except Exception:
            atomic_write_bytes(STATUS, original_bytes)
            raise
        print("Registered local coherent recovery-set evidence in OPS-P0-007")
    else:
        print("Coherent recovery-set authority already normalized")
    print("temporal recovery-point skew measured: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, subprocess.CalledProcessError) as exc:
        print(f"COHERENT BACKUP AUTHORITY RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
