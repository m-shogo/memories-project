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
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
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


def expect_direct_authority_rejected(
    reconciler: Any,
    name: str,
    field: str,
    mutate: Callable[[], None],
    restore: Callable[[], None],
    contract_before: bytes,
    registry_before: bytes,
    status_before: bytes,
) -> None:
    mutate()
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct reconciler unexpectedly accepted: {name}")
        require(CONTRACT.read_bytes() == contract_before, f"canonical contract mutated while rejecting {name}")
        require(REGISTRY.read_bytes() == registry_before, f"canonical registry mutated while rejecting {name}")
        require(STATUS.read_bytes() == status_before, f"canonical status mutated while rejecting {name}")
    finally:
        restore()


def prove_atomic_write_failure(reconciler: Any, contract_before: bytes, registry_before: bytes, status_before: bytes) -> None:
    original_replace = reconciler.os.replace

    def reject_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("synthetic atomic replace rejection")

    reconciler.os.replace = reject_replace
    try:
        try:
            reconciler.write_text(CONTRACT, contract_before.decode("utf-8") + " ")
        except reconciler.Fail as exc:
            require("cannot atomically write" in str(exc), f"atomic write rejected at wrong boundary: {exc}")
        else:
            raise Fail("synthetic atomic replace failure unexpectedly accepted")
    finally:
        reconciler.os.replace = original_replace

    require(CONTRACT.read_bytes() == contract_before, "atomic replace rejection mutated canonical drill-request contract")
    require(REGISTRY.read_bytes() == registry_before, "atomic replace rejection mutated canonical drill-request registry")
    require(STATUS.read_bytes() == status_before, "atomic replace rejection mutated canonical production status")
    leftovers = (
        list(CONTRACT.parent.glob(f".{CONTRACT.name}.*.tmp"))
        + list(REGISTRY.parent.glob(f".{REGISTRY.name}.*.tmp"))
        + list(STATUS.parent.glob(f".{STATUS.name}.*.tmp"))
    )
    require(not leftovers, f"atomic replace rejection left temporary drill-request authority files: {leftovers}")
    print("PASS boundary: failed atomic drill-request write preserves canonical bytes and cleans temporary files")


def main() -> int:
    require(RECONCILER.is_file(), "drill request reconciler missing")
    for path in (CONTRACT, REGISTRY, GEN_REGISTRY, OBJECTIVES, STATUS):
        require(path.is_file(), f"canonical authority missing: {path.name}")

    reconciler = load_reconciler()
    require(issubclass(reconciler.Fail, RuntimeError), "reconciler Fail must remain a runtime validation error")

    canonical_contract = CONTRACT.read_bytes()
    canonical_registry = REGISTRY.read_bytes()
    canonical_status = STATUS.read_bytes()
    original_contract_path = reconciler.CONTRACT
    original_registry_path = reconciler.REGISTRY
    original_gen_registry = reconciler.GEN_REGISTRY
    original_objectives_registry = reconciler.OBJECTIVES_REGISTRY
    original_status_path = reconciler.STATUS
    original_writer = reconciler.WRITER
    original_eligibility = reconciler.ELIGIBILITY_HELPER
    original_objectives_writer = reconciler.OBJECTIVES_WRITER
    original_validator = reconciler.VALIDATOR
    original_operability = reconciler.OPERABILITY_VALIDATOR

    authority_cases = (
        ("drill request contract substitution", "drill request contract", "CONTRACT", original_status_path),
        ("drill request registry substitution", "drill request registry", "REGISTRY", original_contract_path),
        ("environment generation registry substitution", "environment generation registry", "GEN_REGISTRY", original_registry_path),
        ("recovery objectives registry substitution", "recovery objectives registry", "OBJECTIVES_REGISTRY", original_registry_path),
        ("drill request writer substitution", "drill request writer", "WRITER", original_objectives_writer),
        ("semantic eligibility helper substitution", "semantic generation eligibility helper", "ELIGIBILITY_HELPER", original_writer),
        ("recovery objectives writer substitution", "recovery objectives writer", "OBJECTIVES_WRITER", original_writer),
        ("drill request validator substitution", "drill request validator", "VALIDATOR", original_operability),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", original_validator),
        ("production status substitution", "production operability status", "STATUS", original_contract_path),
    )
    for name, field, attribute, replacement in authority_cases:
        original = getattr(reconciler, attribute)
        expect_direct_authority_rejected(
            reconciler,
            name,
            field,
            lambda attribute=attribute, replacement=replacement: setattr(reconciler, attribute, replacement),
            lambda attribute=attribute, original=original: setattr(reconciler, attribute, original),
            canonical_contract,
            canonical_registry,
            canonical_status,
        )

    prove_atomic_write_failure(reconciler, canonical_contract, canonical_registry, canonical_status)

    original_enforcer = reconciler.enforce_runtime_authorities
    try:
        # Production direct invocation is canonical-only. Repo-local copies are
        # allowed only inside this negative harness to prove corruption rejection
        # and byte-for-byte rollback independently of the runtime identity gate.
        reconciler.enforce_runtime_authorities = lambda: None

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
    finally:
        reconciler.enforce_runtime_authorities = original_enforcer
        reconciler.CONTRACT = original_contract_path
        reconciler.REGISTRY = original_registry_path
        reconciler.GEN_REGISTRY = original_gen_registry
        reconciler.OBJECTIVES_REGISTRY = original_objectives_registry
        reconciler.STATUS = original_status_path

    print("Memory OS backup/restore drill request reconcile rollback negative suite PASS")
    print(f"direct reconciler data/executable authority substitutions rejected: {len(authority_cases)}")
    print("corrupt recovery objective authority rejected before derived writes: true")
    print("shared objective authority corruption cases: 6")
    print("non-atomic drill-request authority write accepted: false")
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
