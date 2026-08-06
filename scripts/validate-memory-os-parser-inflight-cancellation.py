#!/usr/bin/env python3
"""Fail-closed validation for in-flight parser cancellation evidence."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/parser-inflight-cancellation-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/parser-inflight-cancellation-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def strings(value: Any, field: str, minimum: int = 0) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(len(value) >= minimum, f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def validate_result(result: dict[str, Any], expected_sha: str | None) -> None:
    require(result.get("schemaVersion") ==
            "memory-os-parser-inflight-cancellation-results.v1",
            "in-flight cancellation result schemaVersion drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "in-flight result commitSha must be a full SHA")
    if expected_sha:
        require(commit_sha == expected_sha,
                f"in-flight result SHA {commit_sha} != expected {expected_sha}")
    environment = result.get("environment")
    require(isinstance(environment, dict), "in-flight result environment missing")
    require(environment.get("mode") == "GITHUB_ACTIONS_UBUNTU_LINUX",
            "in-flight environment mode drift")
    require(environment.get("productionEvidence") is False,
            "in-flight result cannot claim production evidence")
    require(environment.get("syntheticDataOnly") is True,
            "in-flight result must use synthetic data only")
    require(environment.get("containsSecrets") is False,
            "in-flight result must state containsSecrets false")
    require(result.get("result") == "PASS" and result.get("integrityResult") == "PASS",
            "in-flight cancellation result is not PASS")
    require(result.get("exitCode") == 0, "in-flight cancellation exitCode is not zero")
    assertions = result.get("assertions")
    require(isinstance(assertions, dict), "in-flight assertions missing")
    for flag in (
        "workerFrameObservedBeforeCancel", "spoolDataObservedBeforeCancel",
        "returnedContextCanceled", "spoolResidueAbsent", "sameSpoolReusable",
        "replacementSealValid", "independentVerificationMatched",
    ):
        require(assertions.get(flag) is True, f"in-flight assertion failed: {flag}")
    latency = assertions.get("cancellationLatencyMilliseconds")
    require(isinstance(latency, (int, float)) and 0 <= latency < 1000,
            "in-flight cancellation latency is not below one second")
    require(assertions.get("configuredWallClockMilliseconds") == 10000,
            "in-flight configured wall clock drift")
    limitations = strings(result.get("limitations"), "result.limitations", 6)
    joined = "\n".join(limitations)
    for phrase in (
        "child-process orphan scan not measured",
        "host restart not executed",
        "production artifact not exercised",
        "not production chaos evidence",
    ):
        require(phrase in joined, f"in-flight limitation omitted: {phrase}")
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "password=", "authorization: bearer", "processid", "workerpath",
        "spoolpath", "secretaccesskey", "user content",
    ):
        require(forbidden not in serialized,
                f"in-flight result contains forbidden value: {forbidden}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") ==
            "memory-os-parser-inflight-cancellation.v1",
            "in-flight contract schemaVersion drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-parser-inflight-cancellation-results.v1",
            "in-flight results schemaVersion drift")
    require(contract.get("runnerCommand") ==
            "go test ./internal/parsersup -run ^TestSupervisorCancelsStartedWorkerPromptly$ -count=1",
            "in-flight runner command drift")
    require(contract.get("workingDirectory") == "services/import-api",
            "in-flight workingDirectory drift")
    strings(contract.get("requiredAssertions"), "requiredAssertions", 7)
    strings(contract.get("implementationGuards"), "implementationGuards", 4)
    strings(contract.get("limitations"), "limitations", 6)
    privacy = contract.get("privacy")
    require(isinstance(privacy, dict), "in-flight privacy must be an object")
    require(privacy.get("productionEvidence") is False,
            "in-flight contract cannot claim production evidence")
    for flag in (
        "syntheticDataOnly", "processIdInEvidenceForbidden",
        "workerPathInEvidenceForbidden", "spoolPathInEvidenceForbidden",
        "secretsInEvidenceForbidden", "userContentInEvidenceForbidden",
    ):
        require(privacy.get(flag) is True, f"in-flight privacy.{flag} must be true")

    supervisor = (ROOT / "services/import-api/internal/parsersup/supervisor_linux.go").read_text(encoding="utf-8")
    for snippet in (
        "stopCancellationWatch", "case <-ctx.Done()",
        "outputRead.SetReadDeadline(time.Now())", "if ctxErr := ctx.Err()",
        "syscall.Kill(-pid, syscall.SIGKILL)", "command.Wait()",
    ):
        require(snippet in supervisor, f"supervisor missing cancellation boundary: {snippet}")
    worker = (ROOT / "services/import-api/internal/parsersup/worker.go").read_text(encoding="utf-8")
    require('case "frame_then_sleep"' in worker,
            "worker harness missing frame_then_sleep mode")
    test_source = (ROOT / "services/import-api/internal/parsersup/inflight_cancellation_drill_linux_test.go").read_text(encoding="utf-8")
    for snippet in (
        "spoolAttemptContainsData", "time.After(time.Second)",
        "context.Canceled", "assertRootEmpty", "replacement.Parse", "verifier.Verify",
    ):
        require(snippet in test_source, f"in-flight test missing boundary: {snippet}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "in-flight readiness must be an object")
    for foundation in (
        "contractDefined", "implementationUpdated", "testImplemented", "validatorImplemented",
    ):
        require(readiness.get(foundation) is True,
                f"in-flight readiness.{foundation} must be true")
    for unproven in (
        "exactSourcePassResultCommitted", "childProcessOrphanScanCompleted",
        "hostRestartExecuted", "productionArtifactExecuted", "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven in-flight readiness cannot be true: {unproven}")
    refs = strings(contract.get("evidenceRefs"), "evidenceRefs", 5)
    for ref in refs:
        require((ROOT / ref).is_file(), f"in-flight evidence missing: {ref}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA_RE.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be a full SHA")
        require(RESULT_PATH.is_file(), "exact-source in-flight result is missing")
    if RESULT_PATH.is_file():
        validate_result(load(RESULT_PATH), expected_sha)
    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "in-flight CI evidence cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict) and gate.get("status") != "READY",
            "in-flight local drill cannot make OPS-P0-009 READY")
    print("Memory OS parser in-flight cancellation validation PASS")
    print(f"result present: {RESULT_PATH.is_file()}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"PARSER IN-FLIGHT CANCELLATION VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
