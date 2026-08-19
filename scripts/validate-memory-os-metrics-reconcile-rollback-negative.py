#!/usr/bin/env python3
"""Prove metrics authority reconciles roll back on post-write failure."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "contracts/operations/metrics-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(name: str, path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected object: {path.relative_to(ROOT)}")
    return value


def run_case(name: str, module: ModuleType) -> None:
    original_metrics = METRICS.read_bytes()
    original_status = STATUS.read_bytes()
    metrics = copy.deepcopy(load_json(METRICS))
    status = copy.deepcopy(load_json(STATUS))
    metrics["_rollbackNegativeMarker"] = name
    status["_rollbackNegativeMarker"] = name

    def fail_after_write() -> None:
        raise module.ReconcileFailure("controlled post-write validator failure")

    original_validator = module.validate_written_authority
    module.validate_written_authority = fail_after_write
    try:
        try:
            module.write_transactionally(metrics, status)
        except module.ReconcileFailure as exc:
            require(
                "controlled post-write validator failure" in str(exc),
                f"{name}: unexpected failure: {exc}",
            )
        else:
            raise NegativeFailure(f"{name}: controlled validator failure was accepted")
    finally:
        module.validate_written_authority = original_validator

    require(METRICS.read_bytes() == original_metrics, f"{name}: metrics authority was not rolled back")
    require(STATUS.read_bytes() == original_status, f"{name}: operability status was not rolled back")


def run_status_case(name: str, module: ModuleType) -> None:
    original_status = STATUS.read_bytes()
    status = copy.deepcopy(load_json(STATUS))
    status["asOf"] = "2099-01-01"

    def fail_after_write() -> None:
        raise module.ReconcileFailure("controlled post-write validator failure")

    original_validator = module.validate_written_authority
    module.validate_written_authority = fail_after_write
    try:
        try:
            module.write_transactionally(status)
        except module.ReconcileFailure as exc:
            require(
                "controlled post-write validator failure" in str(exc),
                f"{name}: unexpected failure: {exc}",
            )
        else:
            raise NegativeFailure(f"{name}: controlled validator failure was accepted")
    finally:
        module.validate_written_authority = original_validator

    require(STATUS.read_bytes() == original_status, f"{name}: operability status was not rolled back")


def main() -> int:
    scrape = load_module(
        "metrics_scrape_status_reconcile",
        "scripts/reconcile-memory-os-metrics-scrape-status.py",
    )
    operations = load_module(
        "metrics_operations_reconcile",
        "scripts/reconcile-memory-os-metrics-operations.py",
    )
    alerting = load_module(
        "metrics_alerting_reconcile",
        "scripts/reconcile-memory-os-metrics-alerting.py",
    )
    run_status_case("scrape", scrape)
    run_case("operations", operations)
    run_case("alerting", alerting)
    print("PASS: metrics scrape, operations and alerting reconciles roll back after post-write validation failure")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"METRICS RECONCILE ROLLBACK NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
