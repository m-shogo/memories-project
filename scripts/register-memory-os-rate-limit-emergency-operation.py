#!/usr/bin/env python3
"""Append one validated rate-limit emergency-operation event.

This writer records bounded operational intent/evidence only. It never mutates
runtime rate-limit state and it cannot create production readiness.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/rate-limit-emergency-ledger-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/rate-limit-emergency-ledger.v1.json"
POLICY = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
OPERATIONS = ROOT / "contracts/operations/rate-limit-operations-contract.v1.json"
LOCK = ROOT / "contracts/operations/.rate-limit-emergency-ledger.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
EVENT_ID = re.compile(r"^rle_[a-z0-9][a-z0-9_-]{7,63}$")
OPERATION_ID = re.compile(r"^rlo_[a-z0-9][a-z0-9_-]{7,63}$")
REF_ID = re.compile(r"^(?:op|rv)_[a-z0-9][a-z0-9_-]{7,63}$")
MODES = {"NORMAL_CONFIGURED", "STRICT_LOCAL_EMERGENCY", "ROUTE_FAIL_CLOSED"}
PROXY_MODES = {"TRUSTED_PROXY_CONFIGURED", "TRUSTED_PROXY_DISABLED"}
ENVIRONMENTS = {"LOCAL_SIMULATION", "PRODUCTION_EQUIVALENT", "PRODUCTION"}
EVENT_TYPES = {"ACTIVATE_INTENT", "EXPIRE_OBSERVED", "RESTORE_VERIFIED", "CLOSE_OPERATION"}
PRODUCTION_CONFIRMATION = "REGISTER PRODUCTION RATE LIMIT OPERATION INTENT"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(result.returncode == 0, f"git {' '.join(args)} failed")
    return result.stdout.strip()


def timestamp(value: Any, field: str) -> dt.datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be UTC RFC3339")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail(f"{field} invalid") from exc
    require(parsed.utcoffset() == dt.timedelta(0), f"{field} must be UTC")
    return parsed


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum, f"{field} requires at least {minimum} item(s)")
    require(all(isinstance(item, str) and item for item in value), f"{field} invalid")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def validate_common(record: dict[str, Any]) -> None:
    require(record.get("schemaVersion") == "memory-os-rate-limit-emergency-operation-event.v1", "record schema drift")
    require(isinstance(record.get("eventId"), str) and EVENT_ID.fullmatch(record["eventId"]) is not None, "eventId invalid")
    require(isinstance(record.get("operationId"), str) and OPERATION_ID.fullmatch(record["operationId"]) is not None, "operationId invalid")
    require(record.get("eventType") in EVENT_TYPES, "eventType invalid")
    require(isinstance(record.get("sourceCommitSha"), str) and SHA40.fullmatch(record["sourceCommitSha"]) is not None, "sourceCommitSha invalid")
    timestamp(record.get("recordedAt"), "recordedAt")
    require(isinstance(record.get("operatorRef"), str) and REF_ID.fullmatch(record["operatorRef"]) is not None, "operatorRef invalid")
    require(isinstance(record.get("reviewerRef"), str) and REF_ID.fullmatch(record["reviewerRef"]) is not None, "reviewerRef invalid")
    require(record["operatorRef"] != record["reviewerRef"], "operator and reviewer must be distinct")
    require(record.get("runtimeApplied") is False, "writer cannot register runtimeApplied=true before control-plane integration")
    require(record.get("productionEvidence") is False, "writer cannot create production evidence")
    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in ("postgres://", "postgresql://", "authorization: bearer", "password=", "minioadmin", "raw_ip", "bearer_token", "account_id", "request_body", "@"):
        require(forbidden not in serialized, f"record contains forbidden material: {forbidden}")


def validate_activation(record: dict[str, Any], policy: dict[str, Any], operations: dict[str, Any], confirmation: str) -> None:
    required = set(load(CONTRACT).get("requiredActivationFields", []))
    require(required.issubset(record), f"activation missing fields: {sorted(required - set(record))}")
    require(record.get("environmentClass") in ENVIRONMENTS, "environmentClass invalid")
    if record["environmentClass"] == "PRODUCTION":
        require(confirmation == PRODUCTION_CONFIRMATION, f"production intent requires confirmation: {PRODUCTION_CONFIRMATION}")
    require(isinstance(record.get("environmentIdentityDigest"), str) and SHA256.fullmatch(record["environmentIdentityDigest"]) is not None, "environmentIdentityDigest invalid")
    previous = record.get("previousMode")
    requested = record.get("requestedMode")
    require(previous in MODES and requested in MODES and previous != requested, "mode transition invalid")
    allowed = {(row.get("from"), row.get("to")) for row in operations.get("allowedTransitions", []) if isinstance(row, dict)}
    require((previous, requested) in allowed, "mode transition is not permitted by operations authority")
    require(record.get("proxyMode") in PROXY_MODES, "proxyMode invalid")
    known = {row.get("policyId"): row for row in policy.get("policies", []) if isinstance(row, dict)}
    affected = strings(record.get("affectedPolicyIds"), "affectedPolicyIds")
    require(all(item in known for item in affected), "affectedPolicyIds contains unknown policy")
    if requested == "STRICT_LOCAL_EMERGENCY":
        require(all(known[item].get("failureMode") == "fail_closed_emergency_local" for item in affected), "strict local emergency requested for policy without emergency-local authority")
    starts = timestamp(record.get("startsAt"), "startsAt")
    expires = timestamp(record.get("expiresAt"), "expiresAt")
    require(expires > starts, "expiresAt must be after startsAt")
    require(expires - starts <= dt.timedelta(minutes=60), "emergency activation exceeds 60-minute maximum")
    require(isinstance(record.get("incidentReference"), str) and record["incidentReference"], "incidentReference required")
    require(record.get("activationReasonCode") in {"SHARED_STORE_UNAVAILABLE", "POLICY_STATE_UNCERTAIN", "IDENTITY_BOUNDARY_UNCERTAIN", "CARDINALITY_STATE_UNCERTAIN", "RECOVERY_CANARY"}, "activationReasonCode invalid")
    require(record.get("publicCommunicationDecision") in {"NOT_REQUIRED", "REVIEW_REQUIRED", "COMMUNICATION_REQUIRED"}, "publicCommunicationDecision invalid")


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".rate-limit-ledger.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    record_path = Path(args.record).resolve()
    try:
        record_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Fail("input record must be outside repository")
    require(git("status", "--porcelain") == "", "working tree must be clean")
    record = load(record_path)
    validate_common(record)
    policy = load(POLICY)
    operations = load(OPERATIONS)
    if record["eventType"] == "ACTIVATE_INTENT":
        validate_activation(record, policy, operations, args.confirm)
    else:
        require(isinstance(record.get("relatedActivationEventId"), str) and EVENT_ID.fullmatch(record["relatedActivationEventId"]) is not None, "non-activation event requires relatedActivationEventId")
    require(git("cat-file", "-e", record["sourceCommitSha"] + "^{commit}") == "", "source commit does not exist")

    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("rate-limit ledger lock already exists") from exc
    try:
        os.write(lock_fd, (record["operationId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        events = registry.get("events")
        require(isinstance(events, list), "registry events invalid")
        require(all(isinstance(item, dict) for item in events), "registry contains invalid event")
        require(all(item.get("eventId") != record["eventId"] for item in events), "eventId already registered")
        if record["eventType"] != "ACTIVATE_INTENT":
            require(any(item.get("eventId") == record["relatedActivationEventId"] and item.get("operationId") == record["operationId"] for item in events), "related activation event not registered")
        events.append(record)
        registry["registeredEventCount"] = len(events)
        registry["registeredOperationCount"] = len({item.get("operationId") for item in events})
        atomic_write(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass
    print(f"Registered rate-limit operation event: {record['eventId']}")
    print("Runtime state was not changed; production evidence remains false.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RATE-LIMIT OPERATION REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
