#!/usr/bin/env python3
"""Classify existing candidate/local mixed-version SIGKILL recovery in OPS-P0-009.

This does not change the canonical production-shaped chaos scenario. It only
prevents the status ledger from calling all mixed-version failure behavior
unproven after the exact candidate/local Apply interruption result passed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / "contracts/operations/version-compatibility-execution-evidence.v1.json"
RESULT = ROOT / "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
MIXED_VERSION_VALIDATOR = ROOT / "scripts/validate-memory-os-mixed-version-apply.py"
EXECUTION_VALIDATOR = ROOT / "scripts/validate-memory-os-version-compatibility-execution-evidence.py"
CHAOS_VALIDATOR = ROOT / "scripts/validate-memory-os-chaos-failure-drills-v2.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"

CANONICAL_AUTHORITIES = {
    "execution": ROOT / "contracts/operations/version-compatibility-execution-evidence.v1.json",
    "result": ROOT / "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json",
    "status": ROOT / "contracts/operations/production-operability-status.json",
    "mixed-version validator": ROOT / "scripts/validate-memory-os-mixed-version-apply.py",
    "execution validator": ROOT / "scripts/validate-memory-os-version-compatibility-execution-evidence.py",
    "chaos validator": ROOT / "scripts/validate-memory-os-chaos-failure-drills-v2.py",
    "operability validator": ROOT / "scripts/validate-memory-os-operability.py",
}

EVIDENCE = (
    "historical-candidate/current mixed-version Apply failure recovery is executed locally: the historical process is terminated during an in-progress Apply, its uncommitted Apply/memory rows remain zero, and the current process retries the same operation to exactly one durable mutation with no in-progress residue or duplicate materialization; this remains candidate/local evidence, not an approved-release production-shaped failure drill"
)
REFS = (
    "contracts/operations/version-compatibility-execution-evidence.v1.json",
    "scripts/validate-memory-os-version-compatibility-execution-evidence.py",
    "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json",
)
OLD_BLOCKER = "mixed-version failure drill"
NEW_BLOCKER = (
    "approved predecessor/current production-shaped mixed-version failure and rollback drill with release-authority binding, connection drain, rollback timing, dependency recovery and independent review"
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


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def require_canonical_authorities() -> None:
    actual = {
        "execution": EXECUTION,
        "result": RESULT,
        "status": STATUS,
        "mixed-version validator": MIXED_VERSION_VALIDATOR,
        "execution validator": EXECUTION_VALIDATOR,
        "chaos validator": CHAOS_VALIDATOR,
        "operability validator": OPERABILITY_VALIDATOR,
    }
    for label, expected in CANONICAL_AUTHORITIES.items():
        path = actual[label]
        require(path == expected, f"{label} authority substitution")
        require(path.is_file(), f"{label} authority missing")
        require(path.resolve() == expected, f"{label} authority escapes canonical path")


def run_validator(path: Path) -> None:
    try:
        subprocess.run([sys.executable, str(path)], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        raise Fail(f"validator rejected authority: {path.relative_to(ROOT)}") from exc


def validate_source_authority() -> None:
    require_canonical_authorities()
    run_validator(MIXED_VERSION_VALIDATOR)
    run_validator(EXECUTION_VALIDATOR)


def validate_post_write_authority() -> None:
    run_validator(MIXED_VERSION_VALIDATOR)
    run_validator(EXECUTION_VALIDATOR)
    run_validator(CHAOS_VALIDATOR)
    run_validator(OPERABILITY_VALIDATOR)


def main() -> int:
    validate_source_authority()
    execution = load(EXECUTION)
    readiness = execution.get("readiness")
    boundary = execution.get("releaseAuthorityBoundary")
    require(isinstance(readiness, dict) and isinstance(boundary, dict), "compatibility execution authority missing")
    require(readiness.get("candidateApplyConcurrencyAndSIGKILLRecoveryProven") is True, "candidate Apply SIGKILL recovery is not proven")
    require(boundary.get("approvedReleaseCount") == 0, "approved release authority changed")
    require(boundary.get("releaseCompatibilityEvidence") is False, "candidate evidence cannot become release evidence")
    require(boundary.get("productionEvidence") is False, "candidate evidence cannot become production evidence")

    result = load(RESULT)
    assertions = result.get("assertions")
    environment = result.get("environment")
    require(isinstance(assertions, dict) and isinstance(environment, dict), "mixed-version Apply result missing")
    require(environment.get("historicalCandidateOnly") is True and environment.get("productionEvidence") is False, "candidate boundary drift")
    for field, expected in {
        "oldProcessKilledDuringInProgressApply": True,
        "terminatedAttemptApplyRows": 0,
        "terminatedAttemptMemoryRows": 0,
        "terminatedAttemptInProgressRows": 0,
        "currentRecoveryStatus": 200,
        "currentRecoveryReplayed": False,
        "currentRecoveryCreatedCount": 1,
        "oldProcessTerminationRecoveryPassed": True,
        "postTerminationRecoveryInProgressRows": 0,
        "noDuplicateMaterialization": True,
    }.items():
        require(assertions.get(field) == expected, f"mixed-version failure assertion drift: {field}")

    original_status = STATUS.read_bytes()
    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict), "OPS-P0-009 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-009 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-009 authority arrays missing")
    append_once(existing, EVIDENCE)
    normalized: list[Any] = []
    replaced = False
    for item in missing:
        if item == OLD_BLOCKER:
            if NEW_BLOCKER not in normalized:
                normalized.append(NEW_BLOCKER)
            replaced = True
        elif item not in normalized:
            normalized.append(item)
    if not replaced and NEW_BLOCKER not in normalized:
        normalized.append(NEW_BLOCKER)
    gate["missingEvidence"] = normalized
    for ref in REFS:
        append_once(refs, ref)

    try:
        STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        validate_post_write_authority()
    except Exception:
        STATUS.write_bytes(original_status)
        raise

    print("Memory OS chaos mixed-version overlay reconciliation PASS")
    print("candidate/local Apply SIGKILL recovery: proven")
    print("approved-release production-shaped mixed-version drill: false")
    print("OPS-P0-009: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"CHAOS MIXED-VERSION OVERLAY FAILED: {exc}")
        raise SystemExit(1)
