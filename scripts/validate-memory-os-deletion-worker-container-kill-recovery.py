#!/usr/bin/env python3
"""Fail-closed validator for Docker container-kill deletion-worker recovery evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/deletion-worker-container-kill-recovery-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/deletion-worker-container-kill-recovery-results.sample.v1.json"
CONTROLLER_PATH = ROOT / "services/import-api/cmd/deletion-container-drill/main.go"
HELPER_PATH = ROOT / "services/import-api/cmd/deletion-container-drill-helper/main.go"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


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
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("schemaVersion") == "memory-os-deletion-worker-container-kill-recovery.v1", "contract schema drift")
    require(contract.get("resultsSchemaVersion") == "memory-os-deletion-worker-container-kill-recovery-results.v1", "result schema drift")
    require(contract.get("scenarioId") == "account-deletion-worker-container-kill-recovery-local-dependencies", "scenario drift")
    require(contract.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    require(contract.get("leaseSeconds") == 5, "container drill lease drift")
    require(contract.get("killSignal") == "SIGKILL", "kill signal drift")
    require(contract.get("killedContainerExpectedExitCode") == 137, "container SIGKILL exit code drift")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary required")
    for key in ("syntheticDataOnly", "actualProcessKillCovered", "actualContainerKillCovered", "replacementContainerRecoveryCovered"):
        require(boundary.get(key) is True, f"required local container coverage missing: {key}")
    for key in (
        "actualHostFailureCovered",
        "availabilityZoneFailureCovered",
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"container drill cannot enable {key}")

    limitations = "\n".join(item for item in contract.get("limitations", []) if isinstance(item, str))
    for fragment in (
        "do not prove physical host, VM, node, availability-zone or control-plane failure",
        "not a production lease recommendation",
        "not production-equivalent dependencies",
        "do not establish throughput, capacity or safe operating thresholds",
    ):
        require(fragment in limitations, f"limitation missing: {fragment}")

    helper = HELPER_PATH.read_text(encoding="utf-8")
    controller = CONTROLLER_PATH.read_text(encoding="utf-8")
    for fragment in (
        'currentUser != "memory_app_login" || superuser || bypassRLS',
        "control.Claim(ctx, testLeaseSeconds)",
        "control.ObjectKeys(ctx, claim.AccountID, claim.DeletionEpoch)",
        "objects.EraseObject(ctx, keys[0])",
        'case "recover":',
        "receipts[0].Attempts != 2",
        '[]byte("recovered-attempt-2\\n")',
    ):
        require(fragment in helper, f"container helper primitive missing: {fragment}")
    for forbidden in (
        "MEMORY_OS_CONTAINER_DRILL_ACCOUNT_ID",
        "MEMORY_OS_CONTAINER_DRILL_OBJECT_KEY",
        "MEMORY_OS_CONTAINER_DRILL_JOB_ID",
        "MEMORY_OS_CONTAINER_DRILL_AUTHORIZATION_ID",
    ):
        require(forbidden not in helper, f"worker container must not receive identity input: {forbidden}")
    for fragment in (
        "control.BeginDeletion(ctx, principal)",
        "claimsBeforeExpiry++",
        "killedExit != 137",
        'string(recoverySignal) == "recovered-attempt-2\\n"',
        'document.Environment.ActualContainerKillCovered = true',
        'document.Environment.ReplacementContainerRecovery = true',
    ):
        require(fragment in controller, f"controller proof primitive missing: {fragment}")


def validate_result(contract: dict[str, Any], expected_sha: str | None) -> None:
    result = load(RESULT_PATH)
    require(result.get("schemaVersion") == contract.get("resultsSchemaVersion"), "result schema mismatch")
    commit = result.get("commitSha")
    require(isinstance(commit, str) and SHA_RE.fullmatch(commit) is not None, "full source commit SHA required")
    if expected_sha is not None:
        require(commit == expected_sha, f"result source {commit} != expected {expected_sha}")

    environment = result.get("environment")
    require(isinstance(environment, dict), "environment required")
    require(environment.get("dependencyMode") == "LOCAL_POSTGRES_MINIO", "dependency mode drift")
    for key in ("syntheticDataOnly", "actualProcessKillCovered", "actualContainerKillCovered", "replacementContainerRecoveryCovered"):
        require(environment.get(key) is True, f"result coverage missing: {key}")
    for key in (
        "actualHostFailureCovered",
        "availabilityZoneFailureCovered",
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "containsSecrets",
    ):
        require(environment.get(key) is False, f"result environment.{key} must remain false")

    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "scenario required")
    require(scenario.get("scenarioId") == contract.get("scenarioId"), "scenario id drift")
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
        "actualContainerKillObserved",
        "runtimeContainerRestricted",
        "noIdentityInputToWorkerContainers",
        "ledgerSurvivedContainerKill",
        "objectErasedBeforeContainerKill",
        "noClaimBeforeExpiry",
        "replacementContainerAttempt2",
        "backlogConverged",
        "allOwnedRowsErased",
        "noObjectResurrection",
    ):
        require(assertions.get(key) is True, f"assertion must be true: {key}")
    for key in ("actualHostFailureCovered", "availabilityZoneFailureCovered", "productionEvidence"):
        require(assertions.get(key) is False, f"assertion must remain false: {key}")

    serialized = json.dumps(result, ensure_ascii=False)
    for forbidden in (
        "postgres://",
        "postgresql://",
        "minioadmin",
        "memory_app_login:",
        "acct_",
        "job_",
        "upl_",
        "quarantine/",
        "MEMORY_OS_CONTAINER_DRILL_DATABASE_URL",
    ):
        require(forbidden not in serialized, f"forbidden runtime material in result: {forbidden}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-result", action="store_true")
    parser.add_argument("--expected-commit-sha")
    args = parser.parse_args()

    contract = load(CONTRACT_PATH)
    validate_contract(contract)
    result_exists = RESULT_PATH.is_file()
    if args.require_result:
        require(result_exists, "exact-source container-kill result is required")
    if result_exists:
        validate_result(contract, args.expected_commit_sha)

    print("Memory OS deletion worker container-kill recovery validation PASS")
    print(f"result present: {str(result_exists).lower()}")
    print("actual container kill required: true")
    print("replacement container recovery required: true")
    print("actual host failure covered: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION WORKER CONTAINER-KILL RECOVERY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
