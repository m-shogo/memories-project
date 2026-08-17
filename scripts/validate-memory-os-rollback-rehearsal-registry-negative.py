#!/usr/bin/env python3
"""Negative coverage for rollback rehearsal append-only registry authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/request-memory-os-rollback-rehearsal.py"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-rollback-rehearsal-gate.py"
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rollback-rehearsal-gate.py"
CONTRACT_PATH = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> Any:
    spec = importlib.util.spec_from_file_location("rollback_rehearsal_writer_negative", WRITER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load rollback rehearsal writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(label: str, action: Callable[[], None]) -> None:
    try:
        action()
    except Exception:
        return
    raise RuntimeError(f"corruption was accepted: {label}")


def reconcile_rejects_without_status_write(
    registry: dict[str, Any], registry_bytes: bytes, status_bytes: bytes, label: str
) -> None:
    try:
        REGISTRY_PATH.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        completed = subprocess.run(
            [sys.executable, str(RECONCILER_PATH)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode == 0:
            raise RuntimeError(f"reconciler accepted corrupt registry: {label}")
        if STATUS_PATH.read_bytes() != status_bytes:
            raise RuntimeError(f"reconciler mutated production status on rejection: {label}")
    finally:
        REGISTRY_PATH.write_bytes(registry_bytes)
        STATUS_PATH.write_bytes(status_bytes)


def validator_rejects_lock_drift(contract: dict[str, Any], contract_bytes: bytes) -> None:
    candidate = copy.deepcopy(contract)
    candidate["appendLockPath"] = "contracts/operations/.rollback-rehearsal-registry.alternate.lock"
    try:
        CONTRACT_PATH.write_text(
            json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode == 0:
            raise RuntimeError("standalone validator accepted alternate append lock authority")
    finally:
        CONTRACT_PATH.write_bytes(contract_bytes)


def main() -> int:
    writer = load_writer()
    contract = load_json(CONTRACT_PATH)
    release_registry = load_json(RELEASE_REGISTRY_PATH)
    registry = load_json(REGISTRY_PATH)
    contract_bytes = CONTRACT_PATH.read_bytes()
    registry_bytes = REGISTRY_PATH.read_bytes()
    status_bytes = STATUS_PATH.read_bytes()

    writer.validate_registry_for_append(
        copy.deepcopy(registry), copy.deepcopy(contract), copy.deepcopy(release_registry)
    )

    registry_cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("registryClass", lambda value: value.__setitem__("registryClass", "OTHER")),
        ("appendOnly", lambda value: value.__setitem__("appendOnly", False)),
        ("planningAuthorityOnly", lambda value: value.__setitem__("planningAuthorityOnly", False)),
        ("productionEvidence", lambda value: value.__setitem__("productionEvidence", True)),
        ("boolean count", lambda value: value.__setitem__("rehearsalRequestCount", False)),
        ("count drift", lambda value: value.__setitem__("rehearsalRequestCount", 1)),
        ("latest pointer drift", lambda value: value.__setitem__("latestRehearsalId", "rrh_20991231_forged")),
        ("unknown field", lambda value: value.__setitem__("unexpectedAuthority", True)),
    ]
    for label, mutate in registry_cases:
        candidate = copy.deepcopy(registry)
        mutate(candidate)
        expect_rejected(
            label,
            lambda candidate=candidate: writer.validate_registry_for_append(
                candidate, copy.deepcopy(contract), copy.deepcopy(release_registry)
            ),
        )
        if label in {"registryClass", "appendOnly", "productionEvidence", "boolean count"}:
            reconcile_rejects_without_status_write(
                copy.deepcopy(candidate), registry_bytes, status_bytes, label
            )

    release_cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("release productionEvidence", lambda value: value.__setitem__("productionEvidence", True)),
        ("release boolean count", lambda value: value.__setitem__("approvedReleaseCount", False)),
    ]
    for label, mutate in release_cases:
        candidate_release = copy.deepcopy(release_registry)
        mutate(candidate_release)
        expect_rejected(
            label,
            lambda candidate_release=candidate_release: writer.validate_registry_for_append(
                copy.deepcopy(registry), copy.deepcopy(contract), candidate_release
            ),
        )

    validator_rejects_lock_drift(contract, contract_bytes)

    if CONTRACT_PATH.read_bytes() != contract_bytes:
        raise RuntimeError("rollback contract bytes changed after negative suite")
    if REGISTRY_PATH.read_bytes() != registry_bytes:
        raise RuntimeError("rollback registry bytes changed after negative suite")
    if STATUS_PATH.read_bytes() != status_bytes:
        raise RuntimeError("production status bytes changed after negative suite")

    print("PASS: rollback rehearsal registry and append lock corruption are rejected")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ROLLBACK REHEARSAL REGISTRY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
