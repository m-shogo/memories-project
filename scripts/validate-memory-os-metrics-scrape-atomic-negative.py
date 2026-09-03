#!/usr/bin/env python3
"""Prove metrics derived-authority publication is atomic and transport-bound."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "contracts/operations/production-operability-status.json"
METRICS = ROOT / "contracts/operations/metrics-contract.v1.json"
TARGETS = (
    ("primary", ROOT / "scripts/reconcile-memory-os-metrics-contract.py", ("METRICS_PATH",), False),
    ("scrape", ROOT / "scripts/reconcile-memory-os-metrics-scrape-status.py", ("STATUS_PATH",), False),
    ("operations", ROOT / "scripts/reconcile-memory-os-metrics-operations.py", ("METRICS_PATH", "STATUS_PATH"), True),
    ("alerting", ROOT / "scripts/reconcile-memory-os-metrics-alerting.py", ("METRICS_PATH", "STATUS_PATH"), True),
)


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"metrics_atomic_negative_{name}", path)
    require(spec is not None and spec.loader is not None, f"cannot load {name} reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def expect_rejection(callback, expected: str, label: str) -> None:
    try:
        callback()
    except Exception as exc:
        require(expected in str(exc), f"{label}: unexpected rejection: {exc}")
    else:
        raise NegativeFailure(f"{label}: substitution was incorrectly accepted")


def run_transport_case(name: str, module: ModuleType, has_subprocess: bool) -> None:
    original_replace = module.os.replace
    original_canonical_replace = module.CANONICAL_OS_REPLACE
    fake_replace = lambda _src, _dst: None
    try:
        module.os.replace = fake_replace
        module.CANONICAL_OS_REPLACE = fake_replace
        expect_rejection(
            module.enforce_runtime_authorities,
            "canonical os.replace transport authority drift",
            f"{name}-paired-os-replace",
        )
    finally:
        module.os.replace = original_replace
        module.CANONICAL_OS_REPLACE = original_canonical_replace

    original_writer = module.atomic_write_bytes
    original_canonical_writer = module.CANONICAL_ATOMIC_WRITE_BYTES
    fake_writer = lambda _path, _payload: None
    try:
        module.atomic_write_bytes = fake_writer
        module.CANONICAL_ATOMIC_WRITE_BYTES = fake_writer
        expect_rejection(
            module.enforce_runtime_authorities,
            "canonical atomic writer authority drift",
            f"{name}-paired-atomic-writer",
        )
    finally:
        module.atomic_write_bytes = original_writer
        module.CANONICAL_ATOMIC_WRITE_BYTES = original_canonical_writer

    if has_subprocess:
        original_run = module.subprocess.run
        original_canonical_run = module.CANONICAL_SUBPROCESS_RUN
        fake_run = lambda *_args, **_kwargs: None
        try:
            module.subprocess.run = fake_run
            module.CANONICAL_SUBPROCESS_RUN = fake_run
            expect_rejection(
                module.enforce_runtime_authorities,
                "canonical subprocess transport authority drift",
                f"{name}-paired-subprocess",
            )
        finally:
            module.subprocess.run = original_run
            module.CANONICAL_SUBPROCESS_RUN = original_canonical_run
    else:
        original_spec = module.importlib.util.spec_from_file_location
        original_canonical_spec = module.CANONICAL_SPEC_FROM_FILE_LOCATION
        fake_spec = lambda *_args, **_kwargs: None
        try:
            module.importlib.util.spec_from_file_location = fake_spec
            module.CANONICAL_SPEC_FROM_FILE_LOCATION = fake_spec
            expect_rejection(
                module.enforce_runtime_authorities,
                "canonical validator spec loader authority drift",
                f"{name}-paired-spec-loader",
            )
        finally:
            module.importlib.util.spec_from_file_location = original_spec
            module.CANONICAL_SPEC_FROM_FILE_LOCATION = original_canonical_spec

        original_module = module.importlib.util.module_from_spec
        original_canonical_module = module.CANONICAL_MODULE_FROM_SPEC
        fake_module = lambda *_args, **_kwargs: object()
        try:
            module.importlib.util.module_from_spec = fake_module
            module.CANONICAL_MODULE_FROM_SPEC = fake_module
            expect_rejection(
                module.enforce_runtime_authorities,
                "canonical validator module loader authority drift",
                f"{name}-paired-module-loader",
            )
        finally:
            module.importlib.util.module_from_spec = original_module
            module.CANONICAL_MODULE_FROM_SPEC = original_canonical_module


def run_atomic_helper_failure(name: str, module: ModuleType, path: Path) -> None:
    original_bytes = path.read_bytes()
    original_mode = path.stat().st_mode & 0o7777
    original_replace = module.CANONICAL_OS_REPLACE

    def fail_replace(_src, _dst) -> None:
        raise OSError("controlled atomic replace failure")

    module.CANONICAL_OS_REPLACE = fail_replace
    try:
        try:
            module.atomic_write_bytes(path, b"synthetic atomic failure payload\n")
        except OSError as exc:
            require("controlled atomic replace failure" in str(exc), f"{name}: unexpected atomic failure: {exc}")
        else:
            raise NegativeFailure(f"{name}: controlled atomic replacement failure was accepted")
    finally:
        module.CANONICAL_OS_REPLACE = original_replace

    require(path.read_bytes() == original_bytes, f"{name}: authority bytes changed after atomic failure")
    require((path.stat().st_mode & 0o7777) == original_mode, f"{name}: authority mode changed after atomic failure")
    require(not list(path.parent.glob(f".{path.name}.*.tmp")), f"{name}: temporary atomic authority file leaked")


def run_transaction_rollback(name: str, module: ModuleType) -> None:
    original_metrics = METRICS.read_bytes()
    original_status = STATUS.read_bytes()
    original_metrics_mode = METRICS.stat().st_mode & 0o7777
    original_status_mode = STATUS.stat().st_mode & 0o7777
    original_validator = module.validate_written_authority

    def fail_after_write() -> None:
        raise module.ReconcileFailure("controlled post-write failure")

    module.validate_written_authority = fail_after_write
    try:
        if name == "primary":
            metrics = copy.deepcopy(load_json(METRICS))
            metrics["description"] = "synthetic atomic rollback marker"
            args = (metrics,)
        elif name == "scrape":
            status = copy.deepcopy(load_json(STATUS))
            status["asOf"] = "2099-01-01"
            args = (status,)
        else:
            metrics = copy.deepcopy(load_json(METRICS))
            status = copy.deepcopy(load_json(STATUS))
            metrics["_atomicRollbackNegative"] = name
            status["_atomicRollbackNegative"] = name
            args = (metrics, status)
        try:
            module.write_transactionally(*args)
        except module.ReconcileFailure as exc:
            require("controlled post-write failure" in str(exc), f"{name}: unexpected rollback failure: {exc}")
        else:
            raise NegativeFailure(f"{name}: controlled post-write failure was accepted")
    finally:
        module.validate_written_authority = original_validator

    require(METRICS.read_bytes() == original_metrics, f"{name}: metrics bytes changed after rollback")
    require(STATUS.read_bytes() == original_status, f"{name}: status bytes changed after rollback")
    require((METRICS.stat().st_mode & 0o7777) == original_metrics_mode, f"{name}: metrics mode changed after rollback")
    require((STATUS.stat().st_mode & 0o7777) == original_status_mode, f"{name}: status mode changed after rollback")
    require(not list(METRICS.parent.glob(f".{METRICS.name}.*.tmp")), f"{name}: metrics temp file leaked")
    require(not list(STATUS.parent.glob(f".{STATUS.name}.*.tmp")), f"{name}: status temp file leaked")


def main() -> int:
    for name, script, path_attrs, has_subprocess in TARGETS:
        module = load_module(name, script)
        run_transport_case(name, module, has_subprocess)
        for attr in path_attrs:
            run_atomic_helper_failure(f"{name}-{attr}", module, getattr(module, attr))
        run_transaction_rollback(name, module)
        source = script.read_text(encoding="utf-8")
        for attr in path_attrs:
            require(f"{attr}.write_text(" not in source, f"{name}: direct {attr} write_text regression")
            require(f"{attr}.write_bytes(" not in source, f"{name}: direct {attr} write_bytes rollback regression")

    print("PASS: metrics primary/scrape/operations/alerting use immutable validation and atomic transport")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"METRICS ATOMIC NEGATIVE FAILED: {exc}", file=os.sys.stderr)
        raise SystemExit(1)
