#!/usr/bin/env python3
"""Prove drill-request reconciliation rolls back after a middle authority replace failure."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-request.py"
REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
AUTHORITIES = (REGISTRY, CONTRACT, STATUS)
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


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
    if not TMP_PARENT.is_dir():
        raise Fail("temporary fixture parent missing")
    canonical_before = {path: path.read_bytes() for path in AUTHORITIES}
    canonical_modes = {path: mode(path) for path in AUTHORITIES}
    module = load_module()

    with tempfile.TemporaryDirectory(prefix=".tmp-drill-request-middle-replace-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        fixture_by_canonical: dict[Path, Path] = {}
        for source in AUTHORITIES:
            target = tmp / source.name
            shutil.copyfile(source, target)
            target.chmod(mode(source))
            fixture_by_canonical[source] = target

        fixture_authorities = tuple(fixture_by_canonical[path] for path in AUTHORITIES)
        before = {path: path.read_bytes() for path in fixture_authorities}
        original_modes = {path: mode(path) for path in fixture_authorities}
        original_registry = module.REGISTRY
        original_contract = module.CONTRACT
        original_status = module.STATUS
        original_enforce = module.enforce_runtime_authorities
        original_replace = module.os.replace
        candidate_replace_count = 0
        synthetic_failure_raised = False

        def fail_second_candidate_replace_once(source: str | Path, destination: str | Path) -> None:
            nonlocal candidate_replace_count, synthetic_failure_raised
            destination_path = Path(destination).resolve()
            fixtures = {path.resolve() for path in fixture_authorities}
            if destination_path in fixtures and not synthetic_failure_raised:
                candidate_replace_count += 1
                if candidate_replace_count == 2:
                    synthetic_failure_raised = True
                    raise OSError("synthetic second authority replace failure")
            original_replace(source, destination)

        try:
            module.REGISTRY = fixture_by_canonical[REGISTRY]
            module.CONTRACT = fixture_by_canonical[CONTRACT]
            module.STATUS = fixture_by_canonical[STATUS]
            module.enforce_runtime_authorities = lambda: None
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
            module.enforce_runtime_authorities = original_enforce
            module.REGISTRY = original_registry
            module.CONTRACT = original_contract
            module.STATUS = original_status

        if not synthetic_failure_raised or candidate_replace_count != 2:
            raise Fail(
                f"expected first candidate replace success then second candidate replace failure; observed {candidate_replace_count} candidate replaces"
            )
        for path in fixture_authorities:
            if path.read_bytes() != before[path]:
                raise Fail(f"middle replace failure did not restore exact fixture bytes: {path.name}")
            if mode(path) != original_modes[path]:
                raise Fail(f"middle replace rollback changed fixture mode for {path.name}: {oct(mode(path))}")
            leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
            if leftovers:
                raise Fail(f"middle replace rollback left temporary fixture files for {path.name}: {leftovers}")

    for path in AUTHORITIES:
        if path.read_bytes() != canonical_before[path] or mode(path) != canonical_modes[path]:
            raise Fail(f"negative suite mutated canonical authority: {path.relative_to(ROOT)}")

    print("Memory OS backup/restore drill request middle-replace negative PASS")
    print("registry fixture replacement completed before injected contract fixture replacement failure: true")
    print("fixture registry/contract/status exact bytes+mode restored: true")
    print("canonical registry/contract/status mutated during negative proof: false")
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
