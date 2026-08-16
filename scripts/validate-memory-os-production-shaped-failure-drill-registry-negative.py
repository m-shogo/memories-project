#!/usr/bin/env python3
"""Fail-closed corruption suite for production-shaped failure-drill authority."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/production-shaped-failure-drill-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/production-shaped-failure-drill-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER_PATH = ROOT / "scripts/register-memory-os-production-shaped-failure-drill.py"
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-production-shaped-failure-drills.py"


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_registry(value: dict[str, Any]) -> None:
    REGISTRY.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def expect_writer_rejected(writer: Any, name: str, mutate: Callable[[dict[str, Any]], None], original: bytes) -> None:
    registry = json.loads(original.decode("utf-8"))
    mutate(registry)
    write_registry(registry)
    corrupted = REGISTRY.read_bytes()
    try:
        try:
            writer.validate_registry_before_append(registry)
        except writer.Fail:
            pass
        else:
            raise RuntimeError(f"{name}: corrupt registry accepted before append")
        if REGISTRY.read_bytes() != corrupted:
            raise RuntimeError(f"{name}: rejected writer validation mutated registry")
    finally:
        REGISTRY.write_bytes(original)


def expect_reconciler_rejected(reconciler: Any, name: str, mutate: Callable[[dict[str, Any]], None], original: bytes) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    registry = json.loads(original.decode("utf-8"))
    mutate(registry)
    write_registry(registry)
    corrupted = REGISTRY.read_bytes()
    try:
        try:
            reconciler.main()
        except reconciler.Fail:
            pass
        else:
            raise RuntimeError(f"{name}: reconciler accepted corrupt registry")
        if REGISTRY.read_bytes() != corrupted:
            raise RuntimeError(f"{name}: reconciler mutated corrupt registry")
        if CONTRACT.read_bytes() != contract_before:
            raise RuntimeError(f"{name}: reconciler mutated contract before rejecting corrupt registry")
        if STATUS.read_bytes() != status_before:
            raise RuntimeError(f"{name}: reconciler mutated production status before rejecting corrupt registry")
    finally:
        REGISTRY.write_bytes(original)
        CONTRACT.write_bytes(contract_before)
        STATUS.write_bytes(status_before)


def main() -> int:
    writer = load_module(WRITER_PATH, "failure_drill_writer_negative")
    reconciler = load_module(RECONCILER_PATH, "failure_drill_reconciler_negative")
    original = REGISTRY.read_bytes()
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("schema drift", lambda r: r.__setitem__("schemaVersion", "broken")),
        ("append-only disabled", lambda r: r.__setitem__("appendOnly", False)),
        ("unknown field", lambda r: r.__setitem__("unexpectedAuthority", True)),
        ("boolean registered count", lambda r: r.__setitem__("registeredDrillCount", False)),
        ("registered count drift", lambda r: r.__setitem__("registeredDrillCount", 1)),
        ("boolean production-equivalent count", lambda r: r.__setitem__("productionEquivalentDrillCount", False)),
        ("production-equivalent count drift", lambda r: r.__setitem__("productionEquivalentDrillCount", 1)),
        ("boolean production count", lambda r: r.__setitem__("productionDrillCount", False)),
        ("production count drift", lambda r: r.__setitem__("productionDrillCount", 1)),
        ("production readiness promotion", lambda r: r.__setitem__("productionReady", True)),
    ]
    try:
        for name, mutate in cases:
            expect_writer_rejected(writer, name, mutate, original)
            expect_reconciler_rejected(reconciler, name, mutate, original)
    finally:
        REGISTRY.write_bytes(original)

    print("PASS: production-shaped failure-drill registry corruption is rejected before append/reconcile")
    print(f"corruption cases: {len(cases)}")
    print("reconciler auto-heal: false")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
