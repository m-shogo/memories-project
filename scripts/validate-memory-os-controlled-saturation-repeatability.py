#!/usr/bin/env python3
"""Validate bounded local saturation-repeatability evidence without threshold promotion."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/controlled-saturation-repeatability-contract.v1.json"
RESULT = ROOT / "docs/fixtures/memory-os-operability/controlled-saturation-repeatability-results.v1.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
STEPS = [4, 8, 16, 24, 32, 48]


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def safe_repo_ref(value: Any, field: str) -> Path:
    require(isinstance(value, str) and value, f"{field} missing")
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts, f"{field} must be repository-relative")
    path = ROOT / relative
    require(path.is_file(), f"{field} artifact missing: {value}")
    return path


def main() -> int:
    contract = load(CONTRACT)
    result = load(RESULT)
    require(contract.get("schemaVersion") == "memory-os-controlled-saturation-repeatability.v1", "contract schema drift")
    source_ramp_path = safe_repo_ref(contract.get("sourceRampContract"), "sourceRampContract")
    source_ramp = load(source_ramp_path)
    require(source_ramp.get("schemaVersion") == "memory-os-controlled-saturation-ramp.v1", "source ramp schema drift")
    require(contract.get("sourceScenarioId") == source_ramp.get("scenarioId"), "source ramp scenario binding drift")
    require(contract.get("dependencyMode") == source_ramp.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "source ramp dependency mode drift")
    require(contract.get("requiredIndependentRuns") == 2, "required run count drift")
    require(contract.get("concurrencySteps") == source_ramp.get("concurrencySteps") == STEPS, "source ramp concurrency binding drift")
    require(contract.get("requestsPerStep") == source_ramp.get("requestsPerStep") == 64, "source ramp request-count binding drift")
    source_boundary = source_ramp.get("evidenceBoundary")
    require(isinstance(source_boundary, dict), "source ramp evidence boundary missing")
    for key in ("productionTraffic", "productionCredentials", "productionEvidence", "productionEquivalentDependencies", "capacityBoundaryEstablished", "operationalThresholdApproved", "independentReviewCompleted", "productionReady"):
        require(source_boundary.get(key) is False, f"source ramp cannot enable {key}")

    signal = contract.get("signalPolicy")
    require(isinstance(signal, dict), "signal policy missing")
    require(signal.get("maximumThroughputGainFromPreviousStep") == 0.05, "throughput knee rule drift")
    require(signal.get("minimumP95LatencyRatioFromPreviousStep") == 1.25, "latency knee rule drift")
    require(signal.get("repeatableWhenStepDistanceAtMost") == 1, "repeatability distance drift")
    boundary = contract.get("promotionBoundary")
    require(isinstance(boundary, dict), "promotion boundary missing")
    for key in ("capacityBoundaryEstablished", "operationalThresholdApproved", "productionCapacityEvidence", "productionEquivalentEvidence", "independentReviewCompleted", "productionReady"):
        require(boundary.get(key) is False, f"contract cannot enable {key}")
    require(boundary.get("productionDecision") == "NO_GO", "production decision drift")

    require(result.get("schemaVersion") == "memory-os-controlled-saturation-repeatability-results.v1", "result schema drift")
    source = result.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source) is not None, "sourceCommitSha invalid")
    refs = result.get("runRefs")
    require(isinstance(refs, list) and len(refs) == 2 and len(set(refs)) == 2, "two unique runRefs required")
    for ref in refs:
        require(isinstance(ref, str) and not Path(ref).is_absolute() and ".." not in Path(ref).parts and (ROOT / ref).is_file(), f"runRef invalid: {ref}")
        run = load(ROOT / ref)
        require(run.get("commitSha") == source, f"run source mismatch: {ref}")
        environment = run.get("environment")
        require(isinstance(environment, dict), f"run environment missing: {ref}")
        require(environment.get("dependencyMode") == contract.get("dependencyMode"), f"run dependency mode mismatch: {ref}")
        for key in ("productionTraffic", "productionCredentials", "productionEvidence", "productionEquivalentDependencies"):
            require(environment.get(key) is False, f"run cannot enable {key}: {ref}")
        scenario = run.get("scenario")
        require(isinstance(scenario, dict), f"run scenario missing: {ref}")
        require(scenario.get("scenarioId") == source_ramp.get("scenarioId"), f"run scenario binding mismatch: {ref}")
        require(scenario.get("workloadType") == source_ramp.get("workloadType") == "CONTROLLED_RAMP", f"run workload type mismatch: {ref}")
        require(scenario.get("requestsPerStep") == source_ramp.get("requestsPerStep"), f"run requestsPerStep mismatch: {ref}")
    require(result.get("independentRunCount") == 2, "independentRunCount drift")
    signals = result.get("signals")
    require(isinstance(signals, dict) and set(signals) == {"a", "b"}, "signals missing")
    concurrencies: list[int | None] = []
    for label in ("a", "b"):
        row = signals[label]
        require(isinstance(row, dict), f"signal {label} invalid")
        concurrency = row.get("concurrency")
        require(concurrency is None or concurrency in STEPS, f"signal {label} concurrency invalid")
        require(row.get("kind") in {"ACTUAL_FAILURE_SIGNAL", "THROUGHPUT_LATENCY_KNEE", "NO_SIGNAL"}, f"signal {label} kind invalid")
        concurrencies.append(concurrency)
    expected_repeatable = False
    expected_distance = None
    if concurrencies[0] is not None and concurrencies[1] is not None:
        expected_distance = abs(STEPS.index(concurrencies[0]) - STEPS.index(concurrencies[1]))
        expected_repeatable = expected_distance <= 1
    require(result.get("signalStepDistance") == expected_distance, "signalStepDistance drift")
    require(result.get("repeatableLocalDegradationSignalObserved") is expected_repeatable, "repeatable signal claim drift")
    for key in ("capacityBoundaryEstablished", "operationalThresholdApproved", "independentReviewCompleted", "productionEquivalentEvidence", "productionEvidence", "productionReady"):
        require(result.get(key) is False, f"result cannot enable {key}")
    require(result.get("productionDecision") == "NO_GO", "result production decision drift")
    require(result.get("result") == ("PASS" if expected_repeatable else "INCONCLUSIVE"), "result classification drift")
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in ("postgres://", "postgresql://", "minioadmin", "bearer ", "acct_", "x-amz-credential"):
        require(forbidden not in serialized, f"result contains forbidden runtime material: {forbidden}")

    print("Memory OS controlled saturation repeatability validation PASS")
    print("source ramp semantic binding: true")
    print(f"repeatable local degradation: {expected_repeatable}")
    print("capacity boundary established: false")
    print("operational threshold approved: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"CONTROLLED SATURATION REPEATABILITY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
