#!/usr/bin/env python3
"""Validate the local long-soak contract without conflating it with short CI or production evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
RUNNER_PATH = ROOT / "services/import-api/internal/httpserver/sustained_local_soak_test.go"


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


def positive_int(value: Any, field: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool) and value > 0, f"{field} must be positive integer")
    return value


def validate_runner_safety() -> None:
    try:
        source = RUNNER_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise Fail(f"missing runner: {RUNNER_PATH.relative_to(ROOT)}") from exc
    for required in (
        "DeletionPending               int64",
        "DeletionStuck                 int64",
        "func sustainedSoakDeletionBacklog(t *testing.T, server *liveServer) (int64, int64)",
        "refusing to write long-soak evidence for a run configured below 3600 seconds",
        "sustainedMinimumEvidenceDurationSec = 3600",
        "sustainedMaximumRunDurationSec      = 5400",
    ):
        require(required in source, f"runner safety binding missing: {required}")
    require("DeletionPending               int                       `json:\"deletionPending\"`" not in source,
            "runner reverted deletion pending telemetry to int")
    require("DeletionStuck                 int                       `json:\"deletionStuck\"`" not in source,
            "runner reverted deletion stuck telemetry to int")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-sustained-local-soak.v1", "schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-sustained-local-soak-results.v1", "results schema drift")
    require(contract.get("scenarioId") == "mixed-import-lifecycle-local-long-soak", "scenario drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    require(contract.get("classification") == "LOCAL_LONG_SOAK", "classification drift")
    validate_runner_safety()

    minimum_seconds = positive_int(contract.get("minimumRunDurationSeconds"), "minimumRunDurationSeconds")
    maximum_seconds = positive_int(contract.get("maximumSingleRunDurationSeconds"), "maximumSingleRunDurationSeconds")
    minimum_runs = positive_int(contract.get("minimumIndependentRuns"), "minimumIndependentRuns")
    require(minimum_seconds >= 3600, "long soak minimum must be at least 3600 seconds")
    require(maximum_seconds >= minimum_seconds and maximum_seconds <= 7200, "single-run duration must stay bounded between minimum and two hours")
    require(minimum_runs >= 2, "at least two independent long runs are required")

    window_count = positive_int(contract.get("windowCount"), "windowCount")
    require(window_count >= 12, "long soak must contain at least 12 observation windows")
    preview_requests = positive_int(contract.get("previewRequestsPerWindow"), "previewRequestsPerWindow")
    preview_concurrency = positive_int(contract.get("previewConcurrency"), "previewConcurrency")
    upload_requests = positive_int(contract.get("signedUploadLifecyclesPerWindow"), "signedUploadLifecyclesPerWindow")
    upload_concurrency = positive_int(contract.get("signedUploadConcurrency"), "signedUploadConcurrency")
    parser_runs = positive_int(contract.get("parserRecoveryRunsPerWindow"), "parserRecoveryRunsPerWindow")
    deletion_every = positive_int(contract.get("deletionCycleEveryWindows"), "deletionCycleEveryWindows")
    queue_max = positive_int(contract.get("maximumScanQueuePending"), "maximumScanQueuePending")
    require(preview_concurrency <= preview_requests, "preview concurrency cannot exceed request count")
    require(upload_concurrency <= upload_requests, "upload concurrency cannot exceed lifecycle count")
    require(parser_runs == 1, "parser recovery run count is intentionally fixed at one per window")
    require(window_count % deletion_every == 0, "deletion cadence must divide window count exactly")
    require(upload_requests * window_count + 1 <= queue_max, "scan queue ceiling must also contain the post-run upload recovery probe")
    require(contract.get("maximumDeletionPendingAfterWindow") == 0, "deletion pending backlog must converge to zero each window")
    require(contract.get("maximumDeletionStuckAfterWindow") == 0, "deletion stuck backlog must remain zero")

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
        "elapsedSeconds",
        "requestsBySurface",
        "successesBySurface",
        "failuresBySurface",
        "statusClassCountsBySurface",
        "latencyP95MsBySurface",
        "latencyP99MsBySurface",
        "heapAllocBytes",
        "heapInuseBytes",
        "rssBytes",
        "goroutines",
        "dbPoolMaxConns",
        "dbPoolAcquiredConns",
        "dbPoolEmptyAcquireCount",
        "dbPoolCanceledAcquireCount",
        "dbPoolAcquireDurationMs",
        "scanQueuePending",
        "scanQueueOldestPendingSeconds",
        "deletionPending",
        "deletionStuck",
        "minioLifecycleSuccesses",
        "parserRuns",
        "parserFailures",
    ):
        require(key in observations, f"required observation missing: {key}")

    trends = contract.get("requiredTrendAnalysis")
    require(isinstance(trends, list) and len(trends) >= 8, "requiredTrendAnalysis is incomplete")

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
        "scanQueueRemainsWithinBound",
        "deletionBacklogConvergesEachWindow",
        "postRunRecoveryProbe",
    ):
        require(success.get(key) is True, f"success criterion must remain true: {key}")
    for key in ("containsSecrets", "productionEvidence", "productionEquivalentDependencies"):
        require(success.get(key) is False, f"success criterion cannot enable {key}")

    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict), "promotionRules must be object")
    require(promotion.get("onePassingRunIsLocalSustainedSoakEvidence") is False, "one long run cannot be local sustained-soak evidence")
    require(promotion.get("minimumIndependentPassingRuns", 0) >= 2, "repeated runs required")
    require(promotion.get("allRequiredCoverageMustAppearInEveryPassingRun") is True, "coverage may not be split across runs")
    for key in (
        "trendReviewRequired",
        "positiveSlopeIsNotAutomaticallyALeak",
        "flatSlopeIsNotLeakProof",
        "automaticLeakProofForbidden",
        "automaticOperationalThresholdPromotionForbidden",
        "automaticCapacityBoundaryPromotionForbidden",
        "automaticProductionSoakPromotionForbidden",
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
        "productionSustainedSoakEvidence",
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
        "localSustainedSoakEvidence",
        "productionSustainedSoakEvidence",
        "leakProofAvailable",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(isinstance(readiness.get(key), bool), f"readiness.{key} must be boolean")
    for key in (
        "productionSustainedSoakEvidence",
        "leakProofAvailable",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(key) is False, f"local evidence can never enable readiness.{key}")
    if readiness.get("localSustainedSoakEvidence"):
        require(readiness.get("firstLongRunCommitted") is True and readiness.get("secondIndependentLongRunCommitted") is True,
                "local sustained-soak evidence requires two committed long runs")
        require(readiness.get("allRequiredCoverageExecuted") is True, "local sustained-soak evidence requires full coverage")
        require(readiness.get("trendReviewCompleted") is True, "local sustained-soak evidence requires trend review")

    artifact_flags = {
        "runnerImplemented": contract.get("runner"),
        "validatorImplemented": contract.get("validator"),
        "resultValidatorImplemented": contract.get("resultValidator"),
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

    load_contract = load(ROOT / "contracts/operations/load-test-scenario-contract.v1.json")
    load_readiness = load_contract.get("readiness", {})
    require(load_readiness.get("sustainedSoakEvidence") is False, "LOCAL_LONG_SOAK must not promote generic/production-shaped sustainedSoakEvidence")
    require(load_readiness.get("productionEquivalentDependencies") is False, "LOCAL_LONG_SOAK must not promote production-equivalent dependencies")

    print("Memory OS sustained local soak contract validation PASS")
    print(f"minimum run seconds: {minimum_seconds}")
    print(f"minimum independent runs: {minimum_runs}")
    print(f"local sustained soak evidence: {str(readiness.get('localSustainedSoakEvidence')).lower()}")
    print("production sustained soak evidence: false")
    print("leak proof: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"SUSTAINED LOCAL SOAK CONTRACT FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
