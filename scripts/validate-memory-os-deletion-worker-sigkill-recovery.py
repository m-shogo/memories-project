#!/usr/bin/env python3
"""Fail-closed validator for actual Linux SIGKILL deletion-worker recovery evidence."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-worker-sigkill-recovery-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-sigkill-recovery-results.sample.v1.json"
RUNNER_PATH = ROOT / "services/import-api/internal/httpserver/deletion_worker_sigkill_recovery_linux_test.go"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_JSON_BYTES = 1024 * 1024
MAX_RUNNER_BYTES = 1024 * 1024


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def reject_nonfinite_constant(value: str) -> None:
    raise Fail("non-finite SIGKILL JSON constant rejected")


def parse_finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite SIGKILL JSON number rejected")
    return parsed


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in document, "duplicate SIGKILL JSON key rejected")
        document[key] = value
    return document


def load(path: Path) -> dict[str, Any]:
    require(isinstance(path, Path), "SIGKILL JSON path must be Path")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "SIGKILL JSON symlink rejected")
    require(path.is_file(), "SIGKILL JSON file missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError):
        raise Fail("SIGKILL JSON path escaped repository") from None
    try:
        with path.open("rb") as source:
            raw = source.read(MAX_JSON_BYTES + 1)
        require(len(raw) <= MAX_JSON_BYTES, "SIGKILL JSON exceeds reviewed read limit")
        value = json.loads(raw.decode("utf-8"),
                           parse_constant=reject_nonfinite_constant,
                           parse_float=parse_finite_float,
                           object_pairs_hook=reject_duplicate_json_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, OverflowError, RecursionError):
        raise Fail("SIGKILL JSON unreadable or invalid") from None
    require(isinstance(value, dict), "SIGKILL JSON root must be object")
    return value


def read_runner(path: Path) -> str:
    require(isinstance(path, Path), "SIGKILL runner path must be Path")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "SIGKILL runner symlink rejected")
    require(path.is_file(), "SIGKILL runner missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError):
        raise Fail("SIGKILL runner path escaped repository") from None
    try:
        with path.open("rb") as source:
            raw = source.read(MAX_RUNNER_BYTES + 1)
        require(len(raw) <= MAX_RUNNER_BYTES, "SIGKILL runner exceeds reviewed read limit")
        return raw.decode("utf-8")
    except (OSError, UnicodeError):
        raise Fail("SIGKILL runner unreadable or invalid") from None


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("schemaVersion") == "memory-os-deletion-worker-sigkill-recovery.v1", "contract schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-deletion-worker-sigkill-recovery-results.v1", "result schema drift")
    require(contract.get("scenarioId") == "account-deletion-worker-sigkill-recovery-local-dependencies", "scenario drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    require(contract.get("leaseSeconds") == 5, "bounded SIGKILL test lease drift")
    require(contract.get("killSignal") == "SIGKILL", "kill signal must remain SIGKILL")
    require(contract.get("interruptionPoint") == "AFTER_REAL_OBJECT_ERASURE_BEFORE_DATABASE_SWEEP_OR_LEASE_RELEASE", "interruption point drift")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary must be object")
    require(boundary.get("syntheticDataOnly") is True, "synthetic-only boundary required")
    require(boundary.get("linuxOnly") is True, "Linux-only classification required")
    require(boundary.get("actualProcessKillCovered") is True, "contract must require actual process kill")
    for key in (
        "actualHostFailureCovered",
        "containerRestartCovered",
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"SIGKILL local proof cannot enable {key}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be object")
    require(readiness.get("contractDefined") is True, "contractDefined must be true")
    for key in ("runnerImplemented", "validatorImplemented", "automaticWorkflowImplemented", "exactSourceResultCommitted", "actualSIGKILLRecoveryProven"):
        require(isinstance(readiness.get(key), bool), f"readiness.{key} must be boolean")
    for key in ("productionDependenciesTested", "independentReviewCompleted", "productionReady"):
        require(readiness.get(key) is False, f"local SIGKILL proof cannot enable readiness.{key}")

    limitations = "\n".join(item for item in contract.get("limitations", []) if isinstance(item, str))
    for fragment in (
        "does not prove host, container-runtime or availability-zone failure",
        "not a production lease recommendation",
        "not production-equivalent dependencies",
        "does not establish throughput, capacity or safe operating thresholds",
    ):
        require(fragment in limitations, f"limitation missing: {fragment}")

    runner = read_runner(RUNNER_PATH)
    for fragment in (
        "//go:build linux",
        "exec.Command(os.Args[0]",
        "control.Claim(ctx, deletionWorkerSIGKILLLeaseSeconds)",
        "control.ObjectKeys(ctx, claim.AccountID, claim.DeletionEpoch)",
        "objects.EraseObject(ctx, keys[0])",
        "syscall.Kill(cmd.Process.Pid, syscall.SIGKILL)",
        "waitStatus.Signal() != syscall.SIGKILL",
        "receipts[0].Attempts != 2",
    ):
        require(fragment in runner, f"runner proof primitive missing: {fragment}")
    require("MEMORY_OS_SIGKILL_HELPER_ACCOUNT" not in runner, "parent must not pass account id to child")
    require("MEMORY_OS_SIGKILL_HELPER_OBJECT" not in runner, "parent must not pass object key to child")


def validate_result(contract: dict[str, Any], expected_sha: str | None) -> None:
    result = load(RESULT_PATH)
    require(result.get("schemaVersion") == contract.get("resultsSchemaVersion"), "result schema mismatch")
    commit = result.get("commitSha")
    require(isinstance(commit, str) and SHA_RE.fullmatch(commit) is not None, "full source commit SHA required")
    if expected_sha is not None:
        require(commit == expected_sha, f"result source {commit} != expected {expected_sha}")

    environment = result.get("environment")
    require(isinstance(environment, dict), "environment required")
    require(environment.get("os") == "linux", "actual SIGKILL proof must run on Linux")
    require(environment.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    require(environment.get("syntheticDataOnly") is True, "synthetic-only result required")
    require(environment.get("actualProcessKillCovered") is True, "actual process kill must be covered")
    for key in (
        "actualHostFailureCovered",
        "containerRestartCovered",
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "containsSecrets",
    ):
        require(environment.get(key) is False, f"result environment.{key} must remain false")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "scenario required")
    require(scenario.get("scenarioId") == contract.get("scenarioId"), "result scenario drift")
    criteria = contract.get("successCriteria")
    require(isinstance(criteria, dict), "successCriteria required")
    for key, expected in criteria.items():
        if key == "productionEvidence":
            continue
        require(scenario.get(key) == expected, f"result criterion mismatch: {key}")
    require(scenario.get("result") == "PASS", "result must PASS")
    require(scenario.get("integrityResult") == "PASS", "integrity must PASS")

    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "assertions required")
    for key in (
        "childDiscoveredClaimWithoutAccountInput",
        "actualSIGKILLObserved",
        "ledgerSurvivedSIGKILL",
        "objectErasedBeforeSIGKILL",
        "noClaimBeforeExpiry",
        "replacementClaimWasAttempt2",
        "idempotentObjectRecovery",
        "backlogConverged",
        "allOwnedRowsErased",
    ):
        require(assertions.get(key) is True, f"assertion must be true: {key}")
    for key in ("actualHostFailureCovered", "containerRestartCovered", "productionEvidence"):
        require(assertions.get(key) is False, f"assertion must remain false: {key}")

    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://",
        "postgresql://",
        "minioadmin",
        "bearer ",
        "x-amz-credential",
        "acct_",
        "job_",
        "upl_",
        "quarantine/",
        "memory_os_sigkill_helper_database_url",
    ):
        require(forbidden not in serialized, f"forbidden runtime material in result: {forbidden}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-result", action="store_true")
    parser.add_argument("--expected-commit-sha")
    args = parser.parse_args()

    contract = load(CONTRACT_PATH)
    validate_contract(contract)
    for candidate in (RESULT_PATH, *RESULT_PATH.parents):
        require(not candidate.is_symlink(), "SIGKILL result symlink rejected")
    result_exists = RESULT_PATH.is_file()
    if args.require_result:
        require(result_exists, "exact-source SIGKILL result is required")
    if result_exists:
        validate_result(contract, args.expected_commit_sha)

    print("Memory OS deletion worker SIGKILL recovery validation PASS")
    print(f"result present: {str(result_exists).lower()}")
    print("actual process kill required: true")
    print("actual host failure covered: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION WORKER SIGKILL RECOVERY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
