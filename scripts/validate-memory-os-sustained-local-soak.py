#!/usr/bin/env python3
"""Validate the local long-soak contract without conflating it with short CI samples."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"


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
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), "contract root must be object")
    return value


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-sustained-local-soak.v1", "schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-sustained-local-soak-results.v1", "results schema drift")
    require(contract.get("scenarioId") == "mixed-import-lifecycle-local-long-soak", "scenario drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    require(contract.get("classification") == "LOCAL_LONG_SOAK", "classification drift")

    minimum_seconds = contract.get("minimumRunDurationSeconds")
    maximum_seconds = contract.get("maximumSingleRunDurationSeconds")
    minimum_runs = contract.get("minimumIndependentRuns")
    require(isinstance(minimum_seconds, int) and minimum_seconds >= 3600, "long soak minimum must be at least 3600 seconds")
    require(isinstance(maximum_seconds, int) and maximum_seconds >= minimum_seconds and maximum_seconds <= 7200, "single-run duration must stay bounded between minimum and two hours")
    require(isinstance(minimum_runs, int) and minimum_runs >= 2, "at least two independent long runs are required")

    coverage = contract.get("requiredCoverage")
    require(isinstance(coverage, dict), "requiredCoverage must be object")
    for key in (
        "authenticatedPreviewRead",
        "signedUploadLifecycle",
        "parserSupervisor",
        "scanQueue",
        "deletionWorker",
        "postgresql",
        "minio",
    ):
        require(coverage.get(key) is True, f"required coverage missing: {key}")

    observations = contract.get("requiredObservationsPerWindow")
    require(isinstance(observations, list) and len(observations) == len(set(observations)), "required observations must be unique list")
    for key in (
        "heapAllocBytes",
        "heapInuseBytes",
        "rssBytes",
        "goroutines",
        "dbPoolAcquiredConns",
        "dbPoolEmptyAcquireCount",
        "scanQueuePending",
        "deletionPending",
        "minioLifecycleSuccesses",
        "parserRuns",
        "parserFailures",
    ):
        require(key in observations, f"required observation missing: {key}")

    success = contract.get("successCriteriaForOneRun")
    require(isinstance(success, dict), "successCriteriaForOneRun must be object")
    require(success.get("durationAtLeastSeconds") >= 3600, "one-run duration criterion too short")
    for key in (
        "allRequiredCoverageExecuted",
        "noCrossTenantViolation",
        "noIntegrityViolation",
        "noUnexpected3xxOr4xx",
        "noUnclassified5xx",
        "noUnclassifiedTransportErrors",
        "postRunRecoveryProbe",
    ):
        require(success.get(key) is True, f"success criterion must remain true: {key}")
    for key in ("containsSecrets", "productionEvidence", "productionEquivalentDependencies"):
        require(success.get(key) is False, f"success criterion cannot enable {key}")

    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict), "promotionRules must be object")
    require(promotion.get("onePassingRunIsSustainedSoakEvidence") is False, "one long run cannot be sustained-soak evidence")
    require(promotion.get("minimumIndependentPassingRuns", 0) >= 2, "repeated runs required")
    require(promotion.get("allRequiredCoverageMustAppearInEveryPassingRun") is True, "coverage may not be split across runs")
    for key in (
        "trendReviewRequired",
        "positiveSlopeIsNotAutomaticallyALeak",
        "flatSlopeIsNotLeakProof",
        "automaticLeakProofForbidden",
        "automaticOperationalThresholdPromotionForbidden",
        "automaticCapacityBoundaryPromotionForbidden",
        "independentReviewRequiredForProductionPromotion",
    ):
        require(promotion.get(key) is True, f"promotion safeguard missing: {key}")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary must be object")
    require(boundary.get("syntheticDataOnly") is True, "soak must remain synthetic-only")
    require(boundary.get("loopbackDependenciesOnly") is True, "soak must remain loopback-only")
    for key in (
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "sustainedSoakEvidence",
        "leakProof",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"local long-soak contract cannot enable {key}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be object")
    require(readiness.get("contractDefined") is True, "contractDefined must be true")
    for key in (
        "firstLongRunCommitted",
        "secondIndependentLongRunCommitted",
        "allRequiredCoverageExecuted",
        "trendReviewCompleted",
        "sustainedSoakEvidence",
        "leakProofAvailable",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(key) is False, f"foundation cannot pre-claim readiness.{key}")

    artifact_flags = {
        "runnerImplemented": contract.get("runner"),
        "validatorImplemented": contract.get("validator"),
        "aggregateValidatorImplemented": contract.get("aggregateValidator"),
        "automaticWorkflowImplemented": contract.get("workflow"),
    }
    for flag, ref in artifact_flags.items():
        value = readiness.get(flag)
        require(isinstance(value, bool), f"readiness.{flag} must be boolean")
        require(isinstance(ref, str) and ref, f"contract reference for {flag} missing")
        exists = (ROOT / ref).is_file()
        if value:
            require(exists, f"readiness.{flag}=true but artifact missing: {ref}")

    short_contract = load(ROOT / "contracts/operations/short-stability-sample-contract.v1.json")
    short_readiness = short_contract.get("readiness", {})
    require(short_readiness.get("sustainedSoakExecuted") is False, "short CI sample cannot be promoted by long-soak foundation")
    require(short_readiness.get("leakProofAvailable") is False, "short CI sample cannot become leak proof")

    print("Memory OS sustained local soak contract validation PASS")
    print(f"minimum run seconds: {minimum_seconds}")
    print(f"minimum independent runs: {minimum_runs}")
    print("sustained soak evidence: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"SUSTAINED LOCAL SOAK CONTRACT FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
