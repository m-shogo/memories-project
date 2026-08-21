#!/usr/bin/env python3
"""Reconcile LOCAL_LONG_SOAK implementation/run state without promoting production soak or leak proof."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
CANONICAL_LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_RESULT_DIR = ROOT / "docs/fixtures/memory-os-operability"
CANONICAL_AGGREGATE_PATH = CANONICAL_RESULT_DIR / "sustained-local-soak-results.aggregate.v1.json"
CANONICAL_REVIEW_PATH = CANONICAL_RESULT_DIR / "sustained-local-soak-trend-review.v1.json"
CANONICAL_AGGREGATE_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak-aggregate.py"
CANONICAL_INDEPENDENT_REVIEW_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-soak-independent-review.py"
CANONICAL_SOAK_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak.py"
CANONICAL_LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"

CONTRACT_PATH = CANONICAL_CONTRACT_PATH
LOAD_PATH = CANONICAL_LOAD_PATH
STATUS_PATH = CANONICAL_STATUS_PATH
RESULT_DIR = CANONICAL_RESULT_DIR
RESULT_GLOB = "sustained-local-soak-results.run-*.v1.json"
AGGREGATE_PATH = CANONICAL_AGGREGATE_PATH
REVIEW_PATH = CANONICAL_REVIEW_PATH
AGGREGATE_VALIDATOR = CANONICAL_AGGREGATE_VALIDATOR
INDEPENDENT_REVIEW_VALIDATOR = CANONICAL_INDEPENDENT_REVIEW_VALIDATOR
SOAK_VALIDATOR = CANONICAL_SOAK_VALIDATOR
LOAD_VALIDATOR = CANONICAL_LOAD_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR

FOUNDATION_REFS = (
    "contracts/operations/sustained-local-soak-contract.v1.json",
    "contracts/operations/sustained-soak-independent-review-contract.v1.json",
    "contracts/operations/sustained-soak-independent-review-registry.v1.json",
    "services/import-api/internal/httpserver/sustained_local_soak_test.go",
    "scripts/validate-memory-os-sustained-local-soak.py",
    "scripts/register-memory-os-sustained-soak-independent-review.py",
    "scripts/validate-memory-os-sustained-soak-independent-review.py",
    "scripts/validate-memory-os-sustained-soak-independent-review-negative.py",
    "scripts/validate-memory-os-sustained-local-soak-result.py",
    "scripts/validate-memory-os-sustained-local-soak-aggregate.py",
    "scripts/update-memory-os-sustained-local-soak-aggregate.py",
    "scripts/review-memory-os-sustained-local-soak-trends.py",
    "scripts/validate-memory-os-sustained-local-soak-trend-review.py",
    "scripts/reconcile-memory-os-sustained-local-soak-status.py",
    ".github/workflows/sustained-local-soak.yml",
    ".github/workflows/reconcile-sustained-local-soak-authority.yml",
)
REPEATED_SOAK_STALE_GAPS = {
    "sustained soak with RSS/heap/goroutine-slope evidence (SOAK PROOF INSUFFICIENT)",
    "60-minute-or-longer repeated soak over PostgreSQL, object storage, parser, queue, deletion and authentication paths with RSS/heap/goroutine slope review and independently approved leak/stability criteria",
}
REMAINING_REVIEW_GAP = (
    "independently approved leak/stability criteria and review over the repeated LOCAL_LONG_SOAK trends; descriptive cross-run review is complete but leakProof remains false"
)
PRODUCTION_SOAK_GAP = (
    "production-shaped sustained soak against registered production-equivalent dependencies with runtime topology, TLS, scoped credentials, dependency latency/failure behavior and independent review; LOCAL_LONG_SOAK remains local-only evidence"
)
STALE_REVIEW_AUTHORITY_EVIDENCE = (
    "append-only independent sustained-soak review authority is implemented for future human-approved leak/stability criteria and distinct independent review; automatic threshold selection, leak proof, capacity-boundary promotion and production promotion remain forbidden, and the registry is currently empty"
)
REVIEW_AUTHORITY_EVIDENCE = (
    "append-only independent sustained-soak review authority accepts only externally supplied human-approved leak/stability criteria and distinct independent review; automatic threshold selection, leak proof, capacity-boundary promotion and production promotion remain forbidden"
)
STALE_LOCAL_REVIEW_EVIDENCE = (
    "repeated LOCAL_LONG_SOAK runs plus cross-run trend review are registered as local-only sustained-soak evidence; this is not leak proof or production-shaped evidence"
)
CANONICAL_LOCAL_REVIEW_EVIDENCE = (
    "repeated LOCAL_LONG_SOAK runs plus cross-run descriptive trend review are registered as local-only sustained-soak evidence; this is not leak proof or production-shaped evidence"
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_file(path: Path, expected: Path, label: str) -> None:
    require(path == expected, f"{label} authority substitution")
    require(path.is_file() and not path.is_symlink(), f"{label} canonical file missing or symlinked")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise Fail(f"{label} canonical authority cannot be resolved") from exc
    require(resolved == expected, f"{label} canonical authority escaped repository path")


def require_exact_optional_file(path: Path, expected: Path, label: str) -> None:
    require(path == expected, f"{label} authority substitution")
    require(path.parent.resolve(strict=True) == expected.parent, f"{label} canonical parent escaped repository path")
    if path.exists():
        require(path.is_file() and not path.is_symlink(), f"{label} canonical file is not a regular file")
        require(path.resolve(strict=True) == expected, f"{label} canonical authority escaped repository path")


def enforce_runtime_authorities() -> None:
    require(RESULT_DIR == CANONICAL_RESULT_DIR, "result directory authority substitution")
    require(RESULT_DIR.is_dir() and not RESULT_DIR.is_symlink(), "canonical result directory missing or symlinked")
    require(RESULT_DIR.resolve(strict=True) == CANONICAL_RESULT_DIR, "canonical result directory escaped repository path")
    for path, expected, label in (
        (CONTRACT_PATH, CANONICAL_CONTRACT_PATH, "sustained soak contract"),
        (LOAD_PATH, CANONICAL_LOAD_PATH, "load contract"),
        (STATUS_PATH, CANONICAL_STATUS_PATH, "production status"),
        (AGGREGATE_VALIDATOR, CANONICAL_AGGREGATE_VALIDATOR, "aggregate validator"),
        (INDEPENDENT_REVIEW_VALIDATOR, CANONICAL_INDEPENDENT_REVIEW_VALIDATOR, "independent review validator"),
        (SOAK_VALIDATOR, CANONICAL_SOAK_VALIDATOR, "sustained soak validator"),
        (LOAD_VALIDATOR, CANONICAL_LOAD_VALIDATOR, "load validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
    ):
        require_exact_file(path, expected, label)
    require_exact_optional_file(AGGREGATE_PATH, CANONICAL_AGGREGATE_PATH, "sustained soak aggregate")
    require_exact_optional_file(REVIEW_PATH, CANONICAL_REVIEW_PATH, "sustained soak trend review")


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


def run_validator(path: Path, label: str, *args: str) -> None:
    completed = subprocess.run(
        [sys.executable, str(path), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    require(completed.returncode == 0, f"{label} failed:\n{completed.stdout[-4000:]}{completed.stderr[-4000:]}")


def write_and_validate_transactionally(
    contract: dict[str, Any], load_contract: dict[str, Any], status: dict[str, Any]
) -> None:
    paths = (CONTRACT_PATH, LOAD_PATH, STATUS_PATH)
    original_bytes = {path: path.read_bytes() for path in paths}
    try:
        write(CONTRACT_PATH, contract)
        write(LOAD_PATH, load_contract)
        write(STATUS_PATH, status)
        run_validator(SOAK_VALIDATOR, "post-write sustained local soak validator")
        run_validator(LOAD_VALIDATOR, "post-write load validator")
        run_validator(OPERABILITY_VALIDATOR, "post-write operability validator")
    except Exception:
        for path in paths:
            path.write_bytes(original_bytes[path])
        raise


def main() -> int:
    enforce_runtime_authorities()
    run_validator(INDEPENDENT_REVIEW_VALIDATOR, "sustained-soak independent review authority validator")

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
        run_validator(AGGREGATE_VALIDATOR, "aggregate validator")
        aggregate = load(AGGREGATE_PATH)
    else:
        require(not AGGREGATE_PATH.exists(), "aggregate exists without run documents")
        require(not REVIEW_PATH.exists(), "trend review exists without run documents")

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
        require(REVIEW_PATH.is_file(), "local sustained-soak evidence requires canonical trend-review file")

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
    if readiness["trendReviewCompleted"]:
        append_unique(evidence_refs, str(REVIEW_PATH.relative_to(ROOT)))

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
                "repeated LOCAL_LONG_SOAK execution and descriptive trend review exist, but this local evidence is not leak proof and is not production-shaped sustained-soak evidence; independent leak/stability criteria remain required"
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

    existing = [
        item for item in existing
        if item not in {
            STALE_REVIEW_AUTHORITY_EVIDENCE,
            STALE_LOCAL_REVIEW_EVIDENCE,
        }
    ]
    load_status["existingEvidence"] = existing
    append_unique(
        existing,
        "fail-closed LOCAL_LONG_SOAK foundation requires a long-lived API process plus PostgreSQL, MinIO, parser recovery, scan-queue observation and deletion-worker convergence across 12 windows, and physically refuses to publish result evidence for runs configured below 3600 seconds",
    )
    append_unique(existing, REVIEW_AUTHORITY_EVIDENCE)
    if run_count >= 1:
        append_unique(existing, f"{run_count} exact-source LOCAL_LONG_SOAK run document(s) satisfy the per-run validator; production evidence and leak proof remain false")
    if readiness["localSustainedSoakEvidence"]:
        append_unique(existing, CANONICAL_LOCAL_REVIEW_EVIDENCE)

    local_prefixes = (
        "two independent 60-minute-or-longer LOCAL_LONG_SOAK runs",
        "a second independent 60-minute-or-longer LOCAL_LONG_SOAK run",
        "cross-run LOCAL_LONG_SOAK trend review",
    )
    missing = [
        item for item in missing
        if not (
            isinstance(item, str)
            and (
                item.startswith(local_prefixes)
                or item in REPEATED_SOAK_STALE_GAPS
                or item == REMAINING_REVIEW_GAP
                or item == PRODUCTION_SOAK_GAP
            )
        )
    ]
    if run_count == 0:
        missing.append("two independent 60-minute-or-longer LOCAL_LONG_SOAK runs plus cross-run RSS/heap/goroutine/latency/error/DB/queue/deletion trend review")
    elif run_count < minimum_runs:
        missing.append("a second independent 60-minute-or-longer LOCAL_LONG_SOAK run plus cross-run RSS/heap/goroutine/latency/error/DB/queue/deletion trend review")
    elif not readiness["trendReviewCompleted"]:
        missing.append("cross-run LOCAL_LONG_SOAK trend review before local-only sustained-soak evidence can be registered")
    else:
        missing.append(REMAINING_REVIEW_GAP)
        missing.append(PRODUCTION_SOAK_GAP)
    load_status["missingEvidence"] = missing
    for ref in FOUNDATION_REFS:
        append_unique(refs, ref)
    if run_count:
        append_unique(refs, "docs/fixtures/memory-os-operability/sustained-local-soak-results.aggregate.v1.json")
        for path in paths:
            append_unique(refs, str(path.relative_to(ROOT)))
    if readiness["trendReviewCompleted"]:
        append_unique(refs, str(REVIEW_PATH.relative_to(ROOT)))

    if readiness["localSustainedSoakEvidence"]:
        for stale in REPEATED_SOAK_STALE_GAPS:
            require(stale not in load_status["missingEvidence"],
                    f"completed repeated-soak gap remained stale: {stale}")
        require(REMAINING_REVIEW_GAP in load_status["missingEvidence"],
                "independent leak/stability review gap must remain explicit")
        require(PRODUCTION_SOAK_GAP in load_status["missingEvidence"],
                "production-shaped sustained soak gap must remain explicit")
        require(STALE_REVIEW_AUTHORITY_EVIDENCE not in existing,
                "dynamic empty-registry statement must not remain in existing evidence")
        require(STALE_LOCAL_REVIEW_EVIDENCE not in existing,
                "duplicate pre-descriptive trend-review statement must not remain")
        require(REVIEW_AUTHORITY_EVIDENCE in existing,
                "stable independent-review authority evidence missing")
        require(CANONICAL_LOCAL_REVIEW_EVIDENCE in existing,
                "canonical descriptive trend-review evidence missing")

    require(status.get("productionDecision") == "NO_GO", "production decision drift")
    require(load_status.get("status") == "PARTIAL", "OPS-P0-006 status drift")
    require(load_readiness.get("sustainedSoakEvidence") is False, "generic sustainedSoakEvidence drift")

    write_and_validate_transactionally(contract, load_contract, status)
    print("Memory OS sustained local soak status reconciled")
    print(f"committed LOCAL_LONG_SOAK runs: {run_count}")
    print(f"trend review completed: {str(readiness['trendReviewCompleted']).lower()}")
    print(f"local sustained soak evidence: {str(readiness['localSustainedSoakEvidence']).lower()}")
    print("leak proof: false")
    print("independent leak/stability review: required")
    print("production-shaped sustained soak: required")
    print("production sustained soak evidence: false")
    print("OPS-P0-006: PARTIAL")
    print("Production: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"SUSTAINED LOCAL SOAK RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
