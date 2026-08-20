#!/usr/bin/env python3
"""Prove drill-request reconciliation rejects corrupt authority and rolls back post-validation failures."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-request.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_request_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load drill request reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minify_json(path: Path) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    require(RECONCILER.is_file(), "drill request reconciler missing")
    for path in (CONTRACT, REGISTRY, OBJECTIVES, STATUS):
        require(path.is_file(), f"canonical authority missing: {path.name}")

    reconciler = load_reconciler()
    require(issubclass(reconciler.Fail, RuntimeError), "reconciler Fail must remain a runtime validation error")

    # A corrupt recovery-objective authority must fail before any derived drill
    # contract, request registry or production status mutation can occur.
    with tempfile.TemporaryDirectory(prefix=".memory-os-drill-objective-corruption-", dir=ROOT) as tmp:
        tmp_path = Path(tmp)
        contract = tmp_path / CONTRACT.name
        registry = tmp_path / REGISTRY.name
        objectives = tmp_path / OBJECTIVES.name
        status = tmp_path / STATUS.name
        shutil.copy2(CONTRACT, contract)
        shutil.copy2(REGISTRY, registry)
        shutil.copy2(OBJECTIVES, objectives)
        shutil.copy2(STATUS, status)

        original_contract = contract.read_bytes()
        original_registry = registry.read_bytes()
        original_status = status.read_bytes()
        valid_objectives = json.loads(objectives.read_text(encoding="utf-8"))
        require(isinstance(valid_objectives, dict), "objective registry fixture must be an object")

        reconciler.CONTRACT = contract
        reconciler.REGISTRY = registry
        reconciler.OBJECTIVES_REGISTRY = objectives
        reconciler.STATUS = status

        corruptions: dict[str, Callable[[dict[str, Any]], None]] = {
            "objective registry schema drift": lambda value: value.__setitem__("schemaVersion", "legacy-recovery-objectives"),
            "objective registry append-only disabled": lambda value: value.__setitem__("appendOnly", False),
            "objective registry boolean count": lambda value: value.__setitem__("approvedObjectiveCount", True),
            "objective registry current pointer drift": lambda value: value.__setitem__("currentObjectiveId", "ro_forged_current"),
            "objective registry production evidence forged": lambda value: value.__setitem__("productionEvidence", True),
            "objective registry production ready forged": lambda value: value.__setitem__("productionReady", True),
        }
        for name, mutate in corruptions.items():
            candidate = copy.deepcopy(valid_objectives)
            mutate(candidate)
            write_json(objectives, candidate)
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("recovery objectives registry authority invalid" in str(exc), f"{name} was not rejected by shared objective authority")
                print(f"PASS reject before write: {name}")
            else:
                raise Fail(f"reconciler unexpectedly accepted: {name}")
            require(contract.read_bytes() == original_contract, f"contract mutated while rejecting {name}")
            require(registry.read_bytes() == original_registry, f"request registry mutated while rejecting {name}")
            require(status.read_bytes() == original_status, f"production status mutated while rejecting {name}")

    with tempfile.TemporaryDirectory(prefix=".memory-os-drill-request-rollback-", dir=ROOT) as tmp:
        tmp_path = Path(tmp)
        contract = tmp_path / CONTRACT.name
        registry = tmp_path / REGISTRY.name
        objectives = tmp_path / OBJECTIVES.name
        status = tmp_path / STATUS.name
        shutil.copy2(CONTRACT, contract)
        shutil.copy2(REGISTRY, registry)
        shutil.copy2(OBJECTIVES, objectives)
        shutil.copy2(STATUS, status)

        # Preserve semantically identical but byte-distinct inputs so the synthetic
        # validators can prove reconciliation writes actually happened before the
        # aggregate operability failure forces rollback.
        for path in (contract, registry, status):
            minify_json(path)

        original_contract = contract.read_bytes()
        original_registry = registry.read_bytes()
        original_status = status.read_bytes()
        observed_commands: list[list[str]] = []

        def aggregate_failure_after_drill_success(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            require(contract.read_bytes() != original_contract, "post-validator invoked before contract reconcile write")
            require(registry.read_bytes() != original_registry, "post-validator invoked before registry reconcile write")
            require(status.read_bytes() != original_status, "post-validator invoked before production status reconcile write")
            command = [str(item) for item in (args[0] if args else [])]
            observed_commands.append(command)
            if len(observed_commands) == 1:
                require(command[-1] == str(reconciler.VALIDATOR), "drill request validator was not first post-write validator")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="synthetic drill validator success\n", stderr="")
            require(len(observed_commands) == 2, "unexpected extra post-write validator invocation")
            require(command[-1] == str(reconciler.OPERABILITY_VALIDATOR), "operability validator was not second post-write validator")
            return subprocess.CompletedProcess(args=command, returncode=23, stdout="synthetic operability failure\n", stderr="")

        reconciler.CONTRACT = contract
        reconciler.REGISTRY = registry
        reconciler.OBJECTIVES_REGISTRY = objectives
        reconciler.STATUS = status
        real_run = reconciler.subprocess.run
        reconciler.subprocess.run = aggregate_failure_after_drill_success
        try:
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("post-reconcile operability validator failed" in str(exc), "aggregate operability failure was not the rollback trigger")
            else:
                raise Fail("reconciler unexpectedly accepted failed aggregate operability validation")
        finally:
            reconciler.subprocess.run = real_run

        require(len(observed_commands) == 2, "drill and operability validators were not both invoked after writes")
        require(contract.read_bytes() == original_contract, "contract mutation survived failed aggregate validation")
        require(registry.read_bytes() == original_registry, "registry mutation survived failed aggregate validation")
        require(status.read_bytes() == original_status, "production status mutation survived failed aggregate validation")

    print("Memory OS backup/restore drill request reconcile rollback negative suite PASS")
    print("corrupt recovery objective authority rejected before derived writes: true")
    print("shared objective authority corruption cases: 6")
    print("drill request validator succeeds before aggregate failure: true")
    print("aggregate operability failure observed after all authority writes: true")
    print("contract byte-for-byte rollback: true")
    print("registry byte-for-byte rollback: true")
    print("production status byte-for-byte rollback: true")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL REQUEST RECONCILE NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
