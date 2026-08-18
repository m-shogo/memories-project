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
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-rate-limit-distributed-runtime.py"
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-distributed-runtime.py"
ALTERNATE_EXECUTABLE = ROOT / "scripts/validate-memory-os-rate-limit.py"
ALTERNATE_LOCK = ROOT / "contracts/operations/.rate-limit-distributed-runtime-substitute.lock"


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


def expect_authority_rejected(validator: Any, name: str, callback: Callable[[], None]) -> None:
    try:
        callback()
    except validator.Fail:
        return
    raise RuntimeError(f"{name}: substituted authority accepted")


def prove_executable_authority_rejection(validator: Any, writer: Any, reconciler: Any) -> None:
    original_lock = writer.LOCK
    original_generation_writer = writer.GEN_WRITER
    original_reconciler_validator = reconciler.VALIDATOR
    original_reconciler_status = reconciler.STATUS
    try:
        writer.LOCK = ALTERNATE_LOCK
        expect_authority_rejected(
            validator,
            "writer lock substitution",
            lambda: validator.validate_writer_authority(writer),
        )
        writer.LOCK = original_lock

        writer.GEN_WRITER = ALTERNATE_EXECUTABLE
        expect_authority_rejected(
            validator,
            "generation writer substitution",
            lambda: validator.validate_writer_authority(writer),
        )
        writer.GEN_WRITER = original_generation_writer

        reconciler.VALIDATOR = ALTERNATE_EXECUTABLE
        expect_authority_rejected(
            validator,
            "reconciler validator substitution",
            lambda: validator.validate_reconciler_authority(reconciler),
        )
        reconciler.VALIDATOR = original_reconciler_validator

        reconciler.STATUS = CONTRACT
        expect_authority_rejected(
            validator,
            "reconciler status substitution",
            lambda: validator.validate_reconciler_authority(reconciler),
        )
    finally:
        writer.LOCK = original_lock
        writer.GEN_WRITER = original_generation_writer
        reconciler.VALIDATOR = original_reconciler_validator
        reconciler.STATUS = original_reconciler_status


def prove_contract_lock_binding_rejection(validator: Any) -> None:
    original = CONTRACT.read_bytes()
    contract = json.loads(original.decode("utf-8"))
    contract["appendLockPath"] = str(ALTERNATE_LOCK.relative_to(ROOT))
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    corrupted = CONTRACT.read_bytes()
    try:
        try:
            validator.main()
        except validator.Fail:
            pass
        else:
            raise RuntimeError("contract append lock substitution accepted")
        if CONTRACT.read_bytes() != corrupted:
            raise RuntimeError("rejected contract append lock validation mutated contract")
    finally:
        CONTRACT.write_bytes(original)


def prove_writer_post_append_rollback(writer: Any, original: bytes) -> None:
    candidate = json.loads(original.decode("utf-8"))
    candidate["admittedRuntimeCount"] = 1
    original_post_validator = writer.validate_registry_after_append

    def reject_after_append(_registry: dict[str, Any]) -> list[dict[str, Any]]:
        raise writer.Fail("synthetic post-append validation failure")

    writer.validate_registry_after_append = reject_after_append
    try:
        try:
            writer.commit_registry_update(candidate, original)
        except writer.Fail:
            pass
        else:
            raise RuntimeError("writer accepted synthetic post-append validation failure")
        if REGISTRY.read_bytes() != original:
            raise RuntimeError("writer failed to rollback registry after post-append validation failure")
    finally:
        writer.validate_registry_after_append = original_post_validator
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


def prove_reconciler_status_rollback(reconciler: Any) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    status = json.loads(status_before.decode("utf-8"))
    status["productionDecision"] = "GO"
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    corrupted_status = STATUS.read_bytes()
    try:
        try:
            reconciler.main()
        except reconciler.Fail:
            pass
        else:
            raise RuntimeError("reconciler accepted productionDecision=GO")
        if CONTRACT.read_bytes() != contract_before:
            raise RuntimeError("reconciler partially mutated distributed runtime contract before rejecting status")
        if STATUS.read_bytes() != corrupted_status:
            raise RuntimeError("reconciler mutated corrupt production status while rejecting it")
    finally:
        CONTRACT.write_bytes(contract_before)
        STATUS.write_bytes(status_before)


def main() -> int:
    writer = load_module(WRITER_PATH, "rate_limit_runtime_writer_negative")
    validator = load_module(VALIDATOR_PATH, "rate_limit_runtime_validator_negative")
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
        prove_executable_authority_rejection(validator, writer, reconciler)
        prove_contract_lock_binding_rejection(validator)
        prove_writer_post_append_rollback(writer, original)
        prove_reconciler_no_autoheal(reconciler, original)
        prove_reconciler_status_rollback(reconciler)
    finally:
        REGISTRY.write_bytes(original)

    print("PASS: distributed rate-limit runtime registry corruption, authority substitution, append rollback and reconcile partial writes are rejected")
    print(f"corruption cases: {len(cases)}")
    print("executable authority substitution: rejected")
    print("contract append lock substitution: rejected")
    print("writer post-append rollback: true")
    print("reconciler auto-heal: false")
    print("reconciler partial writes: false")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
