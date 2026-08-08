#!/usr/bin/env python3
"""Register local coherent DB/object recovery-set evidence without promoting production."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "contracts/operations/production-operability-status.json"
INDEX = ROOT / "contracts/operations/backup-local-foundation-evidence.v1.json"
RESULT = ROOT / "docs/fixtures/memory-os-operability/local-coherent-recovery-set-results.sample.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-local-coherent-recovery-set.py"
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
OLD_GAPS = {
    "coherent PostgreSQL and exact object-version recovery-point selection with measured skew",
    "coherent PostgreSQL and object-version recovery-point selection",
    "coherent PostgreSQL and exact object-version restore with measured skew",
}
PRECISE_GAP = (
    "production-shaped correlated PostgreSQL/object recovery with temporal recovery-point skew measurement, an approved skew bound and independent review"
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
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list),
            "OPS-P0-007 evidence arrays missing")
    for item in EVIDENCE:
        append_once(existing, item)
    next_missing = [item for item in missing if item not in OLD_GAPS]
    append_once(next_missing, PRECISE_GAP)
    for ref in REFS:
        require((ROOT / ref).is_file(), f"coherent evidence path missing: {ref}")
        append_once(refs, ref)
    gate["existingEvidence"] = existing
    gate["missingEvidence"] = next_missing
    gate["evidenceRefs"] = refs
    require(gate.get("status") != "READY", "local coherence cannot make OPS-P0-007 READY")
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, check=True)
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
        STATUS.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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
