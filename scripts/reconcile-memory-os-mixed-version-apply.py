#!/usr/bin/env python3
"""Register mixed-version Apply evidence without promoting release readiness."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/mixed-version-apply-contract.v1.json"
CANONICAL_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_APPLY_VALIDATOR = ROOT / "scripts/validate-memory-os-mixed-version-apply.py"
CANONICAL_VERSION_VALIDATOR = ROOT / "scripts/validate-memory-os-version-compatibility.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
STATUS_PATH = CANONICAL_STATUS_PATH
APPLY_VALIDATOR = CANONICAL_APPLY_VALIDATOR
VERSION_VALIDATOR = CANONICAL_VERSION_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

EXISTING = (
    "pinned historical-candidate and current Import API processes mutate and replay persisted Apply idempotency claims on one current expanded PostgreSQL schema",
    "historical-candidate Apply followed by current replay returns the original Apply ID without duplicate materialization",
    "current Apply followed by historical-candidate replay returns the original Apply ID without duplicate materialization",
    "cross-Preview idempotency-key reuse is rejected while exactly two applied claims and two memory items remain with zero in-progress claims",
)
RACE_EXISTING = (
    "simultaneous historical-candidate and current Apply requests using one Preview and idempotency key converge on one Apply ID with exactly one new application and one replay",
    "concurrent old/current idempotency claim race leaves one durable claim, one materialized memory item and zero in-progress residue for the raced Preview",
)
TERMINATION_EXISTING = (
    "historical-candidate process is SIGKILLed while its Apply transaction is blocked before memory materialization; PostgreSQL rolls back the uncommitted claim and memory mutation completely",
    "current process safely retries the same Preview and idempotency key after historical-process death, creates exactly one durable claim and memory item, and leaves zero in-progress residue",
)
OBSOLETE_GAPS = (
    "persisted-state compatibility fixtures across releases",
    "simultaneous old/current mutation traffic and concurrent idempotency-claim race coverage on one production-shaped database",
    "process termination during in-progress Apply with deterministic recovery or safe blocking evidence",
)
PRECISE_GAPS = (
    "persisted Preview and Apply compatibility fixtures across an approved predecessor and successor release pair",
    "simultaneous approved-release old/current mutation traffic and concurrent idempotency-claim race coverage on one production-shaped database",
    "approved-release process termination during in-progress Apply with production-shaped connection-pool cleanup and deterministic recovery evidence",
    "rolling deployment, traffic drain and application rollback rehearsal using rollback-eligible approved release artifacts",
)
REFS = (
    "contracts/operations/mixed-version-apply-contract.v1.json",
    "services/import-api/cmd/memory-os-mixed-version-fixture/main.go",
    "scripts/run-memory-os-mixed-version-apply-drill.sh",
    "scripts/validate-memory-os-mixed-version-apply.py",
    "scripts/reconcile-memory-os-mixed-version-apply.py",
    "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json",
    ".github/workflows/mixed-version-apply.yml",
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
        (CONTRACT_PATH, CANONICAL_CONTRACT_PATH, "mixed-version Apply contract"),
        (RESULT_PATH, CANONICAL_RESULT_PATH, "mixed-version Apply result"),
        (STATUS_PATH, CANONICAL_STATUS_PATH, "production status"),
        (APPLY_VALIDATOR, CANONICAL_APPLY_VALIDATOR, "mixed-version Apply validator"),
        (VERSION_VALIDATOR, CANONICAL_VERSION_VALIDATOR, "version compatibility validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
    ):
        require_exact_authority(path, canonical, label)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def is_ancestor(base: str, head: str) -> bool:
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", base, head],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


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


def validate_authority_chain(current_sha: str, *, require_reconciled: bool) -> None:
    args = ["--expected-commit-sha", current_sha]
    if require_reconciled:
        args.append("--require-reconciled")
    run_validator(APPLY_VALIDATOR, *args)
    run_validator(VERSION_VALIDATOR)
    run_validator(OPERABILITY_VALIDATOR)


def main() -> int:
    enforce_runtime_authorities()
    result = load(RESULT_PATH)
    current_sha = result.get("currentCommitSha")
    old_sha = result.get("oldBackendCommitSha")
    require(isinstance(current_sha, str) and SHA_RE.fullmatch(current_sha) is not None,
            "current result SHA invalid")
    require(isinstance(old_sha, str) and SHA_RE.fullmatch(old_sha) is not None,
            "old result SHA invalid")
    require(is_ancestor(old_sha, current_sha) and is_ancestor(current_sha, "HEAD"),
            "mixed-version Apply source lineage invalid")

    # The canonical validator owns exact-source result, contract, privacy and
    # historical-candidate semantics. Aggregate validators gate any projection.
    validate_authority_chain(current_sha, require_reconciled=False)

    contract = load(CONTRACT_PATH)
    assertions = result.get("assertions")
    require(isinstance(assertions, dict), "mixed-version Apply assertions missing")
    race_passed = assertions.get("concurrentOldCurrentClaimRacePassed") is True
    termination_passed = assertions.get("oldProcessTerminationRecoveryPassed") is True
    readiness = contract.get("readiness")
    refs = contract.get("evidenceRefs")
    require(isinstance(readiness, dict), "contract readiness missing")
    require(isinstance(refs, list), "contract evidenceRefs must be a list")
    for field in ("approvedReleasePairAvailable", "rollbackRehearsalExecuted", "productionReady"):
        require(readiness.get(field) is False, f"historical-candidate evidence cannot promote {field}")

    contract_changed = False
    if readiness.get("exactSourcePassResultCommitted") is not True:
        readiness["exactSourcePassResultCommitted"] = True
        contract_changed = True
    if race_passed and readiness.get("concurrentClaimRaceExecuted") is not True:
        readiness["concurrentClaimRaceExecuted"] = True
        contract_changed = True
    if not race_passed:
        require(readiness.get("concurrentClaimRaceExecuted") is False,
                "contract claims concurrent race evidence absent from result")
    if termination_passed and readiness.get("inProgressProcessTerminationExecuted") is not True:
        readiness["inProgressProcessTerminationExecuted"] = True
        contract_changed = True
    if not termination_passed:
        require(readiness.get("inProgressProcessTerminationExecuted") in (None, False),
                "contract claims process termination evidence absent from result")
    for ref in REFS:
        require((ROOT / ref).is_file(), f"mixed-version Apply evidence missing: {ref}")
        contract_changed = append_once(refs, ref) or contract_changed

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO", "mixed-version Apply evidence cannot change production decision")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL", "OPS-P0-008 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    status_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-008 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-008 missingEvidence must be a list")
    require(isinstance(status_refs, list), "OPS-P0-008 evidenceRefs must be a list")

    status_changed = False
    for item in EXISTING:
        status_changed = append_once(existing, item) or status_changed
    if race_passed:
        for item in RACE_EXISTING:
            status_changed = append_once(existing, item) or status_changed
    if termination_passed:
        for item in TERMINATION_EXISTING:
            status_changed = append_once(existing, item) or status_changed
    for item in OBSOLETE_GAPS:
        if item in missing:
            missing.remove(item)
            status_changed = True
    for item in PRECISE_GAPS:
        status_changed = append_once(missing, item) or status_changed
    for ref in REFS:
        status_changed = append_once(status_refs, ref) or status_changed

    lowered = [str(item).lower() for item in missing]
    for label, terms in {
        "approved release pair": ("approved", "predecessor", "successor"),
        "approved concurrent mixed mutation": ("approved-release", "concurrent", "idempotency"),
        "approved in-progress termination": ("approved-release", "termination", "in-progress"),
        "rolling rollback": ("rolling", "rollback", "rollback-eligible"),
    }.items():
        require(any(all(term in item for term in terms) for item in lowered), f"required compatibility gap disappeared: {label}")
    require(gate.get("status") == "PARTIAL" and status.get("productionDecision") == "NO_GO",
            "mixed-version Apply evidence changed readiness")

    original_contract_bytes = CONTRACT_PATH.read_bytes()
    original_status_bytes = STATUS_PATH.read_bytes()
    if not contract_changed and not status_changed:
        validate_authority_chain(current_sha, require_reconciled=True)
        print("Mixed-version Apply authority already reconciled")
        return 0

    if contract_changed:
        write(CONTRACT_PATH, contract)
    if status_changed:
        status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
        write(STATUS_PATH, status)
    try:
        validate_authority_chain(current_sha, require_reconciled=True)
    except Exception:
        CONTRACT_PATH.write_bytes(original_contract_bytes)
        STATUS_PATH.write_bytes(original_status_bytes)
        raise

    print("Registered mixed-version Apply evidence; OPS-P0-008 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"MIXED-VERSION APPLY RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
