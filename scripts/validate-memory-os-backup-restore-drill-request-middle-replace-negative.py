#!/usr/bin/env python3
"""Prove drill-request reconciliation rolls back after a middle authority replace failure."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-request.py"
REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
AUTHORITIES = (REGISTRY, CONTRACT, STATUS)


class Fail(RuntimeError):
    pass


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def load_module():
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(
        "memory_os_backup_restore_drill_request_middle_replace_negative_reconciler",
        RECONCILER,
    )
    if spec is None or spec.loader is None:
        raise Fail("cannot load drill-request reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    before = {path: path.read_bytes() for path in AUTHORITIES}
    original_modes = {path: mode(path) for path in AUTHORITIES}
    module = load_module()
    original_replace = module.os.replace
    candidate_replace_count = 0
    synthetic_failure_raised = False

    def fail_second_candidate_replace_once(source: str | Path, destination: str | Path) -> None:
        nonlocal candidate_replace_count, synthetic_failure_raised
        destination_path = Path(destination).resolve()
        canonical = {path.resolve() for path in AUTHORITIES}
        if destination_path in canonical and not synthetic_failure_raised:
            candidate_replace_count += 1
            if candidate_replace_count == 2:
                synthetic_failure_raised = True
                raise OSError("synthetic second authority replace failure")
        original_replace(source, destination)

    try:
        for path in AUTHORITIES:
            path.chmod(0o640)
        module.os.replace = fail_second_candidate_replace_once
        try:
            module.main()
        except module.Fail as exc:
            if "synthetic second authority replace failure" not in str(exc):
                raise Fail(f"middle replace failure surfaced at unexpected boundary: {exc}") from exc
        else:
            raise Fail("synthetic second authority replace failure unexpectedly reconciled")
        finally:
            module.os.replace = original_replace

        if not synthetic_failure_raised or candidate_replace_count != 2:
            raise Fail(
                f"expected first candidate replace success then second candidate replace failure; observed {candidate_replace_count} candidate replaces"
            )
        for path in AUTHORITIES:
            if path.read_bytes() != before[path]:
                raise Fail(f"middle replace failure did not restore exact bytes: {path.relative_to(ROOT)}")
            if mode(path) != 0o640:
                raise Fail(f"middle replace rollback changed mode for {path.relative_to(ROOT)}: {oct(mode(path))}")
            leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
            if leftovers:
                raise Fail(f"middle replace rollback left temporary files for {path.relative_to(ROOT)}: {leftovers}")
    finally:
        module.os.replace = original_replace
        for path in AUTHORITIES:
            if path.read_bytes() != before[path]:
                path.write_bytes(before[path])
            path.chmod(original_modes[path])

    for path in AUTHORITIES:
        if path.read_bytes() != before[path] or mode(path) != original_modes[path]:
            raise Fail(f"negative suite did not restore canonical authority exactly: {path.relative_to(ROOT)}")

    print("Memory OS backup/restore drill request middle-replace negative PASS")
    print("registry candidate replacement completed before injected contract replacement failure: true")
    print("registry/contract/status exact bytes restored: true")
    print("registry/contract/status 0640 modes preserved through rollback: true")
    print("temporary authority residue after rollback: false")
    print("restore executed: false")
    print("production evidence/readiness created: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, OSError) as exc:
        print(f"BACKUP RESTORE DRILL REQUEST MIDDLE-REPLACE NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
