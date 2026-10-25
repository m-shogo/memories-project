#!/usr/bin/env python3
"""Negative checks for local migration recovery-artifact reconciliation authority."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-local-migration-recovery-artifact.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action) -> None:
    try:
        action()
    except Exception as exc:
        if exc.__class__.__name__ == "Fail":
            print(f"PASS reject: {name}")
            return
        raise Fail(f"unexpected rejection for {name}: {exc.__class__.__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def select_local_run(module) -> str:
    registry = module.load(module.REGISTRY_PATH)
    records = registry.get("records")
    require(isinstance(records, list), "migration registry records missing")
    for row in reversed(records):
        if not isinstance(row, dict):
            continue
        if row.get("environmentClass") != "LOCAL_POSTGRES_REHEARSAL":
            continue
        run_id = row.get("migrationRunId")
        evidence_ref = row.get("recoveryPointRestoreEvidenceRef")
        if not isinstance(run_id, str) or not isinstance(evidence_ref, str):
            continue
        if evidence_ref == f"docs/evidence/migrations/recovery/{run_id}.json" and (module.ROOT / evidence_ref).is_file():
            return run_id
    raise Fail("no canonical local migration recovery-artifact record available for negative fixture")


def authority_identity_negative(module) -> None:
    real_operability = module.OPERABILITY_VALIDATOR_PATH
    module.OPERABILITY_VALIDATOR_PATH = module.LIFECYCLE_VALIDATOR_PATH
    try:
        expect_rejected(
            "repository-contained operability validator substitution",
            module.validate_runtime_authority,
        )
    finally:
        module.OPERABILITY_VALIDATOR_PATH = real_operability


def atomic_replace_mode_preservation(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-local-migration-recovery-mode-") as temp_dir:
        fixture = Path(temp_dir) / "authority.json"
        fixture.write_bytes(b"before\n")
        fixture.chmod(0o640)
        module.atomic_replace_bytes(fixture, b"after\n")
        require(fixture.read_bytes() == b"after\n",
                "local recovery atomic replacement did not publish fixture payload")
        require(stat.S_IMODE(fixture.stat().st_mode) == 0o640,
                "local recovery atomic replacement did not preserve existing authority mode")


def atomic_replace_negative(module) -> None:
    original_contract = module.CONTRACT_PATH.read_bytes()
    original_mode = stat.S_IMODE(module.CONTRACT_PATH.stat().st_mode)
    original_replace = module.os.replace

    def fail_replace(source, destination) -> None:
        raise OSError("synthetic local recovery atomic replace failure")

    module.os.replace = fail_replace
    try:
        try:
            module.atomic_replace_bytes(module.CONTRACT_PATH, b'{"invalid":"must-not-persist"}\n')
        except OSError as exc:
            require("synthetic local recovery atomic replace failure" in str(exc),
                    f"unexpected atomic replacement rejection: {exc}")
        else:
            raise Fail("local recovery authority accepted synthetic atomic replace failure")
    finally:
        module.os.replace = original_replace

    require(module.CONTRACT_PATH.read_bytes() == original_contract,
            "local recovery-artifact contract changed after atomic replace failure")
    require(stat.S_IMODE(module.CONTRACT_PATH.stat().st_mode) == original_mode,
            "local recovery-artifact contract mode changed after atomic replace failure")
    leftovers = list(module.CONTRACT_PATH.parent.glob(f".{module.CONTRACT_PATH.name}.*.tmp"))
    require(not leftovers, f"local recovery atomic replace left temporary authority files: {leftovers}")


def rollback_negative(module) -> None:
    run_id = select_local_run(module)
    original_contract = module.CONTRACT_PATH.read_bytes()
    original_mode = stat.S_IMODE(module.CONTRACT_PATH.stat().st_mode)
    real_load = module.load
    real_parse_args = module.parse_args
    real_run_validator = module.run_validator
    calls: list[Path] = []

    def stale_contract_load(path: Path):
        value = real_load(path)
        if path != module.CONTRACT_PATH:
            return value
        candidate = copy.deepcopy(value)
        readiness = candidate.get("readiness")
        require(isinstance(readiness, dict), "local recovery readiness missing in fixture")
        readiness["localActualRecoveryArtifactRestoreProven"] = False
        return candidate

    def fake_run_validator(path: Path, *args: str) -> None:
        calls.append(path)
        if len(calls) == 8 and path == module.OPERABILITY_VALIDATOR_PATH:
            raise module.Fail("synthetic aggregate operability rejection")

    module.load = stale_contract_load
    module.parse_args = lambda: argparse.Namespace(run_id=run_id)
    module.run_validator = fake_run_validator
    try:
        expect_rejected(
            "post-write operability rejection rolls back local recovery-artifact contract",
            module.main,
        )
        expected = [
            module.VALIDATOR_PATH,
            module.REGISTRY_VALIDATOR_PATH,
            module.LIFECYCLE_VALIDATOR_PATH,
            module.OPERABILITY_VALIDATOR_PATH,
            module.VALIDATOR_PATH,
            module.REGISTRY_VALIDATOR_PATH,
            module.LIFECYCLE_VALIDATOR_PATH,
            module.OPERABILITY_VALIDATOR_PATH,
        ]
        require(calls == expected, "local recovery validator transaction order drift")
        require(module.CONTRACT_PATH.read_bytes() == original_contract,
                "local recovery-artifact contract was not rolled back byte-for-byte")
        require(stat.S_IMODE(module.CONTRACT_PATH.stat().st_mode) == original_mode,
                "local recovery-artifact contract mode changed after rollback")
    finally:
        module.load = real_load
        module.parse_args = real_parse_args
        module.run_validator = real_run_validator
        if module.CONTRACT_PATH.read_bytes() != original_contract:
            module.CONTRACT_PATH.write_bytes(original_contract)
        module.CONTRACT_PATH.chmod(original_mode)


def rollback_failure_diagnostic_negative(module) -> None:
    run_id = select_local_run(module)
    original_contract = module.CONTRACT_PATH.read_bytes()
    original_mode = stat.S_IMODE(module.CONTRACT_PATH.stat().st_mode)
    real_load = module.load
    real_parse_args = module.parse_args
    real_run_validator = module.run_validator
    real_atomic_replace = module.atomic_replace_bytes
    calls: list[Path] = []
    post_write_failure_seen = False
    rollback_injected = False

    def stale_contract_load(path: Path):
        value = real_load(path)
        if path != module.CONTRACT_PATH:
            return value
        candidate = copy.deepcopy(value)
        readiness = candidate.get("readiness")
        require(isinstance(readiness, dict), "local recovery readiness missing in rollback diagnostic fixture")
        readiness["localActualRecoveryArtifactRestoreProven"] = False
        return candidate

    def fake_run_validator(path: Path, *args: str) -> None:
        nonlocal post_write_failure_seen
        calls.append(path)
        if len(calls) == 8 and path == module.OPERABILITY_VALIDATOR_PATH:
            post_write_failure_seen = True
            raise module.Fail("synthetic aggregate operability rejection")

    def fail_restore_after_restoring(path: Path, payload: bytes) -> None:
        nonlocal rollback_injected
        if post_write_failure_seen and path == module.CONTRACT_PATH and payload == original_contract:
            real_atomic_replace(path, payload)
            if not rollback_injected:
                rollback_injected = True
                raise OSError("synthetic local recovery rollback restore rejection")
            return
        real_atomic_replace(path, payload)

    module.load = stale_contract_load
    module.parse_args = lambda: argparse.Namespace(run_id=run_id)
    module.run_validator = fake_run_validator
    module.atomic_replace_bytes = fail_restore_after_restoring
    try:
        try:
            module.main()
        except module.Fail as exc:
            text = str(exc)
            require("synthetic aggregate operability rejection" in text,
                    f"primary local recovery validator failure was lost: {exc}")
            require("rollback incomplete" in text,
                    f"local recovery rollback incompleteness was not reported: {exc}")
            require("synthetic local recovery rollback restore rejection" in text,
                    f"local recovery rollback restore failure was lost: {exc}")
        else:
            raise Fail("local recovery reconciler accepted validator plus rollback restore failure")
        require(rollback_injected, "local recovery rollback restore failure injection did not execute")
        require(module.CONTRACT_PATH.read_bytes() == original_contract,
                "local recovery contract changed after rollback diagnostic failure")
        require(stat.S_IMODE(module.CONTRACT_PATH.stat().st_mode) == original_mode,
                "local recovery contract mode changed after rollback diagnostic failure")
    finally:
        module.load = real_load
        module.parse_args = real_parse_args
        module.run_validator = real_run_validator
        module.atomic_replace_bytes = real_atomic_replace
        if module.CONTRACT_PATH.read_bytes() != original_contract:
            module.CONTRACT_PATH.write_bytes(original_contract)
        module.CONTRACT_PATH.chmod(original_mode)



def run_id_and_path_boundary_negative(module) -> None:
    original_parse_args = module.parse_args
    original_root = module.EVIDENCE_ROOT
    original_load = module.load
    original_write = module.atomic_replace_bytes
    reads: list[Path] = []
    writes: list[Path] = []

    def forbid_read(path: Path):
        reads.append(path)
        raise Fail('unexpected local recovery read before run-id/path rejection')

    def forbid_write(path: Path, payload: bytes) -> None:
        writes.append(path)
        raise Fail('unexpected local recovery write before run-id/path rejection')

    module.load = forbid_read
    module.atomic_replace_bytes = forbid_write
    try:
        invalid_ids = (
            '../outside', '/tmp/outside', 'mig_20261025_../../outside',
            'mig_20261025_', 'mig_20261025_valid/escape',
            'mig_20261025_abc\n', 'mig_20261025_' + 'x' * 65,
            'mig_20261025_UPPER',
        )
        for run_id in invalid_ids:
            module.parse_args = lambda run_id=run_id: argparse.Namespace(run_id=run_id)
            try:
                module.main()
            except module.Fail as exc:
                require('invalid local recovery run-id' in str(exc),
                        f'wrong local recovery run-id rejection for {run_id!r}: {exc}')
            else:
                raise Fail(f'local recovery accepted invalid run-id: {run_id!r}')
            require(not reads and not writes,
                    'local recovery read or wrote authority before rejecting invalid run-id')

        with tempfile.TemporaryDirectory(prefix='local-recovery-symlink-negative-') as temp:
            root = Path(temp) / 'recovery'
            root.mkdir()
            outside = Path(temp) / 'outside.json'
            outside.write_text('{}\n', encoding='utf-8')
            run_id = 'mig_20261025_synthetic'
            (root / (run_id + '.json')).symlink_to(outside)
            module.EVIDENCE_ROOT = root
            module.parse_args = lambda: argparse.Namespace(run_id=run_id)
            try:
                module.main()
            except module.Fail as exc:
                require('missing or symlinked' in str(exc),
                        f'wrong local recovery symlink rejection: {exc}')
            else:
                raise Fail('local recovery accepted symlinked evidence result')
            require(not reads and not writes,
                    'local recovery read or wrote authority before rejecting symlinked evidence')
    finally:
        module.parse_args = original_parse_args
        module.EVIDENCE_ROOT = original_root
        module.load = original_load
        module.atomic_replace_bytes = original_write
    print('PASS local recovery run-id/path pre-read negatives (9 cases)')

def stronger_recovery_readiness_negative(module) -> None:
    contract = module.load(module.CONTRACT_PATH)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "canonical local recovery readiness missing")
    for field in module.STRONGER_RECOVERY_READINESS_FIELDS:
        require(readiness.get(field) is False, "canonical local recovery stronger readiness is not false")
        for value in (True, None, 0, "false"):
            candidate = copy.deepcopy(readiness)
            candidate[field] = value
            try:
                module.require_no_stronger_recovery_downgrade(candidate)
            except module.Fail as exc:
                require(f"cannot overwrite stronger local recovery readiness authority: {field}" in str(exc),
                        f"wrong local recovery stronger-readiness rejection: {exc}")
            else:
                raise Fail(f"local recovery stronger-readiness mutation accepted: {field}={value!r}")
    print("PASS stronger local recovery readiness strict negatives (8 cases)")

    run_id = select_local_run(module)
    original = module.CONTRACT_PATH.read_bytes()
    original_mode = stat.S_IMODE(module.CONTRACT_PATH.stat().st_mode)
    real_load = module.load
    real_parse_args = module.parse_args
    real_run_validator = module.run_validator
    real_atomic_replace = module.atomic_replace_bytes
    for field in module.STRONGER_RECOVERY_READINESS_FIELDS:
        writes: list[Path] = []

        def stronger_contract_load(path: Path):
            value = real_load(path)
            if path == module.CONTRACT_PATH:
                value = copy.deepcopy(value)
                value["readiness"][field] = True
            return value

        def forbid_write(path: Path, payload: bytes) -> None:
            writes.append(path)
            raise Fail("synthetic local recovery authority write was attempted")

        module.load = stronger_contract_load
        module.parse_args = lambda: argparse.Namespace(run_id=run_id)
        module.run_validator = lambda path, *args: None
        module.atomic_replace_bytes = forbid_write
        try:
            try:
                module.main()
            except module.Fail as exc:
                require(f"cannot overwrite stronger local recovery readiness authority: {field}" in str(exc),
                        f"wrong local recovery main-path rejection for {field}: {exc}")
            else:
                raise Fail(f"local recovery main path accepted stronger authority: {field}")
            require(not writes, f"local recovery main path attempted write before rejecting {field}")
            require(module.CONTRACT_PATH.read_bytes() == original,
                    f"local recovery main path changed canonical authority for {field}")
            require(stat.S_IMODE(module.CONTRACT_PATH.stat().st_mode) == original_mode,
                    f"local recovery main path changed canonical mode for {field}")
        finally:
            module.load = real_load
            module.parse_args = real_parse_args
            module.run_validator = real_run_validator
            module.atomic_replace_bytes = real_atomic_replace
    print("PASS stronger local recovery main-path prewrite rejection (2 cases)")


def main() -> int:
    reconciler = load_module(
        RECONCILER,
        "memory_os_local_migration_recovery_reconcile_negative_target",
    )
    reconciler.validate_runtime_authority()
    authority_identity_negative(reconciler)
    run_id_and_path_boundary_negative(reconciler)
    stronger_recovery_readiness_negative(reconciler)
    atomic_replace_mode_preservation(reconciler)
    atomic_replace_negative(reconciler)
    rollback_negative(reconciler)
    rollback_failure_diagnostic_negative(reconciler)
    print("Memory OS local migration recovery-artifact reconcile negative suite PASS")
    print("canonical validator identity: enforced")
    print("run-id grammar and symlinked evidence path: fail-closed before read")
    print("stronger local recovery readiness cannot be downgraded: enforced")
    print("atomic publication preserves existing authority mode: enforced")
    print("atomic publication failure preserves canonical authority: enforced")
    print("post-write aggregate rollback: enforced")
    print("primary plus rollback failure diagnostics: enforced")
    print("production-equivalent recovery artifact restore: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"LOCAL MIGRATION RECOVERY RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
