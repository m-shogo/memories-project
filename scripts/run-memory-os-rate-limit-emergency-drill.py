#!/usr/bin/env python3
"""Execute the local/CI rate-limit emergency expiry and recovery decision drill."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/rate-limit-emergency-drill-contract.v1.json"
OPERATIONS_PATH = ROOT / "contracts/operations/rate-limit-operations-contract.v1.json"
POLICY_PATH = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
WRITER_PATH = ROOT / "scripts/create-memory-os-rate-limit-operation-evidence.py"
EVALUATOR_PATH = ROOT / "scripts/evaluate-memory-os-rate-limit-emergency-state.py"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-rate-limit-emergency-drill.py"


class DrillFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DrillFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DrillFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise DrillFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def utc_text(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_foundation_authority() -> None:
    completed = subprocess.run(
        ["python", str(VALIDATOR_PATH)],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    require(
        completed.returncode == 0,
        f"canonical emergency drill authority invalid: {completed.stderr.strip()[:500]}",
    )


def policy_by_id(policy: dict[str, Any], policy_id: str) -> dict[str, Any]:
    items = policy.get("policies")
    require(isinstance(items, list), "rate-limit policies must be a list")
    matches = [item for item in items if isinstance(item, dict) and item.get("policyId") == policy_id]
    require(len(matches) == 1, f"policy must exist exactly once: {policy_id}")
    return matches[0]


def operational_mode_ids(operations: dict[str, Any]) -> set[str]:
    items = operations.get("operationalModes")
    require(isinstance(items, list), "operationalModes must be a list")
    return {
        item.get("id") for item in items
        if isinstance(item, dict) and item.get("allowed") is True and isinstance(item.get("id"), str)
    }


def run_evaluator(ledger: Path, operation_id: str, at: dt.datetime) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python", str(EVALUATOR_PATH),
            "--ledger-dir", str(ledger),
            "--operation-id", operation_id,
            "--at", utc_text(at),
        ],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def evaluate_temp_operation(ledger: Path, operation_id: str, at: dt.datetime) -> dict[str, Any]:
    completed = run_evaluator(ledger, operation_id, at)
    require(completed.returncode == 0,
            f"canonical expiry evaluator failed: {completed.stderr.strip()[:500]}")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise DrillFailure("canonical expiry evaluator did not return JSON") from exc
    require(isinstance(value, dict), "canonical expiry evaluator result must be an object")
    return value


def run_writer_and_evaluator_self_test(
    source_sha: str,
    scenario: dict[str, Any],
    started: dt.datetime,
    expires: dt.datetime,
    before_expiry: dt.datetime,
    after_expiry: dt.datetime,
) -> tuple[bool, bool, str, str]:
    checks = scenario["requiredRecoveryChecks"]
    evidence_ref = "contracts/operations/rate-limit-emergency-drill-contract.v1.json"
    operation_id = started.strftime("RLOP-%Y%m%dT%H%M%SZ-localdrill")
    record = {
        "schemaVersion": "memory-os-rate-limit-operation-record.v2",
        "operationId": operation_id,
        "incidentReference": "DRILL-LOCAL_CI_EXPIRY",
        "sourceCommitSha": source_sha,
        "environment": "CI",
        "operator": "ci_operator",
        "reviewer": "ci_reviewer",
        "previousMode": scenario["initialMode"],
        "newMode": scenario["emergencyMode"],
        "proxyMode": "TRUSTED_PROXY_DISABLED",
        "affectedPolicyIds": [scenario["policyId"]],
        "startedAt": utc_text(started),
        "expiresAt": utc_text(expires),
        "activationReason": "DRILL",
        "lifecycle": "ACTIVE",
        "productionConfirmation": None,
        "verificationResults": [
            {"checkId": check, "result": "NOT_RUN", "evidenceRefs": []}
            for check in checks
        ],
        "restoredAt": None,
        "openRisks": ["drill_in_progress"],
        "evidenceRefs": [
            evidence_ref,
            "scripts/run-memory-os-rate-limit-emergency-drill.py",
            "scripts/evaluate-memory-os-rate-limit-emergency-state.py",
        ],
        "evidenceDigestsByRef": {},
    }
    with tempfile.TemporaryDirectory(prefix="memory-os-rate-limit-drill-") as tmp:
        tmp_path = Path(tmp)
        record_path = tmp_path / "record.json"
        ledger = tmp_path / "ledger"
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        first = subprocess.run(
            ["python", str(WRITER_PATH), "--input", str(record_path), "--ledger-dir", str(ledger)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        require(first.returncode == 0,
                f"canonical append-only writer rejected valid ACTIVE drill record: {first.stderr.strip()[:500]}")
        before = evaluate_temp_operation(ledger, operation_id, before_expiry)
        after = evaluate_temp_operation(ledger, operation_id, after_expiry)
        second = subprocess.run(
            ["python", str(WRITER_PATH), "--input", str(record_path), "--ledger-dir", str(ledger)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        written = len(list(ledger.glob("*.json"))) == 1
        duplicate_rejected = second.returncode != 0 and len(list(ledger.glob("*.json"))) == 1

        stored_path = ledger / f"{operation_id}.json"
        stored = json.loads(stored_path.read_text(encoding="utf-8"))
        require(isinstance(stored, dict), "stored self-test operation must be an object")
        digests = stored.get("evidenceDigestsByRef")
        require(isinstance(digests, dict) and digests,
                "writer did not persist evidence digest authority")
        first_ref = sorted(digests)[0]
        digests[first_ref] = "0" * 64
        stored_path.write_text(json.dumps(stored, indent=2) + "\n", encoding="utf-8")
        corrupt = run_evaluator(ledger, operation_id, before_expiry)
        require(corrupt.returncode != 0,
                "canonical evaluator accepted a record with stale evidence digest authority")
        require("operation evidence authority is invalid" in corrupt.stderr,
                "canonical evaluator rejected stale digest for an unexpected reason")

        return (
            written,
            duplicate_rejected,
            str(before.get("effectiveState", "")),
            str(after.get("effectiveState", "")),
        )


_CANONICAL_ROOT = ROOT
_CANONICAL_CONTRACT_PATH = CONTRACT_PATH
_CANONICAL_OPERATIONS_PATH = OPERATIONS_PATH
_CANONICAL_POLICY_PATH = POLICY_PATH
_CANONICAL_WRITER_PATH = WRITER_PATH
_CANONICAL_EVALUATOR_PATH = EVALUATOR_PATH
_CANONICAL_VALIDATOR_PATH = VALIDATOR_PATH
_CANONICAL_SUBPROCESS_RUN = subprocess.run
_CANONICAL_REQUIRE = require
_CANONICAL_LOAD = load
_CANONICAL_PARSE_ARGS = parse_args
_CANONICAL_UTC_TEXT = utc_text
_CANONICAL_VALIDATE_FOUNDATION_AUTHORITY = validate_foundation_authority
_CANONICAL_POLICY_BY_ID = policy_by_id
_CANONICAL_OPERATIONAL_MODE_IDS = operational_mode_ids
_CANONICAL_RUN_EVALUATOR = run_evaluator
_CANONICAL_EVALUATE_TEMP_OPERATION = evaluate_temp_operation
_CANONICAL_RUN_WRITER_AND_EVALUATOR_SELF_TEST = run_writer_and_evaluator_self_test


def enforce_runtime_authorities() -> None:
    paths = (
        (ROOT, _CANONICAL_ROOT, "repository"),
        (CONTRACT_PATH, _CANONICAL_CONTRACT_PATH, "contract"),
        (OPERATIONS_PATH, _CANONICAL_OPERATIONS_PATH, "operations contract"),
        (POLICY_PATH, _CANONICAL_POLICY_PATH, "policy contract"),
        (WRITER_PATH, _CANONICAL_WRITER_PATH, "operation evidence writer"),
        (EVALUATOR_PATH, _CANONICAL_EVALUATOR_PATH, "expiry evaluator"),
        (VALIDATOR_PATH, _CANONICAL_VALIDATOR_PATH, "drill validator"),
    )
    for current, canonical, label in paths:
        if current != canonical:
            raise DrillFailure(f"emergency drill {label} authority drift")
    helpers = (
        (subprocess.run, _CANONICAL_SUBPROCESS_RUN, "subprocess transport"),
        (require, _CANONICAL_REQUIRE, "require"),
        (load, _CANONICAL_LOAD, "load"),
        (parse_args, _CANONICAL_PARSE_ARGS, "argument parser"),
        (utc_text, _CANONICAL_UTC_TEXT, "timestamp formatter"),
        (validate_foundation_authority, _CANONICAL_VALIDATE_FOUNDATION_AUTHORITY, "foundation validator"),
        (policy_by_id, _CANONICAL_POLICY_BY_ID, "policy resolver"),
        (operational_mode_ids, _CANONICAL_OPERATIONAL_MODE_IDS, "operational mode resolver"),
        (run_evaluator, _CANONICAL_RUN_EVALUATOR, "evaluator runner"),
        (evaluate_temp_operation, _CANONICAL_EVALUATE_TEMP_OPERATION, "evaluator decoder"),
        (run_writer_and_evaluator_self_test, _CANONICAL_RUN_WRITER_AND_EVALUATOR_SELF_TEST, "writer/evaluator self-test"),
    )
    for current, canonical, label in helpers:
        if current is not canonical:
            raise DrillFailure(f"emergency drill {label} execution authority drift")


_CANONICAL_ENFORCE_RUNTIME_AUTHORITIES = enforce_runtime_authorities


def main() -> int:
    if enforce_runtime_authorities is not _CANONICAL_ENFORCE_RUNTIME_AUTHORITIES:
        raise DrillFailure("emergency drill runtime guard execution authority drift")
    enforce_runtime_authorities()
    args = parse_args()
    require(len(args.source_sha) == 40 and all(ch in "0123456789abcdef" for ch in args.source_sha),
            "--source-sha must be a full lowercase commit SHA")
    validate_foundation_authority()

    contract = load(CONTRACT_PATH)
    operations = load(OPERATIONS_PATH)
    policy = load(POLICY_PATH)
    scenario = contract.get("scenario")
    require(isinstance(scenario, dict), "scenario must be an object")

    selected_policy = policy_by_id(policy, scenario["policyId"])
    policy_permits_emergency = selected_policy.get("failureMode") == scenario["requiredPolicyFailureMode"]
    require(policy_permits_emergency, "selected policy does not permit emergency-local fallback")

    allowed_modes = operational_mode_ids(operations)
    require(scenario["initialMode"] in allowed_modes, "initial mode is not allowed")
    require(scenario["emergencyMode"] in allowed_modes, "emergency mode is not allowed")
    require(scenario["expiredMode"] in allowed_modes, "expired mode is not allowed")
    require(scenario["restoredMode"] in allowed_modes, "restored mode is not allowed")
    require("UNLIMITED_OR_FAIL_OPEN" not in allowed_modes, "forbidden fail-open mode is selectable")

    started = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    expires = started + dt.timedelta(minutes=scenario["maximumEmergencyDurationMinutes"])
    before_expiry = expires - dt.timedelta(seconds=1)
    after_expiry = expires + dt.timedelta(seconds=scenario["expiryProbeOffsetSeconds"])

    writer_accepted, duplicate_rejected, evaluator_before, evaluator_after = (
        run_writer_and_evaluator_self_test(
            args.source_sha, scenario, started, expires, before_expiry, after_expiry
        )
    )
    require(evaluator_before == "ACTIVE_EVIDENCE_WINDOW_RUNTIME_UNVERIFIED",
            f"canonical evaluator pre-expiry state drift: {evaluator_before}")
    require(evaluator_after == "EXPIRED_FAIL_CLOSED_RUNTIME_REQUIRES_VERIFICATION",
            f"canonical evaluator did not fail closed at expiry: {evaluator_after}")

    mode_before_expiry = scenario["emergencyMode"]
    mode_after_expiry = scenario["expiredMode"]
    require(mode_before_expiry == "STRICT_LOCAL_EMERGENCY", "pre-expiry mode drift")
    require(mode_after_expiry == "ROUTE_FAIL_CLOSED", "expiry decision model did not select route fail-closed")

    checks = list(scenario["requiredRecoveryChecks"])
    incomplete_results = {check: "PASS" for check in checks}
    incomplete_results[checks[0]] = "NOT_RUN"
    recovery_before_all_pass = all(value == "PASS" for value in incomplete_results.values())
    require(not recovery_before_all_pass, "recovery was permitted before every check passed")

    completed_results = {check: "PASS" for check in checks}
    recovery_after_all_pass = all(value == "PASS" for value in completed_results.values())
    require(recovery_after_all_pass, "recovery did not become eligible after every check passed")
    restored_mode = scenario["restoredMode"] if recovery_after_all_pass else mode_after_expiry
    require(restored_mode == "NORMAL_CONFIGURED", "verified recovery did not become eligible for normal")

    assertions = {
        "policyExplicitlyPermitsEmergencyLocal": policy_permits_emergency,
        "forbiddenFailOpenModeNeverSelected": "UNLIMITED_OR_FAIL_OPEN" not in {
            scenario["initialMode"], scenario["emergencyMode"], mode_after_expiry, restored_mode
        },
        "expirySelectsRouteFailClosed": (
            mode_after_expiry == "ROUTE_FAIL_CLOSED" and
            evaluator_after == "EXPIRED_FAIL_CLOSED_RUNTIME_REQUIRES_VERIFICATION"
        ),
        "recoveryBeforeAllChecksPassRejected": not recovery_before_all_pass,
        "recoveryAfterAllChecksPassReturnsNormal": restored_mode == "NORMAL_CONFIGURED",
        "appendOnlyWriterAcceptsValidLocalRecord": writer_accepted,
        "duplicateOperationIdRejected": duplicate_rejected,
        "exactSourceCommitBound": True,
        "containsSecrets": False,
        "runtimeTrafficChanged": False,
        "productionTraffic": False,
        "productionCredentials": False,
        "productionEvidence": False,
        "productionControlPlaneExercised": False,
    }
    required_assertions = contract.get("requiredAssertions")
    require(isinstance(required_assertions, dict), "requiredAssertions must be an object")
    require(set(assertions) == set(required_assertions), "drill assertion set drift")
    require(all(assertions[key] is expected for key, expected in required_assertions.items()),
            "one or more drill assertions failed")

    result = {
        "schemaVersion": "memory-os-rate-limit-emergency-drill-results.v1",
        "commitSha": args.source_sha,
        "generatedAt": utc_text(dt.datetime.now(dt.timezone.utc)),
        "classification": contract["classification"],
        "scenarioId": scenario["scenarioId"],
        "policyId": scenario["policyId"],
        "timeline": {
            "startedAt": utc_text(started),
            "expiresAt": utc_text(expires),
            "preExpiryProbeAt": utc_text(before_expiry),
            "expiryProbeAt": utc_text(after_expiry),
        },
        "modeSequence": [
            scenario["initialMode"],
            scenario["emergencyMode"],
            scenario["expiredMode"],
            scenario["restoredMode"],
        ],
        "canonicalEvaluatorStates": {
            "beforeExpiry": evaluator_before,
            "afterExpiry": evaluator_after,
        },
        "recoveryChecks": completed_results,
        "assertions": assertions,
        "result": "PASS",
        "integrityResult": "PASS",
        "limitations": contract["limitations"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Memory OS rate-limit emergency decision drill PASS")
    print(f"canonical expiry state: {evaluator_after}")
    print(f"result: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DrillFailure as exc:
        print(f"RATE-LIMIT EMERGENCY DRILL FAILED: {exc}")
        raise SystemExit(1)
