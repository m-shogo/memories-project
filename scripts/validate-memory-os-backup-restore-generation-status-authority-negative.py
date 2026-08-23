#!/usr/bin/env python3
"""Prove generation-status reconcile keeps canonical authority and rollback boundaries."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-status.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_generation_status_authority_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load generation status reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_direct_authority_rejected(reconciler, name: str, field: str, attribute: str, replacement: Path) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    original = getattr(reconciler, attribute)
    setattr(reconciler, attribute, replacement)
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct generation status reconciler unexpectedly accepted: {name}")
        require(CONTRACT.read_bytes() == contract_before, f"canonical contract mutated while rejecting {name}")
        require(STATUS.read_bytes() == status_before, f"canonical status mutated while rejecting {name}")
    finally:
        setattr(reconciler, attribute, original)


def main() -> int:
    require(RECONCILER.is_file(), "generation status reconciler missing")
    require(CONTRACT.is_file() and STATUS.is_file(), "canonical generation status authority missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

    cases = (
        ("generation binding contract substitution", "generation binding contract", "CONTRACT", reconciler.STATUS),
        ("generation binding validator substitution", "generation binding validator", "VALIDATOR", reconciler.BACKUP_VALIDATOR),
        ("backup validator substitution", "backup validator", "BACKUP_VALIDATOR", reconciler.OPERABILITY_VALIDATOR),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", reconciler.BACKUP_VALIDATOR),
        ("production status substitution", "production operability status", "STATUS", reconciler.CONTRACT),
    )
    for name, field, attribute, replacement in cases:
        expect_direct_authority_rejected(reconciler, name, field, attribute, replacement)
    print(f"PASS boundary: generation status direct authority substitutions rejected: {len(cases)}")

    original_enforcer = reconciler.enforce_runtime_authorities
    original_contract = reconciler.CONTRACT
    original_status = reconciler.STATUS
    original_runner = reconciler.run_validator
    original_write = reconciler.write_text
    try:
        with tempfile.TemporaryDirectory(prefix=".tmp-generation-status-authority-", dir=TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            contract_copy = tmp / CONTRACT.name
            status_copy = tmp / STATUS.name
            shutil.copyfile(CONTRACT, contract_copy)
            shutil.copyfile(STATUS, status_copy)
            status_before = status_copy.read_bytes()
            observed: list[str] = []
            status_write_observed = False

            def track_write(path: Path, text: str) -> None:
                nonlocal status_write_observed
                if path == status_copy:
                    status_write_observed = True
                original_write(path, text)

            def fail_only_aggregate(path: Path, expected_relative: Path, label: str) -> None:
                observed.append(label)
                if label == "generation binding validator":
                    require(not status_write_observed, "generation binding validator ran after status write")
                    return
                require(status_write_observed, f"{label} ran before status write")
                if label == "backup validator":
                    return
                require(label == "operability validator", f"unexpected generation status validator: {label}")
                raise reconciler.Fail("synthetic generation status operability rejection")

            # Direct production invocation is canonical-only. This harness bypasses
            # only the identity guard around repo-contained copies to prove the
            # status write plus backup/operability validation transaction. The
            # authority may already be byte-current, so observe the atomic write
            # helper rather than requiring a byte-different intermediate state.
            reconciler.enforce_runtime_authorities = lambda: None
            reconciler.CONTRACT = contract_copy
            reconciler.STATUS = status_copy
            reconciler.run_validator = fail_only_aggregate
            reconciler.write_text = track_write
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("synthetic generation status operability rejection" in str(exc), f"rollback rejected at wrong boundary: {exc}")
            else:
                raise Fail("forced generation status operability rejection unexpectedly accepted")

            require(
                observed == ["generation binding validator", "backup validator", "operability validator"],
                "generation status validator order drift",
            )
            require(status_write_observed, "generation status transaction did not invoke atomic status writer")
            require(status_copy.read_bytes() == status_before, "failed aggregate validation left production status mutation behind")
    finally:
        reconciler.enforce_runtime_authorities = original_enforcer
        reconciler.CONTRACT = original_contract
        reconciler.STATUS = original_status
        reconciler.run_validator = original_runner
        reconciler.write_text = original_write

    print("PASS rollback: generation status restored byte-for-byte after aggregate operability rejection")
    print("generation binding validator remains pre-write: true")
    print("backup and operability validators remain post-write: true")
    print("byte-current status still exercises atomic write boundary: true")
    print("canonical blockers rewritten: false")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION STATUS AUTHORITY NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
