#!/usr/bin/env python3
"""Reconcile LOCAL_LONG_SOAK implementation/run state without promoting production soak or leak proof."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RESULT_DIR = ROOT / "docs/fixtures/memory-os-operability"
RESULT_GLOB = "sustained-local-soak-results.run-*.v1.json"
AGGREGATE_PATH = RESULT_DIR / "sustained-local-soak-results.aggregate.v1.json"
AGGREGATE_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-aggregate.py"

FOUNDATION_REFS = (
    "contracts/operations/sustained-local-soak-contract.v1.json",
    "services/import-api/internal/httpserver/sustained_local_soak_test.go",
    "scripts/validate-memory-os-sustained-local-soak.py",
    "scripts/validate-memory-os-sustained-local-soak-result.py",
    "scripts/validate-memory-os-sustained-local-soak-aggregate.py",
    "scripts/update-memory-os-sustained-local-soak-aggregate.py",
    "scripts/reconcile-memory-os-sustained-local-soak-status.py",
    ".github/workflows/sustained-local-soak.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path.relative_to(ROOT)}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def append_unique(values: list[Any], value: Any) -> None:
    if value not in values:
        values.append(value)


def find_by_id(values: list[Any], identifier: str) -> dict[str, Any]:
    for value in values:
        if isinstance(value, dict) and value.get("id") == identifier:
            return value
    raise Fail(f"missing operability area: {identifier}")


def find_scenario(values: list[Any], scenario_id: str) -> dict[str, Any] | None:
    for value in values:
        if isinstance(value, dict) and value.get("scenarioId") == scenario_id:
            return value
    return None


def main() -> int:
    contract = load(CONTRACT_PATH)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "long-soak readiness missing")

    artifact_flags = {
        "runnerImplemented": contract.get("runner"),
        "validatorImplemented": contract.get("validator"),
        "resultValidatorImplemented": contract.get("resultValidator"),
        "aggregateValidatorImplemented": contract.get("aggregateValidator"),
        "automaticWorkflowImplemented": contract.get("workflow"),
    }
    for flag, ref in artifact_flags.items():
        require(isinstance(ref, str) and ref, f"missing artifact ref for {flag}")
        readiness[flag] = (ROOT / ref).is_file()
    require(all(readiness[flag] for flag in artifact_flags), "cannot reconcile incomplete LOCAL_LONG_SOAK foundation")

    paths = sorted(RESULT_DIR.glob(RESULT_GLOB))
    run_count = len(paths)
    minimum_runs = int(contract.get("minimumIndependentRuns", 2))
    aggregate: dict[str, Any] | None = None
    if run_count:
        require(AGGREGATE_PATH.is_file(), "run documents exist without aggregate")
        completed = subprocess.run(
            [sys.executable, str(AGGREGATE_VALIDATOR)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        require(completed.returncode == 0, f"aggregate validator failed:\n{completed.stdout[-4000:]}{completed.stderr[-4000:]}")
        aggregate = load(AGGREGATE_PATH)
    else:
        require(not AGGREGATE_PATH.exists(), "aggregate exists without run documents")

    readiness["contractDefined"] = True
    readiness["firstLongRunCommitted"] = run_count >= 1
    readiness["secondIndependentLongRunCommitted"] = run_count >= minimum_runs
    readiness["allRequiredCoverageExecuted"] = run_count >= 1
    readiness["trendReviewCompleted"] = bool(aggregate and aggregate.get("trendReviewCompleted") is True)
    readiness["localSustainedSoakEvidence"] = bool(aggregate and aggregate.get("localSustainedSoakEvidence") is True)
    for key in (
        "productionSustainedSoakEvidence",
        "leakProofAvailable",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "independentReviewCompleted",
        "productionReady",
    ):
        readiness[key] = False
    if readiness["localSustainedSoakEvidence"]:
        require(run_count >= minimum_runs, "local sustained-soak evidence requires repeated runs")
        require(readiness["trendReviewCompleted"], "local sustained-soak evidence requires trend review")

    load_contract = load(LOAD_PATH)
    load_readiness = load_contract.get("readiness")
    evidence_refs = load_contract.get("evidenceRefs")
    deferred = load_contract.get("deferredScenarios")
    require(isinstance(load_readiness, dict) and isinstance(evidence_refs, list) and isinstance(deferred, list), "load contract structure invalid")
    load_readiness["localLongSoakFoundationImplemented"] = True
    load_readiness["localLongSoakRunCount"] = run_count
    load_readiness["localSustainedSoakEvidence"] = readiness["localSustainedSoakEvidence"]
    require(load_readiness.get("sustainedSoakEvidence") is False, "LOCAL_LONG_SOAK cannot promote generic/production-shaped sustainedSoakEvidence")
    require(load_readiness.get("productionEquivalentDependencies") is False, "LOCAL_LONG_SOAK cannot promote production-equivalent dependencies")
    for ref in FOUNDATION_REFS:
        append_unique(evidence_refs, ref)
    if run_count:
        append_unique(evidence_refs, "docs/fixtures/memory-os-operability/sustained-local-soak-results.aggregate.v1.json")
        for path in paths:
            append_unique(evidence_refs, str(path.relative_to(ROOT)))

    for deferred_id in ("soak-memory-leak", "soak"):
        item = find_scenario(deferred, deferred_id)
        require(item is not None, f"missing deferred scenario {deferred_id}")
        if run_count == 0:
            item["reason"] = (
                "LOCAL_LONG_SOAK contract, multi-surface runner and fail-closed validators exist, but no 60-minute-or-longer exact-source run has been committed; "
                "production-shaped sustained soak and leak proof remain unexecuted"
            )
        elif run_count < minimum_runs:
            item["reason"] = (
                "one exact-source LOCAL_LONG_SOAK run is committed, but a second independent 60-minute-or-longer run and cross-run trend review remain required; "
                "leak proof and production-shaped sustained soak remain unproven"
            )
        elif not readiness["trendReviewCompleted"]:
            item["reason"] = (
                "at least two exact-source LOCAL_LONG_SOAK runs are committed, but cross-run RSS/heap/goroutine/latency/error/DB/queue/deletion trend review remains pending; "
                "leak proof and production-shaped sustained soak remain unproven"
            )
        else:
            item["reason"] = (
                "repeated LOCAL_LONG_SOAK execution and descriptive trend review exist, but this local evidence is not leak proof and is not production-shaped sustained-soak evidence"
            )
        item["requiredDependencyMode"] = "LOCAL_POSTGRES_MINIO"

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO", "refusing to reconcile local soak into non-NO_GO production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "operability areas missing")
    load_status = find_by_id(areas, "OPS-P0-006")
    require(load_status.get("status") == "PARTIAL", "LOCAL_LONG_SOAK must not promote OPS-P0-006")
    existing = load_status.get("existingEvidence")
    missing = load_status.get("missingEvidence")
    refs = load_status.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-006 evidence structure invalid")

    append_unique(
        existing,
        "fail-closed LOCAL_LONG_SOAK foundation requires a long-lived API process plus PostgreSQL, MinIO, parser recovery, scan-queue observation and deletion-worker convergence across 12 windows, and physically refuses to publish result evidence for runs configured below 3600 seconds",
    )
    if run_count >= 1:
        append_unique(existing, f"{run_count} exact-source LOCAL_LONG_SOAK run document(s) satisfy the per-run validator; production evidence and leak proof remain false")
    if readiness["localSustainedSoakEvidence"]:
        append_unique(existing, "repeated LOCAL_LONG_SOAK runs plus cross-run trend review are registered as local-only sustained-soak evidence; this is not leak proof or production-shaped evidence")

    local_prefixes = (
        "two independent 60-minute-or-longer LOCAL_LONG_SOAK runs",
        "a second independent 60-minute-or-longer LOCAL_LONG_SOAK run",
        "cross-run LOCAL_LONG_SOAK trend review",
    )
    missing = [item for item in missing if not (isinstance(item, str) and item.startswith(local_prefixes))]
    if run_count == 0:
        missing.append("two independent 60-minute-or-longer LOCAL_LONG_SOAK runs plus cross-run RSS/heap/goroutine/latency/error/DB/queue/deletion trend review")
    elif run_count < minimum_runs:
        missing.append("a second independent 60-minute-or-longer LOCAL_LONG_SOAK run plus cross-run RSS/heap/goroutine/latency/error/DB/queue/deletion trend review")
    elif not readiness["trendReviewCompleted"]:
        missing.append("cross-run LOCAL_LONG_SOAK trend review before local-only sustained-soak evidence can be registered")
    load_status["missingEvidence"] = missing
    for ref in FOUNDATION_REFS:
        append_unique(refs, ref)
    if run_count:
        append_unique(refs, "docs/fixtures/memory-os-operability/sustained-local-soak-results.aggregate.v1.json")
        for path in paths:
            append_unique(refs, str(path.relative_to(ROOT)))

    require(status.get("productionDecision") == "NO_GO", "production decision drift")
    require(load_status.get("status") == "PARTIAL", "OPS-P0-006 status drift")
    require(load_readiness.get("sustainedSoakEvidence") is False, "generic sustainedSoakEvidence drift")

    write(CONTRACT_PATH, contract)
    write(LOAD_PATH, load_contract)
    write(STATUS_PATH, status)
    print("Memory OS sustained local soak status reconciled")
    print(f"committed LOCAL_LONG_SOAK runs: {run_count}")
    print(f"trend review completed: {str(readiness['trendReviewCompleted']).lower()}")
    print(f"local sustained soak evidence: {str(readiness['localSustainedSoakEvidence']).lower()}")
    print("production sustained soak evidence: false")
    print("leak proof: false")
    print("OPS-P0-006: PARTIAL")
    print("Production: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"SUSTAINED LOCAL SOAK RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
