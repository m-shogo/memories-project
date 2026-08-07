#!/usr/bin/env python3
"""Evaluate ledger state at a supplied UTC timestamp without mutating runtime."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/rate-limit-emergency-ledger.v1.json"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit("registry root must be object")
    return value


def timestamp(value: str) -> dt.datetime:
    if not value.endswith("Z"):
        raise SystemExit("timestamp must be UTC RFC3339")
    return dt.datetime.fromisoformat(value[:-1] + "+00:00")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--at", required=True, help="UTC RFC3339 evaluation time")
    parser.add_argument("--operation-id", required=True)
    args = parser.parse_args()
    at = timestamp(args.at)
    registry = load(REGISTRY)
    events = [row for row in registry.get("events", []) if isinstance(row, dict) and row.get("operationId") == args.operation_id]
    activations = [row for row in events if row.get("eventType") == "ACTIVATE_INTENT"]
    if len(activations) != 1:
        print(json.dumps({"operationId": args.operation_id, "effectiveState": "FAIL_CLOSED_AMBIGUOUS", "runtimeMutationPerformed": False}))
        return 0
    activation = activations[0]
    starts = timestamp(activation["startsAt"])
    expires = timestamp(activation["expiresAt"])
    closures = [row for row in events if row.get("eventType") in {"RESTORE_VERIFIED", "CLOSE_OPERATION"}]
    expired_observed = [row for row in events if row.get("eventType") == "EXPIRE_OBSERVED"]
    if closures:
        state = "CLOSED_REQUIRES_RUNTIME_VERIFICATION"
    elif at < starts:
        state = "NOT_YET_ACTIVE"
    elif at >= expires:
        state = "EXPIRED_FAIL_CLOSED"
    else:
        state = "INTENT_WINDOW_OPEN_RUNTIME_UNVERIFIED"
    output = {
        "operationId": args.operation_id,
        "evaluatedAt": args.at,
        "effectiveState": state,
        "requestedMode": activation.get("requestedMode"),
        "expiresAt": activation.get("expiresAt"),
        "expiryObservationRecorded": bool(expired_observed),
        "runtimeApplied": False,
        "runtimeMutationPerformed": False,
        "productionEvidence": False,
        "productionReady": False
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
