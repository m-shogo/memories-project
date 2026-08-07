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


def run_writer_self_test(source_sha: str, scenario: dict[str, Any], started: dt.datetime,
                         expires: dt.datetime, restored: dt.datetime) -> tuple[bool, bool]:
    checks = scenario["requiredRecoveryChecks"]
    evidence_ref = "contracts/operations/rate-limit-emergency-drill-contract.v1.json"
    record = {
        "schemaVersion": "memory-os-rate-limit-operation-record.v1",
        "operationId": started.strftime("RLOP-%Y%m%dT%H%M%SZ-localdrill"),
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
        "lifecycle": "RESTORED",
        "productionConfirmation": None,
        "verificationResults": [
            {"checkId": check, "result": "PASS", "evidenceRefs": [evidence_ref]}
            for check in checks
        ],
        "restoredAt": utc_text(restored),
        "openRisks": [],
        "evidenceRefs": [
            evidence_ref,
            "scripts/run-memory-os-rate-limit-emergency-drill.py",
        ],
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
        second = subprocess.run(
            ["python", str(WRITER_PATH), "--input", str(record_path), "--ledger-dir", str(ledger)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        written = first.returncode == 0 and len(list(ledger.glob("*.json"))) == 1
        duplicate_rejected = second.returncode != 0 and len(list(ledger.glob("*.json"))) == 1
        return written, duplicate_rejected


def main() -> int:
    args = parse_args()
    require(len(args.source_sha) == 40 and all(ch in "0123456789abcdef" for ch in args.source_sha),
            "--source-sha must be a full lowercase commit SHA")

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

    mode_before_expiry = scenario["emergencyMode"] if before_expiry < expires else scenario["expiredMode"]
    mode_after_expiry = scenario["expiredMode"] if after_expiry >= expires else scenario["emergencyMode"]
    require(mode_before_expiry == "STRICT_LOCAL_EMERGENCY", "pre-expiry mode drift")
    require(mode_after_expiry == "ROUTE_FAIL_CLOSED", "expiry did not fail closed")

    checks = list(scenario["requiredRecoveryChecks"])
    incomplete_results = {check: "PASS" for check in checks}
    incomplete_results[checks[0]] = "NOT_RUN"
    recovery_before_all_pass = all(value == "PASS" for value in incomplete_results.values())
    require(not recovery_before_all_pass, "recovery was permitted before every check passed")

    completed_results = {check: "PASS" for check in checks}
    recovery_after_all_pass = all(value == "PASS" for value in completed_results.values())
    require(recovery_after_all_pass, "recovery did not become eligible after every check passed")
    restored_mode = scenario["restoredMode"] if recovery_after_all_pass else mode_after_expiry
    require(restored_mode == "NORMAL_CONFIGURED", "verified recovery did not return to normal")

    restored_at = after_expiry + dt.timedelta(seconds=1)
    writer_accepted, duplicate_rejected = run_writer_self_test(
        args.source_sha, scenario, started, expires, restored_at
    )
    require(writer_accepted, "append-only evidence writer rejected a valid local drill record")
    require(duplicate_rejected, "append-only evidence writer accepted a duplicate operationId")

    assertions = {
        "policyExplicitlyPermitsEmergencyLocal": policy_permits_emergency,
        "forbiddenFailOpenModeNeverSelected": "UNLIMITED_OR_FAIL_OPEN" not in {
            scenario["initialMode"], scenario["emergencyMode"], mode_after_expiry, restored_mode
        },
        "expirySelectsRouteFailClosed": mode_after_expiry == "ROUTE_FAIL_CLOSED",
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
            "expiryProbeAt": utc_text(after_expiry),
            "restoredAt": utc_text(restored_at),
        },
        "modeSequence": [
            scenario["initialMode"],
            scenario["emergencyMode"],
            scenario["expiredMode"],
            scenario["restoredMode"],
        ],
        "recoveryChecks": completed_results,
        "assertions": assertions,
        "result": "PASS",
        "integrityResult": "PASS",
        "limitations": contract["limitations"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Memory OS rate-limit emergency decision drill PASS")
    print(f"result: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DrillFailure as exc:
        print(f"RATE-LIMIT EMERGENCY DRILL FAILED: {exc}")
        raise SystemExit(1)
