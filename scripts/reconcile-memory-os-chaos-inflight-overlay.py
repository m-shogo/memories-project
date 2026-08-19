#!/usr/bin/env python3
"""Converge the in-flight cancellation slice of OPS-P0-009.

The overlay remains conservative for host/container restart, while preserving
completed child-process reaping authority when its exact-source result validates.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/parser-inflight-cancellation-results.sample.v1.json"
PROCESS_GROUP_RESULT = ROOT / "docs/fixtures/memory-os-operability/parser-process-group-reaping-results.sample.v1.json"
INFLIGHT_VALIDATOR = ROOT / "scripts/validate-memory-os-parser-inflight-cancellation.py"
PROCESS_GROUP_VALIDATOR = ROOT / "scripts/validate-memory-os-parser-process-group-reaping.py"
GAP = "in-flight parser cancellation latency and process-group termination proof while the worker is blocked"
CHILD_REAPING_GAP = "independent child-process orphan/reaping scan after parser process-group termination"
HOST_RESTART_GAP = "parser host or container restart recovery using a reviewed production artifact"
EVIDENCE = "started-worker parser cancellation drill proving a completed frame reaches spool storage before cancellation, the blocked pipe read returns context.Canceled in under one second, cleanup removes the partial attempt and the same spool ID recovers with independent verification"
REFS = (
    "contracts/operations/parser-inflight-cancellation-contract.v1.json",
    "docs/fixtures/memory-os-operability/parser-inflight-cancellation-results.sample.v1.json",
    "services/import-api/internal/parsersup/supervisor_linux.go",
    "services/import-api/internal/parsersup/worker.go",
    "services/import-api/internal/parsersup/inflight_cancellation_drill_linux_test.go",
    "scripts/validate-memory-os-parser-inflight-cancellation.py",
    "scripts/reconcile-memory-os-parser-inflight-cancellation.py",
    "scripts/reconcile-memory-os-chaos-inflight-overlay.py",
    ".github/workflows/parser-inflight-cancellation.yml",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def load_result_validator(path: Path, module_name: str):
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ReconcileFailure(f"canonical result validator missing or escapes repository: {path.name}") from exc
    require(resolved == Path("scripts") / path.name and path.is_file(),
            f"canonical result validator path drift: {path.name}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None,
            f"cannot load canonical result validator: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = getattr(module, "validate_result", None)
    require(callable(validator), f"canonical result validator missing validate_result: {path.name}")
    return validator


def validate_inflight_result(result: dict[str, Any]) -> None:
    try:
        load_result_validator(
            INFLIGHT_VALIDATOR,
            "memory_os_inflight_cancellation_for_chaos_overlay",
        )(result, None)
    except Exception as exc:
        if exc.__class__.__name__ in {"ValidationFailure", "ReconcileFailure"}:
            raise ReconcileFailure(f"in-flight cancellation authority invalid: {exc}") from exc
        raise


def process_group_reaping_complete() -> bool:
    if not PROCESS_GROUP_RESULT.is_file():
        return False
    try:
        load_result_validator(
            PROCESS_GROUP_VALIDATOR,
            "memory_os_process_group_reaping_for_inflight",
        )(load(PROCESS_GROUP_RESULT), None)
    except Exception as exc:
        if exc.__class__.__name__ in {"ValidationFailure", "ReconcileFailure"}:
            raise ReconcileFailure(f"process-group reaping authority invalid: {exc}") from exc
        raise
    return True


def unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def normalize(status: dict[str, Any]) -> dict[str, Any]:
    require(status.get("productionDecision") == "NO_GO",
            "in-flight overlay requires productionDecision NO_GO")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict), "OPS-P0-009 missing")
    require(gate.get("status") == "PARTIAL", "OPS-P0-009 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-009 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-009 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-009 evidenceRefs must be a list")

    if RESULT_PATH.is_file():
        validate_inflight_result(load(RESULT_PATH))
        while GAP in missing:
            missing.remove(GAP)
        if EVIDENCE not in existing:
            existing.append(EVIDENCE)
        if process_group_reaping_complete():
            while CHILD_REAPING_GAP in missing:
                missing.remove(CHILD_REAPING_GAP)
        elif CHILD_REAPING_GAP not in missing:
            missing.append(CHILD_REAPING_GAP)
        if HOST_RESTART_GAP not in missing:
            missing.append(HOST_RESTART_GAP)
        for ref in REFS:
            require((ROOT / ref).is_file(), f"in-flight evidence path missing: {ref}")
            if ref not in refs:
                refs.append(ref)
    else:
        while EVIDENCE in existing:
            existing.remove(EVIDENCE)
        if GAP not in missing:
            missing.append(GAP)
        for ref in REFS:
            while ref in refs:
                refs.remove(ref)

    gate["existingEvidence"] = unique(existing)
    gate["missingEvidence"] = unique(missing)
    gate["evidenceRefs"] = unique(refs)
    require(gate.get("status") == "PARTIAL", "OPS-P0-009 readiness changed unexpectedly")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    current = load(STATUS_PATH)
    candidate = normalize(copy.deepcopy(current))
    candidate["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    left = copy.deepcopy(current)
    right = copy.deepcopy(candidate)
    left.pop("asOf", None)
    right.pop("asOf", None)
    changed = left != right

    if args.check:
        require(not changed, "in-flight chaos authority overlay is not normalized")
        print("Memory OS in-flight chaos authority overlay check PASS")
        return 0
    if not changed:
        print("Memory OS in-flight chaos authority overlay already normalized")
        return 0
    STATUS_PATH.write_text(
        json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Normalized in-flight cancellation evidence within OPS-P0-009")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"CHAOS IN-FLIGHT OVERLAY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
