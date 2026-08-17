#!/usr/bin/env python3
"""Evaluate canonical per-operation rate-limit evidence without mutating runtime."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / "docs/evidence/rate-limit-operations"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-rate-limit-operation-evidence.py"
OPERATION_ID = re.compile(r"^RLOP-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{6,24}$")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit("operation evidence root must be object")
    return value


def load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_operation_validator", VALIDATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise SystemExit("operation evidence validator authority is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def timestamp(value: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise SystemExit("timestamp must be UTC RFC3339")
    return dt.datetime.fromisoformat(value[:-1] + "+00:00")


def resolve_ledger(raw: str | None) -> Path:
    ledger = DEFAULT_LEDGER.resolve() if raw is None else Path(raw).resolve()
    if ledger == DEFAULT_LEDGER.resolve():
        return ledger
    temp_root = Path(os.environ.get("TMPDIR", "/tmp")).resolve()
    if ledger.is_relative_to(ROOT.resolve()) or ledger.is_relative_to(temp_root):
        return ledger
    raise SystemExit("ledger-dir is outside approved repository/temporary roots")


def validate_authority(ledger: Path, record: dict[str, Any]) -> None:
    validator = load_validator()
    try:
        if ledger == DEFAULT_LEDGER.resolve():
            result = validator.main()
            if result != 0:
                raise SystemExit(
                    f"canonical operation ledger validation returned non-zero: {result}"
                )
        else:
            contract, policy_ids = validator.load_contract_context()
            validator.validate_record(record, contract, policy_ids)
    except validator.ValidationFailure as exc:
        raise SystemExit(f"operation evidence authority is invalid: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--at", required=True, help="UTC RFC3339 evaluation time")
    parser.add_argument("--operation-id", required=True)
    parser.add_argument(
        "--ledger-dir",
        help="optional repository/tmp ledger root for isolated CI self-tests; default is canonical ledger",
    )
    args = parser.parse_args()
    at = timestamp(args.at)
    if OPERATION_ID.fullmatch(args.operation_id) is None:
        raise SystemExit("operation-id format invalid")
    ledger = resolve_ledger(args.ledger_dir)
    path = ledger / f"{args.operation_id}.json"
    if not path.is_file():
        print(json.dumps({
            "operationId": args.operation_id,
            "evaluatedAt": args.at,
            "effectiveState": "FAIL_CLOSED_UNKNOWN_OPERATION",
            "runtimeMutationPerformed": False,
            "productionEvidence": False,
            "productionReady": False,
        }, indent=2))
        return 0

    record = load(path)
    validate_authority(ledger, record)
    started = timestamp(record["startedAt"])
    expires = timestamp(record["expiresAt"])
    lifecycle = record.get("lifecycle")
    restored_at = record.get("restoredAt")

    if lifecycle == "RESTORED":
        state = "RESTORED_EVIDENCE_RECORDED"
    elif lifecycle == "FAILED":
        state = "FAIL_CLOSED_FAILED_OPERATION"
    elif at < started:
        state = "NOT_YET_ACTIVE"
    elif at >= expires:
        state = "EXPIRED_FAIL_CLOSED_RUNTIME_REQUIRES_VERIFICATION"
    elif lifecycle == "ACTIVE":
        state = "ACTIVE_EVIDENCE_WINDOW_RUNTIME_UNVERIFIED"
    elif lifecycle == "PLANNED":
        state = "PLANNED_NOT_RUNTIME_AUTHORITY"
    else:
        state = "FAIL_CLOSED_UNKNOWN_LIFECYCLE"

    output = {
        "operationId": args.operation_id,
        "evaluatedAt": args.at,
        "effectiveState": state,
        "recordedLifecycle": lifecycle,
        "requestedMode": record.get("newMode"),
        "expiresAt": record.get("expiresAt"),
        "restoredAt": restored_at,
        "runtimeApplied": False,
        "runtimeMutationPerformed": False,
        "automaticRuntimeExpiryProven": False,
        "productionEvidence": False,
        "productionReady": False,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
