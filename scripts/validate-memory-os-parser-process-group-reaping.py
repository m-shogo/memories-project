#!/usr/bin/env python3
"""Fail-closed validation for parser process-group reaping evidence."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/parser-process-group-reaping-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/parser-process-group-reaping-results.sample.v1.json"
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
    require(result.get("schemaVersion") == "memory-os-parser-process-group-reaping-results.v1",
            "process-group reaping result schemaVersion drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "process-group reaping commitSha must be a full SHA")
    if expected_sha:
        require(commit_sha == expected_sha,
                f"process-group reaping result SHA {commit_sha} != expected {expected_sha}")
    environment = result.get("environment")
    require(isinstance(environment, dict), "process-group reaping environment missing")
    require(environment.get("mode") == "GITHUB_ACTIONS_UBUNTU_LINUX",
            "process-group reaping environment mode drift")
    require(environment.get("productionEvidence") is False,
            "process-group reaping cannot claim production evidence")
    require(environment.get("syntheticDataOnly") is True,
            "process-group reaping must remain synthetic")
    require(environment.get("containsSecrets") is False,
            "process-group reaping must state containsSecrets false")
    require(result.get("result") == "PASS" and result.get("integrityResult") == "PASS",
            "process-group reaping result is not PASS")
    require(result.get("exitCode") == 0, "process-group reaping exitCode is not zero")
    assertions = result.get("assertions")
    require(isinstance(assertions, dict), "process-group reaping assertions missing")
    for flag in (
        "workerFrameObservedBeforeCancel", "returnedContextCanceled",
        "allCapturedProcEntriesGone", "spoolResidueAbsent",
    ):
        require(assertions.get(flag) is True, f"process-group reaping assertion failed: {flag}")
    before = assertions.get("trackedProcessCountBeforeCancel")
    after = assertions.get("trackedProcessCountAfterCancel")
    require(isinstance(before, int) and before >= 2,
            "process-group reaping must observe at least worker plus child")
    require(after == 0, "captured process entries remain after cancellation")
    latency = assertions.get("cancellationLatencyMilliseconds")
    require(isinstance(latency, (int, float)) and 0 <= latency < 1000,
            "process-group reaping cancellation latency must remain below one second")
    limitations = strings(result.get("limitations"), "result.limitations", 5)
    joined = "\n".join(limitations)
    for phrase in (
        "host or container restart not executed",
        "production artifact not exercised",
        "production-equivalent environment not exercised",
        "not production chaos evidence",
    ):
        require(phrase in joined, f"process-group reaping limitation omitted: {phrase}")
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "password=", "authorization: bearer", "processid", "workerpath",
        "spoolpath", "secretaccesskey", "account_id", "session_id",
    ):
        require(forbidden not in serialized,
                f"process-group reaping result contains forbidden value: {forbidden}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-parser-process-group-reaping.v1",
            "process-group reaping contract schemaVersion drift")
    require(contract.get("resultsSchemaVersion") ==
            "memory-os-parser-process-group-reaping-results.v1",
            "process-group reaping results schemaVersion drift")
    require(contract.get("runnerCommand") ==
            "go test ./internal/parsersup -run ^TestSupervisorReapsChildProcessGroupAfterCancellation$ -count=1",
            "process-group reaping runner command drift")
    require(contract.get("workingDirectory") == "services/import-api",
            "process-group reaping workingDirectory drift")
    strings(contract.get("requiredAssertions"), "requiredAssertions", 8)
    strings(contract.get("implementationGuards"), "implementationGuards", 5)
    strings(contract.get("limitations"), "limitations", 6)
    privacy = contract.get("privacy")
    require(isinstance(privacy, dict), "process-group reaping privacy missing")
    require(privacy.get("productionEvidence") is False,
            "process-group reaping contract cannot claim production evidence")
    for flag in (
        "syntheticDataOnly", "processIdentifiersInEvidenceForbidden",
        "workerPathInEvidenceForbidden", "spoolPathInEvidenceForbidden",
        "secretsInEvidenceForbidden", "userContentInEvidenceForbidden",
    ):
        require(privacy.get(flag) is True, f"process-group reaping privacy.{flag} must be true")

    supervisor = (ROOT / "services/import-api/internal/parsersup/supervisor_linux.go").read_text(encoding="utf-8")
    for snippet in (
        "SysProcAttr{Setpgid: true}",
        "syscall.Kill(-pid, syscall.SIGKILL)",
        "command.Wait()",
    ):
        require(snippet in supervisor, f"supervisor missing process-group guard: {snippet}")
    worker = (ROOT / "services/import-api/internal/parsersup/worker.go").read_text(encoding="utf-8")
    for snippet in (
        'case "frame_child_then_sleep"', "exec.Command(executable)",
        "workerEnvWithMode(os.Environ(), \"sleep\")", "child.Start()",
    ):
        require(snippet in worker, f"worker harness missing child-process boundary: {snippet}")
    test_source = (ROOT / "services/import-api/internal/parsersup/process_group_reaping_drill_linux_test.go").read_text(encoding="utf-8")
    for snippet in (
        "markedProcessIDs", 'os.ReadDir("/proc")', "len(tracked) >= 2",
        "allProcEntriesGone", "context.Canceled",
        "MEMORY_OS_TRACKED_PROCESS_COUNT_BEFORE_CANCEL",
        "MEMORY_OS_TRACKED_PROCESS_COUNT_AFTER_CANCEL=0",
    ):
        require(snippet in test_source, f"process-group reaping test missing boundary: {snippet}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "process-group reaping readiness missing")
    for foundation in (
        "contractDefined", "workerHarnessImplemented", "testImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(foundation) is True,
                f"process-group reaping readiness.{foundation} must be true")
    for flag in ("hostRestartExecuted", "productionArtifactExecuted", "productionReady"):
        require(readiness.get(flag) is False,
                f"process-group reaping cannot promote readiness.{flag}")
    if readiness.get("childProcessOrphanScanCompleted") is True:
        require(readiness.get("exactSourcePassResultCommitted") is True,
                "completed child-process scan requires committed exact-source result")
        require(RESULT_PATH.is_file(), "completed child-process scan requires result file")

    refs = strings(contract.get("evidenceRefs"), "evidenceRefs", 7)
    for ref in refs:
        require((ROOT / ref).is_file(), f"process-group reaping evidence missing: {ref}")

    expected_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    if expected_sha:
        require(SHA_RE.fullmatch(expected_sha) is not None,
                "EXPECTED_COMMIT_SHA must be a full SHA")
        require(RESULT_PATH.is_file(), "exact-source process-group reaping result is missing")
    if RESULT_PATH.is_file():
        validate_result(load(RESULT_PATH), expected_sha)

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "process-group reaping evidence cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict) and gate.get("status") != "READY",
            "local process-group reaping cannot make OPS-P0-009 READY")

    print("Memory OS parser process-group reaping validation PASS")
    print(f"result present: {RESULT_PATH.is_file()}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"PARSER PROCESS-GROUP REAPING VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
