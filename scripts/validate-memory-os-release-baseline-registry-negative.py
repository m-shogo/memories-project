#!/usr/bin/env python3
"""Fail-closed corruption negatives for the append-only release baseline registry."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/release-baseline-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-release-baseline.py"
LOCK = ROOT / "contracts/operations/.release-baseline-registry.lock"
RECONCILER = ROOT / "scripts/reconcile-memory-os-release-baseline-registry.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_release_baseline_writer_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load release baseline writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "CONTRACT_PATH", None) == CONTRACT,
            "release writer contract authority drift")
    require(getattr(module, "REGISTRY_PATH", None) == REGISTRY,
            "release writer registry authority drift")
    require(getattr(module, "LOCK_PATH", None) == LOCK,
            "release writer append lock authority drift")
    return module


def load_reconciler() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_release_baseline_reconciler_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load release baseline reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "CONTRACT_PATH", None) == CONTRACT,
            "release reconciler contract authority drift")
    require(getattr(module, "REGISTRY_PATH", None) == REGISTRY,
            "release reconciler registry authority drift")
    require(getattr(module, "STATUS_PATH", None) == STATUS,
            "release reconciler status authority drift")
    return module


def validate_lock_binding(writer: ModuleType, contract: dict[str, Any]) -> None:
    require(contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)),
            "release contract append lock binding drift")
    require(getattr(writer, "LOCK_PATH", None) == LOCK,
            "release writer append lock binding drift")


def expect_lock_binding_rejected(writer: ModuleType, contract: dict[str, Any]) -> None:
    corrupt = copy.deepcopy(contract)
    corrupt["appendLockPath"] = "contracts/operations/.release-baseline-registry-alternate.lock"
    try:
        validate_lock_binding(writer, corrupt)
    except Fail:
        return
    raise Fail("release lock authority accepted substituted contract path")


def expect_writer_rejected(
    writer: ModuleType,
    contract: dict[str, Any],
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    corrupt = copy.deepcopy(load(REGISTRY))
    mutate(corrupt)
    try:
        writer.validate_registry_for_append(corrupt, contract)
    except Exception:
        return
    raise Fail(f"release writer accepted corrupt registry: {name}")


def expect_reconcile_rejected_without_mutation(
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    registry_before = REGISTRY.read_bytes()
    status_before = STATUS.read_bytes()
    corrupt = load(REGISTRY)
    mutate(corrupt)
    REGISTRY.write_text(json.dumps(corrupt, indent=2) + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(RECONCILER)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        require(completed.returncode != 0, f"release reconciler auto-healed corrupt registry: {name}")
        require(STATUS.read_bytes() == status_before, f"release reconciler mutated status after rejecting: {name}")
    finally:
        REGISTRY.write_bytes(registry_before)
        STATUS.write_bytes(status_before)


def validate_reconcile_validator_chain(reconciler: ModuleType) -> None:
    expected = [
        reconciler.VALIDATOR_PATH,
        reconciler.EVIDENCE_BINDING_VALIDATOR_PATH,
        reconciler.VERSION_VALIDATOR_PATH,
        reconciler.OPERABILITY_VALIDATOR_PATH,
    ]
    observed: list[Path] = []
    original_run = reconciler.subprocess.run

    def fake_run(command: list[str], *, cwd: Path, check: bool) -> None:
        require(cwd == ROOT, "release aggregate validator cwd drift")
        require(check is True, "release aggregate validators must fail closed")
        require(len(command) == 2 and command[0] == sys.executable,
                "release aggregate validator command drift")
        observed.append(Path(command[1]))

    reconciler.subprocess.run = fake_run
    try:
        reconciler.run_canonical_validators()
    finally:
        reconciler.subprocess.run = original_run

    require(observed == expected,
            "release reconcile does not enforce registry/evidence/version/operability validators in order")


def validate_reconcile_rollback(reconciler: ModuleType) -> None:
    original = STATUS.read_bytes()
    status = copy.deepcopy(load(STATUS))
    gate = next(
        (item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"),
        None,
    )
    require(isinstance(gate, dict), "OPS-P0-008 missing for release rollback probe")
    evidence = gate.get("existingEvidence")
    require(isinstance(evidence, list), "OPS-P0-008 existingEvidence missing for release rollback probe")
    evidence.append("synthetic release baseline rollback probe")

    def fail_post_write() -> None:
        raise RuntimeError("synthetic release aggregate validator failure")

    try:
        reconciler.commit_status_transaction(status, validator_runner=fail_post_write)
    except RuntimeError as exc:
        require("synthetic release aggregate validator failure" in str(exc),
                "unexpected release rollback failure reason")
    else:
        raise Fail("release reconcile accepted synthetic post-write aggregate failure")

    require(STATUS.read_bytes() == original,
            "release reconcile left partial status after post-write aggregate failure")


def main() -> int:
    writer = load_writer()
    reconciler = load_reconciler()
    contract = load(CONTRACT)
    validate_lock_binding(writer, contract)
    expect_lock_binding_rejected(writer, contract)
    validate_reconcile_validator_chain(reconciler)
    validate_reconcile_rollback(reconciler)
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("schema drift", lambda value: value.__setitem__("schemaVersion", "invalid")),
        ("registry class drift", lambda value: value.__setitem__("registryClass", "CANDIDATE_RELEASES")),
        ("appendOnly false", lambda value: value.__setitem__("appendOnly", False)),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
        ("boolean approved count", lambda value: value.__setitem__("approvedReleaseCount", True)),
        ("approved count drift", lambda value: value.__setitem__("approvedReleaseCount", len(value.get("releases", [])) + 1)),
        ("latest approved pointer drift", lambda value: value.__setitem__("latestApprovedReleaseId", "rel_20991231_invalid")),
        ("latest rollback pointer drift", lambda value: value.__setitem__("latestRollbackEligibleReleaseId", "rel_20991231_invalid")),
        ("unknown registry field", lambda value: value.__setitem__("unexpectedAuthority", True)),
    ]
    for name, mutate in cases:
        expect_writer_rejected(writer, contract, name, mutate)
        expect_reconcile_rejected_without_mutation(name, mutate)
    print("PASS: release baseline registry/append-lock corruption and aggregate reconcile failures are fail-closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE BASELINE REGISTRY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
