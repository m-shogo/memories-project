#!/usr/bin/env python3
"""Fail-closed validator for the live PostgreSQL + MinIO upload checkpoint."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/live-object-load-scenario-contract.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
STATUS_RE = re.compile(r"^[1-5]xx$")


class ValidationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ValidationError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"missing required evidence: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"top-level JSON must be an object: {path.relative_to(ROOT)}")
    return value


def integer(value: Any, field: str, *, minimum: int = 0) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{field} must be an integer")
    require(value >= minimum, f"{field} must be >= {minimum}")
    return value


def positive(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be numeric")
    number = float(value)
    require(number > 0, f"{field} must be > 0")
    return number


def validate() -> None:
    contract = load(CONTRACT_PATH)
    result = load(ROOT / contract["resultPath"])

    require(contract.get("schemaVersion") == "memory-os-live-object-load-scenario.v1",
            "unexpected contract schemaVersion")
    require(contract.get("resultsSchemaVersion") == "memory-os-live-object-load-results.v1",
            "unexpected results schemaVersion")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO",
            "contract dependencyMode must be LOCAL_POSTGRES_MINIO")
    require(contract.get("productionEvidence") is False,
            "local object checkpoint cannot claim production evidence")

    require(result.get("schemaVersion") == contract["resultsSchemaVersion"],
            "result schemaVersion mismatch")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "commitSha must be a full lowercase 40-character SHA")
    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(commit_sha == expected_sha, "commitSha does not match EXPECTED_COMMIT_SHA")

    require(isinstance(result.get("generatedAt"), str) and result["generatedAt"].endswith("Z"),
            "generatedAt must be RFC3339 UTC")
    environment = result.get("environment")
    require(isinstance(environment, dict), "environment must be an object")
    require(environment.get("databaseMode") == "LOCAL_POSTGRES",
            "databaseMode must be LOCAL_POSTGRES")
    require(environment.get("objectStoreMode") == "LOCAL_MINIO_MEASURED",
            "objectStoreMode must be LOCAL_MINIO_MEASURED")
    require(environment.get("productionEvidence") is False,
            "ephemeral MinIO results cannot claim production evidence")
    integer(environment.get("numCpu"), "environment.numCpu", minimum=1)

    expected_items = contract.get("scenarios")
    observed_items = result.get("scenarios")
    require(isinstance(expected_items, list) and len(expected_items) == 1,
            "contract must define exactly one object-load scenario")
    require(isinstance(observed_items, list) and len(observed_items) == 1,
            "result must contain exactly one object-load scenario")
    expected = expected_items[0]
    observed = observed_items[0]

    scenario_id = expected["scenarioId"]
    require(observed.get("scenarioId") == scenario_id, "scenarioId mismatch")
    require(observed.get("workloadType") == expected["workloadType"], "workloadType drift")
    require(observed.get("dependencyMode") == "LOCAL_POSTGRES_MINIO",
            "dependencyMode must be LOCAL_POSTGRES_MINIO")
    require(observed.get("result") == "PASS", "scenario result must be PASS")
    require(observed.get("integrityResult") == "PASS", "integrityResult must be PASS")
    require(isinstance(observed.get("startedAt"), str) and observed["startedAt"].endswith("Z"),
            "startedAt must be RFC3339 UTC")

    batch = observed.get("batch")
    require(isinstance(batch, dict), "batch must be an object")
    requests = integer(batch.get("requests"), "batch.requests", minimum=1)
    concurrency = integer(batch.get("concurrency"), "batch.concurrency", minimum=1)
    successes = integer(batch.get("successes"), "batch.successes")
    failures = integer(batch.get("failures"), "batch.failures")
    require(requests == expected["requests"], "request count drift")
    require(concurrency == expected["concurrency"], "concurrency drift")
    require(successes + failures == requests, "successes + failures != requests")
    require(successes == requests and failures == 0, "every upload lifecycle must succeed")

    counts = batch.get("statusClassCounts")
    require(isinstance(counts, dict) and counts, "statusClassCounts must be non-empty")
    total = 0
    observed_classes: set[str] = set()
    for key, value in counts.items():
        require(isinstance(key, str), "status class key must be a string")
        require(key == "transport_error" or STATUS_RE.fullmatch(key) is not None,
                f"invalid status class: {key!r}")
        count = integer(value, f"statusClassCounts[{key!r}]")
        total += count
        if count > 0:
            observed_classes.add(key)
    require(total == requests, "status-class total != requests")
    require(observed_classes == {"2xx"}, f"unexpected status classes: {sorted(observed_classes)}")
    require(counts.get("2xx") == requests, "all lifecycles must finish in 2xx")

    duration = positive(batch.get("durationSeconds"), "batch.durationSeconds")
    throughput = positive(batch.get("throughput"), "batch.throughput")
    require(throughput <= requests / max(duration, 1e-9) * 1.01,
            "throughput exceeds request/duration accounting")
    p50 = positive(batch.get("latencyP50Ms"), "batch.latencyP50Ms")
    p95 = positive(batch.get("latencyP95Ms"), "batch.latencyP95Ms")
    p99 = positive(batch.get("latencyP99Ms"), "batch.latencyP99Ms")
    require(p50 <= p95 <= p99, "latency percentiles are not monotonic")

    expected_db = {
        "consumed_upload_authorization_rows": 32,
        "scan_pending_quarantine_rows": 32,
        "distinct_object_version_ids": 32,
        "distinct_object_keys": 32,
    }
    expected_object = {
        "presigned_put_successes": 32,
        "exact_version_completions": 32,
        "distinct_version_ids_verified": 32,
    }
    require(observed.get("databaseAssertions") == expected_db,
            "database assertions changed or are incomplete")
    require(observed.get("objectStoreAssertions") == expected_object,
            "object-store assertions changed or are incomplete")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for required_claim in (
        "signedAuthorizationMeasured",
        "presignedPutMeasured",
        "exactVersionVerificationMeasured",
        "scanEnqueueMeasured",
    ):
        require(readiness.get(required_claim) is True, f"{required_claim} must be true")
    for forbidden_claim in (
        "productionTLS",
        "productionScopedCredentials",
        "retentionLifecycleEvidence",
        "sustainedSoakEvidence",
        "capacityBoundaryEstablished",
        "productionEquivalentDependencies",
    ):
        require(readiness.get(forbidden_claim) is False,
                f"{forbidden_claim} cannot be true for this local checkpoint")

    print(f"Live MinIO upload evidence PASS: {commit_sha}")


if __name__ == "__main__":
    try:
        validate()
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
