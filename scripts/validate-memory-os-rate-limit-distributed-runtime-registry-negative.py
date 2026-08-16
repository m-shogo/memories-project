#!/usr/bin/env python3
"""Fail-closed corruption suite for distributed rate-limit runtime authority."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER_PATH = ROOT / "scripts/register-memory-os-rate-limit-distributed-runtime.py"
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-distributed-runtime.py"


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(value: dict[str, Any]) -> None:
    REGISTRY.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def expect_rejected(writer: Any, name: str, mutate: Callable[[dict[str, Any]], None], original: bytes) -> None:
    registry = json.loads(original.decode("utf-8"))
    mutate(registry)
    write(registry)
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


def prove_reconciler_no_autoheal(reconciler: Any, original: bytes) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    registry = json.loads(original.decode("utf-8"))
    registry["admittedRuntimeCount"] = False
    write(registry)
    corrupted = REGISTRY.read_bytes()
    try:
        try:
            reconciler.main()
        except reconciler.Fail:
            pass
        else:
            raise RuntimeError("reconciler accepted corrupt distributed runtime registry")
        if REGISTRY.read_bytes() != corrupted:
            raise RuntimeError("reconciler mutated corrupt distributed runtime registry")
        if CONTRACT.read_bytes() != contract_before or STATUS.read_bytes() != status_before:
            raise RuntimeError("reconciler wrote derived authority before rejecting corrupt registry")
    finally:
        REGISTRY.write_bytes(original)
        CONTRACT.write_bytes(contract_before)
        STATUS.write_bytes(status_before)


def main() -> int:
    writer = load_module(WRITER_PATH, "rate_limit_runtime_writer_negative")
    reconciler = load_module(RECONCILER_PATH, "rate_limit_runtime_reconciler_negative")
    original = REGISTRY.read_bytes()
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("schema drift", lambda r: r.__setitem__("schemaVersion", "broken")),
        ("append-only disabled", lambda r: r.__setitem__("appendOnly", False)),
        ("unknown field", lambda r: r.__setitem__("unexpectedAuthority", True)),
        ("boolean admitted count", lambda r: r.__setitem__("admittedRuntimeCount", False)),
        ("admitted count drift", lambda r: r.__setitem__("admittedRuntimeCount", 1)),
        ("boolean production-equivalent count", lambda r: r.__setitem__("productionEquivalentRuntimeCount", False)),
        ("production-equivalent count drift", lambda r: r.__setitem__("productionEquivalentRuntimeCount", 1)),
        ("boolean production count", lambda r: r.__setitem__("productionRuntimeCount", False)),
        ("production count drift", lambda r: r.__setitem__("productionRuntimeCount", 1)),
        ("production readiness promotion", lambda r: r.__setitem__("productionReady", True)),
    ]
    try:
        for name, mutate in cases:
            expect_rejected(writer, name, mutate, original)
        prove_reconciler_no_autoheal(reconciler, original)
    finally:
        REGISTRY.write_bytes(original)

    print("PASS: distributed rate-limit runtime registry corruption is rejected before append/reconcile")
    print(f"corruption cases: {len(cases)}")
    print("reconciler auto-heal: false")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
