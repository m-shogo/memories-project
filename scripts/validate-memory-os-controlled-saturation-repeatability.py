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


def main() -> int:
    contract = load(CONTRACT)
    result = load(RESULT)
    require(contract.get("schemaVersion") == "memory-os-controlled-saturation-repeatability.v1", "contract schema drift")
    require(contract.get("requiredIndependentRuns") == 2, "required run count drift")
    require(contract.get("concurrencySteps") == STEPS and contract.get("requestsPerStep") == 64, "source ramp binding drift")
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
        require(run.get("environment", {}).get("productionEvidence") is False, f"run cannot be production evidence: {ref}")
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
