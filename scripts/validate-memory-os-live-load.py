#!/usr/bin/env python3
"""Fail-closed validation for the live PostgreSQL load checkpoint.

This validator deliberately treats the result as LOCAL_POSTGRES evidence only.
It rejects missing scenarios, status drift, dishonest accounting, malformed
source SHAs, and any attempt to describe the ephemeral harness as production
capacity evidence.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/live-postgres-load-scenario-contract.v1.json"
SHA256_RE = re.compile(r"^[0-9a-f]{40}$")
STATUS_CLASS_RE = re.compile(r"^[1-5]xx$")
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$")


class ValidationError(RuntimeError):
    pass



def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValidationError("duplicate JSON key rejected")
        document[key] = value
    return document


def reject_non_finite_json_constant(value: str) -> None:
    raise ValidationError("non-finite JSON constant rejected: " + value)


def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValidationError("required JSON path is missing or symlink")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (ValueError, OSError) as exc:
        raise ValidationError("JSON path escaped canonical checkout") from exc
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_json_keys,
                           parse_constant=reject_non_finite_json_constant)
    except FileNotFoundError as exc:
        raise ValidationError(f"missing required evidence: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"top-level JSON must be an object: {path.relative_to(ROOT)}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_utc_timestamp(value: Any, field: str) -> None:
    require(isinstance(value, str) and UTC_TIMESTAMP_RE.fullmatch(value) is not None,
            f"{field} must be RFC3339 UTC")
    try:
        dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValidationError(f"{field} must be RFC3339 UTC") from exc


def integer(value: Any, field: str, *, minimum: int = 0) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{field} must be an integer")
    require(value >= minimum, f"{field} must be >= {minimum}")
    return value


def positive_number(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be numeric")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValidationError(f"{field} must be finite") from exc
    require(math.isfinite(number), f"{field} must be finite")
    require(number > 0, f"{field} must be > 0")
    return number


def validate_batch(scenario_id: str, batch: dict[str, Any], contract: dict[str, Any]) -> None:
    requests = integer(batch.get("requests"), f"{scenario_id}.batch.requests", minimum=1)
    concurrency = integer(batch.get("concurrency"), f"{scenario_id}.batch.concurrency", minimum=1)
    successes = integer(batch.get("successes"), f"{scenario_id}.batch.successes")
    failures = integer(batch.get("failures"), f"{scenario_id}.batch.failures")

    require(requests == contract["requests"], f"{scenario_id}: request count drift")
    require(concurrency == contract["concurrency"], f"{scenario_id}: concurrency drift")
    require(successes + failures == requests, f"{scenario_id}: successes + failures != requests")

    counts = batch.get("statusClassCounts")
    require(isinstance(counts, dict) and counts, f"{scenario_id}: statusClassCounts must be non-empty")
    status_total = 0
    observed_classes: set[str] = set()
    for key, value in counts.items():
        require(isinstance(key, str), f"{scenario_id}: status class key must be a string")
        require(key == "transport_error" or STATUS_CLASS_RE.fullmatch(key) is not None,
                f"{scenario_id}: invalid status class {key!r}")
        count = integer(value, f"{scenario_id}.batch.statusClassCounts[{key!r}]")
        status_total += count
        if count > 0:
            observed_classes.add(key)
    require(status_total == requests, f"{scenario_id}: status class total != requests")

    allowed = set(contract["expectedStatusClasses"])
    require("transport_error" not in observed_classes, f"{scenario_id}: transport errors are forbidden")
    require(observed_classes <= allowed,
            f"{scenario_id}: unexpected status classes {sorted(observed_classes - allowed)}")
    require(counts.get("5xx", 0) == 0, f"{scenario_id}: 5xx responses are forbidden")

    duration = positive_number(batch.get("durationSeconds"), f"{scenario_id}.batch.durationSeconds")
    throughput = positive_number(batch.get("throughput"), f"{scenario_id}.batch.throughput")
    require(throughput <= requests / max(duration, 1e-9) * 1.01,
            f"{scenario_id}: throughput exceeds request/duration accounting")

    p50 = positive_number(batch.get("latencyP50Ms"), f"{scenario_id}.batch.latencyP50Ms")
    p95 = positive_number(batch.get("latencyP95Ms"), f"{scenario_id}.batch.latencyP95Ms")
    p99 = positive_number(batch.get("latencyP99Ms"), f"{scenario_id}.batch.latencyP99Ms")
    require(p50 <= p95 <= p99, f"{scenario_id}: latency percentiles are not monotonic")


def validate() -> None:
    contract = load_json(CONTRACT_PATH)
    require(contract.get("resultPath") == "docs/fixtures/memory-os-operability/live-postgres-load-results.sample.v1.json",
            "resultPath authority drift")
    result_path = ROOT / contract["resultPath"]
    result = load_json(result_path)

    require(contract.get("schemaVersion") == "memory-os-live-load-scenario.v1",
            "unexpected live-load contract schemaVersion")
    require(contract.get("resultsSchemaVersion") == "memory-os-live-load-results.v1",
            "unexpected live-load resultsSchemaVersion")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES",
            "live-load contract dependencyMode must remain LOCAL_POSTGRES")
    require(contract.get("productionEvidence") is False,
            "live-load contract must not claim production evidence")

    require(result.get("schemaVersion") == contract["resultsSchemaVersion"],
            "result schemaVersion does not match the contract")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA256_RE.fullmatch(commit_sha) is not None,
            "result commitSha must be a full lowercase 40-character SHA")
    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(commit_sha == expected_sha, "result commitSha does not match EXPECTED_COMMIT_SHA")

    generated_at = result.get("generatedAt")
    require_utc_timestamp(generated_at, "generatedAt")

    environment = result.get("environment")
    require(isinstance(environment, dict), "environment must be an object")
    require(environment.get("databaseMode") == "LOCAL_POSTGRES",
            "databaseMode must be LOCAL_POSTGRES")
    require(environment.get("productionEvidence") is False,
            "ephemeral live-load results must not claim production evidence")
    require(environment.get("objectStoreMode") == "LOCAL_MINIO_HARNESS_ONLY_NOT_MEASURED",
            "object-store mode must state that MinIO was not measured")
    integer(environment.get("numCpu"), "environment.numCpu", minimum=1)
    require(isinstance(environment.get("goVersion"), str) and environment["goVersion"].startswith("go1."),
            "environment.goVersion is invalid")

    contract_scenarios = contract.get("scenarios")
    observed_scenarios = result.get("scenarios")
    require(isinstance(contract_scenarios, list) and contract_scenarios,
            "contract scenarios must be a non-empty list")
    require(isinstance(observed_scenarios, list) and observed_scenarios,
            "result scenarios must be a non-empty list")

    expected: dict[str, dict[str, Any]] = {}
    for item in contract_scenarios:
        require(isinstance(item, dict), "each contract scenario must be an object")
        scenario_id = item.get("scenarioId")
        require(isinstance(scenario_id, str) and scenario_id, "contract scenarioId is required")
        require(scenario_id not in expected, f"duplicate contract scenarioId: {scenario_id}")
        expected[scenario_id] = item

    observed: dict[str, dict[str, Any]] = {}
    for item in observed_scenarios:
        require(isinstance(item, dict), "each result scenario must be an object")
        scenario_id = item.get("scenarioId")
        require(isinstance(scenario_id, str) and scenario_id, "result scenarioId is required")
        require(scenario_id not in observed, f"duplicate result scenarioId: {scenario_id}")
        observed[scenario_id] = item

    require(set(observed) == set(expected),
            f"scenario coverage mismatch: missing={sorted(set(expected) - set(observed))}, "
            f"unexpected={sorted(set(observed) - set(expected))}")

    for scenario_id, scenario in observed.items():
        scenario_contract = expected[scenario_id]
        require(scenario.get("workloadType") == scenario_contract["workloadType"],
                f"{scenario_id}: workloadType drift")
        require(scenario.get("dependencyMode") == "LOCAL_POSTGRES",
                f"{scenario_id}: dependencyMode must be LOCAL_POSTGRES")
        require(scenario.get("result") == "PASS", f"{scenario_id}: result must be PASS")
        require(scenario.get("integrityResult") == "PASS",
                f"{scenario_id}: integrityResult must be PASS")
        require_utc_timestamp(scenario.get("startedAt"), f"{scenario_id}: startedAt")

        batch = scenario.get("batch")
        require(isinstance(batch, dict), f"{scenario_id}: batch must be an object")
        validate_batch(scenario_id, batch, scenario_contract)

        assertions = scenario.get("databaseAssertions")
        require(isinstance(assertions, dict), f"{scenario_id}: databaseAssertions must be an object")
        for key, value in assertions.items():
            integer(value, f"{scenario_id}.databaseAssertions[{key!r}]")

    preview = observed["authenticated-preview-local-postgres"]
    require(preview["batch"]["statusClassCounts"] == {"2xx": 500},
            "preview scenario must be exactly 500 x 2xx")
    require(preview["databaseAssertions"] == {
        "preview_ready_rows": 1,
        "preview_candidate_rows": 2,
        "preview_rejection_rows": 1,
    }, "preview database integrity assertions changed")

    apply_result = observed["concurrent-idempotent-apply-local-postgres"]
    require(apply_result["batch"]["statusClassCounts"].get("2xx", 0) > 0,
            "apply burst must complete at least one transaction")
    require(apply_result["databaseAssertions"] == {
        "memory_item_rows": 2,
        "apply_confirmation_rows": 1,
    }, "apply database integrity assertions changed")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    require(readiness.get("livePostgresHTTPBoundary") is True,
            "livePostgresHTTPBoundary must be true")
    require(readiness.get("forceRLSDeploymentPrincipal") is True,
            "forceRLSDeploymentPrincipal must be true")
    require(readiness.get("idempotencyIntegrityAssertion") is True,
            "idempotencyIntegrityAssertion must be true")
    for forbidden_claim in (
        "objectStoreMeasured",
        "sustainedSoakEvidence",
        "capacityBoundaryEstablished",
        "productionEquivalentDependencies",
    ):
        require(readiness.get(forbidden_claim) is False,
                f"{forbidden_claim} cannot be true for this checkpoint")

    print(f"Live PostgreSQL load evidence PASS: {commit_sha}")


if __name__ == "__main__":
    try:
        validate()
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
