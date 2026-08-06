#!/usr/bin/env python3
"""Register exact-source candidate baseline compatibility evidence conservatively."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/mixed-version-candidate-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
BASELINE_SHA = "a1f39560468ebd5d39c4dd7a336140cb455cf2e8"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RESULT_REF = "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json"

NEW_EXISTING = (
    "historical candidate-baseline compatibility drill applying the current expanded PostgreSQL schema before executing the candidate baseline SQL and selected Go integration surfaces",
    "candidate execution preserves the current memory_os schema fingerprint and current SQL/Go verification passes independently on a separate database",
    "exact baseline/current SHAs are recorded while explicitly classifying the baseline as historical candidate, not approved release evidence",
)
NEW_MISSING = (
    "approved predecessor release artifact and successor release pair for binding compatibility evidence",
    "simultaneous old/current application traffic against the same production-shaped database",
    "rolling deployment order, connection drain, failure injection and application rollback rehearsal",
    "destructive contract-migration and downgrade compatibility proof",
    "production-shaped mixed-version review with zero unresolved Critical or High findings",
)
NEW_REFS = (
    "contracts/operations/mixed-version-candidate-contract.v1.json",
    RESULT_REF,
    "scripts/run-memory-os-mixed-version-candidate.sh",
    "scripts/validate-memory-os-mixed-version-candidate.py",
    "scripts/reconcile-memory-os-mixed-version-candidate.py",
    ".github/workflows/mixed-version-candidate.yml",
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


def main() -> int:
    result = load(RESULT_PATH)
    require(result.get("schemaVersion") ==
            "memory-os-mixed-version-candidate-results.v1",
            "mixed-version result schema drift")
    current_sha = result.get("currentCommitSha")
    require(isinstance(current_sha, str) and SHA_RE.fullmatch(current_sha) is not None,
            "mixed-version current SHA invalid")
    require(result.get("candidateBaselineCommitSha") == BASELINE_SHA,
            "mixed-version baseline SHA drift")
    require(is_ancestor(BASELINE_SHA, current_sha) and is_ancestor(current_sha, "HEAD"),
            "mixed-version source lineage is invalid")
    environment = result.get("environment")
    require(isinstance(environment, dict), "mixed-version environment missing")
    require(environment.get("productionEvidence") is False and
            environment.get("releaseCompatibilityEvidence") is False and
            environment.get("candidateBaselineOnly") is True and
            environment.get("containsSecrets") is False and
            environment.get("syntheticDataOnly") is True,
            "mixed-version evidence boundary drift")
    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "mixed-version scenario missing")
    require(scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "mixed-version candidate result is not PASS")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict) and assertions and
            all(value is True for value in assertions.values()),
            "mixed-version result contains a failed assertion")

    contract = load(CONTRACT_PATH)
    require(contract.get("candidateBaseline", {}).get("commitSha") == BASELINE_SHA,
            "candidate contract baseline drift")
    require(contract.get("evidenceBoundary", {}).get("productionReady") is False,
            "candidate contract cannot claim production readiness")
    readiness = contract.get("readiness")
    refs = contract.get("evidenceRefs")
    require(isinstance(readiness, dict), "candidate contract readiness missing")
    require(isinstance(refs, list), "candidate contract evidenceRefs must be a list")

    contract_changed = False
    for field in (
        "contractDefined", "runnerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        if readiness.get(field) is not True:
            readiness[field] = True
            contract_changed = True
    if readiness.get("exactSourcePassResultCommitted") is not True:
        readiness["exactSourcePassResultCommitted"] = True
        contract_changed = True
    for field in (
        "approvedReleaseBaselineAvailable", "simultaneousMixedTrafficExecuted",
        "rollingDeploymentFailureExecuted", "productionReady",
    ):
        require(readiness.get(field) is False,
                f"candidate evidence cannot promote readiness.{field}")
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"mixed-version evidence path missing: {ref}")
        if ref not in refs:
            refs.append(ref)
            contract_changed = True

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "candidate evidence cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict), "OPS-P0-008 missing")
    require(gate.get("status") == "PARTIAL", "OPS-P0-008 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    status_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-008 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-008 missingEvidence must be a list")
    if status_refs is None:
        status_refs = []
        gate["evidenceRefs"] = status_refs
    require(isinstance(status_refs, list), "OPS-P0-008 evidenceRefs must be a list")

    status_changed = False
    for item in NEW_EXISTING:
        if item not in existing:
            existing.append(item)
            status_changed = True
    for item in NEW_MISSING:
        if item not in missing:
            missing.append(item)
            status_changed = True
    for ref in NEW_REFS:
        if ref not in status_refs:
            status_refs.append(ref)
            status_changed = True

    lowered = [item.lower() for item in missing]
    for label, terms in {
        "approved predecessor release": ("approved", "predecessor", "release"),
        "simultaneous mixed traffic": ("simultaneous", "old/current", "traffic"),
        "rolling rollback": ("rolling", "rollback"),
        "contract migration": ("contract-migration", "downgrade"),
        "independent review": ("critical", "high"),
    }.items():
        require(any(all(term in item for term in terms) for item in lowered),
                f"required mixed-version gap disappeared: {label}")
    require(gate.get("status") == "PARTIAL", "candidate evidence changed readiness")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if contract_changed:
        write(CONTRACT_PATH, contract)
    if status_changed:
        status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
        write(STATUS_PATH, status)
    if not contract_changed and not status_changed:
        print("Mixed-version candidate authority already reconciled")
        return 0
    print("Registered historical candidate compatibility; OPS-P0-008 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"MIXED-VERSION CANDIDATE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
