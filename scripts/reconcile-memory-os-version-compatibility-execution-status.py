#!/usr/bin/env python3
"""Reconcile executed candidate/local compatibility evidence into OPS-P0-008 without changing release authority."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / "contracts/operations/version-compatibility-execution-evidence.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-version-compatibility-execution-evidence.py"
CANONICAL_VALIDATOR = ROOT / "scripts/validate-memory-os-version-compatibility.py"
FOUNDATION_VALIDATOR = ROOT / "scripts/validate-memory-os-version-compatibility-foundations.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

EXECUTION_EVIDENCE = (
    "supplemental executed-compatibility authority proves historical-candidate/current session interoperability, bidirectional persisted Apply replay, "
    "simultaneous idempotency-claim convergence and historical-process SIGKILL rollback/retry on the shared current schema, plus a local PostgreSQL "
    "16-to-17 logical forward restore preserving schema authority, RLS, active session resolution and deletion non-resurrection; all remain candidate/local-CI-only"
)

REFS = (
    "contracts/operations/version-compatibility-execution-evidence.v1.json",
    "scripts/validate-memory-os-version-compatibility-execution-evidence.py",
    "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/mixed-version-session-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/mixed-version-apply-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/postgresql-major-upgrade-results.sample.v1.json",
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


def append_once(items: list[Any], value: str) -> None:
    if value not in items:
        items.append(value)


def run_validator(path: Path, label: str) -> None:
    completed = subprocess.run(
        ["python", str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"{label} failed:\n{completed.stdout[-4000:]}{completed.stderr[-4000:]}",
    )


def run_post_write_validators() -> None:
    run_validator(CANONICAL_VALIDATOR, "canonical version compatibility validator")
    run_validator(FOUNDATION_VALIDATOR, "compatibility foundation validator")
    run_validator(OPERABILITY_VALIDATOR, "operability validator")


def commit_status_transaction(
    status: dict[str, Any],
    *,
    validator_runner: Callable[[], None] = run_post_write_validators,
) -> None:
    original = STATUS.read_bytes()
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        validator_runner()
    except Exception:
        STATUS.write_bytes(original)
        raise


def reconcile_execution_projection(status: dict[str, Any]) -> dict[str, Any]:
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict), "OPS-P0-008 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True,
            "OPS-P0-008 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list), "OPS-P0-008 existingEvidence must be list")
    require(isinstance(refs, list), "OPS-P0-008 evidenceRefs must be list")
    require(isinstance(missing, list) and all(isinstance(item, str) and item.strip() for item in missing),
            "OPS-P0-008 missingEvidence must remain a non-empty string list")
    require(missing, "OPS-P0-008 production blockers may not be cleared by candidate/local evidence")

    # Candidate/local execution evidence is supplemental only. It may add its own
    # evidence/ref classification, but it does not own production blockers. The
    # canonical foundation/release authorities evolve missingEvidence separately.
    # Preserving the existing list prevents this weaker projection from
    # reintroducing stale blockers or erasing stronger current authority.
    append_once(existing, EXECUTION_EVIDENCE)
    for ref in REFS:
        require((ROOT / ref).is_file(), f"evidence ref missing: {ref}")
        append_once(refs, ref)
    return status


def main() -> int:
    run_validator(VALIDATOR, "version compatibility execution evidence validator")
    execution = load(EXECUTION)
    release = execution.get("releaseAuthorityBoundary", {})
    readiness = execution.get("readiness", {})
    require(release.get("approvedReleaseCount") == 0, "approved release count must remain zero")
    require(release.get("approvedRollbackPairCount") == 0, "approved rollback pair count must remain zero")
    require(release.get("reviewedParserArtifactCount") == 0, "reviewed parser artifact count must remain zero")
    require(release.get("canonicalReleaseMatrixChanged") is False, "canonical release matrix may not change")
    require(release.get("releaseCompatibilityEvidence") is False, "candidate evidence may not become release evidence")
    require(release.get("productionEvidence") is False, "candidate evidence may not become production evidence")
    require(release.get("productionReady") is False and release.get("productionDecision") == "NO_GO", "release boundary drift")
    for key in (
        "candidateOnlyMixedVersionExecutionProven",
        "candidateApplyConcurrencyAndSIGKILLRecoveryProven",
        "postgresql17LogicalForwardExecutionProven",
    ):
        require(readiness.get(key) is True, f"execution proof missing: {key}")
    for key in (
        "approvedReleasePairAvailable",
        "productionRollingDeploymentProven",
        "clientServerSkewProven",
        "reviewedParserArtifactAvailable",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(key) is False, f"unsafe compatibility promotion: {key}")

    status = reconcile_execution_projection(load(STATUS))
    commit_status_transaction(status)
    print("Memory OS version compatibility execution status reconciliation PASS")
    print("candidate/local execution evidence: classified")
    print("production blockers: preserved from current canonical authority")
    print("approved release pair: false")
    print("canonical release matrix changed: false")
    print("OPS-P0-008: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"VERSION COMPATIBILITY EXECUTION STATUS FAILED: {exc}")
        raise SystemExit(1)
