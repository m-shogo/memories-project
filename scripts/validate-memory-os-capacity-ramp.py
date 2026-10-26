#!/usr/bin/env python3
"""Fail-closed validation for the bounded local PostgreSQL capacity ramp."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/capacity-ramp-contract.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def reject_nonfinite_constant(value: str) -> None:
    raise ValidationFailure("non-finite capacity ramp JSON constant rejected")


def parse_finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite capacity ramp JSON number rejected")
    return parsed


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in document, "duplicate capacity JSON key rejected")
        document[key] = value
    return document


def load(path: Path) -> dict[str, Any]:
    """Admit only unambiguous regular JSON within the checked-out repository."""
    require(isinstance(path, Path), "capacity JSON path must be Path")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "capacity JSON symlink rejected")
    require(path.is_file(), "capacity JSON file missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError):
        raise ValidationFailure("capacity JSON path escaped repository") from None
    try:
        value = json.loads(path.read_text(encoding="utf-8"),
                           parse_constant=reject_nonfinite_constant,
                           parse_float=parse_finite_float,
                           object_pairs_hook=reject_duplicate_json_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, OverflowError):
        raise ValidationFailure("capacity JSON unreadable or invalid") from None
    require(isinstance(value, dict), "capacity JSON root must be an object")
    return value


def integer(value: Any, field: str, minimum: int = 0) -> int:
    require(isinstance(value, int) and not isinstance(value, bool),
            f"{field} must be an integer")
    require(value >= minimum, f"{field} must be >= {minimum}")
    return value


def positive_number(value: Any, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool),
            f"{field} must be numeric")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise ValidationFailure(f"{field} must be finite and positive") from None
    require(math.isfinite(number) and number > 0, f"{field} must be finite and positive")
    return number


def is_ancestor(value: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", value, "HEAD"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0



def strict_utc_timestamp(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and UTC_TIMESTAMP_RE.fullmatch(value) is not None,
            f"{field} must be RFC3339 UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise ValidationFailure(f"{field} is not a valid UTC timestamp") from None


def validate_capacity_timestamps(result: dict[str, Any]) -> None:
    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "capacity scenario missing for timestamps")
    started = strict_utc_timestamp(scenario.get("startedAt"), "scenario.startedAt")
    completed = strict_utc_timestamp(scenario.get("completedAt"), "scenario.completedAt")
    generated = strict_utc_timestamp(result.get("generatedAt"), "generatedAt")
    require(started <= completed <= generated, "capacity ramp timestamps must be chronological")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-commit-sha", default=os.getenv("EXPECTED_COMMIT_SHA", ""))
    parser.add_argument("--require-reconciled", action="store_true")
    args = parser.parse_args()

    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-capacity-ramp.v1",
            "capacity ramp contract schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-capacity-ramp-results.v1",
            "capacity ramp result schema drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES",
            "capacity ramp dependency mode drift")
    require(contract.get("workloadType") == "RAMP",
            "capacity ramp workload type drift")
    expected_steps = contract.get("concurrencySteps")
    require(expected_steps == [4, 8, 16, 24, 32, 48],
            "capacity ramp concurrency steps drift")
    requests_per_step = integer(contract.get("requestsPerStep"),
                                "contract.requestsPerStep", 1)
    require(requests_per_step == 240, "capacity ramp request count drift")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary missing")
    for field in (
        "productionTraffic", "productionCredentials", "productionEvidence",
        "productionEquivalentDependencies", "capacityBoundaryEstablished",
        "operationalThresholdApproved", "productionReady",
    ):
        require(boundary.get(field) is False, f"contract overclaims {field}")
    require(boundary.get("syntheticDataOnly") is True,
            "synthetic data boundary missing")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    for field in (
        "contractDefined", "runnerImplemented", "validatorImplemented",
        "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True, f"readiness missing: {field}")
    for field in (
        "capacityBoundaryEstablished", "operationalThresholdApproved",
        "independentReviewCompleted", "productionReady",
    ):
        require(readiness.get(field) is False, f"unproven readiness cannot be true: {field}")

    require(contract.get("resultPath") == "docs/fixtures/memory-os-operability/capacity-ramp-results.sample.v1.json",
            "capacity ramp result path drift")
    result_path = ROOT / contract["resultPath"]
    for candidate in (result_path, *result_path.parents):
        require(not candidate.is_symlink(), "capacity ramp result symlink rejected")
    if not result_path.is_file():
        require(readiness.get("exactSourceResultCommitted") is False,
                "contract claims a missing exact-source result")
        require(not args.expected_commit_sha and not args.require_reconciled,
                "exact-source capacity ramp result is required but missing")
        print("Memory OS capacity ramp static validation PASS")
        print("exact-source result present: False")
        print("capacity boundary established: False")
        print("production decision: NO_GO")
        return 0

    result = load(result_path)
    require(result.get("schemaVersion") == contract["resultsSchemaVersion"],
            "capacity ramp result schema drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "capacity ramp commitSha is invalid")
    require(is_ancestor(commit_sha), "capacity ramp source is not an ancestor of HEAD")
    if args.expected_commit_sha:
        require(SHA_RE.fullmatch(args.expected_commit_sha) is not None,
                "expected commit SHA is invalid")
        require(commit_sha == args.expected_commit_sha,
                "capacity ramp result is not from the expected source")

    environment = result.get("environment")
    require(isinstance(environment, dict), "result environment missing")
    require(environment.get("dependencyMode") == "LOCAL_POSTGRES" and
            environment.get("syntheticDataOnly") is True and
            environment.get("productionTraffic") is False and
            environment.get("productionCredentials") is False and
            environment.get("productionEvidence") is False and
            environment.get("productionEquivalentDependencies") is False and
            environment.get("containsSecrets") is False,
            "capacity ramp evidence boundary drift")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "capacity ramp scenario missing")
    validate_capacity_timestamps(result)
    require(scenario.get("scenarioId") == contract["scenarioId"],
            "capacity ramp scenario ID drift")
    require(scenario.get("workloadType") == "RAMP",
            "capacity ramp workload type mismatch")
    require(scenario.get("requestsPerStep") == requests_per_step,
            "capacity ramp requestsPerStep mismatch")
    require(scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "capacity ramp result is not PASS")
    require(scenario.get("decision") == "BOUNDARY_NOT_ESTABLISHED",
            "bounded ramp cannot establish a capacity boundary")
    require(scenario.get("firstSaturationSignal") is None,
            "unexpected saturation signal requires separate reviewed evidence")
    require(scenario.get("candidateSafeConcurrency") == expected_steps[-1],
            "candidate safe concurrency must equal the highest all-success step")

    steps = scenario.get("steps")
    require(isinstance(steps, list) and len(steps) == len(expected_steps),
            "capacity ramp step coverage mismatch")
    observed_steps: list[int] = []
    for index, item in enumerate(steps):
        require(isinstance(item, dict), f"step {index} must be an object")
        concurrency = integer(item.get("concurrency"), f"step[{index}].concurrency", 1)
        observed_steps.append(concurrency)
        batch = item.get("batch")
        require(isinstance(batch, dict), f"step[{index}].batch missing")
        require(batch.get("concurrency") == concurrency,
                f"step[{index}] concurrency accounting mismatch")
        requests = integer(batch.get("requests"), f"step[{index}].requests", 1)
        successes = integer(batch.get("successes"), f"step[{index}].successes")
        failures = integer(batch.get("failures"), f"step[{index}].failures")
        require(requests == requests_per_step,
                f"step[{index}] request count drift")
        require(successes == requests and failures == 0,
                f"step[{index}] was not all-success")
        counts = batch.get("statusClassCounts")
        require(isinstance(counts, dict), f"step[{index}] status counts missing")
        require(set(counts).issubset({"2xx", "3xx", "4xx", "5xx", "transport_error"}),
                f"step[{index}] unknown status class")
        require(integer(counts.get("2xx"), f"step[{index}].statusClassCounts.2xx") == requests,
                f"step[{index}] must be exactly all 2xx")
        for status_class in ("3xx", "4xx", "5xx", "transport_error"):
            require(integer(counts.get(status_class, 0),
                            f"step[{index}].statusClassCounts.{status_class}") == 0,
                    f"step[{index}] contains non-2xx or infrastructure failure")
        duration = positive_number(batch.get("durationSeconds"),
                                   f"step[{index}].durationSeconds")
        throughput = positive_number(batch.get("throughput"),
                                     f"step[{index}].throughput")
        derived_throughput = requests / duration
        require(math.isfinite(derived_throughput) and
                math.isclose(throughput, derived_throughput, rel_tol=1e-6, abs_tol=1e-6),
                f"step[{index}] throughput does not match measured requests and duration")
        p50 = positive_number(batch.get("latencyP50Ms"), f"step[{index}].latencyP50Ms")
        p95 = positive_number(batch.get("latencyP95Ms"), f"step[{index}].latencyP95Ms")
        p99 = positive_number(batch.get("latencyP99Ms"), f"step[{index}].latencyP99Ms")
        require(p50 <= p95 <= p99,
                f"step[{index}] latency percentiles are not monotonic")
    require(observed_steps == expected_steps, "capacity ramp step order drift")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "capacity ramp assertions missing")
    for field, value in contract["successCriteria"].items():
        require(assertions.get(field) == value,
                f"capacity ramp assertion mismatch: {field}")

    # ASCII credential and identifier markers are case-insensitive.
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "bearer ", "password=",
        "acct_", "job_", "prv_", "idem-",
    ):
        require(forbidden not in serialized,
                f"capacity ramp result contains forbidden content: {forbidden}")

    if args.require_reconciled:
        require(readiness.get("exactSourceResultCommitted") is True and
                readiness.get("localRampExecuted") is True,
                "capacity ramp result is not reconciled")
    else:
        require(readiness.get("exactSourceResultCommitted") in (False, True),
                "exactSourceResultCommitted must be boolean")

    print("Memory OS capacity ramp validation PASS")
    print(f"source: {commit_sha[:12]}")
    print(f"candidate safe concurrency: {scenario['candidateSafeConcurrency']}")
    print("capacity boundary established: False")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"CAPACITY RAMP VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
