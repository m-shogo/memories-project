#!/usr/bin/env python3
"""Prove metrics authority reconciles reject substitution and roll back post-write failure."""

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


def controlled_failure(module: ModuleType):
    def fail_after_write() -> None:
        raise module.ReconcileFailure("controlled post-write validator failure")
    return fail_after_write


def expect_rejection(callback, expected: str, name: str) -> None:
    try:
        callback()
    except Exception as exc:
        require(expected in str(exc), f"{name}: unexpected authority rejection: {exc}")
    else:
        raise NegativeFailure(f"{name}: authority substitution was incorrectly accepted: {expected}")


def run_identity_case(
    name: str,
    module: ModuleType,
    substitutions: tuple[tuple[str, Path, str], ...],
) -> None:
    original_metrics = METRICS.read_bytes()
    original_status = STATUS.read_bytes()
    for attr, substitute, expected in substitutions:
        original = getattr(module, attr)
        try:
            setattr(module, attr, substitute)
            expect_rejection(module.enforce_runtime_authorities, expected, name)
        finally:
            setattr(module, attr, original)
    require(METRICS.read_bytes() == original_metrics, f"{name}: metrics changed after authority rejection")
    require(STATUS.read_bytes() == original_status, f"{name}: status changed after authority rejection")


def run_case(name: str, module: ModuleType) -> None:
    original_metrics = METRICS.read_bytes()
    original_status = STATUS.read_bytes()
    metrics = copy.deepcopy(load_json(METRICS))
    status = copy.deepcopy(load_json(STATUS))
    metrics["_rollbackNegativeMarker"] = name
    status["_rollbackNegativeMarker"] = name

    original_validator = module.validate_written_authority
    module.validate_written_authority = controlled_failure(module)
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


def run_source_delegation_case(name: str, module: ModuleType) -> None:
    original_metrics = METRICS.read_bytes()
    original_status = STATUS.read_bytes()
    original_validator = module.validate_source_authority

    def fail_before_reconcile() -> None:
        raise module.ReconcileFailure("controlled source validator failure")

    module.validate_source_authority = fail_before_reconcile
    try:
        try:
            module.main()
        except module.ReconcileFailure as exc:
            require(
                "controlled source validator failure" in str(exc),
                f"{name}-source: unexpected failure: {exc}",
            )
        else:
            raise NegativeFailure(f"{name}-source: source validator failure was accepted")
    finally:
        module.validate_source_authority = original_validator

    require(
        METRICS.read_bytes() == original_metrics,
        f"{name}-source: metrics authority changed after source rejection",
    )
    require(
        STATUS.read_bytes() == original_status,
        f"{name}-source: operability status changed after source rejection",
    )


def run_metrics_case(name: str, module: ModuleType) -> None:
    original_metrics = METRICS.read_bytes()
    metrics = copy.deepcopy(load_json(METRICS))
    metrics["description"] = f"synthetic rollback marker: {name}"

    original_validator = module.validate_written_authority
    module.validate_written_authority = controlled_failure(module)
    try:
        try:
            module.write_transactionally(metrics)
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


def run_status_case(name: str, module: ModuleType) -> None:
    original_status = STATUS.read_bytes()
    status = copy.deepcopy(load_json(STATUS))
    status["asOf"] = "2099-01-01"

    original_validator = module.validate_written_authority
    module.validate_written_authority = controlled_failure(module)
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
    primary = load_module(
        "metrics_primary_contract_reconcile",
        "scripts/reconcile-memory-os-metrics-contract.py",
    )
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

    run_identity_case(
        "operations",
        operations,
        (
            ("METRICS_PATH", ROOT / "README.md", "metrics contract authority drift"),
            ("DASHBOARD_PATH", ROOT / "README.md", "metrics dashboard contract authority drift"),
            ("RETENTION_PATH", ROOT / "README.md", "metrics retention contract authority drift"),
            ("STATUS_PATH", ROOT / "SECURITY.md", "production operability status authority drift"),
            ("METRICS_VALIDATOR", alerting.CANONICAL_ALERTING_VALIDATOR, "metrics validator authority drift"),
            ("OPERATIONS_VALIDATOR", alerting.CANONICAL_ALERTING_VALIDATOR, "metrics operations validator authority drift"),
            ("OPERABILITY_VALIDATOR", alerting.CANONICAL_ALERTING_VALIDATOR, "operability validator authority drift"),
        ),
    )
    run_identity_case(
        "alerting",
        alerting,
        (
            ("METRICS_PATH", ROOT / "README.md", "metrics contract authority drift"),
            ("ALERTING_PATH", ROOT / "README.md", "metrics alerting contract authority drift"),
            ("STATUS_PATH", ROOT / "SECURITY.md", "production operability status authority drift"),
            ("METRICS_VALIDATOR", operations.CANONICAL_OPERATIONS_VALIDATOR, "metrics validator authority drift"),
            ("ALERTING_VALIDATOR", operations.CANONICAL_OPERATIONS_VALIDATOR, "metrics alerting validator authority drift"),
            ("OPERABILITY_VALIDATOR", operations.CANONICAL_OPERATIONS_VALIDATOR, "operability validator authority drift"),
        ),
    )

    run_metrics_case("primary", primary)
    run_status_case("scrape", scrape)
    run_source_delegation_case("operations", operations)
    run_case("operations", operations)
    run_source_delegation_case("alerting", alerting)
    run_case("alerting", alerting)
    print("PASS: metrics authority identity, source delegation and primary/scrape/operations/alerting rollback are fail-closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"METRICS RECONCILE ROLLBACK NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
